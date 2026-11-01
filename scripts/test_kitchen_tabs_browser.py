#!/usr/bin/env python3
"""Check viewport tabs, keyboard/focus and contained long records in both previews.

This is a local Chromium check. Public hosting, OCR, Safari and physical phones
are separate checks. All interaction uses controls; model calls only read state.
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

        def new(mode, width, height, opaque=False):
            context = browser.new_context(viewport={'width': width, 'height': height}, timezone_id='Asia/Seoul',
                                          reduced_motion='reduce', has_touch=opaque, is_mobile=opaque)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
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
                                  ('kitchen', 'growth'), ('kitchen', 'connections'), ('fridge', None)]:
                    choose(frame, name, sub)
                    viewport(frame)
                    assert frame.locator('.home-shortcuts').bounding_box() == nav
                assert frame.evaluate('KitchenJournal.getEnvelope()') == before
                assert frame.locator('.fridge-stage').bounding_box() == fridge
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
                # A recipe selected from a hidden-scene tab must reveal its
                # actual counter and give focus to a visible control on close.
                choose(frame, 'meals', 'recommendation')
                frame.locator('#homeRecommendation [data-wf="recipe"]').click()
                expect(frame.locator('#tray')).to_be_visible()
                recipe_name = frame.locator('#trayTitle').inner_text()
                opened = frame.evaluate('KitchenJournal.getEnvelope()')
                frame.locator('#tray [data-wf="counterRecipe"]').click()
                expect(frame.locator('#tray')).not_to_be_visible()
                expect(frame.locator('[data-home-tab="fridge"]')).to_have_attribute('aria-selected', 'true')
                expect(frame.locator('body')).to_have_attribute('data-camera', 'counter')
                expect(frame.locator('.counter-zone [data-item="meal"]')).to_be_visible()
                assert frame.evaluate('''()=>{const e=document.activeElement,r=e.getBoundingClientRect();
                    return e!==document.body&&r.width>0&&r.height>0&&r.top>=0&&r.bottom<=innerHeight;}''')
                after_recipe = frame.evaluate('KitchenJournal.getEnvelope()')
                expected_world = json.loads(json.dumps(opened['world']))
                next(item for item in expected_world['items'] if item['kind'] == 'meal')['name'] = recipe_name
                assert after_recipe['world'] == expected_world
                assert after_recipe['play'] == opened['play']
                assert after_recipe['workflow'] == opened['workflow']
                frame.locator('.camera-tabs [data-camera="fridge"]').click()
                viewport(frame)
                report['profiles'].append({'mode': mode, 'width': width, 'height': height, 'opaque': opaque,
                                           'metrics': viewport(frame), 'header': header_metrics, 'small_shelf_labels': shelf_metrics})
                passed(f'{mode} {width}x{height} {"opaque touch" if opaque else "native"}: one viewport, keyboard tabs, stable fridge, recipe-to-counter focus and exact records')
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
