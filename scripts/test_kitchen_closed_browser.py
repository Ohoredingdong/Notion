#!/usr/bin/env python3
"""Check real four-door kitchen painting, storage and prop placement.

Run against a frozen generated previews directory. All browser contexts are
local and disposable; no OCR, provider, publishing or personal storage is used.
Before/after PNGs use the same clock, stock and sequence of actual door clicks.
Geometry checks do not claim human design approval: inspect the PNGs separately.
"""
import argparse
import copy
import functools
import hashlib
import json
import shutil
import threading
import traceback
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright
import test_kitchen_widget_browser as old
import test_kitchen_living_browser as living


REPO = Path(__file__).resolve().parents[1]
PROFILES = ((320, 360), (390, 480), (720, 800), (800, 600))
DOORS = ('freshLeft', 'freshRight', 'frozenLeft', 'frozenRight')
ENTRIES = old.ENTRIES
DELIVERIES = ('miniature-kitchen-widget.html', 'miniature-kitchen-app.html',
              'mobile/widget.html', 'mobile/app.html')
# Existing native photograph and interaction registration, not a new layout.
STAGE = (278, 352, 699, 776)
PANELS = {
    'freshLeft': (0, 0, .496, 448/776),
    'freshRight': (.504, 0, .496, 448/776),
    'frozenLeft': (0, 449/776, .496, 323/776),
    'frozenRight': (.504, 449/776, .496, 323/776),
}
OPEN_BOXES = {
    'freshLeft': (-170, -16, 190, 461),
    'freshRight': (680, -16, 168, 461),
    'frozenLeft': (-170, 448, 190, 365),
    'frozenRight': (680, 448, 168, 365),
}
# Closed-face source registration: a single camera scale chosen from the
# photographed upper height. All four source crops retain that same scale.
FRONT_SCALE = 448/572
FRONT_BOXES = {
    'freshLeft': (176, 174, 450, 572),
    'freshRight': (629, 174, 450, 572),
    'frozenLeft': (176, 747, 450, 400),
    'frozenRight': (629, 747, 450, 400),
}
OPEN_PAINT_BOXES = {
    'freshLeft': (108, 336, 192, 465),
    'freshRight': (958, 336, 168, 466),
    'frozenLeft': (108, 800, 191, 387),
    'frozenRight': (958, 800, 168, 387),
}

