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

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from agent import backend_mode, run_chat_turn

app = FastAPI(title="TUM CampusPilot QandA", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    messages: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})
    try:
        reply, dbg = await run_chat_turn(messages)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return ChatResponse(reply=reply, debug_tools=dbg)
