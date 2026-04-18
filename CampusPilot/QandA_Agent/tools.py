from __future__ import annotations

import json
from typing import Any

from nat_client import (
    fetch_semester_by_key,
    nat_get_semesters,
    nat_get_semesters_dates,
    nat_get_semesters_examperiods,
    nat_get_semesters_extended,
    nat_get_semesters_list,
    nat_get_semesters_schedule,
)
from tool_context import tum_tool_credentials

OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "nat_get_semesters",
            "description": (
                "TUM NAT: `GET /api/v1/semesters` — Liste aller Semester (kompakte Felder pro Eintrag). "
                "Nutzen für Übersicht, Suche nach `semester_key`, aktuelles Semester (`is_current`)."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nat_get_semesters_list",
            "description": (
                "TUM NAT: `GET /api/v1/semesters/list` — ausführlichere Listenansicht (größere JSON-Antwort als `/semesters`)."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nat_get_semesters_extended",
            "description": (
                "TUM NAT: `GET /api/v1/semesters/extended` — sehr große JSON-Antwort mit erweiterten Semesterdaten. "
                "Nur nutzen, wenn explizit nötig; für ein einzelnes Semester oft `get_semester_by_key` oder "
                "`nat_get_semesters_dates` mit `semester_key` sinnvoller."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nat_get_semesters_schedule",
            "description": (
                "TUM NAT: `GET /api/v1/semesters/schedule` — Kalender-/Schedule-Events (z. B. Vorlesungszeit). "
                "Optional Query `semester_key` (z. B. 2026s), sonst typischerweise Fokus auf aktuelles Semester."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "semester_key": {
                        "type": "string",
                        "description": "Optional: technischer Semester-Key, z. B. 2026s",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nat_get_semesters_examperiods",
            "description": (
                "TUM NAT: `GET /api/v1/semesters/examperiods` — alle Prüfungsphasen inkl. Anmeldefristen "
                "(optional Query `semester_key`; wenn gesetzt, kann die API trotzdem alle Semester liefern — "
                "Antwort ggf. clientseitig nach `semester_key` filtern)."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "semester_key": {
                        "type": "string",
                        "description": "Optional: technischer Semester-Key",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "nat_get_semesters_dates",
            "description": (
                "TUM NAT: `GET /api/v1/semesters/dates` — paginierte Semestertermine (Feiertage, vorlesungsfrei, "
                "Rückmeldung, …). Optional: `semester_key` (z. B. 2026s), `datetype` (z. B. holiday, lecturefree, "
                "reenroll), `offset` für Pagination."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "semester_key": {
                        "type": "string",
                        "description": "Optional: technischer Semester-Key",
                    },
                    "datetype": {
                        "type": "string",
                        "description": "Optional: z. B. holiday, lecturefree, reenroll, course_deadline",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Optional: Pagination-Offset (API-Parameter)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_semester_by_key",
            "description": (
                "TUM NAT: `GET /api/v1/semesters/{semester_key}` — vollständiges Semesterobjekt inkl. "
                "`examperiods`, `dates` (nach Typ gruppiert), Vorlesungszeiten, Nachbarsemester usw."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "semester_key": {
                        "type": "string",
                        "description": "Technischer Semester-Key, z. B. 2026s oder 2025w",
                    },
                },
                "required": ["semester_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tum_stored_idp_login_status",
            "description": (
                "Prüft, ob für diese Sitzung TUM-Weblogin-Daten (LRZ/TUM-Kennung für Shibboleth/IdP) "
                "auf dem Server verfügbar sind — nur Metadaten, kein Passwort. Nutzen, wenn der Nutzer "
                "Funktionen braucht, die einen Login am Campus-Portal erfordern (z. B. Modulanmeldung): "
                "Dann erst dieses Tool, dann klar kommunizieren, was automatisch geht und was noch nicht."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "required": [],
            },
        },
    },
]


def bedrock_tool_config() -> dict[str, Any]:
    """Tool definitions for Amazon Bedrock Converse API (toolSpec + inputSchema.json)."""
    tools: list[dict[str, Any]] = []
    for spec in OPENAI_TOOLS:
        fn = spec.get("function") or {}
        name = fn.get("name")
        if not name:
            continue
        desc = str(fn.get("description", ""))
        params = fn.get("parameters") or {"type": "object", "properties": {}}
        tools.append(
            {
                "toolSpec": {
                    "name": name,
                    "description": desc,
                    "inputSchema": {"json": params},
                }
            }
        )
    return {"tools": tools}


async def dispatch_tool_call(name: str, arguments_json: str) -> str:
    try:
        raw = json.loads(arguments_json or "{}")
    except json.JSONDecodeError as e:
        return json.dumps({"error": "invalid_tool_arguments", "detail": str(e)})
    if not isinstance(raw, dict):
        return json.dumps({"error": "invalid_tool_arguments", "detail": "expected JSON object"})
    args = raw

    if name == "nat_get_semesters":
        data = await nat_get_semesters()
        return json.dumps(data, ensure_ascii=False)

    if name == "nat_get_semesters_list":
        data = await nat_get_semesters_list()
        return json.dumps(data, ensure_ascii=False)

    if name == "nat_get_semesters_extended":
        data = await nat_get_semesters_extended()
        return json.dumps(data, ensure_ascii=False)

    if name == "nat_get_semesters_schedule":
        sk = args.get("semester_key")
        sk_s = str(sk).strip() if sk is not None else ""
        data = await nat_get_semesters_schedule(sk_s or None)
        return json.dumps(data, ensure_ascii=False)

    if name == "nat_get_semesters_examperiods":
        sk = args.get("semester_key")
        sk_s = str(sk).strip() if sk is not None else ""
        data = await nat_get_semesters_examperiods(sk_s or None)
        return json.dumps(data, ensure_ascii=False)

    if name == "nat_get_semesters_dates":
        sk = args.get("semester_key")
        sk_s = str(sk).strip() if sk is not None else ""
        dt = args.get("datetype")
        dt_s = str(dt).strip() if dt is not None else ""
        off_raw = args.get("offset")
        off: int | None
        if off_raw is None or off_raw == "":
            off = None
        else:
            try:
                off = int(off_raw)
            except (TypeError, ValueError):
                return json.dumps({"error": "invalid_offset", "detail": "offset must be integer"})
        data = await nat_get_semesters_dates(
            semester_key=sk_s or None,
            datetype=dt_s or None,
            offset=off,
        )
        return json.dumps(data, ensure_ascii=False)

    if name == "get_semester_by_key":
        key = str(args.get("semester_key", "")).strip()
        if not key:
            return json.dumps({"error": "missing_semester_key"})
        data = await fetch_semester_by_key(key)
        return json.dumps(data, ensure_ascii=False)

    if name == "tum_stored_idp_login_status":
        creds = tum_tool_credentials.get()
        if creds is None:
            return json.dumps(
                {
                    "has_stored_credentials": False,
                    "tum_username": None,
                    "note": (
                        "Keine Login-Daten in dieser Anfrage geladen. Der Nutzer sollte sich im "
                        "CampusPilot-Frontend anmelden."
                    ),
                },
                ensure_ascii=False,
            )
        u = creds.tum_username
        masked = u[:2] + "…" if len(u) > 2 else "…"
        return json.dumps(
            {
                "has_stored_credentials": True,
                "tum_username_masked": masked,
                "note": (
                    "Vollständiger Nutzername und Passwort liegen nur serverintern für diese "
                    "Anfrage vor (verschlüsselt in der Datenbank gespeichert). Direkte Shibboleth-"
                    "Browser-Automation (TUMonline/Modulanmeldung) ist im Agenten noch nicht angebunden; "
                    "weise den Nutzer ggf. auf manuelle Schritte im Portal hin."
                ),
            },
            ensure_ascii=False,
        )

    return json.dumps({"error": "unknown_tool", "name": name})
