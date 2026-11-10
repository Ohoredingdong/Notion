#!/usr/bin/env python3
"""Verify dated recipe estimates and the real fitted detail/price editor.

Runs only against immutable local delivery files with disposable browser data.
Price expectations use separate arithmetic, not the production estimate result.
Screenshots still require independent visual review; no real-device, live-price,
OCR, personal-storage, public HTMLPreview or production-deployment claim is made.
"""
import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import traceback

from playwright.sync_api import sync_playwright
import test_kitchen_widget_browser as old
import test_kitchen_living_browser as living
import test_kitchen_closed_browser as closed


REPO = Path(__file__).resolve().parents[1]
DAY = '2026-11-10'
CLOCK = datetime.fromisoformat('2026-11-10T03:00:00+00:00')
PROFILES = ((320, 360), (390, 480), (720, 800), (800, 600))
APP_PROFILES = ((390, 844), (720, 900))
EXPECTED = {
    'recipe-1': 9480/15 + 3733/1500*50 + 2000,
    'recipe-2': 1680/300*150 + 990/4 + 3733/1500*50,
    # Existing quantity parsing stores one-third at six decimal places; keep
    # that documented domain precision while deriving prices independently.
    'recipe-4': 990*round(1/3, 6) + 9480/15,
    'recipe-5': 3980/340*30 + 9480/15*2,
    'recipe-6': 1680/300*150 + 3733/1500*50,
    'recipe-7': 1680/300*150 + 2140/100*70 + 3733/1500*50,
}
PARTIAL = 9480/15*2 + 8480/14
SOURCES = ('test_kitchen_recipe_detail_browser.py', 'test_kitchen_widget_browser.py',
           'test_kitchen_living_browser.py', 'test_kitchen_closed_browser.py')

