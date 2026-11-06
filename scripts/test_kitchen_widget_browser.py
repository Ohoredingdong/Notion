#!/usr/bin/env python3
"""Exercise compact generated kitchen widgets in real, short embed viewports.

Use --root for an already-generated previews directory (native HTML plus
mobile/widget.html), not the source template. Evidence is always external.
This reads actual starter data and navigates actual controls. The one explicitly
labelled legacy-storage fixture comes from the existing tracked v1 fixture.
Broader meal/plan transactions remain in test_kitchen_complete_flow_browser.py.
An isolated, explicitly labelled form-driven B6 regression additionally saves,
undoes and resaves one QA meal. No context invokes OCR or external providers.
"""
import argparse
import base64
import functools
import hashlib
import json
import shutil
import threading
import traceback
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


REPO = Path(__file__).resolve().parents[1]
KEY = 'miniature-kitchen-preview-v1'
CLOCK = datetime.fromisoformat('2026-11-05T03:00:00+00:00')
PROFILES = ((320, 360), (390, 480), (720, 500), (800, 600), (390, 844),
            (561, 800), (562, 800))
TABS = ('fridge', 'meals', 'records', 'kitchen')
ENTRIES = {'native': 'miniature-kitchen-widget.html', 'opaque': 'mobile/widget.html'}
B6_PROFILES = ((320, 360), (320, 568), (390, 480))
QA_STOCK = {'계란': '6개', '양파': '2개', '식용유': '10작은술', '간장': '10작은술', '밥': '10공기'}
QA_FACTS = {'kcal': '78', 'carb': '10', 'protein': '5', 'fat': '2', 'cost': '1000'}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def digest(value):
    return hashlib.sha256(value).hexdigest()


def ready(frame):
    frame.evaluate('''async()=>{
      await document.fonts.ready;
      await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));
      const sources=[...new Set([...document.querySelectorAll('svg image')]
        .map(e=>e.getAttribute('href')).filter(Boolean))];
      await Promise.all(sources.map(src=>{const image=new Image();image.src=src;
        return image.decode().catch(()=>{})}));
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
    }''')


def state(frame):
    return frame.evaluate('''()=>{
      let raw=null,available=true;try{raw=localStorage.getItem(KitchenJournal.storageKey)}
      catch(_){available=false}
      return {key:KitchenJournal.storageKey,raw,available,
        status:KitchenJournal.status,envelope:KitchenJournal.getEnvelope()};
    }''')


PAINT_HELPERS = '''
  const boxOf=e=>{if(!e||!e.getClientRects().length)return null;
    const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,
      right:r.right,bottom:r.bottom}};
  const overlap=(...rs)=>{if(rs.some(r=>!r))return null;
    const x=Math.max(...rs.map(r=>r.x)),y=Math.max(...rs.map(r=>r.y));
    const right=Math.min(...rs.map(r=>r.right)),bottom=Math.min(...rs.map(r=>r.bottom));
    return {x,y,right,bottom,width:Math.max(0,right-x),height:Math.max(0,bottom-y)}};
  const paintedPhoto=async container=>{
    const svg=container?.querySelector('svg.recipe-photo[data-recipe-photo]');
    const frame=boxOf(container),box=boxOf(svg);
    if(!frame||!box||frame.width<=0||frame.height<=0||box.width<=0||box.height<=0)return null;
    const vb=svg.viewBox.baseVal,m=svg.getScreenCTM();if(!m)return null;
    const points=[[vb.x,vb.y],[vb.x+vb.width,vb.y],[vb.x,vb.y+vb.height],
      [vb.x+vb.width,vb.y+vb.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
    const x=Math.min(...points.map(p=>p.x)),y=Math.min(...points.map(p=>p.y));
    const right=Math.max(...points.map(p=>p.x)),bottom=Math.max(...points.map(p=>p.y));
    const projected={x,y,right,bottom,width:right-x,height:bottom-y};
    const visible=overlap(projected,box,frame),sx=Math.hypot(m.a,m.b),sy=Math.hypot(m.c,m.d);
    if(!sx||!sy)return null;
    const image=svg.querySelector('image[href]'),clip=svg.querySelector('clipPath rect');
    const atlas={decoded:false};
    if(image){try{const probe=new Image();probe.src=image.getAttribute('href');await probe.decode();
      atlas.decoded=true;atlas.naturalWidth=probe.naturalWidth;atlas.naturalHeight=probe.naturalHeight;
      atlas.width=image.width.baseVal.value;atlas.height=image.height.baseVal.value;
      atlas.x=image.x.baseVal.value;atlas.y=image.y.baseVal.value;
    }catch(_){atlas.error='Actual recipe atlas failed to decode'}}
    return {frame,svg:box,projected,visible,recipe:svg.dataset.recipePhoto,
      viewBox:{x:vb.x,y:vb.y,width:vb.width,height:vb.height},
      atlas,clip:clip?{x:clip.x.baseVal.value,y:clip.y.baseVal.value,
        width:clip.width.baseVal.value,height:clip.height.baseVal.value}:null,
      scale:{x:sx,y:sy,shear:(m.a*m.c+m.b*m.d)/(sx*sy)},
      blankFraction:1-visible.width*visible.height/(frame.width*frame.height)};
  };
  const textRanges=root=>{
    if(!root||!boxOf(root))return [];
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),rows=[];
    for(let node;node=walker.nextNode();){const text=node.textContent.trim(),element=node.parentElement;
      if(!text||!element||element.closest('.sr-only,[hidden],[aria-hidden="true"]')||!boxOf(element))continue;
      // Icon glyph line boxes may intentionally exceed their painted arrow;
      // accessible button hit targets are checked separately from recipe data.
      if(element.closest('button[aria-label]')&&/^[›‹×↶←→]+$/.test(text))continue;
      const range=document.createRange();range.selectNodeContents(node);
      for(const r of range.getClientRects()){
        if(!r.width||!r.height)continue;
        let readable=r.left>=-1&&r.right<=innerWidth+1&&r.top>=-1&&r.bottom<=innerHeight+1;
        for(let ancestor=element;ancestor;ancestor=ancestor.parentElement){
          const css=getComputedStyle(ancestor),b=ancestor.getBoundingClientRect();
          if(css.visibility==='hidden'||Number(css.opacity)===0)readable=false;
          if(/hidden|clip|auto|scroll/.test(css.overflowX)&&
            (r.left<b.left-1||r.right>b.right+1))readable=false;
          if(/hidden|clip|auto|scroll/.test(css.overflowY)&&
            (r.top<b.top-1||r.bottom>b.bottom+1))readable=false;
        }
        rows.push({text:text.slice(0,100),x:r.x,y:r.y,width:r.width,height:r.height,readable});
      }
    }return rows;
  };
'''


METRICS = '''async()=>{''' + PAINT_HELPERS + '''
  const rect=e=>{if(!e||!e.getClientRects().length)return null;
    const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,
      height:r.height,right:r.right,bottom:r.bottom}};
  const one=s=>rect(document.querySelector(s));
  const control=e=>{const r=rect(e);if(!r)return {label:e?.id,rect:null};
    const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
    return {label:e.getAttribute('aria-label')||e.textContent.trim(),rect:r,
      selected:e.getAttribute('aria-selected'),tabIndex:e.tabIndex,
      centerHit:hit===e||e.contains(hit),fontSize:parseFloat(getComputedStyle(e).fontSize)}};
  const panel=[...document.querySelectorAll('.home-panel')].find(e=>!e.hidden);
  const photo=document.querySelector('#fridgeSceneHost .original-kitchen-photo');
  const world=document.querySelector('#fridgeSceneHost .scene-world');
  const matrix=world?new DOMMatrix(getComputedStyle(world).transform):null;
  return {viewport:{width:innerWidth,height:innerHeight},
    document:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight},
    shell:one('.shell'),header:one('.shell>.masthead'),nav:one('.home-shortcuts'),
    headerPosition:getComputedStyle(document.querySelector('.masthead')).position,
    navCount:[...document.querySelectorAll('.home-shortcuts')].filter(e=>e.getClientRects().length).length,
    visibleMainTabs:[...document.querySelectorAll('[data-home-tab]')].filter(e=>e.getClientRects().length).length,
    panel:panel?{id:panel.id,rect:rect(panel),width:panel.clientWidth,height:panel.clientHeight,
      scrollWidth:panel.scrollWidth,scrollHeight:panel.scrollHeight}:null,
    tabs:[...document.querySelectorAll('.home-shortcuts [data-home-tab]')].map(control),
    add:control(document.querySelector('#addFood')),
    scene:{host:one('#fridgeSceneHost'),photo:rect(photo),world:rect(world),
      canvas:rect(panel),
      stage:one('#fridgeSceneHost .fridge-stage'),
      natural:photo?{width:photo.naturalWidth,height:photo.naturalHeight,complete:photo.complete}:null,
      matrix:matrix?{a:matrix.a,b:matrix.b,c:matrix.c,d:matrix.d}:null},
    balance:[...document.querySelectorAll('#dailyBalance [data-balance]')].map(e=>({
      key:e.dataset.balance,rect:rect(e),text:e.textContent.trim()})),
    recipe:{grid:one('#homeRecommendation .recipe-hub-grid'),
      gridColumns:document.querySelector('#homeRecommendation .recipe-hub-grid')?
        getComputedStyle(document.querySelector('#homeRecommendation .recipe-hub-grid'))
          .gridTemplateColumns.split(/\\s+/).filter(Boolean).length:0,
      filters:window.KitchenHome?.getRecipeFilters?.(),
      catalog:(window.KitchenCatalog||[]).map(r=>({id:r.id,name:r.name,time:r.time})),
      cards:await Promise.all([...document.querySelectorAll('#homeRecommendation .recipe-grid-card')]
        .map(async e=>({id:e.dataset.homeRecipe,rect:rect(e),
          title:e.querySelector('.recipe-grid-copy strong')?.textContent.trim(),
          time:e.querySelector('.recipe-grid-copy small')?.textContent.trim(),
          open:control(e.matches('button[data-wf="recipe"]')?e:e.querySelector('button[data-wf="recipe"]')),
          photo:await paintedPhoto(e.querySelector('.recipe-grid-photo')),
          copy:rect(e.querySelector('.recipe-grid-copy')),text:textRanges(e.querySelector('.recipe-grid-copy'))}))),
      singleRecipePager:[...document.querySelectorAll('#homeRecommendation [data-recipe-hub-nav]')]
        .filter(e=>e.getClientRects().length).length},
    home:document.body.dataset.home};
}'''


