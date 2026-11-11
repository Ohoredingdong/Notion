#!/usr/bin/env python3
"""Verify the eight recipe cards expose truthful one-person nutrition at a glance.

Uses actual frozen delivery HTML and disposable Chromium storage. Reference,
partial, unknown and explicit zero values are checked against the same existing
read-only model used by recipe detail. Screenshots still need visual review.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import traceback

from playwright.sync_api import sync_playwright
import test_kitchen_widget_browser as old
import test_kitchen_living_browser as living
import test_kitchen_closed_browser as closed

REPO = Path(__file__).resolve().parents[1]
DAY = '2026-11-11'
CLOCK = datetime.fromisoformat('2026-11-11T03:00:00+00:00')
KEYS = ('kcal', 'carb', 'protein', 'fat')
PROFILES = tuple((kind, entry, w, h)
                 for kind, entry in old.ENTRIES.items()
                 for w, h in ((320, 360), (390, 480), (720, 800), (800, 600))) + (
    ('app', 'miniature-kitchen-app.html', 390, 844),
    ('app', 'mobile/app.html', 720, 900),
)
SELECTED = {'native-320x360', 'native-720x800', 'opaque-390x480'}
SOURCES = ('test_kitchen_recipe_card_nutrition_browser.py',
           'test_kitchen_widget_browser.py', 'test_kitchen_living_browser.py',
           'test_kitchen_closed_browser.py')
FRIED_RICE = {'kcal': 407.089, 'carb': 65.62429, 'protein': 12.21742, 'fat': 9.73421}
ZUCCHINI_KNOWN = {'kcal': 111.28, 'carb': .36, 'protein': 6.28, 'fat': 9.255}

METRICS = r'''async()=>{''' + old.PAINT_HELPERS + r'''
 const rect=e=>{if(!e||!e.getClientRects().length)return null;const r=e.getBoundingClientRect();
  return{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
 const visible=e=>{if(!rect(e))return false;for(let n=e;n;n=n.parentElement){const s=getComputedStyle(n);
  if(n.hidden||s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0)return false;}return true};
 const inside=e=>{const r=rect(e);if(!r||!visible(e))return false;let l=0,t=0,right=innerWidth,b=innerHeight;
  for(let n=e.parentElement;n;n=n.parentElement){const s=getComputedStyle(n),p=n.getBoundingClientRect();
   if(/hidden|auto|scroll|clip/.test(s.overflowX)){l=Math.max(l,p.x+n.clientLeft);right=Math.min(right,p.x+n.clientLeft+n.clientWidth)}
   if(/hidden|auto|scroll|clip/.test(s.overflowY)){t=Math.max(t,p.y+n.clientTop);b=Math.min(b,p.y+n.clientTop+n.clientHeight)}}
  return r.x>=l-1&&r.right<=right+1&&r.y>=t-1&&r.bottom<=b+1};
 const painted=e=>{const r=rect(e);return r&&[.1,.5,.9].every(x=>[.1,.5,.9].every(y=>{
  const h=document.elementFromPoint(r.x+r.width*x,r.y+r.height*y);return h===e||e.contains(h)}))};
 const fonts=e=>{if(!e)return[];const out=[],walk=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let n;
  while(n=walk.nextNode())if(n.textContent.trim()&&!n.parentElement.closest('.sr-only,[hidden],[aria-hidden=true]')&&visible(n.parentElement))
   out.push(parseFloat(getComputedStyle(n.parentElement).fontSize));return out};
 const num=(e,key)=>{const v=e?.dataset[key];return v===undefined||v===''?null:Number(v)};
 const visibleText=e=>{const out=[],walk=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let n;while(n=walk.nextNode())if(n.textContent.trim()&&visible(n.parentElement)&&parseFloat(getComputedStyle(n.parentElement).fontSize)>0)out.push(n.textContent.trim());for(const n of [e,...e.querySelectorAll('*')])if(visible(n))for(const part of ['::before','::after']){const s=getComputedStyle(n,part);if(s.content!=='none'&&s.content!=='normal'&&parseFloat(s.fontSize)>0)out.push(s.content.slice(1,-1));}return out.join(' ')};
 const grid=document.querySelector('#homeRecommendation .recipe-comparison-grid');
 return {mode:document.body.dataset.mode,clock:new Date().toISOString(),
  shell:rect(document.querySelector('.shell')),grid:rect(grid),docWidth:document.documentElement.scrollWidth,
  viewport:{width:innerWidth,height:innerHeight},scrollY,
  context:[...document.querySelectorAll('#homeRecommendation [data-card-nutrition-context],#homeRecommendation .recipe-card-nutrition-context,#homeRecommendation .recipe-nutrition-legend')].filter(visible).map(visibleText).join(' '),
  cards:await Promise.all([...document.querySelectorAll('#homeRecommendation [data-home-recipe]')].map(async e=>{
   const group=e.querySelector('[data-card-nutrition],.recipe-card-nutrition,.recipe-grid-nutrition');
   return{id:e.dataset.homeRecipe,name:e.querySelector('.recipe-grid-copy strong')?.textContent.trim(),
    rect:rect(e),inside:inside(e),hit:painted(e),text:textRanges(e),aria:e.getAttribute('aria-label'),
    nutritionText:group?.innerText||'',nutritionAria:group?.getAttribute('aria-label')||'',
    photo:visible(e.querySelector('.recipe-grid-photo'))?await paintedPhoto(e.querySelector('.recipe-grid-photo')):null,
    nutrients:Object.fromEntries(['kcal','carb','protein','fat'].map(key=>{
     const n=e.querySelector('[data-card-nutrient="'+key+'"]');return[key,n?{value:num(n,'value'),
      subtotal:num(n,'subtotal'),kind:n.dataset.nutrientKind||n.dataset.kind,text:n.innerText,
      rect:rect(n),inside:inside(n),hit:painted(n),textRanges:textRanges(n),fonts:fonts(n)}:null];}))};}))};
}'''

MODEL = r'''()=>Object.fromEntries(KitchenCatalog.map(recipe=>[recipe.id,
 KitchenRecipeNutrition.estimate(recipe,{flow:KitchenJournal.getWorkflow(),reference:KitchenNutritionReference,day:new Date().toLocaleDateString('en-CA')})]))'''


def check(ev, condition, name, evidence=None):
    ev['checks'].append({'name': name, 'passed': bool(condition), 'evidence': evidence})


def finish(ev):
    check(ev, not ev['page_errors'], 'No browser errors', ev['page_errors'])
    check(ev, not ev['blocked_requests'], 'No external or personal-data requests', ev['blocked_requests'])
    ev['passed'] = all(c['passed'] for c in ev['checks'])
    return ev


def shot(page, folder, label):
    path = folder/(label+'.png')
    page.screenshot(path=str(path), animations='disabled')
    return {'path': str(path), 'sha256': old.digest(path.read_bytes())}


def inspect_cards(ev, frame, expected_unknown=False):
    m, models = frame.evaluate(METRICS), frame.evaluate(MODEL)
    check(ev, len(m['cards']) == 8 and len({c['id'] for c in m['cards']}) == 8,
          'Eight distinct real recipe cards remain in one grid')
    check(ev, m['docWidth'] <= m['viewport']['width']+1 and m['scrollY'] == 0,
          'The widget has no horizontal overflow or outer-page scroll', m['docWidth'])
    check(ev, len({round(c['rect']['x'], 1) for c in m['cards']}) == 2
          and len({round(c['rect']['y'], 1) for c in m['cards']}) == 4,
          'The existing two-column four-row comparison stays intact')
    for card in m['cards']:
        rid = card['id'];box = card['rect']
        check(ev, card['inside'] and card['hit'] and box['width'] >= 44 and box['height'] >= 44,
              rid+' is initially visible with a real 44px card target', box)
        check(ev, bool(card['text']) and all(t['readable'] for t in card['text']),
              rid+' visible comparison text is not clipped', card['text'])
        check(ev, '1인분' in (card['aria'] or '')+' '+card['nutritionAria']+' '+m['context'],
              rid+' has an explicit one-person nutrition basis')
        model = models[rid]['nutrients']
        for key in KEYS:
            metric, expected = card['nutrients'][key], model[key]
            check(ev, metric is not None, rid+' exposes '+key+' without opening detail')
            if metric is None:continue
            check(ev, metric['inside'] and metric['hit'] and metric['textRanges']
                  and all(t['readable'] for t in metric['textRanges'])
                  and metric['fonts'] and min(metric['fonts']) >= 11,
                  rid+' '+key+' is painted, legible and not clipped', metric)
            check(ev, metric['kind'] == expected['kind'] and metric['value'] == expected['value'],
                  rid+' '+key+' uses the unchanged one-person detail calculation',
                  {'card': metric, 'model': expected})
            if expected['kind'] == 'partial':
                check(ev, metric['subtotal'] == expected['knownSubtotal'] and metric['value'] is None
                      and (any(mark in metric['text']+' '+card['nutritionText'] for mark in ('+', '≥', '>0', '확인분', '일부', '부분')) or expected['knownSubtotal']==0 and any(mark in metric['text'] for mark in ('—','–'))),
                      rid+' '+key+' labels the partial subtotal rather than inventing a whole value')
            elif expected['kind'] == 'unknown':
                check(ev, metric['value'] is None and metric['subtotal'] is None
                      and any(word in metric['text'] for word in ('미확인', '미입력', '—', '–')),
                      rid+' '+key+' keeps missing data unknown')
            elif expected['kind'] == 'reference':
                check(ev, any(word in metric['text']+' '+card['nutritionText']+' '+m['context'] for word in ('참고', '추정', '약', '≈')),
                      rid+' '+key+' remains visibly qualified as a reference estimate')
            if expected_unknown:check(ev, metric['kind'] == 'unknown', rid+' '+key+' has no pre-adoption reference')
    return m, models


def profile(browser, before_origin, origin, kind, entry, width, height, folder):
    name = f'{kind}-{width}x{height}';ev={'id':name,'checks':[],'page_errors':[],'blocked_requests':[]}
    contexts=[]
    try:
        for variant, server in [('before', before_origin), ('after', origin)]:
            context,page,frame=old.open_page(browser,server,entry,width,height,ev['page_errors'],ev['blocked_requests'])
            contexts.append(context);initial=old.state(frame);living.tab(frame,'meals');old.ready(frame)
            if name in SELECTED:ev.setdefault('screens',{})[variant]=shot(page,folder,variant+'-'+name)
            if variant == 'before':
                ev['before_state']=initial;ev['before_shell']=frame.evaluate('()=>{const r=document.querySelector(".shell").getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}}')
            else:
                ev['initial_state']=initial;m,models=inspect_cards(ev,frame);ev['cards']=m
                shell={k:m['shell'][k] for k in ('x','y','width','height')}
                check(ev, initial==ev['before_state'] and shell==ev['before_shell'],
                      'Before/after share the same Nov11 raw data, stored envelope and frame')
                for key,value in FRIED_RICE.items():check(ev, models['recipe-1']['nutrients'][key]['value']==value,
                    'Fried rice '+key+' matches independent existing SR28 arithmetic')
                for key,value in ZUCCHINI_KNOWN.items():check(ev, models['recipe-4']['nutrients'][key]['value'] is None
                    and abs(models['recipe-4']['nutrients'][key]['knownSubtotal']-value)<.000001,
                    'Zucchini '+key+' stays a genuinely incomplete ingredient subtotal')
                if name=='native-720x800':
                    for rid in models:
                        frame.locator('#homeRecommendation [data-home-recipe="'+rid+'"]').click();old.ready(frame)
                        if rid=='recipe-1':
                            frame.locator('#recipePortions').fill('4');frame.locator('#recipePortions').dispatch_event('change');old.ready(frame)
                        frame.locator('#tray [data-recipe-tab=nutrition]').click();old.ready(frame)
                        for key in KEYS:
                            item=frame.locator('#tray [data-recipe-nutrient="'+key+'"]')
                            check(ev, item.count()==1 and item.get_attribute('data-nutrient-kind')==models[rid]['nutrients'][key]['kind'],
                                  rid+' '+key+' matches the real one-person detail state')
                            row=models[rid]['nutrients'][key];value=row['value'] if row['value'] is not None else row['knownSubtotal']
                            shown='0.1 미만' if value is not None and 0<value<.1 else format(math.floor(value*10+.5)/10,'g') if value is not None else '미확인'
                            check(ev, shown in item.inner_text().replace(',',''),
                                  rid+' '+key+' detail shows the same one-person number despite a four-person batch',item.inner_text())
                        old.close_tray(frame);living.tab(frame,'meals');old.ready(frame)
                check(ev, old.state(frame)==initial, 'Reading eight cards and details writes no data')
    except Exception as error:
        ev['exception']=str(error);ev['traceback']=traceback.format_exc()
    finally:
        for context in contexts:context.close()
    return finish(ev)


def overrides(browser, origin, kind, entry, folder):
    ev={'id':'override-and-unknown-'+kind,'checks':[],'page_errors':[],'blocked_requests':[]};context=None
    try:
        context,page,frame=old.open_page(browser,origin,entry,390,480,ev['page_errors'],ev['blocked_requests'])
        frame.evaluate('''()=>KitchenJournal.transact(({flow})=>{flow.recipeFacts['recipe-1']={kcal:0,carb:60,protein:0,fat:5,fiber:null,water:null,calcium:null,sodium:null,sugar:null,cost:null,source:'명시적 일회용 QA · 실제 사용자 영양 아님'};})''')
        old.ready(frame);initial=old.state(frame);living.tab(frame,'meals');m,_=inspect_cards(ev,frame)
        card=next(c for c in m['cards'] if c['id']=='recipe-1')
        for key,value in {'kcal':0,'carb':60,'protein':0,'fat':5}.items():
            check(ev, card['nutrients'][key]['kind']=='entered' and card['nutrients'][key]['value']==value,
                  'Explicit user '+key+' including zero overrides the reference without storage edits')
        ev['screens']={'entered':shot(page,folder,'qa-explicit-zero-'+kind)}
        check(ev, old.state(frame)==initial,'Rendering explicit zero preserves the fixture and every other record')
        context.close();context=None
        old.CLOCK=datetime.fromisoformat('2026-11-09T03:00:00+00:00')
        context,page,frame=old.open_page(browser,origin,entry,390,480,ev['page_errors'],ev['blocked_requests'])
        initial=old.state(frame);living.tab(frame,'meals');inspect_cards(ev,frame,expected_unknown=True)
        check(ev, old.state(frame)==initial,'Missing all pre-adoption references does not seed fake nutrition')
    except Exception as error:
        ev['exception']=str(error);ev['traceback']=traceback.format_exc()
    finally:
        old.CLOCK=CLOCK
        if context:context.close()
    return finish(ev)


def inputs(root):
    return {p:{'bytes':(root/p).stat().st_size,'sha256':old.digest((root/p).read_bytes())} for p in closed.DELIVERIES}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--browser-executable',default='/usr/bin/chromium')
    args=parser.parse_args();before,root,out=args.before.resolve(),args.root.resolve(),args.output.resolve()
    if out.is_relative_to(REPO)or any(out.is_relative_to(p)or p.is_relative_to(out)for p in (before,root)):
        parser.error('Evidence must be outside the checkout and frozen input trees.')
    out.mkdir(parents=True,exist_ok=False);folder=out/'screens';folder.mkdir()
    original={'before':inputs(before),'after':inputs(root)};hashes={p:old.digest((REPO/'scripts'/p).read_bytes())for p in SOURCES}
    shutil.copyfile(Path(__file__),out/'executed-test-source.py');old.CLOCK=CLOCK
    report={'scope':'Frozen local Chromium with disposable packaged stock; explicit QA zero fixture only in named cases',
            'clock':CLOCK.isoformat(),'inputs':original,'verification_sources':hashes,'cases':[],'passed':False,
            'manual_review':'Selected real PNGs must be reviewed; not physical Notion/Safari/public execution.'}
    sb,ob=closed.serve(before);sa,oa=closed.serve(root)
    def save(case=None):
        if case:report['cases'].append(case);print(json.dumps({'id':case['id'],'passed':case['passed'],'failed':[c['name']for c in case['checks']if not c['passed']]},ensure_ascii=False),flush=True)
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright()as p:
            browser=p.chromium.launch(executable_path=args.browser_executable,args=['--no-sandbox'])
            for kind,entry,w,h in PROFILES:save(profile(browser,ob,oa,kind,entry,w,h,folder))
            for kind,entry in old.ENTRIES.items():save(overrides(browser,oa,kind,entry,folder))
            browser.close()
    finally:sb.shutdown();sa.shutdown()
    report.update(complete=len(report['cases'])==12,assertions=sum(len(c['checks'])for c in report['cases']),
                  inputs_unchanged=original=={'before':inputs(before),'after':inputs(root)},
                  verification_sources_unchanged=hashes=={p:old.digest((REPO/'scripts'/p).read_bytes())for p in SOURCES},
                  expected_screenshots=8,screenshot_count=len(list(folder.glob('*.png'))),
                  delivery_under_1MiB=all(x['bytes']<=1048576 for h in original.values()for x in h.values()))
    report['screenshots_complete']=report['screenshot_count']==report['expected_screenshots']
    report['passed']=all(report[k]for k in ('complete','inputs_unchanged','verification_sources_unchanged','screenshots_complete','delivery_under_1MiB'))and all(c['passed']for c in report['cases'])
    save();print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'assertions':report['assertions']}))
    raise SystemExit(0 if report['passed']else 1)


if __name__=='__main__':main()
