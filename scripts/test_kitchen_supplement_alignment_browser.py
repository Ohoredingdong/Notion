#!/usr/bin/env python3
"""Exercise the real supplement card in frozen kitchen preview HTML.

The browser and storage are disposable. Fixtures are explicit QA input, never
product defaults. Capture-before is observation only; final acceptance requires
the alignment, unobscured controls, storage and actual-click checks to pass.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import traceback

from playwright.sync_api import sync_playwright
import test_kitchen_closed_browser as closed
import test_kitchen_living_browser as living
import test_kitchen_widget_browser as old


REPO = Path(__file__).resolve().parents[1]
PROFILES = ((320, 360), (390, 480), (599, 700), (600, 700),
            (681, 800), (682, 800), (720, 800), (800, 600))
APP_PROFILES = ((390, 844), (720, 900), (1024, 900))
DAY = living.DAY
ENTRIES = {'native': 'miniature-kitchen-widget.html',
           'opaque': 'mobile/widget.html', 'app': 'miniature-kitchen-app.html'}

FIXTURE = r'''()=>{
 KitchenJournal.transact(({flow})=>{
  flow.supplements=Array.from({length:6},(_,i)=>({
   id:'qa-align-product-'+i,
   name:i===0?'QA 아주 긴 제품 이름을 가진 영양제 표시 확인용':
        i===1?'QA 오메가3 긴 제품명 표시 확인':('QA 명시 입력 제품 '+(i+1)),
   amount:'QA 제품 표시',schedule:'QA 직접 입력 일정',ingredients:'QA 입력 성분 메모',
   days:i===2?['2026-11-05']:i===4?['2026-11-04']:[]
  }));
 });
 return KitchenJournal.getEnvelope();
}'''

METRICS = r'''()=>{
 const box=e=>{if(!e||!e.getClientRects().length)return null;const r=e.getBoundingClientRect();
  return{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
 const visible=e=>{if(!box(e))return false;for(let n=e;n;n=n.parentElement){const c=getComputedStyle(n);
  if(n.hidden||c.display==='none'||c.visibility==='hidden'||Number(c.opacity)===0)return false}return true};
 const ctl=e=>{const rect=box(e);if(!rect)return null;
  const hit=document.elementFromPoint(rect.x+rect.width/2,rect.y+rect.height/2);
  return{rect,label:e.getAttribute('aria-label')||e.textContent.trim(),
   hit:hit===e||e.contains(hit),pressed:e.getAttribute('aria-pressed'),
   product:e.dataset.homeSupplementToday||null,
   title:e.querySelector('span')?.textContent.trim(),
   disabled:e.disabled,scrollWidth:e.scrollWidth,clientWidth:e.clientWidth}};
 const one=s=>document.querySelector(s),rect=s=>box(one(s));
 const shelf=one('#homeSupplementsShelf'),wide=one('#homeSupplementsShelf .shelf-wide'),
  compact=one('#homeSupplementsShelf .shelf-compact'),card=visible(wide)?wide:visible(compact)?compact:null,
  host=one('#fridgeSceneHost'),world=one('#fridgeSceneHost .scene-world');
 const text=card?[...card.querySelectorAll('strong,small')].filter(visible).map(e=>{
  const r=document.createRange();r.selectNodeContents(e);return{text:e.textContent.trim(),
   rect:box(e),ranges:[...r.getClientRects()].map(r=>({x:r.x,y:r.y,right:r.right,bottom:r.bottom}))};
 }):[];
 return{viewport:{width:innerWidth,height:innerHeight},mode:document.body.dataset.mode,
  home:document.body.dataset.home,screen:one('#panel-fridge').dataset.screenId,
  document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,scrollY},
  shell:rect('.shell'),host:box(host),world:box(world),fridge:rect('#fridgeSceneHost .fridge-stage'),
  balance:rect('#dailyBalance'),brand:rect('.masthead .brand'),actions:rect('.masthead .header-actions'),
  shelf:{rect:box(shelf),visible:visible(shelf),card:box(card),kind:card===wide?'wide':card===compact?'compact':null,
   text:card?.textContent.trim(),textRanges:text,controls:card?[...card.querySelectorAll('button')].filter(visible).map(ctl):[],
   compactControl:card===compact?ctl(compact):null,
   bottleGroup:box(shelf.querySelector('.shelf-bottles')),
   bottles:[...shelf.querySelectorAll('[data-home-supplement-today]')].filter(visible).map(ctl),
   shadow:card?getComputedStyle(card).boxShadow:null},
  balanceText:[...document.querySelectorAll('#dailyBalance [data-balance]')].map(e=>({
   key:e.dataset.balance,text:e.textContent.trim(),rect:box(e)}))};
}'''


def check(ev, ok, name, detail=None, layout=False):
    old.Audit(ev).check(ok, name, detail,
                        category='reference-composition' if layout else 'functional')


def center(rect):
    return rect['x']+rect['width']/2


def overlap(a, b):
    if not a or not b:
        return 0
    return max(0, min(a['right'], b['right'])-max(a['x'], b['x'])) * \
        max(0, min(a['bottom'], b['bottom'])-max(a['y'], b['y']))


def inside(a, b, tolerance=1):
    return bool(a and b and a['x'] >= b['x']-tolerance and a['y'] >= b['y']-tolerance
                and a['right'] <= b['right']+tolerance and a['bottom'] <= b['bottom']+tolerance)


def capture(page, frame, folder, label):
    old.ready(frame)
    metrics = frame.evaluate(METRICS)
    page.screenshot(path=str(folder/(label+'.png')), animations='disabled', caret='hide')
    return metrics


def layout(ev, m, label, populated):
    card,host = m['shelf']['card'],m['host']
    check(ev, m['shelf']['visible'] and bool(card) and bool(host),
          label+' actual supplement card is visible in the fridge scene', m['shelf'], True)
    if not card or not host:
        return
    check(ev, abs(center(card)-center(host)) <= 1,
          label+' card is centered on its actual scene host, not asymmetric CSS insets',
          {'card_center':center(card),'host_center':center(host)}, True)
    check(ev, inside(card,host), label+' card stays inside the actual scene host',
          {'card':card,'host':host}, True)
    check(ev, card['width'] >= 44 and card['height'] >= 44,
          label+' card retains a readable actionable size', card, True)
    # Borders may touch; positive-area intersections are not accepted.
    for key in ('balance','brand','actions','fridge'):
        check(ev, overlap(card,m[key]) <= 1,
              label+' card does not cover '+key, {'card':card,'other':m[key],'area':overlap(card,m[key])}, True)
    if m['mode'] == 'widget':
        check(ev, m['document']['width'] <= m['viewport']['width']+1
              and m['document']['height'] <= m['viewport']['height']+1
              and m['document']['scrollY'] == 0,
              label+' widget introduces no document overflow', m['document'], True)
        check(ev, m['shelf']['kind'] == ('compact' if host['width'] <= 679 else 'wide'),
              label+' rendered variant follows actual container width on both sides of680px',
              {'host_width':host['width'],'variant':m['shelf']['kind']}, True)
    controls = [m['shelf']['compactControl']] if m['shelf']['kind']=='compact' else m['shelf']['controls']
    check(ev, bool(controls),label+' has an actual supplement control')
    for c in controls:
        if not c:
            continue
        check(ev,c['rect']['width']>=43.99 and c['rect']['height']>=43.99,
              label+' '+c['label']+' preserves44px touch target', c['rect'],True)
        check(ev, c['hit'] and inside(c['rect'],card),
              label+' '+c['label']+' is unobscured and actually clickable',c,True)
    for t in m['shelf']['textRanges']:
        check(ev,inside(t['rect'],card)and all(inside(r,card)for r in t['ranges']),
              label+' visible label is not clipped by its card: '+t['text'],t,True)
    if populated:
        check(ev,'1 / 6' in m['shelf']['text'],label+' count derives from the six explicit QA products')
        if m['shelf']['kind']=='wide':
            check(ev,m['shelf']['bottleGroup'] is not None and
                  abs(center(m['shelf']['bottleGroup'])-center(card))<=1,
                  label+' product group stays centered despite unequal label and action text',
                  {'group':m['shelf']['bottleGroup'],'card':card},True)
            check(ev,len(m['shelf']['bottles'])==4,
                  label+' exposes the existing first-four products and a management route')
            check(ev,all(c['product']=='qa-align-product-'+str(i)for i,c in enumerate(m['shelf']['bottles'])),
                  label+' preserves product identity despite long visible names')
            check(ev,'QA 아주 긴 제품 이름을 가진 영양제 표시 확인용' in m['shelf']['bottles'][0]['label'],
                  label+' exposes the full product name through its accessible label')
    else:
        check(ev,'제품 등록'in m['shelf']['text']or'영양제 등록'in m['shelf']['text'],
              label+' empty card offers registration without fake products')
        check(ev,not m['shelf']['bottles'],label+' empty card has no fabricated bottle')


def reload_frame(page, kind):
    frame=page.locator('iframe').element_handle().content_frame()if kind=='opaque'else page.main_frame
    frame.wait_for_function('window.MiniKitchen&&window.KitchenHome&&window.KitchenJournal')
    old.ready(frame)
    return frame


def journey(browser,origin,kind,width,height,folder,observe=False):
    label=kind+'-'+str(width)+'x'+str(height)
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
        'reference_checks_required':not observe,'observation_only':observe,'screens':{},
        'fixture':'Existing empty starter followed by six explicit disposable QA product records, including long names'}
    context=page=None
    try:
        context,page,frame=old.open_page(browser,origin,ENTRIES[kind],width,height,
                                        ev['page_errors'],ev['blocked_requests'])
        original=old.state(frame);ev['empty_state']=original
        if not observe:
            check(ev,not original['envelope']['workflow']['supplements'],'Product starter has no fake supplement')
        empty=capture(page,frame,folder,label+'-empty');ev['screens']['empty']=empty
        if not observe:
            layout(ev,empty,'Empty',False)
            old.preservation(old.Audit(ev),frame,original,'Rendering empty shelf preserves the exact original state')
        # Existing explicit QA meals/facts make the nutrition header use its
        # populated height as well; a products-only fixture misses that state.
        frame.evaluate(living.FIXTURE)
        frame.evaluate(FIXTURE)
        populated=old.state(frame);ev['populated_state']=populated
        m=capture(page,frame,folder,label+'-six-products');ev['screens']['six-products']=m
        if not observe:
            layout(ev,m,'Six products',True)
            old.preservation(old.Audit(ev),frame,populated,'Rendering long product names changes no stored field')
            bottle=frame.locator('#homeSupplementsShelf [data-home-supplement-today="qa-align-product-0"]:visible')
            if bottle.count():
                bottle.click()
            else:
                frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
                frame.locator('#homeSupplements [data-home-supplement="qa-align-product-0"]').check()
            old.ready(frame)
            expected=copy.deepcopy(populated['envelope'])
            expected['workflow']['supplements'][0]['days']=[DAY]
            check(ev,old.state(frame)['envelope']==expected,
                  'Actual today control modifies only the selected product day once')
            living.tab(frame,'fridge')
            undo=frame.locator('#homeSupplementsShelf [data-home-supplement-today="qa-align-product-0"]:visible')
            if undo.count():
                undo.click()
            else:
                frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
                frame.locator('#homeSupplements [data-home-supplement="qa-align-product-0"]').uncheck()
            old.ready(frame)
            check(ev,old.state(frame)['envelope']==populated['envelope'],
                  'Unchecking today restores the exact six-product state and other records')
            living.tab(frame,'fridge')
            frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
            check(ev,frame.locator('#homeSupplements:visible').count()==1,
                  'Actual centered management control opens supplement records')
            living.tab(frame,'kitchen','decor')
            check(ev,not frame.evaluate(METRICS)['shelf']['visible'],
                  'Supplement card is absent on the unrelated room editor')
            frame.locator('#homeDecor [data-decor-apply]').click()
            applied=capture(page,frame,folder,label+'-applied-room')
            ev['screens']['applied-room']=applied
            check(ev,applied['screen']=='D6' and not applied['shelf']['visible'],
                  'Actual Apply also hides the card on the committed D6 room view')
            check(ev,closed.without_doors(old.state(frame)['envelope'])==closed.without_doors(populated['envelope']),
                  'Applying the unchanged room preserves every product, record and prop coordinate')
            frame.locator('#growthFridgeOpen').click()
            old.ready(frame)
            check(ev,old.state(frame)['envelope']==populated['envelope'],
                  'Visiting management and room editor preserves all quantities, dates, positions and records')
            stable=old.state(frame);page.reload();frame=reload_frame(page,kind);after=old.state(frame)
            if kind!='opaque':
                check(ev,after==stable,'Native reload preserves exact stored text, product days and other records')
            else:
                check(ev,not after['available']and after['status']=='temporary'
                      and not after['envelope']['workflow']['supplements'],
                      'Opaque preview explicitly resets temporary QA data on actual reload')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No browser JavaScript error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'No remote provider or network write',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline-evidence',type=Path,
                        help='Completed --observe-only evidence folder, not a generated HTML root')
    parser.add_argument('--browser-executable')
    parser.add_argument('--observe-only',action='store_true',help='Capture rejected baseline only, without final acceptance')
    args=parser.parse_args();root,out=args.root.resolve(),args.output.resolve()
    if out.is_relative_to(REPO)or out.is_relative_to(root)or root.is_relative_to(out):
        parser.error('Evidence must stay outside the checkout and frozen generated input')
    out.mkdir(parents=True,exist_ok=False);screens=out/'screens';screens.mkdir()
    start=closed.inputs(root);report={'scope':'Disposable local Chromium; actual generated HTML and controls only',
      'clock':old.CLOCK.isoformat(),'inputs':start,'cases':[],'passed':False,
      'manual_review':'Required independently; geometry pass does not assert design approval',
      'observation_only':args.observe_only,
      'verification_source':{'path':Path(__file__).name,
        'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    server,origin=closed.serve(root)
    def save(row=None):
        if row:
            report['cases'].append(row)
            print(json.dumps({'id':row['id'],'passed':row['passed'],
             'failed':[c['name']for c in row['checks']if not c['passed']]},ensure_ascii=False),flush=True)
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright()as p:
            browser=p.chromium.launch(executable_path=args.browser_executable or shutil.which('chromium'),args=['--no-sandbox'])
            for kind in ('native','opaque'):
                for width,height in PROFILES:save(journey(browser,origin,kind,width,height,screens,args.observe_only))
            for width,height in APP_PROFILES:save(journey(browser,origin,'app',width,height,screens,args.observe_only))
            if not args.observe_only:
                for kind in ('native','opaque'):
                    save(living.supplement_case(browser,origin,kind,720,800,screens))
                    save(living.supplement_registration_case(browser,origin,kind,screens))
            browser.close()
    finally:server.shutdown()
    report['complete']=len(report['cases'])==(19 if args.observe_only else 23)
    report['inputs_unchanged']=closed.inputs(root)==start
    report['delivery_under_1MiB']=all(v['bytes']<=1048576 for v in start.values())
    report['assertions']=sum(len(c['checks'])for c in report['cases'])
    report['passed']=not args.observe_only and report['complete']and report['inputs_unchanged'] \
        and report['delivery_under_1MiB']and all(c['passed']for c in report['cases'])
    report['observation_succeeded']=args.observe_only and report['complete']and report['inputs_unchanged'] \
        and all(c['passed']for c in report['cases'])
    if args.baseline_evidence:
        baseline=args.baseline_evidence.resolve();old_report=json.loads((baseline/'results.json').read_text())
        baseline_cases={c['id']:c for c in old_report['cases']}
        report['baseline_comparison']=[{'id':c['id'],
          'empty_state_equal':c['empty_state']==baseline_cases[c['id']]['empty_state'],
          'populated_state_equal':c['populated_state']==baseline_cases[c['id']]['populated_state']}
          for c in report['cases']if c['id']in baseline_cases]
        report['baseline_states_equal']=len(report['baseline_comparison'])==19 and all(
            c['empty_state_equal']and c['populated_state_equal']for c in report['baseline_comparison'])
        report['baseline_complete']=old_report['complete']and old_report['inputs_unchanged'] \
            and all(c['passed']for c in old_report['cases'])
        report['passed']=report['passed']and report['baseline_states_equal']and report['baseline_complete']
    save();print(json.dumps({k:report.get(k)for k in ('passed','complete','assertions','inputs_unchanged','baseline_states_equal')},ensure_ascii=False),flush=True)
    raise SystemExit(0 if report['passed']or report['observation_succeeded']else 1)


if __name__=='__main__':main()
