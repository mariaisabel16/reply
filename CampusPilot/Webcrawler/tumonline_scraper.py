import asyncio
import getpass
import json
import re
import sys
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.rule import Rule
except ImportError:
    Console = None
    Panel = None
    Table = None
    box = None
    Rule = None

HOME_URL = "https://campus.tum.de/tumonline/ee/ui/ca2/app/desktop/#/home?$ctx=lang=DE"
LOGIN_URL = "https://campus.tum.de/tumonline/ee/ui/ca2/app/desktop/#/login"
CURRICULUM_URL = "https://campus.tum.de/tumonline/ee/ui/ca2/app/desktop/#/slc.cm.cs/student/myStudies/1089084/myCurriculumElements/2917690?$ctx=design=ca;lang=DE&$filter=active-eq=true;currentlyValid-eq=true;partOfCurriculum-eq=true"
STUDENT_CARD_URL = "https://campus.tum.de/tumonline/wbstudkart.wbstudent"
TIMEOUT = 20000

console = Console() if Console is not None else None


def ensure_runtime_dependencies() -> None:
    if async_playwright is None:
        print("Playwright ist nicht installiert.")
        print("Installiere mit:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)
    if console is None:
        print("Rich ist nicht installiert.")
        print("Installiere mit:")
        print("  pip install rich")
        sys.exit(1)


def print_header():
    console.print(
        Panel.fit(
            "[bold green]TUMonline Scraper[/bold green]\n"
            "[dim]Automatischer Login + Curriculum + Studierendenkartei[/dim]",
            border_style="green",
        )
    )


def print_step(msg: str):
    console.print(f"[cyan]->[/cyan] {msg}")


def print_ok(msg: str):
    console.print(f"[green]OK[/green] {msg}")


def print_warn(msg: str):
    console.print(f"[yellow]WARN[/yellow] {msg}")


def print_error(msg: str):
    console.print(f"[red]ERR[/red] {msg}")


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
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def extract_matrikelnummer(text: str):
    text = normalize_for_regex(text)
    match = re.search(r"\b\d{7,8}\b", text)
    return match.group(0) if match else None


def extract_name(text: str):
    text = clean_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    blacklist = {
        "DE",
        "EN",
        "Mein Studium",
        "Studienstatus",
        "Planung",
        "Aktivitaet",
        "Semesterplan",
        "Module",
        "Pruefungen",
    }
    for line in lines[:30]:
        if line in blacklist:
            continue
        if re.search(r"\d", line):
            continue
        if len(line.split()) >= 2 and len(line) < 80:
            if not any(keyword in line.lower() for keyword in ["studium", "credits", "durchschnitt"]):
                return line
    return None


def extract_ects(text: str):
    text = normalize_for_regex(text)
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits\s*erreicht",
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits",
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*ECTS",
        r"(\d+(?:[.,]\d+)?)\s+von\s+(\d+(?:[.,]\d+)?)\s*ECTS",
        r"Credits\s*erreicht.*?(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)",
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?).*?Credits",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            return {
                "ects_current": match.group(1).replace(",", "."),
                "ects_total": match.group(2).replace(",", "."),
            }
    return None


def extract_average(text: str):
    text = normalize_for_regex(text)
    patterns = [
        r"Vorlaeufige\s+Durchschnittsnote\s*(\d+(?:[.,]\d+)?)",
        r"Durchschnittsnote\s*(\d+(?:[.,]\d+)?)",
        r"Notendurchschnitt\s*(\d+(?:[.,]\d+)?)",
        r"Durchschnitt.*?(\d+(?:[.,]\d+)?)",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).replace(",", ".")
    return None


def extract_study_status(text: str):
    text = normalize_for_regex(text)
    patterns = [
        r"(Studienstatus.*?)(?:Planung|Aktivitaet|Vorlaeufige Durchschnittsnote|$)",
        r"(Studienbeitrag\s+\d{4}\s*[SW])",
    ]
    values = []
    for pat in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            value = clean_text(match.group(1))
            if value and value not in values:
                values.append(value)
    return values if values else None