DETAIL = '''async()=>{''' + PAINT_HELPERS + '''
  const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,
    width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
  const pane=document.querySelector('#tray .recipe-ingredients-section'),bounds=rect(pane);
  const tray=rect(document.querySelector('#tray'));
  const rows=[...pane.querySelectorAll('.recipe-ingredient-list>div')].map(e=>{
    const r=rect(e);return {text:e.innerText,rect:r,
      readable:r.y>=Math.max(bounds.y,tray.y,0)-1&&r.bottom<=Math.min(bounds.bottom,tray.bottom,innerHeight)+1
        &&r.x>=Math.max(bounds.x,0)-1&&r.right<=Math.min(bounds.right,innerWidth)+1}});
  const actions=[...document.querySelectorAll('#tray .recipe-detail-actions>button')].map(e=>{
    const r=rect(e),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
    return {text:e.textContent.trim(),rect:r,centerHit:hit===e||e.contains(hit)}});
  return {viewport:{width:innerWidth,height:innerHeight},tray,
    pane:bounds,scrollHeight:pane.scrollHeight,scrollTop:pane.scrollTop,scrollY,rows,actions,
    photo:await paintedPhoto(document.querySelector('#tray .recipe-hero')),
    text:textRanges(document.querySelector('#tray .recipe-detail-overview')),
    documentWidth:document.documentElement.scrollWidth};
}'''


SUCCESS = '''()=>{
  const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,
    height:r.height,right:r.right,bottom:r.bottom}};
  const content=document.querySelector('#trayContent'),tray=document.querySelector('#tray');
  return {viewport:{width:innerWidth,height:innerHeight},tray:rect(tray),
    content:{rect:rect(content),height:content.clientHeight,scrollHeight:content.scrollHeight,
      scrollTop:content.scrollTop},document:{width:document.documentElement.scrollWidth,
      height:document.documentElement.scrollHeight,scrollY},
    deductions:[...document.querySelectorAll('.success-deduction-row')].map(e=>e.dataset.usedItem),
    actions:[...document.querySelectorAll('.success-main-actions>button')].map(e=>{
      const r=rect(e),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
      return {text:e.textContent.trim(),workflow:e.dataset.wf,rect:r,centerHit:hit===e||e.contains(hit)}})};
}'''


REGISTRATION = '''()=>{
  const rect=e=>{if(!e||!e.getClientRects().length)return null;
    const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,
      right:r.right,bottom:r.bottom}};
  const tray=document.querySelector('#tray'),content=document.querySelector('#trayContent');
  const control=e=>{const r=rect(e);if(!r)return {rect:null};
    const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
    const clip={x:0,y:0,right:innerWidth,bottom:innerHeight};
    for(let parent=e.parentElement;parent;parent=parent.parentElement){
      const css=getComputedStyle(parent),b=parent.getBoundingClientRect();
      if(/hidden|clip|auto|scroll/.test(css.overflowX)){
        clip.x=Math.max(clip.x,b.left);clip.right=Math.min(clip.right,b.right)}
      if(/hidden|clip|auto|scroll/.test(css.overflowY)){
        clip.y=Math.max(clip.y,b.top);clip.bottom=Math.min(clip.bottom,b.bottom)}
    }
    return {text:e.textContent.replace(/\\s+/g,' ').trim(),workflow:e.dataset.wf,
      title:e.querySelector('strong')?.textContent.trim(),rect:r,clip,
      disabled:!!e.disabled,centerHit:hit===e||e.contains(hit)};
  };
  const methods=[...document.querySelectorAll('#tray .registration-method')].map(control);
  const actions=[...document.querySelectorAll('#tray .photo-read-actions>button,'+
    '#tray .registration-secondary [data-wf="manualNoPhoto"]')].map(control);
  const fields=[...document.querySelectorAll('#addIngredientForm .registration-primary [name]')]
    .map(e=>({...control(e),name:e.name}));
  return {route:tray.dataset.workflowRoute,viewport:{width:innerWidth,height:innerHeight},
    tray:rect(tray),content:{rect:rect(content),scrollTop:content.scrollTop},
    methods,actions,photoSlots:[...document.querySelectorAll('#tray .photo-slot')].map(e=>({
      axis:e.querySelector('[data-photo]')?.dataset.photo,
      label:e.querySelector('.photo-slot-title')?.textContent.trim(),
      control:control(e.querySelector('.photo-slot-media'))})),
    save:control(document.querySelector('#addIngredientForm [type="submit"]')),fields};
}'''


class Audit:
    def __init__(self, evidence):
        self.evidence = evidence

    def check(self, value, message, detail=None, category='functional'):
        row = {'passed': bool(value), 'name': message, 'category': category}
        if detail is not None:
            row['detail'] = detail
        self.evidence.setdefault('checks', []).append(row)

    def caught(self, error):
        self.check(False, 'Browser journey completes', str(error))


def finish_case(evidence):
    checks = evidence['checks']
    reference = [c for c in checks if c['category'] == 'reference-composition']
    if evidence.get('reference_checks_required') and not reference:
        Audit(evidence).check(False, 'Reference composition checks actually ran', category='reference-composition')
        reference = [checks[-1]]
    evidence['functional_passed'] = all(c['passed'] for c in checks if c['category'] == 'functional')
    evidence['reference_composition_check_count'] = len(reference)
    evidence['reference_composition_checks_passed'] = all(c['passed'] for c in reference) if reference else None
    evidence['passed'] = all(c['passed'] for c in checks)
    return evidence


def breakpoint_continuity(cases, kind):
    pair = [next(c for c in cases if c['id'] == f'{kind}-{width}x800') for width in (561, 562)]
    frames = [c['screens'].get('fridge') for c in pair]
    audit = Audit(pair[1])
    stages = [m['scene']['stage'] if m else None for m in frames]
    ratio = stages[1]['width']/stages[0]['width'] if all(stages) and stages[0]['width'] > 0 else None
    audit.check(ratio is not None and .97 <= ratio <= 1.03,
                'A one-pixel host change at561/562 does not abruptly shrink the fridge projection',
                {'stage_widths': [s['width'] if s else None for s in stages], 'ratio': ratio},
                category='reference-composition')
    fonts = [[t.get('fontSize') for t in m['tabs']] if m else [] for m in frames]
    audit.check(len(fonts[0]) == len(fonts[1]) == 4
                and all(abs(a-b) <= 1 for a, b in zip(*fonts)),
                'UI text sizing is independent of the fridge breakpoint projection', fonts,
                category='reference-composition')
    finish_case(pair[1])


def inside(inner, outer, tolerance=1):
    return bool(inner and outer and inner['x'] >= outer['x']-tolerance
                and inner['y'] >= outer['y']-tolerance
                and inner['right'] <= outer['right']+tolerance
                and inner['bottom'] <= outer['bottom']+tolerance)