METRICS = r'''async()=>{''' + old.PAINT_HELPERS + r'''
 const visible=e=>{if(!e||!e.getClientRects().length)return false;
  for(let n=e;n;n=n.parentElement){const c=getComputedStyle(n);if(n.hidden||c.display==='none'||c.visibility==='hidden'||Number(c.opacity)===0)return false;}return true;};
 const rect=e=>{if(!e||!e.getClientRects().length)return null;const r=e.getBoundingClientRect();
  return{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
 const clipped=e=>{const r=rect(e);if(!r||!visible(e))return false;
  let l=0,t=0,right=innerWidth,b=innerHeight;
  for(let n=e.parentElement;n;n=n.parentElement){const c=getComputedStyle(n),p=rect(n);if(!p)continue;
   if(/hidden|auto|scroll|clip/.test(c.overflowX)){l=Math.max(l,p.x+n.clientLeft);right=Math.min(right,p.x+n.clientLeft+n.clientWidth);}
   if(/hidden|auto|scroll|clip/.test(c.overflowY)){t=Math.max(t,p.y+n.clientTop);b=Math.min(b,p.y+n.clientTop+n.clientHeight);}}
  return r.x>=l-1&&r.right<=right+1&&r.y>=t-1&&r.bottom<=b+1;};
 const ctl=e=>{const r=rect(e);if(!r)return null;const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
  return{rect:r,label:e.getAttribute('aria-label')||e.textContent.trim(),hit:hit===e||e.contains(hit),inside:clipped(e),disabled:e.disabled};};
 const number=e=>{const v=e?.dataset.value;return v===undefined||v===''?null:Number(v);};
 const cost=document.querySelector('#tray .recipe-cost-summary');
 const pane=[...document.querySelectorAll('#tray [data-recipe-panel]')].find(visible);
 return{mode:document.body.dataset.mode,viewport:{width:innerWidth,height:innerHeight},
  shell:rect(document.querySelector('.shell')),document:{width:document.documentElement.scrollWidth,scrollY},
  monthly:{control:ctl(document.querySelector('#recipeMonthBudget')),
   text:document.querySelector('#recipeMonthBudget')?.textContent.trim(),
   label:document.querySelector('#recipeMonthBudget')?.getAttribute('aria-label')},
  cards:await Promise.all([...document.querySelectorAll('#homeRecommendation [data-home-recipe]')].map(async e=>{
   const c=e.querySelector('[data-recipe-cost]');return{id:e.dataset.homeRecipe,control:ctl(e),
    name:e.querySelector('.recipe-grid-copy strong')?.textContent.trim(),text:textRanges(e),
    cost:{value:number(c),kind:c?.dataset.costKind,scope:c?.dataset.costScope,
     subtotal:c?.dataset.subtotal?Number(c.dataset.subtotal):null,text:c?.textContent.trim(),
     font:c?.querySelector('b')?parseFloat(getComputedStyle(c.querySelector('b')).fontSize):null},
    photo:await paintedPhoto(e.querySelector('.recipe-grid-photo'))};})),
  detail:document.querySelector('#tray[open]')?{
   route:document.querySelector('#tray').dataset.workflowRoute,tray:rect(document.querySelector('#tray')),
   contentWidth:(()=>{const e=document.querySelector('#tray'),s=getComputedStyle(e);return e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight);})(),
   name:document.querySelector('#tray .recipe-detail-name')?.textContent.trim(),
   nameFont:document.querySelector('#tray .recipe-detail-name')?parseFloat(getComputedStyle(document.querySelector('#tray .recipe-detail-name')).fontSize):null,
   time:document.querySelector('#tray .recipe-time')?.textContent.trim(),
   photo:document.querySelector('#tray .recipe-hero')?await paintedPhoto(document.querySelector('#tray .recipe-hero')):null,
   cost:cost?{kind:cost.dataset.costKind,scope:cost.dataset.costScope,
    total:cost.dataset.costTotal===''?null:Number(cost.dataset.costTotal),
    subtotal:cost.dataset.costSubtotal===''?null:Number(cost.dataset.costSubtotal),
    text:cost.innerText,value:cost.querySelector('strong')?.textContent.trim(),
    rect:rect(cost),inside:clipped(cost),font:cost.querySelector('strong')?parseFloat(getComputedStyle(cost.querySelector('strong')).fontSize):null}:null,
   portion:ctl(document.querySelector('#recipePortions')),edit:ctl(document.querySelector('#tray [data-wf=recipeCost]')),
   reference:document.querySelector('#tray .recipe-reference-note')?.innerText.trim(),
   context:document.querySelector('#tray .recipe-cost-context')?.innerText,
   tabs:[...document.querySelectorAll('#tray [data-recipe-tab]')].map(e=>({id:e.dataset.recipeTab,control:ctl(e),selected:e.getAttribute('aria-selected')})),
   pane:pane?{id:pane.dataset.recipePanel,rect:rect(pane),scrollHeight:pane.scrollHeight,clientHeight:pane.clientHeight,
    text:pane.innerText}:null,
   feedback:{text:document.querySelector('#tray .workflow-feedback')?.textContent.trim(),
    inside:clipped(document.querySelector('#tray .workflow-feedback'))},
   actions:[...document.querySelectorAll('#tray .recipe-detail-actions>button')].map(e=>({route:e.dataset.wf,control:ctl(e)})),
   editor:document.querySelector('#tray [data-wf-form=recipeCost]')?{
    input:ctl(document.querySelector('#tray [name=cost]')),
    save:ctl(document.querySelector('#tray [data-wf-form=recipeCost] [type=submit]'))}:null,
   fields:[...document.querySelectorAll('#tray .recipe-ingredient-list>div')].map(e=>{
    const r=rect(e),name=e.querySelector('.recipe-ingredient-copy>strong'),required=e.querySelector('.recipe-ingredient-copy>span');
    return{text:e.innerText,rect:r,inside:clipped(e),
     fonts:[name,required].filter(Boolean).map(n=>parseFloat(getComputedStyle(n).fontSize)),
     primaryText:[...textRanges(name),...textRanges(required)],
     unobscured:r&&[.1,.5,.9].every(fx=>[.1,.5,.9].every(fy=>{const hit=document.elementFromPoint(r.x+r.width*fx,r.y+r.height*fy);return hit===e||e.contains(hit)}))};})
  }:null};
}'''

QA_FACTS = r'''()=>{
 const before=KitchenJournal.getEnvelope();
 KitchenJournal.transact(({flow})=>{
  flow.recipeFacts['recipe-1']={kcal:455,carb:60,protein:20,fat:15,fiber:null,water:null,
   calcium:127,sodium:13,sugar:4,cost:2100,source:'명시적 격리 QA · 영양/비용 원문 보존'};
  flow.budgets['2026-11']=300000;
  flow.expenses.push({id:'qa-existing-expense',day:'2026-11-09',name:'QA 실제 구매 기록',amount:128000,category:'groceries'});
 });return{before,after:KitchenJournal.getEnvelope()};
}'''

