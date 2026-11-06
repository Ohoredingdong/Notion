"""Focused regressions for proven short-viewport and keyboard-focus defects.

Uses isolated fictional notebooks. The 640x360/DPR2 case is a layout proxy for
200% at 1280x720, not a real browser-zoom test. The iframe is a local size proxy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import traceback
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import expect, sync_playwright


def view_url(base, view):
    parts = urlsplit(base)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "view"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query + [("view", view)]), parts.fragment))


def outer_fixed(surface, label):
    actual = surface.evaluate("""() => ({w:innerWidth,h:innerHeight,
        sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight,
        x:scrollX,y:scrollY})""")
    assert actual["sw"] <= actual["w"] + 1 and actual["sh"] <= actual["h"] + 1, (label, actual)
    assert actual["x"] == actual["y"] == 0, (label, "outer body moved", actual)


def visible_rectangle(locator):
    """Measure actual clipping, including nested overflow containers."""
    return locator.evaluate("""el => {
      const r=el.getBoundingClientRect();let l=Math.max(0,r.left),t=Math.max(0,r.top),
        right=Math.min(innerWidth,r.right),bottom=Math.min(innerHeight,r.bottom);
      for(let a=el.parentElement;a;a=a.parentElement){const s=getComputedStyle(a),b=a.getBoundingClientRect();
        if(['auto','scroll','hidden','clip'].includes(s.overflowX)){l=Math.max(l,b.left);right=Math.min(right,b.right);}
        if(['auto','scroll','hidden','clip'].includes(s.overflowY)){t=Math.max(t,b.top);bottom=Math.min(bottom,b.bottom);}}
      return {width:r.width,height:r.height,visibleWidth:Math.max(0,right-l),
        visibleHeight:Math.max(0,bottom-t),clientHeight:el.clientHeight};
    }""")


def readable(locator, label, minimum=120):
    expect(locator).to_be_visible()
    locator.scroll_into_view_if_needed()
    actual = visible_rectangle(locator)
    assert actual["clientHeight"] >= minimum, (label, "reading panel collapsed", actual)
    assert actual["visibleHeight"] >= minimum - 1, (label, "reading panel clipped", actual)
    assert actual["visibleWidth"] >= 160, (label, "reading panel too narrow", actual)
    return actual


def reachable(locator, label):
    """Normal scrolling and clicks; never force clicks or patch application DOM."""
    expect(locator).to_be_visible()
    locator.scroll_into_view_if_needed()
    actual = visible_rectangle(locator)
    assert actual["visibleHeight"] >= actual["height"] - 2, (label, "button clipped vertically", actual)
    assert actual["visibleWidth"] >= actual["width"] - 2, (label, "button clipped horizontally", actual)
    locator.click()


def navigate(surface, view):
    surface.locator(f'.nav-item[data-page="{view}"]').click()
    expect(surface.locator(f'.page-content[data-view="{view}"]')).to_be_visible()


def choose_sim_pane(surface, name):
    control = surface.locator(f'.sim-pane-tabs [data-sim-pane="{name}"]')
    if control.is_visible():
        reachable(control, f"simulation {name} pane")


def short_workspace(surface, page, artifacts, label):
    """The old fixed-height shell reduced these bodies to 3–36 CSS pixels."""
    metrics = {}
    navigate(surface, "simulation")
    choose_sim_pane(surface, "document")
    metrics["simulation"] = readable(surface.locator('[data-sim-scroll="document"]'), "fictional document")
    reachable(surface.locator('[data-sim-action="review-document"]'), "document confirmation")
    expect(surface.locator(".sim-document-footer > span")).to_contain_text("1 / 8")
    choose_sim_pane(surface, "analysis")
    reachable(surface.locator('.sim-stages [data-sim-go-stage="1"]'), "rights stage")
    metrics["simulationAnalysis"] = readable(surface.locator('[data-sim-scroll="analysis"]'), "rights question")
    surface.locator('[data-sim-choice]').first.check()
    reachable(surface.locator('[data-sim-action="check-answer"]'), "answer explanation")
    expect(surface.locator(".sim-feedback")).to_be_visible()
    outer_fixed(surface, "simulation")
    page.screenshot(path=str(artifacts / f"{label}-simulation.png"))

    navigate(surface, "learn")
    source = surface.locator('[data-study-pane="document"]')
    if source.is_visible():
        reachable(source, "lesson document pane")
    metrics["lessonDocument"] = readable(surface.locator("#studyDocumentPane"), "guided lesson document")
    outer_fixed(surface, "guided lesson")
    page.screenshot(path=str(artifacts / f"{label}-lesson.png"))

    navigate(surface, "home")
    metrics["homeAnalysis"] = readable(surface.locator(".analysis-progress"), "dashboard analysis list")
    for panel in ("reasons", "cash", "progress"):
        reachable(surface.locator(f'.home-tabs [data-home-panel="{panel}"]'), f"dashboard {panel} tab")
        expect(surface.locator(f"#home-{panel}")).to_be_visible()
    outer_fixed(surface, "dashboard")
    page.screenshot(path=str(artifacts / f"{label}-dashboard.png"))

    navigate(surface, "process")
    to_list = surface.locator('[data-process-pane="list"]')
    if to_list.is_visible():
        reachable(to_list, "process list pane")
    reachable(surface.locator('.process-list [data-process-stage="delivery"]'), "last practical process stage")
    metrics["process"] = readable(surface.locator(".process-detail-scroll"), "process details")
    expect(surface.locator(".process-detail h2")).to_contain_text("인도")
    footer = surface.locator(".process-disclaimer")
    footer.scroll_into_view_if_needed()
    assert visible_rectangle(footer)["visibleHeight"] >= 24, "The court-deadline disclaimer must remain readable"
    outer_fixed(surface, "process")
    page.screenshot(path=str(artifacts / f"{label}-process.png"))
    (artifacts / "panel-metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def short_viewport(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    short_workspace(page, page, artifacts, "short")


def storage_warning_viewport(page, context, args, artifacts):
    context.add_init_script("""(() => {
      const original = Storage.prototype.getItem;
      Storage.prototype.getItem = function(key) {
        if (key === 'auction-study-v1') throw new DOMException('Test-only notebook storage denial', 'SecurityError');
        return original.call(this, key);
      };
    })();""")
    page.goto(view_url(args.url, "simulation"))
    expect(page.locator("#storageWarning")).to_be_visible()
    short_workspace(page, page, artifacts, "storage-warning")


def embedded_short_viewport(page, context, args, artifacts):
    page.goto(args.url)
    page.set_content('<!doctype html><style>html,body{margin:0}iframe{display:block;border:0;width:900px;height:390px}</style><iframe title="local short embed proxy"></iframe>')
    frame = page.locator("iframe").element_handle().content_frame()
    frame.goto(view_url(args.url, "simulation"))
    short_workspace(frame, page, artifacts, "iframe")


def active_id(page):
    return page.evaluate("document.activeElement.id || document.activeElement.tagName")


def create_fictional_note(page, index):
    page.locator('.topbar [data-action="new"]').click()
    page.locator("#case-name").fill(f"키보드 검증 가상 노트 {index}")
    page.locator("#case-address").fill("독립 브라우저의 가상 검증 주소 · 실매물 아님")
    page.locator('#caseForm button[type="submit"]').click()


def notebook_keyboard(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    for index in (1, 2):
        create_fictional_note(page, index)
    navigate(page, "simulation")
    select = page.locator("#caseSelect")
    assert select.locator("option").count() == 3
    select.focus()
    changes = []
    for key in ("ArrowUp", "ArrowUp", "ArrowDown"):
        before = select.input_value()
        page.keyboard.press(key)
        after = select.input_value()
        changes.append({"key": key, "before": before, "after": after, "focus": active_id(page)})
        assert before != after, ("Direction key stopped changing notebooks", changes)
        assert active_id(page) == "caseSelect", ("Notebook selection lost keyboard focus", changes)
    page.keyboard.press("Tab")
    assert page.locator('.topbar [data-action="new"]').evaluate("el => el === document.activeElement"), "Tab after notebook selection must continue to the adjacent new-note button"
    outer_fixed(page, "notebook keyboard selection")
    page.screenshot(path=str(artifacts / "notebook-selector-focus.png"))
    (artifacts / "focus.json").write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")


def lesson_keyboard(page, context, args, artifacts):
    page.goto(view_url(args.url, "learn"))
    select = page.locator("#studyCaseSelect")
    assert select.locator("option").count() >= 2, "The selector needs at least two existing lessons"
    select.select_option(index=0)
    select.focus()
    changes = []
    for key in ("ArrowDown", "ArrowUp", "ArrowDown"):
        before = select.input_value()
        page.keyboard.press(key)
        after = select.input_value()
        changes.append({"key": key, "before": before, "after": after, "focus": active_id(page)})
        assert before != after, ("Direction key stopped changing lessons", changes)
        assert active_id(page) == "studyCaseSelect", ("Lesson selection lost keyboard focus", changes)
    page.keyboard.press("Tab")
    assert page.locator(".study-steps button").first.evaluate("el => el === document.activeElement"), "Tab must continue to the first lesson step"
    focused = visible_rectangle(page.locator(".study-steps button").first)
    assert focused["visibleHeight"] >= focused["height"] - 2, ("Next keyboard target is clipped", focused)
    outer_fixed(page, "lesson keyboard selection")
    page.screenshot(path=str(artifacts / "lesson-selector-focus.png"))
    (artifacts / "focus.json").write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/auction-study.html"))
    parser.add_argument("--executable", default=os.environ.get("BROWSER_EXECUTABLE"))
    parser.add_argument("--artifacts", type=Path, default=Path("/tmp/auction-accessibility-browser"))
    parser.add_argument("--only", nargs="+", help="Run named scenarios only, for a focused fix verification")
    args = parser.parse_args()
    scenarios = [
        ("landscape-844x390", short_viewport, 844, 390, 1),
        ("zoom-layout-proxy-640x360-dpr2", short_viewport, 640, 360, 2),
        ("mobile-320x568", short_viewport, 320, 568, 1),
        ("storage-warning-320x568", storage_warning_viewport, 320, 568, 1),
        ("storage-warning-390x667", storage_warning_viewport, 390, 667, 1),
        ("short-iframe-900x390", embedded_short_viewport, 1024, 768, 1),
        ("notebook-keyboard-1280x720", notebook_keyboard, 1280, 720, 1),
        ("lesson-keyboard-1280x720", lesson_keyboard, 1280, 720, 1),
        ("lesson-keyboard-375x568", lesson_keyboard, 375, 568, 1),
    ]
    if args.only:
        missing = set(args.only) - {item[0] for item in scenarios}
        if missing:
            parser.error(f"Unknown scenarios: {', '.join(sorted(missing))}")
        scenarios = [item for item in scenarios if item[0] in args.only]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = args.artifacts / stamp
    out.mkdir(parents=True, exist_ok=False)
    report = {"started": stamp, "url": args.url, "limitations": ["640x360/DPR2 is a 200% layout proxy, not real browser zoom.", "The local iframe is not actual Notion integration."], "results": []}
    with sync_playwright() as playwright:
        options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if args.executable:
            options["executable_path"] = args.executable
        browser = playwright.chromium.launch(**options)
        for name, test, width, height, dpr in scenarios:
            directory = out / name
            directory.mkdir()
            context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=dpr, locale="ko-KR")
            context.set_default_timeout(6000)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            result = {"name": name, "viewport": [width, height], "dpr": dpr, "artifacts": str(directory)}
            try:
                test(page, context, args, directory)
                assert not errors, ("Uncaught browser errors", errors)
                result["status"] = "passed"
            except Exception as error:
                result.update(status="failed", error=str(error), traceback=traceback.format_exc(), browserErrors=errors)
                try:
                    page.screenshot(path=str(directory / "failure.png"), full_page=True)
                except Exception:
                    pass
            finally:
                report["results"].append(result)
                context.close()
            print(f'{result["status"].upper()}: {name}', flush=True)
            if result["status"] == "failed":
                print(result["error"], flush=True)
        browser.close()
    report["passed"] = sum(result["status"] == "passed" for result in report["results"])
    report["failed"] = len(report["results"]) - report["passed"]
    destination = out / "report.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f'{report["passed"]}/{len(scenarios)} passed. Report: {destination}', flush=True)
    return int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
