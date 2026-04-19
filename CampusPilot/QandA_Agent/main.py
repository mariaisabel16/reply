"""
QandA-Agent HTTP API.

Run from this directory (CampusPilot/QandA_Agent):
  py -3.11 -m venv .venv
  .venv\\Scripts\\activate
  python -m pip install -r requirements.txt
  copy ENV.example .env   # optional: BEDROCK_MODEL_ID and AWS creds, or OPENAI_API_KEY, or OLLAMA_BASE_URL; else demo
  python -m uvicorn main:app --host 127.0.0.1 --port 8010

Windows + Playwright (TUMonline-Chat-Tools, Crawl): **nicht** ``--reload`` verwenden — uvicorn nutzt
dann einen SelectorEventLoop, der **keine** Browser-Subprozesse starten kann (NotImplementedError).
Für Auto-Reload nur auf Linux/macOS oder ohne Playwright testen.

See SETUP.txt for Windows / pip issues.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# Playwright spawns a subprocess; on Windows SelectorEventLoop raises NotImplementedError.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from typing import Annotated, Any

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from agent import backend_mode, run_chat_turn
import chat_session_store
import course_pick_pending
import registration_pending
from campus_crawl import CrawlStatusResponse, compact_study_profile_for_prompt, get_crawl_status_for_user
from campuspilot_auth import (
    SESSION_COOKIE_NAME,
    AuthUser,
    LoginBody,
    MeResponse,
    login_user,
    logout_user,
    me,
    require_auth_user,
)
from config import settings
from tool_context import TumPortalCredentials, current_auth_user_id, tum_tool_credentials
from tum_course_session import close_tum_registration_session

_log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if sys.platform == "win32":
        loop = asyncio.get_running_loop()
        if "Selector" in type(loop).__name__:
            _log.warning(
                "CampusPilot (Windows): SelectorEventLoop aktiv (typisch mit uvicorn --reload). "
                "Playwright/Chromium startet dann nicht (NotImplementedError bei Subprocess). "
                "Für TUMonline-Chat-Tools und Crawl ohne --reload starten, z.B.: "
                "python -m uvicorn main:app --host 127.0.0.1 --port 8010 — sonst sind nur NAT/Chat ohne Browser ok."
            )
    yield


app = FastAPI(title="TUM CampusPilot QandA", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def role_allowed(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("history[].role must be 'user' or 'assistant'")
        return v


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Ignored: Konversation wird serverseitig pro Login-Session gespeichert.",
    )


class ChatResponse(BaseModel):
    reply: str
    debug_tools: list[dict[str, Any]] = Field(default_factory=list)


class ChatMessagesResponse(BaseModel):
    messages: list[ChatMessage]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": backend_mode()}


@app.post("/auth/login", response_model=MeResponse)
async def auth_login(body: LoginBody, response: Response) -> MeResponse:
    return await login_user(body, response)


@app.post("/auth/logout")
async def auth_logout(
    response: Response,
    campuspilot_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
):
    return await logout_user(response, campuspilot_session)


@app.get("/auth/me", response_model=MeResponse)
async def auth_me_cookie(
    campuspilot_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> MeResponse:
    return await me(campuspilot_session)


@app.get("/auth/crawl-status", response_model=CrawlStatusResponse)
async def auth_crawl_status(user: Annotated[AuthUser, Depends(require_auth_user)]) -> CrawlStatusResponse:
    return CrawlStatusResponse(**get_crawl_status_for_user(user.user_id))


@app.get("/chat/messages", response_model=ChatMessagesResponse)
async def chat_messages_get(user: Annotated[AuthUser, Depends(require_auth_user)]) -> ChatMessagesResponse:
    rows = chat_session_store.get_messages(user.user_id)
    return ChatMessagesResponse(
        messages=[ChatMessage(role=m["role"], content=m["content"]) for m in rows],
    )


@app.post("/chat/reset")
async def chat_reset(user: Annotated[AuthUser, Depends(require_auth_user)]) -> dict[str, bool]:
    chat_session_store.clear(user.user_id)
    course_pick_pending.clear(user.user_id)
    registration_pending.clear_user(user.user_id)
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: Annotated[AuthUser, Depends(require_auth_user)],
) -> ChatResponse:
    prior = chat_session_store.get_messages(user.user_id)
    messages: list[dict[str, Any]] = [*prior, {"role": "user", "content": req.message}]
    study_ctx = compact_study_profile_for_prompt(user.user_id)
    cred_token = tum_tool_credentials.set(
        TumPortalCredentials(tum_username=user.tum_username, tum_password=user.password_plain)
    )
    uid_token = current_auth_user_id.set(user.user_id)
    try:
        reply, dbg = await run_chat_turn(messages, study_ctx)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await close_tum_registration_session()
        current_auth_user_id.reset(uid_token)
        tum_tool_credentials.reset(cred_token)
    chat_session_store.set_messages(
        user.user_id,
        [*messages, {"role": "assistant", "content": reply}],
    )
    return ChatResponse(reply=reply, debug_tools=dbg)
