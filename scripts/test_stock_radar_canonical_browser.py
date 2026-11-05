"""Offline browser regression for the canonical investment radar.

Reads the candidate checkout's actual JSON bytes without updating market data.
The optional baseline uses the same captured data, stored-record fixture, clock,
and viewports; captures are evidence of rendered UI, not live Notion/Safari or
financial accuracy. No deployment, broker, notification, or publisher is called.
"""
from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import http.server
import json
import re
import threading
import traceback
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


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
PROFILES = (
    ("desktop-wide", 1629, 929, "native"),
    ("desktop", 1366, 768, "native"),
    ("mobile", 390, 844, "native"),
    ("narrow", 320, 844, "native"),
    ("embed-mobile", 390, 844, "iframe"),
    ("embed-narrow", 320, 844, "iframe"),
    ("opaque-mobile", 390, 844, "opaque"),
)
PROTECTED_KEYS = (
    "radar-v8-stars", "radar-manual-rules-v2",
    "radar-paper-holdings-v2", "codex-existing-unrelated-record-v1",
    "radar-sentiment-market",
)
SELECTION_KEYS = ("radar-last-symbol-v5", "radar-last-market-v5")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def sha(value):
    return hashlib.sha256(value).hexdigest()


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path,
                        default=Path("/tmp/notion-canonical-radar"))
    parser.add_argument("--browser-executable",
                        help="Existing Chromium executable; CI may use Playwright's installed browser.")
    parser.add_argument("--baseline-root", type=Path,
                        help="Read-only archived checkout for matching before/after captures.")
    return parser.parse_args()


def fixtures(root):
    captured = {}
    for name in DATA_FILES:
        value = (root / name).read_bytes()
        # A malformed source is a failure, never replaced with example data.
        if name.endswith(".jsonl"):
            for line in value.decode().splitlines():
                if line.strip():
                    json.loads(line)
        else:
            json.loads(value)
        captured[name] = value
    raw = json.loads(captured["stock-opportunity-data.json"])
    companies = raw.get("companies")
    if not isinstance(companies, list) or not companies:
        raise ValueError("A nonempty actual company snapshot is required")
    symbols = [str(c["symbol"]) for c in companies]
    if len(set(symbols)) != len(symbols):
        raise ValueError("Duplicate symbols in the captured company snapshot")
    primary = next((c for c in companies if str(c["symbol"]) == "005930"), companies[0])
    priced = next((c for c in companies if isinstance(c.get("price"), (int, float))
                   and not isinstance(c.get("price"), bool) and c["price"] > 0), None)
    if priced is None:
        raise ValueError("A captured positive price is required for the stored-record regression")
    # These are isolated preexisting USER records, never substitute market data.
    # Whitespace/unknown metadata deliberately detect destructive normalization.
    saved = {
        "radar-v8-stars": json.dumps([str(primary["symbol"])], indent=2),
        "radar-manual-rules-v2": json.dumps([{
            "symbol": str(priced["symbol"]), "kind": "lte", "value": priced["price"],
            "legacy_note": "existing user condition; browser regression only",
        }], indent=2),
        "radar-paper-holdings-v2": json.dumps([{
            "symbol": str(priced["symbol"]), "qty": 2.5, "cost": priced["price"],
            "legacy_note": "existing manual paper record; not a real order",
        }], indent=2),
        "codex-existing-unrelated-record-v1": '  {"note":"keep exact original bytes"}  ',
        "radar-last-symbol-v5": json.dumps(str(primary["symbol"])),
        "radar-last-market-v5": '"ALL"',
        "radar-sentiment-market": "us",
    }
    stamps = []
    for name, value in captured.items():
        if not name.endswith(".json"):
            continue
        text = json.loads(value).get("generated_at")
        if text:
            try:
                stamp = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
                if stamp.tzinfo is not None:
                    stamps.append(stamp)
            except ValueError:
                pass
    if not stamps:
        raise ValueError("Captured data must disclose an observed generation time")
    clock = max(stamps) + timedelta(minutes=1)
    return captured, raw, primary, saved, clock


