"""
Campus Co-Pilot — TUMonline Agent (v3 - demo)
Hackathon Reply Challenge 2025
Environment: demo.campus.tum.de
"""

import asyncio
import json
import getpass
import os
from urllib.parse import quote
from playwright.async_api import async_playwright, Page
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box
import boto3

# ─────────────────────────────────────────────
# CONFIG — demo.campus.tum.de
# CampusPilot/QandA_Agent: schreibende Anmeldung standardmäßig aus — siehe ENV.example
# (CAMPUSPILOT_TUM_REGISTRATION_*). Nur Demo-URL ohne explizites Flag erlaubt.
# ─────────────────────────────────────────────
BASE_URL        = "https://demo.campus.tum.de/DSYSTEM"
REST_BASE       = f"{BASE_URL}/ee/rest"
UI_BASE         = f"{BASE_URL}/ee/ui/ca2/app/desktop/#"
LOGIN_URL       = f"{UI_BASE}/login"
CURRENT_TERM_ID = (os.environ.get("TUMONLINE_TERM_ID") or "206").strip() or "206"  # Demo-Semester; bei Bedarf setzen
ORG_ID          = "1"

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"  # change to your available model
REGION   = "eu-central-1"                             # change if needed
TIMEOUT  = 25_000

console = Console()