def viewport_box(width, height):
    return {'x': 0, 'y': 0, 'right': width, 'bottom': height}


def primary(audit, control, width, height, label):
    r = control.get('rect')
    audit.check(bool(r and r['width'] >= 43.5 and r['height'] >= 43.5
                     and inside(r, viewport_box(width, height)) and control['centerHit']),
                label+' is >=44px and has an unobscured viewport hit target', control)


def main_geometry(audit, metrics, width, height, reference):
    shell, header, nav, panel = (metrics[k] for k in ('shell', 'header', 'nav', 'panel'))
    audit.check(bool(shell and shell['width'] > 0 and shell['height'] > 0
                     and inside(shell, viewport_box(width, height))),
                'Natural widget canvas fits available host space without overflow', shell)
    audit.check(bool(nav and shell and metrics['navCount'] == 1
                     and metrics['visibleMainTabs'] == 4 and abs(nav['bottom']-shell['bottom']) <= 2),
                'Reference main navigation appears once at the bottom of the canvas',
                {'nav': nav, 'shell': shell, 'count': metrics['navCount']}, category='reference-composition')
    if metrics['home'] == 'fridge':
        audit.check(bool(header and panel and inside(header, panel['rect'])
                         and metrics['headerPosition'] == 'absolute'),
                    'Fridge branding overlays the photograph rather than reserving a chrome row',
                    {'header': header, 'position': metrics['headerPosition']}, category='reference-composition')
    else:
        audit.check(header is None and bool(panel and abs(panel['rect']['y']-shell['y']) <= 2),
                    'Non-fridge tabs start with their own content, without an extra brand header',
                    {'header': header, 'panel': panel}, category='reference-composition')
    audit.check([c['label'] for c in metrics['tabs']] == ['냉장고', '레시피', '기록', '내 부엌']
                and sum(c.get('selected') == 'true' for c in metrics['tabs']) == 1
                and sum(c.get('tabIndex') == 0 for c in metrics['tabs']) == 1,
                'The four named navigation tabs retain one selected keyboard entry')
    frame_width, frame_height = metrics['viewport']['width'], metrics['viewport']['height']
    audit.check(inside(shell, viewport_box(frame_width, frame_height)),
                'Widget fits the actual native or bounded iframe viewport', shell)
    audit.check(metrics['document']['width'] <= frame_width+1
                and metrics['document']['height'] <= frame_height+1,
                'Document has no horizontal or vertical overflow', metrics['document'])
    audit.check(bool(panel and panel['scrollWidth'] <= panel['width']+1
                     and panel['scrollHeight'] <= panel['height']+1
                     and inside(panel['rect'], shell)),
                'Main panel fits its own frame without a page-sized scroll', panel)
    if reference:
        audit.check(all(abs(shell[k]-reference[k]) <= 1 for k in ('x', 'y', 'width', 'height')),
                    'All four main tabs retain the same outer frame', shell)
    for control in metrics['tabs']:
        primary(audit, control, frame_width, frame_height, control['label'])


def scene_geometry(audit, scene, width, height, balance):
    photo, world, stage, host = (scene[k] for k in ('photo', 'world', 'stage', 'host'))
    natural, matrix = scene['natural'], scene['matrix']
    audit.check(bool(natural and natural['complete']
                     and natural['width'] == natural['height'] == 1254),
                'The actual cozy kitchen photograph decodes at its native square aspect', natural)
    audit.check(bool(photo and world and matrix and matrix['a'] > 0
                     and abs(matrix['a']-matrix['d']) < .001
                     and abs(matrix['b']) < .001 and abs(matrix['c']) < .001
                     and abs(photo['width']-photo['height']) <= 1
                     and all(abs(photo[k]-world[k]) <= 1 for k in ('x', 'y', 'width', 'height'))),
                'Kitchen art uses one uniform projection, with no stretched photo', scene,
                category='reference-composition')
    if photo and stage:
        scale = photo['width']/1254
        expected = {'x': photo['x']+278*scale, 'y': photo['y']+352*scale,
                    'width': 699*scale, 'height': 776*scale}
        audit.check(all(abs(stage[k]-expected[k]) <= 1 for k in expected),
                    'Fridge cabinet remains registered to native photograph coordinates',
                    {'actual': stage, 'expected': expected}, category='reference-composition')
    else:
        audit.check(False, 'Fridge photograph and projected cabinet exist', scene, category='reference-composition')
    # The surrounding background may intentionally crop. The actual cabinet
    # corners must remain inside its scene host and the embed viewport.
    audit.check(inside(stage, host) and inside(stage, viewport_box(width, height)),
                'Actual fridge cabinet corners are not cropped by the scene host', scene,
                category='reference-composition')
    canvas = scene['canvas']
    if photo and canvas:
        covered_width = max(0, min(photo['right'], canvas['right'])-max(photo['x'], canvas['x']))
        covered_height = max(0, min(photo['bottom'], canvas['bottom'])-max(photo['y'], canvas['y']))
        coverage = covered_width*covered_height/(canvas['width']*canvas['height'])
    else:
        coverage = 0
    audit.check(coverage >= .945,
                'One continuous kitchen photograph covers the home canvas without a large blank band or sidebar',
                {'photo_coverage': coverage, 'photo': photo, 'canvas': canvas}, category='reference-composition')
    audit.check(bool(canvas and natural and canvas['height'] > 0
                     and abs(canvas['width']/canvas['height']-natural['width']/natural['height']) <= .055),
                'The home canvas follows the native photograph composition instead of forcing a wide host crop',
                canvas, category='reference-composition')
    rows = [b['rect'] for b in balance if b['rect']]
    audit.check(len(rows) == 3 and {b['key'] for b in balance} == {'carb', 'protein', 'fat'}
                and max(r['y'] for r in rows)-min(r['y'] for r in rows) <= 1.5
                and all(inside(r, canvas) for r in rows)
                and rows[0]['right'] <= rows[1]['x']+1 and rows[1]['right'] <= rows[2]['x']+1,
                'Reference nutrition summary keeps all three values in one horizontal row',
                balance, category='reference-composition')