def source_fingerprints(root):
    html = (root / "stock-value-radar.html").read_text()
    paths = {"stock-value-radar.html", "stock-radar-dashboard.html"}
    paths.update(urllib.parse.urlparse(value).path.removeprefix("./")
                 for value in re.findall(r'<script[^>]+src=[\"\']([^\"\']+)', html)
                 if not urllib.parse.urlparse(value).scheme)
    result = {}
    for name in sorted(paths):
        path = (root / name.lstrip("/")).resolve()
        if not path.is_relative_to(root):
            raise ValueError("A runtime asset escapes the selected checkout: " + name)
        result[name] = sha(path.read_bytes())
    return result


def storage(frame):
    return frame.evaluate("""() => {
      try { return {available:true, values:Object.fromEntries(Object.keys(localStorage)
        .sort().map(k=>[k,localStorage.getItem(k)]))}; }
      catch(e) { return {available:false, error:e.name, values:null}; }
    }""")


def snapshot(frame):
    return frame.evaluate("window.StockRadarV2Bridge.snapshot()")


def metrics(frame):
    return frame.evaluate("""() => {
      const box = sel => {
        const el=document.querySelector(sel); if(!el || !el.getClientRects().length)return null;
        const r=el.getBoundingClientRect();
        return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right};
      };
      return {
        url:location.pathname+location.search+location.hash,
        viewport:{width:innerWidth,height:innerHeight},
        document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},
        row:box('.fx-v5-marketline'), title:box('.fx-v5-markettitle'),
        cards:[...document.querySelectorAll('.fx-v5-markets .nr-index')].map(el=>{
          const r=el.getBoundingClientRect(),value=el.querySelector('.nr-num'),plot=el.querySelector('.nr-mini-chart polyline');
          const rect=e=>{if(!e)return null;const b=e.getBoundingClientRect();
            return {left:b.left,top:b.top,right:b.right,bottom:b.bottom,width:b.width,height:b.height};};
          const visible=e=>{for(let n=e;n&&n.nodeType===1;n=n.parentElement){const c=getComputedStyle(n);
            if(c.display==='none'||c.visibility==='hidden'||Number(c.opacity)===0)return false;}return !!e;};
          let number=null;if(value){const range=document.createRange();range.selectNodeContents(value);number=rect(range);}
          const ink=rect(plot),overlap=number&&ink?Math.max(0,Math.min(number.right,ink.right)-Math.max(number.left,ink.left))*
            Math.max(0,Math.min(number.bottom,ink.bottom)-Math.max(number.top,ink.top)):null;
          return {width:r.width,height:r.height,bottom:r.bottom,price_text:value?.textContent?.trim(),
            number,ink,overlap_area:overlap,value_visible:visible(value),plot_visible:visible(plot),
            ink_inside_card:!!ink&&ink.left>=r.left-1&&ink.right<=r.right+1&&ink.top>=r.top-1&&ink.bottom<=r.bottom+1};}),
        flag:box('.fx-sent-v9-flag-svg'), sentiment:box('.fx-sent-v9'),
        main:box('.fx-v5-main'),home:box('.fx-v5-home')
      };
    }""")


