#!/usr/bin/env python3
"""Exercise shared life features in app/widget without external services or real data."""
import argparse
import base64
import functools
import http.server
import json
from pathlib import Path
import threading
import traceback

from playwright.sync_api import expect, sync_playwright
from test_fridge_four_door_browser import QuietHandler, STATE, VIEW, ITEMS, PANELS, seed

LIFE = 'use-me-first-life-v1'
PHOTO = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j3ioAAAAASUVORK5CYII=')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-executable', default='/usr/bin/chromium')
    parser.add_argument('--standalone', action='store_true')
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(root):
        raise SystemExit('Runtime output must be outside the checkout.')
    output.mkdir(parents=True, exist_ok=True)
    result = {'standalone': args.standalone, 'cases': [], 'errors': [], 'scope': 'Local Chromium; synthetic data; external requests blocked'}

    def passed(name):
        print('PASS ' + name, flush=True)
        result['cases'].append(name)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser_executable, args=['--no-sandbox'])
            for mode in ['app', 'widget']:
                for width in [1120 if mode == 'app' else 640, 390, 320]:
                    context = browser.new_context(viewport={'width': width, 'height': 1000 if width > 640 else 760}, has_touch=True, reduced_motion='reduce', timezone_id='Asia/Seoul')
                    page = context.new_page()
                    page.set_default_timeout(10000)
                    errors, external, assets = [], [], []
                    page.on('pageerror', lambda e: errors.append(str(e)))

                    def route(r):
                        if r.request.resource_type != 'document':
                            assets.append(r.request.url)
                        if r.request.url.startswith(origin + '/'):
                            r.continue_()
                        else:
                            external.append(r.request.url)
                            r.abort()

                    page.route('**/*', route)
                    page.clock.set_fixed_time('2026-10-23T03:00:00Z')
                    seed(page, ITEMS, {'version': 2, 'doors': {'fridge': False, 'freezer': False}, 'panels': {k: False for k in PANELS}, 'placements': {}, 'positions': {}})
                    entry = 'use-me-first-widget.html' if mode == 'widget' else 'use-me-first.html'
                    label = f'{mode}-{width}'

                    def go(view):
                        page.locator(f'.life-tools [data-kitchen-page="{view}"]').click()
                        expect(page.locator(f'[data-kitchen-view="{view}"]')).to_be_visible()

                    def fill(form, values):
                        for key, value in values.items():
                            page.locator(f'#{form} [name="{key}"]').fill(value)

                    def submit(form):
                        page.locator(f'#{form} [type="submit"]').click()

                    def stored(key):
                        return page.evaluate('(k) => localStorage.getItem(k)', key)

                    try:
                        page.goto(origin + '/' + entry, wait_until='networkidle')
                        page.wait_for_load_state('domcontentloaded')
                        page.wait_for_function('window.UMFKitchen && window.UMFLifeStore')
                        inventory, view = stored(STATE), stored(VIEW)
                        assert stored(LIFE) is None
                        page.screenshot(path=str(output / f'after-{label}.png'), full_page=True)
                        for section in ['photos','garden','budget','nutrition','monthly']:
                            go(section)
                            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), section
                        assert stored(STATE) == inventory and stored(VIEW) == view and stored(LIFE) is None
                        if args.standalone:
                            assert not assets, 'Standalone export must not load relative assets'
                            assert not external
                        passed(f'{label}: five new screens fit, empty reads preserve every original byte and do not create life data')
                        if width != 390:
                            assert not errors, errors
                            continue

                        go('nutrition')
                        expect(page.locator('#lifeNutrients')).to_contain_text('미설정')
                        assert page.locator('#lifeNutrients strong').all_text_contents() == ['—'] * 4
                        go('garden')
                        page.locator('#lifeGoalForm select').select_option('meal'); submit('lifeGoalForm')
                        page.locator('#lifeClaimButton').click()
                        expect(page.locator('#lifeStatus')).to_contain_text('먼저 오늘의 식사')
                        assert page.evaluate('UMFLifeStore.getState().claims.length') == 0
                        page.locator('#lifeGoalForm select').select_option('care'); submit('lifeGoalForm')
                        page.locator('#lifeClaimButton').click()
                        expect(page.locator('#lifeClaimButton')).to_be_disabled()
                        page.locator('[data-life-theme="sage"]').click()
                        expect(page.locator('body')).to_have_attribute('data-life-theme','sage')
                        assert page.evaluate('UMFLifeStore.getState().claims.length') == 1
                        page.reload(wait_until='networkidle')
                        expect(page.locator('#lifeClaimButton')).to_be_disabled()
                        assert page.evaluate('UMFLifeStore.getState().claims.length') == 1
                        page.screenshot(path=str(output / f'garden-{label}.png'), full_page=True)
                        passed(f'{label}: daily rewards require the chosen action, cannot repeat, unlock a decoration and persist')

                        go('budget')
                        fill('lifeBudgetForm', {'budget':'200000'}); submit('lifeBudgetForm')
                        fill('lifeExpenseForm', {'name':'주말 장보기','amount':'23000'}); submit('lifeExpenseForm')
                        expect(page.locator('#lifeBudgetSummary')).to_contain_text('177,000원')
                        page.once('dialog', lambda d: d.accept())
                        page.locator('[data-life-delete="expenses"]').click()
                        expect(page.locator('#lifeExpenses')).to_contain_text('아직 기록')
                        page.locator('#lifeUndo').click()
                        expect(page.locator('#lifeExpenses')).to_contain_text('23,000원')
                        passed(f'{label}: actual spending, remaining budget, deletion and undo use durable records')

                        go('nutrition')
                        fill('lifeNutritionForm', {'name':'확인한 도시락','kcal':'500','carb':'50','protein':'30','fat':'20'}); submit('lifeNutritionForm')
                        fill('lifeNutritionForm', {'name':'열량만 확인','kcal':'200'}); submit('lifeNutritionForm')
                        expect(page.locator('#lifeNutrients')).to_contain_text('700 kcal')
                        expect(page.locator('#lifeNutrients')).to_contain_text('입력 1/2건')
                        fill('lifeNutritionForm', {'name':'미확인 기록'}); submit('lifeNutritionForm')
                        expect(page.locator('#lifeStatus')).to_contain_text('입력값을 확인')
                        assert page.evaluate('UMFLifeStore.getState().nutrition.length') == 2
                        fill('lifeTargetsForm', {'kcal':'2100'}); submit('lifeTargetsForm')
                        fill('lifeSupplementForm', {'name':'비타민 D','amount':'제품 표시 확인'}); submit('lifeSupplementForm')
                        page.locator('[data-supplement]').click()
                        expect(page.locator('[data-supplement]')).to_have_attribute('aria-pressed','true')
                        page.locator('[data-supplement]').click()
                        expect(page.locator('[data-supplement]')).to_have_attribute('aria-pressed','false')
                        assert page.evaluate('UMFLifeStore.getState().supplements[0].days.length') == 0
                        page.locator('[data-supplement]').click()
                        expect(page.locator('[data-supplement]')).to_have_attribute('aria-pressed','true')
                        page.screenshot(path=str(output / f'nutrition-{label}.png'), full_page=True)
                        passed(f'{label}: manual nutrients retain unknowns, personal targets remain explicit and supplement checks are reversible')

                        go('monthly')
                        expect(page.locator('#lifeRatio')).to_contain_text('40%')
                        expect(page.locator('#lifeRatio')).to_contain_text('24%')
                        expect(page.locator('#lifeRatio')).to_contain_text('36%')
                        expect(page.locator('#lifeMonthNotes')).to_contain_text('2건 중 1건')
                        page.locator('#lifeMonth').fill('2026-09')
                        expect(page.locator('#lifeRatio')).to_contain_text('아직 비율')
                        page.locator('#lifeMonth').fill('2026-10')
                        with page.expect_download() as download:
                            page.locator('#lifeExport').click()
                        backup = json.loads(download.value.path().read_text())
                        assert backup['budget'] == 200000 and len(backup['nutrition']) == 2
                        page.screenshot(path=str(output / f'monthly-{label}.png'), full_page=True)
                        assert stored(STATE) == inventory and stored(VIEW) == view
                        passed(f'{label}: complete-row-only monthly energy ratios, month filters and JSON export leave inventory and positions unchanged')

                        go('photos')
                        for key in ['product','expiry']:
                            page.locator(f'[data-life-photo="{key}"]').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':PHOTO})
                            expect(page.locator(f'[data-life-photo-preview="{key}"]')).to_be_visible()
                        expect(page.locator('.life-connection')).to_contain_text('아직 연결되지')
                        assert stored(STATE) == inventory
                        assert not any('blob:' in value for value in json.loads(page.evaluate('JSON.stringify(localStorage)')).values())
                        fill('lifePhotoForm', {'name':'사진 확인 두부'}); submit('lifePhotoForm')
                        expect(page.locator('#name')).to_have_value('사진 확인 두부')
                        assert stored(STATE) == inventory, 'opening manual confirmation must not save'
                        page.locator('#umfQty').fill('1개');page.locator('#expiry').fill('2026-10-29');page.locator('#save').click()
                        page.wait_for_function("UMFStore.getState().items.some(r=>r.name==='사진 확인 두부' && r.expiry==='2026-10-29')")
                        page.locator('[data-photo-mode="fridge"]').click()
                        page.locator('[data-life-photo="fridge"]').set_input_files({'name':'not-an-image.txt','mimeType':'text/plain','buffer':b'x'})
                        expect(page.locator('#lifeStatus')).to_contain_text('JPEG')
                        page.locator('[data-life-photo="fridge"]').set_input_files({'name':'synthetic.png','mimeType':'image/png','buffer':PHOTO})
                        expect(page.locator('[data-life-photo-preview="fridge"]')).to_be_visible()
                        passed(f'{label}: two-photo and whole-fridge previews do not fabricate OCR, reject invalid files and require manual inventory confirmation')

                        raw = stored(LIFE)
                        other = 'use-me-first.html' if mode == 'widget' else 'use-me-first-widget.html'
                        page.goto(origin+'/'+other, wait_until='networkidle')
                        assert stored(LIFE) == raw
                        expect(page.locator('body')).to_have_attribute('data-life-theme','sage')
                        go('nutrition');expect(page.locator('#lifeNutrients')).to_contain_text('700 kcal')
                        assert page.evaluate('UMFLifeStore.getState().supplements[0].days') == ['2026-10-23']
                        assert stored(VIEW) == view
                        assert not errors, errors
                        passed(f'{label}: both entry files share the same goals, budget, nutrition, supplements and decor after reload')
                        page.locator('#umfKitchenSettings summary').click()
                        page.locator('#widgetThemeControl').click()
                        expect(page.locator('html')).to_have_attribute('data-widget-theme','dark')
                        contrast = page.locator('#lifeNutrients .life-metric').first.evaluate('''e => {
                            const lum = rgb => {const c=rgb.match(/[0-9.]+/g).slice(0,3).map(n=>{const v=Number(n)/255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)});return c[0]*.2126+c[1]*.7152+c[2]*.0722;};
                            const bg=lum(getComputedStyle(e).backgroundColor), fg=lum(getComputedStyle(e.querySelector('span')).color);
                            return (Math.max(bg,fg)+.05)/(Math.min(bg,fg)+.05);
                        }''')
                        assert contrast >= 4.5, contrast
                        assert stored(STATE) != inventory  # Only the explicitly confirmed photo item was added.
                        assert stored(LIFE) == raw and stored(VIEW) == view
                        assert not errors, errors
                        passed(f'{label}: existing theme control retains readable life-card text without changing life records')
                    except Exception as e:
                        result['errors'].append(f'{label}: {type(e).__name__}: {e}')
                        traceback.print_exc()
                        page.screenshot(path=str(output / f'failure-{label}.png'), full_page=True)
                    finally:
                        context.close()
            browser.close()
    finally:
        server.shutdown()
    result['passed'] = not result['errors']
    result['passed_cases'] = len(result['cases'])
    (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
