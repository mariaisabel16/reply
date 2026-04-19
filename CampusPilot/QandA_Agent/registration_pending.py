"""In-memory registration confirmation gate (per user, single-flight)."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

TTL_SECONDS = 15 * 60

_pending: dict[int, _PendingRegistration] = {}


@dataclass(frozen=True)
class _PendingRegistration:
    course_id: str
    procedure_id: str
    confirm_phrase: str
    course_label: str
    created: float


def set_pending(user_id: int, course_id: str, procedure_id: str, course_label: str) -> str:
    """Store or replace the pending registration for this user; return the exact confirmation line."""
    phrase = f"BESTÄTIGE ANMELDUNG {secrets.token_hex(4).upper()}"
    _pending[user_id] = _PendingRegistration(
        course_id=str(course_id),
        procedure_id=str(procedure_id),
        confirm_phrase=phrase,
        course_label=course_label[:200],
        created=time.time(),
    )
    return phrase


def verify_and_consume(user_id: int, course_id: str, procedure_id: str, user_line: str) -> tuple[bool, str | None]:
    """
    If the line matches the pending gate for this user and ids, clear pending and return (True, None).
    Otherwise return (False, error_de).
    """
    p = _pending.get(user_id)
    if p is None:
        return False, (
            "Kein aktiver Anmelde-Schritt: Bitte zuerst `tumonline_get_registration_info` für diese "
            "Lehrveranstaltung ausführen und dem Nutzer die Bestätigungszeile mitteilen."
        )
    if time.time() - p.created > TTL_SECONDS:
        del _pending[user_id]
        return False, "Die Bestätigung ist abgelaufen. Bitte `tumonline_get_registration_info` erneut ausführen."
    if p.course_id != str(course_id).strip() or p.procedure_id != str(procedure_id).strip():
        return False, (
            "course_id/procedure_id stimmen nicht mit dem letzten `tumonline_get_registration_info` überein. "
            "Bitte erneut die Infos laden oder die korrekten IDs verwenden."
        )
    if p.confirm_phrase.strip() != (user_line or "").strip():
        return False, (
            "Die Bestätigungszeile ist falsch oder fehlt. Sie muss **exakt** (inkl. Großbuchstaben) "
            "mit der vom Server vorgegebenen Zeile übereinstimmen."
        )
    del _pending[user_id]
    return True, None
