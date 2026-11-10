#!/usr/bin/env python3
"""Exercise real servings, reference nutrition and personal daily comparisons.

Runs immutable local HTML with disposable Chromium data and explicit QA meals.
No official nutrition provider, personal browser, production or live Notion is
used. Selected PNGs require a separate visual review.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import traceback

from playwright.sync_api import sync_playwright
import test_kitchen_recipe_detail_browser as detail


old, living, closed = detail.old, detail.living, detail.closed
REPO = Path(__file__).resolve().parents[1]
DAY = '2026-11-10'
KEYS = ('kcal','carb','protein','fat','fiber','water','calcium','sodium','sugar')
BASE = ('kcal','carb','protein','fat','fiber','water')
PROFILES = (
    ('native','miniature-kitchen-widget.html',320,360),
    ('native','miniature-kitchen-widget.html',390,480),
    ('native','miniature-kitchen-widget.html',720,800),
    ('opaque','mobile/widget.html',320,360),
    ('opaque','mobile/widget.html',390,480),
    ('opaque','mobile/widget.html',720,800),
    ('app','miniature-kitchen-app.html',390,844),
    ('app','mobile/app.html',720,900),
)
# Separate arithmetic from the checked, dated SR28 food rows and declared
# recipe weights. Missing rice fiber/sugar and g-to-mL water stay unknown.
FRIED_RICE = {
    'kcal':143*.5+40*.5+884*.045+53*.053+130*2.1,
    'carb':.72*.5+9.34*.5+4.93*.053+28.73*2.1,
    'protein':12.56*.5+1.1*.5+8.14*.053+2.36*2.1,
    'fat':9.51*.5+.1*.5+100*.045+.57*.053+.19*2.1,
    'calcium':56*.5+23*.5+33*.053+1*2.1,
    'sodium':142*.5+4*.5+5493*.053,
    'fiber':None,'water':None,'sugar':None,
}
SOURCES = ('test_kitchen_nutrition_browser.py', *detail.SOURCES)
SELECTED = {'native-320x360','native-720x800','opaque-390x480','app-390x844'}

CONTROL = r'''e=>{
 const r=e.getBoundingClientRect();let l=0,t=0,right=innerWidth,b=innerHeight;
 // Fixed controls escape ordinary overflow ancestors until their actual fixed
 // containing block (the size container/transform) is reached. Their logical
 // photo/scroll parents must not create a fictitious clipping boundary.
 let clips=getComputedStyle(e).position!=='fixed';
 for(let n=e.parentElement;n;n=n.parentElement){const s=getComputedStyle(n),p=n.getBoundingClientRect();
  if(!clips)clips=s.containerType!=='normal'||s.transform!=='none'||s.perspective!=='none'||s.filter!=='none'||/layout|paint|strict|content/.test(s.contain)||s.contentVisibility==='auto'||/transform|perspective|filter/.test(s.willChange);
  if(!clips)continue;
  if(/hidden|auto|scroll|clip/.test(s.overflowX)){l=Math.max(l,p.x+n.clientLeft);right=Math.min(right,p.x+n.clientLeft+n.clientWidth)}
  if(/hidden|auto|scroll|clip/.test(s.overflowY)){t=Math.max(t,p.y+n.clientTop);b=Math.min(b,p.y+n.clientTop+n.clientHeight)}}
 const h=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
 const hit9=[.2,.5,.8].every(x=>[.2,.5,.8].every(y=>{const p=document.elementFromPoint(r.x+r.width*x,r.y+r.height*y);return p===e||e.contains(p)}));
 return {rect:{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom},
  inside:r.x>=l-1&&r.right<=right+1&&r.y>=t-1&&r.bottom<=b+1,
  centerHit:h===e||e.contains(h),hit:hit9,disabled:!!e.disabled,label:e.getAttribute('aria-label')||e.textContent.trim()};
}'''
LABEL = r'''e=>{
 const label=e.closest('label'),control=e.getBoundingClientRect();
 const walker=document.createTreeWalker(label,NodeFilter.SHOW_TEXT);let node;
 while(node=walker.nextNode())if(node.textContent.trim()&&!node.parentElement.closest('input,select,option'))break;
 if(!node)return {text:'',lines:[],clear:false};
 const range=document.createRange();range.selectNodeContents(node);
 const lines=[...range.getClientRects()].filter(r=>r.width&&r.height).map(r=>({x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}));
 return {text:node.textContent.trim(),lines,clear:lines.every(r=>r.right<=control.x+1||r.x>=control.right-1||r.bottom<=control.y+1||r.y>=control.bottom-1)};
}'''
TEXT = r'''e=>{''' + old.PAINT_HELPERS + r'''
 const r=e.getBoundingClientRect();let l=0,t=0,right=innerWidth,b=innerHeight;
 for(let n=e.parentElement;n;n=n.parentElement){const s=getComputedStyle(n),p=n.getBoundingClientRect();
  if(/hidden|auto|scroll|clip/.test(s.overflowX)){l=Math.max(l,p.x+n.clientLeft);right=Math.min(right,p.x+n.clientLeft+n.clientWidth)}
  if(/hidden|auto|scroll|clip/.test(s.overflowY)){t=Math.max(t,p.y+n.clientTop);b=Math.min(b,p.y+n.clientTop+n.clientHeight)}}
 return {inside:r.x>=l-1&&r.right<=right+1&&r.y>=t-1&&r.bottom<=b+1,text:textRanges(e),
  font:parseFloat(getComputedStyle(e).fontSize),label:e.innerText,
  hit:[.1,.5,.9].every(x=>[.1,.5,.9].every(y=>{const h=document.elementFromPoint(r.x+r.width*x,r.y+r.height*y);return h===e||e.contains(h)}))};
}'''
REPORT = r'''()=>{
 const recipe=KitchenCatalog.find(r=>r.id==='recipe-1');
 return KitchenRecipeNutrition.estimate(recipe,{flow:KitchenJournal.getWorkflow(),reference:KitchenNutritionReference,day:'2026-11-10'});
}'''
DAILY = r'''()=>KitchenNutritionInsight.daily({play:KitchenJournal.getSnapshot(),flow:KitchenJournal.getWorkflow(),day:'2026-11-10',
 preview:{kind:'reference',nutrients:{kcal:407.089,carb:65.62429,protein:12.21742,fat:9.73421,
  fiber:null,water:null,calcium:43.349,sodium:364.129,sugar:null}}})'''
DAILY_FIXTURE = r'''()=>{
 KitchenJournal.transact(({play,flow})=>{
  play.setTargets({kcal:2000,carb:230,protein:70,fat:60,fiber:25,water:2000});
  flow.extraTargets={calcium:800,sodium:2000,sugar:40};
  const a=play.record({day:'2026-11-10',name:'QA 명시적 아침',portion:'QA 실제입력',recipeId:null,
   nutrients:{kcal:400,carb:40,protein:20,fat:10,fiber:4,water:200}}).record;
  const b=play.record({day:'2026-11-10',name:'QA 명시적 점심',portion:'QA 실제입력',recipeId:null,
   nutrients:{kcal:250,carb:20,protein:10,fat:5,fiber:3,water:100}}).record;
  flow.extraNutrients[a.id]={calcium:100,sodium:1300,sugar:30};
  flow.extraNutrients[b.id]={calcium:50,sodium:900,sugar:15};
 });return KitchenJournal.getEnvelope();
}'''
PARTIAL_FIXTURE = r'''()=>{
 KitchenJournal.transact(({play,flow})=>{
  const m=play.record({day:'2026-11-10',name:'QA 일부 영양 미입력',portion:'QA 입력',recipeId:null,
   nutrients:{kcal:100,carb:null,protein:0,fat:null,fiber:null,water:null}}).record;
  flow.extraNutrients[m.id]={calcium:null,sodium:null,sugar:null};
 });return KitchenJournal.getEnvelope();
}'''


def check(ev, condition, name, evidence=None, visual=False):
    detail.check(ev, condition, name, evidence, visual)


def center(locator):
    locator.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest'})")
    return locator


def readable(ev, locator, label):
    m = center(locator).evaluate(TEXT)
    check(ev, m['inside'] and m['hit'] and m['text'] and all(t['readable'] for t in m['text']),
          label+' is readable through real scrolling without clipping or painted occlusion', m, True)


def target(ev, locator, label):
    m = center(locator).evaluate(CONTROL)
    detail.target(ev,m,label)


def shot(ev, page, folder, name):
    p=folder/(name+'.png');page.screenshot(path=str(p),animations='disabled')
    ev.setdefault('screenshots',[]).append({'path':str(p),'sha256':old.digest(p.read_bytes())})


def finish(ev, context):
    if context:context.close()
    check(ev,not ev['page_errors'],'No browser JavaScript error',ev['page_errors'])
    check(ev,not ev['blocked_requests'],'No external provider or personal-storage request',ev['blocked_requests'])
    return old.finish_case(ev)


def open_case(browser,origin,entry,width,height,ev):
    return old.open_page(browser,origin,entry,width,height,ev['page_errors'],ev['blocked_requests'])


def portion(frame,value):
    detail.show_recipe_ingredients(frame)
    p=center(frame.locator('#recipePortions'));p.fill(str(value));p.dispatch_event('change');old.ready(frame)


def nutrition(frame):
    frame.locator('#tray [data-recipe-tab=nutrition]').click();old.ready(frame)


def report_arithmetic(ev,report):
    for key,expected in FRIED_RICE.items():
        row=report['nutrients'][key]
        check(ev,row['value'] is None if expected is None else row['value'] is not None and abs(row['value']-expected)<.0000011,
              key+' is the independent one-person SR28 sum or remains genuinely missing',row)
    check(ev,report['nutrients']['fiber']['kind']=='partial' and abs(report['nutrients']['fiber']['knownSubtotal']-.8924)<.000001,
          'Missing rice fiber remains a partial subtotal rather than a complete nutrition fact')
    check(ev,report['nutrients']['sugar']['kind']=='partial' and abs(report['nutrients']['sugar']['knownSubtotal']-2.3262)<.000001,
          'Missing rice total sugar stays incomplete and is never assumed zero')


def layout_case(browser,origin,before_origin,entry,width,height,kind,folder):
    label=f'{kind}-{width}x{height}'
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],'reference_checks_required':True}
    context=page=None
    try:
        baseline=None
        if before_origin:
            bc,bp,bf=open_case(browser,before_origin,entry,width,height,ev)
            baseline=old.state(bf);detail.recipe(bf);portion(bf,4)
            before_shell=bf.evaluate(detail.METRICS)['shell']
            if label in SELECTED:
                nutrition(bf);shot(ev,bp,folder,'before-'+label+'-nutrition')
            bc.close()
        context,page,frame=open_case(browser,origin,entry,width,height,ev)
        original=old.state(frame);ev['initial_state']=original
        detail.recipe(frame);first=frame.evaluate(REPORT);report_arithmetic(ev,first)
        serving_label=frame.locator('#recipePortions').locator('..').inner_text()
        check(ev,'만들' in serving_label and '인분' in serving_label,
              'The visible control names the number of portions being cooked',serving_label)
        portion(frame,4);m=frame.evaluate(detail.METRICS)
        check(ev,frame.locator('#recipePortions').input_value()=='4' and any('필요 4개' in row['text'] for row in m['detail']['fields']),
              'Four cooking servings scale the actual ingredient requirement')
        check(ev,m['detail']['cost']['total'] is not None and abs(m['detail']['cost']['total']-detail.EXPECTED['recipe-1']*4)<.00001,
              'The displayed total ingredient estimate scales with four cooking portions')
        check(ev,frame.evaluate(REPORT)==first,'The recipe nutrition basis remains one person after cooking portions change')
        check(ev,old.inside(m['detail']['tray'],m['shell']) and m['document']['width']<=width+1 and m['document']['scrollY']==0,
              'The actual detail remains in the fitted widget without page overflow',m['detail']['tray'],True)
        target(ev,frame.locator('#recipePortions'),'Cooking portion input')
        nutrition(frame)
        service=frame.locator('#tray [data-recipe-nutrition-service]')
        check(ev,service.count()==1 and '1인분 영양' in service.inner_text() and '4인분' in service.inner_text(),
              'The genuine nutrition panel explicitly separates one-person nutrition from the four-person batch')
        check(ev,not frame.locator('#recipePortions').is_visible(),
              'Nutrition replaces the cooking toolbar instead of spending the short viewport on a hidden ingredient task')
        initial_energy=service.locator('.rn-energy').evaluate(TEXT)
        check(ev,initial_energy['inside'] and initial_energy['hit'] and initial_energy['text']
              and all(t['readable'] for t in initial_energy['text']),
              'The first actual nutrition value is readable immediately on tab entry without a test scroll',initial_energy,True)
        for control,control_label in [('#tray .workflow-nav button','Nutrition navigation back'),('#tray .recipe-favorite','Nutrition favorite')]:
            detail.target(ev,frame.locator(control).first.evaluate(CONTROL),control_label)
        for tab in frame.locator('#tray [data-recipe-tab]').all():
            painted=tab.evaluate(TEXT)
            check(ev,painted['inside'] and painted['hit'] and painted['text']
                  and all(t['readable'] for t in painted['text']),
                  'Every nutrition tab keeps its actual painted target clear of the back/favorite overlay immediately on entry',painted,True)
        titles=frame.evaluate("""()=>[...document.querySelectorAll('#trayTitle,.workflow-context')].filter(e=>{
          const s=getComputedStyle(e);return e.getClientRects().length&&s.visibility!=='hidden'&&s.display!=='none'&&e.textContent.trim()==='요리 상세';
        }).map(e=>({id:e.id,class:e.className,text:e.textContent.trim()}))""")
        check(ev,len(titles)==1,'Exactly one recipe-detail header is visible in the actual widget/app mode',titles,True)
        if label in SELECTED:
            # Match the baseline's actual tab-entry state, before the later
            # readability checks deliberately scroll through the long panel.
            shot(ev,page,folder,'after-'+label+'-nutrition')
        for key in KEYS:
            row=service.locator('.rn-recipe [data-recipe-nutrient="'+key+'"]')
            check(ev,row.count()==1,key+' is present exactly once in recipe nutrition')
            readable(ev,row,key+' recipe nutrient')
        check(ev,'407.1' in service.locator('.rn-energy').inner_text(),
              'Displayed energy is the one-person estimate, not four servings')
        text=service.inner_text()
        check(ev,'총당류' in text and '유리당' in text and '직접 정한' in text,
              'Total sugar is distinguished from free/added-sugar recommendations')
        for key in ('carb','protein','fat','sugar','sodium'):
            row=service.locator('[data-daily-nutrient="'+key+'"]')
            check(ev,'식사 기록이 없어요' in row.inner_text() and not row.locator('[data-nutrient-projection]').count(),
                  key+' does not invent zero intake or a projected healthy allowance for an empty diary')
        source=service.locator('.rn-source-details');center(source.locator('summary')).click();old.ready(frame)
        check(ev,'2015' in source.inner_text() and 'USDA' in source.inner_text(),
              'The selected SR28 release is disclosed instead of being called a current food analysis',source.inner_text())
        roles=service.locator('.rn-role-details');center(roles.locator('summary')).click();old.ready(frame)
        check(ev,'계란' in roles.inner_text() and '단백질' in roles.inner_text()
              and '밥' in roles.inner_text() and '탄수화물' in roles.inner_text(),
              'The real recipe connects its ingredients to their nutritional roles instead of generic health promises')
        target(ev,service.locator('[data-wf=nutritionTargets]'),'Personal goals and limits setup')
        if baseline is not None:
            check(ev,original==baseline and m['shell']==before_shell,
                  'Before/after use the exact same default stored data and fitted frame')
        check(ev,old.state(frame)==original,'All portions, nutrition tabs and source disclosures preserve exact stored data')
        living.tab(frame,'records','nutrition')
        frame.locator('#homeNutrition [data-wf=nutritionCoach]').click();old.ready(frame)
        setup=frame.locator('#tray [data-wf=nutritionTargets]')
        check(ev,setup.count()==1,'The empty daily service exposes one unambiguous goal setup action')
        detail.target(ev,setup.evaluate(CONTROL),'Initially visible empty-diary goal setup')
        check(ev,old.state(frame)==original,'An empty nine-nutrient service does not invent a meal, target or zero intake')
        ev['final_state']=old.state(frame)
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:shot(ev,page,folder,label+'-failure')
    return finish(ev,context)


def reference_meal_case(browser,origin,kind,width,height,folder):
    ev={'id':'reference-meal-'+kind,'checks':[],'page_errors':[],'blocked_requests':[]};context=page=None
    try:
        context,page,frame=open_case(browser,origin,old.ENTRIES[kind],width,height,ev)
        frame.evaluate("""()=>KitchenJournal.transact(({play,flow})=>{
          const meal=play.record({day:'2026-11-09',name:'QA preserved historical meal',portion:'QA previously entered',recipeId:null,
            nutrients:{kcal:371,carb:37,protein:19,fat:11,fiber:null,water:null}}).record;
          flow.extraNutrients[meal.id]={calcium:null,sodium:777,sugar:7};
        })""")
        if kind=='opaque':
            frame.evaluate("""()=>KitchenJournal.transact(({flow})=>{
              flow.recipeFacts['recipe-1']={kcal:null,carb:null,protein:0,fat:null,fiber:null,water:null,
                cost:null,source:'QA explicitly entered zero, not a reference default'};
            })""")
        original=old.state(frame);detail.recipe(frame);portion(frame,4)
        frame.locator('#tray [data-wf=logMeal]').click();old.ready(frame)
        form=frame.locator('#workflowMealForm')
        check(ev,form.locator('[name=portions]').input_value()=='1',
              'Four cooking portions open a separate personal meal confirmation defaulting to one')
        check(ev,all(form.locator('[name="'+key+'"]').input_value()==('0' if kind=='opaque' and key=='protein' else '') for key in KEYS),
              'Reference nutrition is not silently inserted as an actual eaten meal')
        check(ev,old.state(frame)==original,'Opening personal meal review writes no nutrition or inventory')
        personal_label=form.locator('[name=portions]').locator('..')
        label=personal_label.evaluate("e=>({text:e.innerText,height:e.getBoundingClientRect().height})")
        check(ev,'먹은 인분' in label['text'] and label['height']<=60,
              'The personal-serving label stays short and readable instead of wrapping vertically through the form',label,True)
        target(ev,form.locator('[name=portions]'),'Actual personal-serving input')
        for key in ('day','slot','portions'):
            field=form.locator('[name="'+key+'"]')
            painted_label=field.evaluate(LABEL)
            check(ev,painted_label['text'] and len(painted_label['lines'])==1 and painted_label['clear'],
                  key+' has a horizontal visible label that does not run beneath its input/select',painted_label,True)
        shot(ev,page,folder,ev['id']+'-confirmation')
        importer=form.locator('[data-wf=useReferenceNutrition]')
        target(ev,importer,'Explicit reference nutrition import')
        importer.click();old.ready(frame)
        confirmed=dict(FRIED_RICE)
        if kind=='opaque':confirmed['protein']=0
        for key,expected in confirmed.items():
            value=form.locator('[name="'+key+'"]').input_value()
            check(ev,value=='' if expected is None else value!='' and abs(float(value)-expected)<.0000011,
                  key+' imports only complete one-person reference data',value)
        check(ev,old.state(frame)==original,'Explicit reference preview still does not record food or consume stock')
        personal=form.locator('[name=portions]')
        old.reveal(personal).fill('0.5');personal.dispatch_event('change');old.ready(frame)
        for key,expected in confirmed.items():
            value=form.locator('[name="'+key+'"]').input_value()
            check(ev,value=='' if expected is None else value!='' and abs(float(value)-expected*.5)<.0000011,
                  key+' follows the independently chosen half-person portion without inventing missing values')
        old.reveal(personal).fill('1');personal.dispatch_event('change');old.ready(frame)
        date=old.reveal(form.locator('[name=day]'));date.fill('2026-11-09');date.dispatch_event('change');old.ready(frame)
        check(ev,all(form.locator('[name="'+key+'"]').input_value()==('0' if kind=='opaque' and key=='protein' else '') for key in KEYS),
              'Moving before reference adoption removes only imported values instead of backfilling later app knowledge')
        date.fill(DAY);date.dispatch_event('change');old.ready(frame)
        form.locator('[data-wf=useReferenceNutrition]').click();old.ready(frame)
        check(ev,old.state(frame)==original,'Changing personal portions and dates remains a read-only meal draft')
        imported_fields={k for k,v in FRIED_RICE.items() if v is not None}
        if kind=='opaque':
            imported_fields.remove('protein')
            form.locator('[data-wf=mealTab][data-arg=details]').click();old.ready(frame)
            old.reveal(form.locator('[name=carb]')).fill('0');old.ready(frame)
            confirmed['carb']=0;imported_fields.remove('carb')
            check(ev,form.locator('[name=protein]').input_value()=='0',
                  'Loading reference estimates preserves an explicit zero previously entered for the recipe')
        form.locator('[type=submit]').click();old.ready(frame)
        saved=old.state(frame)['envelope'];meal=saved['play']['meals'][-1]
        tx=next(t for t in saved['workflow']['transactions'] if t['mealId']==meal['id'] and t['active'])
        check(ev,len(saved['play']['meals'])==len(original['envelope']['play']['meals'])+1
              and tx['portions']==1 and meal['source']=='manual',
              'Actual Save records one confirmed personal serving while preserving the established meal schema',meal)
        check(ev,saved['play']['meals'][:-1]==original['envelope']['play']['meals']
              and all(saved['workflow']['extraNutrients'][m['id']]==original['envelope']['workflow']['extraNutrients'][m['id']]
                      for m in original['envelope']['play']['meals']),
              'Reference data never retroactively replaces the exact historical meal and extra nutrient values')
        for key in BASE:
            expected=confirmed[key];value=meal['nutrients'][key]
            check(ev,value is None if expected is None else abs(value-expected)<.0000011,
                  key+' is stored exactly as explicitly confirmed reference data')
        provenance=tx.get('nutritionSource')
        check(ev,provenance and provenance.get('kind')=='reference-confirmed'
              and set(provenance.get('fields',[]))==imported_fields,
              'Reference provenance records only the fields actually imported, not missing values',provenance)
        check(ev,saved['workflow']['expenses']==original['envelope']['workflow']['expenses']
              and saved['play']['targets']==original['envelope']['play']['targets'],
              'Meal Save changes neither paid cash nor personal targets')
        egg=next(i for i in original['envelope']['world']['items'] if i['name']=='계란')
        egg_after=next(i for i in saved['world']['items'] if i['id']==egg['id'])
        before_count=re.fullmatch(r'(\d+(?:\.\d+)?)개',egg['quantity'])
        after_count=re.fullmatch(r'(\d+(?:\.\d+)?)개',egg_after['quantity'])
        check(ev,before_count and after_count and float(after_count[1])==float(before_count[1])-1,
              'Only one personal portion of egg is consumed, not the four-person batch')
        shot(ev,page,folder,ev['id']+'-saved')
        frame.locator('#tray [data-wf=undoSuccessMeal]').click();old.ready(frame)
        undone=old.state(frame)['envelope']
        check(ev,undone['world']==original['envelope']['world'] and undone['play']['meals']==original['envelope']['play']['meals'],
              'Actual Undo restores exact stock and eaten nutrition without rewriting previous meals')
        restored=frame.locator('#workflowMealForm')
        check(ev,restored.count()==1 and restored.locator('[name=portions]').input_value()=='1',
              'Undo opens the original confirmed personal-serving draft instead of the four-person cooking batch')
        for key,expected in confirmed.items():
            value=restored.locator('[name="'+key+'"]').input_value()
            check(ev,value=='' if expected is None else value!='' and abs(float(value)-expected)<.0000011,
                  key+' survives undo in its saved draft rather than being recomputed from a newer source')
        restored.locator('[type=submit]').click();old.ready(frame)
        resaved=old.state(frame)['envelope'];again=resaved['play']['meals'][-1]
        again_tx=next(t for t in resaved['workflow']['transactions'] if t['mealId']==again['id'] and t['active'])
        check(ev,resaved['world']==saved['world'] and again['nutrients']==meal['nutrients']
              and resaved['workflow']['extraNutrients'][again['id']]==saved['workflow']['extraNutrients'][meal['id']]
              and again_tx.get('nutritionSource')==provenance,
              'Saving the Undo draft restores the same stock use, confirmed nutrition and reference field provenance')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:shot(ev,page,folder,ev['id']+'-failure')
    return finish(ev,context)


def plan_case(browser,origin,kind,folder):
    ev={'id':'cooking-and-legacy-plan-'+kind,'checks':[],'page_errors':[],'blocked_requests':[]};context=page=None
    try:
        context,page,frame=open_case(browser,origin,old.ENTRIES[kind],390,480,ev)
        original=old.state(frame)['envelope'];detail.recipe(frame);portion(frame,4)
        frame.locator('#tray [data-wf=planRecipe]').click();old.ready(frame)
        form=frame.locator('#tray [data-wf-form=plan]');form.locator('[name=day]').fill(DAY)
        form.locator('[type=submit]').click();old.ready(frame)
        planned=old.state(frame)['envelope'];plan=planned['workflow']['plans'][-1]
        check(ev,plan['portions']==4 and plan.get('servingBasis')=='cooking',
              'A newly created batch plan explicitly stores its cooking basis',plan)
        check(ev,planned['world']==original['world'] and planned['play']==original['play'],
              'Planning a batch consumes no stock and creates no eaten nutrition')
        living.tab(frame,'meals','plans')
        center(frame.locator('[data-wf=logPlan][data-arg="'+plan['id']+'"]')).click();old.ready(frame)
        check(ev,frame.locator('#workflowMealForm [name=portions]').input_value()=='1',
              'A batch plan requires a personal one-serving confirmation rather than recording four people as one')
        old.close_tray(frame)
        frame.evaluate("""()=>KitchenJournal.transact(({flow})=>flow.plans.push({id:'qa-legacy-personal-plan',day:'2026-11-10',slot:'dinner',recipeId:'recipe-1',portions:3}))""")
        legacy=old.state(frame);living.tab(frame,'meals','plans')
        center(frame.locator('[data-wf=logPlan][data-arg=qa-legacy-personal-plan]')).click();old.ready(frame)
        check(ev,frame.locator('#workflowMealForm [name=portions]').input_value()=='3',
              'An existing plan without the new basis preserves its historical three-person quantity')
        check(ev,old.state(frame)==legacy,'Opening either plan confirmation leaves the exact plan and historical records untouched')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:shot(ev,page,folder,ev['id']+'-failure')
    return finish(ev,context)


def daily_case(browser,origin,kind,width,height,folder):
    ev={'id':'daily-guidance-'+kind,'checks':[],'page_errors':[],'blocked_requests':[]};context=page=None
    try:
        context,page,frame=open_case(browser,origin,old.ENTRIES[kind],width,height,ev)
        frame.evaluate(DAILY_FIXTURE);fixture=old.state(frame);detail.recipe(frame);nutrition(frame)
        report=frame.evaluate(DAILY)
        for key,remaining in [('carb',170),('protein',40),('fat',45)]:
            row=report['nutrients'][key]
            check(ev,row['remaining']==remaining and row['missingCount']==0 and row['projection'] is not None,
                  key+' reports the actual remaining personal target and complete one-serving projection',row)
            card=frame.locator('#tray [data-daily-nutrient="'+key+'"]');readable(ev,card,key+' complete daily comparison')
            check(ev,'남음' in card.inner_text() and '1인분 후' in card.inner_text(),
                  key+' exposes both current remaining amount and the hypothetical one-person addition')
        for key,excess in [('sodium',200),('sugar',5)]:
            row=report['nutrients'][key]
            check(ev,row['status']=='over' and row['excess']==excess and not row['lowerBound'],
                  key+' compares actual entered amounts with the explicit personal management limit',row)
        check(ev,report['nutrients']['sugar']['projection'] is None,
              'An incomplete recipe total-sugar value cannot create a fictitious safe/over-limit projection')
        sodium=frame.locator('#tray [data-daily-nutrient=sodium]');readable(ev,sodium,'Actual sodium warning')
        check(ev,'많아요' in sodium.inner_text() and '내 기준' in sodium.inner_text(),
              'The warning identifies a personal limit rather than an invented universal prescription')
        target(ev,frame.locator('#tray [data-wf=nutritionTargets]'),'Nutrition target setup')
        frame.locator('#tray [data-wf=nutritionTargets]').click();old.ready(frame)
        goals=frame.locator('#tray [data-wf-form=targets]')
        check(ev,goals.count()==1 and goals.locator('[name=sodium]').input_value()=='2000'
              and goals.locator('[name=sugar]').input_value()=='40',
              'Goal setup exposes the saved sodium and total-sugar management values')
        goals.locator('[type=submit]').click();old.ready(frame)
        check(ev,old.state(frame)==fixture,'Saving unchanged goals preserves all existing meal and stock data')
        old.close_tray(frame);frame.evaluate(PARTIAL_FIXTURE);partial=old.state(frame)
        detail.recipe(frame);nutrition(frame);report=frame.evaluate(DAILY)
        for key in ('carb','fat'):
            row=report['nutrients'][key]
            check(ev,row['status']=='partial' and row['remaining'] is None and row['projection'] is None,
                  key+' with an unentered meal never claims an exact remaining allowance',row)
        for key,excess in [('sodium',200),('sugar',5)]:
            row=report['nutrients'][key]
            check(ev,row['status']=='over' and row['lowerBound'] and row['remaining'] is None and row['excess']==excess,
                  key+' may identify only the already-known minimum excess when another meal is missing',row)
            card=frame.locator('#tray [data-daily-nutrient="'+key+'"]');readable(ev,card,key+' partial-record warning')
            check(ev,'기록된 값만으로 최소' in card.inner_text(),
                  key+' visibly qualifies its lower-bound warning instead of calling missing meals normal')
        check(ev,report['nutrients']['protein']['complete'] and report['nutrients']['protein']['remaining']==40,
              'An explicitly entered zero remains known and does not make protein incomplete')
        check(ev,old.state(frame)==partial,'Guidance and projections never retroactively recalculate saved meals')
        shot(ev,page,folder,ev['id']+'-partial')
        living.tab(frame,'records','nutrition')
        coach=frame.locator('#homeNutrition [data-wf=nutritionCoach]')
        target(ev,coach,'Visible detailed daily nutrition entry')
        coach.click();old.ready(frame)
        check(ev,frame.locator('#tray[data-workflow-route=nutritionCoach]').count()==1
              and frame.locator('#tray .rn-recipe').count()==0,
              'Daily guidance opens its standalone service, not an unrelated recipe or hidden legacy tab')
        shot(ev,page,folder,ev['id']+'-standalone')
        for key in KEYS:
            row=frame.locator('#tray [data-daily-nutrient="'+key+'"]')
            check(ev,row.count()==1,key+' is available in the standalone daily service')
            readable(ev,row,key+' standalone daily comparison')
        check(ev,old.state(frame)==partial,'Opening the standalone nine-nutrient service changes no stored meal or target')
        old.close_tray(frame)
        frame.evaluate("""()=>KitchenJournal.transact(({play,flow})=>{
          for(const meal of play.state().meals)play.remove(meal.id);
          flow.extraNutrients={};
          const m=play.record({day:'2026-11-10',name:'QA explicitly known zero',portion:'QA all fields zero',recipeId:null,
            nutrients:{kcal:0,carb:0,protein:0,fat:0,fiber:0,water:0}}).record;
          flow.extraNutrients[m.id]={calcium:0,sodium:0,sugar:0};
        })""")
        zero=old.state(frame);living.tab(frame,'records','nutrition')
        frame.locator('#homeNutrition [data-wf=nutritionCoach]').click();old.ready(frame)
        report=frame.evaluate(DAILY)
        for key in KEYS:
            row=report['nutrients'][key]
            check(ev,row['value']==0 and row['missingCount']==0 and row['status']=='below',
                  key+' preserves a genuinely entered zero as a complete known value')
            today=frame.locator('#tray [data-daily-nutrient="'+key+'"] .rn-today')
            check(ev,'미입력' not in today.inner_text() and '0 ' in today.inner_text(),
                  key+' renders the explicit zero instead of the missing-value state')
        check(ev,old.state(frame)==zero,'Reading explicit-zero guidance keeps its exact stored values')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:shot(ev,page,folder,ev['id']+'-failure')
    return finish(ev,context)


def inputs(root):
    return {p:{'bytes':(root/p).stat().st_size,'sha256':old.digest((root/p).read_bytes())} for p in closed.DELIVERIES}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--before',type=Path);parser.add_argument('--browser-executable',default='/usr/bin/chromium')
    args=parser.parse_args();root,out=args.root.resolve(),args.output.resolve();before=args.before.resolve() if args.before else None
    if out.is_relative_to(REPO) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in [root,*([before] if before else [])]):
        parser.error('Evidence must be outside the checkout and frozen deliveries.')
    out.mkdir(parents=True,exist_ok=False);screens=out/'screens';screens.mkdir()
    original={'after':inputs(root),**({'before':inputs(before)} if before else {})}
    hashes={p:old.digest((REPO/'scripts'/p).read_bytes()) for p in SOURCES}
    shutil.copyfile(Path(__file__),out/'executed-test-source.py');old.CLOCK=detail.CLOCK
    report={'scope':'Local frozen Chromium; explicit disposable QA records and confirmed reference inputs; no user/provider/production writes',
            'clock':detail.CLOCK.isoformat(),'inputs':original,'verification_sources':hashes,'cases':[],'passed':False,
            'manual_review':'Actual selected PNGs require a separate visual review; no live Notion/Safari/physical-device claim.'}
    server,origin=closed.serve(root);before_server=before_origin=None
    if before:before_server,before_origin=closed.serve(before)
    def save(case=None):
        if case:
            report['cases'].append(case);print(json.dumps({'id':case['id'],'passed':case['passed'],
                'failed':[c['name'] for c in case['checks'] if not c['passed']]},ensure_ascii=False),flush=True)
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.browser_executable,args=['--no-sandbox'])
            for kind,entry,width,height in PROFILES:save(layout_case(browser,origin,before_origin,entry,width,height,kind,screens))
            for kind,width,height in [('native',720,800),('opaque',390,480)]:
                save(reference_meal_case(browser,origin,kind,width,height,screens));save(plan_case(browser,origin,kind,screens))
            for kind,width,height in [('native',720,800),('opaque',320,360)]:save(daily_case(browser,origin,kind,width,height,screens))
            browser.close()
    finally:
        server.shutdown()
        if before_server:before_server.shutdown()
    report.update(expected_cases=14,complete=len(report['cases'])==14,assertions=sum(len(c['checks']) for c in report['cases']),
                  inputs_unchanged=original=={'after':inputs(root),**({'before':inputs(before)} if before else {})},
                  verification_sources_unchanged=hashes=={p:old.digest((REPO/'scripts'/p).read_bytes()) for p in SOURCES},
                  delivery_under_1MiB=all(v['bytes']<=1048576 for group in original.values() for v in group.values()))
    report['expected_screenshots']=16 if before else 12
    report['screenshot_count']=len(list(screens.glob('*.png')))
    report['screenshots_complete']=report['screenshot_count']==report['expected_screenshots']
    report['passed']=all(report[k] for k in ('complete','inputs_unchanged','verification_sources_unchanged','delivery_under_1MiB','screenshots_complete')) and all(c['passed'] for c in report['cases'])
    save();print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'assertions':report['assertions']}))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