def recipe_photo_geometry(audit, photo, label, recipe_id):
    number = int(recipe_id.removeprefix('recipe-')) if recipe_id and recipe_id.removeprefix('recipe-').isdigit() else 0
    expected_viewbox = {'x': (number-1) % 2 * 512, 'y': (number-1) // 2 * 384, 'width': 512, 'height': 384}
    audit.check(bool(photo and 1 <= number <= 8 and photo['recipe'] == recipe_id
                     and photo['viewBox'] == expected_viewbox and photo['clip'] == expected_viewbox
                     and photo['atlas']['decoded']
                     and photo['atlas']['naturalWidth'] == photo['atlas']['width'] == 1024
                     and photo['atlas']['naturalHeight'] == photo['atlas']['height'] == 1536
                     and photo['atlas']['x'] == photo['atlas']['y'] == 0),
                label+' uses the actual selected recipe photograph', photo)
    audit.check(bool(photo and photo['scale']['x'] > 0
                     and photo['scale']['y'] > 0
                     and abs(photo['scale']['x']/photo['scale']['y']-1) <= .005
                     and abs(photo['scale']['shear']) <= .005),
                label+' preserves the actual photograph aspect while allowing a crop',
                photo, category='reference-composition')
    audit.check(bool(photo and photo['blankFraction'] <= .055),
                label+' painted photograph leaves at most about 5% blank frame area',
                photo, category='reference-composition')


def recipe_home_geometry(audit, metrics, expected_ids=None):
    recipe, panel = metrics['recipe'], metrics['panel']
    catalog = {row['id']: row for row in recipe['catalog']}
    cards, grid = recipe['cards'], recipe['grid']
    expected = set(catalog) if expected_ids is None else set(expected_ids)
    actual = [card['id'] for card in cards]
    audit.check(len(cards) == min(8, len(expected)) and len(set(actual)) == len(actual)
                and set(actual) <= expected and (len(expected) > 8 or set(actual) == expected),
                'Recommendation grid shows up to eight distinct actual matching catalog recipes',
                {'expected_ids': sorted(expected), 'actual_ids': actual})
    grid_inside = bool(grid and panel and inside(grid, panel['rect'])
                       and inside(grid, viewport_box(metrics['viewport']['width'], metrics['viewport']['height'])))
    audit.check(grid_inside if cards else grid is None or grid_inside,
                'The complete recommendation grid stays inside its panel and viewport',
                {'grid': grid, 'panel': panel}, category='reference-composition')
    if cards:
        columns = recipe['gridColumns']
        rows = len({round(card['rect']['y'], 1) for card in cards if card['rect']})
        audit.check(columns in (2, 4) and rows <= 4 and (len(cards) < 8 or columns*rows == 8),
                    'Eight recommendations form a two-by-four or four-by-two card grid',
                    {'columns': columns, 'rows': rows}, category='reference-composition')
    audit.check(recipe['singleRecipePager'] == 0 if len(expected) <= 8 else True,
                'Eight or fewer recipes do not require one-card paging', recipe['singleRecipePager'])
    for card in cards:
        expected_row = catalog.get(card['id'])
        audit.check(bool(expected_row and card['title'] == expected_row['name']
                         and card['time'] and expected_row['time'] in card['time']),
                    card['id']+' displays its actual full catalog name and cooking time', card)
        audit.check(bool(expected_row and card['text']) and all(t['readable'] for t in card['text'])
                    and any(t['text'] == expected_row['name'] for t in card['text'])
                    and any(expected_row['time'] in t['text'] for t in card['text']),
                    card['id']+' name and cooking time are readable without clipping', card['text'])
        primary(audit, card['open'], metrics['viewport']['width'], metrics['viewport']['height'],
                card['id']+' recipe card')
        audit.check(inside(card['rect'], grid) and inside(card['open'].get('rect'), card['rect']),
                    card['id']+' full card and hit target fit the initial grid',
                    {'card': card['rect'], 'target': card['open']}, category='reference-composition')
        recipe_photo_geometry(audit, card['photo'], card['id']+' grid thumbnail', card['id'])
        photo, copy = card['photo'], card['copy']
        if photo and copy:
            frame = photo['frame']
            overlap_width = max(0, min(frame['right'], copy['right'])-max(frame['x'], copy['x']))
            overlap_height = max(0, min(frame['bottom'], copy['bottom'])-max(frame['y'], copy['y']))
            audit.check(inside(frame, card['rect']) and inside(copy, card['rect'])
                        and (overlap_width <= 1 or overlap_height <= 1),
                        card['id']+' actual thumbnail and information do not overlap',
                        {'photo': frame, 'copy': copy}, category='reference-composition')
    overlaps = []
    for index, first in enumerate(cards):
        for second in cards[index+1:]:
            a, b = first['rect'], second['rect']
            if a and b and min(a['right'], b['right'])-max(a['x'], b['x']) > .5 \
                    and min(a['bottom'], b['bottom'])-max(a['y'], b['y']) > .5:
                overlaps.append([first['id'], second['id']])
    audit.check(not overlaps, 'Recipe card hit areas do not overlap one another', overlaps)


def registration_targets(audit, controls, geometry, label):
    for control in controls:
        primary(audit, control, geometry['viewport']['width'], geometry['viewport']['height'],
                label+' '+(control.get('title') or control.get('text') or 'control'))
        audit.check(inside(control.get('rect'), geometry['tray'])
                    and inside(control.get('rect'), control.get('clip')),
                    label+' target is initially inside the modal and every clipping ancestor', control)
    overlaps = []
    for index, first in enumerate(controls):
        for second in controls[index+1:]:
            a, b = first.get('rect'), second.get('rect')
            if not a or not b:
                continue
            width = max(0, min(a['right'], b['right'])-max(a['x'], b['x']))
            height = max(0, min(a['bottom'], b['bottom'])-max(a['y'], b['y']))
            if width*height > .01:
                overlaps.append({'first': first.get('workflow', first.get('text')),
                                 'second': second.get('workflow', second.get('text')),
                                 'width': width, 'height': height, 'area': width*height})
    audit.check(not overlaps, label+' initial hitboxes do not overlap', overlaps)


def registration_journey(audit, page, frame, folder, label, original, screens):
    # These routes remain read-only: no file selection, OCR or form submission.
    # Actual two-file selection/save is covered by the separate business suite.
    close_tray(frame)
    frame.locator('.home-shortcuts [data-home-tab="fridge"]').click()
    frame.locator('#addFood').click()
    methods = capture(page, frame, folder, label+'-ingredient-methods', REGISTRATION)
    screens['ingredient-methods'] = methods
    audit.check(methods['route'] == 'add'
                and [(m.get('workflow'), m.get('title')) for m in methods['methods']] == [
                    ('photos', '제품·기한 사진 2장'), ('manualAdd', '직접 입력'), ('fridgePhoto', '사진 보며 입력')],
                'A2 retains all three actual registration choices', methods['methods'])
    registration_targets(audit, methods['methods'], methods, 'A2 registration method')
    preservation(audit, frame, original, 'Read-only registration choices preserve exact stored records')
    frame.locator('#tray [data-wf="photos"]').click()
    photos = capture(page, frame, folder, label+'-ingredient-photos', REGISTRATION)
    screens['ingredient-photos'] = photos
    audit.check(photos['route'] == 'photos'
                and [(p['axis'], p['label']) for p in photos['photoSlots']] == [
                    ('product', '제품 사진'), ('expiry', '기한 사진')],
                'A3 retains separate real product and expiry photo inputs', photos['photoSlots'])
    audit.check({a.get('workflow') for a in photos['actions']} == {
        'retakePhotos', 'readPhotos', 'manualNoPhoto'} and len(photos['actions']) == 3,
        'A3 retains retake, read and manual-entry actions', photos['actions'])
    read = next((a for a in photos['actions'] if a.get('workflow') == 'readPhotos'), None)
    audit.check(bool(read and read['disabled']),
                'Recognition stays disabled while the required two photos are absent')
    registration_targets(audit, [p['control'] for p in photos['photoSlots']], photos, 'A3 photo input')
    registration_targets(audit, photos['actions'], photos, 'A3 photo/manual action')
    preservation(audit, frame, original, 'Read-only photo selection screen preserves exact stored records')
    frame.locator('#tray [data-wf="manualNoPhoto"]').click()
    manual = capture(page, frame, folder, label+'-ingredient-manual', REGISTRATION)
    screens['ingredient-manual'] = manual
    audit.check(manual['route'] == 'manualAdd'
                and {f['name'] for f in manual['fields']} == {'name', 'quantity', 'expiry', 'zone'},
                'A4 retains the actual ingredient name, quantity, expiry and location fields')
    registration_targets(audit, [manual['save']], manual, 'A4 manual ingredient save')
    preservation(audit, frame, original, 'Opening the unsubmitted manual form preserves exact stored records')
    close_tray(frame)
    preservation(audit, frame, original, 'Closing read-only registration preserves original v1 text and envelope')


def open_page(browser, origin, path, width, height, errors, requests, raw=None):
    context = browser.new_context(viewport={'width': width, 'height': height},
                                  locale='ko-KR', timezone_id='Asia/Seoul',
                                  has_touch=width < 500, reduced_motion='reduce')
    # One context init script also runs before opaque srcdoc startup. Do not
    # combine it with page.clock: child-frame Date initialization can otherwise
    # race between the actual day and the fixed QA day.
    context.add_init_script('''(()=>{
      const RealDate=Date,fixed='''+str(int(CLOCK.timestamp()*1000))+''';
      function ReviewDate(...args){
        if(!new.target)return new RealDate(fixed).toString();
        return Reflect.construct(RealDate,args.length?args:[fixed],new.target);
      }
      Object.setPrototypeOf(ReviewDate,RealDate);ReviewDate.prototype=RealDate.prototype;
      ReviewDate.now=()=>fixed;globalThis.Date=ReviewDate;
    })();''')
    def route(request_route):
        request = request_route.request
        parsed = urlsplit(request.url)
        if request.method not in ('GET', 'HEAD') or (
                parsed.scheme in ('http', 'https') and parsed.netloc != urlsplit(origin).netloc):
            requests.append({'url': request.url, 'method': request.method})
            request_route.abort('blockedbyclient')
        else:
            request_route.continue_()

    context.route('**/*', route)
    page = context.new_page()
    page.set_default_timeout(12000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    if raw is not None:
        # Seed exactly once on a script-free same-origin directory listing.
        # A persistent init script could silently reseed a deleted key on
        # reload and hide a destructive storage regression.
        page.goto(origin+'/')
        page.evaluate('([key,raw])=>localStorage.setItem(key,raw)', [KEY, raw])
    page.goto(origin+'/'+path)
    frame = page.locator('iframe').element_handle().content_frame() if '/mobile/' in '/'+path else page.main_frame
    frame.wait_for_function('window.MiniKitchen&&window.KitchenJournal&&window.KitchenHome&&window.KitchenWorkflows')
    ready(frame)
    return context, page, frame


def preservation(audit, frame, original, message):
    current = state(frame)
    audit.check(current['key'] == KEY and current['raw'] == original['raw']
                and current['envelope'] == original['envelope']
                and current['available'] == original['available'], message,
                {'key': current['key'], 'storageAvailable': current['available'],
                 'status': current['status'],
                 'raw_sha256': digest(current['raw'].encode()) if current['raw'] is not None else None})


def capture(page, frame, folder, name, metrics=METRICS):
    ready(frame)
    result = frame.evaluate(metrics)
    page.screenshot(path=str(folder/(name+'.png')))
    return result


def recipe_grid_journey(audit, page, frame, folder, label, original, screens):
    """Use every real card and visible filter controls without saving records."""
    close_tray(frame)
    frame.locator('.home-shortcuts [data-home-tab="meals"]').click()
    recommendation = frame.locator('[data-home-subtab="recommendation"]:visible')
    if recommendation.count():
        recommendation.click()
    ready(frame)
    initial = frame.evaluate(METRICS)
    catalog = {row['id']: row for row in initial['recipe']['catalog']}
    expected_ids = set(catalog)
    cards = initial['recipe']['cards']
    visited = []
    for card in cards:
        recipe_id = card['id']
        target = frame.locator(
            f'#homeRecommendation [data-home-recipe="{recipe_id}"][data-wf="recipe"], '
            f'#homeRecommendation [data-home-recipe="{recipe_id}"] [data-wf="recipe"]').first
        target.click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=recipe]")')
        ready(frame)
        actual = frame.evaluate('''()=>({
          id:document.querySelector('#tray .recipe-favorite')?.dataset.arg,
          name:document.querySelector('#tray .recipe-detail-name')?.textContent.trim(),
          photoId:document.querySelector('#tray svg.recipe-photo')?.dataset.recipePhoto})''')
        audit.check(actual == {'id': recipe_id, 'name': catalog[recipe_id]['name'], 'photoId': recipe_id},
                    recipe_id+' actual card opens its own matching recipe detail and photograph', actual)
        preservation(audit, frame, original, recipe_id+' read-only card detail preserves exact v1 records')
        visited.append(actual)
        close_tray(frame)
    audit.check(len(visited) == min(8, len(expected_ids))
                and {row['id'] for row in visited} == expected_ids,
                'All eight distinct recipe cards are individually reachable through actual clicks', visited)
    screens['recipe-grid-clicks'] = visited

    def apply_time(value):
        frame.locator('#homeRecommendation [data-wf="recipeFilters"]').click()
        form = frame.locator('#tray [data-wf-form="recipeFilters"]')
        for name in ('time', 'budget', 'exclude'):
            form.locator(f'[name="{name}"]').fill(value if name == 'time' else '')
        form.locator('[name="ingredient"]').select_option('')
        form.locator('[type="submit"]').click()
        frame.wait_for_function('!document.querySelector("#tray[open]")')
        ready(frame)
        return frame.evaluate(METRICS)

    filtered_ids = {row['id'] for row in catalog.values()
                    if int(''.join(c for c in row['time'] if c.isdigit())) <= 15}
    filtered = apply_time('15')
    audit.check(0 < len(filtered_ids) < len(catalog),
                'Explicit 15-minute fixture condition selects a genuine catalog subset', sorted(filtered_ids))
    recipe_home_geometry(audit, filtered, filtered_ids)
    preservation(audit, frame, original, 'Visible time filtering preserves exact records and unknown facts')
    screens['recipe-grid-filtered'] = filtered
    empty = apply_time('1')
    audit.check(not empty['recipe']['cards']
                and frame.locator('#homeRecommendation .recipe-hub-empty:visible').count() == 1,
                'No-match conditions show the real empty state instead of filling eight fake cards')
    preservation(audit, frame, original, 'No-match condition does not seed or rewrite stored data')
    frame.locator('#homeRecommendation [data-home-filter-reset]').last.click()
    ready(frame)
    restored = frame.evaluate(METRICS)
    recipe_home_geometry(audit, restored)
    audit.check(not any(restored['recipe']['filters'].values()),
                'Visible reset removes every transient recommendation filter')
    preservation(audit, frame, original, 'Resetting recipe conditions restores all cards without a storage write')


def widget_case(browser, origin, kind, width, height, folder):
    label = f'{kind}-{width}x{height}'
    evidence = {'id': label, 'entry': ENTRIES[kind], 'width': width, 'height': height,
                'screens': {}, 'page_errors': [], 'blocked_requests': [], 'reference_checks_required': True}
    audit = Audit(evidence)
    context = page = None
    try:
        context, page, frame = open_page(browser, origin, ENTRIES[kind], width, height,
                                         evidence['page_errors'], evidence['blocked_requests'])
        if kind == 'opaque':
            grants = (page.locator('iframe').get_attribute('sandbox') or '').split()
            audit.check('allow-scripts' in grants and 'allow-forms' in grants
                        and 'allow-same-origin' not in grants,
                        'Mobile preview retains its opaque sandbox boundary', grants)
            evidence['iframe'] = page.locator('iframe').bounding_box()
        original = state(frame)
        audit.check(original['available'] == (kind == 'native'),
                    'Native storage and opaque temporary storage are distinguished',
                    {'available': original['available'], 'status': original['status']})
        reference = None
        for tab in TABS:
            if tab != 'fridge':
                frame.locator(f'.home-shortcuts [data-home-tab="{tab}"]').click()
            metrics = capture(page, frame, folder, label+'-'+tab)
            evidence['screens'][tab] = metrics
            audit.check(metrics['home'] == tab, 'Actual navigation opens '+tab, metrics['home'])
            main_geometry(audit, metrics, width, height, reference)
            if tab == 'fridge':
                reference = metrics['shell']
                if kind == 'opaque':
                    wrapper = evidence['iframe']
                    audit.check(abs(wrapper['width']-width) <= 1
                                and abs(wrapper['height']-reference['height']) <= 1.5
                                and abs(wrapper['height']-metrics['viewport']['height']) <= 1,
                                'Opaque delivery iframe is bounded to the visible widget height', wrapper)
                primary(audit, metrics['add'], metrics['viewport']['width'],
                        metrics['viewport']['height'], 'Ingredient add')
                scene_geometry(audit, metrics['scene'], metrics['viewport']['width'],
                               metrics['viewport']['height'], metrics['balance'])
            if tab == 'meals':
                recipe_home_geometry(audit, metrics)
            preservation(audit, frame, original, 'Read-only '+tab+' navigation preserves exact stored text and envelope')
        recipe_grid_journey(audit, page, frame, folder, label, original, evidence['screens'])
        frame.locator('.home-shortcuts [data-home-tab="meals"]').click()
        recipe = frame.locator('#todayKitchen [data-wf="recipe"]:visible').first
        recipe_id = recipe.get_attribute('data-arg')
        ingredient_names = frame.evaluate('id=>Object.keys(KitchenCatalog.find(r=>r.id===id).amounts)', recipe_id)
        recipe.click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=recipe]")')
        details = capture(page, frame, folder, label+'-recipe-detail', DETAIL)
        evidence['screens']['recipe-detail'] = details
        recipe_photo_geometry(audit, details['photo'], 'Recipe detail hero', recipe_id)
        audit.check(bool(details['text']) and all(t['readable'] for t in details['text']),
                    'Actual recipe detail title and nutrition text remain readable', details['text'])
        detail_width, detail_height = details['viewport']['width'], details['viewport']['height']
        audit.check(inside(details['tray'], viewport_box(detail_width, detail_height))
                    and details['documentWidth'] <= detail_width+1
                    and details['tray']['height'] <= reference['height']+1
                    and inside(details['pane'], details['tray'])
                    and inside(details['pane'], viewport_box(detail_width, detail_height)),
                    'Recipe detail fits the embed without horizontal overflow', details['tray'])
        audit.check(details['pane']['height'] >= 87.5,
                    'Recipe ingredient body retains at least 88px of usable height', details['pane'])
        audit.check(len(details['rows']) == len(ingredient_names)
                    and all(name in row['text'] for name, row in zip(ingredient_names, details['rows'])),
                    'Recipe detail shows the actual selected recipe ingredients',
                    {'expected': ingredient_names, 'actual': [r['text'] for r in details['rows']]})
        audit.check(sum(r['readable'] for r in details['rows']) >= min(2, len(ingredient_names)),
                    'At least two actual ingredient entries are readable before scrolling', details['rows'])
        audit.check(len(details['actions']) == 2, 'Both plan and actual-meal actions remain present')
        for action in details['actions']:
            primary(audit, action, detail_width, detail_height, action['text'])
        # Exercise the actual ingredient scroller, including the final row.
        last = frame.locator('#tray .recipe-ingredient-list>div').last
        last.scroll_into_view_if_needed()
        scrolled = frame.evaluate(DETAIL)
        evidence['ingredient_after_scroll'] = scrolled
        audit.check(scrolled['rows'][-1]['readable'],
                    'The final actual ingredient remains readable by scrolling', scrolled['rows'][-1])
        audit.check(scrolled['scrollY'] == 0 and (
            details['scrollHeight'] <= details['pane']['height']+1 or scrolled['scrollTop'] > 0),
                    'Ingredient scrolling stays inside its own pane without moving the document',
                    {'before': details['scrollTop'], 'after': scrolled['scrollTop'], 'scrollY': scrolled['scrollY']})
        for action in scrolled['actions']:
            primary(audit, action, detail_width, detail_height, action['text']+' after ingredient scrolling')
        preservation(audit, frame, original, 'Read-only recipe detail and scrolling preserve exact records')
        registration_journey(audit, page, frame, folder, label, original, evidence['screens'])
    except Exception as error:
        audit.caught(error)
        evidence['traceback'] = traceback.format_exc()
        if page:
            page.screenshot(path=str(folder/(label+'-failure.png')))
    finally:
        audit.check(not evidence['page_errors'], 'No uncaught browser error', evidence['page_errors'])
        audit.check(not evidence['blocked_requests'], 'No external-provider or write request is attempted', evidence['blocked_requests'])
        if context:
            context.close()
    return finish_case(evidence)


