"""Browser acceptance test for the custom investment radar UX-flow dashboard.

Uses real saved JSON from this repository via its local HTTP server. Does not
place orders or assert live-trading profitability. Stores screenshots/artifacts.
"""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:8765/stock-value-radar.html"
OUT = Path("decision-browser-tests")
OUT.mkdir(exist_ok=True)
REPORT = {"checks": [], "screenshots": []}

def check(name: str, ok: bool, detail: str = ""):
    REPORT["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")

def settle(page):
    page.goto(BASE, wait_until="domcontentloaded")
    page.locator(".fx-topbar").wait_for(timeout=25000)
    page.wait_for_function(
        "() => !!(window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length)",
        timeout=35000,
    )

def screenshot(page, name):
    file = OUT / name
    page.screenshot(path=str(file), full_page=True)
    REPORT["screenshots"].append(str(file))

with sync_playwright() as play:
    browser = play.chromium.launch(headless=True)
    try:
        for width, height in [(1366, 768), (1440, 900), (1920, 1080)]:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda x: errors.append(str(x)))
            settle(page)
            info = page.evaluate("""() => ({
                html: document.documentElement.scrollHeight,
                body: document.body.scrollHeight,
                screen: innerHeight,
                grid: (() => { let r=document.querySelector(".fx-home-grid").getBoundingClientRect();return {bottom:r.bottom,top:r.top,height:r.height}; })(),
                visible: [...document.querySelectorAll(".fx-home-grid>.fx-panel, .fx-home-grid>.fx-aside")].length,
                stage: document.querySelector(".fx-stage-home")?.getBoundingClientRect().height
            })""")
            check(f"Desktop {width}x{height}: no outer page scroll",
                info["html"] <= height + 3 and info["body"] <= height + 3,
                json.dumps(info,ensure_ascii=False))
            check(f"Desktop {width}x{height}: grid fits screen",
                0 < info["grid"]["top"] < info["grid"]["bottom"] <= height - 18,
                json.dumps(info,ensure_ascii=False))
            check(f"Desktop {width}x{height}: panels rendered",
                page.locator(".fx-home-grid .fx-list-panel").count() == 1 and
                page.locator(".fx-home-grid .fx-focus").count() == 1 and
                page.locator(".fx-home-grid .fx-aside").count() == 1)
            check(f"Desktop {width}x{height}: no page errors", not errors, str(errors))
            screenshot(page, f"radar-flow-{width}x{height}.png")
            page.close()

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda x: errors.append(str(x)))
        settle(page)
        check("No legacy UI rail",
            page.locator(".nr-rail").count() == 0 and
            page.locator(".fx-topbar").count() == 1)
        check("Market index cards",
            page.locator(".fx-market-row .nr-index").count() == 4)
        check("Signal probability labels",
            page.locator(".fx-list-panel .fx-row").count() > 0 and
            page.locator(".fx-focus .fx-ai-card").count() == 1)
        check("Research status labelled honestly",
            "연구용" in page.locator(".fx-focus .fx-ai-card").inner_text())
        page.locator('.fx-nav [data-nr-screen="stocks"]').click()
        check("Stock list opens",page.locator(".fx-page-grid .fx-row").count() > 0)
        page.locator('[data-rf-market="NASDAQ"]').first.click()
        check("NASDAQ filter yields at least one stock",
            page.locator(".fx-row[data-nr-select]").count() > 0)
        first = page.locator(".fx-row[data-nr-select]").first
        symbol = first.get_attribute("data-nr-select")
        first.click()
        check("Selected stock appears in focus",symbol in page.locator(".fx-focus-head").inner_text())
        search = page.locator("#fx-search-input")
        search.fill(symbol)
        check("Search shows selected ticker",page.locator(".fx-row[data-nr-select]").count() == 1 and
              symbol in page.locator(".fx-focus-head").inner_text())
        page.locator(".fx-focus .fx-focus-actions [data-nr-detail]").click()
        check("Details preserve selected ticker",
            symbol in page.locator(".fx-intro h2").inner_text() and page.locator(".fx-detail-grid").count()==1)
        page.locator('.fx-nav [data-nr-screen="scenario"]').click()
        check("Scenario appears without fake future curve",
            page.locator(".fx-scenario-layout").count() == 1 and
            "미래 날짜별 가격 경로" in page.locator(".fx-scenario-layout").inner_text())
        page.locator('.fx-nav [data-nr-screen="performance"]').click()
        check("Prediction outcome results visible",
            page.locator(".fx-audit").count() == 1)
        check("Evaluation disclaimer",
            "실전 매매" in page.locator(".fx-validation-grid").inner_text())

        page.locator('.fx-nav [data-nr-screen="monitor"]').click()
        check("Manual condition form present",page.locator("#radar-rule-form").count() == 1)
        page.locator("#radar-rule-value").fill("1")
        page.locator("#radar-rule-form button[type=submit]").click()
        check("Condition was saved",
            page.locator(".nr-manual-row").count() == 1)
        page.reload(wait_until="domcontentloaded")
        page.locator(".fx-topbar").wait_for()
        page.locator('.fx-nav [data-nr-screen="monitor"]').click()
        check("Condition persists across reload",
            page.locator(".nr-manual-row").count()==1)
        page.locator("[data-nr-rule-remove]").click()
        check("Condition deletion",page.locator(".nr-manual-row").count()==0)

        page.locator('.fx-nav [data-nr-screen="portfolio"]').click()
        check("Paper portfolio input present",
            page.locator("#radar-paper-form").count()==1)
        page.locator("#radar-paper-qty").fill("2")
        page.locator("#radar-paper-cost").fill("100")
        page.locator("#radar-paper-form button[type=submit]").click()
        check("Paper holdings recorded",
            page.locator(".nr-table tbody tr").count()>=1 and
            page.locator(".nr-paper-overview").count()==1)
        page.locator("[data-nr-paper-remove]").click()
        check("Paper holdings removed",
            page.locator(".nr-paper-overview").count()==0)
        page.locator('.fx-nav [data-nr-screen="home"]').click()
        check("Home round-trip and reset",
            page.locator(".fx-home-grid").count()==1 and
            page.locator("#fx-search-input").input_value()=="")
        check("Interaction no page exceptions",not errors,str(errors))
        screenshot(page, "radar-flow-functional-desktop.png")
        page.close()

        mobile = browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        settle(mobile)
        size = mobile.evaluate("() => ({scroll:document.documentElement.scrollWidth,view:innerWidth})")
        check("Mobile no horizontal page overflow",size["scroll"] <= size["view"]+3,str(size))
        check("Mobile cards retained",mobile.locator(".fx-home-grid .fx-focus").count()==1)
        screenshot(mobile,"radar-flow-mobile-390.png")
        mobile.close()
    finally:
        browser.close()

REPORT["pass"] = all(c["pass"] for c in REPORT["checks"])
(OUT/"ux-flow-report.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"pass":REPORT["pass"],"checks":len(REPORT["checks"]),"screenshots":REPORT["screenshots"]},ensure_ascii=False))