METRICS = r'''async()=>{
 const box=e=>{if(!e||!e.getClientRects().length)return null;const r=e.getBoundingClientRect();
  return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
 const visible=e=>{if(!box(e))return false;for(let n=e;n;n=n.parentElement){
  const c=getComputedStyle(n);if(n.hidden||c.display==='none'||c.visibility==='hidden'||Number(c.opacity)===0)return false;
 }return true};
 const source=s=>{if(!s)return null;let h=2166136261;for(let i=0;i<s.length;i++)h=Math.imul(h^s.charCodeAt(i),16777619);
  return {identity:(h>>>0).toString(16),length:s.length,kind:s.startsWith('data:')?s.slice(5,s.indexOf(';')):'url'}};
 const image=async(e,checkOpaque=false)=>{if(!e)return null;const src=e.getAttribute('href')||e.currentSrc||e.src;
  const result={source:source(src),decoded:false};try{const i=new Image();i.src=src;await i.decode();
   Object.assign(result,{decoded:true,naturalWidth:i.naturalWidth,naturalHeight:i.naturalHeight});
   if(checkOpaque){const canvas=document.createElement('canvas');canvas.width=i.naturalWidth;canvas.height=i.naturalHeight;
    const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(i,0,0);
    const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;let nonOpaquePixels=0;
    for(let p=3;p<pixels.length;p+=4)if(pixels[p]!==255)nonOpaquePixels++;
    result.alpha={pixelCount:canvas.width*canvas.height,nonOpaquePixels};
   }
  }catch(_){result.error='The actual image did not decode'}
  if(e.namespaceURI==='http://www.w3.org/2000/svg')Object.assign(result,{x:e.x.baseVal.value,y:e.y.baseVal.value,
   width:e.width.baseVal.value,height:e.height.baseVal.value,preserve:e.getAttribute('preserveAspectRatio')});
  return result};
 const svg=async e=>{if(!e)return null;const v=e.viewBox.baseVal,m=e.getScreenCTM();
  const points=m?[[v.x,v.y],[v.x+v.width,v.y],[v.x,v.y+v.height],[v.x+v.width,v.y+v.height]]
   .map(([x,y])=>new DOMPoint(x,y).matrixTransform(m)):[];
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y),x=Math.min(...xs),y=Math.min(...ys),right=Math.max(...xs),bottom=Math.max(...ys);
  return {rect:box(e),visible:visible(e),viewBox:{x:v.x,y:v.y,width:v.width,height:v.height},
   backgroundColor:getComputedStyle(e).backgroundColor,
   preserve:e.getAttribute('preserveAspectRatio'),projected:m?{x,y,right,bottom,width:right-x,height:bottom-y}:null,
   matrix:m?{a:m.a,b:m.b,c:m.c,d:m.d,e:m.e,f:m.f}:null,image:await image(e.querySelector('image')),
   clipPolygons:[...e.querySelectorAll('clipPath polygon')].map(p=>p.getAttribute('points')),
   clips:[...e.querySelectorAll('clipPath rect')].map(r=>({x:r.x.baseVal.value,y:r.y.baseVal.value,
    width:r.width.baseVal.value,height:r.height.baseVal.value}))};
 };
 const world=document.querySelector('.scene-world'),background=document.querySelector('.original-kitchen-photo');
 const cs=world?getComputedStyle(world):null;
 return {viewport:{width:innerWidth,height:innerHeight},camera:document.body.dataset.camera,
  screen:document.querySelector('#panel-fridge')?.dataset.screenId,
  document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,scrollY},
  shell:box(document.querySelector('.shell')),host:box(document.querySelector('#fridgeSceneHost')),
  world:box(world),logicalWorld:world?{width:world.offsetWidth,height:world.offsetHeight}:null,
  worldMatrix:cs?(()=>{const m=new DOMMatrix(cs.transform);return {a:m.a,b:m.b,c:m.c,d:m.d}})():null,
  stage:box(document.querySelector('.fridge-stage')),background:{rect:box(background),visible:visible(background),image:await image(background,true)},
  body:await svg(document.querySelector('.original-fridge-body svg')),
  hinges:[...document.querySelectorAll('.native-left-hinge,.native-right-hinge')].map(e=>({
   door:e.classList.contains('native-left-hinge')?'freshLeft':'freshRight',visible:visible(e)})),
  revealPatchCount:document.querySelectorAll('.original-door-reveals,[data-reveal]').length,
  doors:await Promise.all([...document.querySelectorAll('[data-door]')].map(async e=>({
   id:e.dataset.door,expanded:e.getAttribute('aria-expanded'),label:e.getAttribute('aria-label'),
   rect:box(e),open:e.classList.contains('is-open'),paint:await svg(e.querySelector('svg')),
   openPaint:!!e.querySelector('.original-open-door'),background:getComputedStyle(e).backgroundImage,
   backgroundColor:getComputedStyle(e).backgroundColor}))),
  clones:[...document.querySelectorAll('#homeSceneDecor .home-prop-mini')].map(e=>({
   id:e.dataset.homeProp,art:e.dataset.homeArt,rect:box(e),visible:visible(e)})),
  realProps:[...document.querySelectorAll('.room .item.decor')].map(e=>({
   id:e.dataset.item,rect:box(e),visible:visible(e)})),
  room:box(document.querySelector('.room')),
  counterSurface:parseFloat(getComputedStyle(document.querySelector('.shell')).getPropertyValue('--counter-surface-y-room'))||null
 };
}'''


def check(ev, value, name, detail=None, layout=False):
    old.Audit(ev).check(value, name, detail,
                        category='reference-composition' if layout else 'functional')


def without_doors(envelope):
    result = copy.deepcopy(envelope)
    result['world'].pop('doors')
    return result


def same_box(a, b, tolerance=1):
    return bool(a and b and all(abs(a[k]-b[k]) <= tolerance
                               for k in ('x', 'y', 'width', 'height')))


def project(base, native, native_width=1254):
    x, y, w, h = native
    scale = base['width']/native_width
    return {'x': base['x']+x*scale, 'y': base['y']+y*scale,
            'width': w*scale, 'height': h*scale,
            'right': base['x']+(x+w)*scale, 'bottom': base['y']+(y+h)*scale}


def capture(page, frame, folder, label):
    old.ready(frame)
    metrics = frame.evaluate(METRICS)
    page.screenshot(path=str(folder/(label+'.png')), animations='disabled', caret='hide')
    return metrics