def legacy_case(browser, origin, folder):
    fixture = REPO/'tests/fixtures/miniature-legacy-world-v1.json'
    world = json.loads(fixture.read_text())
    play = {'version': 1, 'meals': [],
            'targets': {k: None for k in ('kcal', 'carb', 'protein', 'fat', 'fiber', 'water')},
            'discovered': [], 'awarded': [], 'owned': [],
            'equipped': {'frozenLeft': None, 'frozenRight': None},
            'goal': 'collection', 'plateLabel': '우리 집 부엌'}
    # Existing supported v1 envelope: intentionally no workflow property. Keep
    # indentation/newlines so exact text comparison catches silent rewrites.
    raw = json.dumps({'version': 1, 'world': world, 'play': play}, ensure_ascii=False, indent=2)
    evidence = {'id': 'tracked-legacy-v1-native',
                'scope': 'Explicit tracked regression fixture, not real user records or product starter data',
                'fixture': str(fixture.relative_to(REPO)), 'fixture_sha256': digest(fixture.read_bytes()),
                'raw_sha256': digest(raw.encode()), 'page_errors': [], 'blocked_requests': []}
    audit = Audit(evidence)
    context = page = None
    try:
        context, page, frame = open_page(browser, origin, ENTRIES['native'], 390, 480,
                                         evidence['page_errors'], evidence['blocked_requests'], raw)
        original = state(frame)
        audit.check(original['raw'] == raw and original['status'] == 'saved'
                    and original['envelope']['world'] == world and original['envelope']['play'] == play,
                    'Existing v1 world, play state and original stored text load unchanged')
        for tab in TABS:
            frame.locator(f'.home-shortcuts [data-home-tab="{tab}"]').click()
            preservation(audit, frame, original, 'Legacy original survives '+tab+' navigation')
        frame.locator('.home-shortcuts [data-home-tab="meals"]').click()
        frame.locator('#todayKitchen [data-wf="recipe"]:visible').first.click()
        ready(frame)
        page.screenshot(path=str(folder/'tracked-legacy-v1-recipe.png'))
        preservation(audit, frame, original, 'Legacy original survives read-only detail')
        page.reload()
        frame = page.main_frame
        frame.wait_for_function('window.KitchenJournal&&window.KitchenHome')
        ready(frame)
        preservation(audit, frame, original, 'Legacy original and coordinates survive actual reload')
    except Exception as error:
        audit.caught(error)
        if page:
            page.screenshot(path=str(folder/'tracked-legacy-v1-failure.png'))
    finally:
        audit.check(not evidence['page_errors'], 'Legacy fixture has no browser error', evidence['page_errors'])
        audit.check(not evidence['blocked_requests'], 'Legacy fixture attempts no provider/write request', evidence['blocked_requests'])
        if context:
            context.close()
    return finish_case(evidence)


