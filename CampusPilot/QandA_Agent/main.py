"""
QandA-Agent HTTP API.

Run from this directory (CampusPilot/QandA_Agent):
  py -3.11 -m venv .venv
  .venv\\Scripts\\activate
  python -m pip install -r requirements.txt
  copy ENV.example .env   # optional: BEDROCK_MODEL_ID and AWS creds, or OPENAI_API_KEY, or OLLAMA_BASE_URL; else demo
  python -m uvicorn main:app --reload --port 8010

See SETUP.txt for Windows / pip issues.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from agent import backend_mode, run_chat_turn
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
from tool_context import TumPortalCredentials, tum_tool_credentials

app = FastAPI(title="TUM CampusPilot QandA", version="0.1.0")

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
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    debug_tools: list[dict[str, Any]] = Field(default_factory=list)


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


@app.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: Annotated[AuthUser, Depends(require_auth_user)],
) -> ChatResponse:
    messages: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})
    token = tum_tool_credentials.set(
        TumPortalCredentials(tum_username=user.tum_username, tum_password=user.password_plain)
    )
    try:
        reply, dbg = await run_chat_turn(messages)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        tum_tool_credentials.reset(token)
    return ChatResponse(reply=reply, debug_tools=dbg)