def painted_geometry(ev, paint, expected, label):
    check(ev, bool(paint and paint['image'] and paint['image']['decoded']),
          label+' uses a decoded actual image', paint, layout=True)
    if not paint or not paint['matrix']:
        return
    image = paint['image']
    check(ev, bool(image and image['decoded'] and image['width']>0 and image['height']>0
                   and abs(image['width']/image['height']-
                           image['naturalWidth']/image['naturalHeight']) < .00001),
          label+' does not distort the raster inside its SVG', image,layout=True)
    m = paint['matrix']
    check(ev, abs(m['a']-m['d']) < .00001 and abs(m['b']) < .00001 and abs(m['c']) < .00001,
          label+' preserves native image proportions', m, layout=True)
    # Uniform matrix alone passes the old slice crop! Both the viewBox paint
    # and SVG frame must fill exactly the physical door, without cropped art.
    check(ev, same_box(paint['rect'], expected) and same_box(paint['projected'], expected),
          label+' projects the entire source crop onto its exact native frame',
          {'frame':paint['rect'],'projected':paint['projected'],'expected':expected}, layout=True)
    check(ev, 'slice' not in (paint['preserve'] or '')
          and paint['preserve'] != 'none', label+' does not crop or stretch its source viewBox',
          paint['preserve'], layout=True)


