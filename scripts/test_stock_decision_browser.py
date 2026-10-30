"""Check current radar v9 flows with real collected JSON in Chromium.

The source checkout is served locally and its captured JSON replaces only the
widget's raw-GitHub data requests. The browser clock is fixed just after that
snapshot for the normal case; stale/failure cases change responses in memory.
This is deterministic UI QA, not a claim that an old snapshot is current.

Replaces v7's fixed ten-row/overlay selectors with v9 candidate pagination,
company details, explicit first choices and the broad discovery directory.
Preserves the earlier price-condition, different-company, source-link, stale,
failure, no-training-form and desktop/mobile layout checks.
"""
import argparse
import copy
import functools
import hashlib
import http.server
import json
import math
import re
import threading
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


DATA_FILES = (
    "stock-opportunity-data.json",
    "stock-opportunity-discovery.json",
    "stock-official-audit.json",
    "stock-radar-health.json",
    "stock-investment-cases.json",
    "stock-market-groups.json",
)
STATE_LABELS = {
    "ready": "명시 조건 충족 · 매수 후보",
    "verify": "가격·실적 후보 · 공식 대조 전",
    "price": "가격을 기다릴 후보",
    "risk": "실제 위험 먼저 확인",
    "data": "판단 자료 보강",
}
STRICT_STATE_LABELS = {
    "attractive": "핵심 검증 통과 · 조건부 투자 후보",
    "conditional": "좋은 점은 있지만 핵심 검증이 남았어요",
    "price_wait": "회사는 괜찮지만, 더 싸게 기다려요",
    "avoid": "위험 신호의 원인을 먼저 확인해요",
    "insufficient": "자료가 부족해서 아직 판단할 수 없어요",
}
PUBLIC_URL = "https://ohoredingdong.github.io/Notion/stock-value-radar.html"


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(),
                        help="Checkout containing the current HTML/assets/JSON.")
    parser.add_argument("--output", type=Path,
                        help="Artifact directory; defaults to <root>/decision-browser-tests.")
    parser.add_argument("--browser-executable",
                        help="Optional existing Chromium; CI uses Playwright's installed browser.")
    return parser.parse_args()


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def visible_number(value):
    return float(re.sub(r"[^0-9.+-]", "", value))


