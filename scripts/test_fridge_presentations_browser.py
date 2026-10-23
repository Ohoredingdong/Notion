#!/usr/bin/env python3
"""Check feature parity between the app and the small widget at real viewport sizes."""
import argparse
import functools
import http.server
import json
from pathlib import Path
import threading
import traceback

from playwright.sync_api import expect, sync_playwright
from test_fridge_four_door_browser import QuietHandler, STATE, VIEW, ITEMS, PANELS, seed, drag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-executable', default='/usr/bin/chromium')
    parser.add_argument('--standalone', action='store_true')
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(root):
        raise SystemExit('Keep runtime artifacts outside the checkout.')
    output.mkdir(parents=True, exist_ok=True)
    result = {'standalone': args.standalone, 'scope': 'Local Chromium and synthetic storage; external writes blocked', 'cases': [], 'errors': []}

    def passed(name):
        result['cases'].append(name)
        print('PASS ' + name, flush=True)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser_executable, args=['--no-sandbox'])
            try:
                for width, height in [(320, 480), (390, 640), (640, 480)]:
                    context = browser.new_context(viewport={'width': width, 'height': height}, has_touch=True,
                                                  reduced_motion='reduce', timezone_id='Asia/Seoul')
                    page = context.new_page(); page.set_default_timeout(10000)
                    errors, assets, external_writes = [], [], []
                    page.on('pageerror', lambda e: errors.append(str(e)))

                    def route(r):
                        if r.request.resource_type != 'document':
                            assets.append(r.request.url)
                        if r.request.url.startswith(origin + '/'):
                            r.continue_()
                        else:
                            if r.request.method != 'GET':
                                external_writes.append(r.request.url)
                            r.abort()

                    page.route('**/*', route)
                    page.clock.set_fixed_time('2026-10-23T03:00:00Z')
                    seed(page, ITEMS, {'version': 2, 'doors': {'fridge': False, 'freezer': False}, 'placements': {}, 'positions': {}})
                    try:
                        page.goto(origin + '/use-me-first-widget.html', wait_until='networkidle')
                        page.wait_for_load_state('domcontentloaded')
                        page.evaluate('UMFKitchen.ready')
                        original = page.evaluate('localStorage.getItem(%s)' % json.dumps(STATE))
                        expect(page.locator('body')).to_have_attribute('data-kitchen-mode', 'widget')
                        expect(page.locator('.fridge-door')).to_have_count(4)
                        expect(page.locator('.door-display')).to_have_count(2)
                        assert page.locator('.kitchen-scene').bounding_box()['height'] < 500
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        assert page.evaluate('localStorage.getItem(%s)' % json.dumps(STATE)) == original
                        page.screenshot(path=str(output / f'widget-{width}.png'), full_page=True)
                        passed(f'{width}x{height} compact entry, same four doors and two displays, no horizontal overflow or inventory edits')

                        for key in PANELS:
                            control = page.locator('.compartment-toggle[data-compartment="' + key + '"]')
                            control.click(); expect(control).to_have_attribute('aria-expanded', 'true')
                            control.click(); expect(control).to_have_attribute('aria-expanded', 'false')
                        page.locator('[data-action="organize"]').click()
                        for zone in ['fridge-right-middle', 'freezer-right-bottom']:
                            drag(page, page.locator('.fridge-food[data-lot="egg"]'), page.locator('.shelf-canvas[data-zone="' + zone + '"]'), True)
                            page.wait_for_function("zone => UMFKitchenState.zoneFor('egg') === zone", arg=zone)
                        positions = page.evaluate('localStorage.getItem(%s)' % json.dumps(VIEW))
                        page.reload(wait_until='networkidle')
                        assert page.evaluate('localStorage.getItem(%s)' % json.dumps(VIEW)) == positions
                        assert page.evaluate('localStorage.getItem(%s)' % json.dumps(STATE)) == original
                        passed(f'{width}px independent doors and real touch drag into right refrigerator and freezer retain coordinates')

                        page.locator('[data-kitchen-widget-section="seasoning"]').click()
                        expect(page.locator('.seasoning-rack')).to_be_visible()
                        page.locator('.seasoning-mini[data-seasoning-name="간장"]').click()
                        page.locator('#customExpiry').fill('2026-10-24'); page.locator('#customSave').click()
                        page.wait_for_function("UMFStore.getState().seasoningExpiry?.['간장'] === '2026-10-24'")
                        page.screenshot(path=str(output / f'seasoning-{width}.png'), full_page=True)
                        raw = page.evaluate('localStorage.getItem(%s)' % json.dumps(STATE))
                        page.locator('[data-kitchen-mode-switch]').click()
                        expect(page.locator('body')).to_have_attribute('data-kitchen-mode', 'app')
                        page.reload(wait_until='networkidle')
                        expect(page.locator('body')).to_have_attribute('data-kitchen-mode', 'app')
                        page.goto(origin + '/use-me-first.html', wait_until='networkidle')
                        expect(page.locator('body')).to_have_attribute('data-kitchen-mode', 'app')
                        assert page.evaluate('localStorage.getItem(%s)' % json.dumps(STATE)) == raw
                        assert page.evaluate('localStorage.getItem(%s)' % json.dumps(VIEW)) == positions
                        page.locator('[data-kitchen-mode-switch]').click(); page.reload(wait_until='networkidle')
                        expect(page.locator('body')).to_have_attribute('data-kitchen-mode', 'widget')
                        assert page.evaluate('localStorage.getItem(%s)' % json.dumps(STATE)) == raw
                        passed(f'{width}px seasoning expiry, app/widget URL switches and reload share the exact same durable records')

                        page.locator('.nav-btn[data-kitchen-page="recipes"]').click()
                        rice = page.locator('.umf-menu-card[data-name="계란 볶음밥"]')
                        rice.locator('.umf-menu-select').click()
                        expect(page.locator('#umfRecipeDetail')).to_contain_text('만드는 순서')
                        rice.locator('.umf-fav').click()
                        page.locator('#umfLogBtn').click()
                        expect(page.locator('#umfDiaryPage')).to_be_visible()
                        expect(page.locator('#umfMealList')).to_contain_text('계란 볶음밥')
                        page.reload(wait_until='networkidle')
                        assert page.evaluate("UMFStore.getState().favorites.includes('계란 볶음밥')")
                        assert page.evaluate('UMFStore.getState().meals.length') == 1
                        passed(f'{width}px identical recipe instructions, favorites and persistent meal diary in the widget')

                        page.locator('.nav-btn[data-kitchen-page="recipes"]').click()
                        page.locator('#umfExpandRecipes').click()
                        page.locator('.umf-menu-card[data-name="토마토 치즈 오믈렛"] .umf-menu-select').click()
                        page.locator('.nav-btn[data-kitchen-page="shopping"]').click()
                        page.locator('.missing-add[data-name="토마토"]').click()
                        expect(page.locator('#name')).to_have_value('토마토')
                        page.locator('#umfQty').fill('1개'); page.locator('#expiry').fill('2026-11-01'); page.locator('#save').click()
                        page.wait_for_function("UMFStore.getState().items.some(x => x.name === '토마토')")
                        passed(f'{width}px widget shopping opens the original stock form and saves quantity and expiry')

                        page.locator('.nav-btn[data-kitchen-page="home"]').click()
                        page.locator('[data-kitchen-widget-section="inventory"]').click()
                        expect(page.locator('#umfKitchenInventory')).to_be_visible()
                        expect(page.locator('#list')).to_contain_text('토마토')
                        page.locator('#seasonTab').click()
                        page.locator('.umf-season-expiry[data-seasoning-name="간장"]').click()
                        expect(page.locator('#customExpiry')).to_have_value('2026-10-24')
                        page.locator('#customCancel').click()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        assert not errors, errors
                        assert not external_writes, external_writes
                        if args.standalone:
                            assert not assets, assets
                        passed(f'{width}px stock list and seasoning date editor remain available, with no runtime errors or external writes')
                    except Exception as error:
                        result['errors'].append(f'{width}px: {type(error).__name__}: {error}')
                        traceback.print_exc()
                        page.screenshot(path=str(output / f'failure-{width}.png'), full_page=True)
                    finally:
                        context.close()

                context = browser.new_context(viewport={'width': 800, 'height': 700})
                try:
                    page = context.new_page()
                    page.route('**/*', lambda r: r.fulfill(content_type='text/html', body=
                               '<iframe title="냉장고 위젯" src="use-me-first-widget.html" style="width:320px;height:480px;border:0"></iframe>')
                               if r.request.url == origin + '/parent' else r.continue_() if r.request.url.startswith(origin + '/') else r.abort())
                    page.goto(origin + '/parent', wait_until='networkidle')
                    frame = page.frame_locator('iframe')
                    expect(frame.locator('body')).to_have_attribute('data-kitchen-mode', 'widget')
                    frame.locator('[data-kitchen-widget-add]').click()
                    frame.locator('#name').fill('위젯 확인 재료'); frame.locator('#save').click()
                    expect(frame.locator('#mb')).not_to_have_class('modalbg on')
                    frame.locator('.nav-btn[data-kitchen-page="recipes"]').click()
                    expect(frame.locator('#umfRecipesPage')).to_be_visible()
                    passed('320x480 iframe loads the widget entry and keeps inventory forms and recipe navigation usable')
                except Exception as error:
                    result['errors'].append(f'iframe: {type(error).__name__}: {error}'); traceback.print_exc()
                finally:
                    context.close()
            finally:
                browser.close()
    finally:
        server.shutdown(); server.server_close()
    result['passed'] = not result['errors']; result['passed_cases'] = len(result['cases'])
    (output / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
