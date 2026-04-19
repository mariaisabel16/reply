"""
Zugriff auf TUMonline-Crawl-Daten aus dem Agent-Ordner.

Der Crawl läuft im QandA_Agent und speichert in ``CampusPilot/QandA_Agent/data/campus_pilot_auth.db``.
Dieses Modul hängt ``QandA_Agent`` an ``sys.path`` und re-exportiert die gleichen Lesefunktionen.

Wenn ``CampusPilot`` auf ``sys.path`` liegt (wie in ``workflow.py``), z.B.::

    from Agent.crawl_data_access import crawl_payload_for_username

    data = crawl_payload_for_username("ab12cde")
    if data:
        curriculum = data.get("curriculum_data") or {}

Startest du ein Skript direkt im Ordner ``Agent/``, geht auch::

    from crawl_data_access import crawl_payload_for_username
"""

from __future__ import annotations

import os
import sys

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_CAMPUSPILOT = os.path.dirname(_AGENT_DIR)
_QANDA_AGENT = os.path.join(_CAMPUSPILOT, "QandA_Agent")

if _QANDA_AGENT not in sys.path:
    sys.path.insert(0, _QANDA_AGENT)

from campus_crawl import get_crawl_status_for_user, get_stored_crawl_payload  # noqa: E402
from campuspilot_auth import get_user_id_by_tum_username_sync  # noqa: E402


def crawl_payload_for_user_id(user_id: int):
    """Letztes erfolgreiches Crawl-JSON oder ``None``."""
    return get_stored_crawl_payload(user_id)


def crawl_payload_for_username(tum_username: str):
    """Wie ``crawl_payload_for_user_id``, Auflösung über gespeicherte TUM-Kennung."""
    uid = get_user_id_by_tum_username_sync(tum_username)
    if uid is None:
        return None
    return get_stored_crawl_payload(uid)


def crawl_status_for_user_id(user_id: int):
    """Wie ``GET /auth/crawl-status`` (dict mit status, message, scraped_at, data)."""
    return get_crawl_status_for_user(user_id)


__all__ = [
    "crawl_payload_for_user_id",
    "crawl_payload_for_username",
    "crawl_status_for_user_id",
    "get_crawl_status_for_user",
    "get_stored_crawl_payload",
    "get_user_id_by_tum_username_sync",
]
