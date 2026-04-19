"""
TUMonline Scraper — demo.campus.tum.de
Hackathon Reply Challenge 2025

Scrapes in one run:
  1. Student card     → user.json, fachsemester, dynamic IDs
  2. Curriculum page  → scrapped_data.json, study_plan.json, screenshots
  3. Grades/Modules   → modules.json, modules_passed.json

Works for ANY TUM account — IDs are discovered dynamically from the student card page.

All files saved to: CampusPilot/TemporaryUserInfoFiles/session_YYYYMMDD_HHMMSS/
"""

import asyncio
import getpass
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.rule import Rule
except ImportError:
    print("pip install rich")
    sys.exit(1)

# ── Static URLs (same for all users) ─────────
BASE_URL         = "https://demo.campus.tum.de/DSYSTEM"
LOGIN_URL        = f"{BASE_URL}/ee/ui/ca2/app/desktop/#/login"
STUDENT_CARD_URL = f"{BASE_URL}/wbstudkart.wbstudent"
ACHIEVEMENTS_URL = f"{BASE_URL}/ee/ui/ca2/app/desktop/#/slc.xm.ac/achievements?$ctx=lang=DE"

# ── Dynamic URLs (built after reading student card) ──
CURRICULUM_URL    = ""
STUDIENSTATUS_URL = ""

TIMEOUT = 20000

# ── Output directory ──────────────────────────
# Script: CampusPilot/Webcrawler/tumonline_scraper.py
# Output: CampusPilot/TemporaryUserInfoFiles/session_*/
OUTPUT_DIR  = Path(__file__).resolve().parent.parent / "TemporaryUserInfoFiles"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR: Path = OUTPUT_DIR  # overridden at runtime

console = Console()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_regex(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def save_json(filename: str, data):
    path = SESSION_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[green]✓[/green] Saved: {path}")


def save_text(filename: str, text: str):
    path = SESSION_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    console.print(f"[green]✓[/green] Saved: {path}")


async def get_body_text(page: Page) -> str:
    try:
        return await page.locator("body").inner_text()
    except Exception:
        return ""


def _truncate_studiengang_line(s: str) -> str:
    s = clean_text(s.split("\n")[0] if s else "")
    for sep in ("\n", "  ", " Credits", " ECTS", " Pflicht", " | "):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
    return s.strip(" ,.;:-—")[:160]


async def extract_studiengang_from_mein_studium_dom(page: Page) -> str | None:
    """
    TUMonline CA2 / Angular: Studiengang aus sichtbarer Überschrift oder Baumnavigation lesen
    (z. B. „[20211] Bachelor Informatik“, Sidebar „Bachelor Informatik“).
    """
    noise = re.compile(r"Pflichtmodul|Pflichtmodule|Prüfung|Semesterplan|Modulhandbuch", re.I)

    async def _scan_locator(loc) -> str | None:
        try:
            n = await loc.count()
            for i in range(min(n, 30)):
                raw = await loc.nth(i).inner_text()
                txt = clean_text(raw)
                if not txt or len(txt) > 200:
                    continue
                first = txt.split("\n")[0].strip()
                m = re.match(
                    r"^\s*(\[\d{4,6}\]\s*(?:Bachelor|Master)(?:\s+of\s+(?:Science|Arts))?\s+.+)$",
                    first,
                    re.I,
                )
                if m and not noise.search(first):
                    cand = _truncate_studiengang_line(m.group(1))
                    if len(cand) >= 12:
                        return cand
                if re.match(r"^(Bachelor|Master)\s+\S+", first, re.I) and len(first) < 100:
                    if not noise.search(first) and "Credits" not in first:
                        return _truncate_studiengang_line(first)
        except Exception:
            pass
        return None

    for sel in (
        '[role="heading"]',
        "h1",
        "h2",
        ".mat-mdc-card-title",
        "mat-card-title",
        ".mdc-typography--headline5",
        ".mdc-typography--headline4",
        "[class*='headline']",
    ):
        hit = await _scan_locator(page.locator(sel))
        if hit:
            return hit

    try:
        tree = page.locator(
            "mat-tree-node, .mat-tree-node, [role='treeitem'], "
            "a.mat-mdc-list-item, .mat-mdc-list-item-text"
        )
        hit = await _scan_locator(tree)
        if hit:
            return hit
    except Exception:
        pass

    return None


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
async def automated_login(page: Page, username: str, password: str):
    console.print("[cyan]→[/cyan] Opening TUMonline demo login page...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    async def click_first(selectors, timeout=10000):
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=timeout)
                await loc.click()
                return True
            except Exception:
                continue
        return False

    async def fill_first(selectors, value, timeout=12000):
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                await loc.wait_for(state="visible", timeout=timeout)
                await loc.click()
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
                await loc.fill("")
                await loc.fill(value)
                return True
            except Exception:
                continue
        return False

    if not await click_first(['button:has-text("TUM Login")', 'text="TUM Login"']):
        raise RuntimeError("Could not find TUM Login button.")
    console.print("[green]✓[/green] TUM Login clicked")

    await page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2500)

    if not await fill_first(['input[name="j_username"]', 'input[name="username"]',
                              'input[id="username"]', 'input[type="text"]'], username):
        raise RuntimeError("Username field not found.")
    console.print("[green]✓[/green] Username entered")

    if not await fill_first(['input[name="j_password"]', 'input[name="password"]',
                              'input[id="password"]', 'input[type="password"]'], password):
        raise RuntimeError("Password field not found.")
    console.print("[green]✓[/green] Password entered")

    if not await click_first(['button:has-text("LOGIN")', 'button:has-text("Login")',
                               'button[type="submit"]', 'input[type="submit"]']):
        raise RuntimeError("LOGIN button not found.")

    try:
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    except Exception:
        pass
    await page.wait_for_timeout(4000)

    if "wbEeHooks" in page.url or "Hooks" in page.url:
        try:
            await page.locator('a:has-text("Weiter"), button:has-text("Weiter")').first.click()
            await page.wait_for_timeout(2000)
        except Exception:
            pass

    if any(x in page.url.lower() for x in ["login", "shibboleth", "idp"]):
        raise RuntimeError("Login did not complete successfully.")
    console.print("[green]✓[/green] Login successful!")


