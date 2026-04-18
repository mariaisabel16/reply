from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from config import settings
from demo_agent import run_demo_turn
from tools import OPENAI_TOOLS, dispatch_tool_call


SYSTEM_PROMPT = """Du bist ein Studienorganisations-Assistent für TUM-Studierende.
Du beantwortest Fragen zu Semestern, Fristen, Feiertagen und Prüfungsphasen.
Nutze ausschließlich die bereitgestellten Tool-Ergebnisse (NAT-API-Daten) als Faktenquelle.
Wenn Daten fehlen oder das Tool nicht passt, sage das klar und schlage vor, welche Information der Nutzer konkretisieren soll (z. B. Semester-Key wie 2026s).
Antworte auf Deutsch, knapp und korrekt; nenne Daten mit Datum und Titel."""

_openai_client: AsyncOpenAI | None = None
_ollama_client: AsyncOpenAI | None = None


def backend_mode() -> str:
    if settings.openai_api_key:
        return "openai"
    if settings.ollama_base_url:
        return "ollama"
    return "demo"


def _openai_client() -> AsyncOpenAI:
    global _openai_client
    if not settings.openai_api_key.strip():
        raise RuntimeError("OPENAI_API_KEY is not set")
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _ollama_client() -> AsyncOpenAI:
    global _ollama_client
    if not settings.ollama_base_url:
        raise RuntimeError("OLLAMA_BASE_URL is not set")
    if _ollama_client is None:
        # OpenAI-compatible API (Ollama); dummy key satisfies the SDK.
        _ollama_client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )
    return _ollama_client


def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role not in ("system", "user", "assistant", "tool"):
            continue
        content = m.get("content")
        if role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id", ""),
                    "content": content if isinstance(content, str) else json.dumps(content),
                }
            )
            continue
        if not isinstance(content, str):
            continue
        out.append({"role": role, "content": content})
    return out


async def _run_tool_loop(client: AsyncOpenAI, model: str, messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    msgs: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}, *_normalize_messages(messages)]
    transcript: list[dict[str, Any]] = []

    for _ in range(8):
        completion = await client.chat.completions.create(
            model=model,
            messages=msgs,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )

        choice = completion.choices[0].message
        if choice.tool_calls:
            msgs.append(
                {
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in choice.tool_calls
                    ],
                }
            )
            for tc in choice.tool_calls:
                name = tc.function.name
                args = tc.function.arguments or "{}"
                result = await dispatch_tool_call(name, args)
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                transcript.append(
                    {
                        "tool": name,
                        "arguments": args,
                        "result_preview": result if len(result) <= 2000 else result[:2000] + "…",
                    }
                )
            continue

        text = (choice.content or "").strip()
        if not text:
            raise RuntimeError("Leere Modellantwort ohne Tool-Calls")
        return text, transcript

    return "Abbruch: zu viele Tool-Schritte.", transcript


async def run_chat_turn(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """
    Returns (assistant_text, transcript for debug).
    Priority: OpenAI (API key) > Ollama (OLLAMA_BASE_URL) > deterministic demo.
    """
    if settings.openai_api_key:
        return await _run_tool_loop(_openai_client(), settings.openai_model, messages)
    if settings.ollama_base_url:
        return await _run_tool_loop(_ollama_client(), settings.ollama_model, messages)
    return await run_demo_turn(messages)
