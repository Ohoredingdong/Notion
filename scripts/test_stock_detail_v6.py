"""Focused browser regression for the user-approved detailed stock analysis.
Uses the real repository JSON over a local HTTP server. Never places orders.
"""
from __future__ import annotations

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("detail-v6-artifacts")
OUT.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8765/stock-value-radar.html"
REPORT = {"screenshots": [], "checks": []}


def require(name: str, condition: bool, detail: object = "") -> None:
    REPORT["checks"].append({"name": name, "pass": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{name}: {detail}")


with sync_playwright() as play:
    browser = play.chromium.launch(headless=True)
    try:
        for width, height in [(1366, 768), (1440, 900), (1920, 1080), (390, 844)]:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_function(
                "() => (window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length || 0) > 0",
                timeout=50000,
            )
            home_cards = page.locator(".fx-v5-markets .nr-index").count()
            require(f"{width}: home index cards unchanged", home_cards == 4, home_cards)
            page.locator('.fx-nav [data-nr-screen="stockdetail"]').first.click()
            page.locator(".fx-detail-v6").wait_for(timeout=20000)
            require(f"{width}: three top cards",
                    page.locator(".fx-detail-v6 .fx-detail-upper > .fx-panel").count() == 3)
            require(f"{width}: three metric cards",
                    page.locator(".fx-detail-v6 .fx-detail-mid > .fx-panel").count() == 3)
            require(f"{width}: three bottom cards",
                    page.locator(".fx-detail-v6 .fx-detail-lower > .fx-panel").count() == 3)
            require(f"{width}: all 16 indicator definitions",
                    page.locator(".fx-detail-v6 .fx-d-help").count() == 16 and
                    page.locator(".fx-detail-v6 .fx-d-plain").count() == 16)
            decision = page.locator('.fx-detail-v6 [data-investment-assessment="four-questions"]')
            require(f"{width}: four independent investment questions",
                    decision.count() == 1 and decision.locator(".fx-d-fact").count() == 4)
            labels = decision.locator(".fx-d-fact-label > span:first-child").all_text_contents()
            require(f"{width}: direction, valuation, downside and verdict are separate",
                    all(any(word in label for label in labels)
                        for word in ("AI 상승", "지금 가격", "상승여력", "최종 투자")),
                    labels)
            require(f"{width}: no fabricated buy probability",
                    "매수 성공률이 아닙니다" in page.locator(".fx-decision-panel").inner_text())
            require(f"{width}: original-source price chart present",
                    page.locator(".fx-detail-v6 .fx-detail-primary .fx-chart-svg").count() == 1)
            require(f"{width}: stock identity and price preserved",
                    page.locator(".fx-detail-v6 .fx-d-security strong").count() == 1 and
                    bool(page.locator(".fx-detail-v6 .fx-d-quote strong").inner_text().strip()))
            geometry = page.evaluate("""() => {
                const rect = s => [...document.querySelectorAll(s)].map(n => {
                  const b=n.getBoundingClientRect();
                  return {left:b.left,top:b.top,right:b.right,bottom:b.bottom,width:b.width,height:b.height};
                });
                return {
                  pageWidth:document.documentElement.scrollWidth, viewportWidth:innerWidth,
                  pageHeight:document.documentElement.scrollHeight, viewportHeight:innerHeight,
                  upper:rect('.fx-detail-v6 .fx-detail-upper > .fx-panel'),
                  mid:rect('.fx-detail-v6 .fx-detail-mid > .fx-panel'),
                  lower:rect('.fx-detail-v6 .fx-detail-lower > .fx-panel'),
                  footer:rect('.fx-detail-v6 > .fx-flowbar')
                };
            }""")
            require(f"{width}: no horizontal page overflow",
                    geometry["pageWidth"] <= width + 3, geometry)
            require(f"{width}: visible panels have meaningful width",
                    all(x["width"] > 180 for x in geometry["upper"]), geometry)
            if width >= 1180:
                require(f"{width}: top cards in one row",
                        max(x["top"] for x in geometry["upper"]) -
                        min(x["top"] for x in geometry["upper"]) < 3, geometry)
                require(f"{width}: detail fits one viewport",
                        geometry["pageHeight"] <= height + 3 and
                        geometry["lower"][-1]["bottom"] <= height + 2, geometry)
            page.locator('.fx-detail-v6 [data-fx-period="1W"]').click()
            require(f"{width}: chart period control works",
                    "active" in (page.locator('.fx-detail-v6 [data-fx-period="1W"]').get_attribute("class") or ""))
            page.locator('.fx-detail-v6 [data-fx-period="1M"]').click()
            require(f"{width}: period returns to one month",
                    "active" in (page.locator('.fx-detail-v6 [data-fx-period="1M"]').get_attribute("class") or ""))
            require(f"{width}: no JavaScript runtime error", not errors, errors)
            screenshot = OUT / f"stock-detail-v6-{width}x{height}.png"
            page.screenshot(path=str(screenshot), full_page=True)
            REPORT["screenshots"].append(str(screenshot))
            page.close()
        # End-to-end: inspect ACTUAL stored forecast records, not fabricated fixtures.
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_function(
                "() => !!window.StockRadarV2Bridge?.snapshot()?.data?.direction?.records?.length",
                timeout=45000,
            )
            sample = page.evaluate("""() => {
                const d=window.StockRadarV2Bridge.snapshot().data;
                const records=d.direction.records||[],companies=d.raw?.companies||[],now=Date.now();
                const norm=s=>String(s||'').toUpperCase().replace(/\.(KS|KQ)$/,'');
                const valid=records.filter(r=>{
                    const p=r.probabilities||{},issued=Date.parse(r.issued_at||''),
                      start=Date.parse(r.target?.start||''),end=Date.parse(r.target?.end||'');
                    return r.status==='research_prediction'&&issued<=start&&issued<=now+300000&&
                     end>now&&start<end&&['up','flat','down'].every(k=>typeof p[k]==='number'&&p[k]>=0&&p[k]<=1)&&
                     Math.abs(p.up+p.flat+p.down-1)<.025;
                });
                const candidate=companies.find(c=>valid.some(r=>norm(c.symbol)===norm(r.symbol)));
                return {forecastCount:records.length,generatedAt:d.direction.generated_at,
                        firstActiveSymbol:candidate?.symbol||null,
                        forecastStatus:d.direction.status};
            }""")
            require("Forecast JSON loaded with actual issuer coverage",
                    sample["forecastCount"] >= 1 and bool(sample["generatedAt"]), sample)
            if sample["firstActiveSymbol"]:
                page.evaluate("(symbol)=>window.StockRadarV2Bridge.select(symbol)",
                              sample["firstActiveSymbol"])
                page.locator('.fx-nav [data-nr-screen="stockdetail"]').click()
                require("Real valid forecast produces a rendered AI probability",
                        page.locator(".fx-d-ai-body .fx-ai-heading strong").count()==1 and
                        "%" in page.locator(".fx-d-ai-body .fx-ai-heading strong").inner_text(),
                        sample)
            page.evaluate("() => window.StockRadarV2Bridge.select('005930')")
            page.locator(".fx-nav [data-nr-screen='stockdetail']").click()
            require("Samsung AI pane is never blank",
                    bool(page.locator(".fx-d-ai-body").inner_text().strip()))
            if page.locator(".fx-d-ai-empty").count():
                require("No-signal view explains actual model coverage",
                        "AI 모델" in page.locator(".fx-d-ai-empty").inner_text())
                if sample["firstActiveSymbol"]:
                    require("No-signal panel navigates to a working signal",
                            page.locator(".fx-d-ai-empty [data-fx-filter='ai']").count()==1)
                    page.locator(".fx-d-ai-empty [data-fx-filter='ai']").click()
                    require("One-click switch selects a ticker with a valid signal",
                            page.locator(".fx-d-ai-body .fx-ai-heading strong").count()==1)
            page.goto(BASE+"?stock=005930&screen=stockdetail", wait_until="domcontentloaded")
            page.locator(".fx-detail-v6").wait_for(timeout=45000)
            page.wait_for_function(
                "() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length",
                timeout=45000)
            require("Direct Samsung detail link opens the correct actual stock",
                    "삼성전자" in page.locator(".fx-detail-v6 .fx-detail-intro h2").inner_text())
            require("Direct detail link renders its model status without blank panel",
                    bool(page.locator(".fx-detail-v6 .fx-d-ai-body").inner_text().strip()))
        finally:
            page.close()
    finally:
        browser.close()

(OUT / "report.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Stock detail V6 browser acceptance: {len(REPORT['checks'])} checks passed")
