"""Regression checks for the canonical investment radar using saved JSON and Chromium.

Self-hosts a read-only checkout unless --base-url is supplied. Normal cases use
unmodified saved financial data. Fault cases replace only named HTTP responses
in browser memory and are labelled in report.json. Browser time is fixed to the
actual test start, not the data date. This does not verify live data freshness,
external providers, actual Notion permissions, trading quality, or deployment.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import tempfile
from threading import Thread
import traceback
from urllib.parse import urlparse

MAX_CARD_HEIGHT = 150
DATA_FILES = (
    "stock-opportunity-data.json", "stock-radar-chart-data.json",
    "stock-direction-forecast.json", "stock-forecast-learning.json",
    "stock-market-groups.json", "stock-event-risks.json",
    "stock-market-context.json", "stock-investment-cases.json",
    "stock-forecast-autopilot.json", "stock-entry-plan-summary.json",
    "stock-green-review-summary.json", "toss-live-config.json",
    "stock-forecast-outcomes.jsonl", "fear-greed-data.json",
    "stock-korea-fear-greed.json", "stock-radar-accuracy-audit.json",
    "stock-opportunity-summary.json", "stock-investment-cases-summary.json",
    "news-link-data.json", "stock-event-outlook.json",
)
UI_FILES = (
    "stock-value-radar.html", "stock-radar-dashboard.html",
    "assets/stock-radar-clean-bridge.js", "assets/stock-radar-flow-v2.js",
    "assets/stock-forecast.js", "assets/stock-forecast-learning.js",
    "assets/stock-forecast-directions.js", "assets/stock-forecast-autopilot.js",
)
PRESERVED_STORAGE = {
    "radar-v8-stars": '["005930"]',
    "radar-manual-rules-v2": '[{"symbol":"005930","kind":"gte","value":100000}]',
    "radar-paper-holdings-v2": '[{"symbol":"005930","qty":2,"cost":100000}]',
    "codex-qa-preservation-sentinel": "unrelated user preference — keep exactly",
}
SEED = {**PRESERVED_STORAGE, "radar-last-symbol-v5": '"005930"',
        "radar-last-market-v5": '"ALL"', "radar-sentiment-market": "us"}
SNAPSHOT = "() => window.StockRadarV2Bridge.snapshot()"


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-url", help="Existing local server root, e.g. http://127.0.0.1:8765/")
    parser.add_argument("--browser-executable", help="Existing Chromium; otherwise use Playwright's browser")
    parser.add_argument("--output", type=Path, help="Artifacts outside the checkout (default: new /tmp directory)")
    return parser.parse_args()


def fingerprints(root):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in (*DATA_FILES, *UI_FILES)}


def market_symbols(data, groups, market):
    """Independent expected membership from saved exchange metadata, not app helpers."""
    companies = data["companies"]
    if market == "ALL":
        return {str(c["symbol"]) for c in companies}
    members = groups.get("members", {})
    symbols = set()
    for company in companies:
        symbol = str(company["symbol"])
        source = company.get("source_symbol") or symbol
        entry = next((members[key] for key in (source, symbol, source + ".KS", source + ".KQ")
                      if key in members), {})
        venue = entry.get("venue") or {"KSC": "KOSPI", "KOE": "KOSDAQ", "NMS": "NASDAQ",
                                      "NGM": "NASDAQ", "NCM": "NASDAQ", "NYQ": "NYSE"}.get(company.get("exchange"))
        is_dow = groups.get("dow", {}).get("status") == "current" and source in groups["dow"].get("symbols", [])
        if (market == "DOW" and is_dow) or (market != "DOW" and venue == market):
            symbols.add(symbol)
    return symbols


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@contextmanager
def serve(root, base_url):
    if base_url:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("--base-url must point to a local HTTP server; production is never tested implicitly")
        yield base_url.rstrip("/") + "/"
        return
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class Checks:
    def __init__(self, root, output):
        self.root, self.output = root, output
        self.data = json.loads((root / DATA_FILES[0]).read_text())
        self.groups = json.loads((root / "stock-market-groups.json").read_text())
        self.started = datetime.now(timezone.utc)
        self.report = {
            "suite": "canonical-investment-radar", "started_at": self.started.isoformat(),
            "browser_time": "fixed to actual test start for reproducible before/after screenshots",
            "financial_data": {"mode": "unmodified saved repository JSON in normal cases",
                               "generated_at": self.data.get("generated_at"), "companies": len(self.data["companies"])},
            "not_verified": ["live/provider financial freshness", "external source availability",
                             "real Notion workspace permissions and embed policy", "trading results", "production deployment"],
            "checks": [], "screenshots": [], "fault_injections": [], "external_requests": [],
        }

    def check(self, name, condition, detail=None):
        item = {"name": name, "pass": bool(condition)}
        if detail is not None:
            item["detail"] = detail
        self.report["checks"].append(item)
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    def screenshot(self, page, label):
        path = self.output / f"{label}.png"
        content = page.screenshot(path=str(path), full_page=True, animations="disabled", caret="hide")
        self.report["screenshots"].append({"name": label, "path": str(path),
                                           "sha256": hashlib.sha256(content).hexdigest()})
        return content

    def failure_artifact(self, page, label):
        # Capture the failing state before the isolated context is closed. An
        # artifact error must never hide the original assertion or exit status.
        try:
            self.screenshot(page, label + '-failed')
        except Exception as error:
            self.report.setdefault('artifact_errors', []).append(str(error))

    def case(self, name, function):
        first_check = len(self.report['checks'])
        try:
            function()
        except Exception as error:
            failed = [item for item in self.report['checks'][first_check:] if not item['pass']]
            if failed:
                failed[-1].update({'case': name, 'traceback': traceback.format_exc()})
            else:
                self.report["checks"].append({"name": name + " completed", "pass": False,
                                               "detail": str(error), "traceback": traceback.format_exc()})
            print(f"FAIL {name}: {error}", flush=True)
        else:
            print(f"PASS {name}", flush=True)

    def context(self, browser, base, width, height, state=None, embed=False, corrupt=False):
        state = state if state is not None else {}
        context = browser.new_context(viewport={"width": width + 80 if embed else width,
                                                "height": height + 80 if embed else height},
                                      locale="ko-KR", timezone_id="Asia/Seoul", device_scale_factor=1)
        seed = dict(SEED)
        if corrupt:
            for key in ("radar-v8-stars", "radar-manual-rules-v2", "radar-paper-holdings-v2"):
                seed[key] = "{malformed user storage"
        storage_fault = ""
        if state.get('storage_failure'):
            self.report['fault_injections'].append({'storage': 'isolated localStorage profile', 'fault': 'QuotaExceededError on radar writes'})
            storage_fault = """
                const original = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    if (String(key).startsWith('radar-')) throw new DOMException('Controlled quota test', 'QuotaExceededError');
                    return original.call(this, key, value);
                };
            """
        context.add_init_script("""(() => {
            if (!localStorage.getItem('codex-qa-seeded')) {
                for (const [key,value] of Object.entries(SEED)) localStorage.setItem(key,value);
                localStorage.setItem('codex-qa-seeded','1');
            }
            STORAGE_FAULT
        })()""".replace("SEED", json.dumps(seed)).replace('STORAGE_FAULT', storage_fault))
        requests, errors = [], []
        origin = urlparse(base).netloc

        def intercept(route):
            parsed = urlparse(route.request.url)
            name = Path(parsed.path).name
            if parsed.netloc == origin and parsed.path.endswith("/__codex_radar_embed__"):
                route.fulfill(content_type="text/html", body=(
                    '<!doctype html><title>Local Notion-size iframe harness</title>'
                    '<style>html,body{margin:0}iframe{display:block;border:0}</style>'
                    f'<iframe name="radar-under-test" width="{width}" height="{height}" '
                    f'src="{base}stock-value-radar.html"></iframe>'))
                return
            local = parsed.netloc == origin
            raw_mirror = parsed.netloc == "raw.githubusercontent.com" and name in DATA_FILES
            if local or raw_mirror:
                if name in DATA_FILES:
                    requests.append(name)
                    if name == 'stock-direction-forecast.json' and state.get('invalid_probabilities'):
                        # Explicit negative fixture: corrupt only the selected
                        # real ticker's distribution in the HTTP response.
                        payload = json.loads((self.root / name).read_text())
                        for record in payload.get('records', []):
                            if str(record.get('symbol', '')).replace('.KS', '').replace('.KQ', '') == '005930':
                                record['probabilities'] = {'up': .9, 'flat': .8, 'down': .7}
                        self.report['fault_injections'].append({'response': name, 'fault': 'invalid probability sum for saved Samsung records'})
                        route.fulfill(content_type='application/json', body=json.dumps(payload))
                        return
                    if name == DATA_FILES[0] and state.get("fault"):
                        fault = state["fault"]
                        self.report["fault_injections"].append({"response": name, "fault": fault})
                        if fault == "http503":
                            route.fulfill(status=503, body="Controlled browser test failure")
                        elif fault == "empty":
                            route.fulfill(content_type="application/json", body='{"companies":[]}')
                        elif fault == "older":
                            old = dict(self.data)
                            stamp = datetime.fromisoformat(old["generated_at"].replace("Z", "+00:00"))
                            old["generated_at"] = (stamp - timedelta(days=1)).isoformat()
                            route.fulfill(content_type="application/json", body=json.dumps(old))
                        else:
                            raise ValueError("unknown fault " + fault)
                        return
                if raw_mirror:
                    self.report["external_requests"].append({"url": route.request.url, "action": "saved local JSON mirror"})
                    route.fulfill(content_type="application/json", body=(self.root / name).read_bytes())
                elif name == "favicon.ico":
                    route.fulfill(status=204)
                else:
                    route.continue_()
                return
            self.report["external_requests"].append({"url": route.request.url, "action": "blocked unexpected external request"})
            route.abort("blockedbyclient")

        context.route("**/*", intercept)
        page = context.new_page()
        page.clock.set_fixed_time(self.started)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_default_timeout(12000)
        return context, page, requests, errors

    def settle(self, scope, raw=True):
        scope.locator(".fx-topbar").wait_for()
        scope.wait_for_function("""() => !!window.StockRadarV2Bridge?.snapshot()?.data?.newsLink &&
            !document.querySelector('#source-status')?.textContent.includes('재조회 중')""")
        if raw:
            scope.wait_for_function("() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length")

    def navigate(self, scope, screen):
        scope.locator(f'.fx-topbar [data-nr-screen="{screen}"]').first.click()
        self.check(f"navigation {screen}", scope.locator(f'.fx-stage[data-screen="{screen}"]').count() == 1)

    def preserved(self, scope, label):
        actual = scope.evaluate("keys => Object.fromEntries(keys.map(k=>[k,localStorage.getItem(k)]))", list(PRESERVED_STORAGE))
        self.check(label + " preserves user storage exactly", actual == PRESERVED_STORAGE, actual)

    def geometry(self, scope, label, width, height, desktop):
        info = scope.evaluate("""() => {
            const box = sel => {const el=document.querySelector(sel);if(!el)return null;
                const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right}};
            return {width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth,
                scrollHeight:document.documentElement.scrollHeight,row:box('.fx-v5-marketline'),
                flag:box('.fx-sent-v9-flag-svg'),sentiment:box('.fx-sent-v9'),main:box('.fx-v5-main'),
                panels:[...document.querySelectorAll('.fx-v5-main>*')].map(el=>{const r=el.getBoundingClientRect();
                    return {left:r.left,right:r.right,bottom:r.bottom,width:r.width}}),
                cards:[...document.querySelectorAll('.fx-v5-markets .nr-index')].map(el=>{
                    const b=el.getBoundingClientRect();return {width:b.width,height:b.height,bottom:b.bottom}})}
        }""")
        self.check(label + " intended viewport and no horizontal overflow",
                   info["width"] == width and info["height"] == height and info["scrollWidth"] <= width + 1, info)
        self.check(label + " styled bounded sentiment flag", info["flag"] and
                   0 < info["flag"]["width"] <= 32 and 0 < info["flag"]["height"] <= 28, info["flag"])
        self.check(label + " four bounded market cards", len(info["cards"]) == 4 and
                   all(0 < card["height"] <= MAX_CARD_HEIGHT for card in info["cards"]), info["cards"])
        self.check(label + " market strip clears workspace", info["main"] and info["row"] and
                   info["main"]["y"] >= info["row"]["bottom"] - 3, info)
        self.check(label + " workspace retains available width", info["main"]["width"] >= width * .8, info["main"])
        if desktop:
            self.check(label + " bounded market strip", info["row"]["height"] <= MAX_CARD_HEIGHT, info["row"])
            self.check(label + " desktop panels fit one screen", info["scrollHeight"] <= height + 3 and
                       len(info["panels"]) == 3 and all(p["bottom"] <= height - 3 for p in info["panels"]), info)
        else:
            self.check(label + " stacked panels retain usable width", len(info["panels"]) == 3 and
                       all(p["width"] >= width * .8 and p["left"] >= 0 and p["right"] <= width + 1 for p in info["panels"]), info)

    def detail(self, scope, label, width, height):
        """Keep the approved V6 contract from test_stock_detail_v6.py at every size."""
        for section in ('upper', 'mid', 'lower'):
            self.check(label + ' three ' + section + ' detail panels',
                       scope.locator(f'.fx-detail-v6 .fx-detail-{section} > .fx-panel').count() == 3)
        definitions = scope.locator('.fx-detail-v6 .fx-d-help').evaluate_all(
            "els=>els.map(e=>({title:e.title,label:e.getAttribute('aria-label'),tab:e.tabIndex}))")
        self.check(label + ' all 16 accessible indicator definitions', len(definitions) == 16 and
                   scope.locator('.fx-detail-v6 .fx-d-plain').count() == 16 and
                   all(d['title'] and d['label'] and d['tab'] == 0 for d in definitions))
        decision = scope.locator('.fx-detail-v6 [data-investment-assessment="four-questions"]')
        labels = decision.locator('.fx-d-fact-label > span:first-child').all_text_contents()
        self.check(label + ' four independent investment questions', decision.count() == 1 and
                   decision.locator('.fx-d-fact').count() == 4 and
                   all(any(word in item for item in labels) for word in ('AI 상승', '지금 가격', '상승여력', '최종 투자')), labels)
        self.check(label + ' no fabricated buy probability',
                   '매수 성공률이 아닙니다' in scope.locator('.fx-decision-panel').inner_text())
        self.check(label + ' saved-price detail chart and identity preserved',
                   scope.locator('.fx-detail-primary .fx-chart-svg').count() == 1 and
                   scope.locator('.fx-d-security strong').count() == 1 and
                   bool(scope.locator('.fx-d-quote strong').inner_text().strip()))
        geometry = scope.evaluate("""() => {
            const rect = selector => [...document.querySelectorAll(selector)].map(el=>{
                const b=el.getBoundingClientRect();return {top:b.top,bottom:b.bottom,width:b.width}});
            return {pageWidth:document.documentElement.scrollWidth,pageHeight:document.documentElement.scrollHeight,
                upper:rect('.fx-detail-upper > .fx-panel'),lower:rect('.fx-detail-lower > .fx-panel')};
        }""")
        self.check(label + ' detail has no horizontal overflow and usable panels',
                   geometry['pageWidth'] <= width + 3 and all(p['width'] > 180 for p in geometry['upper']), geometry)
        if width >= 1180:
            self.check(label + ' desktop detail top cards align and fit screen',
                       max(p['top'] for p in geometry['upper']) - min(p['top'] for p in geometry['upper']) < 3 and
                       geometry['pageHeight'] <= height + 3 and geometry['lower'][-1]['bottom'] <= height + 2, geometry)
        for period in ('1W', '1M'):
            scope.locator(f'.fx-d-periods [data-fx-period="{period}"]').click()
            self.check(label + ' detail period ' + period + ' responds',
                       scope.locator(f'.fx-d-periods [data-fx-period="{period}"]').get_attribute('aria-pressed') == 'true')

    def layout(self, browser, base, width, height, embed=False):
        label = f'{"notion-iframe" if embed else "viewport"}-{width}x{height}'
        context, page, requests, errors = self.context(browser, base, width, height, embed=embed)
        try:
            target = base + "__codex_radar_embed__" if embed else base + "stock-radar-dashboard.html?stock=005930#home"
            page.goto(target, wait_until="domcontentloaded")
            if embed:
                page.locator('iframe[name="radar-under-test"]').wait_for()
                scope = page.frame(name="radar-under-test")
                self.check(label + " real iframe created", scope is not None)
            else:
                page.wait_for_url("**/stock-value-radar.html?stock=005930#home", timeout=20000)
                scope = page
                self.check(label + " canonical redirect preserves stock query/hash",
                           page.url.endswith("stock-value-radar.html?stock=005930#home"), page.url)
            self.settle(scope)
            self.geometry(scope, label, width, height, width >= 1000)
            self.check(label + " all saved feeds loaded", set(DATA_FILES) <= set(requests), sorted(set(requests)))
            self.check(label + " saved companies loaded without substitution",
                       scope.evaluate("() => window.StockRadarV2Bridge.snapshot().data.raw") == self.data)
            self.check(label + " genuine saved-price chart", scope.locator('.fx-v5-chartarea .fx-chart-svg polyline').count() >= 1)
            self.screenshot(page, label + "-before")
            # Exercise core controls at every size, including inside an actual narrow iframe.
            scope.locator('[data-fx-sentiment-next]').click()
            self.check(label + " Korean sentiment toggles", scope.locator('.fx-sent-v9.is-korea').count() == 1)
            scope.locator('[data-fx-sentiment-next]').click()
            self.navigate(scope, "stockdetail")
            self.check(label + " financial detail usable", scope.locator('.fx-detail-v6 .fx-d-metrics').count() == 3)
            self.detail(scope, label, width, height)
            self.screenshot(page, label + "-detail")
            self.navigate(scope, "home")
            scope.evaluate("window.scrollTo(0,0)")
            self.geometry(scope, label + " after", width, height, width >= 1000)
            self.preserved(scope, label)
            # Reload into the original viewport/state for a deterministic pixel comparison.
            if embed:
                scope.goto(base + "stock-value-radar.html", wait_until="domcontentloaded")
            else:
                page.reload(wait_until="domcontentloaded")
            self.settle(scope)
            scope.evaluate("window.scrollTo(0,0)")
            before = (self.output / (label + "-before.png")).read_bytes()
            after = self.screenshot(page, label + "-after")
            self.check(label + " unchanged UI before/after exercise", before == after,
                       {"comparison": "exact PNG bytes, same saved data/time/storage", "identical": before == after})
            self.check(label + " no JavaScript runtime errors", not errors, errors)
        except Exception:
            self.failure_artifact(page, label)
            raise
        finally:
            context.close()

    def interactions(self, browser, base):
        context, page, requests, errors = self.context(browser, base, 1440, 900)
        try:
            page.goto(base + "stock-value-radar.html", wait_until="domcontentloaded")
            self.settle(page)
            script_names = page.locator('script[src]').evaluate_all("els=>els.map(x=>new URL(x.src).pathname.split('/').pop())")
            self.check("six intentional runtime modules; no legacy injections", set(script_names) == {Path(name).name for name in UI_FILES[2:]} and len(script_names) == 6, script_names)
            self.check('approved home has four right panels and three analysis groups',
                       page.locator('.fx-v5-aside .fx-v5-sidecard').count() == 4 and
                       page.locator('.fx-v5-toptrio>div').count() == 3 and
                       page.locator('.fx-v5-middle>section').count() == 3 and
                       page.locator('.fx-v5-bottom>section').count() == 3)
            self.check('home chart uses actual moving average and disclosed source dates',
                       'MA20' in page.locator('.fx-v5-chartarea .fx-v5-ma-legend').inner_text() and
                       page.locator('.fx-v5-chartarea .fx-chart-svg polyline').count() >= 2 and
                       all(any(word in text for word in ('일봉', '추이', '지표 저장값'))
                           for text in page.locator('.fx-v5-markets .nr-index .nr-sub').all_text_contents()))
            self.check('home research and strict checklist are not investment approval',
                       '연구용' in page.locator('.fx-v5-ai').inner_text() and
                       'AI 방향과 별도' in page.locator('.fx-v5-sidecheck').inner_text() and
                       '수익·매수 성공 확률 아님' in page.locator('.fx-v5-sidecheck').inner_text())
            self.navigate(page, "stocks")
            for market in ("ALL", "KOSPI", "KOSDAQ", "NASDAQ", "DOW"):
                page.locator(f'[data-rf-market="{market}"]').click()
                expected = market_symbols(self.data, self.groups, market)
                shown = page.locator('.fx-list-panel .fx-row').evaluate_all("els=>els.map(e=>e.dataset.nrSelect)")
                count = page.locator('#fx-result-count').inner_text()
                self.check(market + " filter matches saved membership and source count",
                           len(shown) == min(len(expected), 36) and set(shown) <= expected and
                           re.match(rf"{len(shown)} / {len(expected)}개", count) is not None and
                           page.locator(f'[data-rf-market="{market}"]').get_attribute('aria-pressed') == "true",
                           {"expected_count": len(expected), "shown": shown, "label": count})
            page.locator('[data-rf-market="ALL"]').click()
            before_count = page.locator('.fx-row').count()
            page.locator('[data-fx-more]').click()
            self.check("pagination expands real saved candidates", page.locator('.fx-row').count() == min(before_count + 36, len(self.data['companies'])))
            # Search a US ticker while a Korean ticker was initially selected.
            us = next(c for c in self.data['companies'] if c['symbol'] in market_symbols(self.data, self.groups, 'NASDAQ'))
            page.locator('#fx-search-input').fill(str(us['symbol']))
            matching = {str(c['symbol']) for c in self.data['companies'] if str(us['symbol']).lower() in (c['name'] + ' ' + str(c['symbol'])).lower()}
            shown = page.locator('.fx-row').evaluate_all('els=>els.map(e=>e.dataset.nrSelect)')
            self.check("search returns source-backed symbol/name matches", set(shown) == matching, shown)
            page.locator(f'.fx-row[data-nr-select="{us["symbol"]}"]').click()
            self.check("selected company updates analysis", page.evaluate(SNAPSHOT)['selected'] == us['symbol'] and us['name'] in page.locator('#fx-focus-slot').inner_text())
            page.reload(wait_until='domcontentloaded')
            self.settle(page)
            self.check("selected company and market persist on reload", page.evaluate(SNAPSHOT)['selected'] == us['symbol'] and page.evaluate(SNAPSHOT)['market'] == 'ALL')
            self.navigate(page, 'stocks')
            page.locator('#fx-search-input').fill('__no_real_company_matches_this__')
            self.check("empty search is explicit, no fabricated results", page.locator('.fx-row').count() == 0 and '해당하는 종목이 없습니다' in page.locator('#fx-results').inner_text())
            page.locator('#fx-search-input').fill('')
            page.locator('[data-rf-market="NASDAQ"]').click()
            page.evaluate("window.StockRadarV2Bridge.select('005930')")
            self.check("cross-market selection becomes visible", page.locator('[data-rf-market="ALL"]').get_attribute('aria-pressed') == 'true' and page.locator('.fx-row[data-nr-select="005930"]').count() == 1)
            self.navigate(page, 'home')
            page.locator('.fx-v5-actions [data-nr-detail]').click()
            self.check("home financial analysis action opens selected integrated detail", page.locator('.fx-stage[data-screen="stockdetail"]').count() == 1 and '005930' in page.locator('.fx-d-securitybar').inner_text())
            selected = next(c for c in self.data['companies'] if c['symbol'] == '005930')
            self.check("detail displays saved company identity/date and honest research label",
                       selected['name'] in page.locator('.fx-d-security').inner_text() and selected['price_session'] in page.locator('.fx-d-quote').inner_text() and '매수 성공률 아님' in page.locator('.fx-d-research-note').inner_text())
            expected_links = {selected['sources'][key] for key in ('official', 'history', 'estimates', 'cashflow', 'balance') if str(selected.get('sources', {}).get(key, '')).startswith('https://')}
            links = set(page.locator('.fx-d-source-links a').evaluate_all('els=>els.map(e=>e.href)'))
            self.check("financial original-source links match saved company", expected_links == links and bool(links), sorted(links))
            for period in ('1W', '1M', '3M', '6M'):
                page.locator(f'.fx-d-periods [data-fx-period="{period}"]').click()
                self.check(period + " chart period action responds", page.locator(f'.fx-d-periods [data-fx-period="{period}"]').get_attribute('aria-pressed') == 'true' and page.locator('.fx-d-chart-body .fx-chart-svg,.fx-d-chart-body .fx-chart-empty').count() == 1)
            for screen in ('scenario', 'performance', 'portfolio', 'monitor', 'news', 'settings'):
                self.navigate(page, screen)
                self.check(screen + " substantive content renders", len(page.locator('.fx-stage').inner_text().strip()) > 50)
                if screen == 'scenario':
                    self.check('three scenario alternatives never draw a fake future path',
                               page.locator('.fx-scenario-options .fx-scenario-option').count() == 3 and
                               page.locator('.fx-scenario-ai-panel .fx-ai-card').count() == 1 and
                               '미래 경로' in page.locator('.fx-scenario-v4').inner_text())
                    targets = selected.get('targets') or {}
                    values = [targets.get(key) for key in ('low', 'median', 'high')]
                    ordered = (not all(isinstance(value, (int, float)) for value in values)
                               or values[0] <= values[1] <= values[2])
                    self.check('target order is consistent or explicitly unavailable', ordered or
                               '순서 불일치' in page.locator('.fx-scenario-v4').inner_text(), targets)
                if screen == 'performance':
                    text = page.locator('.fx-validation-grid').inner_text()
                    self.check('evaluation exposes outcome table, Brier, source audit and limitations',
                               page.locator('.fx-audit').count() == 1 and
                               all(word in text for word in ('수익성 미입증', '매수 성공률', 'Brier 개선', '정확도 감사')) and
                               page.locator('.fx-validation-grid .nr-validation-note').count() == 1)
                    self.check('independent evaluation distinguished from raw outcome counts',
                               all(word in page.locator('.fx-table-hint').inner_text() for word in ('독립 평가', '두 모수')))
            link = page.locator('a[href="./stock-value-radar-advanced.html"]')
            self.check("preserved advanced financial analysis is accessible", link.count() == 1 and link.get_attribute('target') == '_blank')
            self.navigate(page, 'home')
            page.locator('[data-fx-sentiment-next]').click()
            self.check("Korean sentiment source attribution", 'koreafeargreed.com' in page.locator('.fx-sent-v9-foot a').get_attribute('href') and '코스닥' in page.locator('.fx-sent-v9').inner_text())
            page.reload(wait_until='domcontentloaded')
            self.settle(page)
            self.check("sentiment choice persists through reload", page.locator('.fx-sent-v9.is-korea').count() == 1)
            page.locator('[data-fx-sentiment-next]').click()
            self.check("US sentiment restores with source", page.locator('.fx-sent-v9.is-us').count() == 1 and page.locator('.fx-sent-v9-foot a').get_attribute('href').startswith('https://'))
            # Forecast rendering uses current saved records, never a manufactured
            # active prediction. Old snapshots must show their real status.
            sample = page.evaluate("""() => {
                const d=window.StockRadarV2Bridge.snapshot().data,now=Date.now();
                const norm=s=>String(s||'').toUpperCase().replace(/\\.(KS|KQ)$/,'');
                const records=d.direction?.records||[],valid=records.filter(r=>{
                    const p=r.probabilities||{},issued=Date.parse(r.issued_at||''),
                        start=Date.parse(r.target?.start||''),end=Date.parse(r.target?.end||'');
                    return r.status==='research_prediction'&&issued<=start&&issued<=now+300000&&
                        end>now&&start<end&&['up','flat','down'].every(k=>typeof p[k]==='number'&&p[k]>=0&&p[k]<=1)&&
                        Math.abs(p.up+p.flat+p.down-1)<.025;
                });
                return {forecastCount:records.length,generatedAt:d.direction?.generated_at,
                    firstActiveSymbol:d.raw.companies.find(c=>valid.some(r=>norm(c.symbol)===norm(r.symbol)))?.symbol||null};
            }""")
            self.check('forecast records retain actual issuer coverage', sample['forecastCount'] >= 1 and bool(sample['generatedAt']), sample)
            if sample['firstActiveSymbol']:
                page.evaluate('(symbol)=>window.StockRadarV2Bridge.select(symbol)', sample['firstActiveSymbol'])
                self.navigate(page, 'stockdetail')
                self.check('actual valid forecast renders AI probability',
                           page.locator('.fx-d-ai-body .fx-ai-heading strong').count() == 1 and
                           '%' in page.locator('.fx-d-ai-body .fx-ai-heading strong').inner_text(), sample)
            else:
                self.report['not_verified'].append('active-forecast rendering: no currently valid saved forecast in this run')
            page.goto(base + 'stock-value-radar.html?stock=005930&screen=stockdetail', wait_until='domcontentloaded')
            self.settle(page)
            self.check('direct Samsung financial detail link preserves stock/model status',
                       '삼성전자' in page.locator('.fx-detail-intro h2').inner_text() and
                       bool(page.locator('.fx-d-ai-body').inner_text().strip()))
            if page.locator('.fx-d-ai-empty').count():
                self.check('unavailable signal explains actual model coverage', 'AI 모델' in page.locator('.fx-d-ai-empty').inner_text())
                if sample['firstActiveSymbol']:
                    page.locator('.fx-d-ai-empty [data-fx-filter="ai"]').click()
                    self.check('no-signal action selects real valid forecast', page.locator('.fx-d-ai-body .fx-ai-heading strong').count() == 1)
            self.preserved(page, 'filters/navigation/reload')
            self.check("interactions have no JavaScript runtime errors", not errors, errors)
            self.screenshot(page, 'interaction-complete')
        except Exception:
            self.failure_artifact(page, 'interactions')
            raise
        finally:
            context.close()

    def user_forms(self, browser, base):
        """Exercise saved user features in a disposable profile with an existing holding/rule."""
        context, page, _requests, errors = self.context(browser, base, 1440, 900)
        try:
            page.goto(base + 'stock-value-radar.html', wait_until='domcontentloaded')
            self.settle(page)
            self.navigate(page, 'stocks')
            page.locator('[data-fx-filter="star"]').click()
            self.check('favorite filter retains pre-existing saved ticker',
                       page.locator('.fx-row').count() == 1 and
                       page.locator('.fx-row[data-nr-select="005930"]').count() == 1)
            self.navigate(page, 'home')
            self.check('home returns with search and direction filter reset',
                       page.locator('#fx-search-input').input_value() == '' and
                       page.locator('[data-fx-filter="all"]').get_attribute('aria-pressed') == 'true')
            self.navigate(page, 'stockdetail')
            page.locator('.fx-d-star').click()
            self.check('favorite action removes selected ticker', page.evaluate(SNAPSHOT)['favorites'] == [])
            page.locator('.fx-d-star').click()
            self.check('favorite action restores original saved ticker', page.evaluate(SNAPSHOT)['favorites'] == ['005930'])
            self.navigate(page, 'monitor')
            page.locator('#radar-rule-symbol').select_option('AAPL')
            page.locator('#radar-rule-value').fill('1')
            page.locator('#radar-rule-form button[type="submit"]').click()
            self.check('manual condition adds without overwriting prior rule',
                       len(page.evaluate(SNAPSHOT)['rules']) == 2 and page.locator('.nr-manual-row').count() == 2)
            page.reload(wait_until='domcontentloaded')
            self.settle(page)
            self.navigate(page, 'monitor')
            self.check('manual condition survives reload', len(page.evaluate(SNAPSHOT)['rules']) == 2)
            page.locator('[data-nr-rule-remove="1"]').click()
            self.preserved(page, 'deleting new manual condition')
            self.navigate(page, 'portfolio')
            self.check('new paper form initially follows selected company',
                       page.locator('#radar-paper-symbol').input_value() == '005930')
            page.locator('#radar-paper-symbol').select_option('AAPL')
            page.evaluate('window.StockRadarV2Bridge.render()')
            self.check('paper ticker survives unrelated re-render independently of global stock',
                       page.locator('#radar-paper-symbol').input_value() == 'AAPL' and
                       page.evaluate(SNAPSHOT)['selected'] == '005930')
            for qty, cost in (('2', '100'), ('3', '120')):
                page.locator('#radar-paper-qty').fill(qty)
                page.locator('#radar-paper-cost').fill(cost)
                page.locator('#radar-paper-form button[type="submit"]').click()
                self.check('paper ticker remains AAPL after adding ' + qty + ' shares',
                           page.locator('#radar-paper-symbol').input_value() == 'AAPL')
            holdings = page.evaluate(SNAPSHOT)['paper']
            new = next(item for item in holdings if item['symbol'] == 'AAPL')
            self.check('paper additions use weighted average without touching existing holding',
                       len(holdings) == 2 and new['qty'] == 5 and abs(new['cost'] - 112) < 1e-8 and
                       holdings[0] == json.loads(PRESERVED_STORAGE['radar-paper-holdings-v2'])[0], holdings)
            self.check('paper registration does not change durable global selected stock',
                       page.evaluate(SNAPSHOT)['selected'] == '005930' and
                       page.evaluate("() => localStorage.getItem('radar-last-symbol-v5')") == SEED['radar-last-symbol-v5'])
            self.report['portfolio_regression'] = {
                'fixture': 'disposable local user profile; simulated holdings only',
                'before_holdings': json.loads(PRESERVED_STORAGE['radar-paper-holdings-v2']),
                'selected_once': 'AAPL', 'submissions': [{'qty': 2, 'cost': 100}, {'qty': 3, 'cost': 120}],
                'after_holdings': holdings, 'global_selected': page.evaluate(SNAPSHOT)['selected'],
            }
            self.screenshot(page, 'portfolio-after-repeat-purchase')
            self.check('mixed-currency paper valuations remain separate and simulated',
                       page.locator('.nr-paper-overview').count() == 2 and
                       '모의' in page.locator('.nr-screen-head').inner_text())
            page.reload(wait_until='domcontentloaded')
            self.settle(page)
            self.navigate(page, 'portfolio')
            self.check('paper holdings survive reload', page.evaluate(SNAPSHOT)['paper'] == holdings)
            page.locator('[data-nr-paper-remove="1"]').click()
            self.preserved(page, 'deleting newly added paper holding')
            self.check('user forms have no JavaScript runtime errors', not errors, errors)
        except Exception:
            self.failure_artifact(page, 'user-forms')
            raise
        finally:
            context.close()

    def invalid_probabilities(self, browser, base):
        context, page, _requests, errors = self.context(browser, base, 1440, 900, state={'invalid_probabilities': True})
        try:
            page.goto(base + 'stock-value-radar.html', wait_until='domcontentloaded')
            self.settle(page)
            self.check('malformed probability sum is blocked and explained',
                       '예측 확률·발행시각 검증 실패' in page.locator('.fx-v5-ai').inner_text() and
                       page.locator('.fx-v5-ai .fx-ai-heading strong').count() == 0)
            self.preserved(page, 'invalid forecast response')
            self.check('invalid forecast response has no JavaScript runtime errors', not errors, errors)
            self.screenshot(page, 'invalid-probability-response')
        except Exception:
            self.failure_artifact(page, 'invalid-probabilities')
            raise
        finally:
            context.close()

    def storage_failure(self, browser, base):
        context, page, _requests, errors = self.context(browser, base, 390, 844, state={'storage_failure': True})
        try:
            page.goto(base + 'stock-value-radar.html', wait_until='domcontentloaded')
            self.settle(page)
            page.locator('[data-rf-market="NASDAQ"]').click()
            self.check('storage write rejection is visible without destroying saved preferences',
                       '브라우저 저장 실패' in page.locator('#source-status').inner_text() and
                       page.evaluate("() => localStorage.getItem('radar-last-market-v5')") == SEED['radar-last-market-v5'])
            self.preserved(page, 'storage write rejection')
            page.reload(wait_until='domcontentloaded')
            self.settle(page)
            snapshot = page.evaluate(SNAPSHOT)
            self.check('rejected write reload restores last durable selection and market',
                       snapshot['selected'] == '005930' and snapshot['market'] == 'ALL')
            self.preserved(page, 'storage rejection reload')
            self.check('storage rejection has no JavaScript runtime errors', not errors, errors)
        except Exception:
            self.failure_artifact(page, 'storage-write-rejection')
            raise
        finally:
            context.close()

    def recovery(self, browser, base, initial=False):
        label = 'initial-source-failure' if initial else 'refresh-fault-recovery'
        state = {'fault': 'http503'} if initial else {}
        context, page, _requests, errors = self.context(browser, base, 390, 844, state=state)
        try:
            page.goto(base + 'stock-value-radar.html', wait_until='domcontentloaded')
            self.settle(page, raw=not initial)
            if initial:
                self.check(label + " explicit unavailable state without invented prices",
                           page.evaluate(SNAPSHOT)['data'].get('raw') is None and page.locator('.fx-row').count() == 0 and
                           '종목 원자료 이용 불가' in page.locator('#source-status').inner_text())
                self.screenshot(page, label)
                self.preserved(page, label)
            else:
                for fault, text in (('http503', 'raw 조회 실패 · 직전 정상 자료 유지'),
                                    ('empty', 'raw 조회 실패 · 직전 정상 자료 유지'),
                                    ('older', 'raw 이전 시점 응답 · 현재 자료 유지')):
                    state['fault'] = fault
                    page.locator('[data-fx-refresh]').click()
                    page.wait_for_function("() => !document.querySelector('#source-status').textContent.includes('재조회 중')")
                    self.check(fault + " warns while retaining exact last valid data",
                               text in page.locator('#source-status').inner_text() and page.evaluate(SNAPSHOT)['data']['raw'] == self.data)
                    self.preserved(page, fault)
                self.screenshot(page, label + '-warning')
            state.clear()
            page.locator('[data-fx-refresh]').click()
            self.settle(page)
            self.check(label + " recovers using visible refresh action", page.evaluate(SNAPSHOT)['data']['raw'] == self.data and '조회 실패' not in page.locator('#source-status').inner_text())
            self.preserved(page, label + ' recovered')
            self.check(label + " no JavaScript runtime errors", not errors, errors)
            self.screenshot(page, label + '-recovered')
        except Exception:
            self.failure_artifact(page, label)
            raise
        finally:
            context.close()

    def corrupt_storage(self, browser, base):
        context, page, _requests, errors = self.context(browser, base, 320, 640, corrupt=True)
        try:
            page.goto(base + 'stock-value-radar.html', wait_until='domcontentloaded')
            self.settle(page)
            snapshot = page.evaluate(SNAPSHOT)
            self.check("malformed storage does not crash or invent holdings/rules",
                       snapshot['favorites'] == [] and snapshot['rules'] == [] and snapshot['paper'] == [] and not errors, errors)
            self.check("malformed and unrelated user storage not silently deleted",
                       page.evaluate("() => localStorage.getItem('radar-paper-holdings-v2')") == '{malformed user storage' and
                       page.evaluate("() => localStorage.getItem('codex-qa-preservation-sentinel')") == PRESERVED_STORAGE['codex-qa-preservation-sentinel'])
        except Exception:
            self.failure_artifact(page, 'malformed-storage')
            raise
        finally:
            context.close()


def main():
    args = arguments()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='notion-radar-browser-'))
    if output == root or root in output.parents:
        raise SystemExit('Artifacts must be outside the checkout; choose --output /tmp/...')
    output.mkdir(parents=True, exist_ok=True)
    checks = Checks(root, output)
    before = fingerprints(root)
    checks.report['source_sha256_before'] = before
    try:
        from playwright.sync_api import sync_playwright
        with serve(root, args.base_url) as base, sync_playwright() as api:
            checks.report['base_url'] = base
            options = {'headless': True}
            if args.browser_executable:
                options['executable_path'] = args.browser_executable
            browser = api.chromium.launch(**options)
            try:
                # Keep both original geometry viewports, then desktop/mobile/Notion-size coverage.
                for width, height, embed in ((1629, 929, False), (1366, 768, False), (1440, 900, False), (1920, 1080, False),
                                             (390, 844, False), (320, 640, True)):
                    checks.case(f'layout {width}x{height} embed={embed}',
                                lambda w=width, h=height, e=embed: checks.layout(browser, base, w, h, e))
                checks.case('current radar interactions', lambda: checks.interactions(browser, base))
                checks.case('user rules, favorites and paper holdings', lambda: checks.user_forms(browser, base))
                checks.case('invalid forecast probability response', lambda: checks.invalid_probabilities(browser, base))
                checks.case('storage write rejection', lambda: checks.storage_failure(browser, base))
                checks.case('refresh failure and recovery', lambda: checks.recovery(browser, base))
                checks.case('initial failure and recovery', lambda: checks.recovery(browser, base, initial=True))
                checks.case('malformed user storage', lambda: checks.corrupt_storage(browser, base))
            finally:
                browser.close()
    except Exception as error:
        checks.report['checks'].append({'name': 'browser runner infrastructure', 'pass': False,
                                        'detail': str(error), 'traceback': traceback.format_exc()})
    after = fingerprints(root)
    checks.report['source_sha256_after'] = after
    checks.case('source preservation', lambda: checks.check('no source, saved data, or runtime file modified', before == after))
    checks.case('external network isolation', lambda: checks.check('no unexpected external data requests',
                not any(x['action'] == 'blocked unexpected external request' for x in checks.report['external_requests']),
                checks.report['external_requests']))
    failures = [item for item in checks.report['checks'] if not item['pass']]
    checks.report.update({'passed': not failures, 'checks_passed': sum(item['pass'] for item in checks.report['checks']),
                          'checks_failed': len(failures), 'finished_at': datetime.now(timezone.utc).isoformat()})
    report_path = output / 'report.json'
    report_path.write_text(json.dumps(checks.report, ensure_ascii=False, indent=2) + '\n')
    print(f"{checks.report['checks_passed']} checks passed; {len(failures)} failed. Report: {report_path}", flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
