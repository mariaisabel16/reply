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
import registration_pending

from config import settings
from tool_context import current_auth_user_id, tum_tool_credentials
from tum_course_session import get_tum_registration_client

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
            "name": "tumonline_search_courses",
            "description": (
                "TUMonline (Demo-Campus): Kurse/Lehrveranstaltungen suchen nach Kürzel (z. B. IN2061) oder "
                "Titel. Liefert interne `course_id` (lange Zahl) und `can_register` (Kurzfassung aus der LV-Detail-API). "
                "`can_register: false` heißt **nicht** automatisch, dass keine Verfahren/Fristen existieren — "
                "zuverlässige Anmeldedaten liefert `tumonline_get_registration_info`."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Suchbegriff: Modul-/LV-Kürzel oder Stichworte aus dem Titel",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tumonline_get_registration_info",
            "description": (
                "TUMonline (Demo-Campus): Zu einer internen `course_id` die Anmelde**verfahren** laden "
                "(Fristen, Plätze, procedure_id, oft `can_register` pro Verfahren). **Auch aufrufen**, wenn "
                "`tumonline_search_courses` bei der LV `can_register: false` zeigte — dort fehlen Fristen/Plätze. "
                "Legt serverseitig eine **Bestätigungszeile** an: dem Nutzer zeigen; erst nach exakter "
                "Nutzer-Zeile darf `tumonline_register_course` folgen."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "Interne Kurs-ID (lange Zahl) aus `tumonline_search_courses`",
                    },
                },
                "required": ["course_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tumonline_register_course",
            "description": (
                "TUMonline (Demo-Campus): Anmeldung ausführen (Playwright). **Nur** aufrufen, wenn der "
                "Nutzer die in `tumonline_get_registration_info` erzeugte Bestätigungszeile exakt so "
                "geschrieben hat; denselben Text 1:1 in `user_confirmation_line` übergeben."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "course_id": {"type": "string", "description": "Interne Kurs-ID"},
                    "procedure_id": {"type": "string", "description": "procedure_id aus registration_gate"},
                    "user_confirmation_line": {
                        "type": "string",
                        "description": "Exakt die vom Nutzer gesendete Bestätigungszeile (vom Server vorgegeben)",
                    },
                },
                "required": ["course_id", "procedure_id", "user_confirmation_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tumonline_list_my_courses",
            "description": (
                "TUMonline (Demo-Campus): Listet die aktuell für das laufende Semester eingetragenen "
                "Lehrveranstaltungen des Nutzers."
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
            "name": "tumonline_get_my_schedule",
            "description": "TUMonline (Demo-Campus): Stundenplan / Terminzeilen aus der Oberfläche lesen.",
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
            "name": "tum_stored_idp_login_status",
            "description": (
                "Prüft, ob für diese Sitzung TUM-Weblogin-Daten (LRZ/TUM-Kennung für Shibboleth/IdP) "
                "auf dem Server verfügbar sind — nur Metadaten, kein Passwort. Nutzen, wenn der Nutzer "
                "Funktionen braucht, die einen Login am Campus-Portal erfordern (z. B. Modulanmeldung): "
                "Dann erst dieses Tool, dann klar kommunizieren, was automatisch geht."
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


def _pick_primary_procedure(procedures: list[Any]) -> dict[str, Any] | None:
    chosen: dict[str, Any] | None = None
    for p in procedures:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("procedure_id") or "").strip()
        if not pid or pid == "?":
            continue
        if p.get("can_register", True):
            return p
        if chosen is None:
            chosen = p
    return chosen


def _tum_demo_session_error_json(
    exc: BaseException, *, context: str, extra: dict[str, Any] | None = None
) -> str:
    """Structured error so the LLM does not confuse local Playwright with production TUMonline outages."""
    msg = str(exc).strip()
    if len(msg) > 900:
        msg = msg[:900] + "…"
    body: dict[str, Any] = {
        "status": "error",
        "tumonline_scope": "Nur die Demo-Instanz demo.campus.tum.de (BASE_URL in Agent/course_registration.py).",
        "tumonline_outcome": "session_error",
        "context": context,
        "message": msg,
        "user_visible_guidance_de": (
            "Technischer Fehler in der **lokalen** Browser-Automation (Playwright/Login/Timeout) für die "
            "**Demo** — kein Beleg für einen Ausfall des **produktiven** TUMonline."
        ),
        "model_must_not_de": (
            "Keinen TUM Service Desk, keine service.tum.de-Links, keine Formulierungen wie "
            "„TUMonline-System antwortet nicht“ oder „zentrale Störung“ — das trifft hier typischerweise nicht zu."
        ),
    }
    if extra:
        body.update(extra)
    return json.dumps(body, ensure_ascii=False)


async def _tumonline_get_registration_info_with_gate(course_id: str) -> dict[str, Any]:
    client = await get_tum_registration_client()
    info = await client.get_course_registration_info(course_id)
    if info.get("status") != "ok":
        return info
    procedures = info.get("procedures")
    if not isinstance(procedures, list) or not procedures:
        info["registration_gate"] = {
            "de": "Keine Anmeldeverfahren in der Antwort — bitte prüfen, ob die course_id stimmt.",
        }
        return info
    picked = _pick_primary_procedure(procedures)
    if picked is None:
        info["registration_gate"] = {
            "de": "Keine gültige procedure_id gefunden.",
        }
        return info
    uid = current_auth_user_id.get()
    if uid is None:
        info["registration_gate"] = {"de": "Intern: keine Nutzer-ID für Bestätigungsgate."}
        return info
    label = str(info.get("course_name") or picked.get("name") or course_id)
    phrase = registration_pending.set_pending(uid, str(course_id), str(picked["procedure_id"]), label)
    info["registration_gate"] = {
        "procedure_id_for_registration": picked.get("procedure_id"),
        "confirmation_exact_line": phrase,
        "instructions_for_model_de": (
            "Zeige dem Nutzer die wichtigsten Fakten (Name, Fristen, Plätze). "
            "Die Anmeldung erfolgt erst nach ausdrücklicher Zustimmung: Bitte den Nutzer, die folgende "
            "Zeile **exakt** (ohne Anführungszeichen) als eigene Chat-Nachricht zu senden. "
            "Rufe `tumonline_register_course` erst auf, wenn der Nutzer genau diese Zeile geschrieben hat — "
            "und setze `user_confirmation_line` identisch zu dieser Zeile."
        ),
    }
    return info


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
                    "Zugangsdaten sind für diese Server-Anfrage verfügbar. TUMonline-Demo-Tools "
                    "(`tumonline_*`) können damit eine Browser-Sitzung starten (Playwright, headless)."
                ),
            },
            ensure_ascii=False,
        )

    if name == "tumonline_search_courses":
        q = str(args.get("query", "")).strip()
        if not q:
            return json.dumps({"error": "missing_query"})
        try:
            client = await get_tum_registration_client()
            data = await client.search_courses(q)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return _tum_demo_session_error_json(
                e, context="tumonline_search_courses", extra={"search_outcome": "session_error"}
            )

    if name == "tumonline_get_registration_info":
        cid = str(args.get("course_id", "")).strip()
        if not cid:
            return json.dumps({"error": "missing_course_id"})
        try:
            data = await _tumonline_get_registration_info_with_gate(cid)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return _tum_demo_session_error_json(e, context="tumonline_get_registration_info")

    if name == "tumonline_register_course":
        import course_registration as _tum_cr

        cid = str(args.get("course_id", "")).strip()
        pid = str(args.get("procedure_id", "")).strip()
        line = str(args.get("user_confirmation_line", "")).strip()
        if not cid or not pid or not line:
            return json.dumps({"error": "missing_course_id_procedure_id_or_confirmation"})
        base = (_tum_cr.BASE_URL or "").lower()
        if "demo.campus.tum.de" not in base and not settings.tum_registration_allow_non_demo_host:
            return json.dumps(
                {
                    "status": "blocked",
                    "message": (
                        "Anmeldung blockiert: Die TUMonline-Basis-URL in `Agent/course_registration.py` ist nicht "
                        "die Demo-Instanz (demo.campus.tum.de). Schreibende Anmeldung ist damit verboten, bis "
                        "`CAMPUSPILOT_TUM_REGISTRATION_ALLOW_NON_DEMO_HOST=true` gesetzt ist — nur tun, wenn du "
                        "bewusst gegen diese Instanz anmelden willst."
                    ),
                },
                ensure_ascii=False,
            )
        if not settings.tum_registration_executes_writes:
            return json.dumps(
                {
                    "status": "blocked",
                    "message": (
                        "Schreibende Modulanmeldung ist serverseitig aus (Standard). Es wird kein Belegwunsch "
                        "abgeschickt. Zum gezielten Testen: in `.env` "
                        "`CAMPUSPILOT_TUM_REGISTRATION_EXECUTES_WRITES=true` setzen — bei Demo-URL nur Demo-Anmeldung."
                    ),
                },
                ensure_ascii=False,
            )
        uid = current_auth_user_id.get()
        if uid is None:
            return json.dumps({"status": "error", "message": "Intern: keine Nutzer-ID."})
        ok, err = registration_pending.verify_and_consume(uid, cid, pid, line)
        if not ok:
            return json.dumps({"status": "error", "message": err}, ensure_ascii=False)
        try:
            client = await get_tum_registration_client()
            data = await client.register_for_course(cid, pid)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return _tum_demo_session_error_json(e, context="tumonline_register_course")

    if name == "tumonline_list_my_courses":
        try:
            client = await get_tum_registration_client()
            data = await client.get_my_courses()
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return _tum_demo_session_error_json(e, context="tumonline_list_my_courses")

    if name == "tumonline_get_my_schedule":
        try:
            client = await get_tum_registration_client()
            data = await client.get_my_schedule()
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            return _tum_demo_session_error_json(e, context="tumonline_get_my_schedule")

    return json.dumps({"error": "unknown_tool", "name": name})
