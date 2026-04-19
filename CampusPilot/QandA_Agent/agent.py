from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from config import settings
from demo_agent import run_demo_turn
from tools import OPENAI_TOOLS, bedrock_tool_config, dispatch_tool_call


SYSTEM_PROMPT = """Du bist ein Studienorganisations-Assistent für TUM-Studierende.
Du beantwortest Fragen zu Semestern, Fristen, Feiertagen und Prüfungsphasen.
Nutze ausschließlich die bereitgestellten Tool-Ergebnisse (NAT-API-Daten) als Faktenquelle.
NAT-Tools (jeweils GET): `nat_get_semesters`, `nat_get_semesters_list`, `nat_get_semesters_extended`,
`nat_get_semesters_schedule`, `nat_get_semesters_examperiods`, `nat_get_semesters_dates`, `get_semester_by_key`.
Wähle das kleinste passende Tool (z. B. `nat_get_semesters_dates` mit `semester_key` statt immer `extended`).
Wenn der Nutzer keinen Semester-Key nennt, nutze `nat_get_semesters` oder frage nach dem Semester.
Wenn Daten fehlen oder das Tool nicht passt, sage das klar und schlage vor, welche Information konkretisiert werden soll (z. B. Semester-Key wie 2026s).
Für Aufgaben, die einen Login am TUM-Campus-Portal / Shibboleth erfordern (z. B. Modulanmeldung), nutze zuerst
das Tool `tum_stored_idp_login_status`, um zu prüfen, ob serverseitig Login-Daten für diese Sitzung vorliegen — niemals Passwörter ausgeben oder erfinden.

TUMonline-Demo (Modul-/LV-Anmeldung über Chat — **dieselbe** REST-/Playwright-Logik wie im Skript
`CampusPilot/Agent/course_registration.py`, nur über diesen Agenten orchestriert; Ziel-URL = `BASE_URL` dort,
standardmäßig demo.campus.tum.de, **nicht** produktives campus.tum.de):
- Tools: `tumonline_search_courses`, `tumonline_get_registration_info`, `tumonline_register_course`,
  optional `tumonline_list_my_courses`, `tumonline_get_my_schedule`.
- **Verboten in Nutzerantworten** (es sei denn, der Nutzer fragt explizit danach): TUM Service Desk,
  service.tum.de, allgemeine „TUMonline-Produktion antwortet nicht“, „zentrale Störung“ — das passt
  zu diesen Demo-/Lokal-Automation-Tools **nicht** und wirkt wie Halluzination.
- Auswertung `tumonline_search_courses`: Feld `search_outcome` beachten: `hits` = Trefferliste nutzen;
  `zero_hits` = Demo-Katalog hat für diesen Begriff/Semester nichts (**nicht** als „Server offline“
  oder „Campus antwortet nicht“ formulieren — ehrlich „kein Treffer in der Demo“); `api_error` =
  HTTP-/Netzwerk-/Parse-Fehler der **Demo-REST** (Retry, andere Zeit, Titel statt Kürzel sinnvoll);
  `session_error` / `tumonline_outcome: session_error` = Playwright/Login/Timeout **auf dem CampusPilot-Server**
  (lokal für den Nutzer erklären, nicht als TUM-Betriebsausfall).
- Feld `can_register` aus `tumonline_search_courses` ist nur ein **Kurzhinweis** aus der LV-Suche; echte
  Fristen, Plätze und Verfahren-Flags stehen in `tumonline_get_registration_info`. Wenn der Nutzer Details
  will oder sich anmelden möchte, **Schritt (2) trotzdem** ausführen — nicht schon nach der Suche von
  weiteren Schritten abraten, nur weil `can_register: false` war.
- Ablauf Anmeldung: (1) `tumonline_search_courses` mit Kürzel oder Titel → interne `course_id` wählen;
  (2) `tumonline_get_registration_info` mit dieser `course_id` → Tool antwortet mit `registration_gate`
  inkl. `confirmation_exact_line`; (3) dem Nutzer Fristen/Plätze erklären und die Bestätigungszeile **wörtlich**
  mitteilen; (4) **erst** wenn der Nutzer in einer **späteren** Nachricht genau diese Zeile sendet,
  `tumonline_register_course` aufrufen mit derselben Zeile in `user_confirmation_line` (1:1, inkl. Großbuchstaben).
- Ohne exakte Bestätigungszeile darfst du `tumonline_register_course` nicht aufrufen. Bei mehreren Treffern aus
  der Suche kurz nachfragen, welche Lehrveranstaltung gemeint ist, bevor du Schritt (2) ausführst.
- `procedure_id` und `course_id` für `tumonline_register_course` **ausschließlich** aus dem letzten
  `tumonline_get_registration_info` → `registration_gate` kopieren (`procedure_id_for_registration`,
  `course_id_for_registration`). Niemals IDs „korrigieren“ oder aus Prosa erraten; keine Entschuldigung
  für eine zuvor „falsche“ procedure_id erfinden, wenn die Werte nicht aus dem Tool kamen.
- Wenn `tumonline_register_course` mit `status: blocked` antwortet, hat der Server die Anmeldung absichtlich
  verweigert (Sicherheits-Defaults) — kurz erklären, ohne technische Details zu übertreiben.

Antworte auf Deutsch, knapp und korrekt; nenne Daten mit Datum und Titel.

Formatierung (einheitlich für die Chat-Oberfläche):
- Nutze Markdown: **fett** für Fristen, Semester-Keys und wichtige Begriffe; kurze Absätze (Leerzeile zwischen Absätzen).
- Aufzählungen mit `- ` pro Zeile; nummerierte Listen nur bei klarer Reihenfolge.
- Roh-JSON nicht als Kauderwelsch ausgeben — höchstens kompaktes ```json ... ``` wenn wirklich nötig.
- Keine überflüssigen Emojis; keine Meta-Kommentare zur internen API."""