RECEIPT = r'''()=>{
 const before=KitchenJournal.getEnvelope();
 KitchenJournal.transact(({flow})=>{
  const rows=[['계란','10개',1000],['양파','4개',800],['식용유','10작은술',1000],['간장','10작은술',500],['밥','10공기',6000]];
  flow.shopping=rows.map(([name,quantity,estimate],n)=>({id:'qa-price-'+n,name,quantity,estimate,checked:true}));
  KitchenWorkflowModel.commitPurchase(flow,{purchaseId:'qa-original-packs',day:'2026-11-09',amount:9000,
   items:flow.shopping.map(row=>({shoppingId:row.id,quantity:row.quantity,amount:row.estimate}))});
 });return{before,after:KitchenJournal.getEnvelope()};
}'''


def check(ev, passed, name, detail=None, visual=False):
    old.Audit(ev).check(passed, name, detail,
                        category='reference-composition' if visual else 'functional')


def target(ev, control, name, minimum=44):
    r = control and control['rect']
    check(ev, bool(r and r['width'] >= minimum-.5 and r['height'] >= minimum-.5
                  and control['inside'] and control['hit'] and not control['disabled']),
          name+' has a visible, unclipped '+str(minimum)+'px real hit target', control, visual=True)


def readonly(ev, frame, original, name):
    check(ev, old.state(frame) == original, name)


def capture(ev, page, frame, folder, name):
    old.ready(frame)
    m = frame.evaluate(METRICS)
    page.screenshot(path=str(folder/(name+'.png')), animations='disabled')
    ev.setdefault('screens', {})[name] = m
    return m


def open_case(browser, origin, entry, width, height, ev):
    return old.open_page(browser, origin, entry, width, height, ev['page_errors'], ev['blocked_requests'])


def recipe(frame, rid='recipe-1'):
    living.tab(frame, 'meals')
    frame.locator('#homeRecommendation [data-home-recipe="'+rid+'"]').click()
    old.ready(frame)


def cards(ev, m, entered=False):
    check(ev, len(m['cards']) == 8 and len({c['id'] for c in m['cards']}) == 8,
          'Eight genuine recipe cards remain initially available')
    for c in m['cards']:
        rid = c['id'];v = c['cost']
        target(ev, c['control'], rid+' card')
        check(ev, c['photo'] and c['photo']['atlas']['decoded'], rid+' has decoded real food art')
        check(ev, v['font'] and v['font'] >= 11, rid+' exposes a readable cost state', v, visual=True)
        if entered and rid == 'recipe-1':
            check(ev, v['kind'] == 'entered' and v['scope'] == 'recipe' and v['value'] == 2100
                  and '2,100' in v['text'], 'User-entered cost overrides the public reference estimate', v)
        elif rid in EXPECTED:
            check(ev, v['scope'] == 'main' and v['kind'] == 'reference' and v['value'] is not None
                  and abs(v['value']-EXPECTED[rid]) < .00001,
                  rid+' shows the independently calculated dated main-ingredient estimate', v)
            rounded = round(EXPECTED[rid]/100)*100
            check(ev, '주재료' in v['text'] and f'{rounded:,}' in v['text'],
                  rid+' labels the rounded amount as main ingredients rather than a whole cash expense', v)
        elif rid == 'recipe-8':
            check(ev, v['kind'] == 'partial' and v['value'] is None and v['subtotal'] is not None
                  and abs(v['subtotal']-PARTIAL) < .00001 and '+' in v['text'],
                  'Unpriced tomato remains an incomplete amount, never a fabricated total', v)
        else:
            check(ev, rid == 'recipe-3' and v['kind'] == 'unknown' and v['value'] is None
                  and v['subtotal'] is None and '정보 필요' in v['text'],
                  'Missing chicken and tomato prices remain unknown instead of fake zeroes', v)


