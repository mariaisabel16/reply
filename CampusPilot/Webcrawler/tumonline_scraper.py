"""
TUMonline Scraper — demo.campus.tum.de
Hackathon Reply Challenge 2025

Scrapes in one run:
  1. Curriculum page  → scrapped_data.json, study_plan.json, screenshots
  2. Student card     → user.json, screenshot
  3. Grades/Modules   → modules.json, modules_passed.json

All files saved to: CampusPilot/Agent/TemporaryUserInfoFiles/session_YYYYMMDD_HHMMSS/
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

# ── URLs ──────────────────────────────────────
BASE_URL         = "https://demo.campus.tum.de/DSYSTEM"
HOME_URL         = f"{BASE_URL}/ee/ui/ca2/app/desktop/#/home?$ctx=lang=DE"
LOGIN_URL        = f"{BASE_URL}/ee/ui/ca2/app/desktop/#/login"
CURRICULUM_URL   = f"{BASE_URL}/ee/ui/ca2/app/desktop/#/slc.cm.cs/student/myStudies/1089084/myCurriculumElements/2917690?$ctx=design=ca;lang=DE&$filter=active-eq=true;currentlyValid-eq=true;partOfCurriculum-eq=true"
STUDENT_CARD_URL = f"{BASE_URL}/wbstudkart.wbstudent"
ACHIEVEMENTS_URL  = f"{BASE_URL}/ee/ui/ca2/app/desktop/#/slc.xm.ac/achievements?$ctx=lang=DE"
STUDIENSTATUS_URL = f"{BASE_URL}/ee/ui/ca2/app/desktop/#pl/ui/$ctx/studienstatus.ht6ststatusDetail?$ctx=design=ca2;header=max;lang=de&pBasisStudNr=1089084&pEditable=FALSE&pOrgnr=&pStPersonNr=2326956"
TIMEOUT          = 20000

# ── Output directory ──────────────────────────
# Script: CampusPilot/webcrawler/tumonline_scraper.py
# Output: CampusPilot/Agent/TemporaryUserInfoFiles/session_*/
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


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
async def automated_login(page: Page, username: str, password: str):
    console.print("[cyan]→[/cyan] Opening TUMonline demo login page...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    async def click_first(selectors, label, timeout=10000):
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

    if not await click_first(['button:has-text("TUM Login")', 'text="TUM Login"'], "TUM Login"):
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
                              'button[type="submit"]', 'input[type="submit"]'], "LOGIN"):
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
# SECTION 0 — CURRENT SEMESTER
# ─────────────────────────────────────────────
async def scrape_semester(page: Page) -> dict:
    """
    Discovered from body text: "Studienbeitrag 2026 S" → current semester label
    Discovered from Studienstatus page: "Anzahl Semester gemeldet:6" → semester number
    Both are on the Mein Studium / curriculum page body.
    """
    console.print("[cyan]→[/cyan] Extracting semester info from curriculum page...")
    await page.goto(CURRICULUM_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(4000)

    body = await get_body_text(page)
    norm = normalize_for_regex(body)

    result = {
        "current_semester_label": None,   # e.g. "2026 S"
        "current_semester_number": None,  # e.g. 6  (Fachsemester)
        "study_program": None,            # e.g. "Informatik [20211], Bachelor of Science"
        "total_semesters_enrolled": None, # from Studienstatus: "Anzahl Semester gemeldet:6"
    }

    # 1. Semester label from "Studienbeitrag 2026 S" or "Vorgemerkte Lehrveranstaltungen 2026 S"
    m = re.search(r"Studienbeitrag\s+(\d{4}\s*[SW])", norm)
    if not m:
        m = re.search(r"Vorgemerkte Lehrveranstaltungen\s+(\d{4}\s*[SW])", norm)
    if m:
        result["current_semester_label"] = m.group(1).strip()

    # 2. Study program from "Informatik [20211], Bachelor of Science (1630 17 030)"
    m2 = re.search(r"(Informatik\s*\[.*?\],\s*Bachelor[^(\n]+)", norm)
    if m2:
        result["study_program"] = m2.group(1).strip()

    # 3. Navigate to Studienstatus page to get "Anzahl Semester gemeldet:X"
    #    and current Fachsemester (highest number in table)
    try:
        await page.goto(STUDIENSTATUS_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(3000)
        status_body = await get_body_text(page)

        # "Anzahl Semester gemeldet:6"
        m3 = re.search(r"Anzahl Semester gemeldet\s*[:\s]\s*(\d+)", status_body)
        if m3:
            result["total_semesters_enrolled"] = int(m3.group(1))
            result["current_semester_number"]  = int(m3.group(1))

        # Also parse the table for the current row (26S = gemeldet, highest Fachsemester)
        # Format: "26S  gemeldet  01.04.2026  6 Fachsemester - Fach 1"
        fach_matches = re.findall(r"(\d+[SW])\s+gemeldet\s+[\d.]+\s+(\d+)\s+Fachsemester", status_body)
        if fach_matches:
            # Take the one with the highest Fachsemester number
            latest = max(fach_matches, key=lambda x: int(x[1]))
            result["current_semester_number"] = int(latest[1])
            result["current_semester_code"]   = latest[0]  # e.g. "26S"

    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Could not fetch Studienstatus: {e}")

    console.print(f"[green]✓[/green] Semester: {result['current_semester_label']} "
                  f"(Fachsemester {result['current_semester_number']})")
    return result



# ─────────────────────────────────────────────
# SECTION 1 — CURRICULUM
# ─────────────────────────────────────────────
def extract_semester(text):
    text = normalize_for_regex(text)
    for pat in [r"(Wintersemester\s*\d{4}/\d{2,4})", r"(Sommersemester\s*\d{4})",
                r"(WS\s*\d{4}/\d{2,4})", r"(SS\s*\d{4})"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_matrikelnummer(text):
    text = normalize_for_regex(text)
    m = re.search(r"\b\d{7,8}\b", text)
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


def extract_ects(text):
    text = normalize_for_regex(text)
    for pat in [r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits\s*erreicht",
                r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return {"ects_current": m.group(1).replace(",", "."),
                    "ects_total":   m.group(2).replace(",", ".")}
    return None


def extract_average(text):
    text = normalize_for_regex(text)
    for pat in [r"Vorläufige\s+Durchschnittsnote\s*(\d+(?:[.,]\d+)?)",
                r"Durchschnittsnote\s*(\d+(?:[.,]\d+)?)"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).replace(",", ".")
    return None


async def scrape_curriculum(page: Page) -> dict:
    console.print("[cyan]→[/cyan] Opening curriculum page...")
    await page.goto(CURRICULUM_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)

    await page.screenshot(path=str(SESSION_DIR / "tum_curriculum.png"), full_page=True)
    console.print("[green]✓[/green] Screenshot: tum_curriculum.png")

    text = await get_body_text(page)
    save_text("curriculum_body.txt", text)
    norm = normalize_for_regex(text)

    # Extract ECTS from widget
    ects = None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits\s*erreicht", norm, re.IGNORECASE)
    if m:
        ects = {"ects_current": m.group(1).replace(",", "."), "ects_total": m.group(2).replace(",", ".")}
    if not ects:
        ects = extract_ects(norm)

    avg = None
    m2 = re.search(r"Vorläufige\s+Durchschnittsnote\s*(\d+(?:[.,]\d+)?)", norm, re.IGNORECASE)
    if m2:
        avg = m2.group(1).replace(",", ".")

    # Extract module tiles with POSITIV pattern
    modules = []
    seen = set()
    for mo in re.finditer(r"([^\n]+?)\s+POSITIV\s+(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits",
                          norm, re.IGNORECASE):
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
        "name":           extract_name(text),
        "semester":       extract_semester(text),
        "matrikelnummer": extract_matrikelnummer(text),
        "ects":           ects,
        "average":        avg,
        "modules":        modules,
    }


# ─────────────────────────────────────────────
# SECTION 2 — STUDENT CARD
# ─────────────────────────────────────────────
async def scrape_student_card(page: Page) -> dict:
    console.print("[cyan]→[/cyan] Opening Studierendenkartei...")
    await page.goto(STUDENT_CARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(5000)

    await page.screenshot(path=str(SESSION_DIR / "studierendenkartei.png"), full_page=True)
    console.print("[green]✓[/green] Screenshot: studierendenkartei.png")

    text = await get_body_text(page)
    save_text("student_card_body.txt", text)

    result = {
        "matrikelnummer": None,
        "basisinformationen": {},
        "weitere_informationen": {},
    }

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

    result["matrikelnummer"] = (result["basisinformationen"].get("Matrikelnummer")
                                or extract_matrikelnummer(text))
    return result


# ─────────────────────────────────────────────
# SECTION 3 — GRADES / ACHIEVEMENTS
# ─────────────────────────────────────────────
async def scrape_grades(page: Page) -> list:
    """
    Parse all modules from /slc.xm.ac/achievements DOM body.

    Body structure per module:
      Note
      3,7
      3,7 - ausreichend
      PRÜFUNG
      IN0019Numerisches Programmieren     ← ID glued to title
      6 ECTS-Credits | 27.02.2026
      Informatik
      Letztgültige Leistung
    """
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

        # Grade value e.g. "3,7"
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

        # Module ID + title — ID glued to title with no space
        id_title = lines[j]
        # Try with space first: "IN0019 Numerisches..."
        id_match = re.match(r'^([A-Z]{2,4}\d{4,7}[A-Z]{0,2}\d{0,2})\s+(.*)', id_title)
        if not id_match:
            # Fallback: split before first uppercase letter of title
            id_match = re.match(r'^([A-Z]{2,4}\d{4,7}[A-Z]{0,2}\d{0,2})([A-ZÄÖÜ].*)', id_title)
        if not id_match:
            i += 1
            continue

        module_id = id_match.group(1)
        title     = id_match.group(2).strip()
        j += 1

        # ECTS + date "6 ECTS-Credits | 27.02.2026"
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

        is_final   = "Letztgültig" in status
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
def display_summary(curriculum: dict, student: dict, modules: list, semester: dict = None):
    console.print()
    console.print(Rule("[bold green]TUMonline Demo — Full Summary[/bold green]"))

    passed     = [m for m in modules if m["passed"]]
    in_prog    = [m for m in modules if m["in_progress"]]
    total_ects = sum(m["credits"] or 0 for m in passed)

    console.print(Panel(
        f"[bold]Name:[/bold]              {curriculum.get('name') or 'N/A'}\n"
        f"[bold]Matrikelnummer:[/bold]    {student.get('matrikelnummer') or 'N/A'}\n"
        f"[bold]Current Semester:[/bold]  {(semester or {}).get('current_semester_label','N/A')} (Fachsemester {(semester or {}).get('current_semester_number','?')})\n"
        f"[bold]Semester code:[/bold]     {(semester or {}).get('current_semester_code','N/A')}\n"
        f"[bold]ECTS (curriculum):[/bold] "
        f"{(curriculum.get('ects') or {}).get('ects_current','?')} / "
        f"{(curriculum.get('ects') or {}).get('ects_total','?')}\n"
        f"[bold]Grade average:[/bold]     {curriculum.get('average') or 'N/A'}\n"
        f"[bold]Passed modules:[/bold]    {len(passed)}  ({total_ects} ECTS)\n"
        f"[bold]In progress:[/bold]       {len(in_prog)}",
        title="Summary", border_style="cyan"
    ))

    # Passed grades table
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
        "[dim]Curriculum + Student Card + Grades · Reply Hackathon 2025[/dim]\n"
        "[yellow]Environment: demo.campus.tum.de[/yellow]",
        border_style="green"
    ))

    username = console.input("[bold]TUM username:[/bold] ").strip()
    password = getpass.getpass("Password: ")

    # Create session folder
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

        # ── Login ─────────────────────────────────
        try:
            await automated_login(page, username, password)
        except Exception as e:
            console.print(f"[red]✗ Login error: {e}[/red]")
            await browser.close()
            return

        # ── Semester ─────────────────────────────────
        semester = await scrape_semester(page)

        # ── Curriculum ────────────────────────────
        curriculum = await scrape_curriculum(page)
        console.print("[green]✓[/green] Curriculum data extracted.")

        # ── Student card ──────────────────────────
        student = await scrape_student_card(page)
        console.print("[green]✓[/green] Student card data extracted.")

        # ── Grades ────────────────────────────────
        modules = await scrape_grades(page)
        console.print("[green]✓[/green] Grades extracted.")

        await browser.close()

    # ── Save all files ────────────────────────
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
        "semester":               curriculum.get("semester"),
        "current_semester_label":  semester.get("current_semester_label"),
        "current_semester_number": semester.get("current_semester_number"),
        "current_semester_code":   semester.get("current_semester_code"),
        "total_semesters_enrolled":semester.get("total_semesters_enrolled"),
        "study_program":           semester.get("study_program"),
        "ects":                    curriculum.get("ects"),
        "average":                 curriculum.get("average"),
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

    # ── Display ───────────────────────────────
    display_summary(curriculum, student, modules, semester)
    console.print(f"\n[bold]All files saved to:[/bold] {SESSION_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
