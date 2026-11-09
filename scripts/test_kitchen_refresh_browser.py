#!/usr/bin/env python3
"""Exercise the approved kitchen refresh in frozen local preview files.

The photographs and CSS are tested as delivered, not by loading the source
template. Contexts and explicit QA fixtures are disposable. No OCR/provider,
production write, personal storage, physical-device or Notion claim is made.
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
import test_kitchen_widget_browser as old
import test_kitchen_living_browser as living
import test_kitchen_closed_browser as closed
from test_fridge_four_door_browser import drag


REPO = Path(__file__).resolve().parents[1]
PROFILES = ((320, 360), (390, 480), (720, 800), (800, 600))
APP_PROFILES = ((390, 844), (720, 900))
ENTRIES = old.ENTRIES
DELIVERIES = closed.DELIVERIES
DAY = living.DAY

DOOR_FREE_JS = r'''e=>{
 const r=e.getBoundingClientRect(),size=44;if(r.width<43.5||r.height<43.5)return null;
 for(const fx of [0,.25,.5,.75,1])for(const fy of [0,.25,.5,.75,1]){
  const x=r.x+Math.max(0,r.width-size)*fx,y=r.y+Math.max(0,r.height-size)*fy;
  if(x<-.5||y<-.5||x+size>innerWidth+.5||y+size>innerHeight+.5)continue;
  let clear=true;
  for(const dx of [3,22,41])for(const dy of [3,22,41]){
   const hit=document.elementFromPoint(x+dx,y+dy);if(hit!==e&&!e.contains(hit))clear=false;
  }
  if(clear)return{rect:{x,y,width:size,height:size,right:x+size,bottom:y+size},
   x:x+22-r.x,y:y+22-r.y};
 }
 return null;
}'''

METRICS = r'''async()=>{''' + old.PAINT_HELPERS + r'''
 const m=await (''' + living.GEOMETRY + r''')();
 const box=e=>{if(!e||!e.getClientRects().length)return null;const r=e.getBoundingClientRect();
  return{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
 const visible=e=>{if(!box(e))return false;for(let p=e;p;p=p.parentElement){const c=getComputedStyle(p);
  if(p.hidden||c.display==='none'||c.visibility==='hidden'||Number(c.opacity)===0)return false}return true};
 const control=e=>{if(!e)return null;const r=box(e);if(!r)return null;
  const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
  const shell=box(e.closest('.shell'));
  return{rect:r,label:e.getAttribute('aria-label')||e.textContent.trim(),
   hit:hit===e||e.contains(hit),disabled:e.disabled,
   inside:visible(e)&&r.x>=-1&&r.y>=-1&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1
    &&(!shell||(r.x>=shell.x-1&&r.y>=shell.y-1&&r.right<=shell.right+1&&r.bottom<=shell.bottom+1))}};
 const photo=document.querySelector('#fridgeSceneHost .original-kitchen-photo');
 let background=null;
 if(photo){
  const image=new Image();image.src=photo.currentSrc||photo.src;
  try{await image.decode();const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;
   canvas.height=image.naturalHeight;const c=canvas.getContext('2d',{willReadFrequently:true});c.drawImage(image,0,0);
   const pixels=c.getImageData(0,0,canvas.width,canvas.height).data;let nonOpaque=0;
   for(let i=3;i<pixels.length;i+=4)if(pixels[i]!==255)nonOpaque++;
   background={decoded:true,width:image.naturalWidth,height:image.naturalHeight,
    rect:box(photo),nonOpaque,total:canvas.width*canvas.height};
  }catch(error){background={decoded:false,error:String(error)}}
 }
 const freeDoor=(''' + DOOR_FREE_JS + r''');
 const images=new Map(),foodKinds=new Set(['food','seasoning','meal']);
 const itemKinds=new Map(MiniKitchen.exportWorld().items.map(i=>[i.id,i.kind]));
 const actualFood=[];
 for(const e of [...document.querySelectorAll('#fridgeSceneHost .item')].filter(visible)){
  if(!foodKinds.has(itemKinds.get(e.dataset.item)))continue;
  const image=e.querySelector('.food-art image'),svg=image?.closest('svg')||e.querySelector('svg.food-art');
  let paint=null,decoded=null;
  if(image&&svg){
   const src=image.getAttribute('href');
   if(!images.has(src)){
    try{const i=new Image();i.src=src;await i.decode();const c=document.createElement('canvas');
     c.width=i.naturalWidth;c.height=i.naturalHeight;const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(i,0,0);
     images.set(src,{ctx,width:i.naturalWidth,height:i.naturalHeight});
    }catch(_){images.set(src,null)}
   }
   const source=images.get(src);decoded=!!source;
   if(source){
    const v=svg.viewBox.baseVal,im={x:image.x.baseVal.value,y:image.y.baseVal.value,
     w:image.width.baseVal.value,h:image.height.baseVal.value};
    const sx=Math.max(0,Math.floor((v.x-im.x)/im.w*source.width));
    const sy=Math.max(0,Math.floor((v.y-im.y)/im.h*source.height));
    const ex=Math.min(source.width,Math.ceil((v.x+v.width-im.x)/im.w*source.width));
    const ey=Math.min(source.height,Math.ceil((v.y+v.height-im.y)/im.h*source.height));
    if(ex>sx&&ey>sy){const pixels=source.ctx.getImageData(sx,sy,ex-sx,ey-sy).data;
     let l=ex,t=ey,r=-1,b=-1;
     // Alpha16 excludes invisible AVIF residue while retaining actual art/shadows.
     for(let y=sy;y<ey;y++)for(let x=sx;x<ex;x++)if(pixels[((y-sy)*(ex-sx)+x-sx)*4+3]>=16){
      l=Math.min(l,x);r=Math.max(r,x+1);t=Math.min(t,y);b=Math.max(b,y+1)}
     if(r>=l&&b>=t){const m=svg.getScreenCTM(),pts=[[l,t],[r,t],[l,b],[r,b]].map(([x,y])=>
       new DOMPoint(im.x+x/source.width*im.w,im.y+y/source.height*im.h).matrixTransform(m));
      const x=Math.min(...pts.map(p=>p.x)),y=Math.min(...pts.map(p=>p.y)),right=Math.max(...pts.map(p=>p.x)),bottom=Math.max(...pts.map(p=>p.y));
      paint={x,y,right,bottom,width:right-x,height:bottom-y,method:'decoded-alpha16'};
     }
    }
   }
  }else if(svg){
   const b=svg.getBBox(),m=svg.getScreenCTM(),pts=[[b.x,b.y],[b.x+b.width,b.y+b.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
   paint={x:pts[0].x,y:pts[0].y,right:pts[1].x,bottom:pts[1].y,width:pts[1].x-pts[0].x,height:pts[1].y-pts[0].y,method:'vector-bounds'};
  }
  const zone=e.closest('[data-zone]');
  actualFood.push({id:e.dataset.item,kind:itemKinds.get(e.dataset.item),zone:zone?.dataset.zone,zoneRect:box(zone),rect:box(e),paint,decoded,
   labels:[...e.querySelectorAll('.item-name,.item-label,.quantity')].filter(visible).map(box)});
 }
 return {...m,mode:document.body.dataset.mode,
  recipe:{...m.recipe,actions:[...document.querySelectorAll('.recipe-view-actions button,.refresh-recipe-filters button')]
   .filter(visible).map(e=>({...control(e),workflow:e.dataset.wf}))},
  refresh:{background,header:box(document.querySelector('.masthead')),
  appliedBannerVisible:visible(document.querySelector('#appliedRoomMessage')),
  storageStatus:KitchenJournal.status,
  storageNotice:control(document.querySelector('#homeStorageNotice [data-wf="backupTools"]')),
  storageNoticeText:textRanges(document.querySelector('#homeStorageNotice')).filter(r=>r.readable).map(r=>r.text).join(' '),
  storageNoticeFonts:[...document.querySelectorAll('#homeStorageNotice button span,#homeStorageNotice button strong')].filter(visible).map(e=>parseFloat(getComputedStyle(e).fontSize)),
  brandTitle:box(document.querySelector('#refreshBrand h1')),
  balance:box(document.querySelector('#dailyBalance')),shelf:box(document.querySelector('#homeSupplementsShelf')),
  visibleShelfText:textRanges(document.querySelector('#homeSupplementsShelf')).filter(r=>r.readable).map(r=>r.text).join(' '),
  shelfManagement:control([...document.querySelectorAll('#homeSupplementsShelf [data-living-supplements]')].find(visible)),
  nutrition:KitchenJournal.summary('2026-11-05').nutrients,
  balanceValues:[...document.querySelectorAll('#dailyBalance [data-balance]')].map(e=>({
   key:e.dataset.balance,empty:e.dataset.empty,partial:e.dataset.partial,
   value:e.querySelector('.balance-number strong')?.textContent.trim(),
   target:e.querySelector('.balance-number>span')?.textContent.trim(),
   track:box(e.querySelector('.balance-track')),fill:box(e.querySelector('.balance-track i')),
   progress:e.querySelector('.balance-track')?.getAttribute('aria-valuenow'),
   visibleText:textRanges(e).filter(r=>r.readable).map(r=>r.text).join(' ')})),
  add:control(document.querySelector('#addFood')),inventory:control(document.querySelector('.header-actions [data-workflow="inventory"]')),
  doors:[...document.querySelectorAll('[data-door]')].map(e=>({id:e.dataset.door,rect:box(e),
    visible:visible(e),expanded:e.getAttribute('aria-expanded'),free:freeDoor(e)})),
  food:actualFood,roomWorld:box(document.querySelector('#decorStage .scene-world')),
  realDecor:[...document.querySelectorAll('#decorStage .item.decor')].filter(visible)
    .map(e=>({id:e.dataset.item,rect:box(e)}))}};
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


def target(ev, item, name, minimum=44):
    r = item and item.get('rect')
    check(ev, bool(r and r['width'] >= minimum-.5 and r['height'] >= minimum-.5
                  and item.get('hit', True) and item.get('inside',True)), name+' is visible and has a real '+str(minimum)+'px hit area',
          item, layout=True)


def readonly(ev, frame, original, name):
    current = old.state(frame)
    check(ev, current['raw'] == original['raw'] and current['envelope'] == original['envelope']
          and current['key'] == old.KEY, name)


def click_door(frame,key):
    door=frame.locator('[data-door="'+key+'"]');point=door.evaluate(DOOR_FREE_JS)
    if point is None:raise AssertionError('No unobscured44px door target for '+key)
    door.click(position={'x':point['x'],'y':point['y']});old.ready(frame)


def capture(page, frame, folder, name):
    old.ready(frame)
    m = frame.evaluate(METRICS)
    page.screenshot(path=str(folder/(name+'.png')), animations='disabled', caret='hide')
    return m


def shell_geometry(ev, m):
    living.main_geometry(ev, m)
    for tab in m['navTabs']:
        check(ev, old.inside(tab['rect'], m['nav']),
              'Navigation stays in the one footer row', tab['rect'], layout=True)
    check(ev, bool(m['panel'] and m['panel']['height'] > 100),
          'The active screen has usable space inside the bounded widget', m['panel'], layout=True)


def nutrition_view(ev,r):
    for column in r['balanceValues']:
        expected=r['nutrition'][column['key']];value=column['value']or'';goal=column['target']or''
        actual=re.search(r'-?\d+(?:[,.]\d+)*',value)
        check(ev,(('—'in value or'미입력'in value or'기록 전'in value)if expected['value']is None
                   else actual is not None and float(actual[0].replace(',',''))==expected['value']),
              column['key']+' header displays actual entered nutrition or an honest unknown',column)
        target_number=re.search(r'-?\d+(?:[,.]\d+)*',goal)
        check(ev,not target_number if expected['target']is None else target_number is not None
              and float(target_number[0].replace(',',''))==expected['target'],
              column['key']+' header never substitutes the design example for an unset personal target',column)
        check(ev,not expected['missing']or any(word in column['visibleText']for word in ['미입력','일부']),
              column['key']+' retains an initially visible partial-nutrition indication',column)
        if column['track']:
            width=column['fill']['width']if column['fill']else 0
            percent=expected['percent']
            wanted=0 if percent is None else min(100,round(percent))/100*column['track']['width']
            check(ev,abs(width-wanted)<=1 and (percent is not None or column['progress']is None),
                  column['key']+' progress uses the actual personal target and remains empty while unknown',column)


def home_geometry(ev, m, contract, populated):
    r = m['refresh'];nutrition_view(ev,r)
    if r['storageStatus']=='temporary':
        target(ev,r['storageNotice'],'Temporary-session backup entry')
        check(ev,'임시'in r['storageNoticeText'] and '백업'in r['storageNoticeText'],
              'The opaque preview visibly identifies its temporary storage and backup action',r['storageNoticeText'])
        check(ev,bool(r['storageNoticeFonts']) and min(r['storageNoticeFonts'])>=11,
              'Temporary storage and backup use readable text instead of a tiny title underline',r['storageNoticeFonts'],layout=True)
        for other,name in [(r['brandTitle'],'title'),(r['inventory']['rect'],'inventory'),(r['shelf'],'supplements')]:
            check(ev,overlap(r['storageNotice']['rect'],other)<=1,
                  'Temporary backup is separate from '+name,layout=True)
    for item, name in [(r['add'], 'Ingredient addition'), (r['inventory'], 'Ingredient inventory')]:
        target(ev, item, name)
    for item in m['shelf']['controls']:
        target(ev, item, 'Supplement '+item['label'])
    target(ev,r['shelfManagement'],'Supplement registration/management entry')
    check(ev, r['shelf'] and old.inside(r['shelf'], m['shell']),
          'The supplement row fits the shared home header', r['shelf'], layout=True)
    check(ev,not r['appliedBannerVisible'],
          'The initial refrigerator does not show an unearned room-application success banner',layout=True)
    check(ev,not overlap(r['shelf'],r['balance']),
          'The supplement row does not overlap the nutrition summary',
          {'shelf':r['shelf'],'nutrition':r['balance']},layout=True)
    if contract and m['shell']['width']<contract['layout']['compact_content_width']:
        check(ev,old.inside(r['shelf'],r['header']),
              'The compact supplement entry remains within the shared brand row',
              {'shelf':r['shelf'],'brand':r['header']},layout=True)
    if r['shelf'] and m['scene']['host']:
        check(ev, abs(center(r['shelf'])-center(m['scene']['host'])) <= 1,
              'The supplement row is centred on the kitchen', r['shelf'], layout=True)
    if r['shelf'] and m['scene']['stage']:
        check(ev, r['shelf']['bottom'] <= m['scene']['stage']['y']+1,
              'The supplement row does not cover the refrigerator', layout=True)
    check(ev, populated or ('등록' in r['visibleShelfText'] and not re.search(r'0\s*/\s*0',r['visibleShelfText'])),
          'Unregistered supplements use the compact honest registration state', r['visibleShelfText'],layout=True)
    bg = r['background']
    check(ev, bg and bg.get('decoded') and bg.get('nonOpaque') == 0,
          'The delivered continuous kitchen background decodes fully opaque', bg, layout=True)
    natural = m['scene']['natural']
    photo = m['scene']['photo']
    check(ev, natural and photo and abs(photo['width']/photo['height']-
          natural['width']/natural['height']) < .002,
          'Kitchen art retains its actual source aspect ratio', {'source':natural,'painted':photo}, layout=True)
    matrix = m['scene']['matrix']
    check(ev, matrix and abs(matrix['a']-matrix['d']) < .00001
          and abs(matrix['b']) < .00001 and abs(matrix['c']) < .00001,
          'The kitchen scene uses one uniform camera scale', matrix, layout=True)
    if contract and natural:
        check(ev, [natural['width'], natural['height']] == contract['world'],
              'Delivered art matches the reviewed native registration canvas', natural, layout=True)
        if m['scene']['world'] and m['scene']['stage']:
            world = m['scene']['world'];x,y,w,h = contract['body'];scale=world['width']/contract['world'][0]
            expected={'x':world['x']+x*scale,'y':world['y']+y*scale,
                      'width':w*scale,'height':h*scale}
            actual=m['scene']['stage']
            check(ev, all(abs(actual[k]-expected[k]) <= 1 for k in expected),
                  'The real refrigerator stays in its reviewed installation space',
                  {'actual':actual,'expected':expected}, layout=True)
    check(ev, len(r['doors']) == 4 and {d['id'] for d in r['doors']} == set(closed.DOORS),
          'All four actual refrigerator doors remain available')
    for d in r['doors']:
        check(ev, d['rect'] and old.inside(d['rect'], m['scene']['host'], 2),
              d['id']+' has an on-screen door surface', d, layout=True)
        check(ev, d['free'] is not None,
              d['id']+' retains an unobscured44px target despite the approved scene overlay',d['free'],layout=True)
    for food in r['food']:
        check(ev,food['paint'] and food['paint']['width']>1 and food['paint']['height']>1 and food['decoded'] is not False,
              food['id']+' has actual decoded or vector food art',food,layout=True)
        check(ev,food['paint'] and food['zoneRect'] and old.inside(food['paint'],food['zoneRect'],2),
              food['id']+' actual art remains inside its storage compartment',food,layout=True)
        for part in [food['paint'],*food['labels']]:
            check(ev,overlap(r['add'] and r['add']['rect'],part)<=1,
                  'The primary add action does not cover '+food['id']+' art or labels',part,layout=True)


def recipe_geometry(ev, frame, m, populated):
    cards=m['recipe']['cards'];catalog=frame.evaluate('KitchenCatalog.map(r=>({id:r.id,name:r.name,time:r.time}))')
    actual={r['id']:r for r in catalog}
    preparation=frame.evaluate('''()=>Object.fromEntries(KitchenJourneyModel.recommend(KitchenCatalog,
      MiniKitchen.exportWorld(),KitchenJournal.getWorkflow(),KitchenJournal.getSnapshot(),{day:"2026-11-05"})
      .map(c=>[c.recipe.id,{enough:c.availability.rows.filter(r=>r.status==="enough"&&!r.quantityUnknown&&!r.unknownExpiryIds?.length).length,total:c.availability.rows.length}]))''')
    check(ev, len(cards)==8 and {r['id'] for r in cards}==set(actual),
          'Eight distinct real recipes are available for comparison')
    check(ev, len({round(c['rect']['x'],1) for c in cards if c['rect']})==2
          and len({round(c['rect']['y'],1) for c in cards if c['rect']})==4,
          'The eight recipes use the approved two-column four-row layout', layout=True)
    for card in cards:
        rid=card['id'];target(ev,card['control'],rid+' card')
        check(ev, old.inside(card['rect'],m['recipe']['grid']) and old.inside(card['rect'],m['panel']),
              rid+' is initially visible without paging',card['rect'],layout=True)
        check(ev, card['name']==actual[rid]['name'] and card['time']==actual[rid]['time'],
              rid+' displays the actual recipe name and time')
        check(ev, bool(card['text']) and all(t['readable'] for t in card['text']),
              rid+' comparison text remains readable',card['text'],layout=True)
        photo=card['photo']
        check(ev, photo and photo['atlas']['decoded'] and photo['recipe']==rid,
              rid+' uses its actual decoded food picture',photo,layout=True)
        known=populated and rid=='recipe-1'
        check(ev, card['kcal']['value']==('455' if known else '')
              and card['cost']['value']==('2100' if known else '')
              and ('455'in card['kcal']['text']if known else any(t in card['kcal']['text']for t in ['—','미입력']))
              and (any(t in card['cost']['text']for t in ['2,100','2100'])if known else any(t in card['cost']['text']for t in ['—','미입력'])),
              rid+' shows entered nutrition/cost or preserves the unknown',
              {'kcal':card['kcal'],'cost':card['cost']})
        check(ev, 0 <= card['stock']['enough'] <= card['stock']['total'] and card['stock']['total'] > 0,
              rid+' shows genuine ingredient sufficiency metadata',card['stock'])
        expected=preparation[rid]
        check(ev,card['stock']['enough']==expected['enough'] and card['stock']['total']==expected['total']
              and re.search(r'(?<!\d)'+str(expected['enough'])+r'\s*/\s*'+str(expected['total'])+r'(?!\d)',card['stock']['text']),
              rid+' visible ingredient counts match actual quantity/expiry analysis',card['stock'])
    for action in m['recipe']['actions']:
        target(ev,action,'Recipe '+action['label'])
    check(ev,{'recipeCatalog','recipeFilters'}<=set(c['workflow']for c in m['recipe']['actions']),
          'Catalog and filter actions remain visibly available beside the recipe comparison')
    filters=[c for c in m['recipe']['actions']if c['workflow']=='recipeFilters']
    check(ev,len(filters)==1 and '조건'in filters[0]['label'],
          'Recipe conditions have one clearly labelled control instead of three identical fake dropdowns',filters)


def recipe_clicks(ev,frame,original,subset=False):
    """Reuse the existing read-only/filter journey with the visible refresh control.

    The refresh keeps the old hidden button for its compact layout and adds
    three wide condition buttons. Choosing the currently visible control is
    essential: Playwright must exercise a real user click, never force it.
    """
    items=frame.locator('#homeRecommendation .recipe-grid-card').evaluate_all(
        '(nodes)=>nodes.map(e=>({id:e.dataset.homeRecipe,name:e.querySelector("strong").textContent.trim()}))')
    for row in items if not subset else items[:2]:
        frame.locator('#homeRecommendation [data-home-recipe="'+row['id']+'"]').click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=recipe]")')
        old.ready(frame)
        actual=frame.evaluate('''()=>({id:document.querySelector('#tray .recipe-favorite')?.dataset.arg,
          name:document.querySelector('#tray .recipe-detail-name')?.textContent.trim(),
          photo:document.querySelector('#tray svg.recipe-photo')?.dataset.recipePhoto})''')
        check(ev,actual=={'id':row['id'],'name':row['name'],'photo':row['id']},
              row['id']+' card opens the matching existing recipe detail',actual)
        readonly(ev,frame,original,row['id']+' detail is read only')
        old.close_tray(frame)
    def open_filters():
        frame.locator('.recipe-view-actions [data-wf="recipeFilters"]:visible,'
                      '.refresh-recipe-filters [data-wf="recipeFilters"]:visible').first.click()
        return frame.locator('#tray [data-wf-form="recipeFilters"]')
    form=open_filters();form.locator('[name="time"]').fill('15');form.locator('[type="submit"]').click();old.ready(frame)
    names=frame.locator('#homeRecommendation .recipe-grid-card').evaluate_all('(nodes)=>nodes.map(e=>e.dataset.homeRecipe)')
    expected=frame.evaluate(r'KitchenCatalog.filter(r=>Number(r.time.match(/\d+/)[0])<=15).map(r=>r.id)')
    check(ev,set(names)==set(expected)and 0<len(names)<8,
          'Actual filter form produces a genuine subset without fake filler')
    form=open_filters();form.locator('[name="time"]').fill('1');form.locator('[type="submit"]').click();old.ready(frame)
    check(ev,frame.locator('#homeRecommendation .recipe-grid-card').count()==0
          and frame.locator('#homeRecommendation .recipe-hub-empty:visible').count()==1,
          'No-result conditions remain an honest empty state')
    frame.locator('#homeRecommendation [data-home-filter-reset]').click();old.ready(frame)
    check(ev,frame.locator('#homeRecommendation .recipe-grid-card').count()==8,
          'Actual reset restores the eight recipes')
    check(ev,frame.evaluate('document.activeElement?.dataset.wf==="recipeFilters"'),
          'Reset returns keyboard focus to the visible recipe-condition control')
    readonly(ev,frame,original,'Filtering and resetting never persist or seed records')


def counter_geometry(ev,m,contract):
    if not contract or not contract.get('room'):return
    world=m['refresh']['roomWorld'];room=contract['room']
    check(ev,world and abs(world['width']/world['height']-room['world'][0]/room['world'][1])<.002,
          'The room editor uses its reviewed native camera aspect',world,layout=True)
    if not world:return
    x,y,w,h=room['physical_counter_plane'];scale=world['width']/room['world'][0]
    plane={'x':world['x']+x*scale,'right':world['x']+(x+w)*scale,
           'y':world['y']+y*scale,'bottom':world['y']+(y+h)*scale}
    check(ev,bool(m['refresh']['realDecor']),'Existing saved room props remain rendered in the editor')
    for prop in m['refresh']['realDecor']:
        r=prop['rect']
        check(ev,plane['x']-2<=center(r)<=plane['right']+2 and plane['y']-2<=r['bottom']<=plane['bottom']+2,
              prop['id']+' rests on the physical countertop instead of the room wall',
              {'prop':prop,'counter_plane':plane},layout=True)


def calendar_geometry(ev, m, populated):
    cal=m['calendar'];days={r['day'] for r in cal['dates']}
    check(ev,m['page']=='monthly' and days=={'2026-11-'+str(n).zfill(2) for n in range(1,31)},
          'Records opens November with each real date exactly once')
    check(ev,cal['slots'] in (35,42),'The month has complete seven-day weeks',cal['slots'])
    target(ev,cal['budget'],'Visible actual monthly food spending')
    check(ev, ('128,000' in (cal['budgetText'] or '') and '300,000' in (cal['budgetText'] or '')) if populated
          else ('0' in (cal['budgetText'] or '') and '미설정' in (cal['budgetText'] or '')),
          'Calendar keeps actual spending/budget visible without fabricated defaults',cal['budgetText'])
    stamps={r['day']:r for r in cal['dates'] if r['recipe'] or r['image']}
    check(ev,set(stamps)==({DAY,'2026-11-06'} if populated else set()),
          'Only actual recorded meals receive diary pictures',stamps)
    for day in cal['dates']:
        target(ev,day['control'],day['day']+' calendar day',24)


def calendar_clicks(ev,page,frame,folder,label,original,populated):
    target_day='2026-11-06'if populated else'2026-11-07'
    frame.locator('#homeMonthly [data-home-day="'+target_day+'"]').click()
    m=capture(page,frame,folder,label+'-selected-diary')
    text=frame.locator('#homeMonthly').inner_text()
    check(ev,frame.evaluate('KitchenHome.getRecordDay()')==target_day,
          'An actual click changes the selected diary date rather than leaving the initial day')
    check(ev, 'QA 토마토 오믈렛' in text if populated else any(t in text for t in ['없','아직','추가']),
          'Selecting a date shows its real meal diary or an honest empty state',text)
    readonly(ev,frame,original,'Selecting a diary date does not create a food entry')
    back=frame.locator('#homeMonthly [data-record-month-view="calendar"]:visible')
    if back.count():back.first.click()
    frame.locator('#homeMonthly [data-home-date-shift="homeMonth"][data-step="1"]').click()
    old.ready(frame)
    dates=frame.locator('#homeMonthly [data-home-day]').evaluate_all('(nodes)=>nodes.map(e=>e.dataset.homeDay)')
    check(ev, len(dates)==31 and set(dates)=={'2026-12-'+str(i).zfill(2)for i in range(1,32)},
          'Actual month navigation renders every real December date')
    frame.locator('#homeMonthly [data-home-date-shift="homeMonth"][data-step="-1"]').click()
    old.ready(frame)
    if populated and label.startswith(('native-320x360-','opaque-390x480-')):
        picker=frame.locator('#homeMonthly #homeMonth');picker.fill('2026-08');picker.dispatch_event('change')
        august=capture(page,frame,folder,label+'-six-week-August');cal=august['calendar']
        check(ev,cal['slots']==42 and {d['day']for d in cal['dates']}==
              {'2026-08-'+str(i).zfill(2)for i in range(1,32)},
              'The small widget renders every real August day across six complete weeks')
        for day in cal['dates']:target(ev,day['control'],day['day']+' six-week date',24)
        target(ev,cal['budget'],'Six-week calendar actual-spending entry')
        frame.locator('#homeMonthly [data-home-day="2026-08-13"]').click();old.ready(frame)
        check(ev,any(t in frame.locator('#homeMonthly').inner_text()for t in ['없','아직','추가']),
              'A selected unrecorded day in a six-week month remains honestly empty')
        back=frame.locator('#homeMonthly [data-record-month-view="calendar"]:visible')
        if back.count():back.first.click()
        picker=frame.locator('#homeMonthly #homeMonth');picker.fill('2026-11');picker.dispatch_event('change');old.ready(frame)
        readonly(ev,frame,original,'Six-week navigation and selected-date browsing preserve all records')
    frame.locator('#homeMonthly .journal-budget-link').click()
    check(ev,frame.locator('body').get_attribute('data-home-page')=='budget',
          'The visible calendar expense strip opens actual expense management')
    text=frame.locator('#homeBudget').inner_text()
    check(ev, ('128,000'in text and '300,000'in text and '172,000'in text)if populated
          else ('미설정'in text and '0'in text),
          'Expense management retains the same recorded monthly numbers',text)
    readonly(ev,frame,original,'Diary, month and expense browsing preserve exact stored records')


def layout_case(browser,origin,kind,width,height,folder,contract=None,observe=False):
    label=kind+'-'+str(width)+'x'+str(height)
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
        'reference_checks_required':not observe,'observation_only':observe,'screens':{},'states':{}}
    context=page=None
    try:
        entry='miniature-kitchen-app.html' if kind=='app' else ENTRIES[kind]
        context,page,frame=old.open_page(browser,origin,entry,width,height,ev['page_errors'],ev['blocked_requests'])
        check(ev,frame.locator('body').get_attribute('data-mode')==('app'if kind=='app'else'widget'),
              'The delivered entry retains its actual app or embedded-widget mode',
              frame.locator('body').get_attribute('data-mode'))
        storage=old.state(frame)
        check(ev,storage['available']==(kind!='opaque') and storage['status']==('temporary'if kind=='opaque'else'saved'),
              'Native durable storage and opaque temporary preview are explicitly distinguished')
        if kind=='opaque':
            grants=(page.locator('iframe').get_attribute('sandbox')or'').split()
            check(ev,'allow-scripts'in grants and'allow-forms'in grants and'allow-same-origin'not in grants,
                  'The public wrapper retains the actual opaque sandbox boundary',grants)
        for state_name in ['empty','qa']:
            if state_name=='qa':
                before=old.state(frame)['envelope'];seeded=frame.evaluate(living.FIXTURE)
                check(ev,seeded['after']['world']==before['world'],'Explicit QA records leave stock and coordinates intact')
            original=old.state(frame);ev['states'][state_name]=original
            for name in ['fridge','meals','records','kitchen']:
                living.tab(frame,name)
                if name=='records':
                    # Previous acceptance clicks change the selected month/day.
                    # This public read-only navigation selects the same fixed
                    # day already present in every frozen before capture.
                    frame.evaluate('(day)=>KitchenHome.showRecords(day,"monthly")',DAY)
                m=capture(page,frame,folder,label+'-'+state_name+'-'+name)
                ev['screens'][state_name+'-'+name]=m
                if not observe:
                    shell_geometry(ev,m)
                    if name=='fridge':home_geometry(ev,m,contract,state_name=='qa')
                    elif name=='meals':recipe_geometry(ev,frame,m,state_name=='qa')
                    elif name=='records':
                        calendar_geometry(ev,m,state_name=='qa')
                        calendar_clicks(ev,page,frame,folder,label+'-'+state_name,original,state_name=='qa')
                    else:
                        check(ev,m['page']=='decor' and m['decor']['visible'],'My kitchen opens the real studio')
                        for action in m['decor']['actions']:target(ev,action,'Studio '+action['label'])
                        counter_geometry(ev,m,contract)
                readonly(ev,frame,original,state_name+' '+name+' browsing preserves exact existing records')
                if name=='meals' and not observe:
                    recipe_clicks(ev,frame,original,subset=True)
                if name=='kitchen':
                    frame.locator('[data-home-subtab="health"]:visible').click()
                    health=capture(page,frame,folder,label+'-'+state_name+'-health')
                    ev['screens'][state_name+'-health']=health
                    if not observe:
                        shell_geometry(ev,health);living.health_geometry(ev,health)
                        living.health_journey(ev,frame,original)
                    readonly(ev,frame,original,'Health reading never modifies records')
            living.tab(frame,'fridge')
        if kind=='opaque'and not observe:
            original=old.state(frame)
            frame.locator('#homeStorageNotice [data-wf="backupTools"]').click();old.ready(frame)
            check(ev,frame.locator('#tray[open] .backup-tools[open]').count()==1,
                  'The visible temporary-session control opens the actual backup tools')
            exported=json.loads(frame.locator('#tray #journalExport').input_value())
            check(ev,exported==original['envelope'],
                  'The backup textarea contains the exact current disposable envelope')
            readonly(ev,frame,original,'Opening temporary-session backup tools preserves all records')
            page.screenshot(path=str(folder/(label+'-temporary-backup.png')),animations='disabled')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No browser JavaScript error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'No provider or network write',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def registration_case(browser,origin,kind,folder):
    label='supplement-register-'+kind
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
        'fixture':'Explicit QA product text in the actual registration form, not a dosage recommendation'}
    context=page=None
    try:
        context,page,frame=old.open_page(browser,origin,ENTRIES[kind],390,480,ev['page_errors'],ev['blocked_requests'])
        before=old.state(frame)['envelope'];check(ev,not before['workflow']['supplements'],'No invented product is seeded')
        frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
        frame.locator('#homeSupplements [data-workflow="supplements"]').click()
        frame.locator('#tray .supplement-add>summary').click()
        form=frame.locator('#tray [data-wf-form="supplement"]')
        entered={'name':'QA 등록 제품','amount':'QA 제품 표시','remaining':'QA 남은 수량',
                 'schedule':'QA 직접 입력 일정','origin':'QA 제조 표시','ingredients':'QA 성분 메모'}
        for name,value in entered.items():form.locator('[name="'+name+'"]').fill(value)
        form.locator('[type="submit"]').click();old.ready(frame)
        after=old.state(frame)['envelope'];rows=after['workflow']['supplements']
        check(ev,len(rows)==1 and all(rows[0].get(k)==v for k,v in entered.items())and rows[0]['days']==[],
              'The form stores exact entered product fields without a false taken-today mark',rows)
        restored=copy.deepcopy(after);restored['workflow']['supplements']=[]
        check(ev,restored==before,'Registering a product changes no stock, meal, expense or previous field')
        old.close_tray(frame);living.tab(frame,'fridge')
        frame.locator('#homeSupplementsShelf [data-living-supplements]:visible').first.click()
        row=frame.locator('#homeSupplements [data-home-supplement="'+rows[0]['id']+'"]')
        check(ev,row.is_visible()and not row.is_checked(),'The registered product is reachable from the home row and still unchecked')
        check(ev,'QA 등록 제품'in frame.locator('#homeSupplements').inner_text(),'Management shows the full real product name')
        capture(page,frame,folder,label+'-saved')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No product registration browser error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'Product registration calls no provider',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def plan_expense_case(browser,origin,kind,folder):
    label='plan-and-purchase-'+kind
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
        'fixture':'Actual UI plan/shopping/purchase with explicit QA text and paid amount'}
    context=page=None
    try:
        context,page,frame=old.open_page(browser,origin,ENTRIES[kind],390,480,ev['page_errors'],ev['blocked_requests'])
        before=old.state(frame)['envelope'];living.tab(frame,'meals')
        frame.locator('#homeRecommendation [data-home-recipe="recipe-1"]').click()
        frame.locator('#tray [data-wf="planRecipe"]').click();form=frame.locator('#tray [data-wf-form="plan"]')
        form.locator('[name="day"]').fill(DAY);form.locator('[name="slot"][value="dinner"]').check()
        old.reveal(form.locator('[name="recipeId"]')).select_option('recipe-1');form.locator('[name="portions"]').fill('2')
        check(ev,old.state(frame)['envelope']==before,'Reviewing a future plan consumes no food')
        form.locator('[type="submit"]').click();old.ready(frame);planned=old.state(frame)['envelope']
        check(ev,len(planned['workflow']['plans'])==1 and planned['workflow']['plans'][0]['recipeId']=='recipe-1'
              and planned['workflow']['plans'][0]['day']==DAY and planned['workflow']['plans'][0]['slot']=='dinner'
              and planned['workflow']['plans'][0]['portions']==2,
              'Actual plan Save stores the selected recipe, day, meal slot and portions',planned['workflow']['plans'])
        check(ev,planned['world']==before['world']and planned['play']==before['play']
              and planned['workflow']['expenses']==before['workflow']['expenses'],
              'Saving a plan changes neither eaten nutrition, stock nor actual expenses')
        old.close_tray(frame);living.tab(frame,'records','budget')
        frame.locator('#homeBudget [data-workflow="budget"]').click()
        form=frame.locator('#tray [data-wf-form="budget"]');old.reveal(form.locator('[name="budget"]')).fill('300000')
        form.locator('[type="submit"]').click();old.ready(frame)
        frame.locator('#tray [data-wf="shopping"]').click();form=frame.locator('#tray [data-wf-form="shopping"]')
        for key,value in {'name':'QA 구매 재료','quantity':'1개','estimate':'2500'}.items():
            old.reveal(form.locator('[name="'+key+'"]')).fill(value)
        form.locator('[type="submit"]').click();old.ready(frame);shopping=old.state(frame)['envelope']
        check(ev,shopping['world']==planned['world']and shopping['workflow']['expenses']==planned['workflow']['expenses'],
              'Shopping estimate is not stock intake or actual expenditure')
        row=shopping['workflow']['shopping'][-1];frame.locator('#tray [data-shopping-check="'+row['id']+'"]').check()
        frame.locator('#tray [data-wf="purchaseReview"]').click();form=frame.locator('#tray [data-wf-form="purchaseBatch"]')
        form.locator('[name="day"]').fill(DAY);form.locator('[name="paid"]').fill('2000')
        form.locator('[name="quantity0"]').fill('1개');form.locator('[name="paid0"]').fill('2000')
        before_save=old.state(frame)['envelope'];check(ev,not before_save['workflow']['expenses'],
              'Purchase review does not record estimated money before Save')
        form.locator('[type="submit"]').click();old.ready(frame);paid=old.state(frame)['envelope']
        expenses=paid['workflow']['expenses'];check(ev,len(expenses)==1 and expenses[0]['amount']==2000
              and expenses[0]['day']==DAY and len(expenses[0]['receipt']['items'])==1,
              'Actual purchase stores the paid2000 rather than estimated2500 exactly once',expenses)
        check(ev,paid['world']==planned['world']and paid['play']==planned['play']
              and paid['workflow']['plans']==planned['workflow']['plans'],
              'Expense Save does not silently receive inventory or change meals/plans')
        frame.locator('#homeBudget [data-record-budget-view="summary"]').click()
        text=frame.locator('#homeBudget').inner_text();check(ev,'2,000'in text and '298,000'in text,
              'Real home budget updates to the paid amount and remaining budget',text)
        capture(page,frame,folder,label+'-expense-saved')
        frame.locator('#homeBudget [data-workflow="budget"]').click()
        frame.locator('#tray [data-wf="receipt"]').click();frame.locator('#tray [data-wf="purchaseRegister"]').click()
        check(ev,frame.locator('#tray').get_attribute('data-workflow-route')=='photos'
              and frame.locator('#tray [data-photo="product"]').count()==1
              and frame.locator('#tray [data-photo="expiry"]').count()==1,
              'Stock intake remains a separate two-photo review from the saved receipt')
        check(ev,old.state(frame)['envelope']==paid,'Opening receipt intake leaves paid expense and stock unchanged')
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No plan/purchase browser error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'Plan/purchase calls no provider',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def scene_case(browser,origin,kind,folder,contract,width=720,height=800):
    label='doors-drag-empty-stock-'+kind+'-'+str(width)+'x'+str(height)
    ev={'id':label,'checks':[],'page_errors':[],'blocked_requests':[],'reference_checks_required':True,
        'fixture':'Actual door/drag controls, followed by explicit disposable stock-empty rendering fixture'}
    context=page=None
    try:
        context,page,frame=old.open_page(browser,origin,ENTRIES[kind],width,height,ev['page_errors'],ev['blocked_requests'])
        original=old.state(frame);expected=copy.deepcopy(original['envelope']['world']['doors'])
        capture(page,frame,folder,label+'-populated-scene')
        for key in closed.DOORS:
            click_door(frame,key);expected[key]=not expected[key]
            closed.preservation(ev,frame,expected,original,'Toggling '+key)
        saved=old.state(frame);capture(page,frame,folder,label+'-all-closed')
        if kind=='native':
            page.reload();frame=closed.load_frame(page,kind)
            check(ev,old.state(frame)==saved,'Actual native reload preserves the exact closed world and raw text')
        for key in closed.DOORS:
            if not old.state(frame)['envelope']['world']['doors'][key]:click_door(frame,key)
        before_drag=old.state(frame)['envelope'];item=next(i for i in before_drag['world']['items']if i['id']=='milk')
        destination='freshLeft'if item['zone']!='freshLeft'else'freshRight'
        drag(page,frame.locator('#fridgeSceneHost [data-item="milk"]'),frame.locator('[data-zone="'+destination+'"]'),kind=='opaque')
        old.ready(frame);after_drag=old.state(frame)['envelope'];moved=next(i for i in after_drag['world']['items']if i['id']=='milk')
        check(ev,moved['zone']==destination,'Actual pointer drag moves the real milk into the chosen compartment',moved)
        expected_world=copy.deepcopy(before_drag['world']);expected_item=next(i for i in expected_world['items']if i['id']=='milk')
        for key in ['zone','x','y','z']:expected_item[key]=moved[key]
        expected_world['layer']=after_drag['world']['layer']
        check(ev,after_drag['world']==expected_world and after_drag['play']==before_drag['play']
              and after_drag['workflow']==before_drag['workflow'],
              'Dragging changes only milk placement/layer; quantities, expiry, other positions and records are exact')
        old.registration_journey(old.Audit(ev),page,frame,folder,label,old.state(frame),{})
        frame.evaluate('''()=>{const e=KitchenJournal.getEnvelope();e.world.items=e.world.items.filter(i=>!['food','seasoning'].includes(i.kind));
          e.world.items.filter(i=>i.kind==='meal').forEach(i=>i.depleted=true);KitchenJournal.replaceEnvelope(e)}''')
        empty=old.state(frame);living.tab(frame,'fridge');m=capture(page,frame,folder,label+'-NO-FOOD-MANUAL-REVIEW')
        ev['empty_stock_metrics']=m
        check(ev,not [i for i in empty['envelope']['world']['items']if i['kind']in ['food','seasoning']]
              and all(i.get('depleted')for i in empty['envelope']['world']['items']if i['kind']=='meal'),
              'Explicit stock-empty QA preserves the mandatory meal sentinel but contains no live food or seasoning')
        check(ev,not m['refresh']['food'],
              'The rendered scene contains no stale food DOM after stock removal',m['refresh']['food'])
        home_geometry(ev,m,contract,False);readonly(ev,frame,empty,'Rendering empty inventory never invents or restores food records')
        page.reload();frame=closed.load_frame(page,kind);reloaded=old.state(frame)
        if kind=='native':
            check(ev,reloaded==empty,'Reloading an intentionally empty saved fridge does not reseed example food')
        else:
            check(ev,not reloaded['available']and reloaded['status']=='temporary'and reloaded['raw']is None,
                  'Opaque reload remains explicitly temporary rather than falsely claiming durable stock edits')
        ev['manual_review_required']='Compare populated/allclosed/NO-FOOD PNGs; DOM checks alone cannot recognise baked food artwork.'
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/(label+'-failure.png')),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No scene browser error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'Scene changes call no provider',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def legacy_case(browser,origin,folder):
    fixture=REPO/'tests/fixtures/miniature-legacy-world-v1.json';world=json.loads(fixture.read_text())
    play={'version':1,'meals':[],'targets':{k:None for k in ['kcal','carb','protein','fat','fiber','water']},
          'discovered':[],'awarded':[],'owned':[],'equipped':{'frozenLeft':None,'frozenRight':None},
          'goal':'collection','plateLabel':'우리 집 부엌'}
    play['targets'].update(carb=241,protein=83,fat=67)
    play['meals'].append({'id':'qa-existing-legacy-meal','day':DAY,'name':'QA 보존한 직접 식사',
                         'portion':'QA 저장된 분량','recipeId':None,'source':'manual',
                         'nutrients':{'kcal':371,'carb':37,'protein':19,'fat':11,'fiber':None,'water':None}})
    raw=json.dumps({'version':1,'world':world,'play':play},ensure_ascii=False,indent=2)
    ev={'id':'legacy-v1-exact-native','checks':[],'page_errors':[],'blocked_requests':[],
        'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
        'raw_sha256':hashlib.sha256(raw.encode()).hexdigest()};context=page=None
    try:
        context,page,frame=old.open_page(browser,origin,ENTRIES['native'],390,480,ev['page_errors'],ev['blocked_requests'],raw)
        original=old.state(frame);check(ev,original['raw']==raw and original['envelope']['world']==world
              and original['envelope']['play']==play,'Tracked pre-workflow v1 text, positions and records load without rewriting')
        for name in ['fridge','meals','records','kitchen']:
            living.tab(frame,name);readonly(ev,frame,original,'Existing v1 survives '+name+' navigation')
        living.tab(frame,'meals');frame.locator('#homeRecommendation [data-home-recipe]').first.click()
        readonly(ev,frame,original,'Existing v1 survives actual read-only recipe detail')
        page.reload();frame=closed.load_frame(page,'native');readonly(ev,frame,original,'Actual reload preserves exact existing v1 raw text')
        m=capture(page,frame,folder,'legacy-v1-reloaded');nutrition_view(ev,m['refresh'])
        expected_ids={i['id']for i in world['items']if i['kind']in ['food','seasoning']and not i.get('depleted')}
        check(ev,{i['id']for i in m['refresh']['food']}==expected_ids,
              'Old seasoning zones and stock remain visible through display projection without rewriting their saved coordinates',
              {'expected':sorted(expected_ids),'visible':[i['id']for i in m['refresh']['food']]})
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback']=traceback.format_exc()
        if page:page.screenshot(path=str(folder/'legacy-v1-failure.png'),animations='disabled')
    finally:
        check(ev,not ev['page_errors'],'No legacy browser error',ev['page_errors'])
        check(ev,not ev['blocked_requests'],'Legacy viewing calls no provider',ev['blocked_requests'])
        if context:context.close()
    return old.finish_case(ev)


def inputs(root):
    return {p:{'bytes':(root/p).stat().st_size,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()}
            for p in DELIVERIES}


def delivered_modes(browser,origin):
    """Check the actual decoded DOM of all four delivered entries."""
    results=[]
    for entry in DELIVERIES:
        errors=[];blocked=[];context=None
        try:
            context,page,frame=old.open_page(browser,origin,entry,390,480,errors,blocked)
            mode=frame.locator('body').get_attribute('data-mode')
            expected='widget'if 'widget'in entry else'app'
            results.append({'entry':entry,'expected':expected,'actual':mode,'page_errors':errors,
                            'blocked_requests':blocked,'passed':mode==expected and not errors and not blocked})
        except Exception as error:
            results.append({'entry':entry,'passed':False,'error':str(error)})
        finally:
            if context:context.close()
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser-executable',default='/usr/bin/chromium')
    parser.add_argument('--scene-contract',type=Path);parser.add_argument('--observe-only',action='store_true')
    parser.add_argument('--baseline-evidence',type=Path)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    if out.is_relative_to(REPO) or out.is_relative_to(root) or root.is_relative_to(out):
        parser.error('Evidence must be outside the checkout and frozen input.')
    if not args.observe_only and not args.scene_contract:
        parser.error('Final acceptance requires the reviewed native scene registration JSON.')
    contract=json.loads(args.scene_contract.read_text())if args.scene_contract else None
    out.mkdir(parents=True,exist_ok=False);screens=out/'screens';screens.mkdir();before=inputs(root)
    shutil.copy2(Path(__file__),out/'executed-test-source.py')
    source_files=['test_kitchen_refresh_browser.py','test_kitchen_living_browser.py',
                  'test_kitchen_widget_browser.py','test_kitchen_closed_browser.py','test_fridge_four_door_browser.py']
    source_hashes={p:hashlib.sha256((REPO/'scripts'/p).read_bytes()).hexdigest()for p in source_files}
    report={'scope':'Local disposable Chromium; actual frozen preview HTML; no personal/production storage',
            'clock':old.CLOCK.isoformat(),'inputs':before,'observation_only':args.observe_only,
            'verification_sources':source_hashes,
            'delivery_under_1MiB':all(x['bytes']<=1048576 for x in before.values()),
            'scene_contract':contract,'cases':[],'passed':False,
            'manual_review':'Actual PNG and stock-empty scene must be visually reviewed; geometry is not design approval'}
    server,origin=closed.serve(root)
    def save(row=None):
        if row:
            report['cases'].append(row)
            print(json.dumps({'id':row['id'],'passed':row['passed'],
                              'failed':[c['name']for c in row['checks']if not c['passed']]},ensure_ascii=False),flush=True)
        report['inputs_unchanged']=inputs(root)==before
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright()as p:
            browser=p.chromium.launch(executable_path=args.browser_executable,args=['--no-sandbox'])
            report['delivered_modes']=delivered_modes(browser,origin)
            for kind in ENTRIES:
                for width,height in PROFILES:save(layout_case(browser,origin,kind,width,height,screens,contract,args.observe_only))
            for width,height in APP_PROFILES:save(layout_case(browser,origin,'app',width,height,screens,contract,args.observe_only))
            if not args.observe_only:
                for kind in ENTRIES:
                    save(living.supplement_case(browser,origin,kind,390,480,screens))
                    save(registration_case(browser,origin,kind,screens))
                    save(living.decor_case(browser,origin,kind,390,480,screens))
                    width,height=(320,360)if kind=='native'else(390,480)
                    save(living.meal_success_case(browser,origin,kind,width,height,screens))
                    save(plan_expense_case(browser,origin,kind,screens))
                    for width,height in ((320,360),(720,800)):
                        save(scene_case(browser,origin,kind,screens,contract,width,height))
                save(legacy_case(browser,origin,screens))
            browser.close()
    finally:server.shutdown()
    report['expected_cases']=10 if args.observe_only else 25
    report['complete']=len(report['cases'])==report['expected_cases']
    report['assertions']=sum(len(c['checks'])for c in report['cases'])+len(report['delivered_modes'])
    if args.baseline_evidence:
        b=json.loads((args.baseline_evidence/'results.json').read_text())
        comparison=[]
        for c in report['cases']:
            if 'states'not in c:continue
            prior=next(x for x in b['cases']if x['id']==c['id'])
            def same_state(phase):
                return phase in c['states'] and c['states'][phase]==prior['states'][phase]
            def same_day(phase):
                key=phase+'-records'
                return key in c['screens'] and [d['day']for d in c['screens'][key]['calendar']['dates']if d['selected']]==[
                    d['day']for d in prior['screens'][key]['calendar']['dates']if d['selected']]
            comparison.append({'id':c['id'],'empty':same_state('empty'),'qa':same_state('qa'),
                               'empty_calendar_day':same_day('empty'),'qa_calendar_day':same_day('qa')})
        report['baseline_comparison']=comparison
        report['baseline_states_equal']=len(comparison)==10 and all(all(v for k,v in x.items()if k!='id')for x in comparison)
    report['verification_sources_unchanged']=source_hashes=={
        p:hashlib.sha256((REPO/'scripts'/p).read_bytes()).hexdigest()for p in source_files}
    report['passed']=report['complete']and report['inputs_unchanged']and report['delivery_under_1MiB']and all(c['passed']for c in report['cases'])
    report['passed']=report['passed']and len(report['delivered_modes'])==4 and all(c['passed']for c in report['delivered_modes'])
    report['passed']=report['passed']and report['verification_sources_unchanged']
    if args.baseline_evidence:report['passed']=report['passed']and report['baseline_states_equal']
    save();print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'assertions':report['assertions']},ensure_ascii=False))
    raise SystemExit(0 if report['passed']else 1)


if __name__=='__main__':main()
