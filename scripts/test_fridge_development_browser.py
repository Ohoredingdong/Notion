"""Real browser checks for kitchen organizing controls and durable inventory.

Fixtures live in isolated browser contexts only; no sync credentials or live
personal records are used. An iframe is a Notion-like proxy, not a Notion test.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import expect, sync_playwright

STATE = "use-me-first-state-v5"
VIEW = "use-me-first-kitchen-view-v1"


def fixtures():
    return {
        STATE: {
            "version": 5, "revision": 7, "updatedAt": int(time.time() * 1000),
            "items": [
                {"id": "browser-test-buried", "name": "계란", "quantity": "2개", "expiry": "2099-01-01"},
                {"id": "browser-test-front", "name": "계란", "quantity": "7개", "expiry": "2099-01-01"},
            ],
            "season": [], "pantry": [], "customSeason": [], "customPantry": [],
            "meals": [], "favorites": [],
        },
        VIEW: {
            "version": 2, "doors": {"freezer": True, "fridge": True}, "placements": {},
            "positions": {
                "browser-test-buried": {"x": .4, "y": .6, "z": 1},
                "browser-test-front": {"x": .4, "y": .6, "z": 2},
            },
        },
    }


def snapshot(target):
    return target.evaluate("keys => Object.fromEntries(keys.map(k => [k, localStorage.getItem(k)]))", [STATE, VIEW])


def select_through_inventory(target):
    # The buried tile deliberately cannot be clicked through the foreground lot.
    target.locator('#umfKitchenScene [data-action="navigate"][data-page="inventory"]').click()
    target.locator('#list .row[data-id="browser-test-buried"] [data-kitchen-arrange]').click()
    expect(target.locator('.kitchen-layer-controls')).to_be_visible()


def check_layers(target, original_inventory):
    front = target.locator('#umfKitchenScene [data-action="layer-front"]')
    back = target.locator('#umfKitchenScene [data-action="layer-back"]')
    expect(front).to_be_enabled()
    expect(back).to_be_enabled()
    # Normal clicks exercise pointer hit testing; force clicks would hide the
    # banner's old pointer-events:none problem.
    front.click()
    target.wait_for_function("""key => {
        const p=JSON.parse(localStorage.getItem(key)).positions;
        return p['browser-test-buried'].z>p['browser-test-front'].z;
    }""", arg=VIEW)
    after_front = snapshot(target)
    assert after_front[STATE] == original_inventory, "Layering must not rewrite inventory, quantities or IDs"
    front_positions = json.loads(after_front[VIEW])["positions"]
    for value in front_positions.values():
        assert value["x"] == .4 and value["y"] == .6, "Layer changes must preserve the saved coordinates"
    back.click()
    target.wait_for_function("""key => {
        const p=JSON.parse(localStorage.getItem(key)).positions;
        return p['browser-test-buried'].z<p['browser-test-front'].z;
    }""", arg=VIEW)
    saved = snapshot(target)
    assert saved[STATE] == original_inventory
    for value in json.loads(saved[VIEW])["positions"].values():
        assert value["x"] == .4 and value["y"] == .6
    return saved


def scenario(browser, entry_url, name, width, height, embedded, artifacts):
    context = browser.new_context(viewport={"width": width, "height": height})
    fixture = fixtures()
    context.add_init_script("""(() => {
        const fixture = """ + json.dumps(fixture, ensure_ascii=False) + """;
        try {
            for (const [key,value] of Object.entries(fixture)) {
                if (localStorage.getItem(key) === null) localStorage.setItem(key, JSON.stringify(value));
            }
        } catch (_) { /* about:blank cannot access origin storage; the iframe can. */ }
    })();""")
    page = context.new_page()
    page.set_default_timeout(12000)
    errors = []
    context.on("page", lambda p: p.on("pageerror", lambda error: errors.append(str(error))))
    page.on("pageerror", lambda error: errors.append(str(error)))
    result = {"name": name, "viewport": {"width": width, "height": height},
              "mode": "iframe proxy" if embedded else "direct", "passed": False}
    try:
        if embedded:
            # Fixed-size iframe presents the same origin/app inside a smaller
            # document, as an embedded Notion widget would be presented.
            response = page.goto(entry_url, wait_until="domcontentloaded")
            assert response and response.status == 200
            page.set_content('<main style="padding:16px"><iframe title="Kitchen widget embed" '
                             'style="width:900px;height:650px;border:1px solid #ddd"></iframe></main>')
            # Navigate through Playwright's frame handle. Reading the remote
            # frame's Location from about:blank would violate the browser's
            # same-origin policy and manufacture a harness error.
            target = page.locator("iframe").element_handle().content_frame()
            response = target.goto(entry_url, wait_until="domcontentloaded")
            assert response and response.status == 200
        else:
            response = page.goto(entry_url, wait_until="domcontentloaded")
            assert response and response.status == 200
            target = page
        target.locator('#umfKitchenScene .fridge-food').first.wait_for(state="visible")
        original_inventory = snapshot(target)[STATE]
        assert len(json.loads(original_inventory)["items"]) == 2
        target.locator('#umfKitchenScene [data-action="organize"]').click()
        expect(target.locator('.kitchen-layer-controls')).not_to_be_visible()
        select_through_inventory(target)
        saved = check_layers(target, original_inventory)
        target.goto(entry_url, wait_until="domcontentloaded")
        target.locator('#umfKitchenScene .fridge-food').first.wait_for(state="visible")
        assert snapshot(target) == saved, "Reload must retain exact view preferences and original stock bytes"
        select_through_inventory(target)
        for item_id, quantity in [("browser-test-buried", "2개"), ("browser-test-front", "7개")]:
            expect(target.locator(f'.fridge-food[data-lot="{item_id}"] .quantity-mini')).to_have_text(quantity)
        front = target.locator('[data-action="layer-front"]')
        front.scroll_into_view_if_needed()
        # The restored toolbar must stay within its original scene rather than
        # covering inventory or being clipped outside the scene's overflow box.
        geometry = front.evaluate("""el => {
            const b=el.getBoundingClientRect(),s=el.closest('.kitchen-scene').getBoundingClientRect();
            return {inside:b.left>=s.left && b.right<=s.right && b.top>=s.top && b.bottom<=s.bottom,
                    width:b.width,height:b.height};
        }""")
        assert geometry["inside"] and geometry["width"] >= 40 and geometry["height"] >= 40, geometry
        assert not errors, errors
        target.locator('#umfKitchenScene').evaluate("el => el.scrollIntoView({block:'start'})")
        screenshot = artifacts / f"fridge-{name}.png"
        page.screenshot(path=str(screenshot), full_page=False)
        scene_screenshot = artifacts / f"fridge-{name}-scene.png"
        target.locator('#umfKitchenScene').screenshot(path=str(scene_screenshot))
        result.update({"passed": True, "checks": ["visible current controls", "normal click front/back",
                       "buried lot reachable through inventory", "saved ID/quantity/coordinates preserved",
                       "reload preserves original records", "controls stay inside scene", "no page errors"],
                       "screenshot": str(screenshot), "scene_screenshot": str(scene_screenshot),
                       "page_errors": errors, "control_geometry": geometry})
    except Exception as error:
        result["error"] = str(error)
        result["page_errors"] = errors
        page.screenshot(path=str(artifacts / f"fridge-{name}-failure.png"), full_page=False)
    finally:
        context.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8766/")
    parser.add_argument("--artifacts", type=Path, default=Path("/tmp/fridge-development"))
    parser.add_argument("--executable", help="System browser path; omitted uses Playwright's installed bundle")
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        parser.error("--base-url must be an HTTP(S) site root")
    args.artifacts.mkdir(parents=True, exist_ok=True)
    url = urljoin(args.base_url.rstrip("/") + "/", "use-me-first.html")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "url": url,
              "browser": args.executable or "Playwright bundle", "fixture": "isolated explicitly seeded test lots",
              "not_verified": ["actual Notion UI", "remote sync", "real user records", "public deployment"], "results": []}
    try:
        with sync_playwright() as p:
            options = {"headless": True}
            if args.executable:
                options["executable_path"] = args.executable
            browser = p.chromium.launch(**options)
            for case in [("desktop", 1366, 900, False), ("mobile", 390, 844, False), ("iframe", 1200, 900, True)]:
                result = scenario(browser, url, *case, args.artifacts)
                report["results"].append(result)
                print(("PASS" if result["passed"] else "FAIL") + " fridge " + result["name"], flush=True)
            browser.close()
    except Exception as error:
        report["setup_error"] = str(error)
    report["passed"] = len(report["results"]) == 3 and all(r["passed"] for r in report["results"])
    (args.artifacts / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FRIDGE_DEVELOPMENT_BROWSER: " + ("PASS" if report["passed"] else "FAIL"), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
