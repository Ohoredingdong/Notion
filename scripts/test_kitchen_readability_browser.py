#!/usr/bin/env python3
"""Verify the readable kitchen redesign using generated app/widget pages.

This runs synthetic, local browser profiles only. It does not touch production
records, contact OCR/nutrition providers, or claim physical-device coverage.
"""
import argparse
import functools
import json
import re
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
    parser.add_argument('--root', type=Path, required=True,
                        help='Generated previews directory, including mobile/*.html')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-executable', default='/usr/bin/chromium')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root, out = args.root.resolve(), args.output.resolve()
    if out.is_relative_to(repo) or out == root:
        raise SystemExit('Keep browser evidence outside the checkout and source directory')
    for mode in ('app', 'widget'):
        for path in (root/f'miniature-kitchen-{mode}.html', root/'mobile'/f'{mode}.html'):
            if not path.is_file():
                raise SystemExit(f'Missing generated page: {path}')
    out.mkdir(parents=True, exist_ok=True)
    report = {
        'scope': 'Local generated HTML, synthetic native and opaque mobile Chromium profiles; no physical-device, Safari or Notion claim',
        'passed': [], 'failures': [], 'layouts': [],
    }
    errors = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    day = '2026-11-01'
    original_keys = ['use-me-first-state-v5', 'use-me-first-v4', 'use-me-first-life-v1',
                     'use-me-first-kitchen-view-v1', 'umf-seasoning-layout-v3']

    def passed(message):
        report['passed'].append(message)
        print('PASS '+message, flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser_executable, args=['--no-sandbox'])

        def new(mode='app', width=390, height=844, opaque=False, motion='reduce', init=None):
            context = browser.new_context(viewport={'width': width, 'height': height},
                                          timezone_id='Asia/Seoul', reduced_motion=motion,
                                          has_touch=opaque, is_mobile=opaque)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.clock.install(time=datetime.fromisoformat(day+'T03:00:00+00:00'))
            if init:
                page.add_init_script(init)
            page.goto(origin+(f'/mobile/{mode}.html' if opaque else f'/miniature-kitchen-{mode}.html'))
            if opaque:
                wrapper = page.locator('iframe[sandbox]')
                expect(wrapper).to_be_attached()
                grants = (wrapper.get_attribute('sandbox') or '').split()
                assert 'allow-scripts' in grants and 'allow-forms' in grants
                assert 'allow-same-origin' not in grants
                frame = wrapper.element_handle().content_frame()
            else:
                frame = page
            frame.wait_for_function('window.MiniKitchen && window.KitchenJournal && window.KitchenWorkflows')
            return context, page, frame

        def in_view_actions(frame):
            result = frame.evaluate('''() => {
                return ['addFood','recipes','openRecords'].map(id=>{
                    const e=document.getElementById(id),r=e.getBoundingClientRect();
                    const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                    return {id,x:r.x,y:r.y,width:r.width,height:r.height,
                        visible:r.width>0&&r.height>0&&r.left>=-1&&r.right<=innerWidth+1&&r.top>=-1&&r.bottom<=innerHeight+1,
                        uncovered:hit?.closest('button')===e};
                });
            }''')
            assert all(row['visible'] and row['uncovered'] and row['height'] >= 44 for row in result), result
            return result

        def no_macro_clipping(frame):
            clipped = frame.evaluate('''() => {
                const bad=[];
                for(const cell of document.querySelectorAll('[data-balance]')){
                    const outer=cell.getBoundingClientRect();
                    if(cell.scrollWidth>cell.clientWidth+1)bad.push({key:cell.dataset.balance,type:'cell overflow'});
                    for(const text of cell.querySelectorAll('strong,.balance-number>span,.balance-percent,.balance-status')){
                        const range=new Range();range.selectNodeContents(text);
                        for(const r of range.getClientRects())if(r.width>0&&(r.left<outer.left-1||r.right>outer.right+1))
                            bad.push({key:cell.dataset.balance,type:'text clipped',text:text.textContent});
                    }
                }
                return bad;
            }''')
            assert not clipped, clipped

        def tap_door(page, frame, key, touch=False):
            door = frame.locator(f'[data-door="{key}"]')
            door.scroll_into_view_if_needed()
            # Use an actual visible door-surface point, excluding separately
            # interactive condiment art and unrelated overlay controls.
            point = door.evaluate('''e=>{
                const r=e.getBoundingClientRect();
                for(const fy of [.12,.2,.8,.9,.5])for(const fx of [.12,.2,.8,.9,.5]){
                    const x=r.x+r.width*fx,y=r.y+r.height*fy;
                    if(x<1||y<1||x>=innerWidth-1||y>=innerHeight-1)continue;
                    if(document.elementFromPoint(x,y)?.closest('[data-door]')===e)return {x,y};
                }
                return null;
            }''')
            assert point, 'No reachable surface on '+key
            if frame != page:
                offset = frame.frame_element().bounding_box()
                point = {'x': point['x']+offset['x'], 'y': point['y']+offset['y']}
            (page.touchscreen.tap if touch else page.mouse.click)(point['x'], point['y'])

        def check_doors(page, frame, touch=False):
            before = frame.evaluate('MiniKitchen.getSnapshot().doors')
            assert len(before) == 4
            for key in ('freshLeft', 'freshRight', 'frozenLeft', 'frozenRight'):
                expected = dict(before)
                expected[key] = not before[key]
                tap_door(page, frame, key, touch)
                frame.wait_for_function('(expected)=>{const actual=MiniKitchen.getSnapshot().doors;return Object.keys(actual).length===4&&Object.entries(expected).every(([k,v])=>actual[k]===v)}', arg=expected)
                tap_door(page, frame, key, touch)
                frame.wait_for_function('(expected)=>{const actual=MiniKitchen.getSnapshot().doors;return Object.keys(actual).length===4&&Object.entries(expected).every(([k,v])=>actual[k]===v)}', arg=before)

        def show(frame, route):
            frame.evaluate('route=>KitchenWorkflows.show(route)', route)
            expect(frame.locator('#tray')).to_be_visible()

        try:
            profiles = [('app', 320, 660, False), ('app', 390, 844, False), ('app', 1120, 1000, False),
                        ('widget', 320, 660, False), ('widget', 390, 844, False),
                        ('app', 320, 660, True), ('widget', 320, 660, True),
                        ('app', 390, 844, True), ('widget', 390, 844, True)]
            for mode, width, height, opaque in profiles:
                context, page, frame = new(mode, width, height, opaque)
                assert frame.locator('body').get_attribute('data-mode') == mode
                assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
                expect(frame.locator('[data-balance]')).to_have_count(3)
                assert frame.locator('.balance-empty').inner_text().strip()
                for key in ('carb', 'protein', 'fat'):
                    value = frame.locator(f'[data-balance="{key}"] strong')
                    expect(value).to_be_visible()
                    expect(frame.locator(f'[data-balance="{key}"] .balance-number>span')).to_be_visible()
                    current = value.inner_text()
                    assert re.sub(r'\s+', '', current) == '—g', current
                    assert '%' not in frame.locator(f'[data-balance="{key}"] .balance-percent').inner_text()
                no_macro_clipping(frame)
                sizes = frame.locator('[data-balance] strong').evaluate_all('''nodes=>nodes.map(e=>{
                    const r=e.getBoundingClientRect();return parseFloat(getComputedStyle(e).fontSize)*(r.height/(e.offsetHeight||r.height));
                })''')
                assert all(size >= 19.5 for size in sizes), sizes  # Native-size 20px core values, allowing subpixel rounding.
                actions = in_view_actions(frame)
                frame.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
                in_view_actions(frame)
                frame.evaluate('window.scrollTo(0,0)')
                check_doors(page, frame, opaque)
                frame.evaluate('window.scrollTo(0,0)')
                frame.locator('#recipes').click()
                expect(frame.locator('#tray .recipe-filters')).to_be_visible()
                assert frame.locator('#tray .recipe-filters').get_attribute('open') is None
                recipe_cards = frame.locator('#tray [data-wf="recipe"]')
                assert recipe_cards.count() == frame.evaluate('KitchenCatalog.length') == 8
                first = recipe_cards.first.bounding_box()
                assert first and first['y'] >= 0 and first['y']+min(first['height'], 44) <= height, first
                frame.locator('#closeTray').click()
                frame.locator('#openRecords').click()
                expect(frame.locator('#openRecords')).to_have_attribute('aria-selected', 'true')
                expect(frame.locator('#panel-records [data-workflow="nutrition"]')).to_be_visible()
                expect(frame.locator('#panel-records [data-workflow="hub"]')).to_be_visible()
                frame.locator('.home-shortcuts [data-home-tab="fridge"]').click()
                page.screenshot(path=str(out/(f'{mode}-{width}-'+('opaque' if opaque else 'native')+'.png')), full_page=True)
                report['layouts'].append({'mode': mode, 'viewport': [width, height], 'opaque': opaque, 'primary_actions': actions})
                passed(f'{mode} {width}x{height} '+('opaque touch' if opaque else 'native')+': reachable primary actions, unclipped empty macros, real independent doors and recipes before filters')
                context.close()

            context, page, frame = new()
            frame.evaluate('(keys)=>keys.forEach((k,i)=>localStorage.setItem(k,"보존할 원래 기록 "+i))', original_keys)
            frame.locator('#dailyBalance').click()
            frame.locator('#tray [data-wf="targets"],#tray [data-workflow="targets"]').first.click()
            form = frame.locator('[data-wf-form="targets"]')
            expect(form).to_be_visible()
            assert frame.locator('#journalExport').count() == 0 or not frame.locator('#journalExport').is_visible()
            for name, value in [('carb', '230'), ('protein', '70'), ('fat', '60')]:
                form.locator(f'[name="{name}"]').fill(value)
            form.locator('details.target-extras summary').click()
            form.locator('[name="calcium"]').fill('700')
            form.locator('[type="submit"]').click()
            assert frame.evaluate('KitchenJournal.getSnapshot().targets.carb') == 230
            assert frame.evaluate('KitchenJournal.getWorkflow().extraTargets.calcium') == 700
            frame.evaluate('MiniKitchen.closeTray()')
            passed('nutrition opens a dedicated goal form before backup tools and saves core/optional goals')

            # Only test fixtures use direct setup; the entered values are not
            # seeded into product defaults or represented as actual user data.
            frame.evaluate('''() => KitchenJournal.transact(({play:p})=>{
                p.record({day:'2026-11-01',name:'직접 입력 검사',portion:'1회',recipeId:null,nutrients:{kcal:null,carb:160,protein:45,fat:20,fiber:null,water:null}});
                p.record({day:'2026-11-01',name:'미입력 검사',portion:'1회',recipeId:null,nutrients:{kcal:null,carb:null,protein:null,fat:null,fiber:null,water:null}});
            })''')
            for key, value, target in [('carb', 160, 230), ('protein', 45, 70), ('fat', 20, 60)]:
                cell = frame.locator(f'[data-balance="{key}"]')
                assert re.sub(r'\s+', '', cell.locator('strong').inner_text()) == str(value)+'g'
                expect(cell.locator('.balance-number>span')).to_have_text(f'({target}g)')
                percent = cell.locator('.balance-percent').inner_text()
                match = re.search(r'([\d.,]+)\s*%', percent)
                assert match and abs(float(match[1].replace(',', ''))-value/target*100) <= 1, percent
                expect(cell.locator('.balance-status')).to_contain_text('1끼 미입력')
            no_macro_clipping(frame)
            expect(frame.locator('.balance-empty')).to_have_count(0)
            page.screenshot(path=str(out/'entered-macros.png'))
            passed('entered current/target grams and truthful percentages are visible; partial records remain explicit')

            frame.evaluate('''() => KitchenJournal.transact(({play:p})=>{
                for(const m of p.state().meals)p.remove(m.id);
                p.record({day:'2026-11-01',name:'목표 초과 검사',portion:'1회',recipeId:null,nutrients:{kcal:null,carb:300,protein:0,fat:null,fiber:null,water:null}});
            })''')
            percent = frame.locator('[data-balance="carb"] .balance-percent').inner_text()
            assert float(re.search(r'([\d.,]+)\s*%', percent)[1].replace(',', '')) > 100, percent
            progress = frame.locator('[data-balance="carb"] [role="progressbar"]')
            assert float(progress.get_attribute('aria-valuenow')) == 100
            assert re.sub(r'\s+', '', frame.locator('[data-balance="protein"] strong').inner_text()) == '0g'
            assert re.sub(r'\s+', '', frame.locator('[data-balance="fat"] strong').inner_text()) == '—g'
            passed('over-target intake stays over 100%; known zero and missing intake remain distinct')

            assert frame.evaluate('(keys)=>keys.every((k,i)=>localStorage.getItem(k)==="보존할 원래 기록 "+i)', original_keys)
            context.close()
            for width in (320, 390):
                context, page, frame = new(width=width, height=660 if width == 320 else 844)
                frame.evaluate('''() => KitchenJournal.transact(({play:p})=>{
                    p.setTargets({kcal:null,carb:100000,protein:70,fat:60,fiber:null,water:null});
                    p.record({day:'2026-11-01',name:'지원 경계값 검사',portion:'검사',recipeId:null,nutrients:{kcal:null,carb:100000,protein:0,fat:null,fiber:null,water:null}});
                })''')
                no_macro_clipping(frame)
                assert re.sub(r'\s+', '', frame.locator('[data-balance="carb"] strong').inner_text()) == '100,000g'
                assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
                passed(f'{width}px supported large entered values fit without clipping')
                context.close()

            context, page, frame = new()
            frame.evaluate('(keys)=>keys.forEach((k,i)=>localStorage.setItem(k,"보존할 원래 기록 "+i))', original_keys)
            frame.locator('[data-item="egg"]').click()
            form = frame.locator('#ingredientForm')
            expect(form).to_be_visible()
            form.locator('[name="quantity"]').fill('8개')
            form.locator('[name="expiry"]').fill('2026-11-12')
            form.locator('[name="opened"]').fill('2026-11-01')
            form.locator('[type="submit"]').click()
            egg = frame.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="egg")')
            assert (egg['quantity'], egg['expiry'], egg['opened']) == ('8개', '2026-11-12', day)
            expect(frame.locator('#kitchenProgress>span')).to_contain_text('계란')
            expect(frame.locator('#selectedItemMeta')).to_contain_text('8개')
            expect(frame.locator('#selectedItemMeta')).to_contain_text('2026-11-12')
            assert frame.locator('#selectedItemMeta').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)') >= 14
            source, target = frame.locator('[data-item="egg"]').bounding_box(), frame.locator('.fridge-interiors [data-zone="freshRight"]').bounding_box()
            page.mouse.move(source['x']+source['width']/2, source['y']+source['height']/2)
            page.mouse.down()
            page.mouse.move(target['x']+target['width']*.5, target['y']+target['height']*.75, steps=16)
            page.mouse.up()
            moved = frame.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="egg")')
            assert moved['zone'] == 'freshRight' and moved['quantity'] == '8개' and moved['expiry'] == '2026-11-12'
            assert frame.evaluate('(keys)=>keys.every((k,i)=>localStorage.getItem(k)==="보존할 원래 기록 "+i)', original_keys)
            before_reload = frame.evaluate('KitchenJournal.getEnvelope()')
            page.reload()
            frame.wait_for_function('window.KitchenWorkflows')
            assert frame.evaluate('KitchenJournal.getEnvelope()') == before_reload
            passed('native ingredient edit, readable full metadata, drag and reload preserve exact values and all original app keys')
            context.close()

            # A new fixed dock must never become a geometric shelf drop target.
            context, page, frame = new(width=320, height=660)
            before_drop = frame.evaluate('MiniKitchen.exportWorld()')
            for fraction in (.5, .25):
                frame.evaluate('window.scrollTo(0,0)')
                source = frame.locator('[data-item="egg"]').bounding_box()
                dock = frame.locator('#recipes').bounding_box()
                x, y = dock['x']+dock['width']*fraction, dock['y']+dock['height']/2
                assert frame.evaluate('p=>document.elementFromPoint(p.x,p.y)?.closest("button")?.id', {'x':x,'y':y}) == 'recipes'
                page.mouse.move(source['x']+source['width']/2, source['y']+source['height']/2)
                page.mouse.down()
                page.mouse.move(x, y, steps=16)
                page.mouse.up()
                assert frame.evaluate('MiniKitchen.exportWorld()') == before_drop
                assert not frame.locator('#tray').is_visible()
                expect(frame.locator('.ghost,.item.is-dragging')).to_have_count(0)
            passed('drag onto the fixed recipe dock cancels without stock changes, opening a dialog or leaving a ghost')
            context.close()

            # Existing schemas allow long names and an unparsed quantity; native
            # details keep every character while compact scene glyphs may clip.
            long_name = ('VeryLongIngredient직접입력한식재료'*5)[:100]
            long_quantity = ('남은한봉지UNKNOWNQUANTITY확인필요'*6)[:80]
            context, page, frame = new(width=320, height=660)
            frame.evaluate('''data=>KitchenJournal.transact(({world:w})=>{
                const item=w.items.find(i=>i.id==='egg');item.name=data.name;item.quantity=data.quantity;item.expiry='2026-11-12';
            })''', {'name':long_name,'quantity':long_quantity})
            frame.locator('[data-item="egg"]').click()
            expect(frame.locator('#trayTitle')).to_have_text(long_name)
            form = frame.locator('#ingredientForm')
            assert form.locator('[name="name"]').input_value() == long_name
            assert form.locator('[name="quantity"]').input_value() == long_quantity
            assert frame.evaluate('''()=>{
                const dialog=document.querySelector('#tray'),content=document.querySelector('#trayContent');
                return document.documentElement.scrollWidth<=innerWidth&&dialog.scrollWidth<=dialog.clientWidth+1&&content.scrollWidth<=content.clientWidth+1;
            }''')
            page.screenshot(path=str(out/'long-ingredient-detail.png'))
            form.locator('[type="submit"]').click()
            expect(frame.locator('#kitchenProgress>span')).to_have_text(long_name)
            expect(frame.locator('#selectedItemMeta')).to_contain_text(long_quantity)
            assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
            full_item = frame.evaluate('KitchenJournal.getEnvelope().world.items.find(i=>i.id==="egg")')
            assert full_item['name'] == long_name and full_item['quantity'] == long_quantity
            page.screenshot(path=str(out/'long-ingredient-tray.png'), full_page=True)
            passed('320px long valid name and unknown quantity stay exact in the detail, native tray and saved envelope without horizontal overflow')
            context.close()

            for mode in ('app', 'widget'):
                context, page, frame = new(mode, 320, 660, True)
                frame.locator('[data-item="spice0"]').tap()
                form = frame.locator('#ingredientForm')
                expect(form).to_be_visible()
                # Touch completion can dispatch a compatibility click after the
                # pointerup opens/repositions the dialog. It must stay on this
                # ingredient rather than activating a newly placed recipe CTA.
                frame.wait_for_timeout(350)
                expect(form).to_be_visible()
                form.locator('[name="quantity"]').fill('175ml')
                form.locator('[name="expiry"]').fill('2027-03-01')
                form.locator('[name="opened"]').fill(day)
                form.locator('[type="submit"]').tap()
                frame.wait_for_function('!document.querySelector("#tray").open')
                spice = frame.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="spice0")')
                assert (spice['quantity'], spice['expiry'], spice['opened']) == ('175ml', '2027-03-01', day)
                assert frame.evaluate('KitchenJournal.status') == 'temporary'
                expect(frame.locator('[data-item="spice0"]')).to_be_focused()
                passed(mode+' built opaque mobile wrapper saves exact condiment data using real touch and returns focus')
                context.close()

            context, page, frame = new(motion='no-preference')
            frame.evaluate('''() => {const w=MiniKitchen.exportWorld();w.doors.freshLeft=false;MiniKitchen.restoreWorld(w);
                for(const a of document.querySelector('[data-door="freshLeft"]').getAnimations())a.finish();}''')
            frame.locator('[data-door="freshLeft"]').evaluate('''e=>{
                e.click();const animations=e.getAnimations();
                if(!animations.length)throw new Error('Expected the actual opening transition');
                for(const a of animations){a.pause();a.currentTime=0;}
            }''')
            frame.locator('[data-item="egg"]').scroll_into_view_if_needed()
            hit = frame.evaluate('''() => {
                const r=document.querySelector('[data-item="egg"]').getBoundingClientRect(),e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                return {door:e?.closest('[data-door]')?.dataset.door||null,item:e?.closest('[data-item]')?.dataset.item||null};
            }''')
            assert hit == {'door': 'freshLeft', 'item': None}, hit
            passed('food remains behind the front door at the opening identity frame')
            context.close()

            context, page, frame = new()
            frame.locator('[data-home-tab="kitchen"]').click()
            frame.locator('[data-home-subtab="growth"]').click()
            expect(frame.locator('#homeGrowth')).to_be_visible()
            before = frame.evaluate('KitchenJournal.getSnapshot()')
            frame.evaluate('''() => KitchenJournal.transact(({play:p})=>{
                p.record({day:'2026-11-01',name:'도감 진행 검사',portion:'1회',recipeId:'recipe-1',nutrients:{kcal:null,carb:null,protein:null,fat:null,fiber:null,water:null}});
                p.buy('tile');p.equip('frozenLeft','tile');
            })''')
            current = frame.evaluate('KitchenJournal.getSnapshot()')
            assert before['owned'] == [] and current['owned'] == ['tile']
            expect(frame.locator('#homeGrowth')).to_contain_text('세라믹 타일')
            goal = frame.evaluate('KitchenJournal.summary().goal')
            progress = frame.locator('#homeGrowth [role="progressbar"]')
            assert float(progress.get_attribute('aria-valuenow')) == goal['value']
            assert float(progress.get_attribute('aria-valuemax')) == goal['target']
            frame.locator('[data-home-tab="fridge"]').click()
            expect(frame.locator('.fridge-charm.is-interior[data-charm="tile"]')).to_be_visible()
            assert all(frame.evaluate('MiniKitchen.getSnapshot().doors').values())
            page.screenshot(path=str(out/'earned-open-kitchen.png'), full_page=True)
            passed('actual collection progress and owned reward are visible in their tab; equipped interior charm and all four open doors persist in the fridge tab')
            context.close()

            legacy_world = json.loads((repo/'tests/fixtures/miniature-legacy-world-v1.json').read_text())
            legacy_world['items'][0].update(expiry='2000-01-01', quantity='125ml', x=.173, y=.743)
            legacy_play = {'version': 1, 'meals': [], 'targets': {k: None for k in ('kcal','carb','protein','fat','fiber','water')},
                           'discovered': [], 'awarded': [], 'owned': [], 'equipped': {'frozenLeft': None, 'frozenRight': None},
                           'goal': 'collection', 'plateLabel': '우리 집 부엌'}
            raw = json.dumps({'version': 1, 'world': legacy_world, 'play': legacy_play, 'legacyAudit': 'keep'}, ensure_ascii=False)
            init = 'localStorage.setItem("miniature-kitchen-preview-v1",'+json.dumps(raw)+')'
            context, page, frame = new(init=init)
            assert frame.evaluate('MiniKitchen.exportWorld()') == legacy_world
            assert frame.evaluate('KitchenJournal.getSnapshot()') == legacy_play
            assert frame.evaluate('KitchenJournal.getEnvelope().legacyAudit') == 'keep'
            passed('legacy version-1 stock, expired dates, quantities, exact coordinates and unknown envelope fields are preserved')
            context.close()
            assert not errors, errors
            passed('no JavaScript exceptions across all exercised redesigned pages')
        except Exception as error:
            report['failures'].append({'message': str(error), 'trace': traceback.format_exc()})
            try:
                page.screenshot(path=str(out/'failure.png'), full_page=True)
            except Exception:
                pass
            raise
        finally:
            report['javascript_errors'] = errors
            (out/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            browser.close()
            server.shutdown()
    print(json.dumps({'passed': len(report['passed']), 'failed': len(report['failures'])}))


if __name__ == '__main__':
    main()
