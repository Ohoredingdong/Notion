"""Rights workspace regressions using an isolated local browser context.

Run against a local static server. AUCTION_STUDY_URL overrides the page URL;
BROWSER_EXECUTABLE selects a system browser instead of Playwright Chromium.
The iframe cases are local embed checks, not an actual Notion integration test.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


URL = os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/auction-study.html")
KEY = "auction-study-v1"
DESKTOPS = [(1280, 720), (1366, 768), (1440, 900), (1920, 1080)]
DATES = {"base": "2026-11-05", "move": "2026-11-06", "fixed": "2026-11-07", "demand": "2026-11-08"}


def screenshot(page, label):
    path = Path(f"/tmp/auction-study-rights-layout-{label}.png")
    page.screenshot(path=str(path), full_page=True)


def navigate(surface, name):
    surface.locator(f'.nav-item[data-page="{name}"]').click()
    expect(surface.locator(f'.page-content[data-view="{name}"]')).to_be_visible()


def fixed_document(surface, label):
    geometry = surface.evaluate("""() => ({width:innerWidth, height:innerHeight,
        documentWidth:document.documentElement.scrollWidth,
        documentHeight:document.documentElement.scrollHeight, scrollX, scrollY})""")
    assert geometry["documentWidth"] <= geometry["width"] + 1, (label, geometry)
    assert geometry["documentHeight"] <= geometry["height"] + 1, (label, geometry)
    assert geometry["scrollX"] == geometry["scrollY"] == 0, (label, geometry)


def inside(locator, label):
    expect(locator).to_be_visible()
    bounds = locator.evaluate("""el => {const r=el.getBoundingClientRect();
        return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:innerWidth,height:innerHeight};}""")
    assert bounds["left"] >= -1 and bounds["top"] >= -1, (label, bounds)
    assert bounds["right"] <= bounds["width"] + 1, (label, bounds)
    assert bounds["bottom"] <= bounds["height"] + 1, (label, bounds)


def scroll_owners(surface):
    """Count real vertical scrollers, excluding native text editing controls."""
    return surface.locator(".page-content, .page-content *").evaluate_all("""elements => elements
        .filter(el => {
            const r=el.getBoundingClientRect(), s=getComputedStyle(el);
            return r.width && r.height && !el.matches('input,select,textarea') &&
                ['auto','scroll'].includes(s.overflowY) && el.scrollHeight > el.clientHeight + 1;
        }).map(el => ({classes:el.className,tag:el.tagName,height:el.clientHeight,
            scrollHeight:el.scrollHeight,insideColumn:!!el.closest('.split-layout > div:first-child,.split-layout > .side-column')}))
    """)


def shared_scroll(surface, label, require_no_scroll=False):
    owners = scroll_owners(surface)
    assert len(owners) <= 1, (label, "multiple independent vertical scroll areas", owners)
    assert not any(owner["insideColumn"] for owner in owners), (
        label, "columns must use the shared workspace scroll area", owners
    )
    if require_no_scroll:
        assert not owners, (label, "default desktop rights content should fit without scrolling", owners)
    horizontal = surface.locator(".rights-layout, .rights-layout *").evaluate_all("""elements => elements
        .filter(el => el.getClientRects().length && !el.matches('input,select,textarea') &&
            el.scrollWidth > el.clientWidth + 1)
        .map(el => ({classes:el.className,width:el.clientWidth,scrollWidth:el.scrollWidth}))
    """)
    assert not horizontal, (label, "rights content overflows horizontally", horizontal)
    clipped = surface.locator(".rights-layout, .rights-layout *").evaluate_all("""elements => elements
        .filter(el => el.getClientRects().length && !el.matches('input,select,textarea') &&
            ['hidden','clip'].includes(getComputedStyle(el).overflowY) &&
            el.scrollHeight > el.clientHeight + 1)
        .map(el => ({classes:el.className,height:el.clientHeight,scrollHeight:el.scrollHeight}))
    """)
    assert not clipped, (label, "overflow clipping hides rights content", clipped)
    fixed_document(surface, label)


def select_step(surface, index):
    selector = surface.locator(f'.rights-checklist .rights-step-button[data-right-step="{index}"]')
    selector.click()
    expect(selector).to_have_attribute("aria-pressed", "true")
    expect(surface.locator('.rights-step-button[aria-pressed="true"]')).to_have_count(1)
    cards = surface.locator(".rights-card[data-right-panel]")
    expect(cards).to_have_count(6)
    expect(surface.locator(".rights-card[data-right-panel]:visible")).to_have_count(1)
    expect(surface.locator(f'.rights-card[data-right-panel="{index}"]')).to_be_visible()


def compact_verdict(surface):
    expect(surface.locator(".rights-verdict")).to_have_count(1)
    expect(surface.locator(".rights-verdict .decision-title")).to_be_visible()


def dates_layout(surface, label, desktop):
    fields = surface.locator(".rights-dates .timeline-fields input[type=date]")
    expect(fields).to_have_count(4)
    geometry = fields.evaluate_all("""elements => elements.map(el => {
        const r=el.getBoundingClientRect(), s=getComputedStyle(el);
        const label=el.closest('.field').querySelector('label').getBoundingClientRect();
        return {left:r.left,top:r.top,width:r.width,right:r.right,
            labelTop:label.top,labelHeight:label.height,paddingRight:parseFloat(s.paddingRight)};
    })""")
    for item in geometry:
        assert item["paddingRight"] <= 20, (label, "date input reserves space for a nonexistent unit", item)
        if desktop:
            assert item["width"] >= 160, (label, "native date segments need enough room", item)
    if desktop:
        for first, second in [geometry[:2], geometry[2:]]:
            assert first["left"] < second["left"], (label, "desktop dates should use two aligned columns", geometry)
            assert abs(first["labelTop"] - second["labelTop"]) <= 1, (label, geometry)
            assert abs(first["top"] - second["top"]) <= 1, (label, "date input baselines differ after label wrapping", geometry)


def fill_dates(surface):
    for key, value in DATES.items():
        field = surface.locator(f'.rights-dates [data-field="timeline.{key}"]')
        field.fill(value)
        field.press("Tab")
        expect(field).to_have_value(value)
        compact_verdict(surface)


def retained_dates(surface):
    for key, value in DATES.items():
        expect(surface.locator(f'.rights-dates [data-field="timeline.{key}"]')).to_have_value(value)


def wrapped_date_label(surface, label):
    """Long labels must align inputs naturally rather than rely on one line."""
    first = surface.locator(".rights-dates .timeline-fields .field > label").first
    original_style = first.get_attribute("style")
    try:
        first.evaluate("el => el.style.maxWidth = '80px'")
        assert first.evaluate("el => el.getBoundingClientRect().height > parseFloat(getComputedStyle(el).lineHeight) + 1"), (label, "fixture must actually wrap the date label")
        dates_layout(surface, (label, "wrapped label"), desktop=True)
        assert first.evaluate("el => el.scrollHeight <= el.clientHeight + 1"), (label, "wrapped label is clipped")
        shared_scroll(surface, (label, "wrapped date label"))
    finally:
        first.evaluate("""(el, previous) => {
            if (previous === null) el.removeAttribute('style');
            else el.setAttribute('style', previous);
        }""", original_style)


def desktop_layout(page, label):
    navigate(page, "rights")
    for width, height in DESKTOPS:
        page.set_viewport_size({"width": width, "height": height})
        size_label = f"{label}-{width}x{height}"
        dates_layout(page, size_label, desktop=True)
        for index in range(6):
            select_step(page, index)
            shared_scroll(page, (size_label, index), require_no_scroll=True)
            inside(page.locator(f'.rights-card[data-right-panel="{index}"] [data-evidence="{index}"]'), (size_label, index, "evidence"))
            inside(page.locator(".rights-pagination"), (size_label, index, "previous and next controls"))
            inside(page.locator(".rights-dates"), (size_label, index, "date card"))
            inside(page.locator(".rights-verdict .decision-title"), (size_label, index, "decision"))
        fill_dates(page)
        dates_layout(page, size_label, desktop=True)
        wrapped_date_label(page, size_label)
        select_step(page, 0)
        screenshot(page, size_label)
    page.goto(URL, wait_until="domcontentloaded")
    navigate(page, "rights")
    retained_dates(page)


def six_steps(page, label, mobile=False):
    page.set_viewport_size({"width": 390, "height": 844} if mobile else {"width": 1366, "height": 768})
    navigate(page, "rights")
    fill_dates(page)
    # The app saves the sample only after a real edit. Capture a persisted
    # baseline after entering the dates rather than inventing initial storage.
    before = page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY)
    for index in range(6):
        select_step(page, index)
        page.locator(f'[data-right="{index}"]').select_option("clear")
        page.locator(f'[data-evidence="{index}"]').fill(f"레이아웃 검증 근거 {index + 1}: 원문과 열람일 확인")
        compact_verdict(page)
        expect(page.locator("#rightsCount")).to_have_text(f"{index + 1} / 6 완료")
        shared_scroll(page, (label, "input", index), require_no_scroll=not mobile)
    screenshot(page, label)
    page.goto(URL, wait_until="domcontentloaded")
    navigate(page, "rights")
    retained_dates(page)
    for index in range(6):
        select_step(page, index)
        expect(page.locator(f'[data-evidence="{index}"]')).to_have_value(f"레이아웃 검증 근거 {index + 1}: 원문과 열람일 확인")
        expect(page.locator(f'[data-right="{index}"]')).to_have_value("clear")
    after = page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY)
    original = next(item for item in before["cases"] if item["id"] == before["active"])
    changed = next(item for item in after["cases"] if item["id"] == before["active"])
    assert changed["finance"] == original["finance"], (label, "rights edits must preserve investment inputs")
    assert [item["id"] for item in after["cases"]] == [item["id"] for item in before["cases"]], label
    expect(page.locator("#rightsCount")).to_have_text("6 / 6 완료")

    # Native buttons must work with keyboard activation as well as pointer input.
    first = page.locator('.rights-step-button[data-right-step="0"]')
    first.focus()
    first.press("Enter")
    expect(first).to_have_attribute("aria-pressed", "true")
    first.press("Tab")
    second = page.locator('.rights-step-button[data-right-step="1"]')
    expect(second).to_be_focused()
    second.press("Space")
    expect(second).to_have_attribute("aria-pressed", "true")
    page.locator('.rights-pagination [data-right-step="0"]:visible').click()
    expect(first).to_have_attribute("aria-pressed", "true")
    for index in range(1, 6):
        page.locator(f'.rights-pagination [data-right-step="{index}"]:visible').click()
        expect(page.locator(f'.rights-step-button[data-right-step="{index}"]')).to_have_attribute("aria-pressed", "true")
    reasons = page.locator(".rights-verdict details summary")
    reasons.click()
    expect(page.locator(".rights-verdict .reason-list")).to_be_visible()
    page.locator('.rights-pagination [data-page="money"]:visible').click()
    expect(page.locator('.page-content[data-view="money"]')).to_be_visible()
    fixed_document(page, (label, "next finance step"))


def iframe_layout(page, label):
    page.set_viewport_size({"width": 1100, "height": 800})
    page.evaluate("""url => {const iframe=document.createElement('iframe');
        iframe.title='권리분석 임베드 검사';
        iframe.style.cssText='display:block;width:900px;height:650px;border:0';
        iframe.src=url;document.body.replaceChildren(iframe);}""", URL)
    frame = page.locator("iframe").element_handle().content_frame()
    expect(frame.locator("h1")).to_be_visible()
    navigate(frame, "rights")
    dates_layout(frame, label, desktop=False)
    fill_dates(frame)
    for index in range(6):
        select_step(frame, index)
        evidence = frame.locator(f'[data-evidence="{index}"]')
        evidence.scroll_into_view_if_needed()
        inside(evidence, (label, index))
        shared_scroll(frame, (label, index))
    screenshot(page, label)
    frame.goto(URL, wait_until="domcontentloaded")
    navigate(frame, "rights")
    retained_dates(frame)


def all_steps_shared_scroll(page, label):
    for width, height in [(1280, 720), (1366, 768), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        for name in ["rights", "money", "area", "notes"]:
            navigate(page, name)
            shared_scroll(page, (label, width, height, name))
            if name == "rights":
                select_step(page, 5)
                target = page.locator('[data-evidence="5"]')
            elif name == "money":
                target = page.locator('[data-finance="targetProfit"]')
            elif name == "area":
                target = page.locator('.page-content textarea').last
            else:
                target = page.locator("#conclusion")
            target.scroll_into_view_if_needed()
            inside(target, (label, width, height, name, "last input"))
            shared_scroll(page, (label, width, height, name, "after shared scroll"))


def learning_resources(page, label):
    navigate(page, "rights")
    fill_dates(page)
    page.locator('[data-evidence="0"]').fill("학습 자료를 열어도 보존할 나의 확인 기록")
    page.locator('[data-evidence="0"]').press("Tab")
    before = page.evaluate("key => localStorage.getItem(key)", KEY)
    lesson = page.locator(".rights-layout .study-example")
    summary = lesson.locator(":scope > summary")
    expect(summary).to_contain_text("서류 예시·용어·원문")
    summary.focus()
    summary.press("Enter")
    expect(lesson.locator(".example-answer")).to_be_visible()
    expect(lesson.locator(".example-document").nth(0)).to_contain_text("법원 매각물건명세서")
    expect(lesson.locator(".example-document").nth(1)).to_contain_text("등기사항증명서 표제부")
    expect(lesson.locator(".example-document").nth(2)).to_contain_text("내 노트에는 이렇게 기록해요")

    glossary = lesson.locator(".learning-glossary details")
    expect(glossary).to_have_count(4)
    for term in ["말소기준권리", "대항력", "우선변제와 배당요구", "인수금액"]:
        definition = glossary.filter(has=page.locator("summary", has_text=re.compile(f"^{re.escape(term)}$")))
        heading = definition.locator("summary")
        heading.scroll_into_view_if_needed()
        heading.focus()
        heading.press("Enter")
        expect(definition.locator("p")).to_be_visible()
        inside(heading, (label, term))
        assert definition.locator("p").inner_text().strip(), (label, term, "definition is empty")
        heading.press("Enter")
        expect(definition.locator("p")).not_to_be_visible()

    for href in ["https://www.courtauction.go.kr/", "https://www.iros.go.kr/", "https://rt.molit.go.kr/", "https://www.eum.go.kr/"]:
        link = lesson.locator(f'.source-links a[href="{href}"]')
        expect(link).to_have_count(1)
        link.scroll_into_view_if_needed()
        link.focus()
        expect(link).to_be_focused()
        inside(link, (label, href))
    screenshot(page, label)
    summary.scroll_into_view_if_needed()
    summary.focus()
    summary.press("Enter")
    expect(lesson.locator(".example-answer")).not_to_be_visible()
    assert page.evaluate("key => localStorage.getItem(key)", KEY) == before, (
        label, "reading examples, terms or source links must not alter the notebook"
    )
    shared_scroll(page, (label, "lesson closed"), require_no_scroll=True)


def print_all_rights(page, label):
    navigate(page, "rights")
    evidence = {index: f"인쇄 보존 근거 {index + 1}: 확인 기록" for index in range(6)}
    for index in range(6):
        select_step(page, index)
        page.locator(f'[data-evidence="{index}"]').fill(evidence[index])
    # Enter the long value last, then print immediately: a render on another
    # step must not hide a missing update of the print mirror after input.
    evidence[0] = "긴 근거 시작\n" + "등기 원문 <b>그대로 기록</b> & 발급·열람일, 배당요구와 매각 조건을 대조한 확인 기록입니다.\n" * 180 + "전체 근거 마지막 문장"
    assert len(evidence[0]) > 8000
    select_step(page, 0)
    page.locator('[data-evidence="0"]').fill(evidence[0])
    page.locator('[data-evidence="0"]').press("Tab")
    expect(page.locator(".rights-card[data-right-panel]:visible")).to_have_count(1)
    details = page.locator(".rights-verdict .decision-details")
    assert details.get_attribute("open") is None, (label, "print fixture must start with collapsed reasons")
    reasons = details.locator(".reason-list")
    expect(reasons).not_to_be_visible()
    reason_texts = reasons.locator("li").all_text_contents()
    assert reason_texts, (label, "print fixture needs actual unresolved reasons")
    before_print = page.evaluate("key => localStorage.getItem(key)", KEY)
    page.emulate_media(media="print")
    expect(page.locator(".rights-card[data-right-panel]:visible")).to_have_count(6)
    expect(reasons).to_be_visible()
    assert reasons.locator("li").all_text_contents() == reason_texts, (label, "print reasons changed")
    for reason in reasons.locator("li").all():
        expect(reason).to_be_visible()
        assert reason.evaluate("el => el.getBoundingClientRect().height > 0 && el.getClientRects().length > 0"), (label, "closed details suppressed a printed reason")
    for index in range(6):
        card = page.locator(f'.rights-card[data-right-panel="{index}"]')
        expect(card).to_be_visible()
        expect(card.locator(f'[data-evidence="{index}"]')).to_have_value(evidence[index])
        mirror = card.locator(f'.evidence-print[data-print-evidence="{index}"]')
        expect(mirror).to_be_visible()
        assert mirror.text_content() == evidence[index], (label, index, "print mirror omits or changes evidence")
        assert mirror.locator("b").count() == 0, (label, index, "evidence was interpreted as HTML")
        bounds = mirror.evaluate("""el => {
            const r=el.getBoundingClientRect(), card=el.closest('.rights-card').getBoundingClientRect();
            const range=document.createRange();range.selectNodeContents(el);
            const textRects=[...range.getClientRects()];
            const clippedAncestors=[];
            for(let node=el.parentElement;node;node=node.parentElement){
                if(['hidden','clip','auto','scroll'].includes(getComputedStyle(node).overflowY) &&
                    node.scrollHeight > node.clientHeight + 1)
                    clippedAncestors.push({classes:node.className,height:node.clientHeight,scrollHeight:node.scrollHeight});
            }
            return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,
                cardLeft:card.left,cardRight:card.right,cardTop:card.top,cardBottom:card.bottom,
                height:el.clientHeight,scrollHeight:el.scrollHeight,width:el.clientWidth,scrollWidth:el.scrollWidth,
                clippedAncestors,textRects:textRects.length,lastTextBottom:textRects.at(-1)?.bottom};
        }""")
        assert bounds["height"] >= 1 and bounds["scrollHeight"] <= bounds["height"] + 1, (label, index, "print mirror clips long evidence", bounds)
        assert bounds["scrollWidth"] <= bounds["width"] + 1, (label, index, "print evidence overflows horizontally", bounds)
        assert bounds["left"] >= bounds["cardLeft"] - 1 and bounds["right"] <= bounds["cardRight"] + 1, (label, index, bounds)
        assert bounds["top"] >= bounds["cardTop"] - 1 and bounds["bottom"] <= bounds["cardBottom"] + 1, (label, index, "print card does not contain all evidence", bounds)
        assert not bounds["clippedAncestors"], (label, index, "ancestor clips printed evidence", bounds)
        assert bounds["textRects"] > 0 and bounds["lastTextBottom"] <= bounds["bottom"] + 4, (label, index, "last evidence line is not fully rendered", bounds)
        assert card.evaluate("el => el.scrollHeight <= el.clientHeight + 1"), (label, index, "print card clips evidence")
    screenshot(page, label)
    page.emulate_media(media="screen")
    expect(page.locator(".rights-card[data-right-panel]:visible")).to_have_count(1)
    assert page.evaluate("key => localStorage.getItem(key)", KEY) == before_print, (label, "printing altered the notebook")


def main():
    failures = []
    checks = [
        ("desktop", desktop_layout),
        ("six-steps-desktop", six_steps),
        ("six-steps-mobile", lambda page, label: six_steps(page, label, mobile=True)),
        ("iframe-900x650", iframe_layout),
        ("all-steps-shared-scroll", all_steps_shared_scroll),
        ("learning-resources", learning_resources),
        ("print-six-cards", print_all_rights),
    ]
    with sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        for locale in ["en-US", "ko-KR"]:
            for name, check in checks:
                label = re.sub(r"[^a-zA-Z0-9-]", "-", f"{name}-{locale}")
                context = browser.new_context(locale=locale, viewport={"width": 1366, "height": 768})
                page = context.new_page()
                page.set_default_timeout(5000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                try:
                    response = page.goto(URL, wait_until="domcontentloaded")
                    assert response and response.status == 200, (label, "page request failed")
                    check(page, label)
                    assert not errors, (label, errors)
                    print("PASS", label, flush=True)
                except Exception as error:
                    failures.append((label, str(error)))
                    screenshot(page, f"failed-{label}")
                    print("FAIL", label, str(error), flush=True)
                    if os.environ.get("GITHUB_ACTIONS") == "true":
                        detail = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                        print(f"::error title=Auction layout {label}::{detail}", flush=True)
                finally:
                    context.close()
        browser.close()
    total = len(checks) * 2
    print(f"AUCTION_RIGHTS_LAYOUT: {total - len(failures)} passed, {len(failures)} failed", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
