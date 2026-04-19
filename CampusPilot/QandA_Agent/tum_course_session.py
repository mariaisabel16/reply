"""One Playwright + TUMonline session per /chat request (lazy, task-local)."""

from __future__ import annotations

import asyncio
import sys
from contextvars import ContextVar
from pathlib import Path

from tool_context import tum_tool_credentials

_AGENT_DIR = Path(__file__).resolve().parent.parent / "Agent"
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

import course_registration as _cr  # noqa: E402


class _TumPlaywrightSession:
    __slots__ = ("_pw", "_browser", "_client")

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._client: _cr.TUMonlineRESTClient | None = None

    async def ensure_client(self) -> _cr.TUMonlineRESTClient:
        if self._client is not None:
            return self._client
        creds = tum_tool_credentials.get()
        if creds is None:
            raise RuntimeError("Keine TUM-Portal-Zugangsdaten für diese Anfrage gesetzt.")

        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            slow_mo=0,
            args=[
                "--disable-features=AutofillServerCommunication,PasswordManagerEnabled",
                "--disable-save-password-bubble",
            ],
        )
        context = await self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )
        page = await context.new_page()
        await _cr.do_login(page, creds.tum_username, creds.tum_password)
        await page.goto(
            f"{_cr.UI_BASE}/slc.tm.cp/student/courses?$ctx=&$skip=0&objTermId={_cr.CURRENT_TERM_ID}&orgId={_cr.ORG_ID}",
            wait_until="domcontentloaded",
            timeout=_cr.TIMEOUT,
        )
        await page.wait_for_timeout(2000)
        self._client = _cr.TUMonlineRESTClient(page)
        return self._client

    async def aclose(self) -> None:
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw is not None:
            try:
                await self._pw.stop()
            except Exception:
                pass
            self._pw = None
        self._client = None


_session_cv: ContextVar[_TumPlaywrightSession | None] = ContextVar(
    "tum_course_playwright_session", default=None
)
_init_lock = asyncio.Lock()


async def get_tum_registration_client() -> _cr.TUMonlineRESTClient:
    sess = _session_cv.get()
    if sess is None:
        async with _init_lock:
            sess = _session_cv.get()
            if sess is None:
                sess = _TumPlaywrightSession()
                _session_cv.set(sess)
    return await sess.ensure_client()


async def close_tum_registration_session() -> None:
    sess = _session_cv.get()
    if sess is not None:
        await sess.aclose()
        _session_cv.set(None)
