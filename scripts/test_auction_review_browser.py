"""Focused regressions for notebook backups, concurrent tabs, and browser history.

All records are invented in isolated browser contexts. Run against a local
static server or a review URL; this script never deploys or edits real notes.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import traceback
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import expect, sync_playwright


KEY = "auction-study-v1"


def view_url(base, view):
    parts = urlsplit(base)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "view"]
    return urlunsplit(parts._replace(query=urlencode(query + [("view", view)])))


def raw(page):
    return page.evaluate("key => localStorage.getItem(key)", KEY)


def notebook(page):
    return json.loads(raw(page))


def active(data):
    return next(item for item in data["cases"] if item["id"] == data["active"])


def go(page, view):
    page.locator(f'.nav-item[data-page="{view}"]').click()
    expect(page.locator(".page-content")).to_have_attribute("data-view", view)


def seed(page, data):
    page.evaluate("([key,value]) => localStorage.setItem(key,JSON.stringify(value))", [KEY, data])
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("h1")).to_be_visible()


def export_bytes(page):
    with page.expect_download() as result:
        page.locator('.sidebar [data-action="export"]').click()
    return Path(result.value.path()).read_bytes()


def import_bytes(page, payload):
    page.locator("#importFile").set_input_files({
        "name": "invented-auction-backup.json", "mimeType": "application/json", "buffer": payload,
    })


def create_case(page, name):
    page.locator('.topbar [data-action="new"]').click()
    page.locator("#case-name").fill(name)
    page.locator('#caseForm button[type="submit"]').click()


def starting_data(page):
    page.locator('[data-evidence="0"]').fill("Invented original evidence")
    return notebook(page)


def long_notes(page, context, browser, args):
    data = starting_data(page)
    evidence = "기존의 긴 근거 " * 3000 + '</textarea><img src=x onerror="window.backupXSS=1">'
    assert len(evidence) > 20000
    active(data)["rights"][0]["evidence"] = evidence
    active(data)["thesis"] = "기존 메모" * 6000
    seed(page, data)
    expect(page.locator('[data-evidence="0"]')).to_have_value(evidence)
    expect(page.locator('[data-evidence="0"]')).to_have_attribute("maxlength", "20000")
    expect(page.locator("#storageWarning")).to_be_hidden()
    page.locator('[data-right="0"]').select_option("checking")
    page.reload(wait_until="domcontentloaded")
    assert active(notebook(page))["rights"][0]["evidence"] == evidence
    payload = export_bytes(page)
    with browser.new_context(accept_downloads=True) as restored:
        target = restored.new_page()
        target.goto(view_url(args.url, "rights"))
        import_bytes(target, payload)
        expect(target.locator("#toast")).to_contain_text("1개 노트를 추가")
        target.reload(wait_until="domcontentloaded")
        assert active(notebook(target))["rights"][0]["evidence"] == evidence
        assert active(notebook(target))["thesis"] == active(data)["thesis"]
        assert target.evaluate("() => window.backupXSS === undefined")
        expect(target.locator("#storageWarning")).to_be_hidden()
    go(page, "learn")
    page.locator('[data-study-mode="case"]').click()
    expect(page.locator("#studyEvidence")).to_have_attribute("maxlength", "20000")
    expect(page.locator("#studyEvidence")).to_have_value(evidence)


def full_backup(page, context, browser, args):
    data = starting_data(page)
    original = active(data)
    data["cases"] = [{**copy.deepcopy(original), "id": f"invented-cap-{i}", "name": f"Invented note {i}"} for i in range(100)]
    data["active"] = data["cases"][0]["id"]
    seed(page, data)
    payload = export_bytes(page)
    with browser.new_context(accept_downloads=True) as restored:
        target = restored.new_page()
        target.goto(view_url(args.url, "rights"))
        assert raw(target) is None, "The initial example must be unsaved"
        import_bytes(target, payload)
        expect(target.locator("#caseSelect option")).to_have_count(100)
        target.reload(wait_until="domcontentloaded")
        expect(target.locator("#caseSelect option")).to_have_count(100)
        assert [c["name"] for c in notebook(target)["cases"]] == [c["name"] for c in data["cases"]]
    before = raw(page)
    create = page.locator('.topbar [data-action="new"]')
    create.click()
    expect(page.locator("#toast")).to_contain_text("100개")
    assert raw(page) == before


def note_management(page, context, browser, args):
    starting_data(page)
    create_case(page, "Keep this other note")
    page.locator('[data-evidence="0"]').fill("Other note evidence must remain identical")
    create_case(page, 'Delete only this <img src=x onerror="window.deleteXSS=1">')
    before = notebook(page)
    target = active(before)
    page.locator('.topbar [data-action="manage"]').click()
    expect(page.locator("#deleteCaseName")).to_have_text(target["name"])
    expect(page.locator("#deleteCaseCancel")).to_be_focused()
    page.locator("#deleteCaseSubmit").click()
    assert notebook(page) == before, "Deletion requires an explicit checkbox confirmation"
    page.locator("#deleteCaseCancel").click()
    assert notebook(page) == before
    page.locator('.topbar [data-action="manage"]').click()
    with page.expect_download() as result:
        page.locator('#caseDialog [data-action="export"]').click()
    assert json.loads(Path(result.value.path()).read_bytes()) == before
    expect(page.locator("#caseDialog")).to_be_visible()
    page.locator("#confirmCaseDelete").check()
    page.locator("#deleteCaseSubmit").click()
    expect(page.locator("#caseDialog")).not_to_be_visible()
    after = notebook(page)
    assert after["cases"] == [item for item in before["cases"] if item["id"] != target["id"]]
    assert target["id"] not in {item["id"] for item in after["cases"]}
    assert page.evaluate("() => window.deleteXSS === undefined")
    page.reload(wait_until="domcontentloaded")
    assert notebook(page) == after


def last_note_management(page, context, browser, args):
    starting_data(page)
    original = notebook(page)
    go(page, "learn")
    page.locator('input[name="studyAnswer"]').first.check()
    go(page, "simulation")
    page.locator('.sim-stages [data-sim-go-stage="2"]').click()
    page.locator("#simulationNote").fill("Independent simulation record")
    independent = page.evaluate("() => [localStorage.getItem('auction-study-lessons-v1'),localStorage.getItem('auction-simulation-v1')]")
    go(page, "rights")
    page.locator('.topbar [data-action="manage"]').click()
    expect(page.locator("#caseDialog")).to_contain_text("빈 노트 1개")
    with page.expect_download() as result:
        page.locator('#caseDialog [data-action="export"]').click()
    backup = Path(result.value.path()).read_bytes()
    assert json.loads(backup) == original
    page.locator("#confirmCaseDelete").check()
    page.locator("#deleteCaseSubmit").click()
    replacement = notebook(page)
    assert len(replacement["cases"]) == 1
    blank = active(replacement)
    assert blank["id"] != original["active"] and blank["demo"] is False
    assert all(value == "" for value in blank["finance"].values())
    assert all(item == {"status": "unknown", "evidence": ""} for item in blank["rights"])
    assert page.evaluate("() => [localStorage.getItem('auction-study-lessons-v1'),localStorage.getItem('auction-simulation-v1')]") == independent
    page.reload(wait_until="domcontentloaded")
    assert notebook(page) == replacement
    with browser.new_context() as restored:
        target = restored.new_page()
        target.goto(view_url(args.url, "rights"))
        import_bytes(target, backup)
        expect(target.locator("#toast")).to_contain_text("1개 노트를 추가")
        assert active(notebook(target))["rights"] == active(original)["rights"]


def full_notebook_cleanup(page, context, browser, args):
    # Reach the limit through the same dialogs used by a person, without seeding
    # localStorage or modifying the app's in-memory state.
    for index in range(99):
        create_case(page, f"UI-created note {index + 1}")
    expect(page.locator("#caseSelect option")).to_have_count(100)
    before = notebook(page)
    page.locator('.topbar [data-action="new"]').click()
    expect(page.locator("#toast")).to_contain_text("정리")
    page.locator('.topbar [data-action="manage"]').click()
    with page.expect_download() as result:
        page.locator('#caseDialog [data-action="export"]').click()
    assert json.loads(Path(result.value.path()).read_bytes()) == before
    target_id = before["active"]
    page.locator("#confirmCaseDelete").check()
    page.locator("#deleteCaseSubmit").click()
    expect(page.locator("#caseSelect option")).to_have_count(99)
    assert notebook(page)["cases"] == [item for item in before["cases"] if item["id"] != target_id]
    create_case(page, "New note after explicit cleanup")
    expect(page.locator("#caseSelect option")).to_have_count(100)
    assert active(notebook(page))["name"] == "New note after explicit cleanup"


def deletion_conflict(page, context, browser, args):
    starting_data(page)
    create_case(page, "Target visible in both tabs")
    second = context.new_page()
    second.goto(view_url(args.url, "rights"))
    working = notebook(second)
    second.locator('.topbar [data-action="manage"]').click()
    second.locator("#confirmCaseDelete").check()
    create_case(page, "Keep newer note from another tab")
    expected = raw(page)
    expect(second.locator("#deleteCaseError")).to_contain_text("다른 탭")
    expect(second.locator("#deleteCaseSubmit")).to_be_disabled()
    with second.expect_download() as result:
        second.locator('#caseDialog [data-action="export"]').click()
    assert json.loads(Path(result.value.path()).read_bytes()) == working
    assert raw(second) == expected
    second.locator("#deleteCaseCancel").click()
    second.locator('.topbar [data-action="manage"]').click()
    expect(second.locator("#deleteCaseSubmit")).to_be_disabled()
    assert raw(second) == expected


def deletion_write_failure(page, context, browser, args):
    starting_data(page)
    create_case(page, "Preserve this target if storage fails")
    before = notebook(page)
    page.locator('.topbar [data-action="manage"]').click()
    page.locator("#confirmCaseDelete").check()
    page.evaluate("""() => {
      const write=Storage.prototype.setItem;
      Storage.prototype.setItem=function(key,value) {
        if(key==='auction-study-v1')throw new DOMException('Invented quota failure','QuotaExceededError');
        return write.call(this,key,value);
      };
    }""")
    page.locator("#deleteCaseSubmit").click()
    expect(page.locator("#deleteCaseSubmit")).to_be_disabled()
    expect(page.locator("#deleteCaseError")).to_contain_text("삭제를 멈췄")
    expect(page.locator("#toast")).to_contain_text("삭제하지 않았어요")
    assert notebook(page) == before
    with page.expect_download() as result:
        page.locator('#caseDialog [data-action="export"]').click()
    assert json.loads(Path(result.value.path()).read_bytes()) == before


def large_backup(page, context, browser, args):
    data = starting_data(page)
    original = active(data)
    data["cases"] = []
    for index in range(6):
        item = copy.deepcopy(original)
        item.update(id=f"invented-large-{index}", name=f"Invented long note {index}")
        for right in item["rights"]:
            right["evidence"] = "한" * 20000
        data["cases"].append(item)
    data["active"] = data["cases"][0]["id"]
    seed(page, data)
    payload = export_bytes(page)
    assert len(payload) > 2 * 1024 * 1024
    with browser.new_context(accept_downloads=True) as restored:
        target = restored.new_page()
        target.goto(view_url(args.url, "rights"))
        import_bytes(target, payload)
        expect(target.locator("#caseSelect option")).to_have_count(6)
        target.reload(wait_until="domcontentloaded")
        assert len(notebook(target)["cases"]) == 6
        assert all(len(right["evidence"]) == 20000 for item in notebook(target)["cases"] for right in item["rights"])


def edited_example_preserved(page, context, browser, args):
    original = starting_data(page)
    before_id = active(original)["id"]
    payload = export_bytes(page)
    import_bytes(page, payload)
    expect(page.locator("#caseSelect option")).to_have_count(2)
    saved = notebook(page)
    assert any(item["id"] == before_id and item["rights"][0]["evidence"] == "Invented original evidence" for item in saved["cases"])


def concurrent_tabs(page, context, browser, args):
    starting_data(page)
    second = context.new_page()
    second.goto(view_url(args.url, "rights"))
    create_case(page, "Invented note created in tab A")
    expected = raw(page)
    expect(second.locator("#storageWarning")).to_contain_text("다른 탭")
    second.locator('[data-evidence="0"]').fill("Unsaved draft from tab B")
    expect(second.locator('[data-evidence="0"]')).to_be_focused()
    assert raw(second) == expected, "A stale tab must not overwrite the newer notebook"
    expect(second.locator("#saveStatus")).to_contain_text("저장 불가")
    working = json.loads(export_bytes(second))
    assert active(working)["rights"][0]["evidence"] == "Unsaved draft from tab B"
    page.reload(wait_until="domcontentloaded")
    assert any(item["name"] == "Invented note created in tab A" for item in notebook(page)["cases"])
    second.close()
    # Browsers may delay background storage events. The write guard must also
    # detect a conflict when the event has not been delivered.
    delayed = context.new_page()
    delayed.add_init_script("window.addEventListener('storage', event => event.stopImmediatePropagation())")
    delayed.goto(view_url(args.url, "rights"))
    page.locator('[data-evidence="0"]').fill("Newer persisted evidence from tab A")
    expected = raw(page)
    delayed.locator('[data-evidence="0"]').fill("Draft written before storage event")
    assert raw(delayed) == expected
    expect(delayed.locator("#storageWarning")).to_contain_text("다른 탭")
    assert active(json.loads(export_bytes(delayed)))["rights"][0]["evidence"] == "Draft written before storage event"


def failed_storage(page, context, browser, args):
    context.add_init_script("""(() => {
      const write = Storage.prototype.setItem;
      Storage.prototype.setItem = function(key,value) {
        if (key === 'auction-study-v1') throw new DOMException('Invented quota failure','QuotaExceededError');
        return write.call(this,key,value);
      };
    })();""")
    page.reload(wait_until="domcontentloaded")
    page.locator('[data-evidence="0"]').fill("Draft preserved after quota failure")
    expect(page.locator("#saveStatus")).to_contain_text("저장 불가")
    expect(page.locator("#storageWarning")).to_be_visible()
    assert raw(page) is None
    payload = export_bytes(page)
    assert active(json.loads(payload))["rights"][0]["evidence"] == "Draft preserved after quota failure"
    page.locator('.page-heading [data-action="edit"]').click()
    page.locator("#case-name").fill("Invented edit after quota failure")
    page.locator('#caseForm button[type="submit"]').click()
    expect(page.locator("#toast")).to_contain_text("이 화면에 유지")
    expect(page.locator("#toast")).to_contain_text("백업")
    assert "저장했어요" not in page.locator("#toast").inner_text()
    import_bytes(page, payload)
    expect(page.locator("#toast")).to_contain_text("이 화면에 가져왔어요")
    expect(page.locator("#toast")).to_contain_text("백업")
    create_case(page, "Invented new note after quota failure")
    expect(page.locator("#toast")).to_contain_text("이 화면에 만들었어요")
    expect(page.locator("#toast")).to_contain_text("백업")
    go(page, "simulation")
    page.locator('.sim-stages [data-sim-go-stage="2"]').click()
    page.locator('[data-sim-decision][value="hold"]').check()
    page.locator('[data-sim-action="submit"]').click()
    page.locator('[data-sim-action="copy"]').click()
    expect(page.locator("#toast")).to_contain_text("이 화면에 만들었어요")
    expect(page.locator("#toast")).to_contain_text("백업")
    assert len(json.loads(export_bytes(page))["cases"]) == 4
    assert raw(page) is None


def corrupt_original(page, context, browser, args):
    original = '{"version":1,"cases":"invented corrupt bytes, preserve these"}'
    page.evaluate("([key,value]) => localStorage.setItem(key,value)", [KEY, original])
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#storageWarning")).to_be_visible()
    page.locator('[data-evidence="0"]').fill("Working draft with corrupt original preserved")
    assert raw(page) == original
    assert active(json.loads(export_bytes(page)))["rights"][0]["evidence"] == "Working draft with corrupt original preserved"


def empty_originals(page, context, browser, args):
    for key, view in [(KEY, "rights"), ("auction-study-lessons-v1", "learn"), ("auction-simulation-v1", "simulation")]:
        with browser.new_context(accept_downloads=True) as isolated:
            target = isolated.new_page()
            target.goto(view_url(args.url, "rights"))
            target.evaluate("key => localStorage.setItem(key,'')", key)
            target.goto(view_url(args.url, view))
            if view == "rights":
                expect(target.locator("#storageWarning")).to_be_visible()
                target.locator('[data-evidence="0"]').fill("Draft after an empty stored notebook")
                assert active(json.loads(export_bytes(target)))["rights"][0]["evidence"] == "Draft after an empty stored notebook"
            elif view == "learn":
                expect(target.locator(".study-storage-warning")).to_be_visible()
                target.locator('input[name="studyAnswer"]').first.check()
                target.locator('[data-study-action="check"]').click()
                expect(target.locator(".study-progress")).to_contain_text("저장 안 됨")
            else:
                expect(target.locator(".sim-live")).to_contain_text("읽지 못")
                target.locator('.sim-stages [data-sim-go-stage="2"]').click()
                target.locator("#simulationNote").fill("Draft after an empty stored practice")
                expect(target.locator("#simulationNote")).to_have_value("Draft after an empty stored practice")
            assert target.evaluate("key => localStorage.getItem(key)", key) == "", key


def malformed_simulation_records(page, context, browser, args):
    scenario = page.evaluate("() => AuctionSimulationData.cases[0]")
    case_id, question_id = scenario["id"], scenario["quiz"][0]["id"]
    records = [None, [], "broken record", {"answers": None}, {"inputs": []},
               {"reviewed": "broken documents"}, {"answers": {question_id: None}}, {"inputs": {"bid": None}}]
    key = "auction-simulation-v1"
    for record in records:
        original = json.dumps({"version": 1, "caseId": case_id, "records": {case_id: record}})
        with browser.new_context() as isolated:
            target = isolated.new_page()
            target.goto(view_url(args.url, "rights"))
            target.evaluate("([key,value]) => localStorage.setItem(key,value)", [key, original])
            target.goto(view_url(args.url, "simulation"))
            expect(target.locator(".sim-live")).to_contain_text("읽지 못")
            target.locator('.sim-stages [data-sim-go-stage="2"]').click()
            target.locator("#simulation-bid").fill("28500")
            target.locator("#simulationNote").fill("Draft with a malformed saved case")
            expect(target.locator("#simulation-bid")).to_have_value("28500")
            expect(target.locator('[data-sim-action="export-progress"]')).to_be_visible()
            assert target.evaluate("key => localStorage.getItem(key)", key) == original, record


def malformed_learning_records(page, context, browser, args):
    lesson = page.evaluate("() => AuctionLessons.cases[0]")
    lesson_id, step_id = lesson["id"], lesson["steps"][0]["id"]
    records = [None, [], "broken lesson", {step_id: None}, {step_id: []}, {step_id: "broken answer"}]
    key = "auction-study-lessons-v1"
    for record in records:
        original = json.dumps({"version": 1, "caseId": lesson_id, "answers": {lesson_id: record}})
        with browser.new_context() as isolated:
            target = isolated.new_page()
            target.goto(view_url(args.url, "rights"))
            target.evaluate("([key,value]) => localStorage.setItem(key,value)", [key, original])
            target.goto(view_url(args.url, "learn"))
            expect(target.locator(".study-storage-warning")).to_be_visible()
            target.locator('input[name="studyAnswer"]').first.check()
            target.locator('[data-study-action="check"]').click()
            expect(target.locator('input[name="studyAnswer"]').first).to_be_checked()
            expect(target.locator(".study-progress")).to_contain_text("저장 안 됨")
            assert target.evaluate("key => localStorage.getItem(key)", key) == original, record


def legacy_practice_compatibility(page, context, browser, args):
    scenario = page.evaluate("() => AuctionSimulationData.cases[0]")
    case_id, question = scenario["id"], scenario["quiz"][0]
    future = {"keep": ["opaque", 1]}
    simulation = {"version": 1, "caseId": case_id, "futureRoot": future, "records": {
        case_id: {"futureRecord": future, "inputs": {"bid": "28500", "futureInput": future, "sale": "999999"},
                  "answers": {question["id"]: {"choiceId": question["choices"][0]["id"], "futureAnswer": future},
                              "future-question": {"checked": True, "opaque": future}}},
        "future-case": {"opaque": future}}}
    key = "auction-simulation-v1"
    with browser.new_context() as isolated:
        target = isolated.new_page()
        target.goto(view_url(args.url, "rights"))
        target.evaluate("([key,value]) => localStorage.setItem(key,JSON.stringify(value))", [key, simulation])
        target.goto(view_url(args.url, "simulation"))
        expect(target.locator('[data-sim-action="export-progress"]')).to_be_hidden()
        target.locator('.sim-stages [data-sim-go-stage="1"]').click()
        expect(target.locator(".sim-question-progress")).to_contain_text("해설 0개")
        expect(target.locator('input[name="simulation-choice"]').first).to_be_checked()
        target.locator('input[name="simulation-choice"]').nth(1).check()
        target.locator('[data-sim-action="check-answer"]').click()
        expect(target.locator(".sim-question-progress")).to_contain_text("해설 1개")
        target.locator('.sim-stages [data-sim-go-stage="2"]').click()
        expect(target.locator("#simulation-bid")).to_have_value("28500")
        expected_profit = target.evaluate("values => AuctionFormat.money(AuctionModel.calculate({...values,bid:28500}).profit)", scenario["defaults"])
        expect(target.locator('[data-sim-result="profit"]')).to_have_text(expected_profit)
        target.locator("#simulationNote").fill("Optional version-one fields remain usable")
        saved = target.evaluate("key => JSON.parse(localStorage.getItem(key))", key)
        assert saved["futureRoot"] == future and saved["records"]["future-case"] == {"opaque": future}
        record = saved["records"][case_id]
        assert record["futureRecord"] == record["inputs"]["futureInput"] == record["answers"][question["id"]]["futureAnswer"] == future
        assert record["inputs"]["sale"] == "999999", "An unsupported field stays stored without entering the current calculator"
        assert record["answers"]["future-question"] == simulation["records"][case_id]["answers"]["future-question"]
        target.locator('[data-sim-decision][value="hold"]').check()
        target.locator('[data-sim-action="submit"]').click()
        target.locator('[data-sim-action="copy"]').click()
        assert active(notebook(target))["finance"]["sale"] == scenario["defaults"]["sale"], "Copy must use the displayed, validated model rather than hidden future inputs"

    lesson = page.evaluate("() => AuctionLessons.cases[0]")
    lesson_id, step = lesson["id"], lesson["steps"][0]
    learning = {"version": 1, "caseId": lesson_id, "futureRoot": future, "answers": {
        lesson_id: {step["id"]: {"choiceId": step["choices"][0]["id"], "futureAnswer": future},
                    "future-step": {"checked": True, "opaque": future}},
        "future-lesson": {"opaque": future}}}
    key = "auction-study-lessons-v1"
    with browser.new_context() as isolated:
        target = isolated.new_page()
        target.goto(view_url(args.url, "rights"))
        target.evaluate("([key,value]) => localStorage.setItem(key,JSON.stringify(value))", [key, learning])
        target.goto(view_url(args.url, "learn"))
        expect(target.locator(".study-storage-warning")).to_have_count(0)
        expect(target.locator(".study-progress")).to_have_text("학습 0 / 6")
        expect(target.locator('input[name="studyAnswer"]').first).to_be_checked()
        target.locator('input[name="studyAnswer"]').nth(1).check()
        target.locator('[data-study-action="check"]').click()
        expect(target.locator(".study-progress")).to_have_text("학습 1 / 6")
        saved = target.evaluate("key => JSON.parse(localStorage.getItem(key))", key)
        assert saved["futureRoot"] == saved["answers"][lesson_id][step["id"]]["futureAnswer"] == future
        assert saved["answers"]["future-lesson"] == learning["answers"]["future-lesson"]
        assert saved["answers"][lesson_id]["future-step"] == learning["answers"][lesson_id]["future-step"]


def learning_tabs(page, context, browser, args):
    key = "auction-study-lessons-v1"
    go(page, "learn")
    page.locator('input[name="studyAnswer"]').first.check()
    page.locator('[data-study-action="check"]').click()
    second = context.new_page()
    second.goto(view_url(args.url, "learn"))
    page.locator('input[name="studyAnswer"]').nth(1).check()
    page.locator('[data-study-action="check"]').click()
    expected = page.evaluate("key => localStorage.getItem(key)", key)
    expect(second.locator(".study-storage-warning")).to_contain_text("다른 탭")
    second.locator('input[name="studyAnswer"]').nth(1).check()
    assert second.evaluate("key => localStorage.getItem(key)", key) == expected
    second.locator('input[name="studyAnswer"]').first.check()
    second.locator('[data-study-action="check"]').click()
    expect(second.locator('input[name="studyAnswer"]').first).to_be_checked()
    assert second.evaluate("key => localStorage.getItem(key)", key) == expected
    expect(second.locator(".study-progress")).to_contain_text("저장 안 됨")


def learning_write_failure(page, context, browser, args):
    go(page, "learn")
    page.evaluate("""() => {
      const write=Storage.prototype.setItem;
      Storage.prototype.setItem=function(key,value) {
        if(key==='auction-study-lessons-v1')throw new DOMException('Invented quota failure','QuotaExceededError');
        return write.call(this,key,value);
      };
    }""")
    page.locator('input[name="studyAnswer"]').nth(1).check()
    expect(page.locator(".study-storage-warning")).to_be_visible()
    expect(page.locator(".study-storage-warning")).to_contain_text("저장하지 못")
    expect(page.locator('input[name="studyAnswer"]').nth(1)).to_be_checked()
    assert page.evaluate("() => localStorage.getItem('auction-study-lessons-v1')") is None


def simulation_tabs(page, context, browser, args):
    key = "auction-simulation-v1"
    go(page, "simulation")
    page.locator('.sim-stages [data-sim-go-stage="2"]').click()
    page.locator("#simulationNote").fill("Invented initial simulation reasoning")
    second = context.new_page()
    second.goto(view_url(args.url, "simulation"))
    page.locator("#simulationNote").fill("Newer simulation reasoning from tab A")
    expected = page.evaluate("key => localStorage.getItem(key)", key)
    expect(second.locator(".sim-live")).to_contain_text("다른 탭")
    second.locator("#simulationNote").fill("Draft simulation reasoning from tab B")
    expect(second.locator("#simulationNote")).to_be_focused()
    assert second.evaluate("key => localStorage.getItem(key)", key) == expected
    with second.expect_download() as result:
        second.locator('[data-sim-action="export-progress"]').click()
    payload = json.loads(Path(result.value.path()).read_bytes())
    progress = payload["progress"]
    assert progress["records"][progress["caseId"]]["note"] == "Draft simulation reasoning from tab B"


def navigation_history(page, context, browser, args):
    parts = urlsplit(view_url(args.url, "unknown"))
    query = parse_qsl(parts.query, keep_blank_values=True) + [("review", "preserve")]
    page.goto(urlunsplit(parts._replace(query=urlencode(query), fragment="history")))
    expect(page.locator(".page-content")).to_have_attribute("data-view", "course")
    assert dict(parse_qsl(urlsplit(page.url).query))["view"] == "course"
    # The beginner entry changes, while the existing document route stays usable.
    go(page, "learn")
    expect(page.locator(".page-content")).to_have_attribute("data-view", "learn")
    go(page, "simulation")
    go(page, "process")
    assert dict(parse_qsl(urlsplit(page.url).query))["view"] == "process"
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".page-content")).to_have_attribute("data-view", "process")
    go(page, "notes")
    page.go_back(wait_until="domcontentloaded")
    expect(page.locator(".page-content")).to_have_attribute("data-view", "process")
    page.go_back(wait_until="domcontentloaded")
    expect(page.locator(".page-content")).to_have_attribute("data-view", "simulation")
    page.go_forward(wait_until="domcontentloaded")
    expect(page.locator(".page-content")).to_have_attribute("data-view", "process")
    assert dict(parse_qsl(urlsplit(page.url).query))["review"] == "preserve"
    assert urlsplit(page.url).fragment == "history"
    create_case(page, "Invented new-case navigation")
    assert dict(parse_qsl(urlsplit(page.url).query))["view"] == "rights"
    go(page, "simulation")
    page.locator('.sim-stages [data-sim-go-stage="2"]').click()
    page.locator('[data-sim-decision][value="hold"]').check()
    page.locator("#simulationNote").fill("Invented reasoning copied with calculation")
    page.locator('[data-sim-action="submit"]').click()
    page.locator('[data-sim-action="copy"]').click()
    expect(page.locator(".page-content")).to_have_attribute("data-view", "money")
    assert dict(parse_qsl(urlsplit(page.url).query))["view"] == "money"
    assert "Invented reasoning" in active(notebook(page))["thesis"]


def fixed_loan_limit(page, context, browser, args):
    data = starting_data(page)
    active(data)["finance"].update(loan=28000, sale=31000, downside=31000, targetProfit=1000, saleTax=500)
    seed(page, data)
    go(page, "notes")
    expect(page.locator(".page-content")).to_contain_text("대출 재설정 참고값")
    expect(page.locator(".page-content")).to_contain_text("현재 고정 대출액에서는 목표를 만족하는 입찰 상한이 없어")
    expect(page.locator(".page-content")).to_contain_text("27,047.47")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/_auction/auction-study.html"))
    parser.add_argument("--executable", default=os.environ.get("BROWSER_EXECUTABLE"))
    parser.add_argument("--artifacts", default="/tmp/auction-review-browser")
    args = parser.parse_args()
    artifacts = Path(args.artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    report = {"started": datetime.now(timezone.utc).isoformat(), "url": args.url, "results": []}
    checks = [long_notes, full_backup, note_management, last_note_management, full_notebook_cleanup,
              deletion_conflict, deletion_write_failure, large_backup, edited_example_preserved, concurrent_tabs,
              failed_storage, corrupt_original, empty_originals, malformed_simulation_records,
              malformed_learning_records, legacy_practice_compatibility, learning_tabs, learning_write_failure,
              simulation_tabs, navigation_history, fixed_loan_limit]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.executable, headless=True, args=["--no-sandbox"])
        for check in checks:
            with browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True) as context:
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                try:
                    page.goto(view_url(args.url, "rights"), wait_until="domcontentloaded")
                    check(page, context, browser, args)
                    assert not errors, errors
                    result = {"name": check.__name__, "status": "passed"}
                except Exception:
                    result = {"name": check.__name__, "status": "failed", "error": traceback.format_exc(), "page_errors": errors}
                    page.screenshot(path=str(artifacts / f"{check.__name__}-failure.png"), full_page=True)
                report["results"].append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
        browser.close()
    (artifacts / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = sum(item["status"] == "failed" for item in report["results"])
    print(f"AUCTION_REVIEW_BROWSER: {len(checks) - failures} passed, {failures} failed", flush=True)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