def reveal(locator):
    for ancestor in locator.locator('xpath=ancestor::details').all():
        if ancestor.get_attribute('open') is None:
            ancestor.locator('summary').first.click()
    return locator


def close_tray(frame):
    for _ in range(8):
        if not frame.locator('#tray[open]').count():
            return
        close = frame.locator('#closeTray:visible')
        (close if close.count() else frame.locator('#tray [data-wf="back"]:visible').first).click()
    raise AssertionError('The actual close/back controls did not leave the tray')


def prepare_meal_stock(frame):
    """Reuse the existing stock_ui journey with actual edit/add controls only."""
    for name, amount in QA_STOCK.items():
        close_tray(frame)
        frame.locator('.home-shortcuts [data-home-tab="fridge"]').click()
        items = [i for i in state(frame)['envelope']['world']['items']
                 if i['name'] == name and i['kind'] in ('food', 'seasoning')]
        if items:
            if len(items) != 1:
                raise AssertionError('Expected one starter QA stock lot for '+name)
            frame.locator('.header-actions [data-workflow="inventory"]').click()
            frame.locator(f'#tray [data-wf="item"][data-arg="{items[0]["id"]}"]').click()
            form = frame.locator('#ingredientForm')
        else:
            frame.locator('#addFood').click()
            frame.locator('#tray [data-wf="manualAdd"]').click()
            form = frame.locator('#addIngredientForm')
            form.locator('[name="name"]').fill(name)
            seasoning = name in ('식용유', '간장')
            reveal(form.locator('[name="kind"]')).select_option('seasoning' if seasoning else 'food')
            reveal(form.locator('[name="zone"]')).select_option('doorFreshRight' if seasoning else 'freshLeft')
        form.locator('[name="quantity"]').fill(amount)
        form.locator('[name="expiry"]').fill('2026-12-01')
        form.locator('[type="submit"]').click()
        actual = [i for i in state(frame)['envelope']['world']['items'] if i['name'] == name]
        if len(actual) != 1 or actual[0]['quantity'] != amount or actual[0]['expiry'] != '2026-12-01':
            raise AssertionError('The actual stock form did not save '+name)
    close_tray(frame)


