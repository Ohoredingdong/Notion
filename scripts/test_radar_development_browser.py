"""Read-only development checks for the investment radar and iframe embedding.

No collectors, publishers, remote APIs or real browser profiles are used. Input
prices come from the JSON served by --base-url. Fault cases deliberately abort
one endpoint and must expose unavailable/stale data rather than fabricate it.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:8766/", help="Already-running static server root")
    p.add_argument("--artifacts", type=Path, default=Path("/tmp/radar-development"))
    p.add_argument("--executable", help="Optional local Chromium; omit to use Playwright's installed browser")
    p.add_argument("--baseline-dir", type=Path, help="Prior artifact directory containing report.json and screenshots")
    return p


class Checks:
    def __init__(self, options):
        self.options = options
        self.base = options.base_url.rstrip("/") + "/"
        self.origin = (urlsplit(self.base).scheme, urlsplit(self.base).netloc)
        self.out = options.artifacts.resolve()
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + str(time.time_ns())[-7:]
        self.run = self.out / self.run_id
        self.run.mkdir(parents=True, exist_ok=False)
        self.expected = None
        self.report = {
            "version": "radar-development-browser-v1", "run_id": self.run_id,
            "started_at": datetime.now(timezone.utc).isoformat(), "base_url": self.base,
            "results": [], "screenshots": {}, "geometry": {},
            "limitations": [
                "Uses checked-in saved data; does not verify live financial-provider freshness or forecast accuracy.",
                "Iframe simulates an embedding viewport/sandbox; actual Notion UI and its current headers are unverified.",
                "Screenshots and layout comparisons require visual review; changed pixels are not automatically approved.",
            ],
        }
        try:
            self.report["commit"] = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            self.report["commit"] = None

    def assert_(self, value, message):
        self.active["assertions"] += 1
        if not value:
            raise AssertionError(message)

    def context(self, browser, width=1366, height=768):
        context = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")

        def local_only(route):
            parsed = urlsplit(route.request.url)
            if parsed.scheme in ("data", "blob", "about") or (parsed.scheme, parsed.netloc) == self.origin:
                route.continue_()
            else:
                self.active["blocked_external_hosts"].append(parsed.hostname)
                route.abort()

        context.route("**/*", local_only)
        self.context_ = context
        self.page = context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.set_default_timeout(10000)
        return self.page

    def load(self, surface, path="stock-value-radar.html", expect_data=True):
        response = surface.goto(urljoin(self.base, path), wait_until="domcontentloaded")
        self.assert_(response and response.status == 200, "Application document did not return HTTP 200")
        self.loaded(surface, expect_data)

    def loaded(self, surface, expect_data=True):
        surface.locator(".fx-topbar").wait_for(state="visible", timeout=30000)
        if expect_data:
            surface.wait_for_function(
                "() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length", timeout=30000
            )
            snapshot = surface.evaluate("() => window.StockRadarV2Bridge.snapshot().data.raw")
            self.assert_(snapshot == self.expected, "Rendered source differs from served raw JSON")
        else:
            surface.locator("#source-status").filter(has_text="종목 원자료 이용 불가").wait_for(timeout=30000)

    def geometry(self, surface, name):
        info = surface.evaluate("""() => {
            const rect = selector => {
                const el = document.querySelector(selector);
                if (!el) return null;
                const r=el.getBoundingClientRect();
                return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom};
            };
            return {width:innerWidth,height:innerHeight,documentWidth:document.documentElement.scrollWidth,
                documentHeight:document.documentElement.scrollHeight,
                main:rect('.fx-v5-main'),topbar:rect('.fx-topbar'),
                cockpit:rect('.fx-v5-cockpit'),markets:rect('.fx-v5-marketline')};
        }""")
        self.report["geometry"][name] = info
        self.assert_(info["documentWidth"] <= info["width"] + 3, f"Horizontal overflow: {info}")
        self.assert_(info["main"] and info["main"]["width"] > 0, "Research workspace is missing")
        return info

    def screenshot(self, name):
        target = self.run / (name + ".png")
        self.page.screenshot(path=str(target), full_page=True)
        self.report["screenshots"][name] = str(target.relative_to(self.out))

    def market_card_geometry(self, surface, name):
        cards = surface.evaluate("""() => {
            const rect = r => ({x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height});
            const textRects = el => {
                const range=document.createRange();
                range.selectNodeContents(el);
                return Array.from(range.getClientRects(),rect);
            };
            return Array.from(document.querySelectorAll('.fx-v5-markets .nr-index')).map(card => {
                const number=card.querySelector('.nr-num'), chart=card.querySelector('.nr-mini-chart');
                return {label:card.querySelector('h3').textContent,card:rect(card.getBoundingClientRect()),
                    number:textRects(number),change:textRects(card.querySelector('.nr-up,.nr-down,.nr-neutral')),
                    source:textRects(card.querySelector('.nr-sub')),chart:rect(chart.getBoundingClientRect()),
                    chartPoints:chart.querySelector('polyline')?.getAttribute('points'),
                    fontSize:parseFloat(getComputedStyle(number).fontSize)};
            });
        }""")
        self.report["geometry"][name + "-market-cards"] = cards
        self.assert_(len(cards) == 4, "Four saved market index cards must remain available")
        for card in cards:
            label, outer, chart = card["label"], card["card"], card["chart"]
            self.assert_(card["chartPoints"] and chart["width"] >= 40 and chart["height"] >= 20,
                f"{label}: saved trend chart is missing or unreadably small")
            self.assert_(card["fontSize"] >= 18, f"{label}: index number was made too small")
            # Text ranges cover the glyphs, unlike the full-width .nr-num block.
            for group in ("number", "change", "source"):
                self.assert_(card[group] and all(r["x"] >= outer["x"] - 1 and
                    r["right"] <= outer["right"] + 1 and r["y"] >= outer["y"] - 1 and
                    r["bottom"] <= outer["bottom"] + 1 for r in card[group]),
                    f"{label}: {group} text is clipped by its market card")
            self.assert_(chart["x"] >= outer["x"] and chart["right"] <= outer["right"] and
                chart["y"] >= outer["y"] and chart["bottom"] <= outer["bottom"],
                f"{label}: trend chart leaves its market card")
            for group in ("number", "change"):
                self.assert_(all(min(r["right"], chart["right"]) <= max(r["x"], chart["x"]) + 1 or
                    min(r["bottom"], chart["bottom"]) <= max(r["y"], chart["y"]) + 1 for r in card[group]),
                    f"{label}: saved trend chart overlaps actual {group} text")

    def selected_source_matches(self, surface):
        chosen = surface.evaluate("""() => {
            const s=window.StockRadarV2Bridge.snapshot();
            return s.data.raw.companies.find(c=>String(c.symbol)===String(s.selected));
        }""")
        self.assert_(chosen and chosen in self.expected["companies"], "Selected company is not from served data")
        self.assert_(str(chosen["symbol"]) in surface.locator(".fx-v5-stocktitle").inner_text(), "Visible ticker differs from selection")
        quote = surface.locator(".fx-v5-quote strong").inner_text()
        displayed = float(re.sub(r"[^0-9.\-]", "", quote))
        tolerance = 0.51 if chosen.get("currency") == "KRW" else 0.011
        self.assert_(math.isclose(displayed, float(chosen["price"]), abs_tol=tolerance), "Visible quote does not match saved price")
        self.assert_(chosen["price_session"] in surface.locator(".fx-v5-volume").inner_text(), "Quote session is missing")
        return chosen

    def desktop(self, browser):
        page = self.context(browser)
        self.load(page, "stock-radar-dashboard.html?stock=005930#home")
        self.assert_(urlsplit(page.url).path.endswith("/stock-value-radar.html"), "Legacy URL did not redirect")
        self.assert_(urlsplit(page.url).query == "stock=005930" and urlsplit(page.url).fragment == "home", "Redirect lost embedded ticker/hash")
        # Clear the explicit stock query before checking saved-selection restoration.
        self.load(page)
        info = self.geometry(page, "desktop-home")
        self.assert_(info["documentHeight"] <= 771 and info["main"]["bottom"] <= 771, "Approved desktop home no longer fits viewport")
        self.selected_source_matches(page)
        self.assert_(page.locator(".fx-v5-chartarea .fx-chart-svg polyline").count() > 0, "Actual saved price chart is missing")
        self.assert_("실시간 호가 아님" in page.locator("#source-status").inner_text(), "Saved-data disclosure is absent")
        self.screenshot("desktop-home")
        self.market_card_geometry(page, "desktop-home")
        sentinel = '{"note":"사용자 기록 보존 검사","version":1}'
        page.evaluate("value => localStorage.setItem('development-user-note',value)", sentinel)
        page.locator('.fx-nav [data-nr-screen="stocks"]').click()
        rows = page.locator(".fx-row[data-nr-select]")
        self.assert_(rows.count() > 1, "Stock list did not render usable saved companies")
        selected = rows.nth(1).get_attribute("data-nr-select")
        rows.nth(1).click()
        page.wait_for_function("symbol => window.StockRadarV2Bridge.snapshot().selected===symbol", arg=selected)
        self.assert_(selected in page.locator(".fx-focus-head").inner_text(), "Stock click did not update the focus panel")
        bounds = page.evaluate("""() => ({
            focus:document.querySelector('.fx-focus').getBoundingClientRect().bottom,
            flowbar:document.querySelector('.fx-flowbar').getBoundingClientRect().top,
            flowbarBottom:document.querySelector('.fx-flowbar').getBoundingClientRect().bottom,
            actions:document.querySelector('.fx-focus-actions').getBoundingClientRect().bottom,
            viewport:innerHeight,
            stage:document.querySelector('.fx-stage-other').getBoundingClientRect().bottom,
            stageHeight:document.querySelector('.fx-stage-other').clientHeight,
            stageScrollHeight:document.querySelector('.fx-stage-other').scrollHeight
        })""")
        self.report["geometry"]["desktop-stocks"] = bounds
        self.screenshot("desktop-stocks")
        self.assert_(bounds["flowbar"] >= bounds["focus"] - 1, "Following navigation overlaps the stock focus actions")
        self.assert_(bounds["flowbarBottom"] <= bounds["viewport"] + 1 and
            bounds["flowbarBottom"] <= bounds["stage"] + 1 and bounds["actions"] <= bounds["flowbar"],
            "Stock actions and following navigation must both remain visible in the fixed viewport")
        self.assert_(bounds["stageScrollHeight"] <= bounds["stageHeight"] + 1,
            "Stock-screen navigation must not be pushed into an extra stage scroll")
        page.locator(".fx-focus-actions [data-nr-detail]").click()
        self.assert_(selected in page.locator(".fx-d-security").inner_text() and
            page.evaluate("() => window.StockRadarV2Bridge.snapshot().selected") == selected,
            "Details lost the selected ticker")
        self.assert_(page.locator(".fx-detail-content").count() == 1, "Detailed research is absent")
        self.screenshot("desktop-detail")
        page.locator('.fx-nav [data-nr-screen="home"]').click()
        page.locator(f'.fx-v5-star[data-nr-star="{selected}"]').click()
        self.assert_(selected in page.evaluate("() => window.StockRadarV2Bridge.snapshot().favorites"), "Watch-list action was not saved")
        page.reload(wait_until="domcontentloaded")
        self.loaded(page)
        state = page.evaluate("() => window.StockRadarV2Bridge.snapshot()")
        self.assert_(state["selected"] == selected and selected in state["favorites"], "Reload lost selected ticker or watch list")
        self.assert_(page.evaluate("() => localStorage.getItem('development-user-note')") == sentinel, "Unrelated existing user note was changed")
        self.selected_source_matches(page)

        page.set_viewport_size({"width": 1629, "height": 929})
        info = self.geometry(page, "desktop-wide-home")
        self.assert_(info["documentHeight"] <= 932 and info["main"]["bottom"] <= 932,
            "Wide desktop home no longer fits its viewport")
        self.screenshot("desktop-wide-home")
        self.market_card_geometry(page, "desktop-wide-home")

    def mobile(self, browser):
        page = self.context(browser, 390, 844)
        self.load(page)
        self.geometry(page, "mobile-home")
        self.selected_source_matches(page)
        self.screenshot("mobile-home")
        self.market_card_geometry(page, "mobile-home")
        page.locator('.fx-nav [data-nr-screen="stockdetail"]').click()
        self.assert_(page.locator(".fx-detail-content").count() == 1, "Mobile detail navigation failed")
        info = page.evaluate("() => [document.documentElement.scrollWidth,innerWidth]")
        self.assert_(info[0] <= info[1] + 3, "Mobile detail overflows horizontally")
        self.screenshot("mobile-detail")

    def embed(self, browser):
        page = self.context(browser, 960, 730)
        # A local wrapper simulates an embed without accessing or claiming to test Notion itself.
        page.set_content('<!doctype html><html><body style="margin:20px">'
            '<iframe title="Notion-like investment radar embed" width="900" height="650" '
            'sandbox="allow-scripts allow-same-origin allow-forms allow-popups" '
            f'src="{html.escape(urljoin(self.base,"stock-value-radar.html"),quote=True)}"></iframe></body></html>')
        frame = page.frame_locator("iframe")
        frame.locator(".fx-topbar").wait_for(timeout=30000)
        child = next(f for f in page.frames if f.parent_frame is not None)
        self.loaded(child)
        self.geometry(child, "iframe-home")
        self.selected_source_matches(child)
        self.screenshot("iframe-home")
        self.market_card_geometry(child, "iframe-home")
        frame.locator('.fx-nav [data-nr-screen="stockdetail"]').click()
        self.assert_(frame.locator(".fx-detail-content").count() == 1, "Embedded detail navigation failed")
        size = child.evaluate("() => [document.documentElement.scrollWidth,innerWidth]")
        self.assert_(size[0] <= size[1] + 3, "Embedded detail overflows horizontally")
        self.screenshot("iframe-detail")

    def refresh_failure(self, browser):
        page = self.context(browser)
        self.load(page)
        before = page.evaluate("() => window.StockRadarV2Bridge.snapshot().data.raw")
        quote = page.locator(".fx-v5-quote strong").inner_text()
        page.route("**/stock-opportunity-data.json*", lambda route: route.abort())
        self.active["simulated_fault"] = "Abort raw-data endpoint after a successful real saved-data load"
        page.locator("[data-fx-refresh]").click()
        page.locator("#source-status").filter(has_text="raw 조회 실패 · 직전 정상 자료 유지").wait_for(timeout=30000)
        after = page.evaluate("() => window.StockRadarV2Bridge.snapshot().data.raw")
        self.assert_(digest(before) == digest(after), "Failed refresh replaced the valid saved snapshot")
        self.assert_(page.locator(".fx-v5-quote strong").inner_text() == quote, "Failed refresh changed the saved quote")
        self.assert_(page.locator(".fx-row[data-nr-select]").count() > 0, "Failure destroyed the usable saved stock list")
        self.screenshot("failed-refresh")

    def initial_failure(self, browser):
        page = self.context(browser)
        page.route("**/stock-opportunity-data.json*", lambda route: route.abort())
        self.active["simulated_fault"] = "Abort raw-data endpoint before any snapshot exists"
        self.load(page, expect_data=False)
        companies = page.evaluate("() => window.StockRadarV2Bridge.snapshot().data.raw?.companies||[]")
        self.assert_(not companies, "Missing initial data was replaced with fabricated companies")
        self.assert_(page.locator(".fx-v5-quote").count() == 0, "Missing initial data displays a fabricated quote")
        self.assert_(page.locator(".fx-row[data-nr-select]").count() == 0, "Missing initial data displays invented stock rows")
        self.assert_("raw 조회 실패" in page.locator("#source-status").inner_text(), "Initial failure is hidden")
        self.screenshot("initial-data-failure")

    def compare_baseline(self):
        baseline = self.options.baseline_dir
        if baseline is None:
            self.report["visual_comparison"] = {"status": "not_requested", "approved": False}
            return
        baseline = baseline.resolve()
        if baseline == self.out:
            raise ValueError("--baseline-dir must differ from --artifacts to preserve before evidence")
        previous = json.loads((baseline / "report.json").read_text())
        if not previous.get("screenshots"):
            raise ValueError("Baseline contains no screenshot evidence")
        comparisons, rows, missing = [], [], []
        for name, current_path in self.report["screenshots"].items():
            before_path = previous.get("screenshots", {}).get(name)
            if not before_path:
                missing.append(name)
                comparisons.append({"name": name, "status": "baseline_missing"})
                continue
            source = (baseline / before_path).resolve()
            if not source.is_relative_to(baseline):
                raise ValueError("Baseline screenshot must stay inside the baseline artifact directory")
            target = self.run / "before" / (name + ".png")
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            before_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            after_hash = hashlib.sha256((self.out / current_path).read_bytes()).hexdigest()
            comparisons.append({"name": name, "same_image_bytes": before_hash == after_hash,
                "before": str(target.relative_to(self.out)), "after": current_path,
                "before_geometry": previous.get("geometry", {}).get(name),
                "after_geometry": self.report["geometry"].get(name)})
            rows.append(f'<section><h2>{html.escape(name)}</h2><div class="pair"><figure><figcaption>Before</figcaption><img src="{html.escape(str(target.relative_to(self.out)))}"></figure><figure><figcaption>After</figcaption><img src="{html.escape(current_path)}"></figure></div></section>')
        self.report["visual_comparison"] = {
            "status": "partial_before_evidence" if missing else "captured_for_review",
            "approved": False, "baseline_functional_pass": previous.get("pass"),
            "baseline_summary": previous.get("summary"), "missing_before_screenshots": missing,
            "items": comparisons,
        }
        (self.out / "visual-comparison.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Radar before / after evidence</title><style>body{font:14px system-ui;margin:24px;background:#f4f5f7}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{max-width:100%;border:1px solid #ddd}section{margin-bottom:32px}</style><h1>Before / after evidence — manual review required</h1><p>Different image bytes may reflect data, clock, browser or design changes. No visual approval is inferred.</p>'+''.join(rows))

    def execute(self):
        startup_error = None
        try:
            if self.origin[0] not in ("http", "https") or not self.origin[1]:
                raise ValueError("--base-url must be an HTTP(S) server root")
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                launch = {"headless": True}
                if self.options.executable:
                    launch["executable_path"] = self.options.executable
                browser = p.chromium.launch(**launch)
                self.report["browser_version"] = browser.version
                try:
                    source_context = browser.new_context()
                    request = source_context.request
                    document = request.get(urljoin(self.base, "stock-value-radar.html"))
                    if not document.ok:
                        raise RuntimeError("Application HTML is not available from the static server")
                    self.report["tested_resources"] = {"stock-value-radar.html": hashlib.sha256(document.body()).hexdigest()}
                    for src in re.findall(r'<script[^>]*src="([^"]+)"', document.text()):
                        address = urljoin(self.base, src)
                        parsed = urlsplit(address)
                        if (parsed.scheme, parsed.netloc) != self.origin:
                            raise RuntimeError("Current radar must not depend on a remote executable script: " + str(parsed.hostname))
                        resource = request.get(address)
                        if not resource.ok:
                            raise RuntimeError("Runtime script is unavailable: " + parsed.path)
                        self.report["tested_resources"][parsed.path] = hashlib.sha256(resource.body()).hexdigest()
                    response = request.get(urljoin(self.base, "stock-opportunity-data.json"))
                    if not response.ok:
                        raise RuntimeError("Saved raw data is not available from the static server")
                    self.expected = response.json()
                    if not isinstance(self.expected.get("companies"), list) or not self.expected["companies"]:
                        raise RuntimeError("Saved raw data contains no companies; zero-data runs do not validate readiness")
                    self.report["data"] = {"companies": len(self.expected["companies"]),
                        "generated_at": self.expected.get("generated_at"), "sha256": digest(self.expected)}
                    source_context.close()
                    for name in ("desktop", "mobile", "embed", "refresh_failure", "initial_failure"):
                        self.active = {"name": name, "pass": False, "assertions": 0, "blocked_external_hosts": []}
                        self.page, self.context_, self.errors = None, None, []
                        try:
                            getattr(self, name)(browser)
                            self.assert_(not self.errors, "Uncaught page errors: " + str(self.errors))
                            self.active["pass"] = True
                        except Exception as error:
                            self.active["error"] = str(error)
                            self.active["traceback"] = traceback.format_exc()
                            if self.page:
                                try:
                                    self.screenshot(name + "-failure")
                                except Exception:
                                    pass
                        finally:
                            self.active["page_errors"] = self.errors
                            self.active["blocked_external_hosts"] = sorted(set(self.active["blocked_external_hosts"]))
                            if self.context_:
                                self.context_.close()
                        self.report["results"].append(self.active)
                        print(("PASS" if self.active["pass"] else "FAIL"), name, self.active.get("error", ""), flush=True)
                finally:
                    browser.close()
            self.compare_baseline()
        except Exception as error:
            startup_error = str(error)
            self.report["runner_error"] = startup_error
            self.report["runner_traceback"] = traceback.format_exc()
        passed = sum(r["pass"] for r in self.report["results"])
        self.report["summary"] = {"executed": len(self.report["results"]), "passed": passed,
            "failed": len(self.report["results"]) - passed,
            "assertions": sum(r["assertions"] for r in self.report["results"])}
        self.report["pass"] = not startup_error and len(self.report["results"]) == 5 and passed == 5
        self.report["finished_at"] = datetime.now(timezone.utc).isoformat()
        output = json.dumps(self.report, ensure_ascii=False, indent=2)
        (self.out / "report.json").write_text(output)
        (self.run / "report.json").write_text(output)
        print(json.dumps({"pass": self.report["pass"], **self.report["summary"], "report": str(self.out / "report.json")}), flush=True)
        if startup_error:
            print("RUNNER_ERROR", startup_error, flush=True)
        return 0 if self.report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(Checks(parser().parse_args()).execute())