_openai_client: AsyncOpenAI | None = None
_ollama_client: AsyncOpenAI | None = None
_bedrock_runtime: Any | None = None


def backend_mode() -> str:
    if settings.bedrock_model_id:
        return "bedrock"
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


def _bedrock_client() -> Any:
    global _bedrock_runtime
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError("boto3 is required for Bedrock; install with: pip install boto3") from e
    if _bedrock_runtime is None:
        _bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.bedrock_region,
        )
    return _bedrock_runtime


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


def _chat_messages_to_bedrock(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map normalized user/assistant string messages to Bedrock Converse content blocks."""
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content")
        if not isinstance(content, str):
            continue
        out.append({"role": role, "content": [{"text": content}]})
    return out


def _bedrock_message_text(message: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in message.get("content") or []:
        if isinstance(block, dict) and "text" in block:
            t = block.get("text")
            if isinstance(t, str) and t:
                parts.append(t)
    return "\n".join(parts).strip()


def _bedrock_tool_result_json_value(parsed: Any) -> dict[str, Any]:
    """
    Bedrock Converse requires each toolResult.content[].json to be a JSON object.
    NAT tools often return a top-level array; wrap non-dicts as {"result": ...}.
    """
    if isinstance(parsed, dict):
        return parsed
    return {"result": parsed}


async def _run_bedrock_tool_loop(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    brt = _bedrock_client()
    conversation = _chat_messages_to_bedrock(_normalize_messages(messages))
    system_prompt = [{"text": SYSTEM_PROMPT}]
    tool_config = bedrock_tool_config()
    transcript: list[dict[str, Any]] = []

    for _ in range(8):

        def _converse() -> dict[str, Any]:
            return brt.converse(
                modelId=settings.bedrock_model_id,
                messages=conversation,
                system=system_prompt,
                toolConfig=tool_config,
                inferenceConfig={"maxTokens": 2048, "temperature": 0.2},
            )

        response = await asyncio.to_thread(_converse)
        stop = response.get("stopReason")
        msg = response["output"]["message"]
        conversation.append(msg)

        if stop == "tool_use":
            tool_results: list[dict[str, Any]] = []
            for block in msg.get("content") or []:
                if not isinstance(block, dict) or "toolUse" not in block:
                    continue
                tu = block["toolUse"]
                name = tu.get("name", "")
                args = tu.get("input") if isinstance(tu.get("input"), dict) else {}
                args_json = json.dumps(args, ensure_ascii=False)
                result = await dispatch_tool_call(str(name), args_json)
                try:
                    result_obj: Any = json.loads(result)
                except json.JSONDecodeError:
                    result_obj = {"text": result}
                bedrock_json = _bedrock_tool_result_json_value(result_obj)
                transcript.append(
                    {
                        "tool": name,
                        "arguments": args_json,
                        "result_preview": result if len(result) <= 2000 else result[:2000] + "…",
                    }
                )
                tool_results.append(
                    {
                        "toolResult": {
                            "toolUseId": tu["toolUseId"],
                            "status": "success",
                            "content": [{"json": bedrock_json}],
                        }
                    }
                )
            if not tool_results:
                raise RuntimeError("tool_use ohne ausführbare toolUse-Blöcke")
            conversation.append({"role": "user", "content": tool_results})
            continue

        text = _bedrock_message_text(msg)
        if text:
            return text, transcript
        if stop in ("end_turn", "max_tokens"):
            raise RuntimeError("Leere Modellantwort ohne Tool-Use")
        raise RuntimeError(f"Unerwarteter Bedrock-Stop: {stop!r}")

    return "Abbruch: zu viele Tool-Schritte.", transcript


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
    Priority: Amazon Bedrock (BEDROCK_MODEL_ID, boto3 converse) > OpenAI > Ollama > deterministic demo.
    """
    if settings.bedrock_model_id:
        print("using bedrock")
        return await _run_bedrock_tool_loop(messages)
    if settings.openai_api_key:
        print("using openai")
        return await _run_tool_loop(_openai_client(), settings.openai_model, messages)
    if settings.ollama_base_url:
        print("using ollama")
        return await _run_tool_loop(_ollama_client(), settings.ollama_model, messages)
    return await run_demo_turn(messages)