class Scenario:
    def __init__(self, browser, root, captured, raw, primary, saved, clock, output, profile, baseline=False):
        self.browser, self.root, self.captured = browser, root, captured
        self.raw, self.primary, self.saved, self.clock = raw, primary, saved, clock
        self.output, self.profile = output, profile
        self.baseline = baseline
        self.source_before = source_fingerprints(root)
        self.errors, self.external, self.requests, self.checks = [], [], [], []
        self.raw_failure = False
        self.unrecorded_data = []
        self.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(root)))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_port
        self.app_origin = f"http://127.0.0.1:{self.port}"
        self.parent_server = None
        self.parent_origin = self.app_origin
        if profile[3] != "native":
            owner = self
            class EmbedHandler(QuietHandler):
                def do_GET(handler):
                    if urllib.parse.urlparse(handler.path).path != "/__codex_embed__.html":
                        handler.send_error(404)
                        return
                    data = owner.embed_document().encode()
                    handler.send_response(200)
                    handler.send_header("Content-Type", "text/html; charset=utf-8")
                    handler.send_header("Content-Length", str(len(data)))
                    handler.end_headers()
                    handler.wfile.write(data)
            # Serve a genuine loopback HTTP document. A synthetic fulfilled
            # parent has an unknown network address space, so Chromium rightly
            # blocks its navigation to a local-network iframe.
            self.parent_server = http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), functools.partial(EmbedHandler, directory=str(root)))
            threading.Thread(target=self.parent_server.serve_forever, daemon=True).start()
            self.parent_origin = f"http://127.0.0.1:{self.parent_server.server_port}"
        self.origins = {self.app_origin, self.parent_origin}
        self.context = None
        self.page = None
        self.frame = None
        self.report = {
            "profile": profile[0], "viewport": list(profile[1:3]), "mode": profile[3],
            "passed": False, "checks": self.checks, "screenshots": [],
            "runtime_errors": self.errors, "blocked_external_requests": self.external,
            "controlled_failure": "Only the raw endpoint is deliberately returned as HTTP 503; normal responses are exact captured checkout bytes.",
        }

    def check(self, name, condition, detail=None, baseline_observation=False):
        self.checks.append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition and not (self.baseline and baseline_observation):
            raise AssertionError(f"{name}: {detail}")

    def embed_document(self):
        width, height, mode = self.profile[1:]
        sandbox = "allow-scripts allow-forms" + (" allow-same-origin" if mode == "iframe" else "")
        source = f"{self.app_origin}/stock-radar-dashboard.html?stock={urllib.parse.quote(str(self.primary['symbol']))}#home"
        body = ("<!doctype html><html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                "<body style='margin:0;padding:24px;background:#edf0f5;font:14px sans-serif'>"
                "<p style='margin:0 0 12px'>Cross-origin embedded widget verification</p>"
                f"<iframe title='Investment radar embed' sandbox='{sandbox}' src='{source}' "
                f"width='{width}' height='{height}' style='display:block;border:0;max-width:100%'></iframe></body></html>")
        return body

    def route(self, route):
        parsed = urllib.parse.urlparse(route.request.url)
        if route.request.method not in {"GET", "HEAD"}:
            self.external.append({"url": parsed.path, "method": route.request.method,
                                  "reason": "Non-read-only request rejected"})
            route.abort()
            return
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self.origins:
            self.external.append({"url": origin + parsed.path, "method": route.request.method})
            route.abort()
            return
        if parsed.path == "/__codex_embed__.html":
            route.continue_()
            return
        name = parsed.path.removeprefix("/")
        if name in self.captured:
            failed = name == "stock-opportunity-data.json" and self.raw_failure
            self.requests.append({"file": name, "status": 503 if failed else 200,
                                  "sha256": None if failed else sha(self.captured[name])})
            route.fulfill(status=503 if failed else 200,
                          content_type="text/plain" if failed else "application/json",
                          headers={"Access-Control-Allow-Origin": "*"},
                          body="Controlled regression source failure (HTTP 503)" if failed else self.captured[name])
            return
        if name.endswith((".json", ".jsonl")):
            self.unrecorded_data.append(name)
            route.abort()
            return
        # Actual local HTML/JS/CSS are served from the selected checkout. No
        # external resource, fallback website, or live API is allowed.
        route.continue_()

    def open(self):
        name, width, height, mode = self.profile
        self.context = self.browser.new_context(
            viewport={"width": width if mode == "native" else max(800, width + 48),
                      "height": height if mode == "native" else height + 96},
            is_mobile=width < 500, has_touch=width < 500,
            locale="ko-KR", timezone_id="Asia/Seoul", reduced_motion="reduce")
        self.context.route("**/*", self.route)
        self.context.add_init_script(r"""(() => {
          if(!/\/stock-(?:radar-dashboard|value-radar)\.html$/.test(location.pathname))return;
          const saved=""" + json.dumps(self.saved, ensure_ascii=False) + """;
          try { for(const [key,value]of Object.entries(saved))
            if(localStorage.getItem(key)===null)localStorage.setItem(key,value); }
          catch(e) { /* Opaque sandbox intentionally denies storage. */ }
        })();""")
        self.page = self.context.new_page()
        self.page.set_default_timeout(15000)
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.clock.set_fixed_time(self.clock)
        if mode == "native":
            origin = f"http://127.0.0.1:{self.port}"
            self.page.goto(origin + "/stock-radar-dashboard.html?stock=" +
                           urllib.parse.quote(str(self.primary["symbol"])) + "#home",
                           wait_until="domcontentloaded")
            self.page.wait_for_url("**/stock-value-radar.html?stock=*#home")
            self.frame = self.page.main_frame
        else:
            self.page.goto(self.parent_origin + "/__codex_embed__.html", wait_until="domcontentloaded")
            handle = self.page.locator("iframe").element_handle()
            self.frame = handle.content_frame()
            self.frame.wait_for_url("**/stock-value-radar.html?stock=*#home", wait_until="domcontentloaded")
        self.frame.wait_for_function("window.StockRadarV2Bridge && window.StockRadarFlowV2")
        self.settle()
        self.check("Legacy URL preserves the stock query and hash on canonical redirect",
                   self.frame.url.endswith("/stock-value-radar.html?stock=" +
                                           urllib.parse.quote(str(self.primary["symbol"])) + "#home"),
                   self.frame.url)
        self.report["storage"] = storage(self.frame)
        self.report["origins"] = self.frame.evaluate("({origin:self.origin,location:location.origin,referrer:document.referrer})")
        if mode == "native":
            self.check("Native local browser storage is available", self.report["storage"]["available"])
        elif mode == "iframe":
            self.check("Cross-origin embedded storage is available", self.report["storage"]["available"])
            self.check("Embedded application is a different origin from its parent",
                       self.report["origins"]["origin"] != self.parent_origin)
        else:
            self.check("Opaque sandbox explicitly denies browser storage",
                       not self.report["storage"]["available"], self.report["storage"])
        if mode != "opaque":
            self.check("Existing stored records load without rewriting original bytes",
                       storage(self.frame)["values"] == self.saved)

    def settle(self):
        self.frame.wait_for_function("""() => {
          const text=document.querySelector('#source-status')?.textContent || '';
          return window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length>0
            && text.includes('저장 종목') && !text.includes('자료 재조회 중');
        }""")
        self.frame.evaluate("document.fonts.ready")
        self.frame.locator(".fx-topbar").wait_for()

    def click(self, selector):
        node = self.frame.locator(selector).first
        node.scroll_into_view_if_needed()
        rect = node.bounding_box()
        target = node.evaluate("""e=>{
          const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
          const painted=document.elementFromPoint(x,y);
          return {x,y,width:r.width,height:r.height,viewportWidth:innerWidth,viewportHeight:innerHeight,
            painted:painted===e||e.contains(painted)};
        }""")
        self.check("Actual control is visible and can receive a pointer: " + selector,
                   bool(rect) and target["width"] > 0 and target["height"] > 0 and target["painted"]
                   and 0 <= target["x"] <= target["viewportWidth"]
                   and 0 <= target["y"] <= target["viewportHeight"], target)
        # No forced clicks or direct application method calls.
        node.click()

    def fit(self, name):
        value = metrics(self.frame)
        self.check(name + " has no horizontal document overflow",
                   value["document"]["width"] <= value["viewport"]["width"] + 1, value)
        if self.profile[3] != "native":
            parent = self.page.evaluate("""() => {
              const r=document.querySelector('iframe').getBoundingClientRect();
              return {left:r.left,right:r.right,width:innerWidth,document:document.documentElement.scrollWidth};
            }""")
            self.check("Embedded widget stays within the parent width",
                       parent["left"] >= 0 and parent["right"] <= parent["width"] + 1
                       and parent["document"] <= parent["width"] + 1, parent)
        return value

    def capture(self, name):
        path = self.output / self.profile[0] / (name + ".png")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.frame.evaluate("document.fonts.ready")
        if self.profile[3] == "native":
            self.page.screenshot(path=str(path), animations="disabled")
        else:
            self.page.locator("iframe").screenshot(path=str(path), animations="disabled")
        self.report["screenshots"].append({"view": name, "file": str(path), "sha256": sha(path.read_bytes())})

    def preserved(self, name, all_keys=False):
        actual = storage(self.frame)
        if self.profile[3] == "opaque":
            self.check(name + " does not pretend opaque storage is available", not actual["available"])
            return
        keys = tuple(self.saved) if all_keys else PROTECTED_KEYS
        changed = [key for key in keys if actual["values"].get(key) != self.saved[key]]
        self.check(name + " preserves original record bytes", not changed, changed)
        self.check(name + " does not insert new application storage keys",
                   set(actual["values"]) == set(self.saved), sorted(actual["values"]))

    def geometry(self):
        value = self.fit("Canonical home")
        self.report["home_geometry"] = value
        # Preserve both original desktop regression cases and all their giant
        # market strip / flag / overlap / narrow-workspace assertions.
        if self.profile[1] >= 1180:
            self.check("Market strip is not oversized",
                       value["row"] is not None and value["row"]["height"] <= MAX_CARD_HEIGHT, value["row"])
            self.check("Market cards cannot become full-screen overlays",
                       len(value["cards"]) == 4 and all(0 < c["height"] <= MAX_CARD_HEIGHT
                                                       for c in value["cards"]), value["cards"])
            self.check("Market strip does not overlap the research workspace",
                       value["main"] is not None and value["main"]["y"] >= value["row"]["bottom"] - 3, value)
            self.check("Research workspace keeps the original desktop width",
                       value["main"] is not None and value["main"]["width"] >= self.profile[1] * .8, value["main"])
        flag = value["flag"]
        self.check("Sentiment flag is styled instead of becoming a giant SVG",
                   flag is not None and 0 < flag["width"] <= 32 and 0 < flag["height"] <= 28, flag)
        self.check("All four sourced market cards remain present", len(value["cards"]) == 4)
        self.check("Market values and genuine chart ink remain visible inside their cards",
                   all(c["value_visible"] and c["plot_visible"] and c["number"] and c["ink"]
                       and c["number"]["width"] > 0 and c["ink"]["width"] > 0
                       and c["ink_inside_card"] for c in value["cards"]), value["cards"],
                   baseline_observation=True)
        self.check("Market chart ink does not overlap the actual numeric text",
                   all(c["overlap_area"] == 0 for c in value["cards"]), value["cards"],
                   baseline_observation=True)

    def detail_matches(self, company, name):
        text = self.frame.locator(".fx-d-quote strong").inner_text().strip()
        number = re.sub(r"[^0-9.+-]", "", text)
        expected = company.get("price")
        tolerance = .51 if company.get("currency") == "KRW" else .0051
        self.check(name + " keeps the actual company name and ticker",
                   company["name"] in self.frame.locator(".fx-detail-intro h2").inner_text()
                   and self.frame.locator(".fx-d-security small").inner_text().split(" · ")[0]
                   == str(company["symbol"]))
        self.check(name + " renders the captured price at its displayed precision",
                   bool(number) and isinstance(expected, (int, float))
                   and abs(float(number) - expected) <= tolerance,
                   {"captured": expected, "rendered": text, "tolerance": tolerance})

    def full_flow(self):
        self.open()
        self.geometry()
        before = snapshot(self.frame)
        self.check("Rendered companies equal the actual captured source",
                   before["data"]["raw"] == self.raw)
        self.capture("home")
        self.click('.fx-nav [data-nr-screen="stockdetail"]')
        self.frame.locator(".fx-detail-v6").wait_for()
        self.fit("Company detail")
        self.detail_matches(self.primary, "Initial detail")
        self.capture("detail")
        self.click('.fx-detail-v6 [data-nr-screen="stocks"]')
        self.click('.fx-nav [data-nr-screen="home"]')
        self.preserved("Home/detail/back navigation", all_keys=True)
        self.check("Read-only navigation does not modify any captured market data",
                   snapshot(self.frame)["data"] == before["data"])

        self.click('.fx-nav [data-nr-screen="stocks"]')
        self.click('[data-rf-market="NASDAQ"]')
        listed = self.frame.locator('.fx-row[data-nr-select]')
        self.check("NASDAQ market filter uses existing companies", listed.count() > 0)
        markets = json.loads(self.captured["stock-market-groups.json"])
        def venue(company):
            key = company.get("source_symbol") or company["symbol"]
            info = next((markets.get("members", {}).get(k) for k in
                         [key, company["symbol"], str(key)+".KS", str(key)+".KQ"]
                         if markets.get("members", {}).get(k)), {})
            return info.get("venue") or {"NMS":"NASDAQ", "NGM":"NASDAQ", "NCM":"NASDAQ"}.get(company.get("exchange"))
        nasdaq = [c for c in self.raw["companies"] if venue(c) == "NASDAQ"]
        shown = listed.evaluate_all("nodes=>nodes.map(n=>n.dataset.nrSelect)")
        self.check("Market filter contains only captured NASDAQ members",
                   set(shown).issubset({str(c["symbol"]) for c in nasdaq}), shown)
        # Symbols such as ON also occur in other company names. Pick a real
        # unambiguous query instead of incorrectly requiring substring search
        # to behave like an exact-ticker filter.
        company = next((c for c in nasdaq if sum(str(c["symbol"]).lower() in
                       (str(o["name"])+" "+str(o["symbol"])).lower() for o in nasdaq) == 1), None)
        self.check("Captured NASDAQ data contains an unambiguous real search query", company is not None)
        symbol = str(company["symbol"])
        search = self.frame.locator("#fx-search-input")
        search.fill(symbol)
        expect(self.frame.locator('.fx-row[data-nr-select]')).to_have_count(1)
        self.check("Search result corresponds to the actual requested company",
                   self.frame.locator('.fx-row[data-nr-select]').first.get_attribute("data-nr-select") == symbol)
        self.capture("search")
        self.click('.fx-row[data-nr-select]')
        self.click('.fx-focus [data-nr-detail]')
        self.frame.locator(".fx-detail-v6").wait_for()
        self.detail_matches(company, "Search-to-detail")
        self.preserved("Search/market selection")
        if self.profile[3] != "opaque":
            values = storage(self.frame)["values"]
            self.check("Selection metadata changes only to the chosen symbol and market",
                       values[SELECTION_KEYS[0]] == json.dumps(symbol)
                       and values[SELECTION_KEYS[1]] == '"NASDAQ"')
        else:
            self.check("Blocked save is disclosed in the opaque sandbox",
                       "브라우저 저장 실패" in self.frame.locator("#source-status").inner_text())
        self.click('.fx-nav [data-nr-screen="home"]')
        self.fit("Home after search")
        self.preserved("Return from searched company")
        if self.profile[3] != "opaque":
            selected = snapshot(self.frame)
            persisted = storage(self.frame)
            # Open the canonical URL without an explicit stock query, so the
            # deliberate query-parameter override cannot mask storage recovery.
            self.frame.goto(self.app_origin + "/stock-value-radar.html", wait_until="domcontentloaded")
            self.settle()
            recovered = snapshot(self.frame)
            self.check("Selected company and market survive reopening the plain URL",
                       recovered["selected"] == selected["selected"]
                       and recovered["market"] == selected["market"])
            self.check("Reopening preserves every existing record byte",
                       storage(self.frame) == persisted)
            self.preserved("Reopening the widget")
            self.capture("reopened")
        else:
            self.report["persistence"] = {
                "status": "unavailable", "reason": "Opaque sandbox denies localStorage; no durable-save claim."}

        current = snapshot(self.frame)
        self.raw_failure = True
        failures = sum(r["status"] == 503 for r in self.requests)
        self.click("[data-fx-refresh]")
        self.frame.wait_for_function("""() => {
          const text=document.querySelector('#source-status')?.textContent||'';
          return text.includes('raw 조회 실패') && !text.includes('자료 재조회 중');
        }""")
        self.check("Controlled HTTP503 was actually requested",
                   sum(r["status"] == 503 for r in self.requests) > failures)
        self.check("Failed refresh keeps the exact last successful company snapshot",
                   snapshot(self.frame)["data"]["raw"] == current["data"]["raw"])
        self.check("Failed refresh visibly explains use of the previous observation",
                   "직전 정상 자료 유지" in self.frame.locator("#source-status").inner_text())
        self.check("Failure cannot invent or remove companies",
                   [c["symbol"] for c in snapshot(self.frame)["data"]["raw"]["companies"]]
                   == [c["symbol"] for c in self.raw["companies"]])
        self.capture("source-failure")
        self.raw_failure = False
        requests = len(self.requests)
        self.click("[data-fx-refresh]")
        self.settle()
        self.check("Recovery makes a new successful raw request",
                   any(r["file"] == "stock-opportunity-data.json" and r["status"] == 200
                       for r in self.requests[requests:]))
        self.check("Recovery removes the raw-source failure warning",
                   "raw 조회 실패" not in self.frame.locator("#source-status").inner_text())
        self.preserved("Failure and successful retry")
        self.check("Normal source bytes remain unchanged after retry",
                   snapshot(self.frame)["data"]["raw"] == self.raw)
        self.fit("Recovered home")
        self.capture("recovered")
        self.check("No runtime page errors", not self.errors, self.errors)
        self.check("No unrecorded external network calls", not self.external, self.external)
        self.check("Every requested data endpoint has an immutable captured response",
                   not self.unrecorded_data, self.unrecorded_data)
        self.report["data_requests"] = self.requests
        self.report["passed"] = all(c["passed"] for c in self.checks)

    def run(self):
        try:
            self.full_flow()
        except Exception as error:
            self.report["error"] = str(error)
            self.report["traceback"] = traceback.format_exc()
            if self.page is not None and self.frame is not None:
                try:
                    self.capture("failure")
                except Exception:
                    pass
        finally:
            self.report["data_requests"] = self.requests
            self.report["unrecorded_data_requests"] = self.unrecorded_data
            self.report["source_files_before"] = self.source_before
            self.report["source_files_after"] = source_fingerprints(self.root)
            self.report["source_unchanged"] = self.report["source_files_before"] == self.report["source_files_after"]
            if not self.report["source_unchanged"]:
                self.report["passed"] = False
                self.report["error"] = "Source files changed during this browser case; rerun the frozen source."
            if self.context is not None:
                self.context.close()
            self.server.shutdown()
            self.server.server_close()
            if self.parent_server is not None:
                self.parent_server.shutdown()
                self.parent_server.server_close()
        return self.report


