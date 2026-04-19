"""Last `tumonline_search_courses` hits per user — for disambiguation via `tumonline_pick_course`."""

from __future__ import annotations

import time
from typing import Any

TTL_SECONDS = 15 * 60
_MAX_ITEMS = 25

_store: dict[int, tuple[list[dict[str, Any]], float]] = {}


def clear(user_id: int) -> None:
    _store.pop(user_id, None)


def store_from_courses(user_id: int, courses: list[dict[str, Any]]) -> None:
    """Normalize last search results (pick_index 1..n). Pass [] to clear."""
    if not courses:
        _store.pop(user_id, None)
        return
    norm: list[dict[str, Any]] = []
    for i, c in enumerate(courses[:_MAX_ITEMS], start=1):
        norm.append(
            {
                "pick_index": i,
                "course_id": str(c.get("course_id") or "").strip(),
                "code": str(c.get("code") or "?").strip(),
                "name": str(c.get("name") or "?").strip(),
                "type": str(c.get("type") or "").strip(),
            }
        )
    _store[user_id] = (norm, time.time())


def _get_rows(user_id: int) -> list[dict[str, Any]] | None:
    row = _store.get(user_id)
    if not row:
        return None
    rows, ts = row
    if time.time() - ts > TTL_SECONDS:
        del _store[user_id]
        return None
    return rows


def pick_course(
    user_id: int,
    *,
    pick_index: int | None,
    course_code: str | None,
    course_id: str | None,
    title_contains: str | None,
) -> dict[str, Any]:
    """
    Resolve one course from the last search. Priority: course_id > pick_index > course_code > title_contains.
    """
    rows = _get_rows(user_id)
    if not rows:
        return {
            "status": "error",
            "message_de": "Keine gespeicherte Suche: zuerst `tumonline_search_courses` mit Modulkürzel oder Titel ausführen.",
        }

    cid_in = str(course_id).strip() if course_id else ""
    if cid_in:
        hits = [r for r in rows if r["course_id"] == cid_in]
        if len(hits) == 1:
            return {"status": "ok", "picked": hits[0], "course_id": hits[0]["course_id"]}
        if len(hits) == 0:
            return {
                "status": "error",
                "message_de": "course_id passt zu keinem Treffer der letzten Suche.",
                "last_search": rows,
            }
        return {"status": "ambiguous", "matches": hits}

    if pick_index is not None:
        try:
            ix = int(pick_index)
        except (TypeError, ValueError):
            return {"status": "error", "message_de": "pick_index muss eine ganze Zahl sein."}
        hit = next((r for r in rows if r["pick_index"] == ix), None)
        if hit is None:
            return {
                "status": "error",
                "message_de": f"pick_index {ix} ungültig (erlaubt 1–{len(rows)}).",
                "last_search": rows,
            }
        return {"status": "ok", "picked": hit, "course_id": hit["course_id"]}

    code_in = str(course_code).strip() if course_code else ""
    if code_in:
        hits = [r for r in rows if r["code"].lower() == code_in.lower()]
        if len(hits) == 1:
            return {"status": "ok", "picked": hits[0], "course_id": hits[0]["course_id"]}
        if not hits:
            return {
                "status": "error",
                "message_de": f"Kein Treffer mit Kürzel/code gleich {code_in!r} in der letzten Suche.",
                "last_search": rows,
            }
        return {"status": "ambiguous", "matches": hits, "message_de": "Mehrere Treffer mit diesem Kürzel — pick_index oder course_id nutzen."}

    title_in = str(title_contains).strip() if title_contains else ""
    if title_in:
        needle = title_in.lower()
        hits = [r for r in rows if needle in r["name"].lower()]
        if len(hits) == 1:
            return {"status": "ok", "picked": hits[0], "course_id": hits[0]["course_id"]}
        if not hits:
            return {
                "status": "error",
                "message_de": "title_contains passt zu keinem Treffernamen der letzten Suche.",
                "last_search": rows,
            }
        return {
            "status": "ambiguous",
            "matches": hits,
            "message_de": "Mehrere Treffer für diesen Titelteil — bitte pick_index oder eindeutigeres title_contains / course_code.",
        }

    return {
        "status": "error",
        "message_de": "Mindestens eines angeben: pick_index, course_code, course_id oder title_contains.",
        "last_search": rows,
    }
