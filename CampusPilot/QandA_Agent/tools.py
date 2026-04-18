from __future__ import annotations

import json
from typing import Any

from nat_client import fetch_semester_by_key

OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_semester_by_key",
            "description": (
                "Ruft organisatorische Semesterinformationen von der TUM-NAT-Studien-API ab: "
                "Vorlesungszeit, Semesterzeitraum, Prüfungsphasen inkl. Anmeldefristen, "
                "Fristen (z. B. Rückmeldung) und Feiertage/Urlaubstage im `dates`-Objekt "
                "(z. B. datetype `holiday`). "
                "Der Parameter `semester_key` ist der technische Schlüssel, z. B. `2026s` "
                "für das Sommersemester 2026 oder `2025w` für das Wintersemester."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "semester_key": {
                        "type": "string",
                        "description": "Technischer Semester-Key, z. B. 2026s oder 2025w",
                    }
                },
                "required": ["semester_key"],
            },
        },
    }
]


async def dispatch_tool_call(name: str, arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError as e:
        return json.dumps({"error": "invalid_tool_arguments", "detail": str(e)})

    if name == "get_semester_by_key":
        key = str(args.get("semester_key", "")).strip()
        if not key:
            return json.dumps({"error": "missing_semester_key"})
        data = await fetch_semester_by_key(key)
        return json.dumps(data, ensure_ascii=False)

    return json.dumps({"error": "unknown_tool", "name": name})
