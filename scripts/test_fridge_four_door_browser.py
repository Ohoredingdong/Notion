"""Exercise the four-door kitchen with isolated local data in real Chromium.

No personal sync calls or production writes. Artifacts are outside the checkout.
The fixed clock keeps expiry labels and screenshots reproducible.
"""
import argparse
import functools
import http.server
import json
import threading
import traceback
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


STATE = "use-me-first-state-v5"
VIEW = "use-me-first-kitchen-view-v1"
PANELS = ("fridge", "fridge-right", "freezer", "freezer-right")
ITEMS = [
    {"id": "egg", "name": "계란", "quantity": "2개", "expiry": "2026-10-23"},
    {"id": "milk", "name": "우유", "quantity": "500ml", "expiry": "2026-10-24"},
    {"id": "tofu", "name": "두부", "quantity": "150g", "expiry": "2026-10-26"},
    {"id": "onion", "name": "양파", "quantity": "1개", "expiry": "2026-11-01"},
]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def seed(page, items, view):
    inventory = {"version": 5, "revision": 7, "updatedAt": 1792728000000,
                 "items": items, "season": ["간장", "된장", "고추장", "식용유", "소금", "후추"],
                 "pantry": ["밥/즉석밥"], "customSeason": [], "customPantry": [],
                 "meals": [], "favorites": []}
    # An unconditional init script would reset data on reload and fake persistence.
    page.add_init_script("""(() => {
        if (sessionStorage.getItem('four-door-fixture')) return;
        const values = %s;
        for (const [key, value] of Object.entries(values)) localStorage.setItem(key, JSON.stringify(value));
        sessionStorage.setItem('four-door-fixture', 'loaded');
    })();""" % json.dumps({STATE: inventory, VIEW: view}, ensure_ascii=False))


def drag(page, source, target, touch):
    source.scroll_into_view_if_needed()
    source.evaluate("e => e.scrollIntoView({block:'center',behavior:'instant'})")
    start, end = source.bounding_box(), target.bounding_box()
    assert start and end, "Both the ingredient and destination must be rendered"
    x, y = start["x"] + start["width"] / 2, start["y"] + start["height"] / 2
    tx, ty = end["x"] + end["width"] * .72, end["y"] + end["height"] * .55
    if touch:
        session = page.context.new_cdp_session(page)
        try:
            session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y, "id": 1}]})
            height = page.viewport_size['height']
            if ty < 105 or ty > height - 80:
                edge = 35 if ty < 105 else height - 25
                session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": tx, "y": edge, "id": 1}]})
                page.wait_for_function("e => { const r=e.getBoundingClientRect();return r.y+r.height*.55>110 && r.y+r.height*.55<innerHeight-85; }", arg=target.element_handle())
                # Leave the edge before measuring: the application keeps scrolling
                # while a held finger remains there, just as on a physical screen.
                session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": tx, "y": height/2, "id": 1}]})
                end = target.bounding_box()
                tx, ty = end['x']+end['width']*.72, end['y']+end['height']*.55
                x, y = tx, height/2
            for step in range(1, 13):
                session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [
                    {"x": x + (tx - x) * step / 12, "y": y + (ty - y) * step / 12, "id": 1}]})
            session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        finally:
            session.detach()
    else:
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(tx, ty, steps=12)
        page.mouse.up()