def meal_success_case(browser, origin, kind, width, height, folder):
    """B6 needs five real deductions, not a fabricated success DOM/model result."""
    label = f'meal-success-{kind}-{width}x{height}'
    evidence = {'id': label, 'scope': 'Isolated browser QA context; stock and recipe facts are explicitly '
                'typed into actual forms. Values are test inputs, not verified food composition or user records.',
                'qa_stock': QA_STOCK, 'qa_facts': QA_FACTS,
                'page_errors': [], 'blocked_requests': []}
    audit = Audit(evidence)
    context = page = None
    try:
        context, page, frame = open_page(browser, origin, ENTRIES[kind], width, height,
                                         evidence['page_errors'], evidence['blocked_requests'])
        widget = frame.evaluate(METRICS)['shell']
        prepare_meal_stock(frame)
        frame.locator('.home-shortcuts [data-home-tab="meals"]').click()
        frame.locator('#homeRecommendation [data-wf="recipeCatalog"]').click()
        frame.locator('#tray .recipe-result[data-arg="recipe-1"]').click()
        frame.locator('#tray [data-recipe-tab="nutrition"]').click()
        frame.locator('#tray [data-wf="recipeFacts"]').click()
        facts = frame.locator('#tray [data-wf-form="facts"]')
        for name, value in QA_FACTS.items():
            reveal(facts.locator(f'[name="{name}"]')).fill(value)
        facts.locator('[name="source"]').fill('명시적 브라우저 QA 입력 · 1회분 · 실제 식품 성분값 아님')
        facts.locator('[type="submit"]').click()
        before = state(frame)['envelope']
        audit.check(all(before['workflow']['recipeFacts']['recipe-1'][k] == float(v)
                        for k, v in QA_FACTS.items()), 'Actual recipe facts form saves the explicit QA inputs')
        frame.locator('#tray [data-wf="logMeal"]').click()
        form = frame.locator('#workflowMealForm')
        form.locator('[name="day"]').fill('2026-11-05')
        form.locator('[name="slot"]').select_option('lunch')
        form.locator('[name="portions"]').fill('1')
        audit.check(all(form.locator(f'[name="{k}"]').input_value() == v
                        for k, v in QA_FACTS.items() if k != 'cost'),
                    'Actual meal form carries the entered one-portion nutrition')
        audit.check(state(frame)['envelope'] == before,
                    'Opening and reviewing the meal does not consume stock before save')
        ready(frame)
        page.screenshot(path=str(folder/(label+'-B5.png')))
        form.locator('[type="submit"]').click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=mealSuccess]")')
        geometry = capture(page, frame, folder, label+'-B6', SUCCESS)
        evidence['initial_success'] = geometry
        after = state(frame)['envelope']
        previous_ids = {m['id'] for m in before['play']['meals']}
        added = [m for m in after['play']['meals'] if m['id'] not in previous_ids]
        audit.check(len(added) == 1 and len(after['play']['meals']) == len(before['play']['meals'])+1,
                    'Saving through the actual control adds exactly one meal')
        if len(added) != 1:
            raise AssertionError('Cannot identify the single saved QA meal')
        meal = added[0]
        transaction = next(t for t in after['workflow']['transactions'] if t['mealId'] == meal['id'])
        audit.check(meal['recipeId'] == 'recipe-1' and meal['day'] == '2026-11-05'
                    and all(meal['nutrients'][k] == float(v) for k, v in QA_FACTS.items() if k != 'cost')
                    and meal['nutrients']['fiber'] is None and meal['nutrients']['water'] is None,
                    'The saved meal retains entered nutrition and leaves unknown values unknown', meal)
        expected = {'계란': '5개', '양파': '1.75개', '식용유': '9작은술', '간장': '9작은술', '밥': '9공기'}
        quantities = {i['name']: i['quantity'] for i in after['world']['items'] if i['name'] in expected}
        audit.check(transaction['active'] and transaction['portions'] == 1
                    and len(transaction['deductions']) == 5 and quantities == expected,
                    'The actual transaction consumes the five intended ingredient amounts', quantities)
        audit.check(after['workflow']['expenses'] == before['workflow']['expenses']
                    and after['workflow']['plans'] == before['workflow']['plans'],
                    'Meal consumption leaves actual purchase expenses and plans unchanged')
        audit.check(inside(geometry['tray'], widget)
                    and geometry['content']['scrollHeight'] <= geometry['content']['height']+1
                    and geometry['content']['scrollTop'] == 0 and geometry['document']['scrollY'] == 0,
                    'B6 fits the visible widget with no outer-content scrolling to find actions', geometry['content'])
        audit.check({a['workflow'] for a in geometry['actions']} == {
            'successRecords', 'successHome', 'undoSuccessMeal'}, 'B6 retains all three real primary actions')
        audit.check(len(geometry['deductions']) == 5, 'B6 retains every actual deduction row')
        for action in geometry['actions']:
            primary(audit, action, geometry['viewport']['width'], geometry['viewport']['height'], action['text'])
            audit.check(inside(action['rect'], geometry['tray']) and inside(action['rect'], widget),
                        action['text']+' is initially inside the visible widget', action['rect'])
        # Geometry is captured before any primary action can auto-scroll.
        frame.locator('#tray [data-wf="undoSuccessMeal"]').click()
        undone = state(frame)['envelope']
        audit.check(undone['world'] == before['world'] and undone['play']['meals'] == before['play']['meals']
                    and not next(t for t in undone['workflow']['transactions'] if t['mealId'] == meal['id'])['active'],
                    'Actual undo restores that meal inventory and nutrition')
        form = frame.locator('#workflowMealForm')
        audit.check(form.locator('[name="day"]').input_value() == '2026-11-05'
                    and form.locator('[name="kcal"]').input_value() == QA_FACTS['kcal'],
                    'Undo keeps the entered meal available for review')
        form.locator('[type="submit"]').click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=mealSuccess]")')
        resaved = state(frame)['envelope']
        audit.check(resaved['world'] == after['world']
                    and len(resaved['play']['meals']) == len(after['play']['meals'])
                    and resaved['play']['awarded'] == after['play']['awarded']
                    and resaved['play']['owned'] == after['play']['owned'],
                    'Actual resave creates one meal without duplicate stock use or reward')
        exit_route, home = ('successHome', 'fridge') if kind == 'native' else ('successRecords', 'records')
        frame.locator(f'#tray [data-wf="{exit_route}"]').click()
        audit.check(not frame.locator('#tray[open]').count()
                    and frame.locator('body').get_attribute('data-home') == home
                    and state(frame)['envelope'] == resaved,
                    'Actual '+exit_route+' exits B6 without modifying the saved meal')
        page.screenshot(path=str(folder/(label+'-exit.png')))
    except Exception as error:
        audit.caught(error)
        evidence['traceback'] = traceback.format_exc()
        if page:
            page.screenshot(path=str(folder/(label+'-failure.png')))
    finally:
        audit.check(not evidence['page_errors'], 'B6 journey has no browser error', evidence['page_errors'])
        audit.check(not evidence['blocked_requests'], 'B6 journey attempts no provider or network write', evidence['blocked_requests'])
        if context:
            context.close()
    return finish_case(evidence)


def app_screens(browser, origin, folder, verify_recipe_grid=False):
    results = []
    for width, height in ((390, 844), (800, 600)):
        errors, requests = [], []
        context, page, frame = open_page(browser, origin, 'miniature-kitchen-app.html', width, height, errors, requests)
        try:
            original = state(frame)
            recipe_snapshot = recipe_result = None
            for tab in TABS:
                if tab != 'fridge':
                    frame.locator(f'.home-shortcuts [data-home-tab="{tab}"]').click()
                metrics = capture(page, frame, folder, f'app-{width}x{height}-{tab}')
                result = {'id': f'app-{width}x{height}-{tab}', 'shell': metrics['shell'],
                          'page_errors': errors, 'blocked_requests': requests}
                if verify_recipe_grid and tab == 'meals':
                    recipe_snapshot, recipe_result = metrics, result
                results.append(result)
            # Compare identical four-tab histories before either snapshot set
            # gets extra modal/filter activity. The new grid journey is still
            # checked fully, after all preservation screenshots are captured.
            if verify_recipe_grid:
                grid = {'id': recipe_result['id']+'-grid', 'reference_checks_required': True, 'screens': {}}
                audit = Audit(grid)
                recipe_home_geometry(audit, recipe_snapshot)
                recipe_grid_journey(audit, page, frame, folder, recipe_result['id'], original, grid['screens'])
                recipe_result['recipe_grid_result'] = finish_case(grid)
        finally:
            context.close()
    return results