def detail_geometry(ev, m, rid='recipe-1', expected=None, observe=False):
    d = m['detail']
    check(ev, d and d['route'] == 'recipe' and d['name'], 'The actual recipe-detail workflow opens')
    if not d:return
    check(ev, old.inside(d['tray'], m['shell']) and m['document']['width'] <= m['viewport']['width']+1
          and m['document']['scrollY'] == 0, 'Detail stays in the fitted widget without a page overflow', d['tray'], visual=True)
    if observe:return
    check(ev, d['photo'] and d['photo']['atlas']['decoded'] and d['photo']['recipe'] == rid,
          'Detail uses the matching decoded recipe photograph', d['photo'])
    check(ev, d['time'] and '분' in d['time'], 'The actual cooking time remains visible with its recipe photograph', d['time'])
    check(ev, d['nameFont'] >= (20 if d['contentWidth'] >= 560 else 14),
          'Detail name uses the appropriate reading scale', d['nameFont'], visual=True)
    check(ev, d['cost'] and d['cost']['inside'] and d['cost']['font'] >= 16,
          'Cost is initially visible and prominent rather than a tiny secondary line', d['cost'], visual=True)
    if expected is not None:
        check(ev, d['cost']['total'] is not None and abs(d['cost']['total']-expected) < .00001,
              'Detail amount matches independent serving arithmetic', d['cost'])
    target(ev, d['edit'], 'Fast recipe-cost entry')
    target(ev, d['portion'], 'Visible recipe serving input')
    check(ev, {x['route'] for x in d['actions']} == {'planRecipe', 'logMeal'},
          'Planning and actual-meal actions remain separate')
    for x in d['actions']:target(ev, x['control'], x['route'])


def check_basis(ev, frame):
    basis = frame.locator('#tray .recipe-cost-basis')
    check(ev, basis.count() == 1, 'One actual cost-basis disclosure remains available')
    if not basis.count():return
    if basis.get_attribute('open') is None:basis.locator('summary').click()
    old.ready(frame)
    text = basis.inner_text()
    check(ev, '200g' in text and '210g' in text and '계산 가정' in text,
          'Onion weight and rice-serving assumptions are explicit, not disguised observations', text)
    check(ev, '계산 가정: 계산 가정:' not in text,
          'Arithmetic assumptions carry one readable label rather than repeated prefixes', text)
    check(ev, '9480' in text.replace(',', '') or '계란' in text,
          'The basis identifies actual ingredient rows rather than a made-up total', text)
    summary = frame.locator('#tray .recipe-cost-summary').inner_text()
    note = frame.locator('#tray .recipe-reference-note').inner_text()
    check(ev, '양념' in summary+note and ('10.23' in note or '2026.10.23' in note),
          'The visible summary distinguishes pantry exclusions and the observation day',
          {'summary':summary,'visible_note':note})
    check(ev, '2026-10-23' in text and '실제 지출' in text,
          'The expanded basis exposes the full observation date and never calls the estimate a cash entry',text)


def finish(ev, context):
    check(ev, not ev['page_errors'], 'No browser JavaScript error', ev['page_errors'])
    check(ev, not ev['blocked_requests'], 'No provider or personal-data request', ev['blocked_requests'])
    if context:context.close()
    return old.finish_case(ev)


