"""Real-browser regressions for guided practice and user-owned auction documents.

Fixtures and PDFs exist only inside independent browser contexts. The local
iframe is an embedding proxy, not proof of actual Notion integration.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import expect, sync_playwright


BASE_URL = os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/auction-study.html")
NOTEBOOK = "auction-study-v1"
LESSONS = "auction-study-lessons-v1"
DESKTOPS = [(1280, 720), (1366, 768), (1440, 900), (1920, 1080)]
OUT = Path("/tmp")


def view_url(view="learn"):
    parts = urlsplit(BASE_URL)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "view"]
    query.append(("view", view))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def shot(page, label):
    path = OUT / f"auction-study-learning-{label}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def go_learning(surface, mode="practice"):
    surface.locator('.nav-item[data-page="learn"]').click()
    expect(surface.locator(".learning-workspace")).to_be_visible()
    surface.locator(f'[data-study-mode="{mode}"]').click()


def choose_step(surface, index):
    surface.locator(f'button[data-study-step="{index}"]').first.click()


def choose_pane(surface, pane):
    button = surface.locator(f'button[data-study-pane="{pane}"]')
    if button.count() and button.first.is_visible():
        button.first.click()


def notebook(surface):
    return surface.evaluate("key => JSON.parse(localStorage.getItem(key))", NOTEBOOK)


def active(data):
    return next(item for item in data["cases"] if item["id"] == data["active"])


def current_lessons(surface):
    cases = surface.evaluate("() => window.AuctionLessons?.cases")
    assert isinstance(cases, list) and len(cases) >= 2, "Two real lesson definitions must load"
    for case in cases[:2]:
        assert case.get("fictional") is True, "Practice cases must identify fictional evidence"
        assert len(case.get("steps", [])) == 6, "Every lesson must provide all six analysis steps"
        for step in case["steps"]:
            ids = [choice["id"] for choice in step["choices"]]
            assert step["correctChoice"] in ids and len(set(ids)) >= 2
            assert step.get("explanation", "").strip(), "The answer must teach its reason"
            assert any(row.get("focus") for row in step.get("rows", [])), "The lesson must identify supporting document rows"
    return cases[:2]


def select_lesson(surface, case):
    surface.locator("#studyCaseSelect").select_option(case["id"])


def check_answer(surface, step, correct):
    answer = step["correctChoice"] if correct else next(item["id"] for item in step["choices"] if item["id"] != step["correctChoice"])
    surface.locator(f'input[name="studyAnswer"][value="{answer}"]').check()
    surface.locator('[data-study-action="check"]').click()
    feedback = surface.locator("#studyFeedback")
    expect(feedback).to_be_visible()
    expect(feedback).to_have_attribute("data-correct", "true" if correct else "false")
    # A colored success badge alone is not an explanation.
    text = feedback.inner_text().strip()
    assert len(text) >= 25, "Feedback must include a useful explanation"
    assert step["explanation"].strip() in text, "Feedback must explain the actual selected lesson"
    highlighted = surface.locator(".study-document-row.focused dt").all_inner_texts()
    assert highlighted == [row["label"] for row in step["rows"] if row.get("focus")], "Feedback must highlight the actual supporting rows, not unrelated evidence"


def inside(locator, label):
    expect(locator).to_be_visible()
    bounds = locator.evaluate("""el => { const r=el.getBoundingClientRect();
        return {left:r.left, top:r.top, right:r.right, bottom:r.bottom,
            width:innerWidth, height:innerHeight}; }""")
    assert bounds["left"] >= -1 and bounds["top"] >= -1, (label, bounds)
    assert bounds["right"] <= bounds["width"] + 1, (label, bounds)
    assert bounds["bottom"] <= bounds["height"] + 1, (label, bounds)


def fixed_document(surface, label):
    bounds = surface.evaluate("""() => ({width:innerWidth,height:innerHeight,
        scrollWidth:document.documentElement.scrollWidth,scrollHeight:document.documentElement.scrollHeight,
        scrollX,scrollY})""")
    assert bounds["scrollWidth"] <= bounds["width"] + 1, (label, bounds)
    assert bounds["scrollHeight"] <= bounds["height"] + 1, (label, bounds)
    assert bounds["scrollX"] == bounds["scrollY"] == 0, (label, bounds)


def working_area_fits(surface, label, desktop=False):
    fixed_document(surface, label)
    inside(surface.locator(".learning-workspace"), (label, "workspace"))
    inside(surface.locator('[data-study-action="check"]'), (label, "answer control"))
    inside(surface.locator('[data-study-action="hint"]'), (label, "hint control"))
    clipped = surface.locator(".learning-workspace, .learning-workspace *").evaluate_all("""elements => elements
        .filter(el => el.getClientRects().length && !el.matches('input,select,textarea,iframe') && !el.closest('.sr-only') &&
            ['hidden','clip'].includes(getComputedStyle(el).overflowY) && el.scrollHeight > el.clientHeight+1)
        .map(el => ({classes:el.className,height:el.clientHeight,scrollHeight:el.scrollHeight}))""")
    assert not clipped, (label, "clipping hides learning content", clipped)
    if desktop:
        scrollers = surface.locator(".learning-workspace, .learning-workspace *").evaluate_all("""elements => elements
            .filter(el => el.getClientRects().length && !el.matches('input,select,textarea,iframe') && !el.closest('.sr-only') &&
                ['auto','scroll'].includes(getComputedStyle(el).overflowY) && el.scrollHeight > el.clientHeight+1)
            .map(el => ({classes:el.className,height:el.clientHeight,scrollHeight:el.scrollHeight}))""")
        assert not scrollers, (label, "basic desktop lesson needs scrolling", scrollers)


def create_actual_case(page, name):
    page.locator('.topbar [data-action="new"]').click()
    page.locator("#case-name").fill(name)
    page.locator("#case-address").fill("독립 브라우저 검증용 주소 · 실제 물건 아님")
    page.locator('#caseForm button[type="submit"]').click()
    return active(notebook(page))["id"]


def pdf_bytes(label="User-owned test PDF"):
    stream = f"BT /F1 14 Tf 50 750 Td ({label}) Tj ET".encode("ascii")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    start = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(output)


def upload(surface, name, data, mime="application/pdf"):
    surface.locator("#studyDocument").set_input_files({"name": name, "mimeType": mime, "buffer": data})


def latest_pdf_wins(page, first_data, iteration):
    # Delay only browser file I/O, not the application handler or its result.
    # Both selections still travel through the actual File input/change path.
    page.evaluate("""() => {
        window.__nativeStudyBlobText = Blob.prototype.text;
        window.__holdNextStudyRead = true;
        window.__releaseStudyHeader = null;
        Blob.prototype.text = function(...args) {
            const result = window.__nativeStudyBlobText.apply(this,args);
            if (!window.__holdNextStudyRead) return result;
            window.__holdNextStudyRead = false;
            return new Promise((resolve,reject) => {
                window.__releaseStudyHeader = async () => {
                    try { resolve(await result); } catch(error) { reject(error); }
                };
            });
        };
    }""")
    upload(page, f"delayed-old-{iteration}.pdf", first_data)
    page.wait_for_function("() => typeof window.__releaseStudyHeader === 'function'")
    latest_name = f"auction-browser-A-latest-{iteration}.pdf"
    latest_data = pdf_bytes(f"Latest document {iteration}, test fixture only")
    upload(page, latest_name, latest_data)
    expect(page.locator(".study-upload-bar > span")).to_have_text(latest_name)
    expect(page.locator("#studySourceError")).not_to_be_visible()
    latest_source = page.locator("#studyPdf").get_attribute("src")
    page.evaluate("""async () => {
        await window.__releaseStudyHeader();
        await new Promise(resolve => requestAnimationFrame(()=>requestAnimationFrame(resolve)));
        Blob.prototype.text = window.__nativeStudyBlobText;
    }""")
    expect(page.locator("#studyPdf")).to_have_attribute("src", latest_source)
    expect(page.locator(".study-upload-bar > span")).to_have_text(latest_name)
    expect(page.locator("#studySourceError")).not_to_be_visible()
    # A stale callback must not revoke the latest blob while leaving its old
    # URL in the DOM. Fetching that real local blob detects the revoked case.
    contents = page.evaluate("url => fetch(url).then(response=>response.text())", latest_source.split("#", 1)[0])
    assert contents == latest_data.decode("ascii"), "Latest selected PDF bytes must remain available after the older read completes"
    return latest_source


def practice_curriculum(page, context, label):
    page.goto(view_url("home"), wait_until="domcontentloaded")
    create_actual_case(page, "연습과 분리되어야 하는 실제 분석 노트")
    before = page.evaluate("key => localStorage.getItem(key)", NOTEBOOK)
    go_learning(page)
    cases = current_lessons(page)
    for case in cases:
        select_lesson(page, case)
        for index, step in enumerate(case["steps"]):
            choose_step(page, index)
            page.locator('[data-study-action="hint"]').click()
            assert page.locator(".study-document-row.focused").count() > 0
            check_answer(page, step, False)
            check_answer(page, step, True)
            assert page.evaluate("key => localStorage.getItem(key)", NOTEBOOK) == before
            if index < 5:
                page.locator(f'#studyGuidePane [data-study-step="{index + 1}"]').click()
                expect(page.locator('#studyGuidePane .study-card-header h2')).to_have_text(case["steps"][index + 1]["title"])
        expect(page.locator(".study-progress")).to_contain_text(re.compile(r"6\s*/\s*6"))
        page.locator('#studyGuidePane [data-study-action="finish"]').click()
        expect(page.locator('[data-study-mode="case"]')).to_have_attribute("aria-pressed", "true")
        expect(page.locator('.study-real-guide [data-right]')).to_have_value("unknown")
        expect(page.locator('.study-real-guide [data-evidence]')).to_have_value("")
        assert page.evaluate("key => localStorage.getItem(key)", NOTEBOOK) == before, "Applying a lesson must not copy fictional answers to an actual property"
        go_learning(page, "practice")
    saved = page.evaluate("key => localStorage.getItem(key)", LESSONS)
    assert saved and all(case["id"] in saved for case in cases), "Progress must be stored by lesson case"
    page.goto(view_url(), wait_until="domcontentloaded")
    go_learning(page)
    for case in cases:
        select_lesson(page, case)
        expect(page.locator(".study-progress")).to_contain_text(re.compile(r"6\s*/\s*6"))
    assert page.evaluate("key => localStorage.getItem(key)", NOTEBOOK) == before
    shot(page, label)


def actual_documents(page, context, label):
    first_id = create_actual_case(page, "문서 A를 보관할 분석 노트")
    go_learning(page, "case")
    choose_step(page, 2)
    before = active(notebook(page))
    upload(page, "auction-browser-A.pdf", pdf_bytes("Document A, test fixture only"))
    viewer = page.locator("#studyPdf")
    expect(viewer).to_be_visible()
    expect(viewer).to_have_attribute("title", "선택한 경매 PDF 자료")
    source_a = viewer.get_attribute("src")
    assert source_a and source_a.startswith("blob:"), "PDF must remain a local object URL"
    source_a = latest_pdf_wins(page, pdf_bytes("Delayed valid document, test fixture only"), 1)
    source_a = latest_pdf_wins(page, b"NOT-A-PDF", 2)
    after_upload = active(notebook(page))
    assert after_upload["rights"] == before["rights"], "Viewing a PDF must not fabricate rights conclusions"
    assert after_upload["finance"] == before["finance"], "Viewing a PDF must not invent investment values"

    for value in ["javascript:alert('unsafe')", "http://example.test/auction.pdf", "https://user:password@example.test/auction.pdf"]:
        page.locator("#studySourceURL").fill(value)
        page.locator('[data-study-action="open-source"]').click()
        expect(page.locator("#studySourceError")).to_be_visible()
        assert len(context.pages) == 1, "An unsafe source must not open a window"
        expect(viewer).to_have_attribute("src", source_a)
    for name, data, mime in [("not-a-pdf.pdf", b"plain text, not a PDF", "application/pdf"),
                             ("wrong-type.txt", pdf_bytes(), "text/plain"),
                             ("too-large.pdf", b"%PDF-1.4\n" + b"x" * (20 * 1024 * 1024), "application/pdf")]:
        upload(page, name, data, mime)
        expect(page.locator("#studySourceError")).to_be_visible()
        expect(viewer).to_have_attribute("src", source_a)

    requests = []
    context.route("https://example.test/**", lambda route: (requests.append(route.request.url), route.abort()))
    page.locator("#studySourceURL").fill("https://example.test/auction-source.pdf")
    with context.expect_page() as opened, context.expect_event("request", predicate=lambda request: request.url == "https://example.test/auction-source.pdf"):
        page.locator('[data-study-action="open-source"]').click()
    popup = opened.value
    popup.close()
    assert "https://example.test/auction-source.pdf" in requests, "The HTTPS action must actually open the selected link"
    expect(viewer).to_have_attribute("src", source_a)

    second_id = create_actual_case(page, "문서 B를 보관할 분석 노트")
    go_learning(page, "case")
    assert second_id != first_id
    assert not page.locator('#studyPdf[src^="blob:"]:visible').count(), "Another case must not inherit the previous PDF"
    upload(page, "auction-browser-B.pdf", pdf_bytes("Document B, test fixture only"))
    source_b = page.locator("#studyPdf").get_attribute("src")
    assert source_b and source_b.startswith("blob:") and source_b != source_a
    page.locator("#caseSelect").select_option(first_id)
    go_learning(page, "case")
    expect(page.locator("#studyPdf")).to_have_attribute("src", source_a)
    choose_step(page, 2)
    page.locator('[data-right="2"]').select_option("checking")
    text = "실제 문서 대조 후 남길 테스트 근거: 점유·전입·배당요구 확인 필요"
    page.locator('[data-evidence="2"]').fill(text)
    data = notebook(page)
    assert active(data)["rights"][2] == {"status": "checking", "evidence": text}
    assert active(data)["finance"] == before["finance"]
    other = next(item for item in data["cases"] if item["id"] == second_id)
    assert other["rights"][2]["evidence"] == "", "Editing one case must not overwrite another case"
    shot(page, label)
    choose_step(page, 5)
    page.locator('#studyGuidePane [data-study-action="finish"]').click()
    expect(page.locator('.page-content[data-view="money"]')).to_be_visible()
    assert active(notebook(page))["rights"][2]["evidence"] == text
    page.goto(view_url(), wait_until="domcontentloaded")
    go_learning(page, "case")
    choose_step(page, 2)
    expect(page.locator('[data-evidence="2"]')).to_have_value(text)
    expect(page.locator('[data-right="2"]')).to_have_value("checking")
    assert not page.locator('#studyPdf[src^="blob:"]:visible').count(), "Session-only PDFs must not be misrepresented as restored after reload"


def desktop_learning(page, context, label):
    go_learning(page)
    cases = current_lessons(page)
    for width, height in DESKTOPS:
        page.set_viewport_size({"width": width, "height": height})
        for case in cases:
            select_lesson(page, case)
            for index, step in enumerate(case["steps"]):
                choose_step(page, index)
                working_area_fits(page, (label, width, height, case["id"], index, "question"), desktop=True)
                check_answer(page, step, False)
                working_area_fits(page, (label, width, height, case["id"], index, "wrong feedback"), desktop=True)
                check_answer(page, step, True)
                working_area_fits(page, (label, width, height, case["id"], index, "correct feedback"), desktop=True)
        shot(page, f"{label}-{width}x{height}")


def mobile_learning(page, context, label):
    go_learning(page)
    lesson = current_lessons(page)[0]
    for width, height in [(390, 844), (390, 667)]:
        page.set_viewport_size({"width": width, "height": height})
        select_lesson(page, lesson)
        for index, step in enumerate(lesson["steps"]):
            choose_step(page, index)
            choose_pane(page, "document")
            inside(page.locator(".study-document"), (label, height, index, "document pane"))
            fixed_document(page, (label, height, index))
            choose_pane(page, "guide")
            answer = page.locator('[data-study-action="check"]')
            answer.scroll_into_view_if_needed()
            inside(answer, (label, height, index, "answer control after allowed pane scroll"))
            check_answer(page, step, False)
            answer.scroll_into_view_if_needed()
            inside(answer, (label, height, index, "answer after feedback"))
            owners = page.locator(".learning-workspace, .learning-workspace *").evaluate_all("""elements => elements
                .filter(el => el.getClientRects().length && !el.matches('input,select,textarea,iframe') && !el.closest('.sr-only') &&
                    ['auto','scroll'].includes(getComputedStyle(el).overflowY) && el.scrollHeight>el.clientHeight+1)
                .map(el => ({classes:el.className,height:el.clientHeight,scrollHeight:el.scrollHeight}))""")
            assert len(owners) <= 1, (label, height, index, "competing active-pane scrollers", owners)
            fixed_document(page, (label, height, index, "feedback"))
            choose_pane(page, "document")
            assert page.locator(".study-document-row.focused").count() > 0
        choose_pane(page, "guide")
        shot(page, f"{label}-{height}")


def iframe_learning(page, context, label):
    page.set_viewport_size({"width": 1100, "height": 800})
    page.evaluate("""url => {const frame=document.createElement('iframe');frame.title='경매 학습 임베드';
        frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-forms allow-popups');
        frame.style.cssText='display:block;width:900px;height:650px;border:0';frame.src=url;
        document.body.replaceChildren(frame);}""", view_url())
    surface = page.locator("iframe").element_handle().content_frame()
    expect(surface.locator(".learning-workspace")).to_be_visible()
    go_learning(surface)
    case = current_lessons(surface)[0]
    for index, step in enumerate(case["steps"]):
        choose_step(surface, index)
        choose_pane(surface, "document")
        inside(surface.locator(".study-document"), (label, index, "document"))
        choose_pane(surface, "guide")
        check_answer(surface, step, False)
        inside(surface.locator('[data-study-action="check"]'), (label, index, "check"))
        fixed_document(surface, (label, index))
    shot(page, label)


def font_fallback(page, context, label):
    context.route("**/*", lambda route: route.abort() if route.request.resource_type == "font" else route.continue_())
    page.reload(wait_until="domcontentloaded")
    # Explicitly exercise fallback metrics; a substring search for "serif"
    # would incorrectly accept "sans-serif" without changing any rendered font.
    page.add_style_tag(content="body.auction-app {font-family:serif!important}")
    assert page.locator("body").evaluate("e=>getComputedStyle(e).fontFamily").strip().lower() == "serif"
    go_learning(page)
    font = page.locator(".study-document").evaluate("e=>({family:getComputedStyle(e).fontFamily,size:parseFloat(getComputedStyle(e).fontSize),width:e.getBoundingClientRect().width})")
    assert re.search(r"(?:^|,)\s*serif\s*(?:,|$)", font["family"].lower()), (label, "Document reading must have a serif fallback", font)
    assert font["size"] >= 12 and font["width"] > 100, (label, font)
    case = current_lessons(page)[0]
    choose_step(page, 0)
    check_answer(page, case["steps"][0], True)
    working_area_fits(page, label, desktop=True)
    shot(page, label)


def blocked_storage(page, context, label):
    page.add_init_script("""(() => {const fail=()=>{throw new DOMException('Test-only blocked storage','SecurityError');};
        Storage.prototype.getItem=fail;Storage.prototype.setItem=fail;Storage.prototype.removeItem=fail;})();""")
    page.reload(wait_until="domcontentloaded")
    go_learning(page)
    case = current_lessons(page)[0]
    choose_step(page, 0)
    check_answer(page, case["steps"][0], True)
    expect(page.locator(".learning-workspace")).to_be_visible()
    assert re.search(r"저장.*(불가|실패|안|못)|내보내기|이번 화면|현재 화면", page.locator("body").inner_text()), "Blocked storage must not be presented as durable success"
    shot(page, label)


def main():
    scenarios = [("practice-curriculum", practice_curriculum), ("actual-documents", actual_documents),
                 ("desktop-fit", desktop_learning), ("mobile-panes", mobile_learning),
                 ("iframe-panes", iframe_learning), ("font-fallback", font_fallback),
                 ("blocked-storage", blocked_storage)]
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "url": view_url(),
              "limitations": ["Independent test browser contexts only", "Local iframe proxy, not actual Notion UI", "Test PDFs are not real auction evidence"], "results": []}
    with sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["BROWSER_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        for name, check in scenarios:
            context = browser.new_context(viewport={"width": 1366, "height": 768}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(7000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            result = {"name": name, "passed": False}
            try:
                response = page.goto(view_url(), wait_until="domcontentloaded")
                assert response and response.status == 200, "Learning page did not return HTTP 200"
                expect(page.locator(".learning-workspace")).to_be_visible()
                check(page, context, name)
                assert not errors, errors
                result["passed"] = True
                print("PASS", name, flush=True)
            except Exception as error:
                result["error"] = str(error)
                result["screenshot"] = shot(page, "failed-" + name)
                message = str(error).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print(f"::error title=Auction learning browser {name}::{message}", flush=True)
                print("FAIL", name, str(error), flush=True)
            finally:
                report["results"].append(result)
                context.close()
        browser.close()
    report["passed"] = sum(result["passed"] for result in report["results"])
    report["failed"] = len(report["results"]) - report["passed"]
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (OUT / "auction-study-learning-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"AUCTION_LEARNING_BROWSER: {report['passed']} passed, {report['failed']} failed", flush=True)
    if report["failed"] or not report["results"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
