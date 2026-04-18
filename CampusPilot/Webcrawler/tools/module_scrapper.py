import asyncio
import json
import re
from playwright.async_api import async_playwright

# Replace these with the PUBLIC FPO URLs you copied from an Incognito window
CAREER_URLS = {
    "BSC_INFORMATION_SYSTEMS": "https://campus.tum.de/tumonline/wbstpcs.showSpoTree?pStStudiumNr=&pSJNr=1621&pStpStpNr=4999&pStartSemester=", 
    "BSC_COMPUTER_SCIENCE": "https://campus.tum.de/tumonline/wbstpcs.showSpoTree?pStStudiumNr=&pSJNr=1621&pStpStpNr=5371&pStartSemester="
}

async def expand_all_nodes(page):
    print("🌳 Brute-forcing the curriculum tree with raw JavaScript...")
    
    # Wait for the initial tree to render
    try:
        await page.wait_for_selector('mat-tree, table', timeout=15000)
    except Exception:
        print("⚠️ Warning: Main tree container not found.")

    expanded_total = 0
    
    while True:
        clicked_in_this_pass = 0
        
        # 1. Grab every single right-facing arrow currently in the DOM
        # We look specifically for the material icon text 'chevron_right'
        icons = await page.locator('mat-icon', has_text='chevron_right').all()
        
        for icon in icons:
            # Check if it's actually visible on the screen
            if await icon.is_visible():
                try:
                    # TRICK: Do NOT use Playwright's standard click().
                    # Inject JavaScript to forcefully click the element at the DOM level.
                    # This ignores overlapping elements, invisible blockers, and animations.
                    await icon.evaluate("node => node.click()")
                    clicked_in_this_pass += 1
                    expanded_total += 1
                    
                    # Tiny pause so Angular doesn't crash from clicking 50 things at once
                    await page.wait_for_timeout(200) 
                except Exception:
                    pass # Ignore detached nodes, just keep moving

        if clicked_in_this_pass == 0:
            # We scanned the whole page and couldn't click a single new arrow.
            print(f"✅ Tree fully expanded! (Forced {expanded_total} clicks)")
            break
            
        # Give the network time to fetch the new rows we just asked for
        print(f"🔄 Pass complete (clicked {clicked_in_this_pass} nodes). Waiting for data to load...")
        await page.wait_for_timeout(1500)

    # Take a final screenshot to prove it worked
    await page.screenshot(path="debug_tree_expanded_bruteforce.png", full_page=True)
    print("📸 Saved snapshot to 'debug_tree_expanded_bruteforce.png'")
    
async def extract_modules(page, degree_id):
    print(f"🕵️ Scanning for modules in {degree_id}...")
    
    modules = []
    seen_ids = set()
    
    # Regex to find TUM module codes (e.g., IN0001, MA0902)
    module_code_pattern = re.compile(r"\b([A-Z]{2,4}\d{4,5})\b") 
    
    # Broaden the search: grab every single row/div that could contain text
    rows = page.locator("tr, mat-tree-node, .tree-row, .node-content")
    row_count = await rows.count()
    
    for i in range(row_count):
        row = rows.nth(i)
        if not await row.is_visible():
            continue
            
        text = await row.inner_text()
        
        match = module_code_pattern.search(text)
        if match:
            module_id = match.group(1)
            
            if module_id in seen_ids:
                continue
            seen_ids.add(module_id)
            
            # Try to grab ECTS
            ects_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:Credits|ECTS|CP)", text, re.IGNORECASE)
            ects = ects_match.group(1) if ects_match else "Unknown"
            
            module_record = {
                "degree_id": degree_id,
                "module_id": module_id,
                "raw_scraped_text": text.replace('\n', ' | '), 
                "ects": ects
            }
            modules.append(module_record)

    print(f"🎉 Found {len(modules)} modules for {degree_id}!")
    
    # --- DEBUGGING OUTPUT ---
    if len(modules) == 0:
        print(f"⚠️ FOUND 0 MODULES! Dumping page text to debug_{degree_id}.txt")
        body_text = await page.locator("body").inner_text()
        with open(f"debug_{degree_id}.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
            
    return modules

async def main():
    database_records = []

    print("🚀 Starting Public TUMonline Scraper...")
    
    async with async_playwright() as pw:
        # HEADLESS=FALSE: Watch the browser so you can see if it actually clicks the arrows!
        browser = await pw.chromium.launch(headless=False, slow_mo=100) 
        context = await browser.new_context()
        page = await context.new_page()

        for degree_id, url in CAREER_URLS.items():
            print(f"\n--- Processing {degree_id} ---")
            await page.goto(url, wait_until="networkidle")
            
            await expand_all_nodes(page)
            
            modules = await extract_modules(page, degree_id)
            database_records.extend(modules)

        await browser.close()

    with open("tum_database_seed.json", "w", encoding="utf-8") as f:
        json.dump(database_records, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Database seed file created: tum_database_seed.json")

if __name__ == "__main__":
    asyncio.run(main())