def composition(ev, metrics, label):
    m = metrics
    viewport = old.viewport_box(m['viewport']['width'], m['viewport']['height'])
    check(ev, old.inside(m['shell'], viewport), label+' shell fits the actual embed', m['shell'], layout=True)
    check(ev, m['document']['width'] <= m['viewport']['width']+1
          and m['document']['height'] <= m['viewport']['height']+1 and m['document']['scrollY'] == 0,
          label+' has no document overflow', m['document'], layout=True)
    world = m['world']
    check(ev, m['logicalWorld'] == {'width':1254,'height':1254}
          and abs(world['width']-world['height']) < 1,
          label+' retains one native square kitchen projection', m['logicalWorld'], layout=True)
    stage = project(world, STAGE)
    check(ev, same_box(m['stage'], stage), label+' refrigerator stays in its original installation opening',
          {'stage':m['stage'],'expected':stage}, layout=True)
    check(ev, m['revealPatchCount'] == 0,
          label+' has no rectangular duplicate background patches', m['revealPatchCount'], layout=True)
    bg = m['background']
    check(ev, bg['visible'] and bg['image'] and bg['image']['decoded']
          and bg['image']['naturalWidth'] == 1254 and bg['image']['naturalHeight'] == 1254
          and same_box(bg['rect'], world), label+' uses a single decoded continuous kitchen background', bg, layout=True)
    check(ev, bool(bg['image'] and bg['image'].get('alpha')
                   and bg['image']['alpha']['pixelCount']==1254*1254
                   and bg['image']['alpha']['nonOpaquePixels']==0),
          label+' actual delivered background covers the whole kitchen rather than sparse transparent patches',
          bg['image'].get('alpha') if bg['image'] else None,layout=True)
    body = m['body']
    painted_geometry(ev, body, world, label+' native refrigerator body')
    if body:
        check(ev, bool(body['clips']) and body['clips'][0] ==
              dict(zip(('x','y','width','height'),STAGE)),
              label+' original body is clipped to the original refrigerator opening',
              body['clips'],layout=True)
    if body and body['image'] and bg['image']:
        check(ev, body['image']['source'] != bg['image']['source'],
              label+' separates the original refrigerator body from the empty continuous background', layout=True)
    check(ev, not any(p['visible'] for p in m['clones']),
          label+' shows no floating duplicate counter props over the fridge photograph', m['clones'], layout=True)
    check(ev, not any(p['visible'] for p in m['realProps']),
          label+' keeps room-camera props out of the incompatible fridge photograph', m['realProps'], layout=True)
    check(ev, len(m['doors']) == 4 and {d['id'] for d in m['doors']} == set(DOORS),
          label+' retains four distinct interactive doors')
    check(ev, len(m['hinges'])==2 and all(
        h['visible']==next((d['open'] for d in m['doors'] if d['id']==h['door']),None)
        for h in m['hinges']),
        label+' shows each outer hinge only while its corresponding upper door is open',
        m['hinges'],layout=True)
    closed_paints = [d['paint'] for d in m['doors'] if not d['open'] and d['paint']]
    if closed_paints:
        sources = [p['image']['source'] for p in closed_paints if p['image']]
        check(ev, len(sources)==len(closed_paints) and all(s==sources[0] for s in sources),
              label+' closed faces share one source photograph and camera',sources,layout=True)
    for door in m['doors']:
        key = door['id']
        if key not in PANELS:
            continue
        sx,sy,sw,sh = FRONT_BOXES[key]
        native = OPEN_BOXES[key] if door['open'] else (
            349.5+(sx-627.5)*FRONT_SCALE,(sy-174)*FRONT_SCALE,
            sw*FRONT_SCALE,sh*FRONT_SCALE)
        expected = project(stage, native, 699)
        check(ev, same_box(door['rect'], expected), label+' '+key+' preserves its registered hit area',
              {'rect':door['rect'],'expected':expected}, layout=True)
        paint_expected = project(world,OPEN_PAINT_BOXES[key]) if door['open'] else expected
        painted_geometry(ev, door['paint'], paint_expected, label+' '+key)
        if not door['open'] and door['paint']:
            v = door['paint']['viewBox']
            expected_scale = world['width']/1254*FRONT_SCALE
            scale_drift = abs(door['paint']['matrix']['a']-expected_scale)*max(v['width'],v['height'])
            # Chromium quantizes CSS layout to 1/64px before the SVG meet
            # transform. At 720x800 the observed full-face drift is .00733
            # CSS px, despite identical X/Y scale and the exact source crop.
            # Bound the painted error to one layout quantum rather than using
            # a scale epsilon whose pixel meaning varies with crop size.
            check(ev, v==dict(zip(('x','y','width','height'),FRONT_BOXES[key]))
                  and scale_drift<=1/64,
                  label+' '+key+' uses the registered complete face at the common camera scale',
                  {'viewBox':v,'expected_scale':expected_scale,
                   'measured_scale':door['paint']['matrix']['a'],'paint_drift_css_px':scale_drift,
                   'maximum_layout_quantum_css_px':1/64},layout=True)
        check(ev, door['openPaint'] == door['open'],
              label+' '+key+' switches to the matching native open/closed painting')
        if door['open'] and door['paint']:
            check(ev, bool(door['paint']['clipPolygons']),
                  label+' '+key+' masks the open door rather than painting another rectangular wall patch', layout=True)
            check(ev, door['paint']['backgroundColor']=='rgba(0, 0, 0, 0)'
                  and door['backgroundColor']=='rgba(0, 0, 0, 0)',
                  label+' '+key+' keeps the native polygon surroundings transparent',
                  {'button':door['backgroundColor'],'svg':door['paint']['backgroundColor']},layout=True)
            if body and body['image'] and door['paint']['image']:
                check(ev, door['paint']['image']['source'] == body['image']['source'],
                      label+' '+key+' retains its original photographed open door', layout=True)
        check(ev, door['expanded'] == str(door['open']).lower()
              and ('닫기' if door['open'] else '열기') in door['label'],
              label+' '+key+' exposes its actual action and state')


def click_door(frame, key):
    """Use an actual unobscured point, never force or dispatch a synthetic click."""
    door = frame.locator('[data-door="'+key+'"]')
    point = door.evaluate(r'''e=>{const r=e.getBoundingClientRect();
      const samples=[[6,8],[r.width-6,8],[6,r.height-8],[r.width-6,r.height-8],
        [r.width/2,8],[r.width/2,r.height-8],[r.width/2,r.height/2]];
      for(const [x,y]of samples){const hit=document.elementFromPoint(r.x+x,r.y+y);
       if(hit===e||e.contains(hit))return{x,y}}
      return null}''')
    if point is None:
        raise AssertionError('No genuinely clickable point on '+key)
    door.click(position=point)
    frame.wait_for_function('(key)=>document.querySelector("[data-door=\\""+key+"\\"]").getAttribute("aria-expanded")'
                            '===String(MiniKitchen.exportWorld().doors[key])', arg=key)
    old.ready(frame)


def preservation(ev, frame, expected_doors, original, label):
    current = old.state(frame)
    check(ev, current['envelope']['world']['doors'] == expected_doors,
          label+' changes only the intended door boolean', current['envelope']['world']['doors'])
    check(ev, without_doors(current['envelope']) == without_doors(original['envelope']),
          label+' preserves every quantity, expiry, position, meal, expense, supplement and setting')
    return current