def compare_captures(browser, cases):
    before = {(c["profile"], s["view"]): s for c in cases if c["phase"] == "before"
              for s in c["screenshots"]}
    after = {(c["profile"], s["view"]): s for c in cases if c["phase"] == "after"
             for s in c["screenshots"]}
    pairs = []
    page = browser.new_page()
    try:
        for key in sorted(before.keys() & after.keys()):
            old, new = before[key], after[key]
            row = {"profile": key[0], "view": key[1], "before": old["file"], "after": new["file"],
                   "png_bytes_identical": old["sha256"] == new["sha256"]}
            if row["png_bytes_identical"]:
                row["differing_pixels"] = 0
            else:
                sources = ["data:image/png;base64," + base64.b64encode(Path(s["file"]).read_bytes()).decode()
                           for s in [old, new]]
                row["pixel_comparison"] = page.evaluate(r"""async sources => {
                  const images=await Promise.all(sources.map(src=>new Promise((resolve,reject)=>{
                    const image=new Image();image.onload=()=>resolve(image);image.onerror=reject;image.src=src;
                  })));
                  const [a,b]=images;if(a.width!==b.width||a.height!==b.height)
                    return {same_dimensions:false,before:[a.width,a.height],after:[b.width,b.height]};
                  const pixels=images.map(image=>{
                    const c=document.createElement('canvas');c.width=image.width;c.height=image.height;
                    const ctx=c.getContext('2d');ctx.drawImage(image,0,0);return ctx.getImageData(0,0,c.width,c.height).data;
                  });let count=0,left=a.width,top=a.height,right=-1,bottom=-1;
                  for(let i=0;i<pixels[0].length;i+=4){if([0,1,2,3].some(k=>pixels[0][i+k]!==pixels[1][i+k])){
                    count++;const x=(i/4)%a.width,y=Math.floor(i/4/a.width);
                    left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
                  }}return {same_dimensions:true,width:a.width,height:a.height,differing_pixels:count,
                    changed_bounds:count?{left,top,right,bottom}:null};
                }""", sources)
            pairs.append(row)
    finally:
        page.close()
    return {"status": "captured", "pairs": pairs,
            "missing_before": sorted([list(k) for k in after.keys()-before.keys()]),
            "missing_after": sorted([list(k) for k in before.keys()-after.keys()]),
            "scope": "Same actual candidate data, clock, stored-user-record fixture and viewports. Pixel differences are review evidence, not automatic design approval."}


