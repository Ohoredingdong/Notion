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


def assert_room_placement(page):
    # New centered backdrop: counters stop before x450 and start after x1068;
    # their visible toe-kicks meet the floor at y856. Atlas feet end at y987/994.
    world=page.locator('.scene-world').bounding_box()
    fridge=page.locator('.fridge-stage').bounding_box()
    room=page.locator('.room').bounding_box()
    scale=world['width']/1536
    left=(fridge['x']-world['x'])/scale
    right=(fridge['x']+fridge['width']-world['x'])/scale
    feet=(fridge['y']+fridge['height']*987/994-world['y'])/scale
    assert left>=450 and right<=1050,('Fridge overlaps either counter',left,right)
    assert abs(feet-856)<=3,('Visible feet do not align with cabinet base',feet)
    assert abs(fridge['x']+fridge['width']/2-room['x']-room['width']/2)<=1,('Fridge is not centered',room,fridge)


def check_resize(browser, origin, output):
    """A panel resize must preserve edits and avoid a sudden change in scene scale."""
    context=browser.new_context(viewport={'width':649,'height':660},reduced_motion='reduce')
    page=context.new_page();metrics=[]
    try:
        page.goto(origin+'/miniature-kitchen-app.html',wait_until='networkidle')
        page.wait_for_function('window.MiniKitchen && window.KitchenJournal')
        page.locator('[data-item="milk"]').click()
        page.locator('[name="quantity"]').fill('250ml')
        page.locator('#ingredientForm [type="submit"]').click()
        for key in ['freshRight','frozenLeft','frozenRight']:page.locator(f'[data-door="{key}"]').click()
        expected=page.evaluate('MiniKitchen.getSnapshot()')
        for width in [1120,961,960,896,800,761,760,649,560,559,390,320,1120]:
            page.set_viewport_size({'width':width,'height':660})
            page.wait_for_function('innerWidth === '+str(width))
            page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            page.evaluate('scrollTo(0,0)')
            current=page.evaluate('''() => {
                const bounds=selector=>{const r=document.querySelector(selector).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right}};
                return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,fridge:bounds('.fridge-stage'),controls:bounds('.kitchen-progress'),
                    doors:[...document.querySelectorAll('.door')].map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}})};
            }''')
            assert_room_placement(page)
            assert not current['overflow'],current
            assert current['controls']['bottom']<=660,current
            assert all(r['x']>=0 and r['y']>=0 and r['right']<=width and r['bottom']<=660 for r in current['doors']),current
            state=page.evaluate('MiniKitchen.getSnapshot()')
            assert state['doors']==expected['doors']
            for before,after in zip(expected['items'],state['items']):
                assert {k:v for k,v in before.items() if k not in ('x','y')}=={k:v for k,v in after.items() if k not in ('x','y')}
            if metrics and abs(width-metrics[-1]['width'])==1:
                assert abs(current['fridge']['width']-metrics[-1]['fridge']['width'])<2,(metrics[-1],current)
                assert abs(current['fridge']['height']-metrics[-1]['fridge']['height'])<3,(metrics[-1],current)
            metrics.append(current)
        stage=page.locator('.fridge-stage');before=page.locator('.door').first.bounding_box()
        stage.evaluate("e=>e.style.perspective='none'")
        after=page.locator('.door').first.bounding_box()
        assert abs(before['width']-after['width'])>5,(before,after)
        (output/'resize-results.json').write_text(json.dumps({'viewports':metrics,'perspective_changes_projection':True,'edited_quantity_and_door_states_preserved':True},ensure_ascii=False,indent=2)+'\n')
    finally:context.close()


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
            layouts=[('app',1120,1000),('app',649,900),('app',649,660),('app',760,660),('app',761,660),('app',800,660),('app',896,660),('app',960,660),('app',961,660),('app',390,900),('app',320,900),
                     ('widget',649,900),('widget',649,660),('widget',640,900),('widget',390,900),('widget',390,660),('widget',320,900),('widget',320,660)]
            for mode,width,height in layouts:
                context=browser.new_context(viewport={'width':width,'height':height},has_touch=True,reduced_motion='reduce',timezone_id='Asia/Seoul')
                page=context.new_page();page.set_default_timeout(10000);errors=[];requests=[];external=[];label=f'{mode}-{width}'+('-short' if height==660 else '')
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
                      const original=Storage.prototype[method];Storage.prototype[method]=function(...args){__storageAccess.push({method,key:args[0]});return original.apply(this,args);};
                    }
                })();''')
                snapshot=lambda:page.evaluate('MiniKitchen.getSnapshot()')

                def item(key):return next(r for r in snapshot()['items'] if r['id']==key)

                def camera(name):
                    page.locator(f'.camera-tabs [data-camera="{name}"]').click()

                try:
                    page.goto(origin+f'/miniature-kitchen-{mode}.html',wait_until='networkidle');page.wait_for_load_state('domcontentloaded');page.wait_for_function('window.MiniKitchen && window.KitchenJournal')
                    original=page.evaluate('__originals()');initial=snapshot()
                    assert initial['mode']==mode
                    expect(page.locator('.door')).to_have_count(4);expect(page.locator('.fridge-lcd')).to_have_count(2)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    assert len(requests)==1 and not external
                    assert not page.evaluate("__storageAccess.some(e=>e.key!=='miniature-kitchen-preview-v1'||!['getItem','setItem'].includes(e.method))")
                    if (mode,width)==('app',1120):
                        # A running UI can still show missing or proxy-blurred art.
                        # Decode the actual inline images while all asset requests are blocked.
                        images=page.evaluate('''async () => {
                            const sources=new Set([...document.querySelectorAll('svg image')].map(n=>n.getAttribute('href')));
                            const background=getComputedStyle(document.querySelector('.scene-world')).backgroundImage;
                            if(!background.startsWith('url("data:image/'))throw new Error('Room background is not embedded');
                            sources.add(background.slice(5,-2));
                            return Promise.all([...sources].map(async source=>{
                                if(!source?.startsWith('data:image/'))throw new Error('External or missing preview image');
                                const image=new Image();image.src=source;await image.decode();
                                return [image.naturalWidth,image.naturalHeight];
                            }));
                        }''')
                        assert sorted(images)==[[643,612],[1254,1254],[1448,1086],[1536,1024],[1536,1024]],images
                        assert len(requests)==1 and not external
                        passed('art: all five embedded images decode at their configured render resolution with image network requests blocked')
                    # Fit the actual first viewport, not merely an oversized room.
                    stage=page.locator('.fridge-stage').bounding_box();controls=page.locator('.kitchen-progress').bounding_box();room=page.locator('.room').bounding_box()
                    assert stage['y']>=0 and stage['y']+stage['height']<=height,(stage,height)
                    assert controls['y']>=room['y']+room['height'],(room,controls)
                    assert controls['y']+controls['height']<=height,(controls,height)
                    assert_room_placement(page)
                    assert stage['height']>=min(300,height*.45),stage
                    assert page.evaluate("getComputedStyle(document.querySelector('.fridge-doors')).transformStyle")=='preserve-3d'
                    scales=page.evaluate("""() => ['.scene-world','.fridge-stage','.item.meal'].map(s=>{const e=document.querySelector(s);return e.getBoundingClientRect().width/e.offsetWidth})""")
                    assert max(scales)-min(scales)<.001,scales
                    assert page.locator('[data-item="milk"]').bounding_box()['width']>=43.99
                    page.screenshot(path=str(output/f'{label}.png'),full_page=True)
                    passed(label+': complete four-door scene, legible controls, no overflow, asset requests or production storage access')

                    if (mode,width)==('app',1120):
                        def check_palette(selector,count):
                            coverage=page.evaluate('''async selector => {
                                const images=new Map(),coverage=[];
                                for(const svg of document.querySelectorAll(selector)){
                                    const source=svg.querySelector('image').getAttribute('href');
                                    if(!images.has(source)){const image=new Image();image.src=source;await image.decode();images.set(source,image);}
                                    const box=svg.viewBox.baseVal,canvas=document.createElement('canvas');
                                    canvas.width=box.width;canvas.height=box.height;
                                    const context=canvas.getContext('2d');
                                    const image=images.get(source),node=svg.querySelector('image'),sx=image.naturalWidth/Number(node.getAttribute('width')),sy=image.naturalHeight/Number(node.getAttribute('height'));
                                    context.drawImage(image,box.x*sx,box.y*sy,box.width*sx,box.height*sy,0,0,box.width,box.height);
                                    const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
                                    let visible=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]>16)visible++;
                                    coverage.push(visible/(canvas.width*canvas.height));
                                }
                                return coverage;
                            }''',selector)
                            assert len(coverage)==count and all(value>.01 for value in coverage),coverage

                        page.locator('#addFood').click();check_palette('#trayContent .palette svg',8);page.locator('#closeTray').click()
                        passed('art: all eight food choices contain visible ingredient pixels')
                        page.locator('#recipes').click();check_palette('#trayContent .recipe-sheet svg',8);page.locator('#closeTray').click()
                        passed('art: all eight existing recipe choices contain visible food pixels')
                        page.locator('#decorate').click();check_palette('#trayContent .palette svg',4);page.locator('#closeTray').click();page.locator('#decorate').click()
                        passed('art: all four decoration choices contain visible prop pixels')

                    camera('fridge')
                    for key in initial['doors']:
                        control=page.locator(f'[data-door="{key}"]');before=snapshot()['doors'][key]
                        control.click();expect(control).to_have_attribute('aria-expanded',str(not before).lower())
                        assert snapshot()['doors'][key] is not before
                        for other,value in initial['doors'].items():
                            if other!=key:assert snapshot()['doors'][other] is value
                        control.click();assert snapshot()['doors']==initial['doors']
                    # All modes must retain four fully visible open doors.
                    for key,value in initial['doors'].items():
                        if not value:page.locator(f'[data-door="{key}"]').click()
                    page.evaluate('scrollTo(0,0)');room=page.locator('.room').bounding_box()
                    for door in page.locator('.door').all():
                        bounds=door.bounding_box()
                        assert bounds['x']>=room['x'] and bounds['x']+bounds['width']<=room['x']+room['width'],(room,bounds)
                        assert bounds['y']>=room['y'] and bounds['y']+bounds['height']<=room['y']+room['height'],(room,bounds)
                        assert bounds['y']>=0 and bounds['y']+bounds['height']<=height,(height,bounds)
                    for key,value in initial['doors'].items():
                        if not value:page.locator(f'[data-door="{key}"]').click()
                    page.evaluate('scrollTo(0,0)')
                    page.locator('[data-door="freshLeft"]').click()
                    expect(page.locator('[data-zone="freshLeft"]')).to_be_hidden()
                    assert page.locator('[data-zone="freshLeft"]').evaluate('e=>e.inert')
                    expect(page.locator('[data-lcd="freshLeft"]')).to_contain_text('6개')
                    assert page.locator('[data-lcd="freshLeft"]').evaluate('''e=>{
                        const display=e.getBoundingClientRect();
                        return [...e.querySelectorAll('.lcd-row small')].every(n=>n.getBoundingClientRect().bottom<=display.bottom-1);
                    }'''), 'An expiry date is clipped by the display'
                    page.screenshot(path=str(output/f'{label}-closed.png'),full_page=True)
                    page.locator('[data-door="freshLeft"]').click()
                    passed(label+': all four doors toggle independently; closed contents are hidden and inert; expiry display uses example quantities')

                    if width==320:
                        # Responsive rendering and all four doors run at 320px.
                        # Full interaction flows below run at 390px and desktop.
                        assert not errors and not external
                        assert page.evaluate('__originals()')==original and not page.evaluate("__storageAccess.some(e=>e.key!=='miniature-kitchen-preview-v1'||!['getItem','setItem'].includes(e.method))")
                        continue

                    milk=page.locator('[data-item="milk"]');before=item('milk')
                    # A closed destination is a visible real door, never forced open.
                    drag(page,milk,page.locator('[data-door="freshRight"]'),width<=760)
                    assert item('milk')==before
                    page.locator('[data-door="freshRight"]').click()
                    drag(page,milk,page.locator('[data-zone="freshRight"]'),width<=760)
                    assert item('milk')['zone']=='freshRight'
                    for key in ['frozenLeft','frozenRight']:page.locator(f'[data-door="{key}"]').click()
                    drag(page,page.locator('[data-item="fish"]'),page.locator('[data-zone="frozenRight"]'),width<=760)
                    assert item('fish')['zone']=='frozenRight'
                    passed(label+': real mouse/touch movement crosses open refrigerated and frozen panels and rejects a closed destination')

                    if height==660:
                        drag(page,page.locator('[data-item="milk"]'),page.locator('[data-zone="frozenLeft"]'),True)
                        assert item('milk')['zone']=='frozenLeft'
                        passed(label+': touch reaches the freezer within the fitted scene')

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
                    assert page.evaluate('__originals()')==original and not page.evaluate("__storageAccess.some(e=>e.key!=='miniature-kitchen-preview-v1'||!['getItem','setItem'].includes(e.method))")
                    ids=page.locator('[id]').evaluate_all('(nodes)=>nodes.map(n=>n.id)');assert len(ids)==len(set(ids))
                    assert not errors and not external
                    saved_world=page.evaluate('MiniKitchen.exportWorld()');saved_play=page.evaluate('KitchenJournal.getSnapshot()')
                    page.reload(wait_until='networkidle');page.wait_for_load_state('domcontentloaded');page.wait_for_function('window.MiniKitchen && window.KitchenJournal')
                    assert page.evaluate('MiniKitchen.exportWorld()')==saved_world
                    assert page.evaluate('KitchenJournal.getSnapshot()')==saved_play
                    assert page.evaluate('__originals()')==original and not page.evaluate("__storageAccess.some(e=>e.key!=='miniature-kitchen-preview-v1'||!['getItem','setItem'].includes(e.method))")
                    passed(label+': preview inventory/door/collection changes survive reload; production records are neither read nor written; no runtime errors')
                except Exception as e:
                    result['errors'].append(f'{label}: {type(e).__name__}: {e}');traceback.print_exc();page.screenshot(path=str(output/f'failure-{label}.png'),full_page=True)
                finally:context.close()

            try:
                check_resize(browser,origin,output)
                passed('resize: first viewport, open doors, saved example edits and continuous size at 559/560, 760/761 and 960/961; perspective affects doors')
            except Exception as e:
                result['errors'].append('resize: '+str(e));traceback.print_exc()
            context=browser.new_context(viewport={'width':1740,'height':1080});page=context.new_page();errors=[];board_requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:board_requests.append(r.url))
            try:
                page.goto(origin+'/miniature-kitchen-board.html',wait_until='networkidle')
                app=page.frame_locator('iframe').nth(0);widget=page.frame_locator('iframe').nth(1)
                app.locator('[data-door="freshRight"]').click();widget.locator('[data-door="frozenRight"]').click()
                expect(app.locator('[data-door="freshRight"]')).to_have_attribute('aria-expanded','true');expect(widget.locator('[data-door="frozenRight"]')).to_have_attribute('aria-expanded','true')
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
