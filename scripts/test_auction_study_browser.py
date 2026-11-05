"""Functional regression checks for the static auction study notebook.

Run with a local static server. Uses system Chromium, no external services.
AUCTION_STUDY_URL may override the default local page URL.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


URL = os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/auction-study.html")
KEY = "auction-study-v1"


def notebook(page):
    return page.evaluate("key => JSON.parse(localStorage.getItem(key))", KEY)


def active(data):
    return next(c for c in data["cases"] if c["id"] == data["active"])


def seed(page, data):
    page.evaluate("([key,value]) => localStorage.setItem(key,JSON.stringify(value))", [KEY, data])
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("h1")).to_be_visible()


def navigate(page, name):
    page.locator(f'.nav-item[data-page="{name}"]').click()


def favorable(page):
    # The initial sample is intentionally unverified. Seed checked user evidence,
    # rather than satisfying the final signal by changing application functions.
    navigate(page, "money")
    page.locator('[data-finance="bid"]').fill("28000")
    data = notebook(page)
    c = active(data)
    c["rights"] = [{"status": "clear", "evidence": f"검토 서류 {i + 1}: 원문·열람일 확인"} for i in range(6)]
    c["finance"]["saleTax"] = 100
    c["region"].update({
        "supply": "manageable", "demand": "steady", "checked": "2026-11-05",
        "evidence": "최근 거래량과 입주 예정 물량을 직접 확인함",
        "comps": [
            {"price": "33000", "area": "84", "date": "2026-10-01", "source": "국토부 실거래·동일 단지·중층"},
            {"price": "34000", "area": "84", "date": "2026-10-14", "source": "국토부 실거래·동일 단지·중층"},
            {"price": "", "area": "", "date": "", "source": ""},
        ],
    })
    seed(page, data)
    return data


def shell_and_calculator(page):
    expect(page.locator("h1")).to_have_text("물건 검토 한눈에 보기")
    expect(page.locator(".case-banner")).to_contain_text("가상 연습 물건 · 실매물 아님")
    expect(page.locator(".cash-number")).to_contain_text("13,756")
    navigate(page, "money")
    page.locator('[data-finance="bid"]').fill("30000")
    expect(page.locator(".cash-number")).to_contain_text("15,778")
    assert active(notebook(page))["finance"]["bid"] == 30000
    page.locator('[data-finance="bid"]').fill("")
    expect(page.locator('[data-results] [role="alert"]')).to_contain_text("예상 낙찰가")
    expect(page.locator(".cash-number")).to_have_count(0)
    expect(page.locator("#cashSchedule")).to_contain_text("입력 오류")
    page.locator('[data-finance="bid"]').fill("24500")
    expect(page.locator(".cash-number")).to_contain_text("10,218")
    page.reload(wait_until="domcontentloaded")
    navigate(page, "money")
    expect(page.locator('[data-finance="bid"]')).to_have_value("24500")


def rights_and_new_case(page):
    navigate(page, "rights")
    for i in range(6):
        page.locator(f'[data-right="{i}"]').select_option("clear")
    expect(page.locator(".decision-title")).to_have_text("아직은, 검토 보류")
    expect(page.locator("#rightsCount")).to_have_text("0 / 6 완료")
    before_example = notebook(page)
    page.locator(".study-example summary").click()
    expect(page.locator(".example-answer")).to_be_visible()
    expect(page.locator(".example-document").first).to_contain_text("법원 매각물건명세서")
    assert notebook(page) == before_example, "Opening a lesson must not fill user evidence"
    for i in range(6):
        page.locator(f'[data-evidence="{i}"]').fill(f"실제 확인 서류와 질문 {i + 1}")
    # No blur/change event here: the completion state must follow the active input.
    expect(page.locator(".panel-header .badge").first).to_have_text("6 / 6 완료")
    page.reload(wait_until="domcontentloaded")
    navigate(page, "rights")
    expect(page.locator('[data-evidence="5"]')).to_have_value("실제 확인 서류와 질문 6")
    old_id = active(notebook(page))["id"]
    page.locator('.topbar [data-action="new"]').click()
    expect(page.locator("#caseDialog")).to_be_visible()
    page.locator("#case-name").fill("나의 두 번째 경매 물건")
    page.locator("#case-address").fill("사용자가 확인한 주소")
    page.locator('#caseForm button[type="submit"]').click()
    expect(page.locator(".case-title")).to_have_text("나의 두 번째 경매 물건")
    data = notebook(page)
    assert len(data["cases"]) == 2
    assert any(c["id"] == old_id for c in data["cases"])
    assert active(data)["demo"] is False
    assert active(data)["rights"][0]["status"] == "unknown"
    page.reload(wait_until="domcontentloaded")
    expect(page.locator(".case-title")).to_have_text("나의 두 번째 경매 물건")


def immediate_decision_revalidation(page):
    favorable(page)
    navigate(page, "rights")
    expect(page.locator(".decision-title")).to_have_text("다음 검토 단계로")
    page.locator('[data-evidence="0"]').fill("")
    expect(page.locator(".decision-title")).to_have_text("아직은, 검토 보류")
    expect(page.locator(".reason-list").last).to_contain_text("권리분석")
    # The warning is durable, not only a temporary DOM update.
    page.reload(wait_until="domcontentloaded")
    navigate(page, "rights")
    expect(page.locator(".decision-title")).to_have_text("아직은, 검토 보류")


def imports_preserve_and_validate(page):
    favorable(page)
    original = notebook(page)
    original_id = active(original)["id"]
    with page.expect_download() as result:
        page.locator('.sidebar [data-action="export"]').click()
    download = result.value
    exported = json.loads(Path(download.path()).read_text(encoding="utf-8"))
    assert active(exported)["id"] == original_id
    page.locator("#importFile").set_input_files({
        "name": "my-auction-notes.json", "mimeType": "application/json",
        "buffer": json.dumps(exported, ensure_ascii=False).encode("utf-8"),
    })
    expect(page.locator("#toast")).to_contain_text("노트를 추가")
    merged = notebook(page)
    assert len(merged["cases"]) == 2
    assert len({c["id"] for c in merged["cases"]}) == 2
    assert any(c["id"] == original_id for c in merged["cases"])
    invalid = copy.deepcopy(exported)
    active(invalid)["region"]["comps"][0]["source"] = 123
    page.locator("#importFile").set_input_files({
        "name": "invalid-notes.json", "mimeType": "application/json",
        "buffer": json.dumps(invalid, ensure_ascii=False).encode("utf-8"),
    })
    expect(page.locator("#toast")).to_contain_text("유효한 경매노트 파일이 아니")
    assert notebook(page) == merged
    navigate(page, "area")
    expect(page.locator("#compSummary")).to_contain_text("2건")


def deposit_liquidity_guard(page):
    data = favorable(page)
    c = active(data)
    c["finance"]["depositRate"] = 100
    # Total equity is affordable; the pre-loan deposit is deliberately not.
    c["finance"]["available"] = 15000
    seed(page, data)
    expect(page.locator(".verdict-heading")).to_have_text("입찰 판단을 보류하고 있어요.")
    expect(page.locator(".overview-tasks")).to_contain_text("보증금")
    navigate(page, "money")
    expect(page.locator("#cashSchedule")).to_contain_text("24,500")
    c["finance"].update({
        "loan": 28000, "depositRate": 10, "available": 0, "reserve": 0,
        "acquisitionRate": 0, "legal": 0, "repairs": 0, "eviction": 0,
        "arrears": 0, "assumed": 0, "loanRate": 0,
    })
    seed(page, data)
    expect(page.locator(".verdict-heading")).to_have_text("입찰 판단을 보류하고 있어요.")
    expect(page.locator(".overview-tasks")).to_contain_text("보증금")


def mobile_navigation(page):
    for name in ["home", "rights", "money", "area", "notes"]:
        navigate(page, name)
        expect(page.locator("h1")).to_be_visible()
        width = page.evaluate("({document:document.documentElement.scrollWidth, viewport:innerWidth})")
        assert width["document"] <= width["viewport"] + 1, (name, width)
    page.screenshot(path="/tmp/auction-study-mobile.png", full_page=True)


def main():
    failures = []
    cases = [
        ("shell_and_calculator", shell_and_calculator, 1440),
        ("rights_and_new_case", rights_and_new_case, 1440),
        ("immediate_decision_revalidation", immediate_decision_revalidation, 1440),
        ("imports_preserve_and_validate", imports_preserve_and_validate, 1440),
        ("deposit_liquidity_guard", deposit_liquidity_guard, 1440),
        ("mobile_navigation", mobile_navigation, 390),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
        for name, check, width in cases:
            context = browser.new_context(viewport={"width": width, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(5000)
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            try:
                response = page.goto(URL, wait_until="domcontentloaded")
                assert response and response.status == 200
                check(page)
                assert not page_errors, page_errors
                print("PASS", name, flush=True)
            except Exception as error:
                failures.append((name, str(error)))
                page.screenshot(path=f"/tmp/auction-study-failed-{name}.png", full_page=True)
                print("FAIL", name, str(error), flush=True)
            finally:
                context.close()
        browser.close()
    print(f"AUCTION_STUDY_BROWSER: {len(cases) - len(failures)} passed, {len(failures)} failed", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