def layout_case(browser, origin, entry, width, height, folder, observe):
    label=('opaque' if entry=='mobile/widget.html' else 'app' if 'app' in entry else 'native')+'-'+str(width)+'x'+str(height)
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],'reference_checks_required':True};context=page=None
    try:
        context,page,frame=open_case(browser,origin,entry,width,height,ev)
        original=old.state(frame);ev['initial_state']=original
        living.tab(frame,'meals');m=capture(ev,page,frame,folder,label+'-cards')
        if not observe:
            cards(ev,m);target(ev,m['monthly']['control'],'Actual monthly-spending entry')
            check(ev,'0원' in m['monthly']['label'] and not original['envelope']['workflow']['expenses'],
                  'Default actual spending remains zero while the reference estimates are nonzero',m['monthly'])
        readonly(ev,frame,original,'Opening the estimate cards never adds facts or spending')
        frame.locator('#homeRecommendation [data-home-recipe="recipe-1"]').click()
        m=capture(ev,page,frame,folder,label+'-ingredients')
        detail_geometry(ev,m,expected=None if observe else EXPECTED['recipe-1'],observe=observe)
        if not observe:
            check_basis(ev,frame)
            frame.locator('#recipePortions').focus();old.ready(frame)
            focused=frame.evaluate(METRICS)
            target(ev,focused['detail']['portion'],'Keyboard-focused serving control after expanding the cost basis')
            for tab in focused['detail']['tabs']:
                frame.locator('#tray [data-recipe-tab="'+tab['id']+'"]').focus();old.ready(frame)
                current=frame.evaluate(METRICS)
                control=next(t['control']for t in current['detail']['tabs']if t['id']==tab['id'])
                target(ev,control,'Keyboard-focused '+tab['id']+' tab after expanding the cost basis')
            for index in range(frame.locator('#tray .recipe-ingredient-list>div').count()):
                row=frame.locator('#tray .recipe-ingredient-list>div').nth(index)
                # "if needed" checks clipping but ignores sticky tabs. Center
                # each row in its actual scroll viewport, then retain hit tests
                # against the painted tabs/footer rather than treating clipping
                # geometry alone as proof that its text can be read.
                row.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest'})")
                observed=frame.evaluate(METRICS)['detail']['fields'][index]
                check(ev,observed['inside'] and observed['unobscured'] and len(observed['fonts'])==2
                      and min(observed['fonts'])>=12 and observed['primaryText']
                      and all(t['readable']for t in observed['primaryText']),
                      'Every ingredient name and required amount is readable through the actual unclipped detail scroll',observed,visual=True)
            portion=frame.locator('#recipePortions');old.reveal(portion).fill('2');portion.dispatch_event('change');old.ready(frame)
            m=capture(ev,page,frame,folder,label+'-two-servings')
            check(ev,m['detail']['cost']['total'] is not None and abs(m['detail']['cost']['total']-EXPECTED['recipe-1']*2)<.00001,
                  'Changing servings scales displayed estimate only')
            readonly(ev,frame,original,'Viewing two servings leaves exact stored stock, meals, prices and spending untouched')
            old.reveal(frame.locator('#recipePortions')).fill('1');frame.locator('#recipePortions').dispatch_event('change');old.ready(frame)
            for bad in ['0','0.005','101','']:
                invalid=old.reveal(frame.locator('#recipePortions'));invalid.fill(bad);invalid.dispatch_event('change');old.ready(frame)
                invalid_state=frame.evaluate('''()=>({marked:document.querySelector('#recipePortions').getAttribute('aria-invalid'),
                  valid:document.querySelector('#recipePortions').validity.valid,
                  actions:[...document.querySelectorAll('.recipe-detail-actions button,[data-wf="missingToShopping"]')].map(b=>b.disabled)})''')
                check(ev,invalid_state['marked']=='true' and not invalid_state['valid']
                      and len(invalid_state['actions'])>=3 and all(invalid_state['actions']),
                      'Invalid serving '+(bad or 'empty')+' blocks plan/meal/shopping instead of using stale values',invalid_state)
                invalid_metrics=frame.evaluate(METRICS)
                check(ev,invalid_metrics['detail']['feedback']['text'] and invalid_metrics['detail']['feedback']['inside'],
                      'Serving validation explains the actual error inside the fitted detail',invalid_metrics['detail']['feedback'],visual=True)
                readonly(ev,frame,original,'Invalid servings cannot mutate any stored record')
                invalid.fill('1');invalid.dispatch_event('change');old.ready(frame)
                check(ev,frame.evaluate('document.querySelector("#recipePortions").getAttribute("aria-invalid")===null&&[...document.querySelectorAll(".recipe-detail-actions button")].every(b=>!b.disabled)'),
                      'Correcting the serving restores the actual main actions')
        for tab in ['steps','nutrition']:
            frame.locator('#tray [data-recipe-tab="'+tab+'"]').click();old.ready(frame)
            m=capture(ev,page,frame,folder,label+'-'+tab)
            check(ev,frame.locator('#tray [data-recipe-panel="'+tab+'"]:visible').count()==1,
                  tab+' opens the genuine detail content')
            if not observe:
                for action in m['detail']['actions']:target(ev,action['control'],tab+' '+action['route'])
        readonly(ev,frame,original,'All detail tabs and ingredient scrolling preserve exact source records')
        old.close_tray(frame)
        if not observe:
            recipe(frame,'recipe-5')
            yogurt_basis=frame.locator('#tray .recipe-cost-basis')
            yogurt_basis.locator('summary').click();old.ready(frame)
            yogurt_text=yogurt_basis.inner_text()
            check(ev,'요거트' in yogurt_text and '15g' in yogurt_text and '계산 가정' in yogurt_text
                  and '계산 가정: 계산 가정:' not in yogurt_text,
                  'Yogurt spoon-to-weight arithmetic is explicitly an assumption rather than a purchased or measured fact',yogurt_text)
            readonly(ev,frame,original,'Reading yogurt conversion assumptions never changes persisted units or stock')
            old.close_tray(frame)
            frame.evaluate(QA_FACTS);qa=old.state(frame);check(ev,qa['envelope']['world']==original['envelope']['world'],
                 'Explicit QA facts and real-expense fixture do not alter any stock or scene coordinate')
            living.tab(frame,'meals');m=capture(ev,page,frame,folder,label+'-entered-cards');cards(ev,m,True)
            check(ev,'128,000' in m['monthly']['label'] and '172,000' in m['monthly']['label'],
                  'Recipe view exposes actual registered monthly cash and remaining budget',m['monthly'])
            frame.locator('#recipeMonthBudget').click();old.ready(frame)
            check(ev,frame.locator('#tray[data-workflow-route=budget]').count()==1
                  and frame.locator('#budgetMonth').input_value()=='2026-11',
                  'Monthly summary opens the current month, not an unrelated stale month')
            old.close_tray(frame);recipe(frame)
            m=capture(ev,page,frame,folder,label+'-entered-detail');detail_geometry(ev,m,expected=2100)
            check(ev,m['detail']['cost']['kind']=='entered' and m['detail']['cost']['scope']=='recipe',
                  'Entered total stays distinct from pantry-excluded references',m['detail']['cost'])
            readonly(ev,frame,qa,'Entered detail rendering never changes the saved facts or actual cash')
        ev['final_state']=old.state(frame)
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        if context:context.close()
    return finish(ev,None)