def load_frame(page, kind):
    frame = page.locator('iframe').element_handle().content_frame() if kind == 'opaque' else page.main_frame
    frame.wait_for_function('window.MiniKitchen&&window.KitchenJournal&&window.KitchenHome&&window.KitchenWorkflows')
    old.ready(frame)
    return frame


def room_props(ev, page, frame, folder, label, original):
    frame.locator('.home-shortcuts [data-home-tab="kitchen"]').click()
    if frame.locator('body').get_attribute('data-home-page') != 'decor':
        frame.locator('[data-home-subtab="decor"]:visible').click()
    old.ready(frame)
    draft = old.state(frame)
    check(ev, draft == original, 'Entering the live room editor does not write or modify records')
    metrics = capture(page, frame, folder, label+'-counter')
    expected = {i['id'] for i in original['envelope']['world']['items'] if i['kind']=='decor'}
    props = {p['id']:p for p in metrics['realProps']}
    check(ev, expected and expected <= set(props) and all(props[k]['visible'] for k in expected),
          'Counter editor retains the actual saved props', props, layout=True)
    for key in expected:
        check(ev, old.inside(props[key]['rect'], metrics['room'], 2),
              key+' remains placed within the actual room surface', props[key], layout=True)
    frame.locator('[data-home-subtab="health"]:visible').click()
    check(ev, old.state(frame) == original,
          'Leaving the room editor cancels its preview and preserves all stored props and records')
    frame.locator('.home-shortcuts [data-home-tab="fridge"]').click()
    old.ready(frame)
    frame.locator('.home-shortcuts [data-home-tab="kitchen"]').click()
    if frame.locator('body').get_attribute('data-home-page') != 'decor':
        frame.locator('[data-home-subtab="decor"]:visible').click()
    frame.locator('#homeDecor [data-decor-apply]').click()
    old.ready(frame)
    applied = old.state(frame)
    check(ev, without_doors(applied['envelope']) == without_doors(original['envelope'])
          and applied['envelope']['world']['doors'] == {k:False for k in DOORS},
          'Applying the unchanged room only closes doors; saved prop coordinates and records remain exact')
    metrics = capture(page,frame,folder,label+'-D6-applied')
    check(ev, metrics['screen']=='D6', 'Actual Apply enters the existing D6 room view')
    clones = {p['id']:p for p in metrics['clones']}
    check(ev, expected <= set(clones) and all(clones[k]['visible'] for k in expected),
          'D6 retains visible committed room props rather than globally hiding decoration', clones,layout=True)
    for item in original['envelope']['world']['items']:
        if item['id'] not in expected or item['id'] not in clones:
            continue
        scale = metrics['room']['width']/1000
        surface = metrics['counterSurface']
        bottom = metrics['room']['y']+(surface or 0)+(40*item['y']-38.4)*scale
        prop = clones[item['id']]
        check(ev, surface is not None and old.inside(prop['rect'],metrics['room'],2)
              and abs(prop['rect']['bottom']-bottom)<=1,
              'D6 '+item['id']+' is projected onto the actual counter surface',
              {'prop':prop,'counterSurface':surface,'expected_bottom':bottom},layout=True)
    frame.locator('#growthFridgeOpen').click()
    old.ready(frame)
    reopened = old.state(frame)
    check(ev, without_doors(reopened['envelope']) == without_doors(original['envelope'])
          and reopened['envelope']['world']['doors'] == {k:True for k in DOORS},
          'D6 Open Fridge restores all four real doors and preserves all committed records')
    metrics = capture(page,frame,folder,label+'-D6-return')
    composition(ev,metrics,'Returning from D6')


