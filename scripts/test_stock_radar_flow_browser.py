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
                grid: (() => { let r=document.querySelector(".fx-v5-main").getBoundingClientRect();return {bottom:r.bottom,top:r.top,height:r.height}; })(),
                visible: [...document.querySelectorAll(".fx-v5-main>.fx-list-panel, .fx-v5-main>.fx-v5-central, .fx-v5-main>.fx-v5-aside")].length,
                stage: document.querySelector(".fx-stage-home")?.getBoundingClientRect().height
            })""")
            check(f"Desktop {width}x{height}: no outer page scroll",
                info["html"] <= height + 3 and info["body"] <= height + 3,
                json.dumps(info,ensure_ascii=False))
            check(f"Desktop {width}x{height}: grid fits screen",
                0 < info["grid"]["top"] < info["grid"]["bottom"] <= height - 3,
                json.dumps(info,ensure_ascii=False))
            check(f"Desktop {width}x{height}: genuine chart drawn",
                page.locator(".fx-v5-chartarea .fx-chart-svg polyline").count() > 0,
                "Price chart should not disappear when the current snapshot is newer than the history file")
            check(f"Desktop {width}x{height}: no overflowing insight cards",
                page.evaluate("""() => {
                    const main=document.querySelector('.fx-v5-main').getBoundingClientRect();
                    const center=document.querySelector('.fx-v5-cockpit').getBoundingClientRect();
                    const aside=document.querySelector('.fx-v5-aside').getBoundingClientRect();
                    return center.bottom<=main.bottom+3&&aside.bottom<=main.bottom+3&&center.width>400;
                }"""), "Center and right rail must fit inside research grid")
            check(f"Desktop {width}x{height}: panels rendered",
                page.locator(".fx-v5-main .fx-list-panel").count() == 1 and
                page.locator(".fx-v5-main .fx-v5-cockpit").count() == 1 and
                page.locator(".fx-v5-main .fx-v5-aside").count() == 1)
            check(f"Desktop {width}x{height}: no page errors", not errors, str(errors))
            for target, selector in [("detail", "stockdetail"),("scenario", "scenario")]:
                page.locator(f'.fx-nav [data-nr-screen="{selector}"]').click()
                bounds = page.evaluate("""() => ({
                    html:document.documentElement.scrollHeight,
                    body:document.body.scrollHeight,
                    inner:innerHeight,
                    visible:document.querySelector('.fx-stage-other')?.getBoundingClientRect().bottom,
                    content:document.querySelector('.fx-detail-content,.fx-scenario-v4')?.getBoundingClientRect().bottom
                })""")
                check(f"Desktop {width}x{height}: {target} one-screen fit",
                    bounds["html"] <= height + 3 and bounds["body"] <= height + 3 and
                    0 < bounds["content"] <= height+3,
                    json.dumps(bounds,ensure_ascii=False))
                screenshot(page,f"radar-flow-{target}-{width}x{height}.png")
            page.locator('.fx-nav [data-nr-screen="home"]').click()
            screenshot(page, f"radar-flow-{width}x{height}.png")
            page.close()

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda x: errors.append(str(x)))
        settle(page)
        check("No legacy UI rail",
            page.locator(".nr-rail").count() == 0 and
            page.locator(".fx-topbar").count() == 1)
        assets=page.locator("script[src]").evaluate_all(
            "(nodes) => nodes.map(n => n.getAttribute('src'))")
        expected_modules=("stock-radar-clean-bridge.js","stock-radar-flow-v2.js",
                          "stock-catalog-ui.js","stock-world-brief.js")
        check("Four approved V5 runtime modules, without outdated scripts",
            len(assets)==4 and all(sum(name in x for x in assets)==1
                                   for name in expected_modules),
            str(assets))
        check("Market index cards",
            page.locator(".fx-v5-markets .nr-index").count() == 4)
        check("Market strip has separate spacing before analysis",
            page.evaluate("""() => {
                const upper=document.querySelector('.fx-v5-marketline')?.getBoundingClientRect();
                const lower=document.querySelector('.fx-v5-main')?.getBoundingClientRect();
                return upper && lower && lower.top-upper.bottom>=10;
            }"""), "Expected visible vertical gap between index strip and AI/research panels")
        check("Initial sentiment card has provider attribution and session date",
            page.locator(".fx-sent-v9 .fx-sent-v9-foot a").count()==1 and
            bool(page.locator(".fx-sent-v9 .fx-sent-v9-foot span").inner_text().strip()))
        page.locator('[data-fx-sentiment-next]').click()
        check("Arrow switches to Korean market sentiment",
            page.locator(".fx-sent-v9.is-korea").count()==1 and
            "코스닥" in page.locator(".fx-sent-v9.is-korea").inner_text())
        check("Korean sentiment source attribution and session date",
            "koreafeargreed.com" in (page.locator(".fx-sent-v9.is-korea .fx-sent-v9-foot a").get_attribute("href") or "") and
            page.locator(".fx-sent-v9 .fx-sent-v9-foot span").count()==1)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length")
        check("Korean choice persists after reload",
            page.locator(".fx-sent-v9.is-korea").count()==1)
        page.locator('[data-fx-sentiment-next]').click()
        check("Arrow switches back to US CNN sentiment",
            page.locator(".fx-sent-v9.is-us").count()==1)
        check("Signal probability labels",
            page.locator(".fx-list-panel .fx-row").count() > 0 and
            page.locator(".fx-v5-cockpit .fx-v5-ai").count() == 1)
        check("Approved reference dashboard has four right panels",
            page.locator(".fx-v5-aside .fx-v5-sidecard").count()==4)
        check("Approved reference dashboard has three aligned analysis groups",
            page.locator(".fx-v5-cockpit .fx-v5-toptrio>div").count()==3 and
            page.locator(".fx-v5-cockpit .fx-v5-middle>section").count()==3 and
            page.locator(".fx-v5-cockpit .fx-v5-bottom>section").count()==3)
        check("Real moving average chart not fictional OHLC",
            page.locator(".fx-v5-chartarea .fx-chart-svg").count()==1 and
            "MA20" in page.locator(".fx-v5-chartarea .fx-v5-ma-legend").inner_text() and
            page.locator(".fx-v5-chartarea .fx-chart-svg polyline").count()>=2)
        check("Research status labelled honestly",
            "연구용" in page.locator(".fx-v5-cockpit .fx-v5-ai").inner_text())
        check("Strict checklist cannot be mistaken for an investment approval",
            "매수 성공 확률 아님" in page.locator(".fx-v5-sidecheck .fx-v5-footnote").inner_text() and
            "실사" in page.locator(".fx-v5-sidecheck .fx-v5-footnote").inner_text())
        check("Index card discloses historical sparkline date",
            all(any(label in x for label in ("일봉","추이","지표 저장값")) for x in page.locator(".fx-v5-markets .nr-index .nr-sub").all_text_contents()))
        page.locator('.fx-nav [data-nr-screen="stocks"]').click()
        check("Stock list opens",page.locator(".fx-page-grid .fx-row").count() > 0)
        page.locator('[data-rf-market="NASDAQ"]').first.click()
        check("NASDAQ filter yields at least one stock",
            page.locator(".fx-row[data-nr-select]").count() > 0)
        page.evaluate("window.StockRadarV2Bridge.select('005930')")
        check("Cross-market selection automatically reveals chosen ticker",
            page.locator('.fx-row[data-nr-select="005930"]').count()==1 and
            page.locator('[data-rf-market="ALL"].active').count()==1,
            "Explicit selection must clear incompatible NASDAQ market filter")
        page.locator('[data-rf-market="NASDAQ"]').first.click()
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
            symbol in page.locator(".fx-intro h2").inner_text() and page.locator(".fx-detail-content").count()==1)
        check("Deep financial analysis now integrated",
            page.locator(".fx-detail-mid .fx-panel").count() == 3 and
            page.locator(".fx-detail-lower .fx-panel").count() == 3 and
            page.locator(".fx-detail-v4").count() == 1)
        check("Deep analysis uses actual price chart",
            page.locator(".fx-detail-primary .fx-chart-svg polyline").count() >= 1)
        screenshot(page, "radar-flow-integrated-research.png")
        page.locator('.fx-nav [data-nr-screen="scenario"]').click()
        check("Scenario appears without fake future curve",
            page.locator(".fx-scenario-v4").count() == 1 and
            "미래 경로" in page.locator(".fx-scenario-v4").inner_text() and
            page.locator(".fx-scenario-option").count() == 3)
        check("Target bands are internally consistent or explicitly unavailable",
            page.evaluate("""() => {
                const list=window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies||[];
                const current=window.StockRadarV2Bridge?.snapshot()?.selected;
                const c=list.find(x=>x.symbol===current);
                if(!c || !c.targets)return true;
                const {low,median,high}=c.targets;
                const complete=[low,median,high].every(v=>typeof v==="number"&&Number.isFinite(v));
                return !complete || (low<=median && median<=high) ||
                  document.querySelector(".fx-scenario-v4")?.textContent?.includes("순서 불일치");
            }"""))
        check("All three scenario alternatives and model probabilities",
            page.locator(".fx-scenario-options .fx-scenario-option").count() == 3 and
            page.locator(".fx-scenario-ai-panel .fx-ai-card").count() == 1)
        screenshot(page, "radar-flow-three-scenarios.png")
        page.locator('.fx-nav [data-nr-screen="performance"]').click()
        check("Prediction outcome results visible",
            page.locator(".fx-audit").count() == 1)
        check("Evaluation disclaimer",
            "수익성 미입증" in page.locator(".fx-validation-grid").inner_text() and
            "매수 성공률" in page.locator(".fx-validation-grid").inner_text())
        check("Evidence thresholds and source-audit state are explicit",
            page.locator(".fx-validation-grid .nr-validation-note").count() == 1 and
            "Brier 개선" in page.locator(".fx-validation-grid").inner_text() and
            "정확도 감사" in page.locator(".fx-validation-grid").inner_text())
        check("Independent evaluated sample distinguished from raw outcomes",
            "독립 평가" in page.locator(".fx-table-hint").inner_text() and
            "두 모수" in page.locator(".fx-table-hint").inner_text())

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
        page.locator("#radar-paper-qty").fill("3")
        page.locator("#radar-paper-cost").fill("120")
        page.locator("#radar-paper-form button[type=submit]").click()
        check("Repeated paper buys use weighted average cost",
            page.evaluate("""() => {
                const values=JSON.parse(localStorage.getItem("radar-paper-holdings-v2") || "[]");
                return values.length===1 && values[0].qty===5 && Math.abs(values[0].cost-112)<1e-6;
            }"""))
        page.locator("[data-nr-paper-remove]").click()
        check("Paper holdings removed",
            page.locator(".nr-paper-overview").count()==0)
        page.locator('.fx-nav [data-nr-screen="home"]').click()
        check("Home round-trip and reset",
            page.locator(".fx-v5-main").count()==1 and
            page.locator("#fx-search-input").input_value()=="")
        # Fail a data endpoint and confirm refresh remains usable with last known-good snapshot.
        page.route("**/stock-opportunity-data.json*", lambda route: route.abort())
        page.locator("[data-fx-refresh]").click()
        page.wait_for_function(
            "() => (document.querySelector('#source-status')?.textContent || '').includes('직전 정상 자료 유지')",
            timeout=25000,
        )
        check("Failed refresh keeps the last valid market snapshot",
            page.locator(".fx-v5-cockpit").count()==1 and
            page.locator(".fx-row[data-nr-select]").count()>0)
        check("Failed refresh visibly warns about incomplete data",
            "raw 조회 실패" in page.locator("#source-status").inner_text())
        page.unroute("**/stock-opportunity-data.json*")
        page.evaluate("""() => {
            const snap=window.StockRadarV2Bridge.snapshot();
            snap.data.raw.companies.push({
                symbol:"TEST-BAD",name:"Bad Forecast Sample",market:"US",
                currency:"USD",price:100,price_session:"2026-11-02"
            });
            snap.data.direction.records.push({
                symbol:"TEST-BAD",mode:"daily",status:"research_prediction",
                direction:"up",issued_at:"2026-11-02T01:00:00Z",
                target:{end:"2026-11-05T01:00:00Z"},
                probabilities:{up:0.9,flat:0.8,down:0.7}
            });
            window.StockRadarV2Bridge.select("TEST-BAD");
        }""")
        check("Malformed model probability is blocked and explained",
            "예측 확률·발행시각 검증 실패" in page.locator(".fx-v5-ai").inner_text() and
            "90%" not in page.locator(".fx-v5-ai").inner_text())
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length")
        page.evaluate("window.StockRadarV2Bridge.select('NVDA')")
        page.locator('[data-rf-market="NASDAQ"]').first.click()
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length")
        check("Selected ticker and market survive reload",
            page.evaluate("""() => {
                const state=window.StockRadarV2Bridge.snapshot();
                return state.selected==="NVDA" && state.market==="NASDAQ";
            }"""))
        check("Persisted ticker is shown in the visible cockpit",
            "NVIDIA" in page.locator(".fx-v5-stocktitle").inner_text())

        check("Interaction no page exceptions",not errors,str(errors))
        screenshot(page, "radar-flow-functional-desktop.png")
        page.close()

        mobile = browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        settle(mobile)
        size = mobile.evaluate("() => ({scroll:document.documentElement.scrollWidth,view:innerWidth})")
        check("Mobile no horizontal page overflow",size["scroll"] <= size["view"]+3,str(size))
        check("Mobile cards retained",mobile.locator(".fx-v5-main .fx-v5-cockpit").count()==1)
        screenshot(mobile,"radar-flow-mobile-390.png")
        mobile.close()
    finally:
        browser.close()

REPORT["pass"] = all(c["pass"] for c in REPORT["checks"])
(OUT/"ux-flow-report.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"pass":REPORT["pass"],"checks":len(REPORT["checks"]),"screenshots":REPORT["screenshots"]},ensure_ascii=False))
