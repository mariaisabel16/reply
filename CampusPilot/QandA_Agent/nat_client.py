from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def _fixture_path_for_key(semester_key: str) -> Path:
    safe = semester_key.strip().lower().replace("/", "").replace("..", "")
    return _fixture_dir() / f"semester_{safe}.json"


async def fetch_semester_by_key(semester_key: str) -> dict:
    """
    Loads semester JSON from the NAT API (configured URL template) or,
    if unset / on failure and use_fixture_if_nat_fails, from a local fixture.
    """
    tpl = (settings.nat_semester_url_template or "").strip()
    if tpl:
        url = tpl.format(semester_key=semester_key)
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
            "NAT_SEMESTER_URL_TEMPLATE is not set and no local fixture exists. "
            f"Expected {specific} (fixtures/semester_<key>.json). "
            "Set NAT_SEMESTER_URL_TEMPLATE in .env or add that JSON file."
        )
    raw = specific.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("Fixture root must be a JSON object")
    return data
