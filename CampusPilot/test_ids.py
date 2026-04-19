# test_ids.py
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://demo.campus.tum.de/DSYSTEM"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(f"{BASE_URL}/ee/ui/ca2/app/desktop/#/login")
        input("Login manualmente y presiona ENTER...")

        # Test the redirect endpoint
        data = await page.evaluate(f"""
            async () => {{
                const r = await fetch(
                    "{BASE_URL}/ee/rest/slc.cm.cs/student/redirects/myStudies/selection-or-primary-root",
                    {{ credentials: "include", headers: {{ "Accept": "application/json" }} }}
                );
                return await r.text();
            }}
        """)
        print(f"Redirect endpoint response:\n{data[:1000]}")

        # Also check current URL after navigating to myStudies
        await page.goto(f"{BASE_URL}/ee/ui/ca2/app/desktop/#/slc.cm.cs/student/myStudies")
        await page.wait_for_timeout(3000)
        print(f"\nURL after navigating to myStudies:\n{page.url}")

        input("ENTER to close...")
        await browser.close()

asyncio.run(main())