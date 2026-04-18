"""
TUMonline Scraper — demo.campus.tum.de
Hackathon Reply Challenge 2025
All output files saved to: CampusPilot/TemporaryUserInfoFiles/
No screenshots generated.
"""

import asyncio
import getpass
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright not installed: pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.rule import Rule
except ImportError:
    print("Rich not installed: pip install rich")
    sys.exit(1)

# ── URLs ──────────────────────────────────────
HOME_URL         = "https://demo.campus.tum.de/DSYSTEM/ee/ui/ca2/app/desktop/#/home?$ctx=lang=DE"
LOGIN_URL        = "https://demo.campus.tum.de/DSYSTEM/ee/ui/ca2/app/desktop/#/login"
CURRICULUM_URL   = "https://demo.campus.tum.de/DSYSTEM/ee/ui/ca2/app/desktop/#/slc.cm.cs/student/myStudies/1089084/myCurriculumElements/2917690?$ctx=design=ca;lang=DE&$filter=active-eq=true;currentlyValid-eq=true;partOfCurriculum-eq=true"
STUDENT_CARD_URL = "https://demo.campus.tum.de/DSYSTEM/wbstudkart.wbstudent"
TIMEOUT          = 20000

# ── Output directory — session folders are created here each run ──
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "TemporaryUserInfoFiles"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SESSION_DIR: Path = OUTPUT_DIR  # overridden at runtime

console = Console()


def print_header():
    console.print(Panel.fit(
        "[bold green]TUMonline Scraper[/bold green]\n"
        "[dim]Auto login + Curriculum + Studierendenkartei[/dim]\n"
        "[yellow]Environment: demo.campus.tum.de[/yellow]\n"
        f"[dim]Output: {OUTPUT_DIR}[/dim]",
        border_style="green"
    ))


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


