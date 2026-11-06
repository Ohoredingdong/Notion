"""Real browser QA for fictional auction dossiers, process, and cash calculations.

Every case uses an isolated browser context and locally invented records. The
same-origin iframe is a sizing/embedding proxy, not an actual Notion check.
Run against a local static server; this script never deploys or uses real notes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import traceback
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import expect, sync_playwright


NOTEBOOK = "auction-study-v1"
PRACTICE = "auction-simulation-v1"


def view_url(base, view):
    parts = urlsplit(base)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "view"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query + [("view", view)]), parts.fragment))


def raw(surface, key):
    return surface.evaluate("key => localStorage.getItem(key)", key)


def number(text):
    match = re.search(r"[-−]?[\d,]+(?:\.\d+)?", text)
    assert match, f"No visible amount in {text!r}"
    return float(match.group().replace(",", "").replace("−", "-"))


def near(actual, expected, label):
    assert math.isclose(actual, expected, abs_tol=0.011), (label, actual, expected)


def independent_cash(values):
    """Independent arithmetic, without invoking or importing the app model."""
    v = {k: float(value) for k, value in values.items()}
    tax = v["bid"] * v["acquisitionRate"] / 100
    interest = v["loan"] * v["loanRate"] / 100 * v["months"] / 12
    costs = tax + interest + sum(v[k] for k in ("legal", "repairs", "eviction", "arrears", "assumed"))
    cash = v["bid"] + costs - v["loan"] + v["reserve"]
    deposit = v["minimum"] * v["depositRate"] / 100
    return {
        "cash": cash, "deposit": deposit, "costs": costs,
        "gap": max(0, cash - v["available"], deposit - v["available"]),
        "cashGap": max(0, cash - v["available"]),
        "depositGap": max(0, deposit - v["available"]),
        "profit": v["sale"] * (1 - v["sellingRate"] / 100) - v["saleTax"] - v["bid"] - costs,
        "downside": v["downside"] * (1 - v["sellingRate"] / 100) - v["saleTax"] - v["bid"] - costs,
    }


def navigate(surface, view):
    surface.locator(f'.nav-item[data-page="{view}"]').click()
    expect(surface.locator(f'.page-content[data-view="{view}"]')).to_be_visible()


def pane(surface, name):
    button = surface.locator(f'.sim-pane-tabs [data-sim-pane="{name}"]')
    if button.is_visible():
        button.click()


def stage(surface, index):
    surface.locator(f'.sim-stages [data-sim-go-stage="{index}"]').click()
    expect(surface.locator(".simulation-workspace")).to_have_attribute("data-sim-stage", str(index))


def layout(surface, root, label):
    """Allow deliberate inner scrolling, but reject outer scroll and clipping."""
    metrics = surface.evaluate("""() => ({w:innerWidth,h:innerHeight,
        sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight,
        x:scrollX,y:scrollY})""")
    assert metrics["sw"] <= metrics["w"] + 1 and metrics["sh"] <= metrics["h"] + 1, (label, "outer scroll", metrics)
    assert metrics["x"] == metrics["y"] == 0, (label, "outer page moved", metrics)
    expect(surface.locator(root)).to_be_visible()
    issues = surface.locator(f"{root}, {root} *").evaluate_all("""els => els.flatMap(el => {
      if (!el.getClientRects().length || el.closest('.sr-only') || el.matches('input,select,textarea')) return [];
      const s=getComputedStyle(el), r=el.getBoundingClientRect();
      if(s.display==='none'||s.visibility==='hidden')return [];
      const errors=[];
      if(['hidden','clip'].includes(s.overflowY)&&el.scrollHeight>el.clientHeight+2)
        errors.push('vertical content clipped');
      if(['hidden','clip'].includes(s.overflowX)&&el.scrollWidth>el.clientWidth+2)
        errors.push('horizontal content clipped');
      if(errors.length)return [{tag:el.tagName,classes:el.className,errors,
        client:[el.clientWidth,el.clientHeight],scroll:[el.scrollWidth,el.scrollHeight]}];
      return [];
    })""")
    assert not issues, (label, issues)
    # Critical persistent controls must remain inside the current viewport.
    selectors = ["#simulationCase", ".sim-stages", ".sim-document-footer", ".sim-navigation"] if root == ".simulation-workspace" else [".process-intro", ".process-panes"]
    for selector in selectors:
        element = surface.locator(selector)
        if element.is_visible():
            bounds = element.bounding_box()
            assert bounds and bounds["x"] >= -1 and bounds["y"] >= -1, (label, selector, bounds)
            assert bounds["x"] + bounds["width"] <= metrics["w"] + 1, (label, selector, bounds)
            assert bounds["y"] + bounds["height"] <= metrics["h"] + 1, (label, selector, bounds)


def open_document(surface, doc, reviewed=False):
    pane(surface, "document")
    surface.locator(f'.sim-document-tabs [data-sim-document="{doc["id"]}"]').click()
    expect(surface.locator(".sim-document-heading h2")).to_have_text(doc["title"])
    expect(surface.locator(".sim-paper-tag")).to_contain_text("가상")
    text = surface.locator(".sim-paper").inner_text()
    for section in doc["sections"]:
        assert section["title"] in text
        for row in section["rows"]:
            assert row["label"] in text and str(row["value"]) in text, (doc["id"], row)
    if reviewed:
        button = surface.locator('[data-sim-action="review-document"]')
        if "취소" not in button.inner_text():
            button.click()


def answer(surface, question, index, correct):
    pane(surface, "analysis")
    surface.locator(f'.sim-question-dots [data-sim-question="{index}"]').click()
    choice = question["answerId"] if correct else next(c["id"] for c in question["choices"] if c["id"] != question["answerId"])
    surface.locator(f'[data-sim-choice="{question["id"]}"][value="{choice}"]').check()
    assert surface.locator(".sim-feedback").count() == 0, "Changing an answer must clear stale feedback"
    surface.locator('[data-sim-action="check-answer"]').click()
    feedback = surface.locator(".sim-feedback")
    expect(feedback).to_have_class(re.compile(r"\bcorrect\b" if correct else r"\breview\b"))
    assert question["explanation"] in feedback.inner_text()
    assert feedback.locator(f'[data-sim-document="{question["documentId"]}"]').count() == 1


def assert_sim_cash(surface, values):
    expected = independent_cash(values)
    near(number(surface.locator('[data-sim-result="cashNeeded"]').inner_text()), expected["cash"], "simulation cash")
    for result, key in [("deposit", "deposit"), ("costs", "costs"), ("cashGap", "cashGap"), ("depositGap", "depositGap"), ("profit", "profit"), ("downsideProfit", "downside")]:
        near(number(surface.locator(f'[data-sim-result="{result}"]').inner_text()), expected[key], key)
    return expected


def create_note(surface):
    surface.locator('.topbar [data-action="new"]').click()
    surface.locator("#case-name").fill("보존 검증용 독립 노트")
    surface.locator("#case-address").fill("가상 검증 주소 · 실매물 아님")
    surface.locator('#caseForm button[type="submit"]').click()
    navigate(surface, "notes")
    surface.locator("#thesis").fill("기존 사용자 메모 보존: 한글 <태그> & 금액 123.45")
    return raw(surface, NOTEBOOK)


def curriculum(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    before = create_note(page)
    navigate(page, "simulation")
    cases = page.evaluate("() => AuctionSimulationData.cases")
    assert len(cases) == 3
    known = {"simulation-basic": (13021.5, 3713.5, 1226), "simulation-senior": (18464.5, 670.5, -2314.5), "simulation-hold": (13167, 2368, -1612)}
    for scenario in cases:
        assert scenario["fictional"] is True
        page.locator("#simulationCase").select_option(scenario["id"])
        assert len(scenario["documents"]) == 8 and len(scenario["quiz"]) == 6
        assert page.locator(".sim-document-tabs button").count() == 8
        for doc in scenario["documents"]:
            open_document(page, doc, reviewed=True)
        expect(page.locator(".sim-document-footer > span")).to_have_text("8 / 8종 확인")
        photos = page.locator(".sim-photo")
        assert photos.count() == len(scenario["observations"]) >= 4, "The dossier must show every fictional onsite observation"
        for photo in photos.all():
            assert "AI" in photo.get_attribute("aria-label")
            ratio = photo.evaluate("el => el.getBoundingClientRect().width / el.getBoundingClientRect().height")
            assert math.isclose(ratio, 4 / 3, abs_tol=0.01), ("The 4:3 source photo must preserve its proportions", ratio)
            url = photo.evaluate("el => getComputedStyle(el).backgroundImage.match(/url\\([\"']?(.*?)[\"']?\\)/)[1]")
            image = page.evaluate("""url => new Promise(resolve => {const i=new Image();i.onload=()=>resolve({w:i.naturalWidth,h:i.naturalHeight});i.onerror=()=>resolve(null);i.src=url})""", url)
            assert image and image["w"] > 500 and image["h"] > 250, ("Actual PNG did not load", url, image)
        assert all("AI로 만든 가상" in text and "실매물 사진 아님" in text for text in page.locator(".sim-photos figcaption").all_inner_texts())
        page.screenshot(path=str(artifacts / f'{scenario["id"]}-dossier.png'))
        with page.expect_download() as pending:
            page.locator('[data-sim-action="download"]').click()
        download = pending.value
        destination = artifacts / download.suggested_filename
        download.save_as(destination)
        downloaded = destination.read_text(encoding="utf-8")
        assert "모든 사건·인물·금액·서류는 학습을 위한 가상" in downloaded
        assert downloaded.count("<article>") == 8
        for doc in scenario["documents"]:
            assert f'<h2>{doc["title"]}</h2>' in downloaded
        stage(page, 1)
        for index, question in enumerate(scenario["quiz"]):
            answer(page, question, index, False)
            answer(page, question, index, True)
        stage(page, 2)
        expected = assert_sim_cash(page, scenario["defaults"])
        for key, value in zip(("cash", "profit", "downside"), known[scenario["id"]]):
            near(expected[key], value, f"{scenario['id']} independent fixture {key}")
        page.locator('[data-sim-decision][value="hold"]').check()
        page.locator("#simulationNote").fill(f"{scenario['id']} — 권리와 비용 확인 후 판단한다.")
        page.locator('[data-sim-action="submit"]').click()
        expect(page.locator(".sim-recap")).to_contain_text(scenario["id"])
        if scenario["id"] == "simulation-hold":
            expect(page.locator(".sim-result-status")).to_have_class(re.compile(r"\bhold\b"))
            expect(page.locator(".sim-result-status")).to_contain_text("미확인")
        assert raw(page, NOTEBOOK) == before, "Reading/answering/simulating must not modify the user's notebook bytes"
        layout(page, ".simulation-workspace", scenario["id"])
        page.screenshot(path=str(artifacts / f'{scenario["id"]}-results.png'))
    saved = raw(page, PRACTICE)
    page.reload()
    expect(page.locator("#simulationCase")).to_have_value("simulation-hold")
    expect(page.locator(".simulation-workspace")).to_have_attribute("data-sim-stage", "3")
    expect(page.locator(".sim-recap")).to_contain_text("simulation-hold")
    assert raw(page, PRACTICE) == saved and raw(page, NOTEBOOK) == before
    original_cases = json.loads(before)["cases"]
    page.locator('[data-sim-action="copy"]').click()
    expect(page.locator('.page-content[data-view="money"]')).to_be_visible()
    copied = json.loads(raw(page, NOTEBOOK))
    assert len(copied["cases"]) == len(original_cases) + 1
    # Compare existing case serialization, not only names or counts.
    assert [json.dumps(c, ensure_ascii=False, separators=(",", ":")) for c in copied["cases"][:-1]] == [json.dumps(c, ensure_ascii=False, separators=(",", ":")) for c in original_cases]
    new = copied["cases"][-1]
    assert new["demo"] is True and "모의" in new["name"] and copied["active"] == new["id"]
    assert all(r["status"] == "unknown" and not r["evidence"] for r in new["rights"])
    assert raw(page, PRACTICE) == saved, "Copy must preserve practice progress too"
    navigate(page, "simulation")
    page.locator('[data-sim-action="copy"]').click()
    repeated = json.loads(raw(page, NOTEBOOK))
    assert len(repeated["cases"]) == len(copied["cases"]) + 1
    assert repeated["cases"][:-1] == copied["cases"], "A repeated explicit copy must append, not overwrite its previous copy"
    assert len({case["id"] for case in repeated["cases"]}) == len(repeated["cases"])


def cash_edges(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    cases = page.evaluate("() => AuctionSimulationData.cases")
    scenario = cases[0]
    stage(page, 2)
    values = dict(scenario["defaults"])
    for key, value in {"bid": values["bid"] + 123.4, "loan": values["loan"] - 111.1, "available": 500}.items():
        page.locator(f"#simulation-{key}").fill(str(value))
        values[key] = value
    assert_sim_cash(page, values)
    assert independent_cash(values)["depositGap"] > 0
    expect(page.locator("#simulationCalculation")).to_contain_text("부족")
    for key, value in {"loan": values["bid"], "available": 2500}.items():
        page.locator(f"#simulation-{key}").fill(str(value))
        values[key] = value
    edge = assert_sim_cash(page, values)
    assert edge["cashGap"] == 0 and edge["depositGap"] > 0, "Pre-loan deposit gap must remain visible even with enough eventual equity"
    page.locator("#simulation-bid").fill(str(values["minimum"] - 1))
    expect(page.locator(".sim-calculation-error")).to_be_visible()
    assert page.locator(".sim-cash-result").count() == 0
    page.locator('[data-sim-decision][value="bid"]').check()
    page.locator('[data-sim-action="submit"]').click()
    expect(page.locator(".simulation-workspace")).to_have_attribute("data-sim-stage", "2")
    stage(page, 3)
    assert page.locator(".sim-result-status.review").count() == 0
    assert page.locator('[data-sim-action="copy"]').count() == 0, "An invalid, unsubmitted calculation must not present a copyable verdict"
    expect(page.locator(".sim-analysis")).to_contain_text("판단")


def calculator(page, context, args, artifacts):
    page.goto(view_url(args.url, "money"))
    values = page.evaluate("() => AuctionModel.defaults()")
    for key, value in {"bid": 24500, "loan": 15000.5, "repairs": 813.75}.items():
        page.locator(f'input[data-finance="{key}"]').fill(str(value))
        values[key] = value
    near(number(page.locator("[data-results] .cash-number").inner_text()), independent_cash(values)["cash"], "live calculator")
    expect(page.locator(".calculator-guide")).to_contain_text("낙찰가·대출·비용")
    page.locator('input[data-finance="available"]').fill("500")
    expect(page.locator("[data-results]")).to_contain_text("1,950만원 부족")
    page.locator('input[data-finance="bid"]').fill("")
    expect(page.locator("[data-results] .form-error")).to_be_visible()
    assert page.locator("[data-results] .cash-number").count() == 0
    assert "입력 오류" in page.locator("#cashSchedule").inner_text()
    page.locator('input[data-finance="bid"]').fill("24500")
    page.locator('input[data-finance="loan"]').fill("24500")
    expect(page.locator(".calculator-credit")).to_contain_text("반환")
    page.screenshot(path=str(artifacts / "calculator-cash-timing.png"))


def verdicts(page, context, args, artifacts):
    """A completed checklist cannot turn misunderstood rights or losses green."""
    page.goto(view_url(args.url, "simulation"))
    scenario = page.evaluate("() => AuctionSimulationData.cases[0]")
    for doc in scenario["documents"]:
        open_document(page, doc, reviewed=True)
    stage(page, 1)
    for index, question in enumerate(scenario["quiz"]):
        answer(page, question, index, False)
    stage(page, 2)
    page.locator('[data-sim-decision][value="bid"]').check()
    page.locator('[data-sim-action="submit"]').click()
    expect(page.locator(".sim-result-status")).to_have_class(re.compile(r"\bhold\b"))
    stage(page, 1)
    for index, question in enumerate(scenario["quiz"]):
        answer(page, question, index, True)
    stage(page, 2)
    page.locator('[data-sim-action="submit"]').click()
    expect(page.locator(".sim-result-status")).to_have_class(re.compile(r"\breview\b"))
    values = dict(scenario["defaults"])
    for bid in (40000, 29000, 28500):
        stage(page, 2)
        page.locator("#simulation-bid").fill(str(bid))
        page.locator("#simulation-available").fill("100000")
        values.update(bid=bid, available=100000)
        expected = assert_sim_cash(page, values)
        assert expected["cashGap"] == 0
        assert expected["profit"] < values["targetProfit"] or expected["downside"] < 0
        page.locator('[data-sim-action="submit"]').click()
        expect(page.locator(".sim-result-status")).to_have_class(re.compile(r"\bhold\b"))
    page.screenshot(path=str(artifacts / "loss-must-hold.png"))


def process_checks(surface):
    navigate(surface, "process")
    data = surface.evaluate("() => ({stages:AuctionProcessData.stages,documents:AuctionProcessData.documentSet})")
    assert len(data["stages"]) == 16 and len(data["documents"]) == 9
    for item in data["stages"]:
        button = surface.locator('[data-process-pane="list"]')
        if button.is_visible():
            button.click()
        surface.locator(f'.process-list [data-process-stage="{item["id"]}"]').click()
        expect(surface.locator(".process-detail h2")).to_have_text(item["title"])
        assert item["description"] in surface.locator(".process-detail").inner_text()
        for branch in item["branches"]:
            if branch.get("to"):
                surface.locator(f'.process-branches [data-process-stage="{branch["to"]}"]').click()
                target = next(stage for stage in data["stages"] if stage["id"] == branch["to"])
                expect(surface.locator(".process-detail h2")).to_have_text(target["title"])
                # Restore the stage through the actual list, before next branch.
                button = surface.locator('[data-process-pane="list"]')
                if button.is_visible():
                    button.click()
                surface.locator(f'.process-list [data-process-stage="{item["id"]}"]').click()
    for item in data["documents"]:
        button = surface.locator('[data-process-pane="list"]')
        if button.is_visible():
            button.click()
        surface.locator(f'.process-list [data-process-document="{item["id"]}"]').click()
        expect(surface.locator(".process-detail h2")).to_have_text(item["name"])
        text = surface.locator(".process-detail").inner_text()
        assert item["where"] in text and all(check in text for check in item["checklist"])
    layout(surface, ".auction-process", "process details")


def responsive(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    cases = page.evaluate("() => AuctionSimulationData.cases")
    for scenario in cases:
        page.locator("#simulationCase").select_option(scenario["id"])
        for index in range(4):
            stage(page, index)
            layout(page, ".simulation-workspace", f"{scenario['id']} stage {index}")
            pane(page, "document")
            for doc in scenario["documents"]:
                open_document(page, doc)
            pane(page, "analysis")
            layout(page, ".simulation-workspace", f"{scenario['id']} analysis {index}")
        stage(page, 1)
        answer(page, scenario["quiz"][0], 0, False)
        answer(page, scenario["quiz"][0], 0, True)
        stage(page, 2)
        page.locator("#simulationNote").fill("작은 화면에서도 마지막 판단 버튼에 도달한다.")
        page.locator('[data-sim-decision][value="hold"]').check()
        page.locator('[data-sim-action="submit"]').click()
        expect(page.locator(".sim-recap")).to_contain_text("작은 화면")
        layout(page, ".simulation-workspace", "submitted on responsive viewport")
    page.screenshot(path=str(artifacts / "simulation.png"))
    process_checks(page)
    page.screenshot(path=str(artifacts / "process.png"))


def iframe(page, context, args, artifacts):
    page.goto(args.url)
    page.set_content('<!doctype html><style>html,body{margin:0}iframe{border:0;width:900px;height:650px;display:block}</style><iframe title="Notion size proxy"></iframe>')
    frame = page.locator("iframe").element_handle().content_frame()
    frame.goto(view_url(args.url, "simulation"))
    layout(frame, ".simulation-workspace", "900×650 iframe")
    stage(frame, 1)
    scenario = frame.evaluate("() => AuctionSimulationData.cases[0]")
    answer(frame, scenario["quiz"][0], 0, False)
    answer(frame, scenario["quiz"][0], 0, True)
    stage(frame, 2)
    assert_sim_cash(frame, scenario["defaults"])
    layout(frame, ".simulation-workspace", "iframe calculator")
    process_checks(frame)
    page.screenshot(path=str(artifacts / "notion-size-proxy.png"))


def blocked_storage(page, context, args, artifacts):
    page.add_init_script("""Storage.prototype.getItem=function(){throw new DOMException('Blocked for isolated QA','SecurityError')};Storage.prototype.setItem=function(){throw new DOMException('Blocked for isolated QA','SecurityError')};""")
    page.goto(view_url(args.url, "simulation"))
    expect(page.locator(".sim-live")).to_contain_text("화면")
    layout(page, ".simulation-workspace", "blocked storage")
    page.locator("#simulationCase").select_option("simulation-senior")
    stage(page, 2)
    page.locator("#simulation-bid").fill("28123.4")
    expect(page.locator(".sim-cash-result")).to_be_visible()
    navigate(page, "process")
    expect(page.locator(".auction-process")).to_be_visible()
    navigate(page, "simulation")
    expect(page.locator("#simulationCase")).to_have_value("simulation-senior")
    expect(page.locator("#simulation-bid")).to_have_value("28123.4")
    page.screenshot(path=str(artifacts / "storage-denied.png"))


def corrupt_storage(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    before = create_note(page)
    corrupt = '{"version":1,"records": ["keep original bytes"]}'
    page.evaluate("([key,value]) => localStorage.setItem(key,value)", [PRACTICE, corrupt])
    page.goto(view_url(args.url, "simulation"))
    expect(page.locator(".sim-live")).to_contain_text("원본은 보존")
    stage(page, 2)
    page.locator("#simulation-bid").fill("28001")
    assert raw(page, PRACTICE) == corrupt and raw(page, NOTEBOOK) == before


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/_auction/auction-study.html"))
    parser.add_argument("--artifacts", type=Path, default=Path("/tmp/auction-simulation-browser"))
    parser.add_argument("--executable", default=os.environ.get("BROWSER_EXECUTABLE"))
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = args.artifacts / stamp
    output.mkdir(parents=True, exist_ok=False)
    report = {"started": stamp, "url": args.url, "limitations": ["The iframe is a local Notion size proxy; actual Notion embedding and production deployment are not verified."], "results": []}
    scenarios = [("curriculum-and-preservation", curriculum, 1366, 768), ("cash-edges", cash_edges, 1366, 768), ("live-calculator", calculator, 1440, 900), ("incorrect-and-loss-verdicts", verdicts, 1366, 768), ("desktop-1366x768", responsive, 1366, 768), ("desktop-1440x900", responsive, 1440, 900), ("mobile-390x844", responsive, 390, 844), ("mobile-390x667", responsive, 390, 667), ("notion-proxy-900x650", iframe, 1024, 768), ("storage-denied", blocked_storage, 390, 667), ("corrupt-practice-preserved", corrupt_storage, 1366, 768)]
    with sync_playwright() as playwright:
        launch = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if args.executable:
            launch["executable_path"] = args.executable
        browser = playwright.chromium.launch(**launch)
        for name, test, width, height in scenarios:
            directory = output / name
            directory.mkdir()
            context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True, locale="ko-KR")
            context.set_default_timeout(6000)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            result = {"name": name, "viewport": [width, height]}
            try:
                test(page, context, args, directory)
                assert not errors, ("Uncaught browser exceptions", errors)
                result["status"] = "passed"
            except Exception as error:
                result.update(status="failed", error=str(error), traceback=traceback.format_exc(), browserErrors=errors)
                try:
                    page.screenshot(path=str(directory / "failure.png"), full_page=True)
                except Exception:
                    pass
            finally:
                result["artifacts"] = str(directory)
                report["results"].append(result)
                context.close()
            print(f'{result["status"].upper()}: {name}', flush=True)
            if result["status"] == "failed":
                print(result["error"], flush=True)
        browser.close()
    report["passed"] = sum(r["status"] == "passed" for r in report["results"])
    report["failed"] = len(report["results"]) - report["passed"]
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f'{report["passed"]}/{len(scenarios)} passed. Report: {output / "report.json"}', flush=True)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