# ─────────────────────────────────────────────
# SECTION 1 — STUDENT CARD (+ dynamic ID discovery)
# ─────────────────────────────────────────────
async def scrape_student_card(page: Page) -> dict:
    """
    Scrapes the student card AND discovers dynamic IDs needed for other URLs.

    Observed across 3 users:
      myStudies ID  = pBasisStudNr  (same number, e.g. 1089084)
      curriculumElements ID          (varies per user, e.g. 2917690)
      pStPersonNr                    (varies per user, e.g. 2326956)

    The student card page contains links with all these IDs.
    """
    global CURRICULUM_URL, STUDIENSTATUS_URL

    console.print("[cyan]→[/cyan] Opening Studierendenkartei (+ ID discovery)...")
    await page.goto(STUDENT_CARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)

    await page.screenshot(path=str(SESSION_DIR / "studierendenkartei.png"), full_page=True)
    console.print("[green]✓[/green] Screenshot: studierendenkartei.png")

    text = await get_body_text(page)
    save_text("student_card_body.txt", text)

    result = {
        "matrikelnummer":    None,
        "full_name":         None,
        "vorname":           None,
        "nachname":          None,
        "studiengang":       None,
        "fachsemester":      None,
        "studien_id":        None,
        "spo_version":       None,
        "basisinformationen":    {},
        "weitere_informationen": {},
    }

    # ── Extract Basisinformationen table ─────
    try:
        tables = page.locator("table")
        count = await tables.count()
        for i in range(count):
            tbl_text = clean_text(await tables.nth(i).inner_text())
            if not any(k in tbl_text for k in ["Basisinformationen", "Weitere Informationen"]):
                continue
            rows = tables.nth(i).locator("tr")
            row_count = await rows.count()
            current = None
            for r in range(row_count):
                cells = rows.nth(r).locator("th, td")
                values = []
                for c in range(await cells.count()):
                    try:
                        values.append(clean_text(await cells.nth(c).inner_text()))
                    except Exception:
                        pass
                values = [v for v in values if v]
                if not values:
                    continue
                joined = " | ".join(values)
                if "Basisinformationen" in joined:
                    current = "basisinformationen"
                elif "Weitere Informationen" in joined:
                    current = "weitere_informationen"
                elif len(values) == 2 and current:
                    result[current][values[0]] = values[1]
    except Exception:
        pass

    for section in ("basisinformationen", "weitere_informationen"):
        d = result.get(section) or {}
        if not isinstance(d, dict):
            continue
        for k, v in d.items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            kl = k.strip().lower()
            if ("studiengang" in kl or "studienprogramm" in kl or kl == "studienfach") and v.strip():
                result["studiengang"] = v.strip()
                break
        if result.get("studiengang"):
            break

    # Extract fields from body text.
    # Line 1 has the display name: "Maria Sagastume Giron"
    # Fields have \t suffix and value is 2 lines later:
    #   line N:   "Matrikelnummer\t"
    #   line N+2: "03781850"
    lines = text.splitlines()

    # Full name is on line index 1 (second line of body)
    if len(lines) > 1:
        candidate = lines[1].strip()
        if candidate and not any(x in candidate for x in ["Campus", "Studierenden", "TUM", "http"]):
            result["full_name"] = candidate

    for i, line in enumerate(lines):
        stripped = line.strip().rstrip("\t").strip()
        if stripped == "Matrikelnummer" and i + 2 < len(lines):
            val = lines[i+2].strip()
            if re.match(r"\d{7,8}", val):
                result["matrikelnummer"] = val
        elif stripped == "Familien- oder Nachname" and i + 2 < len(lines):
            result["nachname"] = lines[i+2].strip()
        elif stripped == "Vorname" and i + 2 < len(lines):
            val = lines[i+2].strip()
            if val and not any(x in val for x in ["Bitte", "Männlich", "Weiblich", "Divers"]):
                result["vorname"] = val

    if not result["matrikelnummer"]:
        m = re.search(r"\b(\d{7,8})\b", text)
        if m:
            result["matrikelnummer"] = m.group(1)

    # ── Extract Fachsemester from study status table ──
    # Body text structure (each value on its own line):
    #   1630 17 030     20211   01.10.2023 -
    #   6 /          <- Fachsemester on its own line after Studien-ID line
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Find the Studien-ID line (format: "1630 17 030  20211  ...")
        sid_match = re.match(r"(\d{4}\s\d{2}\s\d{3})", stripped)
        if sid_match:
            result["studien_id"] = sid_match.group(1)
            spo = re.search(r"\b(\d{5})\b", stripped)
            if spo:
                result["spo_version"] = spo.group(1)
            # Fachsemester is on one of the next lines as "6 /"
            for data_line in lines[i+1:i+6]:
                m = re.match(r"^\s*(\d+)\s*/", data_line)
                if m and int(m.group(1)) <= 30:
                    result["fachsemester"] = int(m.group(1))
                    break
            break

    if result["fachsemester"]:
        console.print(f"[green]✓[/green] Fachsemester: {result['fachsemester']}")
    else:
        console.print("[yellow]⚠[/yellow] Could not extract Fachsemester")

    # ── Discover dynamic IDs from page links ──
    # Links on this page contain myStudies/STUDY_ID/myCurriculumElements/ELEM_ID
    # and pBasisStudNr=STUDY_ID&pStPersonNr=PERSON_ID
    study_id = None
    elem_id  = None
    person_id = None
    basis_nr  = None

    all_hrefs = await page.evaluate("""
        () => [...document.querySelectorAll('a')].map(a => a.href || a.getAttribute('href') || '')
    """)

    for href in all_hrefs:
        if not href:
            continue
        if not study_id:
            m = re.search(r"myStudies/(\d+)/myCurriculumElements/(\d+)", href)
            if m:
                study_id = m.group(1)
                elem_id  = m.group(2)
        if not person_id:
            pm = re.search(r"pStPersonNr=(\d+)", href)
            bm = re.search(r"pBasisStudNr=(\d+)", href)
            if pm: person_id = pm.group(1)
            if bm: basis_nr  = bm.group(1)
        if study_id and person_id:
            break

    # Build dynamic URLs
    if study_id and elem_id:
        CURRICULUM_URL = (
            f"{BASE_URL}/ee/ui/ca2/app/desktop/#/slc.cm.cs/student/myStudies/"
            f"{study_id}/myCurriculumElements/{elem_id}"
            f"?$ctx=design=ca;lang=DE&$filter=active-eq=true;currentlyValid-eq=true;partOfCurriculum-eq=true"
        )
        console.print(f"[green]✓[/green] Curriculum URL built (study={study_id}, elem={elem_id})")
    else:
        CURRICULUM_URL = ""
        console.print("[yellow]⚠[/yellow] Could not find study IDs — curriculum will be skipped")

    if person_id and basis_nr:
        STUDIENSTATUS_URL = (
            f"{BASE_URL}/studienstatus.ht6ststatusDetail"
            f"?pBasisStudNr={basis_nr}&pEditable=FALSE&pOrgnr=&pStPersonNr={person_id}"
        )
        console.print(f"[green]✓[/green] Studienstatus URL built (person={person_id})")
    else:
        STUDIENSTATUS_URL = ""
        console.print("[yellow]⚠[/yellow] Could not find person IDs — Studienstatus will be skipped")

    result["study_id"]  = study_id
    result["person_id"] = person_id

    return result