def extract_semester(text: str):
    text = normalize_for_regex(text)
    patterns = [
        r"(Wintersemester\s*\d{4}/\d{2,4})",
        r"(Sommersemester\s*\d{4})",
        r"(WS\s*\d{4}/\d{2,4})",
        r"(SS\s*\d{4})",
        r"(Studienbeitrag\s+\d{4}\s*[SW])",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return None


def extract_matrikelnummer(text: str):
    text = normalize_for_regex(text)
    m = re.search(r"\b\d{7,8}\b", text)
    return m.group(0) if m else None


def extract_name(text: str):
    text = clean_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    blacklist = {"DE", "EN", "Mein Studium", "Studienstatus", "Planung", "Aktivität", "Semesterplan", "Module", "Prüfungen"}
    for line in lines[:30]:
        if line in blacklist:
            continue
        if re.search(r"\d", line):
            continue
        if len(line.split()) >= 2 and len(line) < 80:
            if not any(x in line.lower() for x in ["studium", "credits", "durchschnitt"]):
                return line
    return None


def extract_ects(text: str):
    text = normalize_for_regex(text)
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits\s*erreicht",
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits",
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*ECTS",
        r"(\d+(?:[.,]\d+)?)\s+von\s+(\d+(?:[.,]\d+)?)\s*ECTS",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return {"ects_current": m.group(1).replace(",", "."), "ects_total": m.group(2).replace(",", ".")}
    return None


def extract_average(text: str):
    text = normalize_for_regex(text)
    patterns = [
        r"Vorläufige\s+Durchschnittsnote\s*(\d+(?:[.,]\d+)?)",
        r"Durchschnittsnote\s*(\d+(?:[.,]\d+)?)",
        r"Notendurchschnitt\s*(\d+(?:[.,]\d+)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).replace(",", ".")
    return None


def extract_study_status(text: str):
    text = normalize_for_regex(text)
    patterns = [
        r"(Studienstatus.*?)(?:Planung|Aktivität|Vorläufige Durchschnittsnote|$)",
        r"(Studienbeitrag\s+\d{4}\s*[SW])",
    ]
    values = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            value = clean_text(m.group(1))
            if value and value not in values:
                values.append(value)
    return values if values else None


async def get_body_text(page):
    try:
        return await page.locator("body").inner_text()
    except Exception:
        return ""


async def get_tables(page):
    all_tables = []
    try:
        tables = page.locator("table")
        table_count = await tables.count()
        for i in range(table_count):
            table = tables.nth(i)
            rows = table.locator("tr")
            row_count = await rows.count()
            parsed_rows = []
            for r in range(row_count):
                row = rows.nth(r)
                cells = row.locator("th, td")
                cell_count = await cells.count()
                values = []
                for c in range(cell_count):
                    try:
                        values.append(clean_text(await cells.nth(c).inner_text()))
                    except Exception:
                        values.append("")
                if any(values):
                    parsed_rows.append(values)
            if parsed_rows:
                all_tables.append(parsed_rows)
    except Exception:
        pass
    return all_tables


async def get_cards(page):
    selectors = ["mat-card", '[class*="card"]', '[class*="tile"]', '[class*="summary"]', '[class*="stat"]', '[class*="widget"]']
    cards = []
    seen = set()
    for sel in selectors:
        try:
            loc = page.locator(sel)
            count = await loc.count()
            for i in range(count):
                try:
                    txt = clean_text(await loc.nth(i).inner_text())
                    if txt and txt not in seen:
                        seen.add(txt)
                        cards.append({"selector": sel, "text": txt})
                except Exception:
                    pass
        except Exception:
            pass
    return cards[:100]


async def get_links(page):
    links = []
    seen = set()
    for selector in ["a", "button", '[role="button"]']:
        try:
            loc = page.locator(selector)
            count = await loc.count()
            for i in range(count):
                item = loc.nth(i)
                try:
                    text = clean_text(await item.inner_text())
                except Exception:
                    text = ""
                try:
                    href = await item.get_attribute("href")
                except Exception:
                    href = None
                if text or href:
                    key = (text, href)
                    if key not in seen:
                        seen.add(key)
                        links.append({"selector": selector, "text": text, "href": href})
        except Exception:
            pass
    return links[:200]


async def extract_status_widgets(page):
    body_text = await get_body_text(page)
    body_text_norm = normalize_for_regex(body_text)
    result = {"ects": None, "average": None}
    ects_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits\s*erreicht",
        body_text_norm, re.IGNORECASE | re.DOTALL,
    )
    if ects_match:
        result["ects"] = {
            "ects_current": ects_match.group(1).replace(",", "."),
            "ects_total": ects_match.group(2).replace(",", "."),
        }
    avg_match = re.search(
        r"Vorläufige\s+Durchschnittsnote\s*(\d+(?:[.,]\d+)?)",
        body_text_norm, re.IGNORECASE | re.DOTALL,
    )
    if avg_match:
        result["average"] = avg_match.group(1).replace(",", ".")
    return result


async def extract_module_tiles(page):
    text = await get_body_text(page)
    text = normalize_for_regex(text)
    modules = []
    pattern = r"([^\n]+?)\s+POSITIV\s+(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits"
    for m in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
        module_name = clean_text(m.group(1))
        if module_name:
            modules.append({
                "module_name":    module_name,
                "status":         "POSITIV",
                "credits_current": m.group(2).replace(",", "."),
                "credits_total":   m.group(3).replace(",", "."),
            })
    deduped, seen = [], set()
    for mod in modules:
        key = (mod["module_name"], mod["credits_current"], mod["credits_total"])
        if key not in seen:
            seen.add(key)
            deduped.append(mod)
    return deduped


async def scrape_curriculum_page(page):
    text = await get_body_text(page)
    normalized_text = normalize_for_regex(text)
    tables  = await get_tables(page)
    cards   = await get_cards(page)
    links   = await get_links(page)
    widgets = await extract_status_widgets(page)
    modules = await extract_module_tiles(page)
    return {
        "url":            page.url,
        "name":           extract_name(text),
        "semester":       extract_semester(text),
        "matrikelnummer": extract_matrikelnummer(text),
        "ects":           widgets.get("ects") or extract_ects(normalized_text),
        "average":        widgets.get("average") or extract_average(normalized_text),
        "study_status":   extract_study_status(normalized_text),
        "modules":        modules,
        "text_preview":   text[:5000],
        "cards":          cards,
        "tables":         tables,
        "links":          links,
    }


async def maybe_dismiss_password_popup(page):
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass


async def click_first_visible(page, selectors, timeout=8000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.click()
            return True, sel
        except Exception:
            continue
    return False, None


async def fill_first_visible(page, selectors, value, timeout=8000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.click()
            await maybe_dismiss_password_popup(page)
            await loc.fill("")
            await loc.fill(value)
            return True, sel
        except Exception:
            continue
    return False, None


async def automated_login(page, username: str, password: str):
    console.print("[cyan]→[/cyan] Opening TUMonline demo login page...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    clicked, selector = await click_first_visible(
        page,
        ['button:has-text("TUM Login")', 'text="TUM Login"', 'input[value="TUM Login"]'],
        timeout=10000,
    )
    if not clicked:
        raise RuntimeError("Could not find the TUM Login button.")
    console.print(f"[green]✓[/green] TUM Login clicked")

    await page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2500)

    user_ok, _ = await fill_first_visible(
        page,
        ['input[name="j_username"]', 'input[name="username"]', 'input[id="username"]',
         'input[placeholder*="@tum"]', 'input[type="text"]'],
        username, timeout=12000,
    )
    if not user_ok:
        raise RuntimeError("Username field not found.")
    console.print("[green]✓[/green] Username entered")

    pass_ok, _ = await fill_first_visible(
        page,
        ['input[name="j_password"]', 'input[name="password"]', 'input[id="password"]', 'input[type="password"]'],
        password, timeout=12000,
    )
    if not pass_ok:
        raise RuntimeError("Password field not found.")
    console.print("[green]✓[/green] Password entered")

    submit_ok, _ = await click_first_visible(
        page,
        ['button:has-text("LOGIN")', 'button:has-text("Login")', 'button[type="submit"]', 'input[type="submit"]'],
        timeout=10000,
    )
    if not submit_ok:
        raise RuntimeError("LOGIN button not found.")

    try:
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    except Exception:
        pass
    await page.wait_for_timeout(4000)

    # Handle hooks/welcome page if it appears
    if "wbEeHooks" in page.url or "Hooks" in page.url:
        try:
            await page.locator('a:has-text("Weiter"), button:has-text("Weiter")').first.click()
            await page.wait_for_timeout(2000)
        except Exception:
            pass

    current_url = page.url.lower()
    if any(x in current_url for x in ["login", "shibboleth", "idp"]):
        raise RuntimeError("Login did not complete successfully.")
    console.print("[green]✓[/green] Login successful!")


async def extract_student_card_data(page):
    text = await get_body_text(page)
    result = {
        "url": page.url, "matrikelnummer": None, "nachname": None, "vorname": None,
        "email": None, "geburtsdatum": None, "geburtsort": None, "telefon": None,
        "geschlecht": None, "basisinformationen": {}, "weitere_informationen": {},
        "text_preview": text[:4000],
    }
    try:
        tables = page.locator("table")
        table_count = await tables.count()
        for i in range(table_count):
            table = tables.nth(i)
            table_text = clean_text(await table.inner_text())
            if not any(k in table_text for k in ["Basisinformationen", "Weitere Informationen"]):
                continue
            rows = table.locator("tr")
            row_count = await rows.count()
            current_section = None
            for r in range(row_count):
                row = rows.nth(r)
                cells = row.locator("th, td")
                cell_count = await cells.count()
                values = []
                for c in range(cell_count):
                    try:
                        values.append(clean_text(await cells.nth(c).inner_text()))
                    except Exception:
                        values.append("")
                values = [v for v in values if v]
                if not values:
                    continue
                joined = " | ".join(values)
                if "Basisinformationen" in joined:
                    current_section = "basisinformationen"
                    continue
                if "Weitere Informationen" in joined:
                    current_section = "weitere_informationen"
                    continue
                if len(values) == 2 and current_section:
                    result[current_section][values[0]] = values[1]
                elif len(values) >= 4 and current_section == "weitere_informationen":
                    for j in range(0, len(values) - 1, 2):
                        if values[j]:
                            result[current_section][values[j]] = values[j+1] if j+1 < len(values) else ""
    except Exception:
        pass

    basis = result["basisinformationen"]
    result["matrikelnummer"] = basis.get("Matrikelnummer") or extract_matrikelnummer(text)
    return result


def save_json(filename: str, data: dict):
    path = SESSION_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[green]✓[/green] Saved: {path}")


def save_text(filename: str, text: str):
    path = SESSION_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    console.print(f"[green]✓[/green] Saved: {path}")


async def main():
    global SESSION_DIR
    print_header()

    username = console.input("[bold]TUM username:[/bold] ").strip()
    password = getpass.getpass("Password: ")

    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    SESSION_DIR = OUTPUT_DIR / f"session_{session_ts}"
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    console.print(f"[dim]Session folder: {SESSION_DIR}[/dim]")

    result = {
        "scraped_at":   datetime.now().isoformat(),
        "environment":  "demo.campus.tum.de",
        "curriculum_data":   {},
        "student_card_data": {},
    }

    async with async_playwright() as pw:
        console.print("[cyan]→[/cyan] Starting browser...")
        browser = await pw.chromium.launch(
            headless=False, slow_mo=100,
            args=["--disable-features=AutofillServerCommunication,PasswordManagerEnabled",
                  "--disable-save-password-bubble"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 950},
            locale="de-DE", timezone_id="Europe/Berlin",
        )
        page = await context.new_page()

        try:
            await automated_login(page, username, password)
        except Exception as e:
            console.print(f"[red]✗ Login error: {e}[/red]")
            await browser.close()
            return

        # ── Curriculum ────────────────────────────
        console.print("[cyan]→[/cyan] Opening curriculum page...")
        await page.goto(CURRICULUM_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(5000)

        await page.screenshot(path=str(SESSION_DIR / "tum_curriculum.png"), full_page=True)
        console.print("[green]✓[/green] Screenshot saved: tum_curriculum.png")

        curriculum_body_text = await get_body_text(page)
        save_text("curriculum_body.txt", curriculum_body_text)

        result["curriculum_data"] = await scrape_curriculum_page(page)
        console.print("[green]✓[/green] Curriculum data extracted.")

        # ── Student card ──────────────────────────
        console.print("[cyan]→[/cyan] Opening Studierendenkartei...")
        await page.goto(STUDENT_CARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(5000)

        student_card_body_text = await get_body_text(page)

        await page.screenshot(path=str(SESSION_DIR / "studierendenkartei.png"), full_page=True)
        console.print("[green]✓[/green] Screenshot saved: studierendenkartei.png")
        save_text("student_card_body.txt", student_card_body_text)

        result["student_card_data"] = await extract_student_card_data(page)
        console.print("[green]✓[/green] Student card data extracted.")

        # ── Save all JSON files ───────────────────
        save_json("scrapped_data.json", result)
        save_json("user.json", result["student_card_data"])
        save_json("modules.json", {"modules": result["curriculum_data"].get("modules", [])})
        save_json("study_plan.json", {
            "semester":  result["curriculum_data"].get("semester"),
            "ects":      result["curriculum_data"].get("ects"),
            "average":   result["curriculum_data"].get("average"),
            "status":    result["curriculum_data"].get("study_status"),
        })

        # ── Summary ───────────────────────────────
        console.print()
        console.print(Rule("[bold green]TUMonline Demo Summary[/bold green]"))
        cd = result["curriculum_data"]
        sd = result["student_card_data"]
        console.print(Panel(
            f"[bold]Name:[/bold] {cd.get('name') or 'N/A'}\n"
            f"[bold]Matrikelnummer:[/bold] {sd.get('matrikelnummer') or 'N/A'}\n"
            f"[bold]Semester:[/bold] {cd.get('semester') or 'N/A'}\n"
            f"[bold]ECTS:[/bold] {(cd.get('ects') or {}).get('ects_current','?')} / {(cd.get('ects') or {}).get('ects_total','?')}\n"
            f"[bold]Grade avg:[/bold] {cd.get('average') or 'N/A'}",
            title="Summary", border_style="cyan"
        ))

        modules = cd.get("modules") or []
        if modules:
            t = Table(title="Modules", box=box.ROUNDED, border_style="green", show_lines=True)
            t.add_column("Module", style="white", overflow="fold")
            t.add_column("Status", style="green")
            t.add_column("Credits", style="cyan")
            for mod in modules:
                t.add_row(
                    mod.get("module_name", ""),
                    mod.get("status", ""),
                    f"{mod.get('credits_current','?')}/{mod.get('credits_total','?')}"
                )
            console.print(t)

        console.print()
        console.print(f"[bold]All files saved to:[/bold] {OUTPUT_DIR}")
        console.print("[dim]Browser stays open. Press Ctrl+C to close.[/dim]")
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            pass

        await browser.close()
        console.print("[green]✓[/green] Browser closed.")


if __name__ == "__main__":
    asyncio.run(main())
