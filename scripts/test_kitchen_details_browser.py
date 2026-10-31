#!/usr/bin/env python3
"""Verify the kitchen detail pass using generated pages and actual gestures/forms."""
import argparse
import functools
import json
import threading
import traceback
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, help='Optional before-capture folder with matching state JSON')
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):
        raise SystemExit('Keep output outside the checkout')
    out.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    report = {'scope': 'Generated preview only; Chromium desktop/mobile profiles, not physical devices', 'passed': [], 'failures': []}
    errors = []
    def passed(message):
        report['passed'].append(message)
        print('PASS ' + message, flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        def new(mode='app', width=390, height=844, opaque=False):
            context = browser.new_context(viewport={'width': width, 'height': height}, reduced_motion='reduce', timezone_id='Asia/Seoul', has_touch=opaque, is_mobile=opaque)
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.clock.install(time=datetime.fromisoformat('2026-11-01T03:00:00+00:00'))
            page.goto(origin + (f'/mobile/{mode}.html' if opaque else f'/miniature-kitchen-{mode}.html'))
            frame = page.frames[1] if opaque else page
            frame.wait_for_function('window.KitchenWorkflows && window.KitchenJournal')
            return context, page, frame
        try:
            for mode, width, height in [('app', 320, 660), ('app', 390, 844), ('app', 1120, 1000), ('widget', 320, 660), ('widget', 390, 844), ('widget', 1120, 1000)]:
                context, page, frame = new(mode, width, height)
                assert frame.locator('body').get_attribute('data-mode') == mode
                assert not frame.evaluate('document.documentElement.scrollWidth > innerWidth')
                assert frame.evaluate('MiniKitchen.getSnapshot().selected') is None
                # Existing warm room, centered cabinet and all stock/expiry/coordinates are preserved.
                room, cabinet = frame.locator('.room').bounding_box(), frame.locator('.cabinet').bounding_box()
                assert abs((cabinet['x'] + cabinet['width']/2) - (room['x'] + room['width']/2)) < 2
                if args.baseline:
                    before = json.loads((args.baseline/f'{mode}-{width}-state.json').read_text())
                    assert frame.evaluate('KitchenJournal.getEnvelope()') == before
                if width == 1120:
                    assert frame.locator('#desktopSummary').is_visible() == (mode == 'app')
                    if mode == 'widget':
                        assert room['width'] > 700  # No desktop sidebar shrinking a wide widget.
                assert frame.evaluate('''() => [...document.querySelectorAll('.worktop-actions button')].every(b=>{
                    const text=[...b.childNodes].find(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim());
                    const r=new Range();r.selectNode(text);return r.getClientRects().length===1;
                })''')
                # Default label names are readable; full user names remain in the accessible label/editor.
                for item in ['broccoli', 'mushroom', 'mixveg']:
                    name = frame.locator(f'.shelf-label[data-for-item="{item}"] b')
                    assert name.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                # Painted labels must remain above neighboring images; enable hit testing only for this probe.
                occluded = frame.evaluate('''() => {
                    const failures=[];
                    for(const label of document.querySelectorAll('.shelf-label')){
                        label.scrollIntoView({block:'nearest',behavior:'instant'});
                        const r=label.getBoundingClientRect(),old=label.style.pointerEvents;label.style.pointerEvents='auto';
                        const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height-2);label.style.pointerEvents=old;
                        if(hit?.closest('.shelf-label')!==label)failures.push({id:label.dataset.forItem,y:r.y,hit:hit?.tagName});
                    }
                    window.scrollTo({top:0,behavior:'instant'});return failures;
                }''')
                assert not occluded, occluded
                frame.locator('#dailyBalance').click()
                expect(frame.locator('#tray .workflow-nav')).to_have_count(1)
                expect(frame.locator('#tray .journal-tabs')).to_have_count(0)
                expect(frame.locator('#tray .workflow-nav [aria-current="page"]')).to_have_text('기록')
                # Actual keyboard close returns to the triggering control.
                page.keyboard.press('Escape')
                expect(frame.locator('#dailyBalance')).to_be_focused()
                page.screenshot(path=str(out/f'{mode}-{width}-home.png'), full_page=True)
                passed(f'{mode} {width}: centered room, preserved data, readable labels/buttons and one navigation bar')
                context.close()
            # Expiry filters use the exact same active non-zero batches as the home counts.
            context, page, frame = new()
            frame.evaluate('''() => KitchenJournal.transact(({world:w})=>{
                const egg=w.items.find(i=>i.id==='egg');egg.expiry='2026-11-01';
                const milk=w.items.find(i=>i.id==='milk');milk.expiry='2026-11-01';milk.quantity='0ml';
                const tofu=w.items.find(i=>i.id==='tofu');tofu.expiry='2026-11-01';tofu.depleted=true;
                const tomato=w.items.find(i=>i.id==='tomato');tomato.expiry='2026-10-31';
            })''')
            before = frame.evaluate('KitchenJournal.getEnvelope()')
            for group in ['today', 'overdue', 'soon']:
                control = frame.locator(f'#expirySummary [data-arg="{group}"]')
                count = int(control.locator('b').inner_text())
                control.click()
                expect(frame.locator('#tray [data-wf="item"]')).to_have_count(count)
                expect(frame.locator('.current-filter')).to_contain_text(f'{count}개 묶음')
                frame.locator('[data-wf="inventoryReset"]').click()
                expect(frame.locator('.current-filter')).to_have_count(0)
                frame.locator('#closeTray').click()
            assert frame.evaluate('KitchenJournal.getEnvelope()') == before
            passed('home expiry chips filter matching batches without modifying any record')
            # Partial records must be marked on the home, not presented as complete intake.
            frame.evaluate('''() => KitchenJournal.transact(({play:p})=>{
                p.setTargets({kcal:null,carb:230,protein:70,fat:60,fiber:null,water:null});
                p.record({day:'2026-11-01',name:'직접 입력 식사',portion:'1회',recipeId:null,nutrients:{kcal:null,carb:160,protein:45,fat:20,fiber:null,water:null}});
                p.record({day:'2026-11-01',name:'미입력 식사',portion:'1회',recipeId:null,nutrients:{kcal:null,carb:null,protein:null,fat:null,fiber:null,water:null}});
            })''')
            for key, value, target in [('carb','160','230'),('protein','45','70'),('fat','20','60')]:
                cell = frame.locator(f'[data-balance="{key}"]')
                expect(cell.locator('strong')).to_have_text(value+'g')
                expect(cell.locator('.balance-number>span')).to_have_text('('+target+'g)')
                expect(cell.locator('.balance-status')).to_have_text('1끼 미입력')
            page.screenshot(path=str(out/'partial-nutrition.png'))
            passed('current and target grams remain distinct and partial intake is explicitly marked')
            frame.evaluate('''() => KitchenJournal.transact(({play:p})=>{
                for(const meal of p.state().meals)p.remove(meal.id);
                p.setTargets({kcal:null,carb:100000,protein:70,fat:60,fiber:null,water:null});
                p.record({day:'2026-11-01',name:'입력 경계값',portion:'검사',recipeId:null,nutrients:{kcal:null,carb:100000,protein:0,fat:null,fiber:null,water:null}});
            })''')
            expect(frame.locator('[data-balance="protein"] strong')).to_have_text('0g')
            expect(frame.locator('[data-balance="fat"] strong')).to_have_text('—g')
            assert frame.evaluate('''() => [...document.querySelectorAll('.balance-value')].every(e=>e.scrollWidth<=e.clientWidth+1)''')
            passed('large entered values fit; known zero and missing values are not conflated')
            for tab in ['nutrition', 'book', 'rewards', 'backup', 'nutrition']:
                frame.evaluate('tab=>KitchenJournal.show(tab)', tab)
                expect(frame.locator('#tray .workflow-nav')).to_have_count(1)
                expect(frame.locator('#tray .journal-tabs')).to_have_count(0)
                expect(frame.locator('#tray .workflow-nav [aria-current="page"]')).to_have_count(1)
            frame.locator('#closeTray').click()
            passed('journal date/tab rerenders retain one navigation bar and reachable collection rewards')
            context.close()
            # Actual isolated mobile wrappers: open, modify, submit, and restore focus.
            for mode in ['app', 'widget']:
                context, page, frame = new(mode, 320, 660, True)
                frame.locator('[data-item="spice0"]').tap()
                expect(frame.locator('#ingredientForm .ingredient-identity')).to_be_visible()
                form = frame.locator('#ingredientForm')
                form.locator('[name="quantity"]').fill('175ml')
                form.locator('[name="expiry"]').fill('2027-03-01')
                form.locator('[name="opened"]').fill('2026-11-01')
                form.locator('[type="submit"]').tap()
                frame.wait_for_function('!document.querySelector("#tray").open')
                spice = frame.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="spice0")')
                assert (spice['quantity'], spice['expiry'], spice['opened']) == ('175ml','2027-03-01','2026-11-01')
                expect(frame.locator('[data-item="spice0"]')).to_be_focused()
                assert frame.evaluate('KitchenJournal.status') == 'temporary'
                passed(mode+' opaque touch: reorganized condiment form saves exact values and returns focus')
                context.close()
            assert not errors, errors
            passed('no JavaScript exceptions across all detail cases')
        except Exception as error:
            report['failures'].append({'error': str(error), 'trace': traceback.format_exc()})
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
    print(json.dumps({'passed':len(report['passed']), 'failed':len(report['failures'])}))

if __name__ == '__main__':
    main()