def normalized_urls(values):
    return {urllib.parse.unquote(value).rstrip("/") for value in values}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class RadarChecks:
    def __init__(self, root, output):
        self.root, self.output = root, output
        self.snapshots = {name: json.loads((root / name).read_text()) for name in DATA_FILES}
        self.data = self.snapshots["stock-opportunity-data.json"]
        self.directory = self.snapshots["stock-opportunity-discovery.json"]
        require(isinstance(self.data.get("companies"), list) and self.data["companies"],
                "A real nonempty collected decision snapshot is required.")
        require(isinstance(self.directory.get("companies"), list) and self.directory["companies"],
                "A real nonempty discovery snapshot is required.")
        self.companies = {row["symbol"]: row for row in self.data["companies"]}
        self.case_snapshot = self.snapshots.get("stock-investment-cases.json") or {}
        self.case_by_symbol = {row["symbol"]: row for row in self.case_snapshot.get("companies", [])}
        require(len(self.companies) == len(self.data["companies"]), "Duplicate decision symbols.")
        require("MSFT" in self.companies and "000660" in self.companies,
                "The existing Microsoft/SK Hynix regression examples must remain in the snapshot.")
        self.generated = datetime.fromisoformat(self.data["generated_at"].replace("Z", "+00:00"))
        require(self.generated.tzinfo is not None, "Snapshot generated_at must include a timezone.")
        evidence_times = [self.generated]
        for value in [self.case_snapshot.get("generated_at")]:
            if value:
                try:
                    evidence_times.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
                except ValueError:
                    pass
        for case in self.case_by_symbol.values():
            reviewed = (case.get("green_review") or {}).get("reviewed_at")
            if reviewed:
                try:
                    evidence_times.append(datetime.fromisoformat(reviewed.replace("Z", "+00:00")))
                except ValueError:
                    pass
        self.normal_time = max(evidence_times) + timedelta(minutes=1)
        require((self.normal_time - self.generated) <= timedelta(hours=float(self.data.get("max_age_hours", 18))),
                "Captured strict-review evidence is already outside the raw-data freshness window.")
        self.report = {
            "cases": [], "errors": [],
            "mode": "Real collected JSON + checked-out v9 widget; separate public HTML observation",
            "source": {
                "root": str(root),
                "generated_at": self.data["generated_at"],
                "browser_clock": self.normal_time.isoformat(),
                "companies": len(self.companies),
                "directory_companies": len(self.directory["companies"]),
                "sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                           for name in ("stock-value-radar.html", *DATA_FILES)},
            },
        }

    def record(self, name, detail=""):
        self.report["cases"].append({"name": name, "passed": True, "detail": detail})
        print("PASS " + name, flush=True)

    def failed(self, name, error):
        detail = type(error).__name__ + ": " + str(error)
        self.report["cases"].append({"name": name, "passed": False, "detail": detail})
        self.report["errors"].append(name + ": " + detail)

    def install_routes(self, page, origin, state, requests):
        local_host = urllib.parse.urlparse(origin).netloc

        def intercept(route):
            parsed = urllib.parse.urlparse(route.request.url)
            name = Path(parsed.path).name
            if parsed.netloc == "raw.githubusercontent.com" and name in DATA_FILES:
                requests.append(name)
                if name == "stock-opportunity-data.json":
                    if state["decision"] == "failure":
                        route.fulfill(status=503, content_type="text/plain",
                                      body="Controlled decision source failure")
                        return
                    value = self.data
                    if state["decision"] == "stale":
                        value = copy.deepcopy(value)
                        max_age = float(self.data.get("max_age_hours", 18))
                        value["generated_at"] = (
                            self.normal_time - timedelta(hours=max_age + 1)
                        ).isoformat()
                elif name == "stock-opportunity-discovery.json" and state["directory_failure"]:
                    route.fulfill(status=503, content_type="text/plain",
                                  body="Controlled directory source failure")
                    return
                else:
                    value = self.snapshots[name]
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(value, ensure_ascii=False))
                return
            if parsed.netloc == local_host:
                route.continue_()
                return
            requests.append("unexpected: " + parsed.scheme + "://" + parsed.netloc + parsed.path)
            route.fulfill(status=404, content_type="text/plain",
                          body="Unrecorded external resource")
        page.route("**/*", intercept)

    def new_page(self, browser, origin, width, height, state):
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1, timezone_id="Asia/Seoul",
        )
        page = context.new_page()
        page.set_default_timeout(10000)
        page.clock.set_fixed_time(self.normal_time)
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        self.install_routes(page, origin, state, requests)
        page.goto(origin + "/stock-value-radar.html", wait_until="networkidle")
        return context, page, errors, requests

    def fresh(self, page):
        expect(page.locator("#reload")).to_be_enabled()
        expect(page.locator("#liveStatus")).not_to_have_class(re.compile(r"\berror\b"))
        require(page.locator("#companySelect option").count() == len(self.companies),
                "The last valid detailed-company inventory must remain available.")

    def layout(self, page, name):
        dimensions = page.evaluate(
            "() => ({viewport: innerWidth, document: document.documentElement.scrollWidth, "
            "body: document.body.scrollWidth})"
        )
        require(dimensions["document"] <= dimensions["viewport"] + 1 and
                dimensions["body"] <= dimensions["viewport"] + 1, str(dimensions))
        self.record(name, dimensions)

    def screenshot(self, page, name):
        page.screenshot(path=str(self.output / (name + ".png")), full_page=True)

    def select_company(self, page, symbol):
        page.evaluate("document.getElementById('tab-detail').click()")
        page.locator("#companySelect").select_option(symbol)
        expect(page.locator("#view-detail")).to_be_visible()
        expect(page.locator("#detailBody .company-heading h2")).to_have_text(
            self.companies[symbol]["name"]
        )

    def company_detail(self, page, symbol, label):
        row = self.companies[symbol]
        self.select_company(page, symbol)
        require(page.locator("#detailBody").count() == 1 and
                page.locator("#detailBody .company-heading").count() == 1,
                "Company navigation must replace one research view, not accumulate overlays.")
        strict = self.case_by_symbol.get(symbol)
        strict_current = (
            strict
            and self.case_snapshot.get("source_generated_at") == self.data.get("generated_at")
            and strict.get("input_price") == row.get("price")
            and strict.get("input_price_session") == row.get("price_session")
            and strict.get("input_forecast_eps") == (row.get("forecasts", {}).get("next_fy", {}).get("avg"))
        )
        green = (strict.get("green_review") or {}) if strict else {}
        green_inputs_aligned = (
            strict_current
            and green
            and green.get("version") == "strict-green-1.0"
            and green.get("source_generated_at") == self.data.get("generated_at")
            and green.get("input_price") == row.get("price")
            and green.get("input_price_session") == row.get("price_session")
            and green.get("input_forecast_eps") == (row.get("forecasts", {}).get("next_fy", {}).get("avg"))
        )
        def _dt(value):
            if not value:
                return None
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return None
        reviewed_at = _dt(green.get("reviewed_at"))
        valid_until = _dt(green.get("valid_until"))
        green_time_aligned = (
            reviewed_at is not None and valid_until is not None
            and reviewed_at <= self.normal_time + timedelta(minutes=5)
            and self.normal_time - reviewed_at <= timedelta(hours=18)
            and valid_until > self.normal_time
        )
        effective_state = (
            "insufficient" if strict_current and green and not (green_inputs_aligned and green_time_aligned)
            else strict.get("state") if strict_current
            else None
        )
        expected_heading = (
            STRICT_STATE_LABELS.get(effective_state)
            if strict_current else STATE_LABELS[row["assessment"]["state"]]
        )
        expect(page.locator("#detailBody .decision-grid > .panel").first.locator("h3")).to_have_text(
            expected_heading
        )
        tolerance = 0.51 if row["currency"] == "KRW" else 0.0051
        quote = visible_number(page.locator("#detailBody .company-quote strong").inner_text())
        require(math.isclose(quote, row["price"], rel_tol=0, abs_tol=tolerance),
                f"{symbol} displayed quote is not the collected quote.")
        if strict_current:
            price_text = page.locator("#detailBody .plain-price-guide").first.inner_text()
            require("독립평가 매수 참고선" in price_text,
                    "Strict detail must distinguish independent valuation from analyst target prices.")
            green_eligible = green.get("green_eligible") is True and green_inputs_aligned
            if not green_eligible:
                require("평가 근거 확인 전" in price_text,
                        "An unapproved strict review must not expose an independent-value buy line.")
            condition = "strict independent valuation" if green_eligible else "blocked pending strict evidence"
        else:
            displayed = visible_number(
                page.locator("#detailBody .condition-price").first.locator("strong").inner_text()
            )
            expected = row["targets"]["median"] / 1.20
            require(math.isclose(displayed, expected, rel_tol=0, abs_tol=tolerance),
                    f"{symbol} legacy condition price {displayed} != target median / 1.20 ({expected}).")
            condition = displayed
        self.record(label + " " + symbol + " collected quote and current valuation gate",
                    {"assessment": expected_heading, "quote": quote, "condition": condition})
        body = page.locator("#detailBody").text_content()
        if strict_current:
            visible_strict = page.locator("#detailBody .case-primary").inner_text()
            pending = [x for x in (strict.get("green_review") or {}).get("checks", [])
                       if x.get("status") != "pass"]
            for item in pending[:3]:
                require(item.get("term", "") in visible_strict,
                        f"{symbol} visible strict-review task missing: {item.get('term')}")
        for reason in row["assessment"].get("risks", []):
            require(reason in body, f"{symbol} risk explanation missing: {reason}")
        expected_sources = normalized_urls(
            row["sources"][key] for key in ("estimates", "history", "official", "cashflow", "balance")
        )
        anchors = page.locator("#detailBody a[href]")
        actual_sources = normalized_urls(anchors.evaluate_all("(nodes) => nodes.map(n => n.href)"))
        require(expected_sources <= actual_sources,
                "Displayed numeric research must retain all five collected source destinations.")
        source_anchors = anchors.evaluate_all(
            "(nodes) => nodes.map(n => ({href:decodeURIComponent(n.href).replace(/\\/$/,''),"
            "target:n.target,rel:n.rel,text:n.textContent.trim()}))"
        )
        unsafe_external = [a for a in source_anchors if a["href"] in expected_sources and
                           not (a["target"] == "_blank" and
                                "noopener" in a["rel"] and "noreferrer" in a["rel"])]
        require(not unsafe_external,
                "Expected external source links must retain safe external-link attributes: " + str(unsafe_external))
        self.record(label + " " + symbol + " distinct risks and numeric source links",
                    {"sources": len(expected_sources), "risk_reasons": len(row["assessment"].get("risks", []))})
        self.layout(page, label + " " + symbol + " detail width")
        self.screenshot(page, label + "-" + symbol)

    def normal_flow(self, browser, origin, width, height, label):
        state = {"decision": "normal", "directory_failure": False}
        context, page, errors, requests = self.new_page(browser, origin, width, height, state)
        try:
            self.fresh(page)
            require(page.locator('script[src*="stock-radar-v9.js"]').count() == 1,
                    "The current v9 extension must be included exactly once.")
            if page.locator("#view-home").count():
                expect(page.locator("#view-home")).to_be_visible()
                expect(page.locator("#nr-home-content")).to_be_visible()
                require(page.locator("#nr-company,#nr-ops-panel,#nr-comparison").count() == 3,
                        "Neutral home must expose company, operations and comparison panels.")
                self.record(label + " neutral home exposes comparison, company and operating status")
                page.locator('.nr-rail [data-nr-view="discover"]').click()
                expect(page.locator("#view-discover")).to_be_visible()
            require(page.locator("#companySelect option").count() == len(self.companies),
                    "The selector must include every collected company, not a fixed ten-row fixture.")
            expect(page.locator("#listCount")).to_have_text(
                f"{len(self.companies)}개 / 전체 {len(self.companies)}개"
            )
            visible = page.locator("#cards .name-button").evaluate_all(
                "(nodes) => nodes.map(n => n.dataset.open)"
            )
            require(len(set(visible)) == len(visible) and set(visible) <= set(self.companies),
                    "Initial cards must be unique collected companies.")
            self.record(label + " current v9 and complete collected candidate inventory",
                        {"total": len(self.companies), "initial_cards": len(visible)})
            require(page.locator("textarea, input[type=number], form").count() == 0 and
                    page.locator("#decision-v7-panel,#decision-v7-home,#v6Save,#v6Reason").count() == 0,
                    "The research tool must not contain old overlays or training/order entry forms.")
            self.record(label + " one research UI without legacy or training forms")
            brief = self.data.get("decision_brief") or {}
            now = brief.get("now", [])
            expect(page.locator("#todayBrief")).not_to_be_empty()
            strict_cards = page.locator("#todayBrief .brief-card")
            warning = page.locator("#todayBrief .brief-warning")
            require(strict_cards.count() > 0 or warning.count() > 0 or
                    "없어요" in page.locator("#todayBrief").inner_text(),
                    "The first-choice area must show strict candidates or an explicit fail-closed state.")
            shown = page.locator("#todayBrief [data-brief]").evaluate_all(
                "(nodes) => [...new Set(nodes.map(n => n.dataset.brief).filter(Boolean))]"
            )
            require(set(shown) <= set(self.companies),
                    "First-choice UI may only link to collected companies.")
            self.record(label + " strict first-choice area is populated or explicitly fail-closed",
                        {"raw_brief": [row["symbol"] for row in now], "shown": shown})
            self.layout(page, label + " overview width")
            self.screenshot(page, label + "-overview")

            if len(self.companies) > 9:
                page.locator("#more").click()
                expect(page.locator("#cards .candidate")).to_have_count(min(18, len(self.companies)))
                self.record(label + " candidate pagination reveals the next collected page")
            if shown:
                first = shown[0]
                page.locator('#todayBrief [data-brief="'+first+'"]').first.click()
                expect(page.locator("#detailBody .company-heading h2")).to_have_text(
                    self.companies[first]["name"]
                )
                self.record(label + " first-choice button opens the matching collected company")

            page.locator('.nr-rail [data-nr-view="discover"]').click()
            page.locator("#search").fill("MSFT")
            expect(page.locator("#cards .name-button")).to_have_count(1)
            expect(page.locator("#cards .name-button")).to_have_attribute("data-open", "MSFT")
            page.locator("#market").select_option("KR")
            expect(page.locator("#cards .candidate")).to_have_count(0)
            expect(page.locator("#cards")).to_contain_text("해당하는 종목이 없습니다")
            page.locator("#market").select_option("ALL")
            expect(page.locator("#cards .name-button")).to_have_count(1)
            page.locator('#cards .name-button[data-open="MSFT"]').click()
            self.record(label + " search and market filters use actual companies and empty state")
            self.company_detail(page, "MSFT", label)
            self.company_detail(page, "000660", label)

            page.locator('.nr-rail [data-nr-view="discover"]').click()
            page.locator("#search").fill("")
            page.locator('[data-mode="short"]').click()
            ready = [row for row in self.companies.values()
                     if row["status"] == "current"
                     and row.get("short", {}).get("state") == "conditional"
                     and row.get("period_integrity", {}).get("status") == "ok"]
            expect(page.locator("#todayBrief .brief-open")).to_have_count(min(3, len(ready)))
            expect(page.locator("#listTitle")).to_have_text("완료 거래일의 단기 조건")
            self.record(label + " short-term view stays separate from long-term first choices",
                        {"qualifying_short_companies": len(ready)})
            page.locator('[data-mode="long"]').click()

            page.locator("#wideDirectory > summary").click()
            directory_rows = self.directory["companies"]
            expect(page.locator("#directoryRows tbody tr")).to_have_count(min(40, len(directory_rows)))
            expect(page.locator("#directoryCount")).to_have_text(
                f"{len(directory_rows)}개 / 기본 탐색 {len(directory_rows)}개 · 정밀분석 {len(self.companies)}개"
            )
            if len(directory_rows) > 40:
                page.locator("#directoryMore").click()
                expect(page.locator("#directoryRows tbody tr")).to_have_count(min(80, len(directory_rows)))
            self.record(label + " v9 directory counts and pagination use captured discovery data")
            deep = next(row for row in directory_rows if row["symbol"] in self.companies)
            shallow = next(row for row in directory_rows if row["symbol"] not in self.companies)
            page.locator("#directorySearch").fill(shallow["symbol"])
            shallow_row = page.locator("#directoryRows tbody tr").filter(
                has=page.locator(".directory-symbol").filter(
                    has_text=re.compile(r"^" + re.escape(shallow["symbol"]) + r"\b")
                )
            )
            expect(shallow_row).to_contain_text("기본 탐색만")
            require(shallow_row.get_by_role("button", name="정밀분석 보기 ›").count() == 0,
                    "A discovery-only company must not masquerade as completed analysis.")
            require(normalized_urls(shallow_row.locator("a").evaluate_all(
                "(nodes) => nodes.map(n => n.href)"
            )) == normalized_urls([shallow["source_url"]]), "Discovery source link changed.")
            self.record(label + " directory distinguishes basic exploration from completed analysis")
            self.layout(page, label + " expanded directory width")
            self.screenshot(page, label + "-directory")
            page.locator("#directorySearch").fill(deep["symbol"])
            deep_row = page.locator("#directoryRows tbody tr").filter(
                has=page.locator(".directory-symbol").filter(
                    has_text=re.compile(r"^" + re.escape(deep["symbol"]) + r"\b")
                )
            )
            deep_row.get_by_role("button", name="정밀분석 보기 ›").click()
            expect(page.locator("#detailBody .company-heading h2")).to_have_text(
                self.companies[deep["symbol"]]["name"]
            )
            self.record(label + " directory deep-analysis link opens the correct company")
            page.locator('.nr-rail [data-nr-view="system"]').click()
            expect(page.locator("#systemBody")).to_contain_text("수집 시각과 기준")
            expect(page.locator("#systemBody")).to_contain_text("18시간")
            self.record(label + " source status and freshness policy remain accessible")

            self.select_company(page, "MSFT")
            previous_quote = page.locator("#detailBody .company-quote strong").inner_text()
            previous_observation = page.locator("#detailBody .company-heading p").inner_text()
            for fault in ("stale", "failure"):
                state["decision"] = fault
                page.locator("#reload").click()
                expect(page.locator("#reload")).to_be_enabled()
                expect(page.locator("#liveStatus")).to_have_class(re.compile(r"\berror\b"))
                expect(page.locator("#detailBody .decision-grid > .panel").first.locator("h3")).to_have_text(
                    "새 자료가 올 때까지 평가 중지"
                )
                expect(page.locator("#todayBrief .brief-warning")).to_contain_text(
                    "우선 매수 후보를 표시하지 않습니다"
                )
                require(page.locator("#cards .candidate.ready").count() == 0,
                        "Failed or stale data must not retain a current ready badge.")
                require(page.locator("#detailBody .company-quote strong").inner_text() == previous_quote and
                        page.locator("#detailBody .company-heading p").inner_text() == previous_observation,
                        "Failure must preserve the last valid quote and its original collection time.")
                self.record(label + " " + fault + " pauses judgments and retains last observation")
                self.screenshot(page, label + "-" + fault)
                state["decision"] = "normal"
                page.locator("#reload").click()
                self.fresh(page)
                expect(page.locator("#todayBrief")).not_to_be_empty()
                require(page.locator("#todayBrief .brief-card").count() > 0 or
                        page.locator("#todayBrief .brief-warning").count() > 0 or
                        "없어요" in page.locator("#todayBrief").inner_text(),
                        "Recovery must restore strict candidates or an explicit fail-closed state.")
                self.record(label + " recovery after " + fault + " restores current strict research")

            require(not errors, "; ".join(errors))
            require(not [url for url in requests if url.startswith("unexpected:")],
                    "Unexpected external requests: " + str(requests))
            self.record(label + " no runtime errors or unrecorded external data requests")
        finally:
            context.close()

    def initial_failure_and_directory_recovery(self, browser, origin):
        state = {"decision": "failure", "directory_failure": False}
        context, page, errors, _requests = self.new_page(browser, origin, 320, 844, state)
        try:
            expect(page.locator("#liveStatus")).to_have_class(re.compile(r"\berror\b"))
            if page.locator('.nr-rail [data-nr-view="discover"]').count():
                page.locator('.nr-rail [data-nr-view="discover"]').click()
                expect(page.locator("#view-discover")).to_be_visible()
            expect(page.locator("#cards")).to_contain_text("최신 자료를 불러오지 못했습니다")
            require(page.locator("#cards .candidate,#companySelect option").count() == 0,
                    "Initial source failure must not create zero-valued or demo candidates.")
            self.record("initial failure shows unavailable state without fabricated companies")
            self.screenshot(page, "initial-failure")
            state["decision"] = "normal"
            page.locator("#reload").click()
            self.fresh(page)
            self.record("initial failure recovers through the visible reload action")

            state["directory_failure"] = True
            page.locator("#wideDirectory > summary").click()
            expect(page.locator("#directoryRows .error-text")).to_contain_text("확장 종목 목록을 읽지 못했습니다")
            require(page.locator("#cards .candidate").count() == min(9, len(self.companies)),
                    "A separate directory failure must not discard valid research candidates.")
            self.record("directory source failure is explicit and retains valid detailed research")
            state["directory_failure"] = False
            page.locator("#wideDirectory > summary").click()
            page.locator("#wideDirectory > summary").click()
            expect(page.locator("#directoryRows tbody tr")).to_have_count(
                min(40, len(self.directory["companies"]))
            )
            self.record("directory can retry after source recovery")
            self.layout(page, "initial/directory recovery narrow layout")
            require(not errors, "; ".join(errors))
            self.record("initial/directory failure handling has no runtime errors")
        finally:
            context.close()

    def observe_publication(self):
        # As before, this observation is distinct from the local CI gate:
        # GitHub Pages may still be publishing when a push-triggered test starts.
        try:
            request = urllib.request.Request(
                PUBLIC_URL + "?verify=decision-ui-v9",
                headers={"User-Agent": "Stock-Decision-Deployment-Check/9"},
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read()
                refs = re.findall(r'<script[^>]+src=["\']([^"\']+)', body.decode())
                self.report["deployment"] = {
                    "status": response.status, "script_sources": refs,
                    "contains_v9": any("stock-radar-v9.js" in ref for ref in refs),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "matches_checked_out_html": body == (self.root / "stock-value-radar.html").read_bytes(),
                    "x_frame_options": response.headers.get("X-Frame-Options"),
                    "scope": "Independent public HTML observation; UI interactions above use captured source.",
                }
        except Exception as error:
            self.report["deployment"] = {"error": str(error)[:200], "scope": "Public HTML observation unavailable"}


def main():
    args = arguments()
    root = args.root.resolve()
    output = (args.output or root / "decision-browser-tests").resolve()
    output.mkdir(parents=True, exist_ok=True)
    checks = None
    server = None
    try:
        checks = RadarChecks(root, output)
        handler = functools.partial(QuietHandler, directory=str(root))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = "http://127.0.0.1:" + str(server.server_port)
        with sync_playwright() as playwright:
            launch = {"headless": True, "args": ["--no-sandbox"]}
            if args.browser_executable:
                launch["executable_path"] = args.browser_executable
            browser = playwright.chromium.launch(**launch)
            try:
                for width, height, label in ((1120, 900, "desktop"), (390, 844, "mobile"), (320, 844, "narrow")):
                    try:
                        checks.normal_flow(browser, origin, width, height, label)
                    except Exception as error:
                        checks.failed(label + " flow", error)
                        traceback.print_exc()
                try:
                    checks.initial_failure_and_directory_recovery(browser, origin)
                except Exception as error:
                    checks.failed("initial/directory failure flow", error)
                    traceback.print_exc()
            finally:
                browser.close()
        checks.observe_publication()
    except Exception as error:
        if checks is None:
            report = {"cases": [], "errors": [type(error).__name__ + ": " + str(error)]}
        else:
            checks.failed("test setup", error)
        traceback.print_exc()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    if checks is not None:
        report = checks.report
    report["passed"] = not report["errors"]
    report["passed_cases"] = sum(case["passed"] for case in report["cases"])
    report["failed_cases"] = sum(not case["passed"] for case in report["cases"])
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