def editor_case(browser,origin,kind,width,height,folder):
    label='cost-editor-'+kind+'-'+str(width);ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[]};context=page=None
    try:
        context,page,frame=open_case(browser,origin,old.ENTRIES[kind],width,height,ev)
        frame.evaluate(QA_FACTS);initial=old.state(frame);recipe(frame)
        for value in ['3300','0','']:
            frame.locator('#tray [data-wf=recipeCost]').click();old.ready(frame)
            m=capture(ev,page,frame,folder,label+'-form-'+(value or 'clear'))
            target(ev,m['detail']['editor']['save'],'Fast cost save')
            inp=old.reveal(frame.locator('#tray [data-wf-form=recipeCost] [name=cost]'));inp.fill(value)
            before=old.state(frame);expected=copy.deepcopy(before['envelope']);expected['workflow']['recipeFacts']['recipe-1']['cost']=int(value)if value else None
            frame.locator('#tray [data-wf-form=recipeCost] [type=submit]').click();old.ready(frame);after=old.state(frame)
            check(ev,after['envelope']==expected,'Cost '+(value or 'clear')+' changes only the intended cost field; nutrition/source/extra fields and cash stay exact')
            m=capture(ev,page,frame,folder,label+'-saved-'+(value or 'clear'))
            expected_cost=int(value)if value else EXPECTED['recipe-1']
            check(ev,m['detail']['cost']['total'] is not None and abs(m['detail']['cost']['total']-expected_cost)<.00001,
                  'Saved '+(value or 'clear')+' is shown as explicit zero/value or dated-reference fallback',m['detail']['cost'])
            check(ev,(m['detail']['cost']['kind']=='entered')==bool(value),
                  'Clearing the override restores a reference; zero remains explicitly entered')
        frame.locator('#tray [data-wf=recipeCost]').click();old.ready(frame)
        duplicate_form=frame.locator('#tray [data-wf-form=recipeCost]');old.reveal(duplicate_form.locator('[name=cost]')).fill('4400')
        detached=duplicate_form.element_handle();before_duplicate=old.state(frame)
        duplicate_form.locator('[type=submit]').click();old.ready(frame)
        detached.evaluate('''form=>{form.elements.namedItem('cost').value='9999';form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}''')
        old.ready(frame);expected_duplicate=copy.deepcopy(before_duplicate['envelope'])
        expected_duplicate['workflow']['recipeFacts']['recipe-1']['cost']=4400
        check(ev,old.state(frame)['envelope']==expected_duplicate,
              'A detached editor cannot replay a stale second submit over the newly saved cost')
        saved=old.state(frame);frame.locator('#tray [data-wf=recipeCost]').click();old.ready(frame)
        form=frame.locator('#tray [data-wf-form=recipeCost]');old.reveal(form.locator('[name=cost]')).fill('-1')
        form.locator('[type=submit]').click();old.ready(frame)
        check(ev,old.state(frame)==saved and frame.locator('#tray [data-wf-form=recipeCost]').count()==1,
              'Invalid negative price cannot silently overwrite valid source data')
        form.locator('[name=cost]').fill('9999');frame.locator('#tray [data-wf=back]').click();old.ready(frame)
        readonly(ev,frame,saved,'Canceling a price draft preserves the entire saved envelope and raw text')
        frame.locator('#tray [data-recipe-tab=nutrition]').click();old.ready(frame)
        old.reveal(frame.locator('#tray [data-wf=recipeFacts]')).click();old.ready(frame)
        check(ev,frame.locator('#tray [data-wf-form=facts]').count()==1
              and frame.locator('#tray [data-wf-form=facts] [name=kcal]').input_value()=='455',
              'The original full nutrition/facts editor remains available with preserved values')
        readonly(ev,frame,saved,'Opening the full facts editor preserves costs and existing extra nutrition')
        check(ev,initial['envelope']['world']==saved['envelope']['world']
              and initial['envelope']['workflow']['expenses']==saved['envelope']['workflow']['expenses'],
              'Cost edits never manufacture stock deductions, purchases or meal records')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        if context:context.close()
    return finish(ev,None)