# ─────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────
TOOLS = [
    {
        "name": "search_courses",
        "description": (
            "Search for courses in TUMonline by code (e.g. 'IN2061') or name. "
            "Returns the internal courseId (long number), name, type, and whether registration is available. "
            "Always call this FIRST to get the courseId before registering."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Course code e.g. 'IN2061' or name e.g. 'Signalverarbeitung'"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_course_registration_info",
        "description": (
            "Given an internal courseId (e.g. 950878455), retrieves the registration procedures: "
            "dates, available spots, and the procedureId needed to register."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string", "description": "Internal course ID (long number, e.g. 950878455)"},
            },
            "required": ["course_id"],
        },
    },
    {
        "name": "register_for_course",
        "description": (
            "Registers the student for a course. Requires both courseId AND procedureId "
            "(obtain both via search_courses + get_course_registration_info). "
            "ALWAYS ask the user for explicit confirmation before calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "course_id":    {"type": "string", "description": "Internal course ID (e.g. 950878455)"},
                "procedure_id": {"type": "string", "description": "Registration procedure ID (e.g. 73526)"},
            },
            "required": ["course_id", "procedure_id"],
        },
    },
    {
        "name": "unregister_from_course",
        "description": "Unregisters the student from a course. ALWAYS ask for confirmation before calling.",
        "input_schema": {
            "type": "object",
            "properties": {
                "course_id": {"type": "string", "description": "Internal course ID"},
            },
            "required": ["course_id"],
        },
    },
    {
        "name": "get_my_courses",
        "description": "Lists the courses the student is currently enrolled in this semester.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_my_schedule",
        "description": "Returns the student's weekly timetable.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

# ─────────────────────────────────────────────
# REST CLIENT
# Uses the authenticated browser session to call TUMonline REST APIs directly
# ─────────────────────────────────────────────
class TUMonlineRESTClient:
    def __init__(self, page: Page):
        self.page = page

    async def _get(self, path: str, params: dict = None) -> dict | list | None:
        url = f"{REST_BASE}/{path}"
        if params:
            # OData $filter enthält ; und = — ohne Encoding kann der Request fehlschlagen oder leer bleiben.
            parts: list[str] = []
            for key, val in params.items():
                k = quote(str(key), safe="$")
                v = quote(str(val), safe="")
                parts.append(f"{k}={v}")
            url = f"{url}?{'&'.join(parts)}"
        js = f"""
        async () => {{
            try {{
                const r = await fetch({json.dumps(url)}, {{
                    method: "GET",
                    headers: {{"Accept": "application/json, text/plain, */*"}},
                    credentials: "include"
                }});
                if (!r.ok) return {{ __error: r.status, __url: {json.dumps(url)} }};
                const text = await r.text();
                try {{ return JSON.parse(text); }} catch {{ return {{ __raw: text.slice(0, 500) }}; }}
            }} catch(e) {{ return {{ __error: e.toString() }}; }}
        }}
        """
        return await self.page.evaluate(js)

    async def _post(self, path: str, body: dict = None) -> dict | None:
        url = f"{REST_BASE}/{path}"
        js = f"""
        async () => {{
            try {{
                const r = await fetch({json.dumps(url)}, {{
                    method: "POST",
                    headers: {{
                        "Accept": "application/json, text/plain, */*",
                        "Content-Type": "application/json"
                    }},
                    credentials: "include",
                    body: {json.dumps(json.dumps(body or {}))}
                }});
                const text = await r.text();
                try {{ return {{ ok: r.ok, status: r.status, data: JSON.parse(text) }}; }}
                catch {{ return {{ ok: r.ok, status: r.status, data: text.slice(0,500) }}; }}
            }} catch(e) {{ return {{ __error: e.toString() }}; }}
        }}
        """
        return await self.page.evaluate(js)

    # ── SEARCH COURSES ───────────────────────────
    async def search_courses(self, query: str) -> dict:
        # API returns courses inside "links" with rel="detail" and name="CpCourseDto"
        q = (query or "").strip()
        if not q:
            return {"status": "error", "message": "empty_query"}

        async def _collect_from_response(data: dict | list | None) -> list[dict]:
            courses: list[dict] = []
            if not data or not isinstance(data, dict) or "__error" in data:
                return courses
            for link in data.get("links", []):
                if link.get("rel") == "detail" and link.get("name") == "CpCourseDto":
                    course_id = link.get("key", "?")
                    detail = await self._get(f"slc.tm.cp/student/courses/{course_id}")
                    if detail and isinstance(detail, dict) and "__error" not in detail:
                        courses.append({
                            "course_id":    course_id,
                            "code":         detail.get("courseCode", "?"),
                            "name":         detail.get("title", "?"),
                            "type":         detail.get("courseTypeCode", ""),
                            "sws":          str(detail.get("semesterHours", "")),
                            "can_register": detail.get("registrationPossible", True),
                        })
            return courses

        # Zuerst typische LV (LVEAB); bei 0 Treffern breiter suchen (z. B. andere courseNormKey).
        filter_variants = [
            f"courseNormKey-eq=LVEAB;filterTerm-like={q};orgId-eq={ORG_ID};termId-eq={CURRENT_TERM_ID}",
            f"filterTerm-like={q};orgId-eq={ORG_ID};termId-eq={CURRENT_TERM_ID}",
        ]
        last_error: dict | list | None = None
        for filter_str in filter_variants:
            data = await self._get("slc.tm.cp/student/courses", {
                "$filter":  filter_str,
                "$orderBy": "title=ascnf",
                "$skip":    "0",
                "$top":     "20",
            })
            if not data or (isinstance(data, dict) and "__error" in data):
                last_error = data
                continue
            courses = await _collect_from_response(data)
            if courses:
                return {
                    "status": "ok",
                    "search_outcome": "hits",
                    "query": q,
                    "count": len(courses),
                    "courses": courses,
                    "filter_used": filter_str.split(";")[0][:80],
                }

        if last_error is not None and isinstance(last_error, dict):
            err: dict[str, object] = {
                "status": "error",
                "search_outcome": "api_error",
                "message": str(
                    last_error.get("__error")
                    or last_error.get("__raw")
                    or last_error
                ),
            }
            if "__error" in last_error:
                err["http_status_or_error"] = last_error.get("__error")
            if "__url" in last_error:
                u = str(last_error["__url"])
                err["request_url_suffix"] = u[-220:] if len(u) > 220 else u
            return err
        if last_error is not None:
            return {
                "status": "error",
                "search_outcome": "api_error",
                "message": str(last_error),
            }
        return {
            "status": "ok",
            "search_outcome": "zero_hits",
            "query": q,
            "count": 0,
            "courses": [],
            "term_id": CURRENT_TERM_ID,
            "hint": (
                "Für diesen Suchbegriff und termId liefert die Demo **keine** passende Lehrveranstaltung "
                "(Katalog leer) — das ist **kein** Ausfall der REST-API, sondern fehlende Daten in der Demo. "
                "Mit anderem Titel/Kürzel suchen oder TUMONLINE_TERM_ID prüfen; die Demo spiegelt nicht "
                "immer die produktive TUMonline-Kursliste."
            ),
        }

    # ── REGISTRATION INFO ────────────────────────
    async def get_course_registration_info(self, course_id: str) -> dict:
        """
        Real API structure:
        resource[i].link → name="RpRegistrationProcedureDto" → key = procedure_id
        resource[i].content.cpCourseRegProcRelationsDto → procedure details
        """
        procs = await self._get(f"slc.tm.cp/student/courses/{course_id}/registrationProcedures")

        if not procs or "__error" in procs:
            return {"status": "error", "message": f"Could not retrieve procedures: {procs}"}

        resource_list = procs.get("resource", [])
        procedures = []

        for item in resource_list:
            if not isinstance(item, dict):
                continue

            # procedure_id is in item["link"] with name="RpRegistrationProcedureDto"
            procedure_id = "?"
            for lnk in item.get("link", []):
                if lnk.get("name") == "RpRegistrationProcedureDto":
                    procedure_id = lnk.get("key", "?")
                    break

            content = item.get("content", {})
            dto = content.get("cpCourseRegProcRelationsDto", {})
            course_name = dto.get("courseTitle", {}).get("value", "?")

            reg_procs = dto.get("registrationProcedures", dto.get("regProcedures", []))
            if isinstance(reg_procs, dict):
                reg_procs = [reg_procs]

            if reg_procs:
                for rp in reg_procs:
                    procedures.append({
                        "procedure_id":         procedure_id,
                        "name":                 rp.get("name", {}).get("value", "?"),
                        "registration_from":    rp.get("registrationFrom", rp.get("regFrom", "")),
                        "registration_to":      rp.get("registrationTo",   rp.get("regTo", "")),
                        "unregister_deadline":  rp.get("deregistrationTo", ""),
                        "max_participants":     rp.get("maxParticipants", "unlimited"),
                        "current_participants": rp.get("currentParticipants", "?"),
                        "can_register":         rp.get("registrationPossible", True),
                    })
            else:
                # Fallback: at least return the procedure_id we found
                procedures.append({
                    "procedure_id": procedure_id,
                    "name":         course_name,
                    "can_register": True,
                })

        if not procedures:
            return {"status": "error", "message": "No procedures found in the API response."}

        return {
            "status":      "ok",
            "course_id":   course_id,
            "course_name": procedures[0].get("name", "?"),
            "procedures":  procedures,
        }

    # ── REGISTER ─────────────────────────────────
    async def register_for_course(self, course_id: str, procedure_id: str) -> dict:
        reg_url = f"{UI_BASE}/slc.tm.cp/student/registrationProcedures/{procedure_id}?$ctx=&courseId={course_id}"
        await self.page.goto(reg_url, wait_until="domcontentloaded", timeout=TIMEOUT)
        await self.page.wait_for_timeout(3500)

        # STEP 1: Some courses require selecting a group (Standardgruppe checkbox) first.
        # The checkbox must be checked before "Belegwunsch erfassen" becomes enabled.
        try:
            checkboxes = self.page.locator('input[type="checkbox"]')
            count = await checkboxes.count()
            if count > 0:
                for i in range(count):
                    cb = checkboxes.nth(i)
                    is_checked = await cb.is_checked()
                    if not is_checked:
                        await cb.click()
                        console.print(f"[dim]   → Checked group checkbox {i+1}/{count} (Standardgruppe)[/dim]")
                        await self.page.wait_for_timeout(800)
            else:
                # Fallback: try mat-checkbox or custom checkbox elements
                mat_checkboxes = self.page.locator('mat-checkbox, .mat-checkbox, [class*="checkbox"]')
                mat_count = await mat_checkboxes.count()
                for i in range(mat_count):
                    try:
                        await mat_checkboxes.nth(i).click()
                        console.print(f"[dim]   → Clicked mat-checkbox {i+1}/{mat_count}[/dim]")
                        await self.page.wait_for_timeout(800)
                    except Exception:
                        pass
        except Exception as e:
            console.print(f"[dim]   → No checkboxes found or error: {e}[/dim]")

        await self.page.wait_for_timeout(1000)

        # STEP 2: Click "Belegwunsch erfassen" on the main page (now enabled after checkbox)
        try:
            btn = self.page.locator('button:has-text("Belegwunsch erfassen")').first
            await btn.wait_for(state="visible", timeout=8000)
            await btn.click()
            console.print("[dim]   → Click 1: Belegwunsch erfassen (page)[/dim]")
            await self.page.wait_for_timeout(2000)
        except Exception as e:
            body = await self.page.locator("body").inner_text()
            return {
                "status": "button_not_found",
                "message": "Could not find 'Belegwunsch erfassen'. You may already be registered or the registration period is closed.",
                "page_excerpt": body[:400],
            }

        # STEP 3: Confirmation modal appears with another "Belegwunsch erfassen" (blue button)
        # "Bitte überprüfen Sie Ihren Belegwunsch vor dem endgültigen Erfassen."
        try:
            await self.page.wait_for_selector('button:has-text("Belegwunsch erfassen")', timeout=5000)
            # Two buttons with the same text now — the modal one is the last
            confirm_btn = self.page.locator('button:has-text("Belegwunsch erfassen")').last
            await confirm_btn.wait_for(state="visible", timeout=5000)
            await confirm_btn.click()
            console.print("[dim]   → Click 2: Belegwunsch erfassen (confirmation modal)[/dim]")
            await self.page.wait_for_timeout(2500)
        except Exception as e:
            return {
                "status": "modal_not_found",
                "message": f"First click succeeded but confirmation modal did not appear: {e}",
            }

        # STEP 4: Verify result
        body = await self.page.locator("body").inner_text()
        if any(kw in body.lower() for kw in ["erfolgreich", "angemeldet", "bestätigt", "success", "gespeichert"]):
            return {"status": "success", "message": "✓ Registration completed successfully."}

        return {
            "status":  "completed",
            "message": "All clicks executed. Please verify in the browser that registration was successful.",
            "page_excerpt": body[:300],
        }

    # ── UNREGISTER ───────────────────────────────
    async def unregister_from_course(self, course_id: str) -> dict:
        # First get the procedure_id
        info = await self.get_course_registration_info(course_id)
        if info.get("status") != "ok" or not info.get("procedures"):
            return {"status": "error", "message": "No registration procedures found."}

        procedure_id = info["procedures"][0]["procedure_id"]
        reg_url = f"{UI_BASE}/slc.tm.cp/student/registrationProcedures/{procedure_id}?$ctx=&courseId={course_id}"
        await self.page.goto(reg_url, wait_until="domcontentloaded", timeout=TIMEOUT)
        await self.page.wait_for_timeout(3500)

        # STEP 1: Click the "Abmelden" button on the main page
        for sel in ['button:has-text("Abmelden")', 'button:has-text("Austragen")', 'button:has-text("Stornieren")']:
            try:
                btn = self.page.locator(sel).first
                await btn.wait_for(state="visible", timeout=5000)
                await btn.click()
                console.print("[dim]   → Click 1: Abmelden (page)[/dim]")
                await self.page.wait_for_timeout(2000)
                break
            except Exception:
                continue
        else:
            return {"status": "button_not_found", "message": "Could not find unregistration button."}

        # STEP 2: Confirmation modal appears — "Vom Verfahren abmelden"
        # Modal has an "Abmelden" (blue) and "Abbrechen" button
        # We click the "Abmelden" inside the modal (the last one visible)
        try:
            await self.page.wait_for_selector('button:has-text("Abmelden")', timeout=5000)
            confirm_btn = self.page.locator('button:has-text("Abmelden")').last
            await confirm_btn.wait_for(state="visible", timeout=5000)
            await confirm_btn.click()
            console.print("[dim]   → Click 2: Abmelden (confirmation modal)[/dim]")
            await self.page.wait_for_timeout(2500)
        except Exception as e:
            return {
                "status": "modal_not_found",
                "message": f"First click succeeded but confirmation modal did not appear: {e}",
            }

        # STEP 3: Verify result
        body = await self.page.locator("body").inner_text()
        if any(kw in body.lower() for kw in ["erfolgreich", "abgemeldet", "success", "gespeichert"]):
            return {"status": "success", "message": f"✓ Successfully unregistered from course {course_id}."}

        return {
            "status":  "completed",
            "message": "Both clicks executed. Please verify in the browser that unregistration was successful.",
            "page_excerpt": body[:300],
        }

    # ── MY COURSES ───────────────────────────────
    async def get_my_courses(self) -> dict:
        await self.page.goto(
            f"{UI_BASE}/slc.tm.cp/student/myCourses?$ctx=&objTermId={CURRENT_TERM_ID}",
            wait_until="domcontentloaded", timeout=TIMEOUT
        )
        await self.page.wait_for_timeout(3000)

        data = await self._get("slc.tm.cp/student/myCourses", {"semesterId": CURRENT_TERM_ID})

        if data and "__error" not in data:
            links = data.get("links", [])
            courses = []
            for link in links:
                if link.get("rel") == "detail" and link.get("name") == "CpCourseDto":
                    course_id = link.get("key", "?")
                    detail = await self._get(f"slc.tm.cp/student/courses/{course_id}")
                    if detail and "__error" not in detail:
                        courses.append({
                            "course_id": course_id,
                            "code":      detail.get("courseCode", "?"),
                            "name":      detail.get("title", "?"),
                            "type":      detail.get("courseTypeCode", ""),
                        })
            if courses:
                return {"status": "ok", "my_courses": courses}

        # DOM fallback
        body = await self.page.locator("body").inner_text()
        lines = [l.strip() for l in body.splitlines() if l.strip() and len(l.strip()) > 5]
        return {"status": "ok_dom", "courses_raw": lines[:30]}

    # ── MY SCHEDULE ──────────────────────────────
    async def get_my_schedule(self) -> dict:
        await self.page.goto(
            f"{UI_BASE}/slc.tm.cp/student/myCourses?$ctx=&objTermId={CURRENT_TERM_ID}",
            wait_until="domcontentloaded", timeout=TIMEOUT
        )
        await self.page.wait_for_timeout(3500)

        body = await self.page.locator("body").inner_text()
        events, seen = [], set()

        # Extract lines containing weekday abbreviations
        for line in body.splitlines():
            line = line.strip()
            if any(d in line for d in ["Mo ", "Di ", "Mi ", "Do ", "Fr "]):
                if len(line) > 8 and line not in seen:
                    seen.add(line)
                    events.append(line)

        # Also try extracting from tables
        try:
            rows = self.page.locator("table tr")
            count = await rows.count()
            for i in range(1, min(count, 40)):
                cells = await rows.nth(i).locator("td").all_inner_texts()
                entry = " | ".join(c.strip() for c in cells if c.strip())
                if entry and entry not in seen and len(entry) > 5:
                    seen.add(entry)
                    events.append(entry)
        except Exception:
            pass

        return {
            "status":   "ok",
            "term":     f"SS2026 (termId={CURRENT_TERM_ID})",
            "schedule": events[:25] or ["No events found in your schedule."],
        }


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
async def do_login(page: Page, username: str, password: str):
    console.print("[cyan]→[/cyan] Connecting to TUMonline demo...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    for sel in ['button:has-text("TUM Login")', 'text="TUM Login"']:
        try:
            await page.locator(sel).first.click()
            break
        except Exception:
            continue

    await page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2500)

    for sel in ['input[name="j_username"]', 'input[name="username"]', 'input[type="text"]']:
        try:
            await page.locator(sel).first.fill(username)
            break
        except Exception:
            continue

    for sel in ['input[name="j_password"]', 'input[name="password"]', 'input[type="password"]']:
        try:
            await page.locator(sel).first.fill(password)
            break
        except Exception:
            continue

    for sel in ['button:has-text("LOGIN")', 'button[type="submit"]']:
        try:
            await page.locator(sel).first.click()
            break
        except Exception:
            continue

    try:
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    except Exception:
        pass
    await page.wait_for_timeout(3500)

    # Handle hooks/welcome page if it appears
    if "wbEeHooks" in page.url or "Hooks" in page.url:
        try:
            await page.locator('a:has-text("Weiter"), button:has-text("Weiter")').first.click()
            await page.wait_for_timeout(2000)
        except Exception:
            pass

    console.print("[green]✓[/green] Login successful")


# ─────────────────────────────────────────────
# BEDROCK ORCHESTRATOR
# ─────────────────────────────────────────────
class CampusCoPilot:
    def __init__(self, rest_client: TUMonlineRESTClient, region: str = REGION):
        self.bedrock = boto3.Session(
            region_name=region
        ).client("bedrock-runtime")
        self.rest    = rest_client
        self.history: list[dict] = []
        self.system  = (
            "You are the Campus Co-Pilot for TU München. You help students manage their university life "
            "by performing real actions in TUMonline DEMO environment.\n\n"
            "REGISTRATION FLOW (always follow this order):\n"
            "1. search_courses(query) → get the internal courseId (long number, e.g. 950878455)\n"
            "2. get_course_registration_info(course_id) → get procedureId and check dates/spots\n"
            "3. Show the info to the user and ask for explicit confirmation\n"
            "4. Only if confirmed: register_for_course(course_id, procedure_id)\n\n"
            "RULES:\n"
            "- Never register or unregister without explicit user confirmation.\n"
            "- Course codes like 'IN2061' are for searching — the real courseId is a long number.\n"
            "- Respond in English. Be concise and clear.\n"
            "- If there is an API error, explain it to the user in simple terms."
        )

    async def _run_tool(self, name: str, inp: dict) -> str:
        console.print(f"[yellow]⚙[/yellow] [bold]{name}[/bold] {inp}")
        try:
            match name:
                case "search_courses":               r = await self.rest.search_courses(**inp)
                case "get_course_registration_info": r = await self.rest.get_course_registration_info(**inp)
                case "register_for_course":          r = await self.rest.register_for_course(**inp)
                case "unregister_from_course":       r = await self.rest.unregister_from_course(**inp)
                case "get_my_courses":               r = await self.rest.get_my_courses()
                case "get_my_schedule":              r = await self.rest.get_my_schedule()
                case _:                              r = {"error": f"Unknown tool: {name}"}
        except Exception as e:
            r = {"error": str(e)}
        out = json.dumps(r, ensure_ascii=False)
        console.print(f"[dim]   {out[:300]}{'...' if len(out) > 300 else ''}[/dim]")
        return out

    async def chat(self, msg: str) -> str:
        self.history.append({"role": "user", "content": msg})
        while True:
            resp = self.bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "system": self.system,
                    "tools": TOOLS,
                    "messages": self.history,
                }),
                accept="application/json",
                contentType="application/json",
            )
            body        = json.loads(resp["body"].read())
            stop_reason = body.get("stop_reason")
            content     = body.get("content", [])
            self.history.append({"role": "assistant", "content": content})

            if stop_reason == "tool_use":
                results = []
                for block in content:
                    if block.get("type") == "tool_use":
                        out = await self._run_tool(block["name"], block.get("input", {}))
                        results.append({"type": "tool_result", "tool_use_id": block["id"], "content": out})
                self.history.append({"role": "user", "content": results})
                continue

            return " ".join(
                b.get("text", "") for b in content if b.get("type") == "text"
            ).strip() or "(No response)"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
