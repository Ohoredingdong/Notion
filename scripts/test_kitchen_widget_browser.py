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
PROFILES = ((320, 360), (390, 480), (720, 500), (800, 600), (390, 844))
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


METRICS = '''()=>{
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
    panel:panel?{id:panel.id,rect:rect(panel),width:panel.clientWidth,height:panel.clientHeight,
      scrollWidth:panel.scrollWidth,scrollHeight:panel.scrollHeight}:null,
    tabs:[...document.querySelectorAll('.home-shortcuts [data-home-tab]')].map(control),
    add:control(document.querySelector('#addFood')),
    scene:{host:one('#fridgeSceneHost'),photo:rect(photo),world:rect(world),
      stage:one('#fridgeSceneHost .fridge-stage'),
      natural:photo?{width:photo.naturalWidth,height:photo.naturalHeight,complete:photo.complete}:null,
      matrix:matrix?{a:matrix.a,b:matrix.b,c:matrix.c,d:matrix.d}:null},
    home:document.body.dataset.home};
}'''


DETAIL = '''()=>{
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


class Audit:
    def __init__(self, evidence):
        self.evidence = evidence

    def check(self, value, message, detail=None):
        row = {'passed': bool(value), 'name': message}
        if detail is not None:
            row['detail'] = detail
        self.evidence.setdefault('checks', []).append(row)

    def caught(self, error):
        self.check(False, 'Browser journey completes', str(error))


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
    audit.check(bool(shell and abs(shell['width']-width) <= 1 and abs(shell['x']) <= 1),
                'Widget fills actual host width without height-driven narrowing', shell)
    audit.check(bool(shell and shell['y'] >= -1 and shell['bottom'] <= height+1
                     and min(height, 300) <= shell['height'] <= min(height, 520)+1),
                'Widget height fits the host and remains bounded at 520px', shell)
    audit.check(bool(header and 43.5 <= header['height'] <= 48.5 and abs(header['y']) <= 1),
                'Compact brand header stays at the top and 44–48px high', header)
    audit.check(bool(nav and 43.5 <= nav['height'] <= 48.5 and header
                     and abs(nav['y']-header['bottom']) <= 1),
                'Text navigation stays below the header and 44–48px high', nav)
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


def scene_geometry(audit, scene, width, height):
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
                'Kitchen art uses one uniform projection, with no stretched photo', scene)
    if photo and stage:
        scale = photo['width']/1254
        expected = {'x': photo['x']+278*scale, 'y': photo['y']+352*scale,
                    'width': 699*scale, 'height': 776*scale}
        audit.check(all(abs(stage[k]-expected[k]) <= 1 for k in expected),
                    'Fridge cabinet remains registered to native photograph coordinates',
                    {'actual': stage, 'expected': expected})
    else:
        audit.check(False, 'Fridge photograph and projected cabinet exist', scene)
    # The surrounding background may intentionally crop. The actual cabinet
    # corners must remain inside its scene host and the embed viewport.
    audit.check(inside(stage, host) and inside(stage, viewport_box(width, height)),
                'Actual fridge cabinet corners are not cropped by the scene host', scene)


def open_page(browser, origin, path, width, height, errors, requests, raw=None):
    context = browser.new_context(viewport={'width': width, 'height': height},
                                  locale='ko-KR', timezone_id='Asia/Seoul',
                                  has_touch=width < 500, reduced_motion='reduce')
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
    page.clock.install(time=CLOCK)
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


def widget_case(browser, origin, kind, width, height, folder):
    label = f'{kind}-{width}x{height}'
    evidence = {'id': label, 'entry': ENTRIES[kind], 'width': width, 'height': height,
                'screens': {}, 'page_errors': [], 'blocked_requests': []}
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
                               metrics['viewport']['height'])
            preservation(audit, frame, original, 'Read-only '+tab+' navigation preserves exact stored text and envelope')
        frame.locator('.home-shortcuts [data-home-tab="meals"]').click()
        recipe = frame.locator('#todayKitchen [data-wf="recipe"]:visible').first
        recipe_id = recipe.get_attribute('data-arg')
        ingredient_names = frame.evaluate('id=>Object.keys(KitchenCatalog.find(r=>r.id===id).amounts)', recipe_id)
        recipe.click()
        frame.wait_for_function('document.querySelector("#tray[open][data-workflow-route=recipe]")')
        details = capture(page, frame, folder, label+'-recipe-detail', DETAIL)
        evidence['screens']['recipe-detail'] = details
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
    evidence['passed'] = all(c['passed'] for c in evidence['checks'])
    return evidence


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
    evidence['passed'] = all(c['passed'] for c in evidence['checks'])
    return evidence


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
    evidence['passed'] = all(c['passed'] for c in evidence['checks'])
    return evidence


def app_screens(browser, origin, folder):
    results = []
    for width, height in ((390, 844), (800, 600)):
        errors, requests = [], []
        context, page, frame = open_page(browser, origin, 'miniature-kitchen-app.html', width, height, errors, requests)
        try:
            for tab in TABS:
                if tab != 'fridge':
                    frame.locator(f'.home-shortcuts [data-home-tab="{tab}"]').click()
                metrics = capture(page, frame, folder, f'app-{width}x{height}-{tab}')
                results.append({'id': f'app-{width}x{height}-{tab}', 'shell': metrics['shell'],
                                'page_errors': errors, 'blocked_requests': requests})
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
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    baseline = args.baseline_root.resolve() if args.baseline_root else None
    if out.is_relative_to(REPO) or out.is_relative_to(root) or root.is_relative_to(out):
        parser.error('Keep screenshots/results outside the checkout and generated input directory.')
    if baseline and (out.is_relative_to(baseline) or baseline.is_relative_to(out)):
        parser.error('Evidence must not overwrite the baseline build.')
    if args.check_app_unchanged and not baseline:
        parser.error('--check-app-unchanged requires --baseline-root.')
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
              'clock': CLOCK.isoformat(), 'source_sha256': inputs, 'cases': [], 'baseline_observations': [],
              'comparisons': [], 'entry_geometry_comparisons': [], 'errors': []}
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
                        print(f'{label.upper()} {"PASS" if case["passed"] else "FAIL"} {case["id"]}', flush=True)
                if label == 'after':
                    report['cases'].append(legacy_case(browser, origin, folder))
                    for kind in ENTRIES:
                        for width, height in B6_PROFILES:
                            case = meal_success_case(browser, origin, kind, width, height, folder)
                            report['cases'].append(case)
                            print(f'AFTER {"PASS" if case["passed"] else "FAIL"} {case["id"]}', flush=True)
                if args.check_app_unchanged:
                    report[label+'_app'] = app_screens(browser, origin, folder)
            if baseline:
                compare_out = out/'comparison'
                compare_out.mkdir(exist_ok=True)
                for before in sorted((out/'before').glob('*.png')):
                    after = out/'after'/before.name
                    if after.is_file():
                        result = compare_png(browser, before, after, compare_out/before.name)
                        result['image'] = before.name
                        result['app_unchanged_required'] = args.check_app_unchanged and before.name.startswith('app-')
                        report['comparisons'].append(result)
            # Native embeds and the opaque delivery wrapper must show the same
            # component, even when the outer phone browser is much taller.
            for width, height in PROFILES:
                pair = [next(c for c in report['cases'] if c['id'] == f'{kind}-{width}x{height}')
                        for kind in ('native', 'opaque')]
                comparisons = []
                for tab in TABS:
                    screens = [c['screens'].get(tab) for c in pair]
                    equal = bool(all(screens)) and all(
                        s[box] for s in screens for box in ('shell', 'header', 'nav')) and all(
                        abs(screens[0][box][key]-screens[1][box][key]) <= 1.5
                        for box in ('shell', 'header', 'nav')
                        for key in ('x', 'y', 'width', 'height'))
                    comparisons.append({'screen': tab, 'same_geometry': equal})
                row = {'profile': f'{width}x{height}', 'screens': comparisons,
                       'passed': all(c['same_geometry'] for c in comparisons)}
                report['entry_geometry_comparisons'].append(row)
                if not row['passed']:
                    report['errors'].append('Native/opaque widget geometry differs: '+row['profile'])
            browser.close()
        for key, original in inputs.items():
            label, relative = key.split('/', 1)
            source = root if label == 'after' else baseline
            if digest((source/relative).read_bytes()) != original:
                report['errors'].append('Generated input changed during browser verification: '+key)
        if args.check_app_unchanged:
            app = [c for c in report['comparisons'] if c['app_unchanged_required']]
            if len(app) != len(TABS)*2 or not all(c['pixelsEqual'] for c in app):
                report['errors'].append('App preservation screenshots differ or are missing; inspect comparison evidence.')
            if any(c['page_errors'] or c['blocked_requests'] for c in report['after_app']):
                report['errors'].append('App preservation journey emitted browser errors or blocked requests.')
        report['passed'] = bool(report['cases']) and all(c['passed'] for c in report['cases']) and not report['errors']
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
                      'failures': failures, 'errors': report['errors'],
                      'report': str(out/'results.json')}, ensure_ascii=False), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
