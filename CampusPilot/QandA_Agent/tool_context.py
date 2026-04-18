"""Request-scoped credentials for tools (never sent to the LLM as plain text)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class TumPortalCredentials:
    """TUM web login (LRZ IdP) — in memory only for the duration of one /chat request."""

    tum_username: str
    tum_password: str


tum_tool_credentials: ContextVar[TumPortalCredentials | None] = ContextVar(
    "tum_tool_credentials",
    default=None,
)
