"""Browser regressions for the beginner course, without editing real notes.

All attempts use isolated browser contexts and fictional lesson documents.
Viewport and iframe checks are proxies; they do not verify actual devices,
Notion's application, legal advice, or an independent learner's understanding.
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


KEY = "auction-course-v1"
PRESERVED = ("auction-study-v1", "auction-study-lessons-v1", "auction-simulation-v1")
PANES = ("basics", "example", "practice")
LABELS = ("기초", "예제", "실습")


def view_url(base, view=None):
    parts = urlsplit(base)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "view"]
    if view is not None:
        query.append(("view", view))
    return urlunsplit(parts._replace(query=urlencode(query)))


def go(page, args):
    page.goto(view_url(args.url, "course"), wait_until="domcontentloaded")
    expect(page.locator(".course-workspace")).to_be_visible()


def data(surface):
    result = surface.evaluate("() => window.AuctionCourseData.lessons")
    assert len(result) >= 5, "A primer must teach all five agreed topics"
    return result


def raw(surface):
    return surface.evaluate("key => localStorage.getItem(key)", KEY)


def stored(surface):
    return json.loads(raw(surface))


def records(surface):
    result = stored(surface)
    return result.get("progress", result)["records"]


def tab(surface, pane):
    surface.locator(f'button[data-course-tab="{pane}"]').click()
    expect(surface.locator(".course-workspace")).to_have_attribute("data-course-pane", pane)


def choose_lesson(surface, lesson):
    surface.locator(f'button[data-course-lesson="{lesson["id"]}"]').click()


def answer_value(practice, correct=True):
    if practice["type"] == "amount":
        return str(practice["answerValue"] if correct else practice["answerValue"] + 17)
    if correct:
        return practice["answerId"]
    return next(choice["id"] for choice in practice["choices"] if choice["id"] != practice["answerId"])


def enter(surface, practice, value):
    if practice["type"] == "amount":
        surface.locator("#courseAnswer").fill(str(value))
    else:
        surface.locator(f'input[name="courseAnswer"][value="{value}"]').check()


def submit(surface):
    surface.locator('[data-course-action="check"]').click()


def feedback(surface, correct):
    expect(surface.locator("#courseFeedback")).to_have_attribute("data-correct", str(correct).lower())
    assert len(surface.locator("#courseFeedback").inner_text().strip()) >= 20, "Feedback must teach a reason"


def no_answer(surface, lesson):
    assert surface.locator("#courseFeedback").count() == 0, "Feedback must not be hidden in the DOM before an attempt"
    assert lesson["practice"]["explanation"] not in surface.locator(".course-workspace").inner_text(), "Practice reasoning must wait until an attempt"


def preserve_snapshot(surface):
    return surface.evaluate("keys => Object.fromEntries(keys.map(k=>[k,localStorage.getItem(k)]))", list(PRESERVED))


def course_flow(page, context, args, out):
    # A fresh arrival must have an obvious beginner entry point.
    page.goto(view_url(args.url), wait_until="domcontentloaded")
    expect(page.locator(".page-content")).to_have_attribute("data-view", "course")
    expect(page.locator(".course-workspace")).to_have_attribute("data-course-pane", "basics")
    assert page.locator('button[data-course-tab]').all_inner_texts() == list(LABELS)
    lessons = data(page)
    # Create a genuine notebook through its existing UI before exercising course storage.
    page.locator('.nav-item[data-page="home"]').click()
    page.locator('.topbar [data-action="new"]').click()
    page.locator("#case-name").fill("입문 강좌 보존 검증 · 가상 노트")
    page.locator('#caseForm button[type="submit"]').click()
    original = preserve_snapshot(page)
    assert original[PRESERVED[0]], "The preservation test needs an actual saved note"
    page.locator('.nav-item[data-page="course"]').click()
    for index, lesson in enumerate(lessons):
        choose_lesson(page, lesson)
        tab(page, "basics")
        text = page.locator(".course-workspace").inner_text()
        assert lesson["basics"]["lead"] in text
        for term in lesson["basics"]["terms"]:
            assert term["term"] in text and term["text"] in text, "New terms need their explanation before analysis"
        page.screenshot(path=str(out / f'{index + 1}-basics.png'))
        tab(page, "example")
        text = page.locator(".course-workspace").inner_text()
        assert lesson["example"]["answer"] in text, "A worked example must show its result"
        for step in lesson["example"]["steps"]:
            assert step["text"] in text, "A worked example must show how evidence leads to the answer"
        assert "가상" in text, "Invented document excerpts must be identified"
        tab(page, "practice")
        assert lesson["practice"]["title"] in page.locator(".course-workspace").inner_text()
        assert lesson["practice"]["title"] != lesson["example"]["title"], "Independent practice must change the case"
        no_answer(page, lesson)
        submit(page)
        assert page.locator("#courseFeedback[data-correct=true]").count() == 0, "Empty answers must not pass"
        assert not records(page).get(lesson["id"], {}).get("firstAttempt"), "Empty answers are not a genuine first attempt"
        wrong = answer_value(lesson["practice"], False)
        enter(page, lesson["practice"], wrong)
        submit(page)
        feedback(page, False)
        initial = records(page)[lesson["id"]]["firstAttempt"]
        assert initial == {"answer": wrong, "correct": False}, initial
        enter(page, lesson["practice"], answer_value(lesson["practice"]))
        submit(page)
        feedback(page, True)
        record = records(page)[lesson["id"]]
        assert record["firstAttempt"] == initial, "A corrected answer must not rewrite the original attempt"
        assert record["attempts"] == 2 and record["lastAttempt"]["correct"] is True
        assert lesson["practice"]["explanation"] in page.locator("#courseFeedback").inner_text()
        assert preserve_snapshot(page) == original, "Course practice must never overwrite existing notes or advanced progress"
        page.screenshot(path=str(out / f'{index + 1}-practice-reviewed.png'))
        if index + 1 < len(lessons):
            page.locator('[data-course-action="next"]').click()
            expect(page.locator(".course-workspace")).to_have_attribute("data-course-pane", "basics")
            expect(page.locator(f'[data-course-lesson="{lessons[index+1]["id"]}"]')).to_have_attribute("aria-current", "step")
    snapshot = raw(page)
    page.reload(wait_until="domcontentloaded")
    assert raw(page) == snapshot, "Reload must retain all practice attempts"
    assert len([record for record in records(page).values() if record.get("lastAttempt", {}).get("correct")]) == len(lessons)
    assert preserve_snapshot(page) == original
    page.locator('[data-course-action="next"]').click()
    expect(page.locator(".page-content")).to_have_attribute("data-view", "simulation")


def amount_validation(page, context, args, out):
    go(page, args)
    amounts = [lesson for lesson in data(page) if lesson["practice"]["type"] == "amount"]
    assert len(amounts) >= 2, "Deposit and cash need independent numerical practice"
    by_id = {lesson["id"]: lesson for lesson in amounts}
    deposit = by_id["bid-deposit"]
    cash = by_id["cash-needed"]
    # These are independent calculations, not calls to the production grader.
    assert deposit["example"]["inputs"] == {"minimum": 10000, "depositRate": 10, "bid": 12000}
    assert deposit["practice"]["inputs"] == {"minimum": 8000, "depositRate": 20, "bid": 9500}
    assert 10000 * 10 / 100 == 1000 and 12000 - 1000 == 11000
    assert deposit["practice"]["answerValue"] == 8000 * 20 / 100 == 1600
    assert cash["example"]["inputs"] == {"bid": 10000, "costs": 700, "loan": 6000, "reserve": 300, "deposit": 1000}
    assert cash["practice"]["inputs"] == {"bid": 15000, "costs": 900, "loan": 9000, "reserve": 400, "deposit": 1500}
    assert 10000 + 700 - 6000 + 300 == 5000
    assert cash["practice"]["answerValue"] == 15000 + 900 - 9000 + 400 == 7300
    for lesson in amounts:
        choose_lesson(page, lesson)
        tab(page, "practice")
        practice = lesson["practice"]
        for invalid in ("", "-1"):
            enter(page, practice, invalid)
            submit(page)
            assert page.locator("#courseFeedback[data-correct=true]").count() == 0
            assert not records(page).get(lesson["id"], {}).get("firstAttempt"), "Invalid input must not become a valid recorded attempt"
        enter(page, practice, "0")
        submit(page)
        feedback(page, False)
        assert records(page)[lesson["id"]]["firstAttempt"] == {"answer":"0","correct":False}, "A real zero must be graded as an attempt, unlike an empty field"
        enter(page, practice, f'{practice["answerValue"]:,}')
        submit(page)
        feedback(page, True)
        assert records(page)[lesson["id"]]["firstAttempt"]["answer"] == "0"
    page.screenshot(path=str(out / "amount-validation.png"))


def storage_failure(page, context, args, out):
    go(page, args)
    lesson = next(item for item in data(page) if item["practice"]["type"] == "amount")
    choose_lesson(page, lesson)
    tab(page, "practice")
    before = raw(page)
    page.evaluate("""key => {
        const original = Storage.prototype.setItem;
        Storage.prototype.setItem = function(name,value) {
            if (name === key) throw new DOMException('Course storage quota test', 'QuotaExceededError');
            return original.call(this,name,value);
        };
    }""", KEY)
    value = answer_value(lesson["practice"])
    enter(page, lesson["practice"], value)
    submit(page)
    expect(page.locator("#courseStorageWarning")).to_be_visible()
    expect(page.locator("#courseAnswer")).to_have_value(value)
    assert raw(page) == before, "A failed write must preserve the previous saved bytes"
    page.screenshot(path=str(out / "storage-failure.png"))


def storage_conflict(page, context, args, out):
    go(page, args)
    lesson = next(item for item in data(page) if item["practice"]["type"] == "amount")
    choose_lesson(page, lesson)
    tab(page, "practice")
    draft = answer_value(lesson["practice"], False)
    enter(page, lesson["practice"], draft)
    # Open the peer after the draft so it starts from the newest stored state
    # even if input drafts are persisted before submission.
    peer = context.new_page()
    go(peer, args)
    choose_lesson(peer, lesson)
    tab(peer, "practice")
    enter(peer, lesson["practice"], answer_value(lesson["practice"]))
    submit(peer)
    feedback(peer, True)
    latest = raw(peer)
    expect(page.locator("#courseStorageWarning")).to_be_visible()
    expect(page.locator("#courseAnswer")).to_have_value(draft)
    submit(page)
    assert raw(page) == latest, "A stale tab must not overwrite a peer's saved attempt"
    expect(page.locator("#courseAnswer")).to_have_value(draft)
    page.screenshot(path=str(out / "storage-conflict.png"))
    peer.close()


def corrupt_storage(page, context, args, out):
    go(page, args)
    fixtures = {
        "empty-storage": "",
        "invalid-json": '{"version":1,"records":',
        "unknown-schema": json.dumps({"version":99,"lessonId":"auction-flow","pane":"basics","records":{}}),
        "inconsistent-attempt": json.dumps({"version":1,"lessonId":"bid-deposit","pane":"practice","records":{"bid-deposit":{"answer":"1600","submitted":True,"firstAttempt":None,"lastAttempt":{"answer":"1600","correct":True},"attempts":1}}}),
    }
    for name, broken in fixtures.items():
        page.evaluate("([key,value])=>localStorage.setItem(key,value)", [KEY, broken])
        page.reload(wait_until="domcontentloaded")
        expect(page.locator(".course-workspace")).to_be_visible()
        expect(page.locator("#courseStorageWarning")).to_be_visible()
        lesson = data(page)[0]
        tab(page, "practice")
        enter(page, lesson["practice"], answer_value(lesson["practice"]))
        submit(page)
        assert raw(page) == broken, "Unreadable saved progress must not be silently reset or overwritten"
        expect(page.locator("#courseStorageWarning")).to_be_visible()
        page.screenshot(path=str(out / f"{name}.png"))


def keyboard(page, context, args, out):
    go(page, args)
    tabs = page.locator('[role="tablist"] [role="tab"]')
    assert tabs.count() == 3
    tabs.nth(0).focus()
    page.keyboard.press("ArrowRight")
    expect(tabs.nth(1)).to_be_focused()
    expect(tabs.nth(1)).to_have_attribute("aria-selected", "true")
    page.keyboard.press("End")
    expect(tabs.nth(2)).to_be_focused()
    expect(page.locator(".course-workspace")).to_have_attribute("data-course-pane", "practice")
    page.keyboard.press("Home")
    expect(tabs.nth(0)).to_be_focused()
    page.keyboard.press("ArrowLeft")
    expect(tabs.nth(2)).to_be_focused()
    lesson = data(page)[0]
    enter(page, lesson["practice"], answer_value(lesson["practice"]))
    page.locator('[data-course-action="check"]').focus()
    page.keyboard.press("Enter")
    feedback(page, True)
    expect(page.locator("#courseFeedback")).to_be_focused()
    page.screenshot(path=str(out / "keyboard.png"))


def layout(surface, name):
    bounds = surface.evaluate("""() => ({w:innerWidth,h:innerHeight,sw:document.documentElement.scrollWidth,
        sh:document.documentElement.scrollHeight,x:scrollX,y:scrollY})""")
    assert bounds["sw"] <= bounds["w"] + 1 and bounds["sh"] <= bounds["h"] + 1, (name, "Document must stay in its viewport", bounds)
    assert bounds["x"] == bounds["y"] == 0, (name, bounds)
    hidden = surface.locator(".course-workspace,.course-workspace *").evaluate_all("""els => els.filter(el =>
      el.getClientRects().length && !el.closest('.sr-only') && !el.matches('input,select,textarea') &&
      ['hidden','clip'].includes(getComputedStyle(el).overflowY) && el.scrollHeight>el.clientHeight+2)
      .map(el=>({classes:el.className,text:el.textContent.trim().slice(0,80),height:el.clientHeight,scroll:el.scrollHeight}))""")
    assert not hidden, (name, "Learning content must remain readable through its own scroll region", hidden)
    clipped = surface.locator(".course-workspace button,.course-workspace h2,.course-workspace h3").evaluate_all("""els=>els.filter(el=>
      el.getClientRects().length && (el.scrollWidth>el.clientWidth+2||el.scrollHeight>el.clientHeight+2))
      .map(el=>({text:el.textContent.trim(),client:[el.clientWidth,el.clientHeight],scroll:[el.scrollWidth,el.scrollHeight]}))""")
    assert not clipped, (name, "Controls and headings must fit their own bounds", clipped)


def within_clip(locator, name):
    bounds = locator.evaluate("""el=>{
      const r=el.getBoundingClientRect(); let clip={left:0,top:0,right:innerWidth,bottom:innerHeight};
      for(let parent=el.parentElement;parent;parent=parent.parentElement){
        const style=getComputedStyle(parent),p=parent.getBoundingClientRect();
        if(['auto','scroll','hidden','clip'].includes(style.overflowX)){clip.left=Math.max(clip.left,p.left);clip.right=Math.min(clip.right,p.right);}
        if(['auto','scroll','hidden','clip'].includes(style.overflowY)){clip.top=Math.max(clip.top,p.top);clip.bottom=Math.min(clip.bottom,p.bottom);}
      }
      return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,clip};
    }""")
    clip = bounds["clip"]
    assert bounds["left"] >= clip["left"]-1 and bounds["right"] <= clip["right"]+1 and bounds["top"] >= clip["top"]-1 and bounds["bottom"] <= clip["bottom"]+1, (name,"Primary control must be available without scrolling",bounds)


def visual_views(surface, page, out):
    for lesson in data(surface):
        choose_lesson(surface, lesson)
        for pane in PANES:
            tab(surface, pane)
            layout(surface, f'{lesson["id"]}/{pane}')
            viewport = surface.evaluate("() => ({width:innerWidth,height:innerHeight})")
            if viewport["width"] >= 1200 and viewport["height"] >= 800:
                if pane == "basics":
                    within_clip(surface.locator('[data-course-action="example"]'), f'{lesson["id"]}/basics CTA')
                if pane == "practice":
                    within_clip(surface.locator('[data-course-action="check"]'), f'{lesson["id"]}/practice submit')
            if viewport["width"] < 600:
                nav = surface.locator('.course-lessons').evaluate("""el=>({height:el.getBoundingClientRect().height,buttons:[...el.querySelectorAll('button')].map(b=>({top:b.getBoundingClientRect().top,height:b.getBoundingClientRect().height}))})""")
                assert max(button["top"] for button in nav["buttons"]) - min(button["top"] for button in nav["buttons"]) <= 2, ("Mobile lessons must occupy one horizontal row",nav)
                assert nav["height"] <= 52, ("Mobile lesson navigation uses too much screen height",nav)
                within_clip(surface.locator(f'[data-course-lesson="{lesson["id"]}"]'), "Active mobile lesson")
            page.screenshot(path=str(out / f'{lesson["id"]}-{pane}.png'))


def mobile_persistence(page, context, args, out):
    go(page, args)
    last = data(page)[-1]
    choose_lesson(page, last)
    tab(page, "practice")
    selected = page.locator(f'[data-course-lesson="{last["id"]}"]')
    within_clip(selected, "Last mobile lesson after selection")
    page.reload(wait_until="domcontentloaded")
    expect(selected).to_have_attribute("aria-current", "step")
    within_clip(selected, "Last mobile lesson after reload")
    page.screenshot(path=str(out / "last-lesson-reloaded.png"))
    page.locator('.nav-item[data-page="home"]').click()
    expect(page.locator(".page-content")).to_have_attribute("data-view", "home")
    page.locator('.nav-item[data-page="course"]').click()
    expect(selected).to_have_attribute("aria-current", "step")
    within_clip(selected, "Last mobile lesson after leaving and returning")
    expect(page.locator(".course-workspace")).to_have_attribute("data-course-pane", "practice")
    page.screenshot(path=str(out / "last-lesson-returned.png"))


def visual(page, context, args, out):
    go(page, args)
    visual_views(page, page, out)


def iframe_visual(page, context, args, out):
    page.goto(args.url)
    page.set_content('<!doctype html><style>html,body{margin:0}iframe{display:block;width:900px;height:650px;border:0}</style><iframe title="Notion viewport proxy"></iframe>')
    frame = page.locator("iframe").element_handle().content_frame()
    frame.goto(view_url(args.url, "course"), wait_until="domcontentloaded")
    visual_views(frame, page, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/_auction/auction-study.html"))
    parser.add_argument("--executable", default=os.environ.get("BROWSER_EXECUTABLE"))
    parser.add_argument("--artifacts", type=Path, default=Path("/tmp/auction-course-browser"))
    parser.add_argument("--only", nargs="+")
    args = parser.parse_args()
    scenarios = [("course-flow", course_flow, 1440, 900), ("amount-validation", amount_validation, 1440, 900), ("storage-failure", storage_failure, 1440, 900), ("storage-conflict", storage_conflict, 1440, 900), ("corrupt-storage", corrupt_storage, 1440, 900), ("keyboard", keyboard, 1440, 900), ("mobile-persistence", mobile_persistence, 375, 667), ("1440x900", visual, 1440, 900), ("375x667", visual, 375, 667), ("320x568", visual, 320, 568), ("844x390", visual, 844, 390), ("900x650-iframe", iframe_visual, 1024, 768)]
    if args.only:
        unknown = set(args.only) - {item[0] for item in scenarios}
        if unknown:
            parser.error(f"Unknown scenarios: {', '.join(sorted(unknown))}")
        scenarios = [item for item in scenarios if item[0] in args.only]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = args.artifacts / stamp
    out.mkdir(parents=True, exist_ok=False)
    report = {"started": stamp, "url": args.url, "limitations": ["Viewport and local iframe checks are not actual device or Notion-app tests.", "The course uses fictional evidence. These tests do not establish expert legal review or independent learning outcomes."], "results": []}
    with sync_playwright() as playwright:
        options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if args.executable:
            options["executable_path"] = args.executable
        browser = playwright.chromium.launch(**options)
        for name, test, width, height in scenarios:
            directory = out / name
            directory.mkdir()
            context = browser.new_context(viewport={"width": width, "height": height}, locale="ko-KR")
            context.set_default_timeout(6000)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            result = {"name": name, "viewport": [width, height], "artifacts": str(directory)}
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