def receipt_case(browser,origin,kind,folder):
    label='purchase-estimate-'+kind;ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[]};context=page=None
    try:
        context,page,frame=open_case(browser,origin,old.ENTRIES[kind],720,800,ev)
        seeded=frame.evaluate(RECEIPT);original=old.state(frame)
        check(ev,seeded['before']['world']==seeded['after']['world'],'An actual purchase record and its original pack quantities do not create or replace stock')
        recipe(frame);m=capture(ev,page,frame,folder,label+'-one-serving')
        # 1/10 egg pack + 1/16 onion pack + 1/10 oil + 1/10 soy + 1/10 rice.
        wanted=100+50+100+50+600
        check(ev,m['detail']['cost']['kind']=='purchase' and m['detail']['cost']['scope']=='recipe'
              and m['detail']['cost']['total']==wanted,
              'Compatible original purchase-pack prices supersede all public references',m['detail']['cost'])
        frame.locator('#tray .recipe-cost-basis summary').click();old.ready(frame)
        basis=frame.locator('#tray .recipe-cost-basis').inner_text()
        check(ev,'실제' in basis and ('할인' in basis or '차이' in basis),
              'The actual cost-basis disclosure explains unallocated item/receipt cash differences',basis)
        old.reveal(frame.locator('#recipePortions')).fill('2');frame.locator('#recipePortions').dispatch_event('change');old.ready(frame)
        m=capture(ev,page,frame,folder,label+'-two-servings')
        check(ev,m['detail']['cost']['total']==wanted*2,'Two servings scale the use amount without dividing by current fridge residue')
        readonly(ev,frame,original,'Purchase-derived estimate viewing leaves original pack, actual paid total and stock exact')
        old.close_tray(frame);living.tab(frame,'meals');m=capture(ev,page,frame,folder,label+'-cash')
        check(ev,'9,000' in m['monthly']['label'], 'Monthly actual cash remains the receipt paid total, never a sum of recipe estimates',m['monthly'])
        frame.evaluate(r'''()=>{KitchenJournal.transact(({flow})=>flow.expenses.push({id:'qa-future-price',day:'2026-11-11',name:'QA future',amount:99999,category:'groceries',receipt:{purchaseId:'qa-future-price',items:[{id:'qa-future-egg',name:'계란',quantity:'1개',amount:99999,registeredItemId:null}]}}))}''')
        future=old.state(frame);recipe(frame)
        # Recipe display portions intentionally survive closing the tray; reset
        # via its real control before comparing the one-serving future-price case.
        old.reveal(frame.locator('#recipePortions')).fill('1');frame.locator('#recipePortions').dispatch_event('change');old.ready(frame)
        m=capture(ev,page,frame,folder,label+'-future-price')
        check(ev,m['detail']['cost']['total']==wanted,'A future receipt is never used as a present cooking unit price')
        readonly(ev,frame,future,'Rejecting future receipt prices does not delete any future record')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        if context:context.close()
    return finish(ev,None)


def notes_case(browser,origin,kind,folder):
    label='detail-notes-'+kind;ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[]};context=page=None
    try:
        context,page,frame=open_case(browser,origin,old.ENTRIES[kind],390,480,ev)
        frame.evaluate(QA_FACTS);original=old.state(frame);recipe(frame)
        frame.locator('#tray [data-wf=favoriteRecipe]').click();old.ready(frame)
        expected=copy.deepcopy(original['envelope']);expected['workflow']['recipeNotes']['recipe-1']={'note':'','variation':'','favorite':True}
        check(ev,old.state(frame)['envelope']==expected,'Favoriting changes only the existing favorite field and preserves all price facts/cash')
        frame.locator('#tray [data-recipe-tab=nutrition]').click();old.ready(frame)
        form=frame.locator('#tray [data-wf-form=recipeNotes]');old.reveal(form.locator('[name=note]')).fill('QA 다음 조리 때 확인')
        old.reveal(form.locator('[name=variation]')).fill('QA 대체 재료 메모');form.locator('[type=submit]').click();old.ready(frame)
        expected['workflow']['recipeNotes']['recipe-1'].update(note='QA 다음 조리 때 확인',variation='QA 대체 재료 메모')
        check(ev,old.state(frame)['envelope']==expected,'Actual note save retains favorite, price/source, nutrition, shopping and exact stock')
        capture(ev,page,frame,folder,label+'-saved')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        if context:context.close()
    return finish(ev,None)