def compare_png(browser, before, after, output):
    """Decode actual PNGs with Chromium; avoid optional image-library dependencies."""
    page = browser.new_page()
    try:
        result = page.evaluate('''async([before,after])=>{
          const load=async url=>{const i=new Image();i.src=url;await i.decode();return i};
          const [a,b]=await Promise.all([load(before),load(after)]);
          if(a.width!==b.width||a.height!==b.height)return {sameSize:false,
            before:[a.width,a.height],after:[b.width,b.height],pixelsEqual:false};
          const canvas=document.createElement('canvas');canvas.width=a.width;canvas.height=a.height;
          const c=canvas.getContext('2d',{willReadFrequently:true});c.drawImage(a,0,0);
          const x=c.getImageData(0,0,a.width,a.height);c.clearRect(0,0,a.width,a.height);c.drawImage(b,0,0);
          const y=c.getImageData(0,0,a.width,a.height),diff=c.createImageData(a.width,a.height);
          let changed=0;for(let i=0;i<x.data.length;i+=4){const different=[0,1,2,3].some(k=>x.data[i+k]!==y.data[i+k]);
            if(different){changed++;diff.data.set([255,0,75,255],i)}else diff.data.set([y.data[i],y.data[i+1],y.data[i+2],70],i)}
          c.putImageData(diff,0,0);return {sameSize:true,changedPixels:changed,
            totalPixels:a.width*a.height,pixelsEqual:changed===0,diff:canvas.toDataURL('image/png')};
        }''', ['data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode() for p in (before, after)])
        encoded = result.pop('diff', None)
        if encoded and not result['pixelsEqual']:
            output.write_bytes(base64.b64decode(encoded.split(',', 1)[1]))
            result['diff_image'] = output.name
        return result
    finally:
        page.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Already-generated previews directory')
    parser.add_argument('--output', type=Path, required=True, help='Evidence directory outside the checkout')
    parser.add_argument('--browser-executable', help='Optional Chromium path; otherwise use system or Playwright Chromium')
    parser.add_argument('--baseline-root', type=Path, help='Optional external build of the previous revision')
    parser.add_argument('--check-app-unchanged', action='store_true',
                        help='Require baseline app screenshots to have identical decoded pixels')
    parser.add_argument('--allow-app-recipe-grid-change', action='store_true',
                        help='With --check-app-unchanged, validate the intentional recipe grid change '
                             'while requiring the other six app screenshots to remain pixel-identical')
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    baseline = args.baseline_root.resolve() if args.baseline_root else None
    if out.is_relative_to(REPO) or out.is_relative_to(root) or root.is_relative_to(out):
        parser.error('Keep screenshots/results outside the checkout and generated input directory.')
    if baseline and (out.is_relative_to(baseline) or baseline.is_relative_to(out)):
        parser.error('Evidence must not overwrite the baseline build.')
    if args.check_app_unchanged and not baseline:
        parser.error('--check-app-unchanged requires --baseline-root.')
    if args.allow_app_recipe_grid_change and not args.check_app_unchanged:
        parser.error('--allow-app-recipe-grid-change requires --check-app-unchanged and --baseline-root.')
    paths = list(ENTRIES.values())+(['miniature-kitchen-app.html'] if args.check_app_unchanged else [])
    inputs = {}
    for label, source in [('after', root)]+([('before', baseline)] if baseline else []):
        for path in paths:
            actual = source/path
            if not actual.is_file():
                parser.error(f'Missing generated preview: {actual}. Build native and mobile previews first.')
            inputs[f'{label}/{path}'] = digest(actual.read_bytes())
    out.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'scope': 'Actual generated compact native and opaque widgets in local Chromium; '
              'no physical-device/Safari/Notion claim. Layout/navigation cases are read-only. '
              'B6 cases type labelled QA inputs and save/undo/resave a meal in isolated contexts only; '
              'no OCR/provider or outside-context writes. '
              'Before failures are observations; only candidate contracts and optional app preservation gate this run.',
              'clock': CLOCK.isoformat(), 'clock_method': 'Single context-init Date; native timers/RAF',
              'source_sha256': inputs, 'cases': [], 'baseline_observations': [],
              'comparisons': [], 'entry_geometry_comparisons': [], 'errors': [], 'visual_regressions': [],
              'intentional_app_change': 'Recommendation tab uses up to eight real recipe cards'
                if args.allow_app_recipe_grid_change else None,
              'manual_reference_review': {'required': True, 'status': 'not-assessed-by-automation',
                'note': 'Passing geometric/photo checks is not design approval. Review same-state screenshots '
                        'against the supplied A1–D6 reference composition and record any remaining differences.'}}
    servers = []
    try:
        with sync_playwright() as playwright:
            executable = args.browser_executable or shutil.which('chromium') or shutil.which('chromium-browser')
            launch = {'args': ['--no-sandbox']}
            if executable:
                launch['executable_path'] = executable
            browser = playwright.chromium.launch(**launch)
            report['browser'] = {'version': browser.version,
                                 'executable': executable or 'Playwright-managed Chromium'}
            for label, source in [('before', baseline), ('after', root)]:
                if source is None:
                    continue
                folder = out/label
                folder.mkdir(exist_ok=True)
                server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(source)))
                threading.Thread(target=server.serve_forever, daemon=True).start()
                servers.append(server)
                origin = f'http://127.0.0.1:{server.server_port}'
                target = report['cases'] if label == 'after' else report['baseline_observations']
                for kind in ENTRIES:
                    for width, height in PROFILES:
                        case = widget_case(browser, origin, kind, width, height, folder)
                        target.append(case)
                        if width == 562 and height == 800:
                            breakpoint_continuity(target, kind)
                        print(f'{label.upper()} {"PASS" if case["passed"] else "FAIL"} {case["id"]}', flush=True)
                if label == 'after':
                    report['cases'].append(legacy_case(browser, origin, folder))
                    for kind in ENTRIES:
                        for width, height in B6_PROFILES:
                            case = meal_success_case(browser, origin, kind, width, height, folder)
                            report['cases'].append(case)
                            print(f'AFTER {"PASS" if case["passed"] else "FAIL"} {case["id"]}', flush=True)
                if args.check_app_unchanged:
                    report[label+'_app'] = app_screens(browser, origin, folder,
                        verify_recipe_grid=label == 'after' and args.allow_app_recipe_grid_change)
            if baseline:
                compare_out = out/'comparison'
                compare_out.mkdir(exist_ok=True)
                for before in sorted((out/'before').glob('*.png')):
                    after = out/'after'/before.name
                    if after.is_file():
                        result = compare_png(browser, before, after, compare_out/before.name)
                        result['image'] = before.name
                        is_app = before.name.startswith('app-')
                        expected_grid_change = args.allow_app_recipe_grid_change and is_app and before.name.endswith('-meals.png')
                        result['app_unchanged_required'] = args.check_app_unchanged and is_app and not expected_grid_change
                        result['app_change_expected'] = expected_grid_change
                        report['comparisons'].append(result)
            # Native embeds and the opaque delivery wrapper must show the same
            # component, even when the outer phone browser is much taller.
            for width, height in PROFILES:
                pair = [next(c for c in report['cases'] if c['id'] == f'{kind}-{width}x{height}')
                        for kind in ('native', 'opaque')]
                comparisons = []
                for tab in TABS:
                    screens = [c['screens'].get(tab) for c in pair]
                    equal = bool(all(screens))
                    if equal:
                        for box in ('shell', 'header', 'nav'):
                            a, b = screens[0][box], screens[1][box]
                            if a is None or b is None:
                                equal = equal and a is b
                            else:
                                equal = equal and all(abs(a[key]-b[key]) <= 1.5
                                                      for key in ('x', 'y', 'width', 'height'))
                    comparisons.append({'screen': tab, 'same_geometry': equal})
                row = {'profile': f'{width}x{height}', 'screens': comparisons,
                       'passed': all(c['same_geometry'] for c in comparisons)}
                report['entry_geometry_comparisons'].append(row)
                if not row['passed']:
                    report['visual_regressions'].append('Native/opaque widget geometry differs: '+row['profile'])
            browser.close()
        for key, original in inputs.items():
            label, relative = key.split('/', 1)
            source = root if label == 'after' else baseline
            if digest((source/relative).read_bytes()) != original:
                report['errors'].append('Generated input changed during browser verification: '+key)
        if args.check_app_unchanged:
            app = [c for c in report['comparisons'] if c['app_unchanged_required']]
            all_app = [c for c in report['comparisons'] if c['image'].startswith('app-')]
            expected_unchanged = (len(TABS)-int(args.allow_app_recipe_grid_change))*2
            grids = [row['recipe_grid_result'] for row in report['after_app'] if 'recipe_grid_result' in row]
            report['app_recipe_grid_passed'] = len(grids) == 2 and all(row['passed'] for row in grids) \
                if args.allow_app_recipe_grid_change else None
            report['app_recipe_grid_functional_passed'] = len(grids) == 2 and all(
                row['functional_passed'] for row in grids) if args.allow_app_recipe_grid_change else None
            report['app_recipe_grid_reference_passed'] = len(grids) == 2 and all(
                row['reference_composition_checks_passed'] for row in grids) if args.allow_app_recipe_grid_change else None
            report['app_preservation_passed'] = len(all_app) == len(TABS)*2 \
                and len(app) == expected_unchanged and all(c['pixelsEqual'] for c in app) \
                and (not args.allow_app_recipe_grid_change or report['app_recipe_grid_passed'])
            if not report['app_preservation_passed']:
                report['visual_regressions'].append('App preservation screenshots differ or are missing; inspect comparison evidence.')
            if any(c['page_errors'] or c['blocked_requests'] for c in report['after_app']):
                report['errors'].append('App preservation journey emitted browser errors or blocked requests.')
        else:
            report['app_preservation_passed'] = None
        report['functional_passed'] = bool(report['cases']) and all(c['functional_passed'] for c in report['cases']) \
            and not report['errors'] and (not args.allow_app_recipe_grid_change
                                         or report.get('app_recipe_grid_functional_passed') is True)
        reference_cases = [c for c in report['cases'] if c.get('reference_checks_required')]
        report['reference_composition_checks_passed'] = bool(reference_cases) and all(
            c['reference_composition_checks_passed'] for c in reference_cases) \
            and (not args.allow_app_recipe_grid_change or report.get('app_recipe_grid_reference_passed') is True)
        report['entry_geometry_passed'] = len(report['entry_geometry_comparisons']) == len(PROFILES) and all(
            c['passed'] for c in report['entry_geometry_comparisons'])
        report['passed'] = report['functional_passed'] and report['reference_composition_checks_passed'] and not report['visual_regressions']
    except Exception as error:
        report['errors'].append(str(error))
        report['traceback'] = traceback.format_exc()
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        (out/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    failures = [{'case': case['id'],
                 'checks': sorted({check['name'] for check in case.get('checks', [])
                                   if not check['passed']})}
                for case in report['cases'] if not case['passed']]
    print(json.dumps({'passed': report['passed'], 'candidate_cases': len(report['cases']),
                      'functional_passed': report.get('functional_passed'),
                      'reference_composition_checks_passed': report.get('reference_composition_checks_passed'),
                      'manual_reference_review_required': True,
                      'failures': failures, 'errors': report['errors'], 'visual_regressions': report['visual_regressions'],
                      'report': str(out/'results.json')}, ensure_ascii=False), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
