"""Canonical radar's extended scenario and stored-record regression.

Retains the existing flow, scenario, watch-condition and paper-holding checks.
Current runtime/selector corrections were reviewed against the existing
0e46462d development-safety work; no application logic or market data is changed.
Normal responses use exact captured checkout JSON; malformed-distribution input
is explicitly confined to one isolated negative-control browser state.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import threading
import traceback
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
from test_stock_radar_canonical_browser import QuietHandler, fixtures, sha, source_fingerprints

BASE = ""
OUT = None
REPORT = None
CAPTURED = {}
CLOCK = None
ORIGIN = ""


def check(name: str, ok: bool, detail=""):
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


def open_page(browser, **options):
    page = browser.new_page(**options)
    page.clock.set_fixed_time(CLOCK)
    def route(request):
        parsed = urlparse(request.request.url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if request.request.method not in {"GET", "HEAD"} or origin != ORIGIN:
            REPORT["blocked_requests"].append({"url": origin+parsed.path, "method": request.request.method})
            request.abort()
            return
        name = parsed.path.removeprefix("/")
        if name in CAPTURED:
            REPORT["data_requests"].append({"file": name, "sha256": sha(CAPTURED[name])})
            request.fulfill(status=200, content_type="application/json", body=CAPTURED[name])
        elif name.endswith((".json", ".jsonl")):
            REPORT["blocked_requests"].append({"url": parsed.path, "reason": "Unrecorded data endpoint"})
            request.abort()
        else:
            request.continue_()
    page.route("**/*", route)
    return page


def exercise(browser):
    for width, height in [(1366, 768), (1440, 900), (1920, 1080)]:
        page = open_page(browser, viewport={"width": width, "height": height})
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

    page = open_page(browser, viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda x: errors.append(str(x)))
    settle(page)
    check("No legacy UI rail",
        page.locator(".nr-rail").count() == 0 and
        page.locator(".fx-topbar").count() == 1)
    approved_scripts = {
        "./assets/stock-radar-clean-bridge.js",
        "./assets/stock-radar-flow-v2.js",
        "./assets/stock-forecast.js",
        "./assets/stock-forecast-learning.js",
        "./assets/stock-forecast-directions.js",
        "./assets/stock-forecast-autopilot.js",
    }
    runtime_scripts = page.locator("script[src]").evaluate_all(
        "elements => elements.map(el => el.getAttribute('src').split('?')[0])"
    )
    check("Only approved current runtime scripts on main URL",
        len(runtime_scripts)==len(approved_scripts) and set(runtime_scripts)==approved_scripts,
        "Unexpected or duplicate runtime script: " + json.dumps(runtime_scripts))
    check("Market index cards",
        page.locator(".fx-v5-markets .nr-index").count() == 4)
    check("Market strip has separate spacing before analysis",
        page.evaluate("""() => {
            const upper=document.querySelector('.fx-v5-marketline')?.getBoundingClientRect();
            const lower=document.querySelector('.fx-v5-main')?.getBoundingClientRect();
            return upper && lower && lower.top-upper.bottom>=10;
        }"""), "Expected visible vertical gap between index strip and AI/research panels")
    check("Initial sentiment card is sourced",
        page.locator(".fx-sent-v9 .fx-sent-v9-foot a").count()==1)
    page.locator('[data-fx-sentiment-next]').click()
    check("Arrow switches to Korean market sentiment",
        page.locator(".fx-sent-v9.is-korea").count()==1 and
        "코스닥" in page.locator(".fx-sent-v9.is-korea").inner_text())
    check("Korean sentiment source attribution and after-close date",
        "koreafeargreed.com" in (page.locator(".fx-sent-v9.is-korea a").get_attribute("href") or "") and
        page.locator(".fx-sent-v9-foot").count()==1)
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
    checklist_text = page.locator(".fx-v5-sidecheck").inner_text()
    check("Strict checklist discloses evidence coverage rather than buy-success probability",
        "AI 방향과 별도" in checklist_text and "수익·매수 성공 확률 아님" in checklist_text)
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
    search_rows = page.locator(".fx-row[data-nr-select]")
    check("Search keeps selected ticker and only matching results",
        search_rows.count() > 0 and
        page.locator(f'.fx-row[data-nr-select="{symbol}"]').count() == 1 and
        symbol in page.locator(".fx-focus-head").inner_text() and
        all(symbol.lower() in text.lower() for text in search_rows.all_text_contents()),
        "Ticker/name substring searches can legitimately match more than one company")
    page.locator(".fx-focus .fx-focus-actions [data-nr-detail]").click()
    check("Details preserve selected ticker",
        symbol in page.locator(".fx-d-security").inner_text() and
        page.evaluate("() => window.StockRadarV2Bridge.snapshot().selected")==symbol and
        page.locator(".fx-detail-content").count()==1)
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
    # Synthetic malformed record is confined to this isolated browser test.
    # Use a valid current target window so only the bad distribution is exercised.
    page.evaluate("""() => {
        const snap=window.StockRadarV2Bridge.snapshot(),now=Date.now();
        snap.data.raw.companies.push({
            symbol:"TEST-BAD",name:"Bad Forecast Sample",market:"US",
            currency:"USD",price:100,price_session:new Date(now).toISOString().slice(0,10)
        });
        snap.data.direction.records.push({
            symbol:"TEST-BAD",mode:"daily",status:"research_prediction",
            direction:"up",issued_at:new Date(now-60000).toISOString(),
            target:{start:new Date(now+60000).toISOString(),end:new Date(now+3600000).toISOString()},
            probabilities:{up:0.9,flat:0.8,down:0.7}
        });
        window.StockRadarV2Bridge.select("TEST-BAD");
    }""")
    check("Malformed model probability is blocked and explained",
        "예측 확률·발행시각 검증 실패" in page.locator(".fx-v5-ai").inner_text() and
        page.locator(".fx-v5-ai .fx-prob-row").count()==0)
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

    mobile = open_page(browser, viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
    settle(mobile)
    size = mobile.evaluate("() => ({scroll:document.documentElement.scrollWidth,view:innerWidth})")
    check("Mobile no horizontal page overflow",size["scroll"] <= size["view"]+3,str(size))
    check("Mobile cards retained",mobile.locator(".fx-v5-main .fx-v5-cockpit").count()==1)
    screenshot(mobile,"radar-flow-mobile-390.png")
    mobile.close()



def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("/tmp/notion-radar-flow"))
    parser.add_argument("--browser-executable", default=os.environ.get("NOTION_BROWSER_EXECUTABLE") or os.environ.get("BROWSER_EXECUTABLE"))
    return parser.parse_args()


def main():
    global BASE, OUT, REPORT, CAPTURED, CLOCK, ORIGIN
    args = arguments()
    root, OUT = args.root.resolve(), args.output.resolve()
    if OUT == root or OUT.is_relative_to(root):
        raise SystemExit("Keep browser artifacts outside the source checkout")
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT = {"scope": "Extended canonical UI flows over exact captured checkout JSON. Isolated browser-only manual records and malformed-probability negative control. No live collection, publisher, notification or order.",
              "checks": [], "screenshots": [], "passed": False, "pass": False,
              "data_requests": [], "blocked_requests": [], "errors": []}
    server = None
    before = None
    try:
        CAPTURED, _raw, _primary, _stored, CLOCK = fixtures(root)
        REPORT["captured_data_sha256"] = {name: sha(value) for name, value in CAPTURED.items()}
        REPORT["clock"] = CLOCK.isoformat()
        before = source_fingerprints(root)
        REPORT["source_files_before"] = before
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        ORIGIN = f"http://127.0.0.1:{server.server_port}"
        BASE = ORIGIN + "/stock-value-radar.html"
        with sync_playwright() as api:
            launch = {"headless": True}
            if args.browser_executable:
                launch["executable_path"] = args.browser_executable
            browser = api.chromium.launch(**launch)
            try:
                exercise(browser)
            except Exception:
                pages = [page for context in browser.contexts for page in context.pages]
                if pages:
                    try:
                        screenshot(pages[-1], "failure.png")
                    except Exception:
                        pass
                raise
            finally:
                browser.close()
        check("No unrecorded external or writable requests", not REPORT["blocked_requests"], REPORT["blocked_requests"])
        REPORT["source_files_after"] = source_fingerprints(root)
        check("Source files stay frozen during the extended browser check", before == REPORT["source_files_after"])
        check("Captured source data is not rewritten by testing",
              all(sha((root/name).read_bytes()) == sha(value) for name,value in CAPTURED.items()))
        REPORT["passed"] = REPORT["pass"] = bool(REPORT["checks"]) and all(c["pass"] for c in REPORT["checks"])
    except Exception as error:
        REPORT["errors"].append(str(error))
        REPORT["traceback"] = traceback.format_exc()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    (OUT/"results.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+"\n")
    (OUT/"ux-flow-report.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"passed":REPORT["passed"],"checks":len(REPORT["checks"]),
                      "output":str(OUT),"errors":REPORT["errors"]},ensure_ascii=False),flush=True)
    return 0 if REPORT["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
