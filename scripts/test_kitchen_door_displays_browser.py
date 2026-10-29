#!/usr/bin/env python3
"""Check visible LCD paint during real door motion and the return to native text."""
import argparse
from functools import partial
import http.server
import json
from pathlib import Path
import subprocess
import threading
import traceback

from playwright.sync_api import expect, sync_playwright
from test_fridge_four_door_browser import QuietHandler


def paint(png):
    pixels = subprocess.run(['magick', '-limit', 'thread', '1', 'png:-', '-depth', '8', 'rgb:-'],
                            input=png, capture_output=True, check=True).stdout
    colors = list(zip(pixels[0::3], pixels[1::3], pixels[2::3]))
    return {'dark_fraction': sum(max(c) < 150 for c in colors) / len(colors),
            'mint_pixels': sum(max(abs(a-b) for a,b in zip(c, (163,234,214))) <= 15 for c in colors)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mobile-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):
        raise SystemExit('Keep screenshots and results outside the checkout.')
    out.mkdir(parents=True, exist_ok=True)
    result = {'cases': [], 'errors': [], 'scope': 'Local Chromium; real CSS transitions, native and opaque frames. Not physical iPhone/Safari or remote renderer validation.'}
    servers = [http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root.resolve())))
               for root in (args.root, args.mobile_root)]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            conditions = [(kind, mode, width, height, 'no-preference')
                          for kind in ('native', 'opaque') for mode in ('app', 'widget')
                          for width,height in ((649,900), (390,660))]
            conditions += [('native', mode, 320,568, 'no-preference') for mode in ('app','widget')]
            conditions += [('native', mode, 390,660, 'reduce') for mode in ('app','widget')]
            for kind, mode, width, height, motion in conditions:
                label = f'{kind}-{mode}-{width}-{motion}'
                ctx = browser.new_context(viewport={'width':width,'height':height}, device_scale_factor=2,
                                          has_touch=True, reduced_motion=motion, timezone_id='Asia/Seoul')
                page = ctx.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                server = servers[0 if kind == 'native' else 1]
                path = f'miniature-kitchen-{mode}.html' if kind == 'native' else f'{mode}.html'
                page.goto(f'http://127.0.0.1:{server.server_port}/{path}', wait_until='networkidle')
                frame = page if kind == 'native' else page.frames[1]
                frame.wait_for_function('window.KitchenJournal && window.MiniKitchen')
                door = lambda key: frame.locator(f'[data-door="{key}"]')
                lcd = lambda key: frame.locator(f'#fridgeDisplays [data-lcd="{key}"]')
                # Programmatic activation isolates the animation/paint regression
                # from the separately recorded opaque-frame touch-delivery issue.
                click = lambda key: door(key).evaluate('e=>e.click()')
                before = frame.evaluate('MiniKitchen.exportWorld()')
                for key in ('freshLeft','freshRight'): click(key)
                frame.wait_for_function("document.querySelectorAll('.door').length===4 && [...document.querySelectorAll('.door')].every(e=>e.getAnimations().every(a=>a.playState==='finished'))")
                moving = []
                for key in ('freshRight', 'freshLeft'):
                    click(key)
                    if motion == 'no-preference':
                        # Pause the actual CSS transition near its closed face;
                        # the 650ms recovery timer must not have fired yet.
                        door(key).evaluate('''e=>{const a=e.getAnimations().find(a=>a.transitionProperty==='transform');if(!a)throw new Error('No real door transition');a.pause();a.currentTime=Number(a.effect.getComputedTiming().duration)*.78;}''')
                        png = door(key).screenshot()
                        (out/f'{label}-{key}-moving.png').write_bytes(png)
                        assert frame.evaluate('k=>MiniKitchen.isDoorClosing(k)',key), 'Recovery timer fired before the moving-frame sample'
                        values = paint(png)
                        assert values['dark_fraction'] > .15, (label,key,'Blank display on moving door',values)
                        if key == 'freshRight': assert values['mint_pixels'] >= 4, (label,'Recipe ring not painted',values)
                        moving.append({'door':key,**values})
                        door(key).evaluate("e=>e.getAnimations().forEach(a=>a.play())")
                    frame.wait_for_function('k=>!MiniKitchen.isDoorClosing(k)',arg=key)
                    expect(lcd(key)).to_be_visible()
                    assert lcd(key).evaluate("e=>{for(let n=e;n;n=n.parentElement)if(getComputedStyle(n).transform!=='none'||getComputedStyle(n).filter!=='none')return false;return true}")
                expect(frame.locator('.door-live-display')).to_have_count(0)
                if motion == 'no-preference':
                    # Reverse directions before the previous transition settles.
                    frame.evaluate("async()=>{const d=document.querySelector('[data-door=\"freshRight\"]');for(let i=0;i<4;i++){d.click();await new Promise(r=>setTimeout(r,35));}}")
                    frame.wait_for_function("!MiniKitchen.isDoorClosing('freshRight') && !MiniKitchen.exportWorld().doors.freshRight")
                    expect(lcd('freshRight')).to_be_visible()
                    # A missing transitionend must still restore the live LCD.
                    frame.evaluate("()=>{window.__blockEnd=e=>{if(e.target.dataset.door==='freshRight')e.stopImmediatePropagation()};document.addEventListener('transitionend',__blockEnd,true)}")
                    click('freshRight')
                    frame.wait_for_function("document.querySelector('[data-door=\"freshRight\"]').getAnimations().every(a=>a.playState==='finished')")
                    click('freshRight')
                    frame.wait_for_function("!MiniKitchen.isDoorClosing('freshRight')")
                    expect(lcd('freshRight')).to_be_visible()
                    frame.evaluate("()=>document.removeEventListener('transitionend',__blockEnd,true)")
                    # Cancel a transition by removing motion while it is closing.
                    click('freshRight')
                    frame.wait_for_function("document.querySelector('[data-door=\"freshRight\"]').getAnimations().every(a=>a.playState==='finished')")
                    click('freshRight')
                    door('freshRight').evaluate("e=>e.style.transition='none'")
                    frame.wait_for_function("!MiniKitchen.isDoorClosing('freshRight')")
                    expect(lcd('freshRight')).to_be_visible()
                expect(frame.locator('#fridgeDisplays .fridge-lcd')).to_have_count(2)
                expect(frame.locator('.door-live-display')).to_have_count(0)
                after = frame.evaluate('MiniKitchen.exportWorld()')
                stable = lambda world: dict(world,items=[{k:v for k,v in item.items() if k!='x'} for item in world['items']])
                assert stable(before)==stable(after), 'Inventory, dates, quantities or final door state changed'
                assert not errors, errors
                page.screenshot(path=str(out/f'{label}-settled.png'))
                result['cases'].append({'label':label,'moving_paint':moving,'native_text_restored':True,'rapid_reversal_and_missing_event_recovery':motion=='no-preference','inventory_preserved':True,'errors':errors})
                print('PASS',label,flush=True)
                ctx.close()
            browser.close()
    except Exception:
        result['errors'].append(traceback.format_exc())
        raise
    finally:
        for server in servers: server.shutdown()
        result['passed'] = not result['errors'] and len(result['cases']) == 12
        (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    main()