def door_case(browser, origin, kind, width, height, folder, populated=False, assertions=True):
    label = kind+'-'+str(width)+'x'+str(height)+('-populated' if populated else '')
    ev = {'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
          'reference_checks_required':assertions,'screens':{},
          'fixture':'Existing generated starter, unchanged except actual door toggles' if not populated
                    else 'Explicit disposable QA populated records using the existing living-browser fixture'}
    context = page = None
    try:
        context,page,frame = old.open_page(browser,origin,ENTRIES[kind],width,height,
                                           ev['page_errors'],ev['blocked_requests'])
        if kind == 'opaque':
            grants = (page.locator('iframe').get_attribute('sandbox') or '').split()
            check(ev,'allow-scripts' in grants and 'allow-forms' in grants
                  and 'allow-same-origin' not in grants,
                  'Mobile preview retains its actual opaque sandbox boundary',grants)
        if populated:
            frame.evaluate(living.FIXTURE)
        original = old.state(frame)
        ev['original'] = original
        check(ev, original['key'] == old.KEY and original['available'] == (kind=='native')
              and original['status'] == ('saved' if kind=='native' else 'temporary'),
              'Native storage and opaque temporary preview are explicitly distinguished')
        expected = copy.deepcopy(original['envelope']['world']['doors'])
        for key in DOORS:
            if not expected[key]:
                click_door(frame,key)
                expected[key] = True
        initial = capture(page,frame,folder,label+'-open')
        ev['screens']['open'] = initial
        if assertions:
            composition(ev,initial,'All open')
        for key in DOORS:
            click_door(frame,key)
            expected[key] = False
            preservation(ev,frame,expected,original,'Closing '+key)
            m = capture(page,frame,folder,label+'-closed-'+key)
            ev['screens']['closed-'+key] = m
            if assertions:
                composition(ev,m,'After closing '+key)
        closed = old.state(frame)
        ev['all_closed'] = closed
        page.reload()
        frame = load_frame(page,kind)
        reloaded = old.state(frame)
        ev['reload_snapshot'] = reloaded
        if kind == 'native':
            check(ev, reloaded == closed,
                  'Actual native reload preserves the exact closed world, dates, quantities and stored text')
        else:
            check(ev, not reloaded['available'] and reloaded['status']=='temporary'
                  and reloaded['envelope']['world']['doors'] == {k:True for k in DOORS}
                  and reloaded['envelope'] != closed['envelope'],
                  'Opaque reload is temporary and does not falsely promise persistent door/QA records')
            # Opaque reload starts a new temporary world. Close its actual doors
            # to test reopening, with its own genuine reload snapshot.
            original = reloaded
            expected = copy.deepcopy(reloaded['envelope']['world']['doors'])
            for key in DOORS:
                if expected[key]:
                    click_door(frame,key)
                    expected[key] = False
        ev['screens']['reloaded-closed'] = capture(page,frame,folder,label+'-reloaded-closed')
        if assertions:
            composition(ev,ev['screens']['reloaded-closed'],'Reloaded closed world')
        for key in DOORS:
            click_door(frame,key)
            expected[key] = True
            preservation(ev,frame,expected,original,'Reopening '+key)
            m = capture(page,frame,folder,label+'-reopened-'+key)
            ev['screens']['reopened-'+key] = m
            if assertions:
                composition(ev,m,'After reopening '+key)
        if assertions:
            room_props(ev,page,frame,folder,label,old.state(frame))
    except Exception as error:
        old.Audit(ev).caught(error)
        ev['traceback'] = traceback.format_exc()
        if page:
            page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev, not ev['page_errors'], 'No browser JavaScript error', ev['page_errors'])
        check(ev, not ev['blocked_requests'], 'No provider, remote or network write request', ev['blocked_requests'])
        if context:
            context.close()
    return old.finish_case(ev)


