"""Server-side chat history per logged-in user (in-memory; lost on process restart)."""

from __future__ import annotations

from typing import Any

# Rough cap so one user cannot grow RAM unbounded (each /chat adds 2 messages).
_MAX_MESSAGES = 200

_sessions: dict[int, list[dict[str, str]]] = {}


def get_messages(user_id: int) -> list[dict[str, str]]:
    return [dict(m) for m in _sessions.get(user_id, ())]


def set_messages(user_id: int, messages: list[dict[str, Any]]) -> None:
    clean: list[dict[str, str]] = []
    for m in messages:
        role = str(m.get("role", ""))
        content = m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        clean.append({"role": role, "content": content})
    if len(clean) > _MAX_MESSAGES:
        clean = clean[-_MAX_MESSAGES :]
    _sessions[user_id] = clean


def clear(user_id: int) -> None:
    _sessions.pop(user_id, None)
