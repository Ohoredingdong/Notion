#!/usr/bin/env python3
"""Check viewport tabs, keyboard/focus and contained long records in both previews.

This is a local Chromium check. Public hosting, OCR, Safari and physical phones
are separate checks. Interaction uses controls and read-only model assertions;
explicit legacy-storage fixtures and one documented concurrent-stock update are intentional setup; recorded business journeys use actual controls.
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



def reveal(locator):
    """Open real optional-detail controls before interacting with their fields."""
    for details in locator.locator('xpath=ancestor::details').all():
        if details.get_attribute('open') is None:
            details.locator('summary').first.click()
    return locator

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
    report = {'scope': 'Local Chromium tabs, keyboard/focus, actual-form records and explicitly controlled OCR-result UI contract; no OCR recognition or physical-phone claim',
              'source_sha256': hashes, 'passed': [], 'failures': [], 'profiles': []}
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []

    def passed(name):
        report['passed'].append(name)
        print('PASS '+name, flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])

        def new(mode, width, height, opaque=False, init=None, device_scale_factor=1):
            context = browser.new_context(viewport={'width': width, 'height': height}, timezone_id='Asia/Seoul',
                                          reduced_motion='reduce', has_touch=opaque, is_mobile=opaque,
                                          device_scale_factor=device_scale_factor)
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
            if frame.locator('.decor-footer [data-decor-cancel]').is_visible():
                frame.locator('.decor-footer [data-decor-cancel]').click()
            control = frame.locator(f'.home-shortcuts [data-home-tab="{name}"]')
            control.click()
            expect(control).to_have_attribute('aria-selected', 'true')
            if sub:
                control = frame.locator(f'[data-home-subtab="{sub}"]')
                if control.get_attribute('aria-selected') != 'true':
                    if control.is_visible():
                        control.click()
                    else:
                        frame.locator(f'[data-home-open="{sub}"]:visible').first.click()
                expect(control).to_have_attribute('aria-selected', 'true')

        def viewport(frame):
            metrics = frame.evaluate('''()=>({height:innerHeight,pageHeight:document.documentElement.scrollHeight,
                width:innerWidth,pageWidth:document.documentElement.scrollWidth,scrollY,
                shell:(()=>{const r=document.querySelector('.shell').getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height};})(),
                nav:(()=>{const r=document.querySelector('.home-shortcuts').getBoundingClientRect();return {top:r.top,bottom:r.bottom,width:r.width};})(),
                panels:[...document.querySelectorAll('.home-panel')].filter(e=>!e.hidden).map(e=>e.id),
                tabs:[...document.querySelectorAll('.home-shortcuts button')].map(e=>{const r=e.getBoundingClientRect();return {
                    text:e.textContent.trim(),bottom:r.bottom,selected:e.getAttribute('aria-selected'),tabIndex:e.tabIndex,height:r.height,width:r.width,
                    inView:r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth,
                    hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===e};})})''')
            assert metrics['pageHeight'] <= metrics['height']+1, metrics
            assert metrics['pageWidth'] <= metrics['width']+1, metrics
            assert metrics['scrollY'] == 0, metrics
            assert len(metrics['panels']) == 1, metrics
            assert [t['text'].strip() for t in metrics['tabs']] == ['냉장고','레시피','기록','내 부엌'], metrics
            if frame.locator('.decor-footer [data-decor-cancel]').is_visible():
                expect(frame.locator('.home-shortcuts')).not_to_be_visible()
                for selector in ('.decor-footer [data-decor-cancel]','[data-decor-apply]'):
                    action = frame.locator(selector)
                    expect(action).to_be_visible()
                    assert action.evaluate('''e=>{const r=e.getBoundingClientRect();return r.height>=44&&r.top>=0&&r.bottom<=innerHeight&&document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===e;}'''), selector
                metrics['focused_decor_editor'] = True
                return metrics
            # The approved widget is a compact component centered in a taller
            # embed. Its navigation belongs to the component, not the viewport.
            assert abs(metrics['nav']['bottom']-metrics['shell']['bottom']) <= 2, metrics
            assert all(t['height'] >= 44 and metrics['shell']['bottom']-44 <= t['bottom'] <= metrics['shell']['bottom']+1 for t in metrics['tabs']), metrics
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
                const rows=[];for(const e of document.querySelectorAll('.fridge-interiors .shelf-label:not(.is-selected) b,.fridge-interiors .shelf-label:not(.is-selected) small')){
                    const label=e.closest('.shelf-label'),style=getComputedStyle(label),glyphStyle=getComputedStyle(e);
                    if(style.display==='none'||style.visibility!=='visible'||Number(style.opacity)===0||glyphStyle.display==='none'||glyphStyle.visibility!=='visible'||Number(glyphStyle.opacity)===0)continue;
                    const range=new Range();range.selectNodeContents(e);
                    for(const r of range.getClientRects())if(r.width&&r.height)rows.push({id:label.dataset.forItem,text:e.textContent,left:r.left,right:r.right,top:r.top,bottom:r.bottom});
                }
                const overlaps=[];for(let i=0;i<rows.length;i++)for(let j=i+1;j<rows.length;j++){
                    const a=rows[i],b=rows[j];if(a.id!==b.id&&Math.min(a.right,b.right)-Math.max(a.left,b.left)>.5&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>.5)
                        overlaps.push([a.text,b.text]);
                }
                const visibleQuantities=[...document.querySelectorAll('.fridge-interiors .shelf-label:not(.is-selected) small')]
                    .filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e),p=getComputedStyle(e.closest('.shelf-label'));return r.width&&r.height&&s.visibility==='visible'&&s.display!=='none'&&Number(s.opacity)>0&&p.visibility==='visible'&&p.display!=='none'&&Number(p.opacity)>0;}).length;
                const ingredientButtons=[...document.querySelectorAll('.fridge-interiors [data-item]')].map(e=>({id:e.dataset.item,name:e.getAttribute('aria-label')}));
                return {rows,overlaps,visibleQuantities,ingredientButtons};
            }''')
            assert result['rows'], result
            assert not result['overlaps'], result
            assert result['ingredientButtons'] and all(row['name'] for row in result['ingredientButtons']), result
            return result

        def drag_prop(page, frame):
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
            return frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")')

        try:
            profiles = [(mode, width, height, False) for mode in ('app', 'widget')
                        for width, height in ((320, 568), (320, 660), (390, 844), (1120, 1000))]
            profiles += [('app', 320, 660, True), ('widget', 320, 568, True), ('widget', 390, 844, True)]
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
                    if name not in ('fridge','records'):
                        expect(frame.locator('#dailyBalance')).not_to_be_visible()
                    if sub != 'decor':
                        current_nav = frame.locator('.home-shortcuts').bounding_box()
                        assert abs(current_nav['x']-nav['x']) <= 1 and abs(current_nav['width']-nav['width']) <= 1
                        # Hubs may use a taller compact card than the fridge;
                        # viewport() verifies the navigation follows its current component bottom.
                assert frame.evaluate('KitchenJournal.getEnvelope()') == before
                actual_fridge = frame.locator('.fridge-stage').bounding_box()
                assert actual_fridge == fridge, (fridge, actual_fridge)
                if mode == 'app' and width >= 1000:
                    desktop_before = frame.evaluate('KitchenJournal.getEnvelope()')
                    frame.locator('#desktopSummary [data-home-open="growth"]').click()
                    expect(frame.locator('[data-home-subtab="growth"]')).to_have_attribute('aria-selected', 'true')
                    frame.locator('#homeGrowth .growth-preview').click()
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
                page.screenshot(path=str(output/f'{mode}-{width}x{height}-{"opaque" if opaque else "native"}-tabs.png'))
                # Recipes lead to useful plan/meal forms in the meals context,
                # rather than jumping to a picture-only counter scene.
                choose(frame, 'meals', 'recommendation')
                frame.locator('#homeRecommendation [data-home-recipe] .home-actions [data-wf="recipe"]').click()
                expect(frame.locator('#tray')).to_be_visible()
                expect(frame.locator('#tray .daily-balance')).to_have_count(0)
                recipe_id = frame.locator('#tray [data-wf="planRecipe"]').get_attribute('data-arg')
                opened = frame.evaluate('KitchenJournal.getEnvelope()')
                expect(frame.locator('#tray [data-wf="counterRecipe"]')).to_have_count(0)
                frame.locator('#tray [data-wf="planRecipe"]').click()
                expect(frame.locator('[data-wf-form="plan"]')).to_be_visible()
                expect(frame.locator('[data-wf-form="plan"] [name="recipeId"]')).to_have_value(recipe_id)
                assert frame.evaluate('KitchenJournal.getEnvelope()') == opened
                frame.locator('#tray .workflow-nav [data-wf="back"]').click()
                expect(frame.locator('#tray')).to_have_attribute('data-workflow-route', 'recipe')
                expect(frame.locator('#tray [data-wf="planRecipe"]')).to_be_visible()
                expect(frame.locator('[data-home-tab="meals"]')).to_have_attribute('aria-selected', 'true')
                expect(frame.locator('body')).to_have_attribute('data-camera', 'fridge')
                assert frame.evaluate('''()=>{const e=document.activeElement,r=e.getBoundingClientRect();
                    return e!==document.body&&r.width>0&&r.height>0&&r.top>=0&&r.bottom<=innerHeight;}''')
                frame.locator('#tray [data-wf="logMeal"]').click()
                expect(frame.locator('#workflowMealForm')).to_be_visible()
                assert frame.evaluate('KitchenJournal.getEnvelope()') == opened
                frame.locator('#tray .workflow-nav [data-wf="back"]').click()
                expect(frame.locator('#tray')).to_have_attribute('data-workflow-route', 'recipe')
                frame.locator('#closeTray').click()
                expect(frame.locator('#tray')).not_to_be_visible()
                choose(frame, 'fridge')
                expect(frame.locator('.camera-tabs')).to_have_count(0)
                choose(frame, 'kitchen', 'decor')
                expect(frame.locator('#decorStage .room')).to_be_visible()
                expect(frame.locator('#decorStage .counter-zone')).to_be_visible()
                expect(frame.locator('.decor-footer [data-decor-cancel]')).to_be_visible()
                expect(frame.locator('[data-decor-apply]')).to_be_visible()
                assert frame.evaluate('KitchenJournal.getEnvelope()') == opened
                viewport(frame)
                frame.locator('.decor-footer [data-decor-cancel]').click()
                expect(frame.locator('[data-home-subtab="growth"]')).to_have_attribute('aria-selected', 'true')
                expect(frame.locator('#panel-kitchen > .hub-heading button').first).to_be_focused()
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
            frame.locator('#homeSupplements .home-block-heading [data-workflow="supplements"]').click()
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
            frame.locator('#homeSupplements .home-block-heading [data-workflow="supplements"]').click()
            frame.locator('#closeTray').click()
            expect(frame.locator('#homeSupplements .home-block-heading [data-workflow="supplements"]')).to_be_focused()
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
            expect(frame.locator('#tray .workflow-context')).to_have_text('재료 목록')
            expected_ids = sorted(item['id'] for item in legacy_world['items'] if item['kind'] == 'seasoning')
            actual_ids = sorted(frame.locator('#tray .inventory-row').evaluate_all('rows=>rows.map(e=>e.dataset.arg)'))
            assert actual_ids == expected_ids
            assert frame.evaluate('KitchenJournal.getEnvelope()') == before
            frame.locator('#inventoryZone').select_option('outside')
            expect(frame.locator('#inventoryZone')).to_have_value('outside')
            assert sorted(frame.locator('#tray .inventory-row').evaluate_all('rows=>rows.map(e=>e.dataset.arg)')) == expected_ids
            assert frame.evaluate('KitchenJournal.getEnvelope()') == before
            frame.locator('#tray [data-wf="item"][data-arg="spice0"]').click()
            form = frame.locator('#ingredientForm')
            expect(form.locator('[name="zone"]')).to_have_value('seasoning')
            form.locator('[name="quantity"]').fill('120mL')
            form.locator('[name="expiry"]').fill('2026-12-20')
            reveal(form.locator('[name="opened"]')).fill('2026-11-01')
            reveal(form.locator('[name="expiryType"]')).select_option('useBy')
            form.locator('[type="submit"]').click()
            expect(frame.locator('[data-home-tab="fridge"]')).to_have_attribute('aria-selected', 'true')
            expect(frame.locator('body')).to_have_attribute('data-camera', 'fridge')
            expect(frame.locator('#tray .inventory-list')).to_be_visible()
            expect(frame.locator('#inventoryZone')).to_have_value('outside')
            expect(frame.locator('#tray [data-wf="inventoryKind"][data-arg="seasoning"]')).to_have_attribute('aria-pressed','true')
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
            expect(frame.locator('#tray .inventory-list')).to_be_visible()
            frame.locator('#closeTray').click()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after
            passed('legacy outside-fridge sauce and food lots remain reachable, editable and exactly located without automatic migration')

            # Decoration is a draft: gesture changes the visible scene, not
            # the committed envelope or persisted bytes until Apply.
            choose(frame, 'kitchen', 'decor')
            expect(frame.locator('#decorStage .room')).to_be_visible()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after
            stored_before = frame.evaluate('localStorage.getItem(KitchenJournal.storageKey)')


            def theme_preview():
                frame.locator('#homeDecor .decor-actions').get_by_role('button',name='배경',exact=True).click()
                form = frame.locator('[data-wf-form="theme"]')
                form.locator('[name="background"]').select_option('stone')
                form.locator('[name="labels"]').select_option('minimal')
                form.locator('[name="organizer"]').check()
                form.locator('[type="submit"]').click()
                expect(frame.locator('#decorStage .room')).to_be_visible()

            old_prop = next(item for item in after['world']['items'] if item['id'] == 'cup')
            home_prop = frame.locator('#homeSceneDecor [data-home-prop="cup"]')
            old_home_left = home_prop.evaluate('e=>e.style.getPropertyValue("--prop-x")')
            old_home_top = home_prop.evaluate('e=>e.style.top')
            preview_prop = drag_prop(page, frame)
            theme_preview()
            assert (old_prop['x'],old_prop['y']) != (preview_prop['x'],preview_prop['y'])
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after
            assert frame.evaluate('localStorage.getItem(KitchenJournal.storageKey)') == stored_before
            assert home_prop.evaluate('e=>e.style.getPropertyValue("--prop-x")') == old_home_left
            assert home_prop.evaluate('e=>e.style.top') == old_home_top
            expect(frame.locator('.decor-footer [data-decor-cancel]')).to_be_visible()
            frame.locator('.decor-footer [data-decor-cancel]').click()
            expect(frame.locator('[data-home-subtab="growth"]')).to_have_attribute('aria-selected','true')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after
            choose(frame, 'kitchen', 'decor')
            assert frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")') == old_prop
            preview_prop = drag_prop(page, frame)
            theme_preview()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after
            frame.locator('[data-decor-apply]').click()
            expect(frame.locator('[data-home-tab="fridge"]')).to_have_attribute('aria-selected','true')
            moved = frame.evaluate('KitchenJournal.getEnvelope()')
            new_prop = next(item for item in moved['world']['items'] if item['id'] == 'cup')
            assert (new_prop['x'], new_prop['y']) == (preview_prop['x'], preview_prop['y'])
            assert {k:v for k,v in new_prop.items() if k not in ['x','y','z']} == {k:v for k,v in old_prop.items() if k not in ['x','y','z']}
            assert [item for item in moved['world']['items'] if item['id'] != 'cup'] == [item for item in after['world']['items'] if item['id'] != 'cup']
            expected_flow = json.loads(json.dumps(after['workflow']))
            expected_flow['theme'] = {'background':'stone','labels':'minimal','organizer':True}
            assert moved['play'] == after['play'] and moved['workflow'] == expected_flow
            expect(frame.locator('#fridgeSceneHost .room')).to_be_visible()
            home_prop = frame.locator('#homeSceneDecor [data-home-prop="cup"]')
            expect(home_prop.locator('svg.decor-art')).to_be_visible()
            assert home_prop.evaluate('e=>e.checkVisibility({opacityProperty:true,visibilityProperty:true})'), 'Applied scene artwork cannot be hidden by CSS opacity or visibility'
            expected_left = new_prop['x'] * 100
            assert abs(float(home_prop.evaluate('e=>e.style.getPropertyValue("--prop-x")').rstrip('%'))-expected_left) < .001
            expected_top = max(0, min(100, new_prop['y'] * 100))
            assert abs(float(home_prop.evaluate('e=>e.style.top').rstrip('%'))-expected_top) < .001
            assert home_prop.evaluate('e=>e.style.getPropertyValue("--prop-x")') != old_home_left
            assert home_prop.evaluate('e=>e.style.top') != old_home_top
            rendered_anchor = home_prop.evaluate('e=>{const r=e.getBoundingClientRect(),p=e.parentElement.getBoundingClientRect();return {x:r.x+r.width/2,y:r.bottom,parentLeft:p.left,parentTop:p.top,parentWidth:p.width,parentHeight:p.height,halfWidth:r.width/2};}')
            expected_x = rendered_anchor['parentLeft'] + max(rendered_anchor['halfWidth'], min(rendered_anchor['parentWidth']-rendered_anchor['halfWidth'], new_prop['x']*rendered_anchor['parentWidth']))
            expected_y = rendered_anchor['parentTop'] + max(0,min(1,new_prop['y']))*rendered_anchor['parentHeight']
            assert abs(rendered_anchor['x']-expected_x) <= 1 and abs(rendered_anchor['y']-expected_y) <= 1, rendered_anchor
            assert home_prop.locator('image').get_attribute('href').startswith('data:image/'), 'Home must render the real committed prop artwork'
            choose(frame, 'kitchen', 'decor')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == moved
            page.screenshot(path=str(output/'decoration-preview-apply.png'))
            frame.locator('.decor-footer [data-decor-cancel]').click()
            page.reload()
            frame.wait_for_function('window.KitchenHome&&window.KitchenWorkflows')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == moved
            choose(frame, 'kitchen', 'decor')
            expect(frame.locator('#decorStage [data-item="cup"]')).to_be_visible()
            assert frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")') == new_prop
            passed('decor preview never persists before Apply, Cancel restores placement, Apply changes only the selected prop/theme and reload preserves exact stock and records')
            context.close()
            # Actual paired-photo files and editable manual draft survive Back;
            # explicit registration cancellation discards only the draft.
            context, page, frame = new('widget', 390, 844)
            initial = frame.evaluate('KitchenJournal.getEnvelope()')
            import base64
            tiny_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jrGQAAAAASUVORK5CYII=')

            def photos_to_manual():
                frame.locator('#addFood').click()
                frame.locator('#tray [data-wf="photos"]').click()
                expect(frame.locator('#tray [data-wf="readPhotos"]')).to_be_disabled()
                for index, slot in enumerate(('product','expiry')):
                    frame.locator(f'#tray [data-photo="{slot}"]').set_input_files({'name':slot+'.png','mimeType':'image/png','buffer':tiny_png})
                    expect(frame.locator(f'#tray img[alt="선택한 {"제품 사진" if slot=="product" else "기한 사진"}"]')).to_be_visible()
                    if index == 0:
                        expect(frame.locator('#tray [data-wf="readPhotos"]')).to_be_disabled()
                expect(frame.locator('#tray [data-wf="readPhotos"]')).to_be_enabled()
                frame.locator('#tray [data-wf="manualAdd"]').click()
                form = frame.locator('#addIngredientForm')
                form.locator('[name="name"]').fill('초안 검수 재료')
                form.locator('[name="quantity"]').fill('250g')
                form.locator('[name="expiry"]').fill('2026-11-12')
                reveal(form.locator('[name="picture"]')).select_option('photo')
                return form

            form = photos_to_manual()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            frame.locator('#tray .workflow-nav [data-wf="back"]').click()
            expect(frame.locator('#tray [data-wf="readPhotos"]')).to_be_enabled()
            expect(frame.locator('#tray [data-photo]')).to_have_count(2)
            frame.locator('#tray [data-wf="manualAdd"]').click()
            form = frame.locator('#addIngredientForm')
            expect(form.locator('[name="name"]')).to_have_value('초안 검수 재료')
            expect(form.locator('[name="quantity"]')).to_have_value('250g')
            expect(form.locator('[name="expiry"]')).to_have_value('2026-11-12')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            frame.locator('#tray .workflow-nav [data-wf="cancelRegistration"]').click()
            frame.locator('#tray [data-wf="confirmRegistrationCancel"]').click()
            expect(frame.locator('#tray')).not_to_be_visible()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            form = photos_to_manual()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            form.locator('[type="submit"]').click()
            after_photo = frame.evaluate('KitchenJournal.getEnvelope()')
            registered = [item for item in after_photo['world']['items'] if item['name'] == '초안 검수 재료']
            assert len(registered) == 1
            item = registered[0]
            assert (item['quantity'],item['expiry']) == ('250g','2026-11-12')
            assert item['photoAsIcon'] is True and item['photo'].startswith('data:image/jpeg;base64,') and item['expiryPhoto'].startswith('data:image/jpeg;base64,')
            assert after_photo['play'] == initial['play'] and after_photo['workflow'] == initial['workflow']
            expect(frame.locator('[data-home-tab="fridge"]')).to_have_attribute('aria-selected','true')
            frame.locator('#addFood').click()
            expect(frame.locator('#tray [data-wf="manualAdd"]')).to_be_visible()
            expect(frame.locator('#addIngredientForm')).to_have_count(0)
            assert frame.evaluate('KitchenJournal.getEnvelope()') == after_photo
            frame.locator('#closeTray').click()
            passed('paired real photo files and manual draft survive Back, explicit Cancel never writes stock, and one confirmed save stores one lot with both photos')
            context.close()

            # Controlled reader response tests only the A4 review UI contract.
            # It deliberately makes no claim about OCR recognition accuracy.
            context, page, frame = new('widget', 390, 844, True, device_scale_factor=2)
            initial = frame.evaluate('KitchenJournal.getEnvelope()')
            frame.evaluate('''()=>{window.KitchenPhotoReader={read:async()=>({
                nameCandidates:['OCR UI 후보'],quantityCandidates:['200g'],
                dateCandidates:[{date:'2026-11-20',label:'expiry',raw:'소비기한 2026.11.20'}],
                warnings:[],text:{product:'OCR UI 후보 200g',expiry:'소비기한 2026.11.20'}
            })};}''')
            frame.locator('#addFood').click()
            frame.locator('#tray [data-wf="photos"]').click()
            for slot in ('product','expiry'):
                frame.locator(f'#tray [data-photo="{slot}"]').set_input_files({'name':slot+'.png','mimeType':'image/png','buffer':tiny_png})
                expect(frame.locator(f'#tray img[alt="선택한 {"제품 사진" if slot=="product" else "기한 사진"}"]')).to_be_visible()
            frame.locator('#tray [data-wf="readPhotos"]').click()
            review = frame.locator('#addIngredientForm[data-photo-review="true"]')
            expect(review).to_be_visible()
            expect(review.locator('[name="name"]')).to_have_value('OCR UI 후보')
            expect(review.locator('[name="quantity"]')).to_have_value('200g')
            expect(review.locator('[name="expiry"]')).to_have_value('2026-11-20')
            expect(review.locator('[name="confirmed"]')).not_to_be_checked()
            review.locator('[type="submit"]').click()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            expect(review).to_be_visible()
            expect(frame.locator('#tray .workflow-feedback')).to_contain_text('원본을 확인')
            review.locator('[name="confirmed"]').locator('..').tap()
            expect(review.locator('[name="confirmed"]')).to_be_checked()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            review.locator('[name="name"]').fill('')
            review.locator('[type="submit"]').click()
            expect(frame.locator('#tray .workflow-feedback')).to_contain_text('재료 이름')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            review.locator('[name="name"]').fill('직접 검수한 재료')
            review.locator('[name="quantity"]').fill('225g')
            review.locator('[name="expiry"]').fill('2026-11-21')
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(output/'a4-controlled-result-ui-fixture-390x844.png'))
            page.set_viewport_size({'width':320,'height':568})
            for change_photo in (False, True):
                review.locator('[name="confirmed"]').check()
                frame.locator('#tray .workflow-nav [data-wf="back"]').click()
                expect(frame.locator('#tray [data-wf="readPhotos"]')).to_be_enabled()
                if change_photo:
                    frame.locator('#tray [data-photo="expiry"]').set_input_files({'name':'revised-expiry.png','mimeType':'image/png','buffer':tiny_png})
                    expect(frame.locator('#tray img[alt="선택한 기한 사진"]')).to_be_visible()
                frame.locator('#tray [data-wf="readPhotos"]').click()
                review = frame.locator('#addIngredientForm[data-photo-review="true"]')
                expect(review.locator('[name="confirmed"]')).not_to_be_checked()
                for name, value in {'name':'직접 검수한 재료','quantity':'225g','expiry':'2026-11-21'}.items():
                    expect(review.locator(f'[name="{name}"]')).to_have_value(value)
                assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            review.locator('[name="confirmed"]').check()
            review.locator('[type="submit"]').click()
            committed = frame.evaluate('KitchenJournal.getEnvelope()')
            lots = [item for item in committed['world']['items'] if item['name']=='직접 검수한 재료']
            assert len(lots)==1 and (lots[0]['quantity'],lots[0]['expiry'])==('225g','2026-11-21')
            assert len(committed['world']['items'])==len(initial['world']['items'])+1
            assert committed['play']==initial['play'] and committed['workflow']==initial['workflow']
            expect(frame.locator('#tray')).not_to_be_visible()
            frame.locator('#addFood').click()
            expect(frame.locator('#tray [data-wf="photos"]')).to_be_visible()
            expect(frame.locator('#addIngredientForm')).to_have_count(0)
            assert frame.evaluate('KitchenJournal.getEnvelope()') == committed
            passed('controlled OCR-result UI only, opaque touch DSF2: A4 blocks unchecked/empty-name saves inline, one label tap recovers, edits survive reread and exactly one save commits')
            context.close()

            # A long list returns to its exact kind/location and scroll position.
            many_world = json.loads(json.dumps(legacy_world))
            template = next(item for item in many_world['items'] if item['id'] == 'egg')
            for index in range(25):
                lot = {**template, 'id':f'qa-food-{index}', 'name':f'보관 재료 {index:02d}', 'quantity':'1개',
                       'expiry':'2026-12-10','zone':'counter','x':.5,'y':.7,'z':60+index}
                many_world['items'].append(lot)
            many_world['layer'] = 100
            many_world['serial'] = 2000
            many_raw = json.dumps({'version':1,'world':many_world,'play':legacy_play},ensure_ascii=False)
            context, page, frame = new('widget',390,844,init='if(localStorage.getItem("miniature-kitchen-preview-v1")===null)localStorage.setItem("miniature-kitchen-preview-v1",'+json.dumps(many_raw)+')')
            initial = frame.evaluate('KitchenJournal.getEnvelope()')
            frame.locator('.header-actions [data-workflow="inventory"]').click()
            frame.locator('#tray [data-wf="inventoryKind"][data-arg="food"]').click()
            frame.locator('#inventoryZone').select_option('outside')
            expected = sorted(item['id'] for item in many_world['items'] if item['kind']=='food' and item['zone'] in ['seasoning','counter'])
            assert sorted(frame.locator('#tray .inventory-row').evaluate_all('els=>els.map(e=>e.dataset.arg)')) == expected
            last = frame.locator('#tray .inventory-row').last
            lot_id = last.get_attribute('data-arg')
            last.scroll_into_view_if_needed()
            scroll_metrics = '''e=>{for(let p=e.parentElement;p;p=p.parentElement){const c=getComputedStyle(p);if(/auto|scroll/.test(c.overflowY)&&p.scrollHeight>p.clientHeight+1)return {top:p.scrollTop,height:p.scrollHeight,client:p.clientHeight};}return {top:scrollY,height:document.documentElement.scrollHeight,client:innerHeight};}'''
            before_scroll = last.evaluate(scroll_metrics)
            assert before_scroll['top'] > 0, before_scroll
            last.click()
            expect(frame.locator('#ingredientForm [name="zone"]')).to_have_value('counter')
            frame.locator('#closeTray').click()
            expect(frame.locator('#inventoryZone')).to_have_value('outside')
            expect(frame.locator('#tray [data-wf="inventoryKind"][data-arg="food"]')).to_have_attribute('aria-pressed','true')
            restored_scroll = frame.locator(f'#tray .inventory-row[data-arg="{lot_id}"]').evaluate(scroll_metrics)
            assert abs(restored_scroll['top']-before_scroll['top']) <= 2,(before_scroll,restored_scroll)
            assert frame.evaluate('KitchenJournal.getEnvelope()') == initial
            frame.locator(f'#tray .inventory-row[data-arg="{lot_id}"]').click()
            form = frame.locator('#ingredientForm')
            form.locator('[name="quantity"]').fill('2개')
            form.locator('[type="submit"]').click()
            expect(frame.locator('#inventoryZone')).to_have_value('outside')
            expect(frame.locator('#tray [data-wf="inventoryKind"][data-arg="food"]')).to_have_attribute('aria-pressed','true')
            saved_scroll = frame.locator(f'#tray .inventory-row[data-arg="{lot_id}"]').evaluate(scroll_metrics)
            assert abs(saved_scroll['top']-before_scroll['top']) <= 2,(before_scroll,saved_scroll)
            changed = frame.evaluate('KitchenJournal.getEnvelope()')
            changed_lot = next(item for item in changed['world']['items'] if item['id']==lot_id)
            original_lot = next(item for item in initial['world']['items'] if item['id']==lot_id)
            assert changed_lot['quantity']=='2개' and all(changed_lot[key]==original_lot[key] for key in ['zone','x','y','z','expiry'])
            assert [item for item in changed['world']['items'] if item['id']!=lot_id] == [item for item in initial['world']['items'] if item['id']!=lot_id]
            assert changed['play']==initial['play'] and changed['workflow']==initial['workflow']
            passed('long inventory retains real kind/location and exact scroll on detail close, then saves only the explicitly edited outside lot')
            context.close()

            # An explicitly simulated concurrent stock update and a real reward
            # purchase must survive cancellation of an unrelated prop draft.
            reward_play = json.loads(json.dumps(legacy_play))
            reward_play['discovered'] = ['recipe-1']
            reward_play['awarded'] = ['recipe-1']
            concurrent_raw = json.dumps({'version':1,'world':legacy_world,'play':reward_play},ensure_ascii=False)
            context, page, frame = new('app',390,844,init='if(localStorage.getItem("miniature-kitchen-preview-v1")===null)localStorage.setItem("miniature-kitchen-preview-v1",'+json.dumps(concurrent_raw)+')')
            choose(frame,'kitchen','decor')
            original = frame.evaluate('KitchenJournal.getEnvelope()')
            draft_prop = drag_prop(page,frame)
            assert frame.evaluate('KitchenJournal.getEnvelope()') == original
            frame.evaluate('''()=>KitchenJournal.transact(({world:w})=>{const item=w.items.find(i=>i.id==='egg');item.quantity='7개';item.expiry='2026-12-02';item.manualRevision=(item.manualRevision||0)+1;})''')
            latest_food = frame.evaluate('KitchenJournal.getEnvelope()')
            assert next(item for item in latest_food['world']['items'] if item['id']=='egg')['quantity']=='7개'
            assert frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")') == draft_prop
            frame.locator('#homeDecor .decor-actions').get_by_role('button',name='배경',exact=True).click()
            frame.locator('#tray [data-wf="rewards"]').click()
            frame.locator('#tray [data-reward="tile"]').click()
            latest = frame.evaluate('KitchenJournal.getEnvelope()')
            assert latest['play']['owned']==['tile']
            assert frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")') == draft_prop
            for _ in range(8):
                if not frame.locator('#tray').is_visible():break
                frame.locator('#closeTray').click()
            frame.locator('.decor-footer [data-decor-cancel]').click()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == latest
            assert next(item for item in latest['world']['items'] if item['id']=='cup') == next(item for item in original['world']['items'] if item['id']=='cup')
            choose(frame,'kitchen','decor')
            assert frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")') == next(item for item in original['world']['items'] if item['id']=='cup')
            passed('cancelled decoration preserves a later explicit stock update and a real acquired reward while discarding only preview placement')
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
