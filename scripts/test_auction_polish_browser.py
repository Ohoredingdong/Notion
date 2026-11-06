"""Browser regressions for money precision, bid ceilings, case photos and copy.

All notebook values are fictional and isolated. Screenshots cover the agreed
desktop/mobile sizes; the local iframe is a sizing proxy for Notion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
import json
import math
import os
from pathlib import Path
import re
import traceback
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import expect, sync_playwright


LABELS = {"simulation": "모의경매", "learn": "서류 연습", "process": "경매 절차", "home": "검토 요약", "rights": "권리 분석", "money": "투자금 계산", "area": "지역·시세", "notes": "최종 검토"}


def view_url(base, view):
    parts = urlsplit(base)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "view"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query + [("view", view)]), parts.fragment))


def go(surface, view):
    surface.locator(f'.nav-item[data-page="{view}"]').click()
    expect(surface.locator(".page-content")).to_have_attribute("data-view", view)


def money_krw(text):
    match = re.search(r"([−-]?[\d,]+(?:\.\d+)?)\s*(만원|원)", text)
    assert match, f"No rendered currency and unit: {text!r}"
    amount = Decimal(match.group(1).replace(",", "").replace("−", "-"))
    return amount * (10000 if match.group(2) == "만원" else 1)


def shown(surface, name, simulation=False):
    attr = "data-sim-result" if simulation else "data-result"
    locator = surface.locator(f'[{attr}="{name}"]').first
    expect(locator).to_be_visible()
    return money_krw(locator.inner_text())


def independent(values):
    """Decimal arithmetic independent of AuctionModel and AuctionFormat."""
    v = {key: Decimal(str(value)) for key, value in values.items()}
    tax = v["bid"] * v["acquisitionRate"] / 100
    interest = v["loan"] * v["loanRate"] / 100 * v["months"] / 12
    fixed = sum(v[key] for key in ("legal", "repairs", "eviction", "arrears", "assumed")) + interest
    costs = tax + fixed
    cash = v["bid"] + costs - v["loan"] + v["reserve"]
    deposit = v["minimum"] * v["depositRate"] / 100
    profit = v["sale"] * (1 - v["sellingRate"] / 100) - v["saleTax"] - v["bid"] - costs
    downside = v["downside"] * (1 - v["sellingRate"] / 100) - v["saleTax"] - v["bid"] - costs
    ceiling = (v["sale"] * (1 - v["sellingRate"] / 100) - v["saleTax"] - fixed - v["targetProfit"]) / (1 + v["acquisitionRate"] / 100)
    return {"cashGap": max(Decimal(0), cash - v["available"]), "depositGap": max(Decimal(0), deposit - v["available"]), "profit": profit, "downsideProfit": downside, "maxBid": ceiling}


def finance(surface, values):
    go(surface, "money")
    # Lower financing first, so a deliberately small bid can be entered safely.
    order = ["loan"] + [key for key in values if key != "loan"]
    for key in order:
        surface.locator(f'[data-finance="{key}"]').fill(str(values[key]))


def main_precision(page, context, args, artifacts):
    page.goto(view_url(args.url, "money"))
    values = page.evaluate("() => AuctionModel.defaults()")
    values.update({key: 0 for key in values})
    values.update(bid=100, minimum=100, depositRate=10, sale=99.999, downside=99.999, available=99.999)
    finance(page, values)
    expected = independent(values)
    assert expected["cashGap"] * 10000 == 10
    assert shown(page, "cashGap") == 10, "A real 10원 cash shortfall must not render 0만원"
    page.screenshot(path=str(artifacts / "main-ten-won-shortfall.png"))
    go(page, "notes")
    assert expected["profit"] * 10000 == -10
    assert shown(page, "profit") == -10
    assert shown(page, "downsideProfit") == -10
    for target in page.locator('[data-result="profit"], [data-result="downsideProfit"]').all():
        assert not re.search(r"[−-]\s*0(?:\.0+)?\s*(?:만원|원)", target.inner_text())
    page.screenshot(path=str(artifacts / "main-minus-ten-won.png"))
    values["available"] = Decimal("9.999")
    finance(page, values)
    assert independent(values)["depositGap"] * 10000 == 10
    assert shown(page, "depositGap") == 10, "Pre-loan deposit precision is independent of eventual cash needs"


def simulation_precision(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    scenario = page.evaluate("() => AuctionSimulationData.cases[0]")
    values = scenario["defaults"]
    result = independent(values)
    # Derive required net cash independently; the fixture is in 만원.
    v = {key: Decimal(str(value)) for key, value in values.items()}
    tax = v["bid"] * v["acquisitionRate"] / 100
    interest = v["loan"] * v["loanRate"] / 100 * v["months"] / 12
    cash = v["bid"] + tax + interest + sum(v[k] for k in ("legal", "repairs", "eviction", "arrears", "assumed")) - v["loan"] + v["reserve"]
    page.locator('.sim-stages [data-sim-go-stage="2"]').click()
    page.locator("#simulation-available").fill(str(cash - Decimal("0.001")))
    assert shown(page, "cashGap", True) == 10
    page.locator("#simulation-available").fill(str(v["minimum"] * v["depositRate"] / 100 - Decimal("0.001")))
    assert shown(page, "depositGap", True) == 10
    # Bid is the only editable price in the practice calculator. Solve its
    # break-even value independently and add exactly 10원 of expected loss.
    fixed = sum(v[k] for k in ("legal", "repairs", "eviction", "arrears", "assumed")) + interest
    revenue = v["sale"] * (1 - v["sellingRate"] / 100) - v["saleTax"]
    losing_bid = (revenue - fixed + Decimal("0.001")) / (1 + v["acquisitionRate"] / 100)
    page.locator("#simulation-bid").fill(str(losing_bid))
    assert shown(page, "profit", True) == -10
    page.screenshot(path=str(artifacts / "simulation-ten-won.png"))


def ceiling_copy(page, context, args, artifacts):
    page.goto(view_url(args.url, "money"))
    values = page.evaluate("() => AuctionModel.defaults()")
    values.update(saleTax=500, downside=34000, available=50000)
    finance(page, values)
    go(page, "notes")
    expected = independent(values)
    floor_bid = (expected["maxBid"] * 100).to_integral_value(rounding=ROUND_FLOOR) / 100
    copied_bid = shown(page, "maxBid") / 10000
    assert copied_bid == floor_bid == Decimal("29260.13"), (copied_bid, expected["maxBid"])
    assert copied_bid <= expected["maxBid"] < copied_bid + Decimal("0.01")
    # Copy the value visible to the user, not a hidden raw JS value.
    go(page, "money")
    page.locator('[data-finance="bid"]').fill(str(copied_bid))
    values["bid"] = copied_bid
    assert independent(values)["profit"] >= Decimal(str(values["targetProfit"]))
    go(page, "notes")
    reasons = page.locator(".reason-list").first.inner_text()
    assert not re.search(r"목표[^\n]*(?:미달|부족)", reasons), ("Displayed bid ceiling must not create a target-missed warning", reasons)
    page.screenshot(path=str(artifacts / "copied-ceiling-meets-target.png"))
    # One 100원 step above the displayed floor crosses the actual ceiling.
    go(page, "money")
    values["bid"] = copied_bid + Decimal("0.01")
    page.locator('[data-finance="bid"]').fill(str(values["bid"]))
    assert independent(values)["profit"] < Decimal(str(values["targetProfit"]))
    go(page, "notes")
    assert re.search(r"목표[^\n]*(?:미달|부족)", page.locator(".reason-list").first.inner_text()), "An actually missed target must still warn"
    page.screenshot(path=str(artifacts / "above-ceiling-warns.png"))


def background(locator):
    return locator.evaluate("""el => {const s=getComputedStyle(el),r=el.getBoundingClientRect();return {
      url:s.backgroundImage.match(/url\\([\"']?(.*?)[\"']?\\)/)?.[1],position:s.backgroundPosition,
      size:s.backgroundSize,ratio:r.width/r.height}}""")


def photo_cases(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    cases = page.evaluate("() => AuctionSimulationData.cases")
    exterior_tiles = []
    observed = []
    for scenario in cases:
        page.locator("#simulationCase").select_option(scenario["id"])
        photo_set = scenario["photoSet"]
        assert photo_set["fictional"] is True and photo_set["aiGenerated"] is True
        assert photo_set["buildingType"] == ("apartment" if scenario["id"] == "simulation-basic" else "multifamily")
        expected_url = page.evaluate("src => new URL(src,document.baseURI).href", photo_set["src"])
        preview = page.locator(".sim-photo-preview")
        initial_preview = background(preview)
        assert initial_preview["url"] == expected_url
        doc = next(item for item in scenario["documents"] if item["kind"] == "fieldnotes")
        page.locator(f'.sim-document-tabs [data-sim-document="{doc["id"]}"]').click()
        photos = page.locator(".sim-photo")
        assert photos.count() == len(scenario["observations"]) >= 4
        loaded = page.evaluate("""url => new Promise(resolve=>{const img=new Image();img.onload=()=>resolve({width:img.naturalWidth,height:img.naturalHeight});img.onerror=()=>resolve(null);img.src=url})""", expected_url)
        assert loaded and loaded["width"] > 500 and loaded["height"] > 500
        tile_ratio = loaded["width"] / photo_set["columns"] / (loaded["height"] / photo_set["rows"])
        assert math.isclose(tile_ratio, 4 / 3, abs_tol=0.01)
        expected_type = "아파트" if scenario["id"] == "simulation-basic" else "다세대"
        building_doc = next(item for item in scenario["documents"] if item["kind"] == "building")
        assert expected_type in json.dumps(building_doc, ensure_ascii=False), "Photo metadata must agree with the building dossier"
        for index, item in enumerate(scenario["observations"]):
            actual = background(photos.nth(index))
            assert actual["url"] == expected_url
            assert actual["size"] == f'{photo_set["columns"] * 100}% {photo_set["rows"] * 100}%'
            assert math.isclose(actual["ratio"], 4 / 3, abs_tol=0.01)
            expected_position = [float(value.rstrip("%")) for value in photo_set["positions"][item["photoKey"]].split()]
            actual_position = [float(value.rstrip("%")) for value in actual["position"].split()]
            assert all(abs(a - b) < 0.001 for a, b in zip(actual_position, expected_position))
            caption = page.locator(".sim-photos figure").nth(index).locator("figcaption").inner_text()
            assert "AI" in caption and "가상" in caption and ("실사진 아님" in caption or "실매물 사진 아님" in caption)
            if item["photoKey"] == "exterior":
                exterior_tiles.append((actual["url"], actual["position"]))
                photos.nth(index).screenshot(path=str(artifacts / f'{scenario["id"]}-exterior.png'))
        observed.append({"case": scenario["id"], "photoSet": photo_set, "loaded": loaded})
        page.screenshot(path=str(artifacts / f'{scenario["id"]}-photos.png'))
    assert len(set(exterior_tiles)) == 3, "Apartment and two distinct multifamily cases must not reuse the same exterior tile"
    (artifacts / "photo-evidence.json").write_text(json.dumps(observed, ensure_ascii=False, indent=2), encoding="utf-8")


def layout(surface, label):
    extent = surface.evaluate("""() => ({w:innerWidth,h:innerHeight,sw:document.documentElement.scrollWidth,
        sh:document.documentElement.scrollHeight,x:scrollX,y:scrollY})""")
    assert extent["sw"] <= extent["w"] + 1 and extent["sh"] <= extent["h"] + 1, (label, extent)
    assert extent["x"] == extent["y"] == 0, (label, extent)
    for selector in (".top-actions button", "#caseSelect", ".page-heading > button", ".page-heading h1"):
        for control in surface.locator(selector).all():
            if control.is_visible():
                rect = control.evaluate("el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}}")
                assert rect["left"] >= -1 and rect["right"] <= extent["w"] + 1, (label, "persistent control clipped horizontally", selector, rect)
                assert rect["top"] >= -1 and rect["bottom"] <= extent["h"] + 1, (label, "persistent control clipped vertically", selector, rect)
    # Check intrinsic text clipping, allowing intentional long-content scrolling.
    clipped = surface.locator(".nav-item,.page-content button,.page-heading h1").evaluate_all("""els=>els.filter(el=>el.getClientRects().length &&
      (el.scrollWidth>el.clientWidth+2||el.scrollHeight>el.clientHeight+2)).map(el=>({text:el.textContent.trim(),
      client:[el.clientWidth,el.clientHeight],scroll:[el.scrollWidth,el.scrollHeight]}))""")
    assert not clipped, (label, "button or heading text clipped", clipped)
    labels = {view: surface.locator(f'.nav-item[data-page="{view}"] > span').first.inner_text().strip() for view in LABELS}
    assert labels == LABELS, labels
    for locator in surface.locator(".page-content [data-sim-action],.page-content [data-study-action],.topbar [data-action]").all():
        if locator.is_visible():
            primary = locator.locator("strong")
            text = re.sub(r"\s+", "", primary.first.inner_text() if primary.count() else locator.inner_text())
            assert len(text) <= 16, ("Action label is still a sentence", text)


def visual_views(surface, page, artifacts):
    for view, title in LABELS.items():
        go(surface, view)
        expect(surface.locator("h1")).to_have_text(title)
        layout(surface, view)
        page.screenshot(path=str(artifacts / f"{view}.png"))
    go(surface, "simulation")
    for stage in (1, 2, 3):
        surface.locator(f'.sim-stages [data-sim-go-stage="{stage}"]').click()
        layout(surface, f"simulation stage {stage}")
        page.screenshot(path=str(artifacts / f"simulation-stage-{stage}.png"))


def visual(page, context, args, artifacts):
    page.goto(view_url(args.url, "simulation"))
    visual_views(page, page, artifacts)


def iframe_visual(page, context, args, artifacts):
    page.goto(args.url)
    page.set_content('<!doctype html><style>html,body{margin:0}iframe{display:block;border:0;width:900px;height:650px}</style><iframe title="local Notion size proxy"></iframe>')
    frame = page.locator("iframe").element_handle().content_frame()
    frame.goto(view_url(args.url, "simulation"))
    visual_views(frame, page, artifacts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("AUCTION_STUDY_URL", "http://127.0.0.1:8766/_auction/auction-study.html"))
    parser.add_argument("--executable", default=os.environ.get("BROWSER_EXECUTABLE"))
    parser.add_argument("--artifacts", type=Path, default=Path("/tmp/auction-polish-browser"))
    parser.add_argument("--only", nargs="+")
    args = parser.parse_args()
    scenarios = [("main-money-precision", main_precision, 1440, 900), ("simulation-money-precision", simulation_precision, 1440, 900), ("displayed-ceiling-copy", ceiling_copy, 1440, 900), ("case-photo-sets", photo_cases, 1440, 900), ("320x568", visual, 320, 568), ("375x667", visual, 375, 667), ("844x390", visual, 844, 390), ("900x650-iframe", iframe_visual, 1024, 768), ("1440x900", visual, 1440, 900)]
    if args.only:
        unknown = set(args.only) - {item[0] for item in scenarios}
        if unknown:
            parser.error(f"Unknown scenarios: {', '.join(sorted(unknown))}")
        scenarios = [item for item in scenarios if item[0] in args.only]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out = args.artifacts / stamp
    out.mkdir(parents=True, exist_ok=False)
    report = {"started": stamp, "url": args.url, "limitations": ["Building type is checked through case/asset metadata and manual visual inspection; the browser does not classify photographs.", "The local iframe is not actual Notion integration."], "results": []}
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
