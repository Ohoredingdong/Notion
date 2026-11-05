#!/usr/bin/env python3
"""PR-only, real-snapshot browser acceptance + before/after screenshot review.

The reference (main) and candidate (PR head) use identical, *real* JSON/JSONL
from the PR checkout for a meaningful UI comparison. Originals are read only.
This never publishes, changes stored financial observations or fabricates data.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Server:
    def __init__(self, root: Path):
        handler = partial(SilentHandler, directory=str(root))
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return "http://127.0.0.1:" + str(self.httpd.server_port)

    def __exit__(self, *args):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def shared_snapshot(route, root: Path):
    url = urlsplit(route.request.url)
    if url.hostname not in ("127.0.0.1", "localhost"):
        route.continue_()
        return
    relative = unquote(url.path).lstrip("/")
    if not relative.endswith((".json", ".jsonl")):
        route.continue_()
        return
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        route.continue_()
        return
    route.fulfill(status=200,
                  content_type="application/json" if relative.endswith(".json") else "application/x-ndjson",
                  body=candidate.read_bytes())


def metrics(page):
    return page.evaluate("""() => ({
       scrollWidth: document.documentElement.scrollWidth,
       innerWidth: window.innerWidth,
       scrollHeight: document.documentElement.scrollHeight,
       innerHeight: window.innerHeight,
       title: document.title,
       cards: document.querySelectorAll('.fx-v5-markets .nr-index').length,
       detail: document.querySelectorAll('.fx-detail-v6 .fx-detail-upper>.fx-panel').length
    })""")


def record(report, label: str, ok: bool, detail=""):
    report["checks"].append({"name": label, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{label}: {str(detail)[:700]}")


def snapshot(page, dest: Path, report: dict, key: str):
    dest.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(dest), full_page=True, animations="disabled")
    report["screenshots"].append(str(dest))
    return metrics(page)


def capture_home(browser, base: str, shared: Path, out: Path, kind: str, report: dict,
                 width: int, height: int):
    context = browser.new_context(viewport={"width": width, "height": height},
                                  color_scheme="light", reduced_motion="reduce",
                                  service_workers="block")
    context.route("**/*", lambda route: shared_snapshot(route, shared))
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    try:
        response = page.goto(base + "/stock-value-radar.html", wait_until="domcontentloaded")
        record(report, kind + " loads", bool(response and response.status == 200))
        page.wait_for_function(
            "() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length",
            timeout=50000,
        )
        page.locator(".fx-v5-markets .nr-index").first.wait_for(timeout=18000)
        info = snapshot(page, out / (kind + ".png"), report, kind)
        record(report, kind + " market indexes", info["cards"] == 4, info)
        record(report, kind + " browser exceptions", not errors, errors)
        return info
    finally:
        context.close()


def capture_detail(browser, base: str, shared: Path, out: Path, kind: str, report: dict,
                   width: int, height: int):
    context = browser.new_context(viewport={"width": width, "height": height},
                                  color_scheme="light", reduced_motion="reduce")
    context.route("**/*", lambda route: shared_snapshot(route, shared))
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    try:
        page.goto(base + "/stock-value-radar.html?screen=stockdetail&stock=005930",
                  wait_until="domcontentloaded")
        page.locator(".fx-detail-v6").wait_for(timeout=45000)
        page.wait_for_function(
            "() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length",
            timeout=45000,
        )
        info = snapshot(page, out / (kind + ".png"), report, kind)
        record(report, kind + " structured detail cards", info["detail"] == 3, info)
        record(report, kind + " actual selected company",
               "삼성전자" in page.locator(".fx-detail-intro h2").inner_text())
        record(report, kind + " nonblank AI pane",
               bool(page.locator(".fx-d-ai-body").inner_text().strip()))
        record(report, kind + " no JS exceptions", not errors, errors)
        return info
    finally:
        context.close()


def capture_embed(browser, base: str, shared: Path, out: Path, kind: str, report: dict,
                  width: int, height: int):
    # Model the *viewport* a Notion iframe grants; do not claim to navigate Notion itself.
    outer_width = width + 54
    context = browser.new_context(viewport={"width": outer_width, "height": height + 65},
                                  color_scheme="light", reduced_motion="reduce",
                                  service_workers="block")
    context.route("**/*", lambda route: shared_snapshot(route, shared))
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    try:
        page.set_content("""<!doctype html><meta charset="utf-8"><title>Notion embed simulation</title>
            <style>body{margin:0;padding:16px;background:#f4f5f7;font-family:system-ui}
            iframe{border:1px solid #dbe3ef;border-radius:12px;background:white}</style>
            <iframe name="notion-widget" title="Investment radar" src="%s/stock-value-radar.html"
            width="%d" height="%d"></iframe>""" % (base, width, height))
        page.frame_locator('iframe[name="notion-widget"]').locator(".fx-topbar").wait_for(timeout=45000)
        frame = page.frame(name="notion-widget")
        record(report, kind + " iframe loaded", frame is not None)
        frame.wait_for_function(
            "() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length",
            timeout=45000,
        )
        child = frame.evaluate("""() => ({
            width:window.innerWidth,scrollWidth:document.documentElement.scrollWidth,
            indexCards:document.querySelectorAll('.fx-v5-markets .nr-index').length,
            sourceText:document.querySelector('#source-status')?.textContent||''
        })""")
        page.screenshot(path=str(out / (kind + ".png")), full_page=True)
        report["screenshots"].append(str(out / (kind + ".png")))
        record(report, kind + " real market cards", child["indexCards"] == 4, child)
        record(report, kind + " has data provenance", bool(child["sourceText"].strip()), child)
        record(report, kind + " no JS exceptions", not errors, errors)
        return child
    finally:
        context.close()


def screenshot_diff(before: Path, after: Path, output: Path) -> dict:
    with Image.open(before) as first, Image.open(after) as second:
        a, b = first.convert("RGB"), second.convert("RGB")
        if a.size != b.size:
            return {"size_changed": True, "before": a.size, "after": b.size,
                    "changed_percent": 100.0}
        diff = ImageChops.difference(a, b)
        output.parent.mkdir(parents=True, exist_ok=True)
        diff.save(output)
        mask = diff.convert("L").point(lambda px: 255 if px > 20 else 0)
        changed = mask.histogram()[255]
        return {"size_changed": False, "before": a.size, "after": b.size,
                "changed_percent": round(100 * changed / (a.width * a.height), 2)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reference", type=Path, required=True, help="unmodified main checkout")
    p.add_argument("--candidate", type=Path, default=Path("."))
    p.add_argument("--changes", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("codex-pr-artifacts"))
    args = p.parse_args()
    ref, head = args.reference.resolve(), args.candidate.resolve()
    assert (ref / "stock-value-radar.html").is_file(), "reference page missing"
    assert (head / "stock-value-radar.html").is_file(), "candidate page missing"
    changes = json.loads(args.changes.read_text(encoding="utf-8"))["changes"]
    visual_changed = any(x["ui"] for x in changes)
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"source": "genuine candidate financial JSON/JSONL, read-only",
              "visual_source_changed": visual_changed,
              "checks": [], "screenshots": [], "visual_diff": {},
              "unverified": ["Live deployed GitHub Pages is NOT changed or probed by this PR check",
                             "This iframe is a local Notion-sized simulation, not actual Notion"]}
    failures = []
    try:
        with Server(ref) as reference_url, Server(head) as candidate_url:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    for name, fn, width, height in (
                        ("home-desktop", capture_home, 1440, 900),
                        ("home-mobile", capture_home, 390, 844),
                        ("detail-desktop", capture_detail, 1440, 900),
                        ("detail-mobile", capture_detail, 390, 844),
                        ("notion-desktop", capture_embed, 920, 680),
                        ("notion-mobile", capture_embed, 360, 620),
                    ):
                        before, after = None, None
                        try:
                            before = fn(browser, reference_url, head, args.out, "before-"+name,
                                        report, width, height)
                            after = fn(browser, candidate_url, head, args.out, "after-"+name,
                                       report, width, height)
                            for axis in ("scrollWidth", "width"):
                                pass
                            before_overflow = before["scrollWidth"] - before.get("innerWidth", before.get("width", width))
                            after_overflow = after["scrollWidth"] - after.get("innerWidth", after.get("width", width))
                            record(report, name + " no new horizontal overflow",
                                   after_overflow <= max(3, before_overflow + 3),
                                   {"before_overflow": before_overflow, "after_overflow": after_overflow})
                            d = screenshot_diff(args.out / ("before-"+name+".png"),
                                                args.out / ("after-"+name+".png"),
                                                args.out / ("diff-"+name+".png"))
                            report["visual_diff"][name] = d
                            if not visual_changed:
                                record(report, name + " untouched UI remains visually equivalent",
                                       not d["size_changed"] and d["changed_percent"] <= 3.0,
                                       d)
                        except Exception as exc:
                            failures.append({"view": name, "error": str(exc)})
                    # Non-radar HTML files changed in the PR receive additional local browser smoke checks.
                    for row in changes:
                        path = row["path"]
                        if not path.endswith(".html") or path == "stock-value-radar.html":
                            continue
                        page = browser.new_page(viewport={"width": 390, "height": 844})
                        try:
                            response = page.goto(candidate_url + "/" + path,
                                                 wait_until="domcontentloaded")
                            record(report, path + " mobile HTTP page", bool(response and response.status == 200))
                            record(report, path + " nonblank DOM", bool(page.locator("body").inner_text().strip()))
                            page.screenshot(path=str(args.out / ("widget-"+Path(path).stem+".png")),
                                            full_page=True)
                        except Exception as exc:
                            failures.append({"view": path, "error": str(exc)})
                        finally:
                            page.close()
                finally:
                    browser.close()
    finally:
        report["failures"] = failures
        (args.out / "visual-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Browser result: %d checks, %d failures" % (len(report["checks"]), len(failures)))
    print(json.dumps(report["visual_diff"], ensure_ascii=False))
    if failures:
        raise SystemExit("Browser regression failures: " + json.dumps(failures, ensure_ascii=False))
    if any(not x["passed"] for x in report["checks"]):
        raise SystemExit("One or more browser acceptance checks failed")
    print("PASS: local before/after desktop, mobile and Notion-sized iframe acceptance")


if __name__ == "__main__":
    main()