def inputs(root):
    return {name:{'bytes':(root/name).stat().st_size,'sha256':old.digest((root/name).read_bytes())}
            for name in closed.DELIVERIES}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser-executable',default='/usr/bin/chromium');parser.add_argument('--observe-only',action='store_true')
    parser.add_argument('--baseline-evidence',type=Path)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    if out.is_relative_to(REPO)or out.is_relative_to(root)or root.is_relative_to(out):parser.error('Evidence must be outside the checkout and frozen inputs.')
    out.mkdir(parents=True,exist_ok=False);screens=out/'screens';screens.mkdir();before=inputs(root)
    hashes={p:old.digest((REPO/'scripts'/p).read_bytes())for p in SOURCES}
    shutil.copyfile(Path(__file__),out/'executed-test-source.py')
    old.CLOCK=CLOCK
    report={'scope':'Local disposable Chromium; frozen self-contained HTML; no live price/provider/user/production writes',
            'clock':CLOCK.isoformat(),'reference_observation_day':'2026-10-23','inputs':before,'observation_only':args.observe_only,
            'verification_sources':hashes,'cases':[],'passed':False,
            'manual_review':'Inspect actual screenshots; numeric layout assertions do not establish user visual approval.'}
    server,origin=closed.serve(root)
    def save(row=None):
        if row:
            report['cases'].append(row);print(json.dumps({'id':row['id'],'passed':row['passed'],
                'failed':[c['name']for c in row['checks']if not c['passed']]},ensure_ascii=False),flush=True)
        report['inputs_unchanged']=inputs(root)==before
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright()as p:
            browser=p.chromium.launch(executable_path=args.browser_executable,args=['--no-sandbox'])
            for kind in old.ENTRIES:
                for width,height in PROFILES:save(layout_case(browser,origin,old.ENTRIES[kind],width,height,screens,args.observe_only))
            for width,height in APP_PROFILES:save(layout_case(browser,origin,'miniature-kitchen-app.html',width,height,screens,args.observe_only))
            if not args.observe_only:
                for kind in old.ENTRIES:
                    for width,height in ((320,360),(390,480)):save(editor_case(browser,origin,kind,width,height,screens))
                    save(receipt_case(browser,origin,kind,screens));save(notes_case(browser,origin,kind,screens))
            browser.close()
    finally:server.shutdown()
    report['expected_cases']=10 if args.observe_only else 18
    report['complete']=len(report['cases'])==report['expected_cases']
    report['assertions']=sum(len(c['checks'])for c in report['cases'])
    report['verification_sources_unchanged']=hashes=={p:old.digest((REPO/'scripts'/p).read_bytes())for p in SOURCES}
    report['delivery_under_1MiB']=all(row['bytes']<=1048576 for row in before.values())
    if args.baseline_evidence:
        prior=json.loads((args.baseline_evidence/'results.json').read_text());pairs=[]
        for row in report['cases']:
            if 'initial_state'not in row:continue
            baseline=next((c for c in prior['cases']if c['id']==row['id']),None)
            before_frame=(baseline or{}).get('screens',{}).get(row['id']+'-cards',{}).get('shell')
            after_frame=row.get('screens',{}).get(row['id']+'-cards',{}).get('shell')
            pairs.append({'id':row['id'],'same_initial_state':bool(baseline)and row['initial_state']==baseline.get('initial_state'),
                          'same_frame':before_frame==after_frame})
        report['baseline_comparison']=pairs
        report['baseline_states_equal']=len(pairs)==10 and all(p['same_initial_state']and p['same_frame']for p in pairs)
    report['passed']=report['complete']and report['inputs_unchanged']and report['verification_sources_unchanged']and report['delivery_under_1MiB']and all(c['passed']for c in report['cases'])
    if args.baseline_evidence:report['passed']=report['passed']and report['baseline_states_equal']
    save();print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'assertions':report['assertions']},ensure_ascii=False))
    raise SystemExit(0 if report['passed']else 1)


if __name__=='__main__':main()