def check_srcdoc(browser, root, output, passed):
    """Exercise the export in the iframe setting that broke detached markup."""
    html = (root / "use-me-first.html").read_text(encoding="utf-8")
    for allow_storage in (True, False):
        context = browser.new_context(viewport={"width": 931, "height": 900})
        try:
            page = context.new_page()
            errors, unexpected_requests = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            origin = "http://standalone-fridge.invalid/"
            sandbox = "allow-scripts allow-same-origin" if allow_storage else "allow-scripts"

            def route(request):
                if request.request.url == origin:
                    request.fulfill(content_type="text/html", body=
                                    '<iframe id="preview" sandbox="' + sandbox +
                                    '" style="width:390px;height:844px;border:0"></iframe>')
                else:
                    unexpected_requests.append(request.request.url)
                    request.abort()

            page.route("**/*", route)
            page.goto(origin)
            page.locator("#preview").evaluate("(node, html) => node.srcdoc = html", html)
            frame = page.frame_locator("#preview")
            expect(frame.locator(".fridge-door")).to_have_count(4)
            if allow_storage:
                frame.locator('.compartment-toggle[data-compartment="freezer-right"]').click()
                expect(frame.locator('.compartment-toggle[data-compartment="freezer-right"]')).to_have_attribute("aria-expanded", "true")
                frame.locator("#umfTopAdd").click()
                frame.locator("#name").fill("미리보기 확인 재료")
                frame.locator("#umfQty").fill("1개")
                frame.locator("#save").click()
                expect(frame.locator("#list")).to_contain_text("미리보기 확인 재료")
                frame.locator("body").evaluate("() => location.reload()")
                expect(frame.locator("#list")).to_contain_text("미리보기 확인 재료")
                expect(frame.locator('.compartment-toggle[data-compartment="freezer-right"]')).to_have_attribute("aria-expanded", "true")
                label = "srcdoc iframe opens a freezer, adds inventory and retains both after iframe reload"
            else:
                expect(frame.locator("#umfStorageStatus")).to_be_visible()
                expect(frame.locator("#umfStorageStatus")).to_contain_text("저장")
                label = "opaque srcdoc iframe renders the kitchen and honestly reports denied storage"
            assert not errors, errors
            assert not unexpected_requests, unexpected_requests
            page.locator("#preview").screenshot(path=str(output / ("iframe-storage.png" if allow_storage else "iframe-denied-storage.png")))
            passed(label)
        finally:
            context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("/tmp/fridge-four-door-browser"))
    parser.add_argument("--browser-executable")
    parser.add_argument("--widths", nargs="+", type=int, default=[1120, 390, 320])
    parser.add_argument("--standalone", action="store_true",
                        help="Require a self-contained export with no asset or external requests")
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(root):
        raise SystemExit("Use an artifact directory outside the checkout.")
    output.mkdir(parents=True, exist_ok=True)
    results = {"scope": "Local Chromium, fixed clock, synthetic storage; no production or personal sync",
               "standalone": args.standalone, "cases": [], "errors": []}

    def passed(name):
        results["cases"].append(name)
        print("PASS " + name, flush=True)

    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = "http://127.0.0.1:" + str(server.server_port)
    try:
        with sync_playwright() as playwright:
            launch = {"headless": True, "args": ["--no-sandbox"]}
            if args.browser_executable:
                launch["executable_path"] = args.browser_executable
            browser = playwright.chromium.launch(**launch)
            try:
                for width in args.widths:
                    context = browser.new_context(viewport={"width": width, "height": 844},
                                                  has_touch=width < 760, timezone_id="Asia/Seoul", reduced_motion="reduce")
                    page = context.new_page()
                    page.set_default_timeout(8000)
                    errors, external_writes, images, asset_requests = [], [], set(), []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("response", lambda response: images.add(Path(urlparse(response.url).path).name)
                            if response.ok and response.request.resource_type == "image" else None)

                    def route(request):
                        if request.request.resource_type != "document":
                            asset_requests.append(request.request.url)
                        if request.request.url.startswith(origin + "/"):
                            request.continue_()
                        else:
                            if request.request.method != "GET":
                                external_writes.append(urlparse(request.request.url).hostname)
                            request.abort()

                    page.route("**/*", route)
                    page.clock.set_fixed_time("2026-10-23T03:00:00Z")
                    legacy = {"version": 2, "doors": {"fridge": False, "freezer": False},
                              "placements": {"milk": "top"}, "positions": {"milk": {"x": .2, "y": .7, "z": 1}}}
                    seed(page, ITEMS, legacy)
                    try:
                        page.goto(origin + "/use-me-first.html", wait_until="networkidle")
                        page.wait_for_load_state("domcontentloaded")
                        page.evaluate("UMFKitchen.ready")
                        original = page.evaluate("localStorage.getItem(%s)" % json.dumps(STATE))
                        expect(page.locator(".fridge-door")).to_have_count(4)
                        expect(page.locator(".four-door .panel-fresh.fridge-door")).to_have_count(2)
                        expect(page.locator(".four-door .panel-frozen.fridge-door")).to_have_count(2)
                        expect(page.locator(".door-display")).to_have_count(2)
                        expect(page.locator("[data-door-expiry]")).to_contain_text("오늘")
                        expect(page.locator("[data-door-expiry]")).to_contain_text("내일")
                        expect(page.locator("[data-door-expiry]")).to_contain_text("150g")
                        passed(f"{width}px white four-door structure, two live displays and expiry quantities")
                        page.locator(".kitchen-scene").screenshot(path=str(output / f"fridge-{width}.png"))

                        for key in PANELS:
                            page.locator('.fridge-door[data-compartment="' + key + '"]').click()
                            for other in PANELS:
                                assert page.locator("#inside-" + other).evaluate("n => n.hasAttribute('inert')") == (other != key)
                            page.locator('.compartment-toggle[data-compartment="' + key + '"]').click()
                        passed(f"{width}px each upper and lower door opens and closes independently")

                        page.locator('.compartment-toggle[data-compartment="freezer-right"]').click()
                        page.reload(wait_until="networkidle")
                        expect(page.locator('.compartment-toggle[data-compartment="freezer-right"]')).to_have_attribute("aria-expanded", "true")
                        expect(page.locator('.compartment-toggle[data-compartment="freezer"]')).to_have_attribute("aria-expanded", "false")
                        assert page.evaluate("UMFKitchenState.getState().positions.milk") == legacy["positions"]["milk"]
                        passed(f"{width}px independent doors persist and legacy lot coordinates survive reload")

                        page.locator('[data-action="organize"]').click()
                        for zone in ("fridge-right-middle", "freezer-middle", "freezer-right-bottom"):
                            drag(page, page.locator('.fridge-food[data-lot="egg"]'), page.locator('.shelf-canvas[data-zone="' + zone + '"]'), width < 760)
                            try:
                                page.wait_for_function("zone => UMFKitchenState.zoneFor('egg') === zone", arg=zone)
                            except Exception as error:
                                actual = page.evaluate("UMFKitchenState.zoneFor('egg')")
                                raise AssertionError(f"Drag to {zone} left egg in {actual}") from error
                        saved = page.evaluate("UMFKitchenState.getState().positions.egg")
                        page.reload(wait_until="networkidle")
                        assert page.evaluate("UMFKitchenState.zoneFor('egg')") == "freezer-right-bottom"
                        assert page.evaluate("UMFKitchenState.getState().positions.egg") == saved
                        assert page.evaluate("localStorage.getItem(%s)" % json.dumps(STATE)) == original
                        passed(f"{width}px {'touch' if width < 760 else 'mouse'} drag across refrigerated and both frozen panels persists without inventory edits")

                        page.locator('.seasoning-rack').evaluate("node => node.scrollIntoView({block:'center',behavior:'instant'})")
                        seasoning = page.locator('.seasoning-mini[data-seasoning-name="간장"]')
                        drag(page, seasoning, page.locator(".seasoning-rack-items"), width < 760)
                        page.wait_for_function("JSON.parse(localStorage.getItem('umf-seasoning-layout-v3') || '{}')['간장']")
                        saved_seasoning = page.evaluate("localStorage.getItem('umf-seasoning-layout-v3')")
                        page.reload(wait_until="networkidle")
                        assert page.evaluate("localStorage.getItem('umf-seasoning-layout-v3')") == saved_seasoning
                        passed(f"{width}px Korean seasoning drag and position persist")

                        before_dates = page.evaluate("localStorage.getItem(%s)" % json.dumps(STATE))
                        before_view = page.evaluate("localStorage.getItem(%s)" % json.dumps(VIEW))
                        page.locator('.seasoning-rack').evaluate("node => node.scrollIntoView({block:'center',behavior:'instant'})")
                        seasoning.click()
                        expect(page.locator("#customExpiry")).to_be_visible()
                        expect(page.locator("#customName")).to_have_attribute("readonly", "")
                        page.locator("#customExpiry").fill("2026-10-22")
                        page.locator("#customCancel").click()
                        assert page.evaluate("localStorage.getItem(%s)" % json.dumps(STATE)) == before_dates
                        seasoning.click()
                        page.locator("#customExpiry").fill("2026-10-22")
                        page.locator("#customSave").click()
                        page.wait_for_function("UMFStore.getState().seasoningExpiry?.['간장'] === '2026-10-22'")
                        page.reload(wait_until="networkidle")
                        expect(seasoning).to_have_attribute("data-expiry-status", "expired")
                        assert page.evaluate("UMFRecipes.getRanked().find(x => x.recipe.name==='계란 볶음밥').missing.some(x => x.name==='간장' && x.reason==='expired')")
                        page.evaluate("UMFRecipes.select('계란 볶음밥')")
                        expect(page.locator("#umfSelectionChips")).to_contain_text("간장 · 기한 경과")
                        assert page.evaluate("localStorage.getItem('use-me-first-before-seasoning-expiry-v1')") == before_dates
                        assert page.evaluate("localStorage.getItem(%s)" % json.dumps(VIEW)) == before_view
                        assert page.evaluate("localStorage.getItem('umf-seasoning-layout-v3')") == saved_seasoning
                        passed(f"{width}px seasoning expiry editing and cancel, reload, recipe exclusion and original-data backup")

                        page.locator('.seasoning-rack').evaluate("node => node.scrollIntoView({block:'center',behavior:'instant'})")
                        seasoning.click()
                        page.locator("#customExpiry").fill("1899-12-31")
                        invalid_before = page.evaluate("localStorage.getItem(%s)" % json.dumps(STATE))
                        page.locator("#customSave").click()
                        expect(page.locator("#umfCustomError")).to_be_visible()
                        assert page.evaluate("localStorage.getItem(%s)" % json.dumps(STATE)) == invalid_before
                        page.locator("#customExpiry").fill("")
                        page.locator("#customSave").click()
                        expect(seasoning).to_have_attribute("data-expiry-status", "unknown")
                        assert page.evaluate("UMFStore.getState().season.includes('간장')")
                        assert page.evaluate("UMFRecipes.getRanked().find(x => x.recipe.name==='계란 볶음밥').available")
                        passed(f"{width}px invalid date does not write and clearing a date retains seasoning ownership")

                        page.locator('[data-action="add-seasoning"]').first.click()
                        page.locator("#customName").fill("유자청")
                        page.locator("#customExpiry").fill("2026-11-01")
                        page.locator("#customSave").click()
                        page.wait_for_function("UMFStore.getState().seasoningExpiry?.['유자청'] === '2026-11-01'")
                        expect(page.locator('.seasoning-mini[data-seasoning-name="유자청"] [data-seasoning-art="jar"]')).to_be_visible()
                        page.locator("#seasonTab").click()
                        expect(page.locator('.umf-season-expiry[data-seasoning-name="간장"]')).to_be_visible()
                        page.locator("#addPantry").click()
                        expect(page.locator("#customExpiryField")).to_be_hidden()
                        page.locator("#customCancel").click()
                        passed(f"{width}px dated custom seasoning, visible grid editor and unchanged pantry entry")

                        page.locator('.nav-btn[data-kitchen-page="recipes"]').click()
                        rice = page.locator('.umf-menu-card[data-name="계란 볶음밥"]')
                        expect(rice.locator('.umf-recipe-board [data-miniature="egg-rice"]')).to_be_visible()
                        rice.locator(".umf-menu-select").click()
                        expect(page.locator("#umfRecipeDetail")).to_be_visible()
                        expect(page.locator("#umfRecipeDetail")).to_contain_text("만드는 순서")
                        rice.locator(".umf-fav").click()
                        page.wait_for_function("UMFStore.getState().favorites.includes('계란 볶음밥')")
                        page.locator("#umfLogBtn").click()
                        expect(page.locator("#umfDiaryPage")).to_be_visible()
                        expect(page.locator("#umfMealList")).to_contain_text("계란 볶음밥")
                        page.reload(wait_until="networkidle")
                        assert page.evaluate("UMFStore.getState().items") == ITEMS
                        assert page.evaluate("UMFStore.getState().favorites.includes('계란 볶음밥')")
                        assert page.evaluate("UMFStore.getState().meals.length") == 1
                        passed(f"{width}px miniature recipe selection, instructions, favorite and meal record retain existing storage")

                        page.locator('.nav-btn[data-kitchen-page="recipes"]').click()
                        page.locator("#umfRecipeSearch").fill("없는메뉴")
                        expect(page.locator("#umfRecipeEmpty")).to_be_visible()
                        expect(page.locator("#umfLogBtn")).to_be_disabled()
                        page.locator("#umfRecipeSearch").fill("")
                        dimensions = page.evaluate("({viewport:innerWidth, scroll:document.documentElement.scrollWidth})")
                        assert dimensions["scroll"] <= dimensions["viewport"] + 1, dimensions
                        assert not errors, errors
                        assert not external_writes, external_writes
                        if args.standalone:
                            assert not asset_requests, "Standalone preview requested other files: " + repr(asset_requests)
                            sizes = page.evaluate(r"""async () => {
                                const atlas = document.querySelector('svg.miniature-art image').getAttribute('href');
                                const background = getComputedStyle(document.querySelector('.kitchen-scene')).backgroundImage;
                                const scene = background.match(/url\("([^"]+)"\)/)?.[1];
                                if (!scene) throw Error('Kitchen scene background is missing');
                                return Promise.all([atlas, scene, UMFKitchenArt.seasoningAsset].map(async src => {
                                    if (!src.startsWith('data:image/')) throw Error('Image was not embedded');
                                    const image = new Image(); image.src = src; await image.decode();
                                    return image.naturalWidth;
                                }));
                            }""")
                            assert sizes[0] == 1254 and sizes[1] > 0 and sizes[2] == 1448, sizes
                        else:
                            assert {"food-miniatures-v2.webp", "kitchen-scene.webp", "seasoning-miniatures-v1.png"} <= images, images
                        page.screenshot(path=str(output / f"recipes-{width}.png"), full_page=True)
                        passed(f"{width}px search/empty state, layout, miniature assets and no runtime errors or external writes")
                    except Exception as error:
                        results["errors"].append(f"{width}px: {type(error).__name__}: {error}")
                        traceback.print_exc()
                        page.screenshot(path=str(output / f"failure-{width}.png"), full_page=True)
                    finally:
                        context.close()
                if args.standalone:
                    try:
                        check_srcdoc(browser, root, output, passed)
                    except Exception as error:
                        results["errors"].append(f"srcdoc: {type(error).__name__}: {error}")
                        traceback.print_exc()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    results["passed"] = not results["errors"]
    results["passed_cases"] = len(results["cases"])
    (output / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
