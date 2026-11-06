#!/usr/bin/env python3
"""Verify the living-kitchen widget using disposable, explicit QA data.

Exercise actual generated native/opaque previews. This does not call OCR,
publish content, read personal browser storage, or seed product data. Evidence
and optional before-build captures must stay outside the checkout.
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


DAY = '2026-11-05'
MONTH = '2026-11'
PROFILES = (*old.PROFILES, (720, 800), (681, 800), (682, 800))
POPULATED_PROFILES = ((320, 360), (390, 480), (800, 600), (720, 800))
ENTRIES = old.ENTRIES
REPO = Path(__file__).resolve().parents[1]

GEOMETRY = r'''async()=>{''' + old.PAINT_HELPERS + r'''
 const rect=boxOf;
 const visible=e=>!!rect(e)&&getComputedStyle(e).visibility!=='hidden';
 const ctl=e=>{
  const r=rect(e);if(!r)return {rect:null,label:e?.getAttribute('aria-label')||''};
  const bounds={x:0,y:0,right:innerWidth,bottom:innerHeight},clips=[];
  for(let n=e.parentElement;n;n=n.parentElement){
   const c=getComputedStyle(n),b=rect(n);if(!b)continue;
   if(/hidden|clip/.test(c.overflowX)&&!/auto|scroll/.test(c.overflowY)){
    // Pure hidden/clip boxes have no cross-axis scrollbar. DOMRect minus
    // computed borders retains fractional padding edges that clientWidth
    // rounds to an integer. Scroll/auto boxes below keep the client viewport.
    bounds.x=Math.max(bounds.x,b.x+parseFloat(c.borderLeftWidth||0));
    bounds.right=Math.min(bounds.right,b.right-parseFloat(c.borderRightWidth||0));
   }else if(/hidden|clip|auto|scroll/.test(c.overflowX)){
    bounds.x=Math.max(bounds.x,b.x+n.clientLeft);bounds.right=Math.min(bounds.right,b.x+n.clientLeft+n.clientWidth);
   }
   if(/hidden|clip/.test(c.overflowY)&&!/auto|scroll/.test(c.overflowX)){
    bounds.y=Math.max(bounds.y,b.y+parseFloat(c.borderTopWidth||0));
    bounds.bottom=Math.min(bounds.bottom,b.bottom-parseFloat(c.borderBottomWidth||0));
   }else if(/hidden|clip|auto|scroll/.test(c.overflowY)){
    bounds.y=Math.max(bounds.y,b.y+n.clientTop);bounds.bottom=Math.min(bounds.bottom,b.y+n.clientTop+n.clientHeight);
   }
  }
  const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
  // One CSS border pixel is the existing project's geometry tolerance.
  // Text clipping below remains governed by the unchanged Range checks.
  return {rect:r,bounds,inside:r.x>=bounds.x-1&&r.y>=bounds.y-1&&r.right<=bounds.right+1&&r.bottom<=bounds.bottom+1,
   hit:hit===e||e.contains(hit),label:e.getAttribute('aria-label')||e.textContent.trim(),
   disabled:!!e.disabled,selected:e.getAttribute('aria-selected'),tabIndex:e.tabIndex};
 };
 const find=s=>document.querySelector(s),one=s=>rect(find(s)),all=s=>[...document.querySelectorAll(s)];
 const active=find('.shell>.home-panel:not([hidden])'),shelf=find('#homeSupplementsShelf');
 const fridgePhoto=find('#fridgeSceneHost .original-kitchen-photo'),world=find('#fridgeSceneHost .scene-world');
 const matrix=world?new DOMMatrix(getComputedStyle(world).transform):null;
 const cards=await Promise.all(all('#homeRecommendation .recipe-grid-card').map(async e=>({
  id:e.dataset.homeRecipe,control:ctl(e),rect:rect(e),text:textRanges(e),
  name:e.querySelector('.recipe-grid-copy strong')?.textContent.trim(),
  time:e.querySelector('[data-recipe-time]')?.textContent.trim(),
  kcal:{text:e.querySelector('[data-recipe-kcal]')?.textContent.trim(),value:e.querySelector('[data-recipe-kcal]')?.dataset.value},
  cost:{text:e.querySelector('[data-recipe-cost]')?.textContent.trim(),value:e.querySelector('[data-recipe-cost]')?.dataset.value},
  stock:{text:e.querySelector('[data-recipe-stock]')?.textContent.trim(),
   enough:Number(e.querySelector('[data-recipe-stock]')?.dataset.readyCount),
   total:Number(e.querySelector('[data-recipe-stock]')?.dataset.requiredCount)},
  photo:await paintedPhoto(e.querySelector('.recipe-grid-photo'))
 })));
 const panelVisible=s=>find(s)&&visible(find(s));
 const cal=panelVisible('#homeMonthly .journal-diary.is-calendar')?find('#homeMonthly .journal-calendar-grid'):null;
 const dates=cal?[...cal.querySelectorAll('[data-home-day]')].map(e=>({
  day:e.dataset.homeDay,control:ctl(e),selected:e.getAttribute('aria-current'),
  recipe:e.querySelector('svg.recipe-photo')?.dataset.recipePhoto,
  additional:e.querySelector('.journal-more-meals')?.textContent.trim(),
  image:!!e.querySelector('img.journal-meal-photo'),text:e.textContent.trim()
 })):[];
 const health=find('#homeHealth'),decor=find('#homeDecor');
 return {viewport:{width:innerWidth,height:innerHeight},home:document.body.dataset.home,
  page:document.body.dataset.homePage,shell:one('.shell'),panel:rect(active),
  document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
   clientWidth:document.documentElement.clientWidth,clientHeight:document.documentElement.clientHeight,scrollY},
  nav:one('.home-shortcuts'),navCount:all('.home-shortcuts').filter(visible).length,
  navTabs:all('.home-shortcuts [data-home-tab]').filter(visible).map(ctl),
  scene:{host:one('#fridgeSceneHost'),photo:rect(fridgePhoto),world:rect(world),canvas:rect(active),
   stage:one('#fridgeSceneHost .fridge-stage'),
   natural:fridgePhoto?{width:fridgePhoto.naturalWidth,height:fridgePhoto.naturalHeight,complete:fridgePhoto.complete}:null,
   matrix:matrix?{a:matrix.a,b:matrix.b,c:matrix.c,d:matrix.d}:null},
  balance:all('#dailyBalance [data-balance]').map(e=>({key:e.dataset.balance,rect:rect(e),text:e.textContent.trim()})),
  localTabs:active?[...active.querySelectorAll('.panel-tabs [data-home-subtab]')].filter(visible).map(ctl):[],
  recipe:{cards,grid:one('#homeRecommendation .recipe-hub-grid'),
   actions:all('.recipe-view-actions button').filter(visible).map(ctl)},
  calendar:{rect:rect(cal),slots:cal?.children.length||0,dates,
   header:one('#homeMonthly .home-date-bar'),budget:ctl(find('#homeMonthly .journal-budget-link')),
   budgetText:find('#homeMonthly .journal-budget-link')?.textContent.trim()},
  dayView:panelVisible('#homeMonthly .journal-diary.is-day'),
  dayNames:all('#homeMonthly .journal-entry-copy h3').filter(visible).map(e=>e.textContent.trim()),
  dayEmpty:panelVisible('#homeMonthly .journal-entry-empty'),
  dayPhotos:all('#homeMonthly .journal-entry-content svg.recipe-photo').filter(visible).map(e=>e.dataset.recipePhoto),
  dayText:textRanges(find('#homeMonthly .journal-entry-content')),
  dayActions:all('#homeMonthly .journal-day-actions button,[data-record-month-view="calendar"]').filter(visible).map(ctl),
  health:{visible:health&&visible(health),text:health?.textContent.trim(),ranges:textRanges(health),
   links:health?[...health.querySelectorAll('a[href]')].map(e=>({label:e.textContent.trim(),href:e.href})):[],
   buttons:health?[...health.querySelectorAll('button')].filter(visible).map(e=>({...ctl(e),text:textRanges(e)})):[]},
  decor:{visible:decor&&visible(decor),stage:one('#decorStage'),
   actions:all('#homeDecor .decor-footer button').filter(visible).map(ctl),
   shelf:all('#homeDecor [data-decor-select],#homeDecor [data-decor-reward],#homeDecor [data-add-prop]').filter(visible).map(ctl),
   selection:find('#decorSelectionName')?.textContent.trim(),
   draft:window.MiniKitchen.getDecorDraftState?.()},
  shelf:{rect:rect(shelf),text:shelf?.textContent.trim(),
   controls:shelf?[...shelf.querySelectorAll('button')].filter(visible).map(ctl):[],
   checked:shelf?[...shelf.querySelectorAll('[data-home-supplement-today]')].map(e=>({id:e.dataset.homeSupplementToday,checked:e.getAttribute('aria-pressed')==='true'})):[]}
 };
}'''

FIXTURE = r'''()=>{
 const before=KitchenJournal.getEnvelope();
 KitchenJournal.transact(({play,flow})=>{
  play.record({day:'2026-11-05',name:'QA 계란 볶음밥',portion:'QA 1회분',recipeId:'recipe-1',
   nutrients:{kcal:455,carb:60,protein:20,fat:15,fiber:null,water:null}});
  play.record({day:'2026-11-06',name:'QA 토마토 오믈렛',portion:'QA 1회분',recipeId:'recipe-8',
   nutrients:{kcal:300,carb:10,protein:20,fat:20,fiber:null,water:null}});
  play.record({day:'2026-11-05',name:'QA 직접 기록한 간식',portion:'QA 입력',recipeId:null,
   nutrients:{kcal:null,carb:null,protein:null,fat:null,fiber:null,water:null}});
  flow.recipeFacts['recipe-1']={kcal:455,carb:60,protein:20,fat:15,fiber:null,water:null,cost:2100,
   source:'격리 브라우저 QA 입력 · 실제 성분값/개인기록 아님'};
  flow.budgets['2026-11']=300000;
  flow.expenses.push({id:'qa-expense-1',day:'2026-11-05',name:'QA 식재료 실제 지출',amount:128000,category:'groceries'});
  flow.supplements.push(
   {id:'qa-supplement-d',name:'QA 비타민D',amount:'QA 제품 표시',schedule:'QA 아침 식후',ingredients:'QA 직접 입력',days:[]},
   {id:'qa-supplement-o',name:'QA 오메가3',amount:'QA 제품 표시',schedule:'QA 저녁',ingredients:'QA 직접 입력',days:['2026-11-04']});
 });
 const stable=KitchenJournal.getEnvelope();
 stable.play.meals.forEach((meal,index)=>{meal.id='qa-diary-meal-'+(index+1)});
 KitchenJournal.replaceEnvelope(stable);
 return {before,after:KitchenJournal.getEnvelope()};
}'''


def check(evidence, value, name, detail=None, layout=False):
    old.Audit(evidence).check(value, name, detail,
                             category='reference-composition' if layout else 'functional')


def control(evidence, item, label, minimum=44):
    r = item.get('rect') if item else None
    check(evidence, bool(r and r['width'] >= minimum-.5 and r['height'] >= minimum-.5
                         and item.get('inside') and item.get('hit')),
          label+' is visible, unoccluded and at least '+str(minimum)+'px', item, layout=True)


def readonly(evidence, frame, original, label):
    current = old.state(frame)
    check(evidence, current['key'] == old.KEY and current['raw'] == original['raw']
          and current['envelope'] == original['envelope'], label)


def capture(page, frame, folder, label):
    old.ready(frame)
    m = frame.evaluate(GEOMETRY)
    page.screenshot(path=str(folder/(label+'.png')), animations='disabled', caret='hide')
    return m


def tab(frame, name, sub=None):
    old.close_tray(frame)
    frame.locator('.home-shortcuts [data-home-tab="'+name+'"]').click()
    if sub and frame.locator('body').get_attribute('data-home-page') != sub:
        frame.locator('[data-home-subtab="'+sub+'"]:visible').click()
    old.ready(frame)


def main_geometry(evidence, m):
    box = old.viewport_box(m['viewport']['width'], m['viewport']['height'])
    check(evidence, old.inside(m['shell'], box), 'Widget canvas stays in its host', m['shell'], layout=True)
    check(evidence, m['document']['width'] <= m['document']['clientWidth']+1
          and m['document']['height'] <= m['document']['clientHeight']+1
          and m['document']['scrollY'] == 0, 'Document does not scroll or overflow', m['document'], layout=True)
    check(evidence, m['navCount'] == 1 and len(m['navTabs']) == 4,
          'One four-tab main navigation remains visible, including decoration', m['navTabs'], layout=True)
    for c in m['navTabs']:
        control(evidence, c, c['label'])
    for c in m['localTabs']:
        control(evidence, c, c['label'])


def recipe_geometry(evidence, frame, m, populated):
    rows = frame.evaluate('KitchenCatalog.map(r=>({id:r.id,name:r.name,time:r.time}))')
    catalog = {r['id']: r for r in rows}
    cards = m['recipe']['cards']
    preparation = frame.evaluate('''()=>Object.fromEntries(KitchenJourneyModel.recommend(
      KitchenCatalog,MiniKitchen.exportWorld(),KitchenJournal.getWorkflow(),KitchenJournal.getSnapshot(),
      {day:"2026-11-05"}).map(c=>[c.recipe.id,{
        enough:c.availability.rows.filter(r=>r.status==="enough"&&!r.quantityUnknown&&!r.unknownExpiryIds?.length).length,
        total:c.availability.rows.length}]))''')
    check(evidence, len(cards) == 8 and {r['id'] for r in cards} == set(catalog),
          'Eight distinct actual catalog recipes are compared together')
    check(evidence, old.inside(m['recipe']['grid'], m['panel']),
          'All eight cards fit the recipe panel', m['recipe']['grid'], layout=True)
    columns={round(c['rect']['x'],1) for c in cards if c['rect']}
    rows_y={round(c['rect']['y'],1) for c in cards if c['rect']}
    check(evidence,len(columns)==2 and len(rows_y)==4,
          'Eight comparison cards retain the requested two-by-four grid',
          {'columns':len(columns),'rows':len(rows_y)},layout=True)
    for card in cards:
        actual = catalog.get(card['id'], {})
        check(evidence, card['name'] == actual.get('name') and card['time'] == actual.get('time'),
              card['id']+' retains its full actual name and cooking time')
        check(evidence, bool(card['text']) and all(t['readable'] for t in card['text']),
              card['id']+' comparison information is initially readable', card['text'], layout=True)
        control(evidence, card['control'], card['id']+' card')
        check(evidence, old.inside(card['rect'], m['recipe']['grid']),
              card['id']+' card fits without paging or scrolling', card['rect'], layout=True)
        old.recipe_photo_geometry(old.Audit(evidence), card['photo'], card['id']+' actual thumbnail', card['id'])
        known = populated and card['id'] == 'recipe-1'
        check(evidence, card['kcal']['value'] == ('455' if known else '')
              and ('455' in card['kcal']['text'] if known else '—' in card['kcal']['text']),
              card['id']+' calorie information uses entered values or an honest unknown', card['kcal'])
        check(evidence, card['cost']['value'] == ('2100' if known else '')
              and ('2,100' in card['cost']['text'] if known else '—' in card['cost']['text']),
              card['id']+' cost uses entered values or an honest unknown', card['cost'])
        check(evidence, 0 <= card['stock']['enough'] <= card['stock']['total']
              and card['stock']['total'] > 0 and '충족' in card['stock']['text'],
              card['id']+' shows checked ingredient sufficiency', card['stock'])
        check(evidence,card['stock']['enough']==preparation[card['id']]['enough']
              and card['stock']['total']==preparation[card['id']]['total'],
              card['id']+' ingredient counts match the existing stock/quantity/expiry analysis')
    for c in m['recipe']['actions']:
        control(evidence, c, 'Recipe '+c['label'])
    check(evidence, len(m['recipe']['actions']) == 2,
          'Catalog and filter actions remain available beside recipe tabs')


def recipe_clicks(evidence, frame, original, subset=False):
    items = frame.locator('#homeRecommendation .recipe-grid-card').evaluate_all(
        '(nodes)=>nodes.map(e=>({id:e.dataset.homeRecipe,name:e.querySelector("strong").textContent.trim()}))')
    for row in items if not subset else items[:2]:
        frame.locator('#homeRecommendation [data-home-recipe="'+row['id']+'"]').click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=recipe]")')
        old.ready(frame)
        actual = frame.evaluate('''()=>({id:document.querySelector('#tray .recipe-favorite')?.dataset.arg,
          name:document.querySelector('#tray .recipe-detail-name')?.textContent.trim(),
          photo:document.querySelector('#tray svg.recipe-photo')?.dataset.recipePhoto})''')
        check(evidence, actual == {'id':row['id'],'name':row['name'],'photo':row['id']},
              row['id']+' card opens the matching existing recipe detail', actual)
        readonly(evidence, frame, original, row['id']+' detail is read only')
        old.close_tray(frame)
    frame.locator('.recipe-view-actions [data-wf="recipeFilters"]').click()
    form = frame.locator('#tray [data-wf-form="recipeFilters"]')
    form.locator('[name="time"]').fill('15')
    form.locator('[type="submit"]').click()
    old.ready(frame)
    names = frame.locator('#homeRecommendation .recipe-grid-card').evaluate_all(
        '(nodes)=>nodes.map(e=>e.dataset.homeRecipe)')
    expected = frame.evaluate('KitchenCatalog.filter(r=>Number(r.time.match(/\\d+/)[0])<=15).map(r=>r.id)')
    check(evidence, set(names) == set(expected) and 0 < len(names) < 8,
          'Actual filter form produces a genuine subset without fake filler')
    frame.locator('.recipe-view-actions [data-wf="recipeFilters"]').click()
    form = frame.locator('#tray [data-wf-form="recipeFilters"]')
    form.locator('[name="time"]').fill('1')
    form.locator('[type="submit"]').click()
    old.ready(frame)
    check(evidence, frame.locator('#homeRecommendation .recipe-grid-card').count() == 0
          and frame.locator('#homeRecommendation .recipe-hub-empty:visible').count() == 1,
          'No-result conditions remain an honest empty state')
    frame.locator('#homeRecommendation [data-home-filter-reset]').click()
    old.ready(frame)
    check(evidence, frame.locator('#homeRecommendation .recipe-grid-card').count() == 8,
          'Actual reset restores the eight recipes')
    readonly(evidence, frame, original, 'Filtering and resetting never persist or seed records')


def calendar_geometry(evidence, m, populated):
    c = m['calendar']
    check(evidence, m['page'] == 'monthly' and c['slots'] == 42,
          'Records initially opens the full 42-slot food diary calendar', {'page':m['page'],'slots':c['slots']})
    check(evidence, len(c['dates']) == 30 and {r['day'] for r in c['dates']} ==
          {MONTH+'-'+str(i).zfill(2) for i in range(1,31)},
          'Calendar contains every real November date exactly once')
    for date in c['dates']:
        control(evidence, date['control'], date['day']+' calendar date', minimum=24)
    control(evidence, c['budget'], 'Visible monthly food-budget entry')
    budget = c['budgetText'] or ''
    check(evidence, ('128,000' in budget and '172,000' in budget) if populated
          else ('0' in budget and '미설정' in budget),
          'Calendar shows actual spending and honest remaining budget', budget)
    stamps = {r['day']: r for r in c['dates'] if r['recipe'] or r['image']}
    check(evidence, set(stamps) == ({DAY,'2026-11-06'} if populated else set()),
          'Only dates with recorded food receive food pictures', stamps)
    if populated:
        check(evidence, stamps[DAY]['recipe'] == 'recipe-1'
              and stamps['2026-11-06']['recipe'] == 'recipe-8'
              and '+1' in (stamps[DAY]['additional'] or ''),
              'Food stamps and additional-meal counts match real recorded entries')


def record_journey(evidence, page, frame, folder, label, original, populated):
    frame.locator('#homeMonthly [data-home-day="'+DAY+'"]').click()
    day = capture(page, frame, folder, label+'-day')
    check(evidence, day['dayView'], 'Clicking a date opens its existing food-diary entry')
    if populated:
        check(evidence, 'QA 계란 볶음밥' in day['dayNames'] and 'recipe-1' in day['dayPhotos'],
              'Selected day displays its actual recorded food name and picture', day['dayNames'])
    else:
        check(evidence, day['dayEmpty'], 'Unrecorded dates show no invented meal entry')
    check(evidence, bool(day['dayText']) and all(t['readable'] for t in day['dayText']),
          'Selected diary entry text is readable in the initial viewport', day['dayText'], layout=True)
    for c in day['dayActions']:
        control(evidence, c, 'Diary '+c['label'])
    readonly(evidence, frame, original, 'Viewing a selected diary date is read only')
    frame.locator('#homeMonthly [data-record-month-view="calendar"]').click()
    frame.locator('#homeMonthly [data-home-date-shift="homeMonth"][data-step="1"]').click()
    old.ready(frame)
    dates = frame.locator('#homeMonthly [data-home-day]').evaluate_all('(nodes)=>nodes.map(e=>e.dataset.homeDay)')
    check(evidence, len(dates) == 31 and all(s.startswith('2026-12-') for s in dates)
          and frame.locator('#homeMonthly .journal-calendar-grid>*').count() == 42,
          'Actual month navigation shows all December dates in 42 slots')
    frame.locator('#homeMonthly [data-home-date-shift="homeMonth"][data-step="-1"]').click()
    old.ready(frame)
    frame.locator('#homeMonthly .journal-budget-link').click()
    check(evidence, frame.locator('body').get_attribute('data-home-page') == 'budget',
          'Calendar food-budget entry opens actual expense management')
    text = frame.locator('#homeBudget').inner_text()
    check(evidence, ('128,000' in text and '300,000' in text and '172,000' in text)
          if populated else ('미설정' in text and '0' in text),
          'Expense management retains the same actual monthly totals', text)
    capture(page, frame, folder, label+'-budget')
    readonly(evidence, frame, original, 'Date/month/budget browsing preserves existing records')


def health_geometry(evidence, m):
    check(evidence, m['page'] == 'health' and m['health']['visible'],
          'Health knowledge has a visible dedicated tab')
    text = m['health']['text'] or ''
    check(evidence, bool(text) and any(s in text for s in ['영양','표시','보관']),
          'Health tab contains readable knowledge content rather than an empty placeholder')
    check(evidence, bool(m['health']['ranges']) and all(t['readable'] for t in m['health']['ranges']),
          'Health topic titles and summaries remain readable',m['health']['ranges'],layout=True)
    check(evidence, len(m['health']['buttons']) == 4,
          'Four actual health-knowledge topics are discoverable')
    for c in m['health']['buttons']:
        control(evidence, c, 'Health '+c['label'])
        ranges=c.get('text',[])
        check(evidence,bool(ranges) and all(old.inside(
            {'x':t['x'],'y':t['y'],'right':t['x']+t['width'],'bottom':t['y']+t['height']},c['rect'])
            for t in ranges),
            'Health topic text fits its own card instead of overlapping another row',ranges,layout=True)
    overlaps=[]
    for index,first in enumerate(m['health']['buttons']):
        for second in m['health']['buttons'][index+1:]:
            a,b=first['rect'],second['rect']
            if a and b and min(a['right'],b['right'])-max(a['x'],b['x'])>.5 \
                    and min(a['bottom'],b['bottom'])-max(a['y'],b['y'])>.5:
                overlaps.append([first['label'],second['label']])
    check(evidence,not overlaps,'Health cards do not overlap one another',overlaps,layout=True)


def health_journey(evidence, frame, original):
    articles = frame.locator('#homeHealth [data-living-article]').evaluate_all(
        '(nodes)=>nodes.map(e=>e.dataset.livingArticle)')
    for article in articles:
        frame.locator('[data-living-article="'+article+'"]').click()
        old.ready(frame)
        info = frame.locator('#tray .health-article')
        check(evidence, info.is_visible() and len(info.inner_text()) > 40,
              article+' opens real readable knowledge content')
        links = info.locator('a[href]').evaluate_all(
            '(nodes)=>nodes.map(e=>({text:e.textContent.trim(),href:e.href}))')
        check(evidence, bool(links) and all(x['text'] and x['href'].startswith('https://www.foodsafetykorea.go.kr/') for x in links),
              article+' explicitly names its reference source without a network call', links)
        old.close_tray(frame)
        readonly(evidence, frame, original, article+' reading preserves exact records')


def layout_case(browser, origin, kind, width, height, folder, populated=False, app=False):
    label = ('app' if app else kind)+'-'+str(width)+'x'+str(height)+('-qa' if populated else '-empty')
    ev = {'id':label,'checks':[],'reference_checks_required':True,'screens':{},
          'fixture':'Explicit isolated QA meals/facts/supplements/expense' if populated else 'Unmodified product starter state; no personal records',
          'page_errors':[],'blocked_requests':[]}
    context = page = None
    try:
        entry = 'miniature-kitchen-app.html' if app else ENTRIES[kind]
        context, page, frame = old.open_page(browser, origin, entry, width, height, ev['page_errors'], ev['blocked_requests'])
        if populated:
            seeded = frame.evaluate(FIXTURE)
            check(ev, seeded['after']['world'] == seeded['before']['world'],
                  'Explicit QA fixture does not alter any starter stock or coordinates')
        original = old.state(frame)
        for name in ['fridge','meals','records','kitchen']:
            tab(frame, name)
            m = capture(page, frame, folder, label+'-'+name)
            ev['screens'][name] = m
            main_geometry(ev, m)
            readonly(ev, frame, original, name+' navigation preserves exact journal records')
            if name == 'fridge':
                if not app:
                    old.scene_geometry(old.Audit(ev),m['scene'],width,height,m['balance'])
                check(ev, bool(m['shelf']['rect']), 'Today supplements are visible above the fridge')
                check(ev, old.inside(m['shelf']['rect'], m['panel']),
                      'Supplement shelf fits the home canvas', m['shelf'], layout=True)
                for c in m['shelf']['controls']:
                    control(ev, c, 'Home supplement '+c['label'])
                if not populated:
                    check(ev, '등록' in (m['shelf']['text'] or '') and not m['shelf']['checked'],
                          'Home offers actual supplement registration without fake products')
            elif name == 'meals':
                recipe_geometry(ev, frame, m, populated)
                recipe_clicks(ev, frame, original, subset=app)
            elif name == 'records':
                calendar_geometry(ev, m, populated)
                record_journey(ev, page, frame, folder, label, original, populated)
            else:
                check(ev, m['page'] == 'decor' and m['decor']['visible'],
                      'My kitchen initially opens the real decoration studio')
                check(ev, m['decor']['stage'] and m['decor']['stage']['height'] >= 100,
                      'Decoration retains a usable live room preview', m['decor']['stage'], layout=True)
                for c in m['decor']['actions']:
                    control(ev, c, 'Studio '+c['label'])
                frame.locator('[data-home-subtab="health"]:visible').click()
                health = capture(page, frame, folder, label+'-health')
                main_geometry(ev, health)
                health_geometry(ev, health)
                health_journey(ev, frame, original)
                readonly(ev, frame, original, 'Leaving decoration for health cancels drafts without a write')
        tab(frame, 'fridge')
        readonly(ev, frame, original, 'Returning home preserves existing records after every view')
    except Exception as error:
        old.Audit(ev).caught(error)
        ev['traceback'] = traceback.format_exc()
        if page:
            page.screenshot(path=str(folder/(label+'-failure.png')), animations='disabled', caret='hide')
    finally:
        check(ev, not ev['page_errors'], 'No uncaught browser errors', ev['page_errors'])
        check(ev, not ev['blocked_requests'], 'No provider or network write is attempted', ev['blocked_requests'])
        if context:
            context.close()
    return old.finish_case(ev)


def supplement_case(browser, origin, kind, width, height, folder):
    label = 'supplement-'+kind+'-'+str(width)+'x'+str(height)
    ev = {'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
          'fixture':'Explicit disposable QA products and meals; no actual supplement recommendation'}
    context = page = None
    try:
        context, page, frame = old.open_page(browser, origin, ENTRIES[kind], width, height,
                                             ev['page_errors'], ev['blocked_requests'])
        frame.evaluate(FIXTURE)
        original = old.state(frame)
        def toggle_today(checked):
            tab(frame,'fridge')
            home = frame.locator('#homeSupplementsShelf [data-home-supplement-today="qa-supplement-d"]:visible')
            if home.count():
                if (home.get_attribute('aria-pressed') == 'true') != checked:
                    home.click()
            else:
                frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
                frame.locator('#homeSupplements [data-home-supplement="qa-supplement-d"]').set_checked(checked)
            old.ready(frame)
        toggle_today(True)
        old.ready(frame)
        after = old.state(frame)['envelope']
        before = original['envelope']
        changed = next(s for s in after['workflow']['supplements'] if s['id']=='qa-supplement-d')
        check(ev, changed['days'] == [DAY], 'Actual home checkbox records only today once', changed)
        expected = copy.deepcopy(before)
        next(s for s in expected['workflow']['supplements'] if s['id']=='qa-supplement-d')['days'] = [DAY]
        check(ev, after == expected, 'Home supplement toggle changes no meal, expense, stock or other product')
        toggle_today(False)
        check(ev, old.state(frame)['envelope'] == before, 'Unchecking today restores the exact previous product days')
        tab(frame,'records','supplements')
        day = frame.locator('#homeSupplementDay')
        day.fill('2026-11-04')
        day.dispatch_event('change')
        old.ready(frame)
        historical = frame.locator('#homeSupplements [data-home-supplement="qa-supplement-d"]')
        historical.check()
        after_history = old.state(frame)['envelope']
        check(ev, next(s for s in after_history['workflow']['supplements'] if s['id']=='qa-supplement-d')['days'] ==
              ['2026-11-04'], 'The selected historical date is independent of home today')
        tab(frame,'fridge')
        home = frame.locator('#homeSupplementsShelf [data-home-supplement-today="qa-supplement-d"]:visible')
        if home.count():
            checked = home.get_attribute('aria-pressed') == 'true'
        else:
            frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
            checked = frame.locator('#homeSupplements [data-home-supplement="qa-supplement-d"]').is_checked()
        check(ev, not checked, 'Historical recording never falsely checks home today')
        check(ev, after_history['play'] == before['play'] and after_history['world'] == before['world']
              and after_history['workflow']['expenses'] == before['workflow']['expenses'],
              'Historical supplement recording preserves meals, stock and expenses')
        capture(page, frame, folder, label+'-recorded')
    except Exception as error:
        old.Audit(ev).caught(error)
        ev['traceback'] = traceback.format_exc()
        if page:
            page.screenshot(path=str(folder/(label+'-failure.png')), animations='disabled')
    finally:
        check(ev, not ev['page_errors'], 'No supplement browser error', ev['page_errors'])
        check(ev, not ev['blocked_requests'], 'Supplement toggles call no provider', ev['blocked_requests'])
        if context:
            context.close()
    return old.finish_case(ev)


def supplement_registration_case(browser, origin, kind, folder):
    label='supplement-register-'+kind
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
        'fixture':'Actual registration form receives explicit QA product text, not a dosage recommendation'}
    context=page=None
    try:
        context,page,frame=old.open_page(browser,origin,ENTRIES[kind],390,480,
                                        ev['page_errors'],ev['blocked_requests'])
        before=old.state(frame)['envelope']
        check(ev,not before['workflow']['supplements'],'No fake supplement exists before registration')
        frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
        frame.locator('#homeSupplements [data-workflow="supplements"]').click()
        frame.locator('#tray .supplement-add>summary').click()
        form=frame.locator('#tray [data-wf-form="supplement"]')
        entered={'name':'QA 등록 제품','amount':'QA 제품 표시','remaining':'QA 남은 수량',
                 'schedule':'QA 내 일정','origin':'QA 제조 표시','ingredients':'QA 성분 메모'}
        for name,value in entered.items():
            form.locator('[name="'+name+'"]').fill(value)
        form.locator('[type="submit"]').click()
        old.ready(frame)
        after=old.state(frame)['envelope']
        rows=after['workflow']['supplements']
        check(ev,len(rows)==1 and all(rows[0].get(k)==v for k,v in entered.items()) and rows[0]['days']==[],
              'Actual product form stores exactly the entered product without a false taken-today mark',rows)
        restored=copy.deepcopy(after)
        restored['workflow']['supplements']=[]
        check(ev,restored==before,'Supplement registration preserves every meal, expense, stock lot and prior field')
        old.close_tray(frame)
        tab(frame,'fridge')
        text=frame.locator('#homeSupplementsShelf').inner_text()
        check(ev,'0 / 1' in text,'Home shelf immediately shows the real registered-product count',text)
        capture(page,frame,folder,label+'-saved')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No registration browser error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'Supplement registration calls no provider',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def decor_case(browser, origin, kind, width, height, folder):
    label = 'decor-'+kind+'-'+str(width)+'x'+str(height)
    ev = {'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
          'fixture':'Disposable QA meals earn two genuine model tickets; no direct fake reward'}
    context = page = None
    try:
        context,page,frame = old.open_page(browser,origin,ENTRIES[kind],width,height,
                                           ev['page_errors'],ev['blocked_requests'])
        frame.evaluate(FIXTURE)
        original = old.state(frame)
        tab(frame,'kitchen','decor')
        frame.locator('#decorPropShelf [data-decor-select="cup"]').click()
        check(ev, '찻잔' in frame.locator('#decorSelectionName').inner_text()
              or '머그' in frame.locator('#decorSelectionName').inner_text(),
              'Actual placed cup is selected from the visible shelf')
        item = frame.locator('#decorStage .item.decor[data-item="cup"]')
        item.focus()
        page.keyboard.press('ArrowRight')
        draft = frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")')
        baseline_cup = next(i for i in original['envelope']['world']['items'] if i['id']=='cup')
        check(ev, draft['x'] != baseline_cup['x'], 'Keyboard moves the actual selected prop in the live preview')
        readonly(ev,frame,original,'Moving a preview does not write its coordinates')
        frame.locator('[data-home-subtab="health"]:visible').click()
        check(ev, not frame.evaluate('MiniKitchen.getDecorDraftState().active'),
              'Leaving the studio cancels an uncommitted draft')
        readonly(ev,frame,original,'Leaving decoration restores the exact committed world and tickets')
        tab(frame,'kitchen','decor')
        frame.locator('#propList').click()
        frame.locator('#tray [data-growth-selectprop="room-frame"]').click()
        frame.locator('#tray [data-reward="room-frame"]').click()
        old.ready(frame)
        pending = frame.evaluate('MiniKitchen.getDecorDraftState()')
        check(ev, pending['active'] and pending['cost'] == 1
              and frame.evaluate('KitchenJournal.summary().tickets') == 2,
              'A paid room prop remains a one-ticket preview until Apply', pending)
        readonly(ev,frame,original,'Selecting an unowned reward does not spend or persist')
        frame.locator('#homeDecor [data-decor-cancel]').click()
        readonly(ev,frame,original,'Cancel restores all records and both tickets')
        old.close_tray(frame)
        tab(frame,'kitchen','decor')
        frame.locator('#propList').click()
        frame.locator('#tray [data-growth-selectprop="room-frame"]').click()
        frame.locator('#tray [data-reward="room-frame"]').click()
        draft_frame = frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.kind==="decor"&&i.art==="frame")')
        frame.locator('#homeDecor [data-decor-apply]').click()
        old.ready(frame)
        applied = old.state(frame)['envelope']
        check(ev, next(i for i in applied['world']['items'] if i.get('art')=='frame') == draft_frame,
              'Apply saves the exact real preview coordinates')
        check(ev, applied['play']['owned'].count('room-frame') == 1
              and frame.evaluate('KitchenJournal.summary().tickets') == 1,
              'Apply buys the room reward exactly once')
        check(ev, applied['workflow'] == original['envelope']['workflow']
              and applied['play']['meals'] == original['envelope']['play']['meals']
              and [i for i in applied['world']['items'] if i['kind']!='decor'] ==
              [i for i in original['envelope']['world']['items'] if i['kind']!='decor'],
              'Applying decoration preserves stock, food diary, expenses and supplements')
        tab(frame,'kitchen','decor')
        frame.locator('#decorPropShelf [data-decor-select="cup"]').click()
        item=frame.locator('#decorStage .item.decor[data-item="cup"]')
        item.focus()
        page.keyboard.press('ArrowRight')
        free_draft=frame.evaluate('MiniKitchen.getSnapshot().items.find(i=>i.id==="cup")')
        check(ev, frame.evaluate('MiniKitchen.getDecorDraftState().cost') == 0,
              'Repositioning an existing free/basic prop costs no ticket')
        frame.locator('#homeDecor [data-decor-apply]').click()
        free = old.state(frame)['envelope']
        check(ev, next(i for i in free['world']['items'] if i['id']=='cup') == free_draft
              and free['play']['owned'] == applied['play']['owned']
              and frame.evaluate('KitchenJournal.summary().tickets') == 1,
              'Free Apply saves its coordinates without duplicate purchase or cost')
        capture(page,frame,folder,label+'-applied')
        if kind=='native':
            saved=old.state(frame)
            page.reload()
            frame.wait_for_function('window.KitchenJournal&&window.KitchenHome')
            old.ready(frame)
            readonly(ev,frame,saved,'Actual native reload preserves applied decoration and records')
    except Exception as error:
        old.Audit(ev).caught(error)
        ev['traceback']=traceback.format_exc()
        if page:
            page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No decoration browser error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'Decoration invokes no provider or network write',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def meal_success_case(browser, origin, kind, width, height, folder):
    """Real stock/facts forms, actual meal save, exact deductions, undo and resave."""
    label='B6-'+kind+'-'+str(width)+'x'+str(height)
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
        'fixture':'Existing explicit stock/facts QA form inputs; not official food composition'}
    context=page=None
    try:
        context,page,frame=old.open_page(browser,origin,ENTRIES[kind],width,height,
                                        ev['page_errors'],ev['blocked_requests'])
        shell=frame.evaluate(GEOMETRY)['shell']
        old.prepare_meal_stock(frame)
        tab(frame,'meals')
        frame.locator('.recipe-view-actions [data-wf="recipeCatalog"]').click()
        frame.locator('#tray .recipe-result[data-arg="recipe-1"]').click()
        frame.locator('#tray [data-recipe-tab="nutrition"]').click()
        frame.locator('#tray [data-wf="recipeFacts"]').click()
        facts=frame.locator('#tray [data-wf-form="facts"]')
        for name,value in old.QA_FACTS.items():
            old.reveal(facts.locator('[name="'+name+'"]')).fill(value)
        facts.locator('[name="source"]').fill('명시적 브라우저 QA · 실제 식품 성분값 아님')
        facts.locator('[type="submit"]').click()
        before=old.state(frame)['envelope']
        check(ev,all(before['workflow']['recipeFacts']['recipe-1'][k]==float(v) for k,v in old.QA_FACTS.items()),
              'Actual facts form saves only explicit QA values')
        frame.locator('#tray [data-wf="logMeal"]').click()
        form=frame.locator('#workflowMealForm')
        form.locator('[name="day"]').fill(DAY)
        form.locator('[name="slot"]').select_option('lunch')
        form.locator('[name="portions"]').fill('1')
        check(ev,old.state(frame)['envelope']==before,'Meal review does not consume stock before save')
        form.locator('[type="submit"]').click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=mealSuccess]")')
        geometry=old.capture(page,frame,folder,label+'-complete',old.SUCCESS)
        after=old.state(frame)['envelope']
        old_ids={m['id'] for m in before['play']['meals']}
        added=[m for m in after['play']['meals'] if m['id'] not in old_ids]
        check(ev,len(added)==1,'Actual Save creates exactly one meal')
        if len(added)!=1:raise AssertionError('Cannot identify single actual QA meal')
        meal=added[0]
        transaction=next(t for t in after['workflow']['transactions'] if t['mealId']==meal['id'])
        check(ev,meal['recipeId']=='recipe-1' and meal['day']==DAY
              and all(meal['nutrients'][k]==float(v) for k,v in old.QA_FACTS.items() if k!='cost')
              and meal['nutrients']['fiber'] is None and meal['nutrients']['water'] is None,
              'Saved nutrition retains entered values and unknowns')
        expected={'계란':'5개','양파':'1.75개','식용유':'9작은술','간장':'9작은술','밥':'9공기'}
        actual={i['name']:i['quantity'] for i in after['world']['items'] if i['name'] in expected}
        check(ev,transaction['active'] and len(transaction['deductions'])==5 and actual==expected,
              'Actual transaction deducts the intended five stock quantities',actual)
        check(ev,after['workflow']['expenses']==before['workflow']['expenses']
              and after['workflow']['plans']==before['workflow']['plans'],
              'Meal consumption never becomes actual purchase expense or edits a plan')
        check(ev,old.inside(geometry['tray'],shell)
              and geometry['content']['scrollHeight']<=geometry['content']['height']+1
              and geometry['document']['scrollY']==0,
              'B6 fits the bounded widget with fixed actions',geometry['content'],layout=True)
        check(ev,{a['workflow'] for a in geometry['actions']}==
              {'successRecords','successHome','undoSuccessMeal'} and len(geometry['deductions'])==5,
              'B6 preserves all actions and every actual deduction row')
        for a in geometry['actions']:
            old.primary(old.Audit(ev),a,width,height,a['text'])
            check(ev,old.inside(a['rect'],geometry['tray']) and old.inside(a['rect'],shell),
                  a['text']+' is initially inside both the tray and widget',a['rect'],layout=True)
        frame.locator('#tray [data-wf="undoSuccessMeal"]').click()
        undone=old.state(frame)['envelope']
        check(ev,undone['world']==before['world'] and undone['play']['meals']==before['play']['meals']
              and not next(t for t in undone['workflow']['transactions'] if t['mealId']==meal['id'])['active'],
              'Actual Undo restores exact stock and meal nutrition')
        form=frame.locator('#workflowMealForm')
        check(ev,form.locator('[name="day"]').input_value()==DAY
              and form.locator('[name="kcal"]').input_value()==old.QA_FACTS['kcal'],
              'Undo retains the entered meal for review')
        form.locator('[type="submit"]').click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=mealSuccess]")')
        saved=old.state(frame)['envelope']
        check(ev,saved['world']==after['world'] and len(saved['play']['meals'])==len(after['play']['meals'])
              and saved['play']['owned']==after['play']['owned'] and saved['play']['awarded']==after['play']['awarded'],
              'Actual resave cannot duplicate inventory use or first-recipe reward')
        frame.locator('#tray [data-wf="successRecords"]').click()
        check(ev,not frame.locator('#tray[open]').count() and frame.locator('body').get_attribute('data-home')=='records'
              and old.state(frame)['envelope']==saved,'Completion opens records without altering saved meal')
        capture(page,frame,folder,label+'-records')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No B6 browser error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'B6 invokes no provider/write request',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def input_hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*.html'))}


def baseline_captures(browser, origin, folder):
    """Capture identical fixed fixture values and clicks; no new-UI assertions."""
    results=[]
    for kind in ENTRIES:
        for w,h in ((320,360),(390,480),(720,800)):
            for populated in (False,True):
                label='before-'+kind+'-'+str(w)+'x'+str(h)+('-qa' if populated else '-empty')
                errors,requests=[],[]
                context,page,frame=old.open_page(browser,origin,ENTRIES[kind],w,h,errors,requests)
                try:
                    if populated:frame.evaluate(FIXTURE)
                    original=old.state(frame)
                    for name in ('fridge','meals','records','kitchen'):
                        old.close_tray(frame)
                        frame.locator('.home-shortcuts [data-home-tab="'+name+'"]').click()
                        old.ready(frame)
                        page.screenshot(path=str(folder/(label+'-'+name+'.png')),
                                        animations='disabled',caret='hide')
                    current=old.state(frame)
                    results.append({'id':label,'fixture':populated,'before':original,
                                    'read_only':current['raw']==original['raw'] and current['envelope']==original['envelope'],
                                    'errors':errors,'blocked_requests':requests})
                finally:context.close()
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--browser-executable')
    p.add_argument('--baseline-root',type=Path,help='Optional fixed previous generated build for same-data before captures')
    p.add_argument('--quick',action='store_true',help='Reduced layout matrix; actual supplement/decor transaction matrix remains')
    p.add_argument('--skip-b6',action='store_true',help='Skip the separately reported existing B6 cases')
    args = p.parse_args()
    root,out = args.root.resolve(),args.output.resolve()
    baseline=args.baseline_root.resolve() if args.baseline_root else None
    if out.is_relative_to(REPO) or out.is_relative_to(root) or root.is_relative_to(out):
        p.error('Evidence must stay outside checkout and frozen input directory.')
    for name in ['miniature-kitchen-widget.html','miniature-kitchen-app.html','mobile/widget.html','mobile/app.html']:
        if not (root/name).is_file():
            p.error('Missing generated entry '+name)
        if baseline and not (baseline/name).is_file():
            p.error('Missing previous generated entry '+name)
    out.mkdir(parents=True,exist_ok=False)
    images=out/'screens';images.mkdir()
    start=input_hashes(root)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(old.Quiet,directory=str(root)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin='http://127.0.0.1:'+str(server.server_port)
    before_server=None
    before_hashes=input_hashes(baseline) if baseline else None
    report={'scope':'Disposable local Chromium contexts only; no live OCR, remote write, production deployment or user design approval.',
            'quick':args.quick,'skipped_b6':args.skip_b6,'clock':DAY,'inputs':start,'cases':[],
            'manual_review':{'required':True,'status':'not judged by automation'},'passed':False}
    def save(row=None):
        if row is not None:
            report['cases'].append(row)
            print(json.dumps({'id':row['id'],'passed':row['passed'],'failed':[c['name'] for c in row['checks'] if not c['passed']]},
                             ensure_ascii=False),flush=True)
        report['inputs_unchanged']=start==input_hashes(root)
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright() as pl:
            executable=args.browser_executable or shutil.which('chromium') or shutil.which('chromium-browser')
            browser=pl.chromium.launch(executable_path=executable,args=['--no-sandbox'])
            if baseline:
                before_server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(old.Quiet,directory=str(baseline)))
                threading.Thread(target=before_server.serve_forever,daemon=True).start()
                before_dir=out/'before';before_dir.mkdir()
                report['baseline_observations']=baseline_captures(
                    browser,'http://127.0.0.1:'+str(before_server.server_port),before_dir)
            profiles=PROFILES[:2] if args.quick else PROFILES
            for kind in ENTRIES:
                for w,h in profiles:
                    save(layout_case(browser,origin,kind,w,h,images))
                for w,h in POPULATED_PROFILES[:2] if args.quick else POPULATED_PROFILES:
                    save(layout_case(browser,origin,kind,w,h,images,populated=True))
                for w,h in ((320,360),(390,480),(720,800)):
                    save(supplement_case(browser,origin,kind,w,h,images))
                for w,h in ((320,360),(390,480)):
                    save(decor_case(browser,origin,kind,w,h,images))
                save(supplement_registration_case(browser,origin,kind,images))
            if not args.quick:
                for w,h in ((390,844),(800,600)):
                    save(layout_case(browser,origin,'native',w,h,images,app=True))
            # Existing exact-v1 text/coordinate preservation is still exercised.
            save(old.legacy_case(browser,origin,images))
            if not args.skip_b6:
                for kind in ENTRIES:
                    for w,h in old.B6_PROFILES:
                        save(meal_success_case(browser,origin,kind,w,h,images))
            browser.close()
    finally:
        server.shutdown()
        if before_server:before_server.shutdown()
    population=POPULATED_PROFILES[:2] if args.quick else POPULATED_PROFILES
    expected=2*(len(profiles)+len(population)+3+2+1)+(0 if args.quick else 2)+1+(0 if args.skip_b6 else 6)
    report['expected_cases']=expected
    report['complete']=len(report['cases'])==expected and len({c['id'] for c in report['cases']})==expected
    if not args.quick:
        for kind in ENTRIES:
            pair=[next(c for c in report['cases'] if c['id']==kind+'-'+str(w)+'x800-empty') for w in (681,682)]
            stages=[c.get('screens',{}).get('fridge',{}).get('scene',{}).get('stage') for c in pair]
            ratio=stages[1]['width']/stages[0]['width'] if all(stages) and stages[0]['width'] else None
            check(pair[1],ratio is not None and .97<=ratio<=1.03,
                  'Supplement shelf681/682 breakpoint preserves the natural fridge projection',
                  {'stages':stages,'ratio':ratio},layout=True)
            old.finish_case(pair[1])
    report['baseline_unchanged']=before_hashes==input_hashes(baseline) if baseline else None
    report['passed']=report['complete'] and all(c['passed'] for c in report['cases']) and start==input_hashes(root) \
        and (not baseline or report['baseline_unchanged'])
    report['functional_passed']=all(c['functional_passed'] for c in report['cases'])
    report['layout_passed']=all(c['reference_composition_checks_passed'] is not False for c in report['cases'])
    report['assertions']=sum(len(c['checks']) for c in report['cases'])
    save()
    print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'assertions':report['assertions'],
                      'result':str(out/'results.json')},ensure_ascii=False),flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':
    main()
