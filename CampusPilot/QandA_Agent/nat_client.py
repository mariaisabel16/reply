from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def _fixture_path_for_key(semester_key: str) -> Path:
    safe = semester_key.strip().lower().replace("/", "").replace("..", "")
    return _fixture_dir() / f"semester_{safe}.json"


def api_v1_semesters_root() -> str:
    """Base path `.../api/v1/semesters` (no trailing slash after semesters)."""
    base = settings.nat_api_base_url.rstrip("/")
    return f"{base}/api/v1/semesters"


def _semester_detail_url(semester_key: str) -> str:
    tpl = (settings.nat_semester_url_template or "").strip()
    if tpl:
        return tpl.format(semester_key=semester_key)
    return f"{api_v1_semesters_root()}/{semester_key}"


def _clean_query(params: dict[str, Any]) -> dict[str, Any] | None:
    out: dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        out[k] = v
    return out or None


async def nat_get_json(suffix: str, *, params: dict[str, Any] | None = None) -> Any:
    """
    GET `{api_v1_semesters_root()}` when suffix is "",
    else GET `{root}/{suffix}`.
    """
    root = api_v1_semesters_root()
    url = root if not suffix else f"{root}/{suffix}"
    q = _clean_query(params) if params else None
    async with httpx.AsyncClient(timeout=settings.nat_http_timeout_s) as client:
        r = await client.get(url, headers={"Accept": "application/json"}, params=q)
        r.raise_for_status()
        return r.json()


async def nat_get_semesters() -> Any:
    """GET /api/v1/semesters"""
    return await nat_get_json("")


async def nat_get_semesters_list() -> Any:
    """GET /api/v1/semesters/list"""
    return await nat_get_json("list")


async def nat_get_semesters_extended() -> Any:
    """GET /api/v1/semesters/extended"""
    return await nat_get_json("extended")


async def nat_get_semesters_schedule(semester_key: str | None = None) -> Any:
    """GET /api/v1/semesters/schedule — optional Query `semester_key`."""
    p: dict[str, Any] = {}
    if semester_key and str(semester_key).strip():
        p["semester_key"] = str(semester_key).strip()
    return await nat_get_json("schedule", params=p or None)


async def nat_get_semesters_examperiods(semester_key: str | None = None) -> Any:
    """GET /api/v1/semesters/examperiods — optional Query `semester_key`."""
    p: dict[str, Any] = {}
    if semester_key and str(semester_key).strip():
        p["semester_key"] = str(semester_key).strip()
    return await nat_get_json("examperiods", params=p or None)


async def nat_get_semesters_dates(
    semester_key: str | None = None,
    datetype: str | None = None,
    offset: int | None = None,
) -> Any:
    """GET /api/v1/semesters/dates — optionale Queries `semester_key`, `datetype`, `offset`."""
    p: dict[str, Any] = {}
    if semester_key and str(semester_key).strip():
        p["semester_key"] = str(semester_key).strip()
    if datetype and str(datetype).strip():
        p["datetype"] = str(datetype).strip()
    if offset is not None:
        p["offset"] = int(offset)
    return await nat_get_json("dates", params=p or None)


async def fetch_semester_by_key(semester_key: str) -> dict:
    """
    GET /api/v1/semesters/{semester_key} (oder NAT_SEMESTER_URL_TEMPLATE).
    Bei Fehler und USE_FIXTURE_IF_NAT_FAILS: fixtures/semester_<key>.json.
    """
    url = _semester_detail_url(semester_key)
    try:
        async with httpx.AsyncClient(timeout=settings.nat_http_timeout_s) as client:
            r = await client.get(url, headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict):
                raise TypeError("NAT response is not a JSON object")
            return data
    except Exception as e:
        logger.warning("NAT semester fetch failed (%s); falling back to fixture if enabled.", e)
        if not settings.use_fixture_if_nat_fails:
            raise

    specific = _fixture_path_for_key(semester_key)
    if not specific.is_file():
        raise FileNotFoundError(
            "Semester-HTTP-Anfrage fehlgeschlagen und kein lokales Fixture gefunden. "
            f"Erwartet {specific} oder erreichbare URL {_semester_detail_url(semester_key)!r}. "
            "Setze NAT_SEMESTER_URL_TEMPLATE / NAT_API_BASE_URL oder lege die Fixture-Datei an."
        )
    raw = specific.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("Fixture root must be a JSON object")
    return data
