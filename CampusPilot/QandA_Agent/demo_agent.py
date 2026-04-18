from __future__ import annotations

import json
import re
from typing import Any

from nat_client import fetch_semester_by_key


_SEMESTER_KEY_RE = re.compile(r"\b(20\d{2}[sw])\b", re.IGNORECASE)


def infer_semester_key(user_text: str) -> str:
    m = _SEMESTER_KEY_RE.search(user_text or "")
    if m:
        return m.group(1).lower()
    return "2026s"


def _fmt_date_range(start: object, end: object) -> str:
    a = (str(start)[:10] if start else "") or "?"
    b = (str(end)[:10] if end else "") or "?"
    if a == b and len(a) == 10:
        return a
    return f"{a} – {b}"


def format_semester_answer_demo(user_question: str, data: dict[str, Any]) -> str:
    """Deterministic German answer from NAT-like semester JSON (no LLM)."""
    tag = str(data.get("semester_tag") or data.get("semester_key") or "")
    title = str(data.get("semester_title") or tag)
    lines: list[str] = [
        "**Demo-Modus** (ohne OpenAI-API-Key): Antwort aus den Semester-Rohdaten (NAT-API oder lokales Fixture).\n",
        f"**{title}** (`{data.get('semester_key', '')}`)\n",
    ]

    lp0 = data.get("lecture_period_start")
    lp1 = data.get("lecture_period_end")
    if lp0 and lp1:
        lines.append(f"- **Vorlesungszeit:** {_fmt_date_range(lp0, lp1)}")

    exams = data.get("examperiods")
    if isinstance(exams, dict):
        for label, ep in exams.items():
            if not isinstance(ep, dict):
                continue
            t = ep.get("examperiod_title") or label
            lines.append(
                f"- **Prüfungsphase:** {t}: {_fmt_date_range(ep.get('examperiod_start'), ep.get('examperiod_end'))} "
                f"(Anmeldung: {_fmt_date_range(ep.get('examperiod_registration_start'), ep.get('examperiod_registration_end'))})"
            )

    dates = data.get("dates")
    holidays: list[dict[str, Any]] = []
    if isinstance(dates, dict):
        raw_h = dates.get("holiday")
        if isinstance(raw_h, list):
            holidays = [h for h in raw_h if isinstance(h, dict)]

    if holidays:
        lines.append("\n**Gesetzliche Feiertage / arbeitsfreie Tage (holiday):**")
        for h in holidays:
            lines.append(
                f"- **{h.get('semesterdate_title', '?')}** "
                f"({_fmt_date_range(h.get('semesterdate_start'), h.get('semesterdate_end'))})"
            )
    elif re.search(r"urlaub|feiertag|ferien|frei", user_question, re.I):
        lines.append("\n*(Zu dieser Frage: Im Datensatz sind unter `dates.holiday` keine Einträge oder das Feld fehlt.)*")

    q = (user_question or "").strip()
    if q:
        lines.append(f"\n_Deine Frage (Auszug):_ „{q[:200]}{'…' if len(q) > 200 else ''}”")

    return "\n".join(lines)


async def run_demo_turn(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    user_parts = [str(m.get("content", "")) for m in messages if m.get("role") == "user"]
    user_q = user_parts[-1] if user_parts else ""
    key = infer_semester_key(user_q)
    data = await fetch_semester_by_key(key)
    reply = format_semester_answer_demo(user_q, data)
    preview = json.dumps(data, ensure_ascii=False)
    if len(preview) > 1800:
        preview = preview[:1800] + "…"
    transcript: list[dict[str, Any]] = [
        {
            "tool": "get_semester_by_key (demo, ohne LLM)",
            "arguments": json.dumps({"semester_key": key}, ensure_ascii=False),
            "result_preview": preview,
        }
    ]
    return reply, transcript