def main():
    args = arguments()
    root, output = args.root.resolve(), args.output.resolve()
    baseline = args.baseline_root.resolve() if args.baseline_root else None
    for source in [root, *([baseline] if baseline else [])]:
        if output == source or output.is_relative_to(source):
            raise SystemExit("Browser artifacts must be outside the candidate and baseline checkouts")
        if not (source / "stock-value-radar.html").is_file():
            raise SystemExit("Missing canonical page: " + str(source))
    output.mkdir(parents=True, exist_ok=True)
    report = {"scope": "Actual captured candidate JSON, isolated stored-user-record fixtures, fixed observation clock, local HTTP browser tests. No live market fetch, publication, broker, authenticated Notion or Safari verification.",
              "candidate": str(root), "baseline": str(baseline) if baseline else None,
              "pass_policy": "All candidate profiles and frozen data/source checks must pass. Reproduced baseline failures remain separately false in cases/baseline_failed_cases; they are never counted as candidate passes.",
              "cases": [], "passed": False}
    try:
        captured, raw, primary, saved, clock = fixtures(root)
        initial = {name: sha(value) for name, value in captured.items()}
        report.update({"captured_data_sha256": initial, "actual_companies": len(raw["companies"]),
                       "clock": clock.isoformat(), "storage_fixture_scope": "Synthetic preexisting USER records referencing actual companies/observed prices; market responses are never synthetic.",
                       "source_html_sha256": sha((root / "stock-value-radar.html").read_bytes()),
                       "harness_sha256": sha(Path(__file__).read_bytes())})
        with sync_playwright() as api:
            options = {"headless": True, "args": ["--no-sandbox"]}
            if args.browser_executable:
                options["executable_path"] = args.browser_executable
            browser = api.chromium.launch(**options)
            try:
                sources = [("before", baseline)] if baseline else []
                sources.append(("after", root))
                for phase, source in sources:
                    for profile in PROFILES:
                        case = Scenario(browser, source, captured, raw, primary, saved, clock,
                                        output / phase, profile, baseline=phase == "before").run()
                        case["phase"] = phase
                        report["cases"].append(case)
                        print(phase, profile[0], "PASS" if case["passed"] else "FAIL", case.get("error", ""), flush=True)
                if baseline:
                    report["comparison"] = compare_captures(browser, report["cases"])
            finally:
                browser.close()
        report["source_data_unchanged"] = all(sha((root / name).read_bytes()) == digest
                                               for name, digest in initial.items())
        current = [case for case in report["cases"] if case["phase"] == "after"]
        previous = [case for case in report["cases"] if case["phase"] == "before"]
        report["baseline_passed"] = all(case["passed"] for case in previous) if baseline else None
        report["baseline_failed_cases"] = [case["profile"] for case in previous if not case["passed"]]
        report["source_files_unchanged"] = all(case.get("source_unchanged", False) for case in report["cases"])
        # A reproduced preexisting baseline failure remains visible. It must
        # not turn a fixed candidate red, or be relabeled as a baseline pass.
        report["passed"] = (len(current) == len(PROFILES) and all(case["passed"] for case in current)
                            and report["source_data_unchanged"] and report["source_files_unchanged"])
        if not baseline:
            report["comparison"] = {"status": "not_run", "reason": "No --baseline-root was supplied."}
    except Exception as error:
        report["setup_error"] = str(error)
        report["traceback"] = traceback.format_exc()
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "cases": len(report["cases"]),
                      "output": str(output), "setup_error": report.get("setup_error")}, ensure_ascii=False), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