# ─────────────────────────────────────────────
# SECTION 2 — CURRICULUM
# ─────────────────────────────────────────────
def extract_matrikelnummer(text):
    m = re.search(r"\b\d{7,8}\b", normalize_for_regex(text))
    return m.group(0) if m else None


def extract_name(text):
    text = clean_text(text)
    blacklist = {"DE", "EN", "Mein Studium", "Studienstatus", "Planung",
                 "Aktivität", "Semesterplan", "Module", "Prüfungen"}
    for line in [l.strip() for l in text.splitlines() if l.strip()][:30]:
        if line in blacklist or re.search(r"\d", line):
            continue
        if len(line.split()) >= 2 and len(line) < 80:
            if not any(x in line.lower() for x in ["studium", "credits", "durchschnitt"]):
                return line
    return None


async def scrape_curriculum(page: Page) -> dict:
    if not CURRICULUM_URL:
        console.print("[yellow]⚠[/yellow] Curriculum URL not available — skipping")
        return {
            "url": None,
            "name": None,
            "matrikelnummer": None,
            "studiengang": None,
            "ects": None,
            "average": None,
            "modules": [],
        }

    console.print("[cyan]→[/cyan] Opening curriculum page...")
    await page.goto(CURRICULUM_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)

    await page.screenshot(path=str(SESSION_DIR / "tum_curriculum.png"), full_page=True)
    console.print("[green]✓[/green] Screenshot: tum_curriculum.png")

    text = await get_body_text(page)
    save_text("curriculum_body.txt", text)
    norm = normalize_for_regex(text)

    studiengang_dom = await extract_studiengang_from_mein_studium_dom(page)
    studiengang_text = None
    try:
        from session_manager import _extract_studiengang_from_body
        from session_manager import _extract_studiengang_mein_studium_heading

        studiengang_text = _extract_studiengang_mein_studium_heading(norm) or _extract_studiengang_from_body(
            norm
        )
    except ImportError:
        pass
    studiengang = studiengang_dom or studiengang_text
    if studiengang:
        console.print(f"[green]✓[/green] Studiengang: {studiengang}")

    # ECTS
    ects = None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits\s*erreicht", norm, re.IGNORECASE)
    if m:
        ects = {"ects_current": m.group(1).replace(",", "."), "ects_total": m.group(2).replace(",", ".")}

    # Grade average
    avg = None
    m2 = re.search(r"Vorläufige\s+Durchschnittsnote\s*(\d+(?:[.,]\d+)?)", norm, re.IGNORECASE)
    if m2:
        avg = m2.group(1).replace(",", ".")

    # Module tiles
    modules = []
    seen = set()
    for mo in re.finditer(
        r"([^\n]+?)\s+POSITIV\s+(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits",
        norm, re.IGNORECASE
    ):
        name = clean_text(mo.group(1))
        key = (name, mo.group(2), mo.group(3))
        if name and key not in seen:
            seen.add(key)
            modules.append({
                "module_name":     name,
                "status":          "POSITIV",
                "credits_current": mo.group(2).replace(",", "."),
                "credits_total":   mo.group(3).replace(",", "."),
            })

    return {
        "url":            page.url,
        "name":           extract_name(text),
        "matrikelnummer": extract_matrikelnummer(text),
        "studiengang":    studiengang,
        "ects":           ects,
        "average":        avg,
        "modules":        modules,
    }


