#!/usr/bin/env python3
"""Check the isolated visual prototype, not production functionality or real data."""
import argparse
import functools
import http.server
import json
from pathlib import Path
import threading
import traceback

from playwright.sync_api import expect, sync_playwright
from test_fridge_four_door_browser import QuietHandler, drag


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd()/'previews')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser-executable',default='/usr/bin/chromium')
    args=parser.parse_args();root=args.root.resolve();output=args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[1]):
        raise SystemExit('Keep browser output outside the checkout.')
    output.mkdir(parents=True,exist_ok=True)
    result={'scope':'Isolated design prototype; examples only; no production storage or external services','cases':[],'errors':[]}

    def passed(name):
        result['cases'].append(name);print('PASS '+name,flush=True)

    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root)))
    threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.browser_executable,args=['--no-sandbox'])
            for mode,width in [('app',1120),('app',390),('app',320),('widget',640),('widget',390),('widget',320)]:
                context=browser.new_context(viewport={'width':width,'height':1000 if width>760 else 900},has_touch=True,reduced_motion='reduce',timezone_id='Asia/Seoul')
                page=context.new_page();page.set_default_timeout(10000);errors=[];requests=[];external=[];label=f'{mode}-{width}'
                page.on('pageerror',lambda e:errors.append(str(e)))

                def route(r):
                    requests.append(r.request.url)
                    if r.request.url.startswith(origin+'/') and r.request.resource_type=='document':r.continue_()
                    else:external.append(r.request.url);r.abort()

                page.route('**/*',route)
                page.clock.set_fixed_time('2026-10-23T03:00:00Z')
                page.add_init_script('''(() => {
                    const keys=['use-me-first-state-v5','use-me-first-kitchen-view-v1','umf-seasoning-layout-v3','use-me-first-life-v1'];
                    const get=Storage.prototype.getItem,set=Storage.prototype.setItem;
                    for(const key of keys)set.call(localStorage,key,'  preserve exact original '+key+'  ');
                    window.__storageAccess=[];
                    window.__originals=()=>keys.map(key=>get.call(localStorage,key));
                    for(const method of ['getItem','setItem','removeItem','clear']){
                      const original=Storage.prototype[method];Storage.prototype[method]=function(...args){__storageAccess.push(method);return original.apply(this,args);};
                    }
                })();''')
                snapshot=lambda:page.evaluate('MiniKitchen.getSnapshot()')

                def item(key):return next(r for r in snapshot()['items'] if r['id']==key)

                def camera(name):
                    if mode=='widget' or width<=760:page.locator(f'.camera-tabs [data-camera="{name}"]').click()

                try:
                    page.goto(origin+f'/miniature-kitchen-{mode}.html',wait_until='networkidle');page.wait_for_load_state('domcontentloaded');page.wait_for_function('window.MiniKitchen')
                    original=page.evaluate('__originals()');initial=snapshot()
                    assert initial['mode']==mode
                    expect(page.locator('.door')).to_have_count(4);expect(page.locator('.display')).to_have_count(2)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    assert len(requests)==1 and not external
                    assert not page.evaluate('__storageAccess')
                    if (mode,width)==('app',1120):
                        # A running UI can still show missing or proxy-blurred art.
                        # Decode the actual inline images while all asset requests are blocked.
                        images=page.evaluate('''async () => {
                            const sources=new Set([...document.querySelectorAll('svg image')].map(n=>n.getAttribute('href')));
                            const background=getComputedStyle(document.querySelector('.room')).backgroundImage;
                            if(!background.startsWith('url("data:image/'))throw new Error('Room background is not embedded');
                            sources.add(background.slice(5,-2));
                            return Promise.all([...sources].map(async source=>{
                                if(!source?.startsWith('data:image/'))throw new Error('External or missing preview image');
                                const image=new Image();image.src=source;await image.decode();
                                return [image.naturalWidth,image.naturalHeight];
                            }));
                        }''')
                        assert sorted(images)==[[1254,1254],[1286,1223],[1448,1086],[1536,1024],[1536,1024]],images
                        assert len(requests)==1 and not external
                        passed('art: all five embedded originals decode at full resolution with image network requests blocked')
                    if mode=='widget' or width<=760:
                        stage=page.locator('.fridge-stage').bounding_box();controls=page.locator('.door-controls').bounding_box()
                        assert stage['y']+stage['height'] <= controls['y']+1, (stage,controls)
                    assert page.locator('[data-item="milk"]').bounding_box()['width']>=44
                    page.screenshot(path=str(output/f'{label}.png'),full_page=True)
                    passed(label+': complete four-door scene, legible controls, no overflow, asset requests or storage access')

                    for key in initial['doors']:
                        control=page.locator(f'[data-toggle="{key}"]');before=snapshot()['doors'][key]
                        control.click();expect(control).to_have_attribute('aria-expanded',str(not before).lower())
                        assert snapshot()['doors'][key] is not before
                        for other,value in initial['doors'].items():
                            if other!=key:assert snapshot()['doors'][other] is value
                        control.click();assert snapshot()['doors']==initial['doors']
                    page.locator('[data-toggle="freshLeft"]').click()
                    expect(page.locator('[data-zone="freshLeft"]')).to_be_hidden()
                    assert page.locator('[data-zone="freshLeft"]').evaluate('e=>e.inert')
                    expect(page.locator('[data-door="freshLeft"] .display')).to_contain_text('6개')
                    page.screenshot(path=str(output/f'{label}-closed.png'),full_page=True)
                    page.locator('[data-toggle="freshLeft"]').click()
                    passed(label+': all four doors toggle independently; closed contents are hidden and inert; expiry display uses example quantities')

                    if width==320:
                        # Responsive rendering and all four doors run at 320px.
                        # Full interaction flows below run at 390px and desktop.
                        assert not errors and not external
                        assert page.evaluate('__originals()')==original and not page.evaluate('__storageAccess')
                        continue

                    milk=page.locator('[data-item="milk"]');before=item('milk')
                    # A closed destination is a visible real door, never forced open.
                    drag(page,milk,page.locator('[data-door="freshRight"]'),width<=760)
                    assert item('milk')==before
                    page.locator('[data-toggle="freshRight"]').click()
                    drag(page,milk,page.locator('[data-zone="freshRight"]'),width<=760)
                    assert item('milk')['zone']=='freshRight'
                    for key in ['frozenLeft','frozenRight']:page.locator(f'[data-toggle="{key}"]').click()
                    drag(page,page.locator('[data-item="fish"]'),page.locator('[data-zone="frozenRight"]'),width<=760)
                    assert item('fish')['zone']=='frozenRight'
                    passed(label+': real mouse/touch movement crosses open refrigerated and frozen panels and rejects a closed destination')

                    page.locator('[data-item="milk"]').click();expect(page.locator('#tray')).to_be_visible()
                    page.locator('#ingredientForm [name="quantity"]').fill('250ml')
                    page.locator('#ingredientForm [name="expiry"]').fill('2026-10-29')
                    page.locator('#ingredientForm [name="zone"]').select_option('freshLeft')
                    page.locator('#ingredientForm [type="submit"]').click()
                    assert item('milk')['quantity']=='250ml' and item('milk')['expiry']=='2026-10-29' and item('milk')['zone']=='freshLeft'
                    before=item('milk')['x'];page.locator('[data-item="milk"]').focus();page.keyboard.press('ArrowRight');assert item('milk')['x']>before
                    camera('seasoning')
                    page.locator('[data-item="spice0"]').click();page.locator('#ingredientForm [name="expiry"]').fill('2026-11-20');page.locator('#ingredientForm [type="submit"]').click();assert item('spice0')['expiry']=='2026-11-20'
                    spice=item('spice1');drag(page,page.locator('[data-item="spice1"]'),page.locator('[data-zone="seasoning"]'),width<=760);assert item('spice1')['x']!=spice['x']
                    page.screenshot(path=str(output/f'{label}-seasoning.png'),full_page=True)
                    passed(label+': example quantities/dates and seasoning dates edit; keyboard alternative and seasoning drag work')

                    page.locator('#decorate').click();expect(page.locator('#trayTitle')).to_contain_text('소품')
                    page.locator('[data-add-prop="cookies"]').click();expect(page.locator('#tray')).not_to_be_visible()
                    added=next(r for r in snapshot()['items'] if r.get('art')=='cookies')
                    drag(page,page.locator(f'[data-item="{added["id"]}"]'),page.locator('[data-zone="counter"]'),width<=760)
                    assert item(added['id'])['x']!=added['x']
                    page.locator(f'[data-item="{added["id"]}"]').click();page.locator('[data-layer="back"]').click()
                    assert item(added['id'])['z']==1
                    page.locator('#propList').click();page.locator(f'[data-select-prop="{added["id"]}"]').click();page.locator('[data-layer="front"]').click()
                    assert item(added['id'])['z']==max(r['z'] for r in snapshot()['items'] if r['zone']=='counter')
                    page.screenshot(path=str(output/f'{label}-decor.png'),full_page=True)
                    page.locator(f'[data-item="{added["id"]}"]').click();page.locator('[data-remove]').click();assert all(r['id']!=added['id'] for r in snapshot()['items'])
                    page.locator('#decorate').click();assert snapshot()['decorating'] is False
                    passed(label+': decor choices place real movable objects, preserve overlapping layers and allow removing the chosen object')

                    page.locator('#addFood').click();page.locator('[data-add-food="당근"]').click();assert any(r['name']=='당근' for r in snapshot()['items'])
                    page.locator('#recipes').click();page.locator('[data-recipe="두부 된장국"]').click();assert item('meal')['name']=='두부 된장국'
                    camera('counter');page.screenshot(path=str(output/f'{label}-counter.png'),full_page=True)
                    assert page.evaluate('__originals()')==original and not page.evaluate('__storageAccess')
                    ids=page.locator('[id]').evaluate_all('(nodes)=>nodes.map(n=>n.id)');assert len(ids)==len(set(ids))
                    assert not errors and not external
                    page.reload(wait_until='networkidle');page.wait_for_load_state('domcontentloaded');page.wait_for_function('window.MiniKitchen')
                    assert snapshot()==initial
                    assert page.evaluate('__originals()')==original and not page.evaluate('__storageAccess')
                    passed(label+': example food/meal changes reset on reload; real records are neither read nor written; no runtime errors')
                except Exception as e:
                    result['errors'].append(f'{label}: {type(e).__name__}: {e}');traceback.print_exc();page.screenshot(path=str(output/f'failure-{label}.png'),full_page=True)
                finally:context.close()

            context=browser.new_context(viewport={'width':1740,'height':1080});page=context.new_page();errors=[];board_requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:board_requests.append(r.url))
            try:
                page.goto(origin+'/miniature-kitchen-board.html',wait_until='networkidle')
                app=page.frame_locator('iframe').nth(0);widget=page.frame_locator('iframe').nth(1)
                app.locator('[data-toggle="freshRight"]').click();widget.locator('[data-toggle="frozenRight"]').click()
                expect(app.locator('[data-toggle="freshRight"]')).to_have_attribute('aria-expanded','true');expect(widget.locator('[data-toggle="frozenRight"]')).to_have_attribute('aria-expanded','true')
                assert not errors,errors
                assert len(board_requests)==1,board_requests
                page.screenshot(path=str(output/'comparison-board.png'),full_page=True)
                with page.expect_popup() as popup:
                    page.locator('.view h2 a').first.click()
                popup.value.wait_for_function('window.MiniKitchen')
                assert popup.value.evaluate('MiniKitchen.getSnapshot().mode')=='app'
                popup.value.close()
                passed('comparison: both app and widget execute in separate opaque sandbox iframes without storage access')
            except Exception as e:
                result['errors'].append('comparison: '+str(e));traceback.print_exc()
            finally:context.close();browser.close()
    finally:server.shutdown()
    result['passed']=not result['errors'];result['passed_cases']=len(result['cases'])
    (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
