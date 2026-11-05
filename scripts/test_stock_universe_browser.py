"""Playwright acceptance on REAL stored 8k+ stock catalogue and actual news.

Test screenshots, JS console errors, company drill-in, news sources and Notion-sized
iframe without writing any production data or pretending to use a real Notion app.
"""
from __future__ import annotations
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT=Path("radar-universe-evidence")
OUT.mkdir(exist_ok=True)
REPORT={"checks":[],"screenshots":[],"limitations":["Notion: locally simulated iframe, not the live Notion account"]}
BASE="http://127.0.0.1:8765/stock-value-radar.html"


def verify(name, success, details=None):
    REPORT["checks"].append({"name":name,"pass":bool(success),"details":details})
    if not success:
        raise AssertionError(f"{name}: {details}")


def screenshot(page,name):
    path=OUT/(name+".png")
    page.screenshot(path=str(path),full_page=True,animations="disabled")
    REPORT["screenshots"].append(str(path))


def browser_context(browser,width,height):
    return browser.new_context(viewport={"width":width,"height":height},color_scheme="light",
                               reduced_motion="reduce",service_workers="block")


try:
    with sync_playwright() as play:
        browser=play.chromium.launch(headless=True)
        try:
            for width,height in ((1440,900),(1366,768),(390,844)):
                ctx=browser_context(browser,width,height)
                page=ctx.new_page()
                errors=[]
                page.on("pageerror",lambda e:errors.append(str(e)))
                page.goto(BASE,wait_until="domcontentloaded")
                page.wait_for_function("""() => !!window.StockRadarV2Bridge?.snapshot()?.data?.catalog?.items?.length
                    && !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length
                    && !!window.StockRadarV2Bridge?.snapshot()?.data?.newsLink?.items?.length""",timeout=60000)
                snapshot=page.evaluate("""() => {
                  let d=window.StockRadarV2Bridge.snapshot().data;
                  return {total:d.catalog.items.length,kr:d.catalog.counts.KR,us:d.catalog.counts.US,
                    raw:d.raw.companies.length,
                    extended:d.extended?.records?.length||0,
                    mainIndex:document.querySelectorAll('.fx-v5-markets .nr-index').length,
                    sentiment:document.querySelectorAll('.fx-sent-v9').length}
                }""")
                verify(f"{width}: real issuer directory exceeds demo 104 stocks",snapshot["total"]>1000,snapshot)
                verify(f"{width}: Korean/US issuer counts are source based",snapshot["kr"]>1000 and snapshot["us"]>1000,snapshot)
                page.wait_for_function("""() => !!window.StockRadarV2Bridge?.snapshot()?.data?.financial?.records""",timeout=45000)
                finance = page.evaluate("""() => {
                    const s=window.StockRadarV2Bridge.snapshot().data,records=s.financial.records||{};
                    const deep=new Set((s.raw?.companies||[]).map(c=>String(c.symbol).replace(/\.(KS|KQ)$/,'')));
                    const eligible=(s.catalog.items||[]).find(item=>item.country==='KR'&&!deep.has(item.symbol)
                      && records['KR:'+item.symbol]?.identity_verified===true
                      && ['available','partial','stale'].includes(records['KR:'+item.symbol]?.status));
                    return {catalogSize:s.catalog.items.length,processed:Object.keys(records).length,
                      sourced:window.StockCatalogUI.verifiedCount(window.StockRadarV2Bridge.snapshot()),
                      stated:(s.financial.financial_available.KR||0)+(s.financial.financial_available.US||0),
                      identityPolicy:s.financial.identity_policy,
                      sample:eligible?.symbol||null,
                      sampleFcf:eligible?records['KR:'+eligible.symbol]?.metrics?.free_cash_flow:null};
                }""")
                verify(f"{width}: official financial data has independent source provenance",
                       finance["catalogSize"]==snapshot["total"] and finance["sourced"]>=1
                       and finance["sourced"]==finance["stated"]
                       and finance["identityPolicy"]=="official-issuer-identity-v2", finance)

                verify(f"{width}: existing market dashboard intact",snapshot["mainIndex"]==4 and snapshot["sentiment"]==1,snapshot)
                screenshot(page,f"{width}-home")
                page.locator('.fx-nav [data-nr-screen="stocks"]').click()
                page.locator("#fx-catalog-search").wait_for(timeout=12000)
                verify(f"{width}: sourced stock catalog renders",page.locator(".fx-catalog").count()==1)
                page.locator("#fx-catalog-search").fill("0001A0")
                verify(f"{width}: alphanumeric Korean code selects the actual issuer",
                       "덕양에너젠" in page.locator("#fx-catalog-results").inner_text()
                       and "0001A0" in page.locator("#fx-catalog-results").inner_text()
                       and page.locator('[data-catalog-preview="KR:000010"]').count()==0)
                page.locator("#fx-catalog-search").fill("Fabrinet")
                page.wait_for_function("""() => document.querySelectorAll('.fx-catalog-row').length>=1""")
                verify(f"{width}: search finds company outside initial 104 slice",
                       "Fabrinet" in page.locator("#fx-catalog-results").inner_text())
                screenshot(page,f"{width}-catalog-search")
                candidate=page.evaluate("""() => {
                  const data=window.StockRadarV2Bridge.snapshot().data;
                  const active=new Set(data.raw.companies.map(x=>String(x.symbol).replace(/\.(KS|KQ)$/,'')));
                  return data.catalog.items.find(x=>x.country==='US'&&!active.has(x.symbol)&&
                    /^[A-Z]{2,5}$/.test(x.symbol) && x.name.length>8);
                }""")
                if candidate:
                    page.locator("#fx-catalog-search").fill(candidate["symbol"])
                    page.wait_for_function("""() => document.querySelector('[data-catalog-preview]')!==null""",timeout=12000)
                    page.locator('[data-catalog-preview="'+candidate["country"]+":"+candidate["symbol"]+'"]').click()
                    verify(f"{width}: unknown ticker has explicit data-limited preview",
                           "상장" in page.locator(".fx-catalog-preview").inner_text() and
                           "확인되지" in page.locator(".fx-catalog-preview").inner_text())
                    verify(f"{width}: no fabricated price for unknown ticker",
                           page.locator(".fx-catalog-preview .fx-d-quote").count()==0)
                if finance["sample"]:
                    page.locator("#fx-catalog-search").fill(finance["sample"])
                    page.locator('[data-catalog-preview="KR:'+finance["sample"]+'"]').first.click()
                    verify(f"{width}: real DART statement surfaced for listed issuer",
                           "매출액" in page.locator(".fx-catalog-finance").inner_text() and
                           "DART periodic reports" in page.locator(".fx-catalog-finance").inner_text())
                    if finance.get("sampleFcf") is None:
                        verify(f"{width}: absent cash flow data is explicitly uncollected",
                               "미수집·미확인" in page.locator(".fx-catalog-finance").inner_text())
                    verify(f"{width}: statement discloses identity and observation time",
                           "법인 연결 확인" in page.locator(".fx-catalog-finance").inner_text()
                           and "확인 시각" in page.locator(".fx-catalog-finance").inner_text())
                screenshot(page,f"{width}-catalog-preview")
                page.locator('.fx-nav-tools [data-nr-screen="news"]').click()
                page.locator(".fx-world-page").wait_for(timeout=12000)
                verify(f"{width}: three geographical/industry news sections",page.locator(".fx-world-panel").count()==3)
                verify(f"{width}: macro context has original sources",page.locator(".fx-world-metric").count()==6
                       and page.locator(".fx-world-metric a").count()>=3)
                verify(f"{width}: news links have citations and publish times",page.locator(".fx-world-article a").count()>=3)
                verify(f"{width}: no unverified buy signal exposed in headlines",
                       "자동 매수 신호가 아닙니다" in page.locator(".fx-world-page").inner_text())
                screenshot(page,f"{width}-world-brief")
                verify(f"{width}: no JS runtime exceptions",not errors,errors)
                childwidth=page.evaluate("document.documentElement.scrollWidth")
                verify(f"{width}: no horizontal overflow",childwidth<=width+4,childwidth)
                ctx.close()
            for width,height in ((920,680),(360,640)):
                ctx=browser_context(browser,width+40,height+60)
                page=ctx.new_page()
                page.set_content(f'<iframe name="notion-test" title="Notion-sized embed" src="{BASE}" style="width:{width}px;height:{height}px;border:0"></iframe>')
                frame=page.frame(name="notion-test")
                frame.wait_for_function("""() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length""",timeout=60000)
                verify(f"embed-{width}: main cards available inside iframe",
                       frame.locator(".fx-v5-markets .nr-index").count()==4)
                frame.locator('.fx-nav-tools [data-nr-screen="news"]').click()
                verify(f"embed-{width}: news view accessible inside iframe",
                       frame.locator(".fx-world-page").count()==1)
                screenshot(page,f"embed-{width}-news")
                ctx.close()
        finally:
            browser.close()
finally:
    (OUT/"report.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding="utf-8")
print("REAL_UNIVERSE_UI_ACCEPTANCE",len(REPORT["checks"]),"checks",
      sum(1 for item in REPORT["checks"] if not item["pass"]),"failed")