# ─────────────────────────────────────────────
# SECTION 3 — GRADES / ACHIEVEMENTS
# ─────────────────────────────────────────────
async def scrape_grades(page: Page) -> list:
    console.print("[cyan]→[/cyan] Navigating to Meine Leistungen (grades)...")
    await page.goto(ACHIEVEMENTS_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(4000)

    body = await get_body_text(page)
    save_text("achievements_body.txt", body)

    lines = [l.strip() for l in body.splitlines() if l.strip()]
    modules = []
    i = 0

    while i < len(lines):
        if lines[i] != "Note":
            i += 1
            continue
        if i + 1 >= len(lines):
            break

        grade_match = re.match(r'^([\d][,\.]\d{1,2})$', lines[i + 1])
        if not grade_match:
            i += 1
            continue

        grade = float(grade_match.group(1).replace(",", "."))
        j = i + 2

        # Skip grade description "3,7 - ausreichend"
        if j < len(lines) and re.match(r'^[\d][,\.][\d].*-', lines[j]):
            j += 1

        # Exam type
        exam_type = ""
        if j < len(lines) and lines[j].upper() in {"PRÜFUNG", "KLAUSUR", "SEMINAR", "PRAKTIKUM", "HAUSARBEIT", "ÜBUNG"}:
            exam_type = lines[j]
            j += 1

        if j >= len(lines):
            i = j
            continue

        # Module ID + title
        id_title  = lines[j]
        id_match  = re.match(r'^([A-Z]{2,4}\d{4,7}[A-Z]{0,2}\d{0,2})\s+(.*)', id_title)
        if not id_match:
            id_match = re.match(r'^([A-Z]{2,4}\d{4,7}[A-Z]{0,2}\d{0,2})([A-ZÄÖÜ].*)', id_title)
        if not id_match:
            i += 1
            continue

        module_id = id_match.group(1)
        title     = id_match.group(2).strip()
        j += 1

        # ECTS + date
        credits, date = None, None
        if j < len(lines):
            em = re.match(r'(\d+)\s*ECTS-Credits\s*\|\s*([\d.]+)', lines[j])
            if em:
                credits = int(em.group(1))
                date    = em.group(2)
                j += 1

        # Department
        department = ""
        if j < len(lines) and not re.match(r'^(Note|PRÜFUNG|[\d]|Letztg|In Bear)', lines[j]):
            department = lines[j]
            j += 1

        # Status
        status = ""
        if j < len(lines) and ("Leistung" in lines[j] or "Bearbeitung" in lines[j]):
            status = lines[j]
            j += 1

        is_final    = "Letztgültig" in status
        in_progress = "Bearbeitung" in status

        modules.append({
            "module_id":   module_id,
            "title":       title,
            "grade":       grade,
            "credits":     credits,
            "date":        date,
            "department":  department,
            "status":      status,
            "type":        exam_type,
            "final":       is_final,
            "passed":      is_final and grade <= 4.0,
            "in_progress": in_progress,
        })
        i = j

    console.print(f"[green]✓[/green] Found {len(modules)} modules in grades")
    return modules


# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────
def display_summary(curriculum: dict, student: dict, modules: list):
    console.print()
    console.print(Rule("[bold green]TUMonline Demo — Full Summary[/bold green]"))

    passed     = [m for m in modules if m["passed"]]
    in_prog    = [m for m in modules if m["in_progress"]]
    total_ects = sum(m["credits"] or 0 for m in passed)

    stud = (
        student.get("studiengang")
        or curriculum.get("studiengang")
        or "N/A"
    )
    console.print(Panel(
        f"[bold]Name:[/bold]              {student.get('full_name') or curriculum.get('name') or 'N/A'}\n"
        f"[bold]Matrikelnummer:[/bold]    {student.get('matrikelnummer') or 'N/A'}\n"
        f"[bold]Studiengang:[/bold]       {stud}\n"
        f"[bold]Fachsemester:[/bold]      {student.get('fachsemester') or 'N/A'}\n"
        f"[bold]Studien-ID:[/bold]        {student.get('studien_id') or 'N/A'}\n"
        f"[bold]Passed modules:[/bold]    {len(passed)}  ({total_ects} ECTS)\n"
        f"[bold]In progress:[/bold]       {len(in_prog)}",
        title="Summary", border_style="cyan"
    ))

    if passed:
        t = Table(
            title=f"✓ Passed Modules ({len(passed)}) — grade ≤ 4.0 & Letztgültig",
            box=box.ROUNDED, border_style="green", show_lines=True
        )
        t.add_column("Module ID", style="cyan",    width=14)
        t.add_column("Title",     style="white",   overflow="fold")
        t.add_column("Grade",     justify="center", width=6)
        t.add_column("Credits",   style="magenta", justify="center", width=8)
        t.add_column("Date",      style="dim",     width=12)

        for m in sorted(passed, key=lambda x: x.get("date") or ""):
            g = m["grade"]
            grade_str = (f"[green]{g}[/green]" if g <= 2.0
                         else f"[yellow]{g}[/yellow]" if g <= 3.5
                         else f"[red]{g}[/red]")
            t.add_row(m["module_id"], m["title"], grade_str,
                      str(m["credits"]) if m["credits"] else "?",
                      m.get("date") or "")
        console.print(t)

    if in_prog:
        t2 = Table(title=f"⏳ In Progress ({len(in_prog)})",
                   box=box.SIMPLE, border_style="yellow")
        t2.add_column("Module ID", style="cyan",    width=14)
        t2.add_column("Title",     style="white",   overflow="fold")
        t2.add_column("Grade",     style="yellow",  justify="center", width=6)
        t2.add_column("Credits",   style="magenta", justify="center", width=8)
        for m in in_prog:
            t2.add_row(m["module_id"], m["title"],
                       str(m["grade"]), str(m["credits"]) if m["credits"] else "?")
        console.print(t2)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
async def main():
    global SESSION_DIR

    console.print(Panel.fit(
        "[bold green]TUMonline Scraper[/bold green]\n"
        "[dim]Student Card + Curriculum + Grades · Reply Hackathon 2025[/dim]\n"
        "[yellow]Environment: demo.campus.tum.de[/yellow]",
        border_style="green"
    ))

    username = console.input("[bold]TUM username:[/bold] ").strip()
    password = getpass.getpass("Password: ")

    SESSION_DIR = OUTPUT_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    console.print(f"[dim]Session folder: {SESSION_DIR}[/dim]\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False, slow_mo=100,
            args=["--disable-features=AutofillServerCommunication,PasswordManagerEnabled",
                  "--disable-save-password-bubble"],
        )
        page = await (await browser.new_context(
            viewport={"width": 1440, "height": 950},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )).new_page()

        try:
            await automated_login(page, username, password)
        except Exception as e:
            console.print(f"[red]✗ Login error: {e}[/red]")
            await browser.close()
            return

        # Student card FIRST — discovers dynamic IDs for other pages
        student = await scrape_student_card(page)
        console.print("[green]✓[/green] Student card data extracted.")

        # Curriculum — uses CURRICULUM_URL built by scrape_student_card
        curriculum = await scrape_curriculum(page)
        console.print("[green]✓[/green] Curriculum data extracted.")
        sg_cur = curriculum.get("studiengang") if isinstance(curriculum, dict) else None
        if sg_cur and not (isinstance(student.get("studiengang"), str) and str(student["studiengang"]).strip()):
            student["studiengang"] = str(sg_cur).strip()

        # Grades
        modules = await scrape_grades(page)
        console.print("[green]✓[/green] Grades extracted.")

        await browser.close()

    console.print()
    console.print(Rule("[bold cyan]Saving files[/bold cyan]"))

    passed = [m for m in modules if m["passed"]]

    save_json("scrapped_data.json", {
        "scraped_at":        datetime.now().isoformat(),
        "environment":       "demo.campus.tum.de",
        "curriculum_data":   curriculum,
        "student_card_data": student,
    })
    save_json("user.json", student)
    save_json("study_plan.json", {
        "fachsemester": student.get("fachsemester"),
        "studien_id":   student.get("studien_id"),
        "spo_version":  student.get("spo_version"),
        "ects":         curriculum.get("ects"),
        "average":      curriculum.get("average"),
    })
    save_json("modules.json", {
        "scraped_at":  datetime.now().isoformat(),
        "total":       len(modules),
        "passed":      len(passed),
        "in_progress": len([m for m in modules if m["in_progress"]]),
        "total_ects":  sum(m["credits"] or 0 for m in passed),
        "modules":     modules,
    })
    save_json("modules_passed.json", {
        "scraped_at": datetime.now().isoformat(),
        "count":      len(passed),
        "total_ects": sum(m["credits"] or 0 for m in passed),
        "modules":    passed,
    })

    display_summary(curriculum, student, modules)
    console.print(f"\n[bold]All files saved to:[/bold] {SESSION_DIR}")


async def scrape_all_async(username: str, password: str, headless: bool = True) -> dict:
    """Programmatic entry for the API backend — no interactive prompts."""
    global SESSION_DIR
    import tempfile
    SESSION_DIR = Path(tempfile.mkdtemp(prefix="campuspilot_"))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            slow_mo=50,
            args=["--disable-features=AutofillServerCommunication,PasswordManagerEnabled",
                  "--disable-save-password-bubble"],
        )
        page = await (await browser.new_context(
            viewport={"width": 1440, "height": 950},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )).new_page()
        try:
            await automated_login(page, username, password)
            student = await scrape_student_card(page)
            curriculum = await scrape_curriculum(page)
            modules = await scrape_grades(page)
        finally:
            await browser.close()

    passed = [m for m in modules if m.get("passed")]
    sg_cur = curriculum.get("studiengang") if isinstance(curriculum, dict) else None
    if isinstance(student, dict) and sg_cur and not (isinstance(student.get("studiengang"), str) and student["studiengang"].strip()):
        student["studiengang"] = str(sg_cur).strip()
    merged_studiengang = None
    if isinstance(student, dict):
        v = student.get("studiengang")
        if isinstance(v, str) and v.strip():
            merged_studiengang = v.strip()
    if not merged_studiengang and isinstance(curriculum, dict):
        v = curriculum.get("studiengang")
        if isinstance(v, str) and v.strip():
            merged_studiengang = v.strip()

    return {
        "scraped_at":        datetime.now().isoformat(),
        "environment":       "demo.campus.tum.de",
        "studiengang":       merged_studiengang,
        "student_card_data": student,
        "curriculum_data":   curriculum,
        "modules_data": {
            "total":       len(modules),
            "passed":      len(passed),
            "in_progress": len([m for m in modules if m.get("in_progress")]),
            "total_ects":  sum(m.get("credits") or 0 for m in passed),
            "items":       modules,
        },
    }


if __name__ == "__main__":
    asyncio.run(main())
