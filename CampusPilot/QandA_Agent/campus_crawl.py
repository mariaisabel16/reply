"""
Post-login TUMonline crawl: runs Playwright scraper with the same credentials as auth.

Crawl snapshots are stored in SQLite table `crawl_snapshots` (same DB as users/sessions) so data
survives process restarts. In-memory state covers pending/running for the current worker only.

Disable background crawl with CAMPUSPILOT_POST_LOGIN_CRAWL=0.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import sqlite3
import sys
import time

# Playwright starts a subprocess; Windows SelectorEventLoop → NotImplementedError in subprocess_exec.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

_log = logging.getLogger(__name__)
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

_DATA_DIR = Path(__file__).resolve().parent / "data"
_AUTH_DB = _DATA_DIR / "campuspilot_auth.db"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_state: dict[int, dict[str, Any]] = {}


def post_login_crawl_enabled() -> bool:
    raw = os.environ.get("CAMPUSPILOT_POST_LOGIN_CRAWL", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True


def session_file_for_user(user_id: int) -> str:
    return str(_DATA_DIR / f"tum_session_{user_id}.json")


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_AUTH_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_crawl_snapshots_table(conn: sqlite3.Connection) -> None:
    """Safe if campuspilot_auth schema init has not run yet (e.g. tests)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS crawl_snapshots (
            user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            message TEXT,
            payload_json TEXT,
            scraped_at TEXT,
            updated_at REAL NOT NULL
        );
        """
    )


def _save_snapshot_to_db(
    user_id: int,
    status: Literal["ok", "error"],
    message: str | None,
    data: dict[str, Any] | None,
    scraped_at: str | None,
) -> None:
    now = time.time()
    payload = json.dumps(data, ensure_ascii=False) if data is not None else None
    conn = _db_connect()
    try:
        _ensure_crawl_snapshots_table(conn)
        conn.execute(
            """
            INSERT INTO crawl_snapshots (user_id, status, message, payload_json, scraped_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                status = excluded.status,
                message = excluded.message,
                payload_json = excluded.payload_json,
                scraped_at = excluded.scraped_at,
                updated_at = excluded.updated_at
            """,
            (user_id, status, message, payload, scraped_at, now),
        )
        conn.commit()
    finally:
        conn.close()


def _load_snapshot_from_db(user_id: int) -> dict[str, Any] | None:
    conn = _db_connect()
    try:
        _ensure_crawl_snapshots_table(conn)
        row = conn.execute(
            "SELECT status, message, payload_json, scraped_at, updated_at FROM crawl_snapshots WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    st = str(row["status"] or "")
    if st not in ("ok", "error"):
        return None
    payload: dict[str, Any] | None = None
    raw_payload = row["payload_json"]
    if raw_payload:
        try:
            p = json.loads(str(raw_payload))
            payload = p if isinstance(p, dict) else {"value": p}
        except json.JSONDecodeError:
            payload = None
    return {
        "status": st,
        "message": row["message"],
        "data": payload,
        "scraped_at": row["scraped_at"],
    }


def set_pending(user_id: int) -> None:
    _state[user_id] = {
        "status": "pending",
        "message": None,
        "data": None,
        "scraped_at": None,
    }


def clear_user(user_id: int) -> None:
    _state.pop(user_id, None)
    p = Path(session_file_for_user(user_id))
    try:
        if p.is_file():
            p.unlink()
    except OSError:
        pass


def get_status_dict(user_id: int) -> dict[str, Any]:
    """Prefer in-memory pending/running/recent; otherwise last snapshot from SQLite."""
    if user_id in _state:
        return _state[user_id]
    db = _load_snapshot_from_db(user_id)
    if db:
        return {
            "status": db["status"],
            "message": db["message"],
            "data": db["data"],
            "scraped_at": db["scraped_at"],
        }
    return {"status": "idle", "message": None, "data": None, "scraped_at": None}


def get_crawl_status_for_user(user_id: int) -> dict[str, Any]:
    """Normalized payload for `CrawlStatusResponse`."""
    d = get_status_dict(user_id)
    st = d.get("status", "idle")
    if st not in ("idle", "pending", "running", "ok", "error"):
        st = "idle"
    return {
        "status": st,
        "message": d.get("message"),
        "scraped_at": d.get("scraped_at"),
        "data": d.get("data"),
    }


def get_stored_crawl_payload(user_id: int) -> dict[str, Any] | None:
    """
    Last successful crawl JSON for this user (same object as in `CrawlStatusResponse.data`).

    Returns None if there is no snapshot, crawl failed, or data is missing. Prefer this over
    reading SQLite directly so you stay compatible with in-memory `running` / DB layout.

    Typical keys: curriculum_data, student_card_data, scraped_at, home_url, etc.
    """
    d = get_status_dict(user_id)
    if d.get("status") != "ok":
        return None
    raw = d.get("data")
    return raw if isinstance(raw, dict) else None


def _compact_crawl_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Reduce size for JSON responses (tables / previews can be huge)."""
    d = copy.deepcopy(raw)
    cd = d.get("curriculum_data")
    if isinstance(cd, dict):
        tp = cd.get("text_preview")
        if isinstance(tp, str) and len(tp) > 4000:
            cd["text_preview"] = tp[:4000] + "\n… (gekürzt)"
        tables = cd.get("tables")
        if isinstance(tables, list) and len(tables) > 40:
            cd["tables"] = tables[:40]
            cd["tables_truncated"] = True
    return d


class CrawlStatusResponse(BaseModel):
    status: Literal["idle", "pending", "running", "ok", "error"]
    message: str | None = None
    scraped_at: str | None = None
    data: dict[str, Any] | None = Field(
        default=None,
        description="Sanitized scrape payload when status is ok",
    )


def _playwright_worker_entry(user_id: int, username: str, password: str) -> None:
    """
    Run async Playwright in a fresh event loop inside a thread pool worker.

    Uvicorn on Windows may keep a Selector-based loop that cannot spawn subprocesses;
    asyncio.run() here gets a new Proactor loop (policy set below).
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(_run_post_login_crawl_async_impl(user_id, username, password))


async def _run_post_login_crawl_async_impl(user_id: int, username: str, password: str) -> None:
    webcrawler_dir = Path(__file__).resolve().parent.parent / "Webcrawler"
    webcrawler_str = str(webcrawler_dir)
    if webcrawler_str not in sys.path:
        sys.path.insert(0, webcrawler_str)

    try:
        import session_manager as sm  # type: ignore[import-untyped]
    except ImportError as e:
        _state[user_id] = {
            "status": "error",
            "message": f"Crawler-Abhängigkeiten fehlen: {e}",
            "data": None,
            "scraped_at": None,
        }
        _save_snapshot_to_db(user_id, "error", _state[user_id]["message"], None, None)
        return

    session_file = session_file_for_user(user_id)
    try:
        result = await sm.scrape_tumonline(
            username=username,
            password=password,
            headless=True,
            session_file=session_file,
            save_debug_screenshots=False,
        )
        compact = _compact_crawl_payload(result)
        scraped_at = compact.get("scraped_at")
        if isinstance(scraped_at, str):
            scraped_s = scraped_at
        else:
            scraped_s = None
        _state[user_id] = {
            "status": "ok",
            "message": None,
            "data": compact,
            "scraped_at": scraped_s,
        }
        _save_snapshot_to_db(user_id, "ok", None, compact, scraped_s)
    except Exception as e:
        msg = str(e)
        _state[user_id] = {
            "status": "error",
            "message": msg,
            "data": None,
            "scraped_at": None,
        }
        _save_snapshot_to_db(user_id, "error", msg, None, None)


async def run_post_login_crawl(user_id: int, username: str, password: str) -> None:
    _state[user_id] = {
        "status": "running",
        "message": None,
        "data": None,
        "scraped_at": None,
    }
    try:
        await asyncio.to_thread(_playwright_worker_entry, user_id, username, password)
    except Exception as e:
        msg = str(e)
        _state[user_id] = {
            "status": "error",
            "message": msg,
            "data": None,
            "scraped_at": None,
        }
        _save_snapshot_to_db(user_id, "error", msg, None, None)


def schedule_post_login_crawl(user_id: int, username: str, password: str) -> None:
    """Schedule crawl in the current loop; log task failures (avoids 'Task exception was never retrieved')."""

    async def _runner() -> None:
        try:
            await run_post_login_crawl(user_id, username, password)
        except Exception:
            _log.exception("post-login crawl failed for user_id=%s", user_id)

    task = asyncio.create_task(_runner())

    def _done(t: asyncio.Task) -> None:
        try:
            t.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            _log.exception("post-login crawl task ended with error (user_id=%s)", user_id)

    task.add_done_callback(_done)
