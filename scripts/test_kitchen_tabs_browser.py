#!/usr/bin/env python3
"""Check viewport tabs, keyboard/focus and contained long records in both previews.

This is a local Chromium check. Public hosting, OCR, Safari and physical phones
are separate checks. Interaction uses controls and read-only model assertions;
the explicit legacy-storage fixture is the sole initial-state setup.
"""
import argparse
import functools
import hashlib
import json
import threading
import traceback
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[1]) or output == root:
        raise SystemExit('Keep browser evidence outside checkout and input root')
    output.mkdir(parents=True, exist_ok=True)
    inputs = [root/f'miniature-kitchen-{mode}.html' for mode in ('app', 'widget')]
    inputs += [root/'mobile'/f'{mode}.html' for mode in ('app', 'widget')]
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    report = {'scope': 'Local Chromium tabs, keyboard/focus and long actual-form records; no physical-phone claim',
              'source_sha256': hashes, 'passed': [], 'failures': [], 'profiles': []}
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []

    def passed(name):
        report['passed'].append(name)
        print('PASS '+name, flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])

        def new(mode, width, height, opaque=False, init=None):
            context = browser.new_context(viewport={'width': width, 'height': height}, timezone_id='Asia/Seoul',
                                          reduced_motion='reduce', has_touch=opaque, is_mobile=opaque)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            if init:
                page.add_init_script(init)
            page.clock.install(time=datetime.fromisoformat('2026-11-01T03:00:00+00:00'))
            path = f'/mobile/{mode}.html' if opaque else f'/miniature-kitchen-{mode}.html'
            page.goto(f'http://127.0.0.1:{server.server_port}'+path)
            frame = page.locator('iframe').element_handle().content_frame() if opaque else page
            frame.wait_for_function('window.KitchenHome&&window.KitchenWorkflows')
            return context, page, frame

        def choose(frame, name, sub=None):
            control = frame.locator(f'.home-shortcuts [data-home-tab="{name}"]')
            control.click()
            expect(control).to_have_attribute('aria-selected', 'true')
            if sub:
                control = frame.locator(f'[data-home-subtab="{sub}"]')
                control.click()
                expect(control).to_have_attribute('aria-selected', 'true')

        def viewport(frame):
            metrics = frame.evaluate('''()=>({height:innerHeight,pageHeight:document.documentElement.scrollHeight,
                width:innerWidth,pageWidth:document.documentElement.scrollWidth,scrollY,
                panels:[...document.querySelectorAll('.home-panel')].filter(e=>!e.hidden).map(e=>e.id),
                tabs:[...document.querySelectorAll('.home-shortcuts button')].map(e=>{const r=e.getBoundingClientRect();return {
                    text:e.textContent,selected:e.getAttribute('aria-selected'),tabIndex:e.tabIndex,height:r.height,width:r.width,
                    inView:r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth,
                    hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===e};})})''')
            assert metrics['pageHeight'] <= metrics['height']+1, metrics
            assert metrics['pageWidth'] <= metrics['width']+1, metrics
            assert metrics['scrollY'] == 0, metrics
            assert len(metrics['panels']) == 1, metrics
            assert all(t['inView'] and t['hit'] and t['height'] >= 44 for t in metrics['tabs']), metrics
            assert max(t['width'] for t in metrics['tabs'])-min(t['width'] for t in metrics['tabs']) <= 1, metrics
            assert sum(t['selected'] == 'true' for t in metrics['tabs']) == 1, metrics
            assert sum(t['tabIndex'] == 0 for t in metrics['tabs']) == 1, metrics
            return metrics

        def header(frame):
            result = frame.evaluate('''()=>{
                const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,left:r.left,right:r.right,top:r.top,bottom:r.bottom};};
                const selectors=['.masthead h1','.header-actions button','#homeStorageNotice span','#homeStorageNotice button'];
                const rows=selectors.map(selector=>{const e=document.querySelector(selector);return {selector,e,r:e?rect(e):null};})
                    .filter(v=>v.r?.width&&v.r?.height);
                const overlaps=[];for(let i=0;i<rows.length;i++)for(let j=i+1;j<rows.length;j++){
                    const a=rows[i].r,b=rows[j].r;if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>.5&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>.5)
                        overlaps.push([rows[i].selector,rows[j].selector]);
                }
                return {overlaps,rows:rows.map(({selector,e,r})=>({selector,...r,hit:e.tagName!=='BUTTON'||document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===e}))};
            }''')
            assert not result['overlaps'], result
            assert all(row['left'] >= 0 and row['hit'] for row in result['rows']), result
            backup = next((row for row in result['rows'] if row['selector'] == '#homeStorageNotice button'), None)
            if backup:
                assert backup['width'] >= 44 and backup['height'] >= 44, backup
                expect(frame.locator('#homeStorageNotice')).to_have_attribute('aria-label', '임시 세션입니다. 닫기 전에 백업해 주세요.')
            return result

        def small_shelf_labels(frame):
            result = frame.evaluate('''()=>{
                const rows=[];for(const e of document.querySelectorAll('.fridge-interiors .shelf-label:not(.is-selected) b')){
                    const label=e.closest('.shelf-label'),range=new Range();range.selectNodeContents(e);
                    for(const r of range.getClientRects())if(r.width&&r.height)rows.push({id:label.dataset.forItem,text:e.textContent,left:r.left,right:r.right,top:r.top,bottom:r.bottom});
                }
                const overlaps=[];for(let i=0;i<rows.length;i++)for(let j=i+1;j<rows.length;j++){
                    const a=rows[i],b=rows[j];if(a.id!==b.id&&Math.min(a.right,b.right)-Math.max(a.left,b.left)>.5&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>.5)
                        overlaps.push([a.text,b.text]);
                }
                const visibleQuantities=[...document.querySelectorAll('.fridge-interiors .shelf-label:not(.is-selected) small')]
                    .filter(e=>e.getBoundingClientRect().width&&e.getBoundingClientRect().height).length;
                return {rows,overlaps,visibleQuantities};
            }''')
            assert result['rows'], result
            assert not result['overlaps'], result
            assert result['visibleQuantities'] == 0, result
            return result

        try:
            profiles = [(mode, width, height, False) for mode in ('app', 'widget')
                        for width, height in ((320, 660), (390, 844), (1120, 1000))]
            profiles += [('app', 320, 660, True), ('widget', 390, 844, True)]
            for mode, width, height, opaque in profiles:
                context, page, frame = new(mode, width, height, opaque)
                before = frame.evaluate('KitchenJournal.getEnvelope()')
                fridge = frame.locator('.fridge-stage').bounding_box()
                nav = frame.locator('.home-shortcuts').bounding_box()
                header_metrics = header(frame)
                shelf_metrics = small_shelf_labels(frame) if width == 320 else None
                for name, sub in [('meals', 'recommendation'), ('meals', 'plans'), ('records', 'nutrition'),
                                  ('records', 'budget'), ('records', 'supplements'), ('records', 'monthly'),
                                  ('kitchen', 'growth'), ('kitchen', 'connections'), ('kitchen', 'decor'), ('fridge', None)]:
                    choose(frame, name, sub)
                    viewport(frame)
                    assert frame.locator('.home-shortcuts').bounding_box() == nav
                assert frame.evaluate('KitchenJournal.getEnvelope()') == before
                assert frame.locator('.fridge-stage').bounding_box() == fridge
                if mode == 'app' and width >= 1000:
                    desktop_before = frame.evaluate('KitchenJournal.getEnvelope()')
                    frame.locator('#desktopSummary [data-home-open="decor"]').click()
                    expect(frame.locator('[data-home-subtab="decor"]')).to_have_attribute('aria-selected', 'true')
                    expect(frame.locator('#decorStage .room')).to_be_visible()
                    assert frame.evaluate('KitchenJournal.getEnvelope()') == desktop_before
                    choose(frame, 'fridge')
                tab = frame.locator('[data-home-tab="fridge"]')
                tab.focus()
                for key, expected in [('ArrowRight', 'meals'), ('End', 'kitchen'), ('ArrowRight', 'fridge'),
                                      ('ArrowLeft', 'kitchen'), ('Home', 'fridge')]:
                    frame.locator('.home-shortcuts [aria-selected="true"]').press(key)
                    expect(frame.locator(f'[data-home-tab="{expected}"]')).to_be_focused()
                    expect(frame.locator(f'[data-home-tab="{expected}"]')).to_have_attribute('aria-selected', 'true')
                    viewport(frame)
                choose(frame, 'records', 'nutrition')
                frame.locator('[data-home-subtab="nutrition"]').focus()
                for key, expected in [('ArrowRight', 'budget'), ('End', 'monthly'), ('ArrowRight', 'nutrition'),
                                      ('ArrowLeft', 'monthly'), ('Home', 'nutrition')]:
                    frame.locator('#panel-records .panel-tabs [aria-selected="true"]').press(key)
                    expect(frame.locator(f'[data-home-subtab="{expected}"]')).to_be_focused()
                    expect(frame.locator(f'[data-home-subtab="{expected}"]')).to_have_attribute('aria-selected', 'true')
                assert frame.evaluate('KitchenJournal.getEnvelope()') == before
                choose(frame, 'fridge')
                page.wait_for_timeout(100)  # Let the opaque iframe's compositor paint its selected panel.
                page.screenshot(path=str(output/f'{mode}-{width}-{"opaque" if opaque else "native"}-tabs.png'))
                # Recipes lead to useful plan/meal forms in the meals context,
                # rather than jumping to a picture-only counter scene.
                choose(frame, 'meals', 'recommendation')
                frame.locator('#homeRecommendation [data-wf="recipe"]').click()
                expect(frame.locator('#tray')).to_be_visible()
                recipe_id = frame.locator('#tray [data-wf="planRecipe"]').get_attribute('data-arg')
                opened = frame.evaluate('KitchenJournal.getEnvelope()')
                expect(frame.locator('#tray [data-wf="counterRecipe"]')).to_have_count(0)
                frame.locator('#tray [data-wf="planRecipe"]').click()
                expect(frame.locator('[data-wf-form="plan"]')).to_be_visible()
                expect(frame.locator('[data-wf-form="plan"] [name="recipeId"]')).to_have_value(recipe_id)
                assert frame.evaluate('KitchenJournal.getEnvelope()') == opened
                frame.locator('#closeTray').click()
                expect(frame.locator('[data-home-tab="meals"]')).to_have_attribute('aria-selected', 'true')
                expect(frame.locator('body')).to_have_attribute('data-camera', 'fridge')
                assert frame.evaluate('''()=>{const e=document.activeElement,r=e.getBoundingClientRect();
                    return e!==document.body&&r.width>0&&r.height>0&&r.top>=0&&r.bottom<=innerHeight;}''')
                frame.locator('#homeRecommendation [data-wf="recipe"]').click()
                frame.locator('#tray [data-wf="logMeal"]').click()
                expect(frame.locator('#workflowMealForm')).to_be_visible()
                assert frame.evaluate('KitchenJournal.getEnvelope()') == opened
                frame.locator('#closeTray').click()
                choose(frame, 'fridge')
                expect(frame.locator('.camera-tabs')).to_have_count(0)
                choose(frame, 'kitchen', 'decor')
                expect(frame.locator('#decorStage .room')).to_be_visible()
                expect(frame.locator('#decorStage .counter-zone')).to_be_visible()
                expect(frame.locator('[data-decor-done]')).to_be_visible()
                assert frame.evaluate('KitchenJournal.getEnvelope()') == opened
                viewport(frame)
                frame.locator('[data-decor-done]').click()
                expect(frame.locator('[data-home-subtab="growth"]')).to_have_attribute('aria-selected', 'true')
                expect(frame.locator('[data-home-subtab="growth"]')).to_be_focused()
                choose(frame, 'fridge')
                expect(frame.locator('#fridgeSceneHost .room')).to_be_visible()
                assert frame.evaluate('KitchenJournal.getEnvelope()') == opened
                viewport(frame)
                report['profiles'].append({'mode': mode, 'width': width, 'height': height, 'opaque': opaque,
                                           'metrics': viewport(frame), 'header': header_metrics, 'small_shelf_labels': shelf_metrics})
                passed(f'{mode} {width}x{height} {"opaque touch" if opaque else "native"}: one viewport, keyboard tabs, stable fridge, recipe-to-plan/meal forms, decor round-trip, no secondary space tabs and exact records')
                context.close()

            # Real forms create enough products to exceed a phone. Only this
            # named list may scroll; main navigation stays visible and fixed.
            context, page, frame = new('app', 390, 844)
            choose(frame, 'records', 'supplements')
            frame.locator('#homeSupplements [data-workflow="supplements"]').click()
            for index in range(16):
                form = frame.locator('[data-wf-form="supplement"]')
                form.locator('[name="name"]').fill(f'검사용 제품 {index+1:02d}')
                form.locator('[name="schedule"]').fill('내가 정한 일정')
                form.locator('[type="submit"]').click()
            frame.locator('#closeTray').click()
            choose(frame, 'records', 'supplements')
            viewport(frame)
            product = frame.locator('[data-home-supplement]').last
            product.scroll_into_view_if_needed()
            product.check()
            viewport(frame)
            saved = frame.evaluate('KitchenJournal.getEnvelope()')
            assert len(saved['workflow']['supplements']) == 16
            assert saved['workflow']['supplements'][-1]['days'] == ['2026-11-01']
            frame.locator('#homeSupplements [data-workflow="supplements"]').click()
            frame.locator('#closeTray').click()
            expect(frame.locator('#homeSupplements [data-workflow="supplements"]')).to_be_focused()
            choose(frame, 'fridge')
            choose(frame, 'records', 'supplements')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == saved
            viewport(frame)
            page.screenshot(path=str(output/'long-supplements-contained.png'))
            passed('16 real-form products scroll within their panel, remain editable, restore modal focus and preserve exact records across tabs')
            context.close()
            # An existing version-1 world can keep stock outside the visible
            # fridge. The new inventory must not relocate or discard those lots.
            legacy_world = json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/miniature-legacy-world-v1.json').read_text())
            next(item for item in legacy_world['items'] if item['id'] == 'milk')['zone'] = 'counter'
            legacy_play = {'version': 1, 'meals': [], 'targets': {k: None for k in ['kcal','carb','protein','fat','fiber','water']},
                           'discovered': [], 'awarded': [], 'owned': [], 'equipped': {'frozenLeft': None, 'frozenRight': None},
                           'goal': 'collection', 'plateLabel': '우리 집 부엌'}
            legacy_raw = json.dumps({'version': 1, 'world': legacy_world, 'play': legacy_play}, ensure_ascii=False)
            context, page, frame = new('app', 390, 844, init='if(localStorage.getItem("miniature-kitchen-preview-v1")===null)localStorage.setItem("miniature-kitchen-preview-v1",'+json.dumps(legacy_raw)+')')
            before = frame.evaluate('KitchenJournal.getEnvelope()')
            assert before['world'] == legacy_world
            frame.locator('.header-actions [data-workflow="inventory"]').click()
            frame.locator('#tray [data-wf="inventoryKind"][data-arg="seasoning"]').click()
            expect(frame.locator('#tray .workflow-nav [aria-current="page"]')).to_have_text('부엌')
            expected_ids = sorted(item['id'] for item in legacy_world['items'] if item['kind'] == 'seasoning')
            actual_ids = sorted(frame.locator('#tray .inventory-row').evaluate_all('rows=>rows.map(e=>e.dataset.arg)'))
            assert actual_ids == expected_ids
            assert frame.evaluate('KitchenJournal.getEnvelope()') == before
            frame.locator('#tray [data-wf="item"][data-arg="spice0"]').click()
            form = frame.locator('#ingredientForm')
            expect(form.locator('[name="zone"]')).to_have_value('seasoning')
            form.locator('[name="quantity"]').fill('120mL')
            form.locator('[name="expiry"]').fill('2026-12-20')
            form.locator('[name="opened"]').fill('2026-11-01')
            form.locator('[name="expiryType"]').select_option('useBy')
            form.locator('[type="submit"]').click()
            expect(frame.locator('[data-home-tab="fridge"]')).to_have_attribute('aria-selected', 'true')
            expect(frame.locator('body')).to_have_attribute('data-camera', 'fridge')
            expect(frame.locator('#tray .inventory-list')).to_be_visible()
            after = frame.evaluate('KitchenJournal.getEnvelope()')
            old_lot = next(item for item in before['world']['items'] if item['id'] == 'spice0')
            new_lot = next(item for item in after['world']['items'] if item['id'] == 'spice0')
            expected_lot = {**old_lot, 'quantity': '120mL', 'expiry': '2026-12-20', 'opened': '2026-11-01',
                            'expiryType': 'useBy', 'depleted': False, 'manualRevision': old_lot.get('manualRevision', 0)+1}
            assert new_lot == expected_lot, new_lot
            expected_world = json.loads(json.dumps(before['world']))
            expected_world['items'] = [expected_lot if item['id'] == 'spice0' else item for item in expected_world['items']]
            assert after['world'] == expected_world
            assert after['play'] == before['play'] and after['workflow'] == before['workflow']
            frame.locator('#tray [data-wf="inventoryKind"][data-arg="all"]').click()
            expect(frame.locator('#tray [data-wf="item"][data-arg="milk"]')).to_contain_text('냉장고 밖 재료')
            frame.locator('#tray [data-wf="item"][data-arg="milk"]').click()
            expect(frame.locator('#ingredientForm [name="zone"]')).to_have_value('counter')
            expect(frame.locator('#ingredientForm [name="quantity"]')).to_have_value('500ml')
            frame.locator('#closeTray').click()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after
            passed('legacy outside-fridge sauce and food lots remain reachable, editable and exactly located without automatic migration')

            # Decoration is a purposeful work mode under My Kitchen. Entering
            # and leaving is read-only; a real drag persists only that prop.
            choose(frame, 'kitchen', 'decor')
            expect(frame.locator('#decorStage .room')).to_be_visible()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after
            prop = frame.locator('#decorStage [data-item="cup"]')
            expect(prop).to_be_visible()
            prop_box, zone_box = prop.bounding_box(), frame.locator('#decorStage .counter-zone').bounding_box()
            assert prop_box and zone_box
            start_x, start_y = prop_box['x']+prop_box['width']/2, prop_box['y']+prop_box['height']/2
            target_x, target_y = zone_box['x']+zone_box['width']*.5, zone_box['y']+zone_box['height']*.72
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(target_x, target_y, steps=12)
            page.mouse.up()
            moved = frame.evaluate('KitchenJournal.getEnvelope()')
            old_prop = next(item for item in after['world']['items'] if item['id'] == 'cup')
            new_prop = next(item for item in moved['world']['items'] if item['id'] == 'cup')
            assert (old_prop['x'], old_prop['y']) != (new_prop['x'], new_prop['y']), (old_prop, new_prop)
            assert {k:v for k,v in new_prop.items() if k not in ['x','y','z']} == {k:v for k,v in old_prop.items() if k not in ['x','y','z']}
            assert [item for item in moved['world']['items'] if item['id'] != 'cup'] == [item for item in after['world']['items'] if item['id'] != 'cup']
            assert moved['play'] == after['play'] and moved['workflow'] == after['workflow']
            frame.locator('[data-decor-done]').click()
            expect(frame.locator('[data-home-subtab="growth"]')).to_have_attribute('aria-selected', 'true')
            choose(frame, 'fridge')
            expect(frame.locator('#fridgeSceneHost .room')).to_be_visible()
            choose(frame, 'kitchen', 'decor')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == moved
            page.screenshot(path=str(output/'decoration-purposeful-mode.png'))
            page.reload()
            frame.wait_for_function('window.KitchenHome&&window.KitchenWorkflows')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == moved
            choose(frame, 'kitchen', 'decor')
            expect(frame.locator('#decorStage [data-item="cup"]')).to_be_visible()
            passed('My Kitchen decoration uses the existing canvas, persists a real prop drag and restores exact stock and records after exit/reload')
            context.close()
            assert not errors, errors
            passed('no JavaScript errors during tab and long-record journeys')
        except Exception as error:
            report['failures'].append({'message': str(error), 'trace': traceback.format_exc()})
            try:
                page.screenshot(path=str(output/'failure.png'), full_page=True)
            except Exception:
                pass
            raise
        finally:
            current = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
            report['inputs_unchanged'] = current == hashes
            report['javascript_errors'] = errors
            (output/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            browser.close()
            server.shutdown()


if __name__ == '__main__':
    main()
