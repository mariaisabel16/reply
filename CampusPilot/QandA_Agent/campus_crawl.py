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


def _truncate_str(s: str, max_len: int) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _compact_label_table(d: Any, *, max_pairs: int, max_val_len: int) -> dict[str, str]:
    if not isinstance(d, dict):
        return {}
    out: dict[str, str] = {}
    for i, (k, v) in enumerate(d.items()):
        if i >= max_pairs:
            break
        if not isinstance(k, str) or not k.strip():
            continue
        if v is None:
            continue
        vs = str(v).strip()
        if not vs:
            continue
        out[_truncate_str(k, 120)] = _truncate_str(vs, max_val_len)
    return out


def compact_study_profile_for_prompt(user_id: int) -> str | None:
    """
    Kurzprofil aus dem letzten erfolgreichen TUMonline-Crawl (SQLite), für den LLM-Systemprompt.

    Keine Passwörter, keine Modullisten — nur Stammdaten/Studienkontext. Gibt None zurück,
    wenn noch kein Crawl oder Fehlerstatus.
    """
    raw = get_stored_crawl_payload(user_id)
    if not raw:
        return None
    sc = raw.get("student_card_data")
    cd = raw.get("curriculum_data")
    md = raw.get("modules_data")
    profile: dict[str, Any] = {}
    if isinstance(raw.get("scraped_at"), str) and raw["scraped_at"].strip():
        profile["scraped_at"] = raw["scraped_at"].strip()
    if isinstance(raw.get("environment"), str) and raw["environment"].strip():
        profile["tum_environment"] = raw["environment"].strip()

    if isinstance(sc, dict):
        stu: dict[str, Any] = {}
        for key in (
            "matrikelnummer",
            "full_name",
            "vorname",
            "nachname",
            "fachsemester",
            "studien_id",
            "spo_version",
        ):
            val = sc.get(key)
            if val is None or val == "":
                continue
            stu[key] = val
        bi = _compact_label_table(sc.get("basisinformationen"), max_pairs=14, max_val_len=220)
        if bi:
            stu["basisinformationen"] = bi
        wi = _compact_label_table(sc.get("weitere_informationen"), max_pairs=8, max_val_len=220)
        if wi:
            stu["weitere_informationen"] = wi
        if stu:
            profile["student_card"] = stu

    if isinstance(cd, dict):
        cur: dict[str, Any] = {}
        for key in ("name", "matrikelnummer", "average", "semester", "study_status"):
            val = cd.get(key)
            if val is None or val == "":
                continue
            cur[key] = val
        ects = cd.get("ects")
        if isinstance(ects, dict) and ects:
            cur["ects"] = ects
        mods = cd.get("modules")
        if isinstance(mods, list):
            cur["curriculum_positiv_module_tiles_count"] = len(mods)
        if cur:
            profile["curriculum_page"] = cur

    if isinstance(md, dict):
        summ: dict[str, Any] = {}
        for key in ("total", "passed", "in_progress", "total_ects"):
            if key in md and md[key] is not None:
                summ[key] = md[key]
        if summ:
            profile["grades_summary"] = summ

    if not any(k in profile for k in ("student_card", "curriculum_page", "grades_summary")):
        return None
    try:
        blob = json.dumps(profile, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return None
    return (
        "## TUMonline-Studierendenkontext (serverseitig nach Login gecrawlt)\n"
        "Die folgenden Felder stammen aus TUMonline (Demo-Campus), Stand siehe `scraped_at`. "
        "Nur nutzen, wenn sie zur Nutzerfrage passen; nichts erfinden oder extrapolieren.\n\n"
        f"```json\n{blob}\n```"
    )


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
        import tumonline_scraper as ts  # type: ignore[import-untyped]
    except ImportError as e:
        _state[user_id] = {
            "status": "error",
            "message": f"Crawler-Abhängigkeiten fehlen: {e}",
            "data": None,
            "scraped_at": None,
        }
        _save_snapshot_to_db(user_id, "error", _state[user_id]["message"], None, None)
        return

    try:
        result = await ts.scrape_all_async(
            username=username,
            password=password,
            headless=True,
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