def normalize_scraped_agent_input(
    scrape_result: dict,
    *,
    program: str = "TUM Studium",
    interests: list[str] | None = None,
    desired_ects: int = 18,
    master_goal: str = "Data Engineering",
    agent_task: str = "Plane mein naechstes Semester, schlage passende Module vor und bereite die Anmeldung vor.",
) -> dict:
    curriculum_data = scrape_result.get("curriculum_data", {})
    student_card_data = scrape_result.get("student_card_data", {})
    ects = curriculum_data.get("ects") or {}
    first_name = student_card_data.get("vorname") or ""
    last_name = student_card_data.get("nachname") or ""
    full_name = f"{first_name} {last_name}".strip() or curriculum_data.get("name") or "Student"

    return {
        "user_id": student_card_data.get("matrikelnummer") or curriculum_data.get("matrikelnummer") or "tum_user",
        "name": full_name,
        "program": program,
        "semester_label": curriculum_data.get("semester"),
        "desired_ects": desired_ects,
        "master_goal": master_goal,
        "agent_task": agent_task,
        "interests": interests or ["Machine Learning", "Data Science"],
        "total_ects": float(ects.get("ects_current", 0) or 0),
        "study_status": curriculum_data.get("study_status") or [],
        "study_history": [],
        "blocked_slots": [],
        "preferred_free_days": [],
        "source": "tumonline_scraper",
    }


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
        for index in range(table_count):
            table = tables.nth(index)
            rows = table.locator("tr")
            row_count = await rows.count()
            parsed_rows = []
            for row_index in range(row_count):
                row = rows.nth(row_index)
                cells = row.locator("th, td")
                cell_count = await cells.count()
                values = []
                for cell_index in range(cell_count):
                    try:
                        values.append(clean_text(await cells.nth(cell_index).inner_text()))
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
    selectors = [
        "mat-card",
        '[class*="card"]',
        '[class*="tile"]',
        '[class*="summary"]',
        '[class*="stat"]',
        '[class*="widget"]',
    ]
    cards = []
    seen = set()
    for selector in selectors:
        try:
            loc = page.locator(selector)
            count = await loc.count()
            for index in range(count):
                try:
                    text = clean_text(await loc.nth(index).inner_text())
                    if text and text not in seen:
                        seen.add(text)
                        cards.append({"selector": selector, "text": text})
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
            for index in range(count):
                item = loc.nth(index)
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
        body_text_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if ects_match:
        result["ects"] = {
            "ects_current": ects_match.group(1).replace(",", "."),
            "ects_total": ects_match.group(2).replace(",", "."),
        }
    avg_match = re.search(
        r"Vorlaeufige\s+Durchschnittsnote\s*(\d+(?:[.,]\d+)?)",
        body_text_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if avg_match:
        result["average"] = avg_match.group(1).replace(",", ".")
    return result


async def extract_module_tiles(page):
    text = await get_body_text(page)
    text = normalize_for_regex(text)
    modules = []
    pattern = r"([^\n]+?)\s+POSITIV\s+(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*Credits"
    for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
        module_name = clean_text(match.group(1))
        if module_name:
            modules.append(
                {
                    "module_name": module_name,
                    "status": "POSITIV",
                    "credits_current": match.group(2).replace(",", "."),
                    "credits_total": match.group(3).replace(",", "."),
                }
            )
    deduped = []
    seen = set()
    for module in modules:
        key = (module["module_name"], module["credits_current"], module["credits_total"])
        if key not in seen:
            seen.add(key)
            deduped.append(module)
    return deduped


async def scrape_curriculum_page(page):
    text = await get_body_text(page)
    normalized_text = normalize_for_regex(text)
    tables = await get_tables(page)
    cards = await get_cards(page)
    links = await get_links(page)
    widgets = await extract_status_widgets(page)
    modules = await extract_module_tiles(page)
    return {
        "url": page.url,
        "name": extract_name(text),
        "semester": extract_semester(text),
        "matrikelnummer": extract_matrikelnummer(text),
        "ects": widgets.get("ects") or extract_ects(normalized_text),
        "average": widgets.get("average") or extract_average(normalized_text),
        "study_status": extract_study_status(normalized_text),
        "modules": modules,
        "text_preview": text[:5000],
        "cards": cards,
        "tables": tables,
        "links": links,
    }


async def maybe_dismiss_password_popup(page):
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass


async def click_first_visible(page, selectors, timeout=8000):
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.click()
            return True, selector
        except Exception:
            continue
    return False, None


async def fill_first_visible(page, selectors, value, timeout=8000):
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.click()
            await maybe_dismiss_password_popup(page)
            await loc.fill("")
            await loc.fill(value)
            return True, selector
        except Exception:
            continue
    return False, None


async def automated_login(page, username: str, password: str):
    print_step("Oeffne TUMonline Login-Seite...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2000)

    print_step("Klicke auf 'TUM Login'...")
    clicked, selector = await click_first_visible(
        page,
        ['button:has-text("TUM Login")', 'text="TUM Login"', 'input[value="TUM Login"]'],
        timeout=10000,
    )
    if not clicked:
        await page.screenshot(path="debug_login_first_page.png", full_page=True)
        raise RuntimeError("Konnte den 'TUM Login'-Button auf der ersten Seite nicht finden.")
    print_ok(f"'TUM Login' geklickt mit Selector: {selector}")

    await page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
    await page.wait_for_timeout(2500)

    print_step("Warte auf zweites Login-Formular...")
    user_ok, user_sel = await fill_first_visible(
        page,
        [
            'input[name="j_username"]',
            'input[name="username"]',
            'input[id="username"]',
            'input[placeholder*="@tum"]',
            'input[type="text"]',
        ],
        username,
        timeout=12000,
    )
    if not user_ok:
        await page.screenshot(path="debug_second_login_username.png", full_page=True)
        raise RuntimeError("Konnte das Username-Feld im zweiten Login-Formular nicht finden.")
    print_ok(f"Username eingetragen mit Selector: {user_sel}")

    pass_ok, pass_sel = await fill_first_visible(
        page,
        [
            'input[name="j_password"]',
            'input[name="password"]',
            'input[id="password"]',
            'input[type="password"]',
        ],
        password,
        timeout=12000,
    )
    if not pass_ok:
        await page.screenshot(path="debug_second_login_password.png", full_page=True)
        raise RuntimeError("Konnte das Passwort-Feld im zweiten Login-Formular nicht finden.")
    print_ok(f"Passwort eingetragen mit Selector: {pass_sel}")

    print_step("Klicke auf 'LOGIN'...")
    submit_ok, submit_sel = await click_first_visible(
        page,
        ['button:has-text("LOGIN")', 'button:has-text("Login")', 'button[type="submit"]', 'input[type="submit"]'],
        timeout=10000,
    )
    if not submit_ok:
        await page.screenshot(path="debug_second_login_submit.png", full_page=True)
        raise RuntimeError("Konnte den LOGIN-Button im zweiten Formular nicht finden.")
    print_ok(f"LOGIN geklickt mit Selector: {submit_sel}")

    try:
        await page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    except Exception:
        pass

    await page.wait_for_timeout(4000)

    current_url = page.url.lower()
    if any(marker in current_url for marker in ["login", "shibboleth", "idp"]):
        await page.screenshot(path="debug_login_not_finished.png", full_page=True)
        raise RuntimeError("Login scheint nicht abgeschlossen zu sein; Seite ist noch im Login-/SSO-Flow.")
    print_ok("Login erfolgreich abgeschlossen.")


async def extract_student_card_data(page):
    text = await get_body_text(page)
    result = {
        "url": page.url,
        "matrikelnummer": None,
        "nachname": None,
        "vorname": None,
        "email": None,
        "geburtsdatum": None,
        "geburtsort": None,
        "telefon": None,
        "geschlecht": None,
        "basisinformationen": {},
        "weitere_informationen": {},
        "text_preview": text[:4000],
    }

    try:
        tables = page.locator("table")
        table_count = await tables.count()
        for table_index in range(table_count):
            table = tables.nth(table_index)
            table_text = clean_text(await table.inner_text())

            if not any(keyword in table_text for keyword in ["Basisinformationen", "Weitere Informationen"]):
                continue

            rows = table.locator("tr")
            row_count = await rows.count()
            current_section = None

            for row_index in range(row_count):
                row = rows.nth(row_index)
                cells = row.locator("th, td")
                cell_count = await cells.count()
                values = []

                for cell_index in range(cell_count):
                    try:
                        values.append(clean_text(await cells.nth(cell_index).inner_text()))
                    except Exception:
                        values.append("")

                values = [value for value in values if value]
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
                    label, value = values[0], values[1]
                    result[current_section][label] = value
                elif len(values) >= 4 and current_section == "weitere_informationen":
                    for index in range(0, len(values) - 1, 2):
                        label = values[index]
                        value = values[index + 1] if index + 1 < len(values) else ""
                        if label:
                            result[current_section][label] = value
    except Exception:
        pass

    async def extract_value_near_label(label_text: str):
        try:
            label_loc = page.locator(f'text="{label_text}"').first
            await label_loc.wait_for(state="visible", timeout=3000)

            container = label_loc.locator("xpath=ancestor::tr[1]")
            if await container.count() > 0:
                cell_text = clean_text(await container.inner_text())
                parts = [part.strip() for part in cell_text.split("\n") if part.strip()]
                filtered = [part for part in parts if part != label_text]
                if filtered:
                    return filtered[0]

            next_td = label_loc.locator("xpath=ancestor::td[1]/following-sibling::td[1]")
            if await next_td.count() > 0:
                value = clean_text(await next_td.inner_text())
                if value:
                    return value
        except Exception:
            pass
        return None

    basis = result["basisinformationen"]
    result["matrikelnummer"] = (
        basis.get("Matrikelnummer")
        or await extract_value_near_label("Matrikelnummer")
        or extract_matrikelnummer(text)
    )

    return result


def render_summary(curriculum_data: dict, student_card_data: dict | None = None):
    console.print()
    console.print(Rule("[bold green]TUMonline Uebersicht[/bold green]"))

    student_card_data = student_card_data or {}
    first_name = student_card_data.get("vorname") or ""
    last_name = student_card_data.get("nachname") or ""
    full_name = f"{first_name} {last_name}".strip()

    name = full_name or curriculum_data.get("name") or "Nicht gefunden"
    semester = curriculum_data.get("semester") or "Nicht gefunden"
    matrikelnummer = student_card_data.get("matrikelnummer") or "Nicht gefunden"
    avg = curriculum_data.get("average") or "Nicht gefunden"
    ects = curriculum_data.get("ects") or {}
    ects_current = ects.get("ects_current", "Nicht gefunden")
    ects_total = ects.get("ects_total", "Nicht gefunden")

    summary = (
        f"[bold]Name:[/bold] {name}\n"
        f"[bold]Matrikelnummer:[/bold] {matrikelnummer}\n"
        f"[bold]Semester / Status:[/bold] {semester}\n"
        f"[bold]ECTS:[/bold] {ects_current} / {ects_total}\n"
        f"[bold]Vorlaeufige Durchschnittsnote:[/bold] {avg}"
    )

    console.print(Panel(summary, title="Zusammenfassung", border_style="cyan"))


def render_status_table(data: dict):
    status_values = data.get("study_status") or []
    table = Table(title="Studienstatus", box=box.ROUNDED, border_style="blue")
    table.add_column("Feld", style="bold white")
    table.add_column("Wert", style="white")

    if status_values:
        for index, value in enumerate(status_values, start=1):
            table.add_row(f"Status {index}", value)
    else:
        table.add_row("Status", "[dim]Nicht gefunden[/dim]")

    console.print(table)


def render_modules_table(data: dict):
    modules = data.get("modules") or []
    table = Table(title="Gefundene Module", box=box.ROUNDED, border_style="green", show_lines=True)
    table.add_column("Modul", style="white", overflow="fold")
    table.add_column("Status", style="green")
    table.add_column("Credits", style="cyan")

    if modules:
        for module in modules:
            current = module.get("credits_current", "?")
            total = module.get("credits_total", "?")
            table.add_row(module.get("module_name", ""), module.get("status", ""), f"{current}/{total}")
    else:
        table.add_row("[dim]Keine Module erkannt[/dim]", "", "")

    console.print(table)


def render_student_card_table(data: dict):
    table = Table(title="Studierendenkartei", box=box.ROUNDED, border_style="magenta")
    table.add_column("Feld", style="bold white")
    table.add_column("Wert", style="white")

    fields = [("Matrikelnummer", data.get("matrikelnummer"))]
    for label, value in fields:
        table.add_row(label, value or "[dim]Nicht gefunden[/dim]")

    console.print(table)


def render_files_panel():
    text = (
        "[bold]Gespeicherte Dateien:[/bold]\n"
        "- tum_curriculum.png\n"
        "- tum_curriculum_body.txt\n"
        "- tum_curriculum_data.json\n"
        "- studierendenkartei.png\n"
        "- studierendenkartei_body.txt\n"
        "- tum_agent_input.json"
    )
    console.print(Panel(text, title="Output", border_style="magenta"))


async def main():
    ensure_runtime_dependencies()
    print_header()

    username = console.input("[bold]TUM-Kennung[/bold]: ").strip()
    password = getpass.getpass("Passwort: ")

    result = {
        "scraped_at": datetime.now().isoformat(),
        "home_url": HOME_URL,
        "curriculum_url": CURRICULUM_URL,
        "student_card_url": STUDENT_CARD_URL,
        "curriculum_data": {},
        "student_card_data": {},
    }

    async with async_playwright() as pw:
        print_step("Starte Browser...")
        browser = await pw.chromium.launch(
            headless=False,
            slow_mo=100,
            args=[
                "--disable-features=AutofillServerCommunication,PasswordManagerEnabled",
                "--disable-save-password-bubble",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1440, "height": 950},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )

        page = await context.new_page()

        try:
            await automated_login(page, username, password)
        except Exception as exc:
            print_error(str(exc))
            print_warn("Debug-Screenshots wurden gespeichert, falls moeglich.")
            await browser.close()
            return

        print_step("Oeffne Curriculum-Seite...")
        await page.goto(CURRICULUM_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(5000)

        await page.screenshot(path="tum_curriculum.png", full_page=True)
        print_ok("Screenshot gespeichert: tum_curriculum.png")

        curriculum_body_text = await get_body_text(page)
        with open("tum_curriculum_body.txt", "w", encoding="utf-8") as handle:
            handle.write(curriculum_body_text)
        print_ok("Body-Text gespeichert: tum_curriculum_body.txt")

        result["curriculum_data"] = await scrape_curriculum_page(page)
        print_ok("Curriculum-Daten extrahiert.")

        print_step("Oeffne Studierendenkartei...")
        await page.goto(STUDENT_CARD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
        await page.wait_for_timeout(5000)

        await page.screenshot(path="studierendenkartei.png", full_page=True)
        print_ok("Screenshot gespeichert: studierendenkartei.png")

        student_card_body_text = await get_body_text(page)
        with open("studierendenkartei_body.txt", "w", encoding="utf-8") as handle:
            handle.write(student_card_body_text)
        print_ok("Body-Text gespeichert: studierendenkartei_body.txt")

        result["student_card_data"] = await extract_student_card_data(page)
        print_ok("Studierendenkartei-Daten extrahiert.")

        with open("tum_curriculum_data.json", "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print_ok("Daten gespeichert: tum_curriculum_data.json")

        agent_input = normalize_scraped_agent_input(result)
        with open("tum_agent_input.json", "w", encoding="utf-8") as handle:
            json.dump(agent_input, handle, ensure_ascii=False, indent=2)
        print_ok("Agent-Input gespeichert: tum_agent_input.json")

        curriculum_data = result["curriculum_data"]
        student_card_data = result["student_card_data"]

        render_summary(curriculum_data, student_card_data)
        render_status_table(curriculum_data)
        render_modules_table(curriculum_data)
        render_student_card_table(student_card_data)
        render_files_panel()

        console.print()
        console.print("[dim]Browser bleibt offen. Mit Ctrl+C beenden.[/dim]")

        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            pass

        await browser.close()
        print_ok("Browser geschlossen.")


if __name__ == "__main__":
    asyncio.run(main())
