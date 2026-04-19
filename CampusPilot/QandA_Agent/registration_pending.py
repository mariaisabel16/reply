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


def set_pending(user_id: int, course_id: str, procedure_id: str, course_label: str) -> tuple[str, bool]:
    """
    Store or replace the pending registration for this user; return (exact confirmation line, reused).

    If the user already has a non-expired pending gate for the **same** course_id and procedure_id,
    the **same** confirmation phrase is kept (TTL refreshed). Avoids flaky UX when the model calls
    `tumonline_get_registration_info` multiple times without changing the target LV/Verfahren.
    """
    cid = str(course_id).strip()
    pid = str(procedure_id).strip()
    now = time.time()
    existing = _pending.get(user_id)
    if existing is not None:
        if (
            existing.course_id == cid
            and existing.procedure_id == pid
            and now - existing.created <= TTL_SECONDS
        ):
            _pending[user_id] = _PendingRegistration(
                course_id=cid,
                procedure_id=pid,
                confirm_phrase=existing.confirm_phrase,
                course_label=course_label[:200],
                created=now,
            )
            return existing.confirm_phrase, True

    phrase = f"BESTÄTIGE ANMELDUNG {secrets.token_hex(4).upper()}"
    _pending[user_id] = _PendingRegistration(
        course_id=cid,
        procedure_id=pid,
        confirm_phrase=phrase,
        course_label=course_label[:200],
        created=now,
    )
    return phrase, False


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