def legacy_closed(browser, origin, width, height, folder):
    label = 'legacy-closed-native-'+str(width)+'x'+str(height)
    fixture = REPO/'tests/fixtures/miniature-legacy-world-v1.json'
    world = json.loads(fixture.read_text())
    world['doors'] = {key:False for key in DOORS}
    play = {'version':1,'meals':[],
            'targets':{k:None for k in ('kcal','carb','protein','fat','fiber','water')},
            'discovered':[],'awarded':[],'owned':[],
            'equipped':{'frozenLeft':None,'frozenRight':None},
            'goal':'collection','plateLabel':'우리 집 부엌'}
    raw = json.dumps({'version':1,'world':world,'play':play},ensure_ascii=False,indent=2)
    ev = {'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
          'reference_checks_required':True,'fixture':'Tracked v1 world with explicitly saved closed doors',
          'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest()}
    context = page = None
    try:
        context,page,frame = old.open_page(browser,origin,ENTRIES['native'],width,height,
                                           ev['page_errors'],ev['blocked_requests'],raw)
        original = old.state(frame)
        check(ev, original['raw']==raw and original['envelope']['world']==world
              and original['envelope']['play']==play,
              'Existing closed v1 world loads without silent rewrite, re-positioning or automatic door opening')
        metrics = capture(page,frame,folder,label+'-boot')
        ev['screen'] = metrics
        composition(ev,metrics,'Existing saved all-closed boot')
        page.reload()
        frame = load_frame(page,'native')
        check(ev, old.state(frame)==original, 'Existing original closed v1 text survives actual reload exactly')
    except Exception as error:
        old.Audit(ev).caught(error)
        ev['traceback'] = traceback.format_exc()
    finally:
        check(ev, not ev['page_errors'], 'Legacy boot has no browser error', ev['page_errors'])
        check(ev, not ev['blocked_requests'], 'Legacy boot makes no provider/write request', ev['blocked_requests'])
        if context:
            context.close()
    return old.finish_case(ev)


def inputs(root):
    return {name:{'bytes':(root/name).stat().st_size,
                  'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()}
            for name in DELIVERIES}


def serve(root):
    server = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(old.Quiet,directory=str(root)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    return server, 'http://127.0.0.1:'+str(server.server_port)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser-executable')
    parser.add_argument('--baseline-root',type=Path)
    args = parser.parse_args()
    root,out = args.root.resolve(),args.output.resolve()
    baseline = args.baseline_root.resolve() if args.baseline_root else None
    if out.is_relative_to(REPO) or out.is_relative_to(root) or root.is_relative_to(out) \
            or (baseline and (out.is_relative_to(baseline) or baseline.is_relative_to(out))):
        parser.error('Evidence must remain outside the repository and frozen input.')
    for directory in (root,baseline):
        if directory:
            for name in DELIVERIES:
                if not (directory/name).is_file():
                    parser.error('Missing generated delivery '+str(directory/name))
    out.mkdir(parents=True,exist_ok=False)
    screens = out/'screens';screens.mkdir()
    start = inputs(root)
    before_inputs = inputs(baseline) if baseline else None
    report = {'scope':'Local disposable Chromium only; real four-door controls, no user storage or production deployment',
              'clock':old.CLOCK.isoformat(),'inputs':start,'cases':[],
              'manual_review':{'required':True,'status':'Not judged by automation; inspect actual PNG material, seams, handles, feet and placement'},
              'delivery_under_1MiB':all(v['bytes']<=1048576 for v in start.values()),'passed':False}
    server,origin = serve(root)
    before_server = None
    def save(row=None):
        if row:
            report['cases'].append(row)
            print(json.dumps({'id':row['id'],'passed':row['passed'],
                              'failed':[c['name'] for c in row['checks'] if not c['passed']]},ensure_ascii=False),flush=True)
        report['inputs_unchanged'] = inputs(root)==start
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright() as pl:
            browser = pl.chromium.launch(executable_path=args.browser_executable or shutil.which('chromium'),
                                         args=['--no-sandbox'])
            if baseline:
                before_server,before_origin = serve(baseline)
                before_dir = out/'before';before_dir.mkdir()
                report['baseline_observations'] = [door_case(browser,before_origin,kind,w,h,before_dir,
                                                             assertions=False)
                                                   for kind in ENTRIES for w,h in PROFILES]
            for kind in ENTRIES:
                for w,h in PROFILES:
                    save(door_case(browser,origin,kind,w,h,screens))
                save(door_case(browser,origin,kind,390,480,screens,populated=True))
            for w,h in PROFILES:
                save(legacy_closed(browser,origin,w,h,screens))
            browser.close()
    finally:
        server.shutdown()
        if before_server:
            before_server.shutdown()
    report['expected_cases'] = 14
    report['complete'] = len(report['cases'])==14 and len({c['id'] for c in report['cases']})==14
    report['baseline_unchanged'] = inputs(baseline)==before_inputs if baseline else None
    report['baseline_complete'] = all(c['passed'] for c in report.get('baseline_observations',[])) if baseline else None
    report['functional_passed'] = all(c['functional_passed'] for c in report['cases'])
    report['layout_passed'] = all(c['reference_composition_checks_passed'] is not False for c in report['cases'])
    report['assertions'] = sum(len(c['checks']) for c in report['cases'])
    report['passed'] = report['complete'] and report['delivery_under_1MiB'] and all(c['passed'] for c in report['cases']) \
        and inputs(root)==start and (not baseline or (report['baseline_unchanged'] and report['baseline_complete']))
    save()
    print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),
                      'assertions':report['assertions'],'result':str(out/'results.json')},ensure_ascii=False),flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':
    main()