async def main():
    console.print(Panel.fit(
        "[bold green]🎓 Campus Co-Pilot v3[/bold green]\n"
        "[dim]TUMonline Agent · Reply Hackathon 2025[/dim]\n"
        "[yellow]Environment: demo.campus.tum.de[/yellow]",
        border_style="green"
    ))

    t = Table(box=box.SIMPLE, border_style="dim")
    t.add_column("Example commands", style="white")
    for cmd in [
        "Search for course IN2061",
        "Register me for course IN2061",
        "Show my enrolled courses",
        "Unregister me from course IN2061",
        "Show my schedule",
    ]:
        t.add_row(f"• {cmd}")
    console.print(t)

    username = console.input("\n[bold]TUM username:[/bold] ").strip()
    password = getpass.getpass("Password: ")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False, slow_mo=80,
            args=["--disable-features=AutofillServerCommunication,PasswordManagerEnabled",
                  "--disable-save-password-bubble"],
        )
        page = await (await browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )).new_page()

        try:
            await do_login(page, username, password)
        except Exception as e:
            console.print(f"[red]✗ Login failed: {e}[/red]")
            await browser.close()
            return

        # Navigate to courses page to establish session context
        await page.goto(
            f"{UI_BASE}/slc.tm.cp/student/courses?$ctx=&$skip=0&objTermId={CURRENT_TERM_ID}&orgId={ORG_ID}",
            wait_until="domcontentloaded", timeout=TIMEOUT
        )
        await page.wait_for_timeout(2000)

        agent = CampusCoPilot(TUMonlineRESTClient(page), region=REGION)

        console.print()
        console.print(Rule("[bold green]Agent ready — type your request[/bold green]"))
        console.print("[dim]Type 'exit' to quit[/dim]\n")

        while True:
            try:
                user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "q"}:
                break

            console.print()
            with console.status("[yellow]Thinking...[/yellow]", spinner="dots"):
                try:
                    response = await agent.chat(user_input)
                except Exception as e:
                    response = f"Error: {e}"

            console.print(Panel(
                response,
                title="[bold green]Campus Co-Pilot[/bold green]",
                border_style="green"
            ))
            console.print()

        await browser.close()
        console.print("[green]✓[/green] Session closed.")


if __name__ == "__main__":
    asyncio.run(main())
