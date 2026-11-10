#!/usr/bin/env python3
"""Compare readable recipe quantities with unchanged frozen model/storage data.

Uses disposable Chromium contexts and real portion/disclosure controls. Both
deliveries use the same Nov10 clock and default stock. Screenshots are selected
before/after pairs, not proof of real-device or live Notion verification.
"""
import argparse
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
PROFILES = (
    ('native', 'miniature-kitchen-widget.html', 320, 360),
    ('native', 'miniature-kitchen-widget.html', 390, 480),
    ('native', 'miniature-kitchen-widget.html', 720, 800),
    ('opaque', 'mobile/widget.html', 320, 360),
    ('opaque', 'mobile/widget.html', 390, 480),
    ('opaque', 'mobile/widget.html', 720, 800),
    ('app', 'miniature-kitchen-app.html', 390, 844),
    ('app', 'mobile/app.html', 720, 900),
)
PORTIONS = (('1', '1/3개'), ('2', '2/3개'), ('3', '1개'),
            ('4', '1 1/3개'), ('0.5', '1/6개'))
SELECTED = {'native-320x360', 'native-390x480', 'native-720x800', 'app-390x844'}
SOURCES = ('test_kitchen_recipe_quantity_browser.py', *detail.SOURCES)
MODEL = r'''portions=>{
 const recipe=KitchenCatalog.find(r=>r.id==='recipe-4'),world=MiniKitchen.exportWorld();
 return {recipe,world,availability:KitchenJourneyModel.recipeAvailability(recipe,world,{day:'2026-11-10',portions}),
  cost:KitchenRecipeCost.suggest(recipe,{flow:KitchenJournal.getWorkflow(),day:'2026-11-10',portions,reference:KitchenRecipeReference})};
}'''
TEXT_GEOMETRY = r'''e=>{''' + old.PAINT_HELPERS + r'''
 const r=e.getBoundingClientRect();let l=0,t=0,right=innerWidth,b=innerHeight;
 for(let n=e.parentElement;n;n=n.parentElement){const s=getComputedStyle(n),p=n.getBoundingClientRect();
  if(/hidden|auto|scroll|clip/.test(s.overflowX)){l=Math.max(l,p.x+n.clientLeft);right=Math.min(right,p.x+n.clientLeft+n.clientWidth)}
  if(/hidden|auto|scroll|clip/.test(s.overflowY)){t=Math.max(t,p.y+n.clientTop);b=Math.min(b,p.y+n.clientTop+n.clientHeight)}}
 return {rect:{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom},
  inside:r.x>=l-1&&r.right<=right+1&&r.y>=t-1&&r.bottom<=b+1,
  text:textRanges(e),unobscured:[.1,.5,.9].every(x=>[.1,.5,.9].every(y=>{const h=document.elementFromPoint(r.x+r.width*x,r.y+r.height*y);return h===e||e.contains(h)}))};
}'''


def check(ev, passed, name, evidence=None, visual=False):
    detail.check(ev, passed, name, evidence, visual)


def center(locator):
    locator.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest'})")
    return locator


def readable(ev, locator, name):
    observed = center(locator).evaluate(TEXT_GEOMETRY)
    check(ev, observed['inside'] and observed['unobscured'] and observed['text']
          and all(t['readable'] for t in observed['text']),
          name+' can be read through actual scrolling without sticky/footer occlusion', observed, True)
    return observed


def delivery(browser, origin, entry, width, height, label, variant, folder, ev):
    context = page = None
    result = {'states': {}}
    try:
        context, page, frame = old.open_page(browser, origin, entry, width, height,
                                              ev['page_errors'], ev['blocked_requests'])
        initial = old.state(frame)
        result['initial_state'] = initial
        detail.recipe(frame, 'recipe-4')
        initial_metrics = frame.evaluate(detail.METRICS)
        result['shell'] = initial_metrics['shell']
        check(ev, old.inside(initial_metrics['detail']['tray'], initial_metrics['shell'])
              and initial_metrics['document']['width'] <= width+1
              and initial_metrics['document']['scrollY'] == 0,
              variant+' retains the fitted frame without horizontal overflow', initial_metrics['detail']['tray'], True)
        for portion, expected in PORTIONS:
            control = center(frame.locator('#recipePortions'))
            control.fill(portion);control.dispatch_event('change');old.ready(frame)
            model = frame.evaluate(MODEL, float(portion))
            row = frame.locator('#tray .recipe-ingredient-list>div').filter(has_text='애호박')
            required = row.locator('.recipe-ingredient-amounts>span').inner_text()
            readable(ev, row, variant+' '+portion+' portion ingredient row')
            row_metrics = frame.evaluate(detail.METRICS)
            quantity_fonts = row_metrics['detail']['fields'][0]['fonts']
            check(ev, len(quantity_fonts) == 2 and min(quantity_fonts) >= 12,
                  variant+' '+portion+' ingredient name and quantity keep readable fonts', quantity_fonts, True)
            if variant == 'after':
                check(ev, required == '필요 '+expected,
                      portion+' portions shows the expected familiar zucchini quantity', required)
            if portion == '1' and label in SELECTED:
                screenshot = folder/(variant+'-'+label+'.png')
                page.screenshot(path=str(screenshot), animations='disabled')
                ev.setdefault('screenshots', []).append(str(screenshot))
            basis = frame.locator('#tray .recipe-cost-basis')
            center(basis.locator('summary')).click();old.ready(frame)
            basis_row = basis.locator('.recipe-cost-breakdown>div').filter(has_text='애호박')
            basis_quantity = basis_row.locator('dt>small').first.inner_text()
            readable(ev, basis_row, variant+' '+portion+' portion actual cost-basis row')
            if variant == 'after':
                check(ev, basis_quantity == '사용량 '+expected,
                      portion+' portions uses the same readable quantity in its actual price basis', basis_quantity)
            center(frame.locator('#recipePortions')).focus();old.ready(frame)
            metrics = frame.evaluate(detail.METRICS)
            detail.target(ev, metrics['detail']['portion'], variant+' '+portion+' focused serving input')
            for action in metrics['detail']['actions']:
                detail.target(ev, action['control'], variant+' '+portion+' '+action['route'])
            check(ev, metrics['detail']['cost']['total'] == model['cost']['total'],
                  variant+' '+portion+' displayed raw cost still equals the unchanged model arithmetic',
                  {'display_raw':metrics['detail']['cost']['total'],'model_raw':model['cost']['total']})
            frame.locator('#tray [data-recipe-tab=nutrition]').click();old.ready(frame)
            stock = frame.locator('#tray .recipe-stock-details')
            center(stock.locator('summary')).click();old.ready(frame)
            table_row = stock.locator('tbody>tr').filter(has_text='애호박')
            stock_required = table_row.locator('td').nth(1).inner_text().splitlines()[0]
            shortage = table_row.locator('td').nth(2).inner_text()
            readable(ev, table_row, variant+' '+portion+' portion stock-detail row')
            if variant == 'after':
                check(ev, stock_required == expected and '부족 '+expected in shortage,
                      portion+' portions retains readable required and missing quantities in nutrition stock details',
                      {'required':stock_required,'shortage':shortage})
                check(ev, not re.search(r'\d+\.\d{5,}', required+' '+basis_quantity+' '+table_row.inner_text()),
                      portion+' portions does not leak the six-decimal internal quantity through any tested text path')
            check(ev, old.state(frame) == initial,
                  variant+' '+portion+' display controls preserve exact raw storage and envelope')
            result['states'][portion] = {'model':model, 'required_text':required,
                                          'basis_quantity':basis_quantity,
                                          'stock_required':stock_required,'shortage':shortage}
        result['final_state'] = old.state(frame)
    finally:
        if context:context.close()
    return result


def profile(browser, before_origin, after_origin, entry, width, height, kind, folder):
    label = kind+'-'+str(width)+'x'+str(height)
    ev = {'id':label,'checks':[],'page_errors':[],'blocked_requests':[],
          'reference_checks_required':True}
    try:
        before = delivery(browser,before_origin,entry,width,height,label,'before',folder,ev)
        after = delivery(browser,after_origin,entry,width,height,label,'after',folder,ev)
        ev['before'], ev['after'] = before, after
        check(ev, before['initial_state'] == after['initial_state'] and before['shell'] == after['shell'],
              'Before/after share the exact Nov10 default stock, stored envelope and frame')
        for portion, _ in PORTIONS:
            check(ev, before['states'][portion]['model'] == after['states'][portion]['model'],
                  portion+' portions retains exact stock, raw availability requirements, shortages and reference prices')
        check(ev, before['final_state'] == before['initial_state']
              and after['final_state'] == after['initial_state'],
              'Every portion, tab and disclosure action is readonly in both frozen deliveries')
        first = before['states']['1']['required_text']
        check(ev, first == '필요 0.333333개', 'The actual reported decimal bug is reproduced in the before candidate', first)
    except Exception as error:
        old.Audit(ev).caught(error);ev['traceback'] = traceback.format_exc()
    check(ev, not ev['page_errors'], 'No browser JavaScript errors', ev['page_errors'])
    check(ev, not ev['blocked_requests'], 'No external or personal-data request', ev['blocked_requests'])
    return old.finish_case(ev)


def hashes(root):
    return {name:{'bytes':(root/name).stat().st_size,'sha256':old.digest((root/name).read_bytes())}
            for name in closed.DELIVERIES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser-executable',default='/usr/bin/chromium')
    args = parser.parse_args()
    before, root, out = args.before.resolve(), args.root.resolve(), args.output.resolve()
    if out.is_relative_to(REPO) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (before,root)):
        parser.error('Evidence must be outside the checkout and frozen input trees.')
    out.mkdir(parents=True,exist_ok=False);screens=out/'screens';screens.mkdir()
    original = {'before':hashes(before),'after':hashes(root)}
    sources = {p:old.digest((REPO/'scripts'/p).read_bytes())for p in SOURCES}
    shutil.copyfile(Path(__file__),out/'executed-test-source.py')
    old.CLOCK = detail.CLOCK
    report = {'scope':'Frozen local Chromium only; disposable default storage, real portion/disclosure controls',
              'clock':detail.CLOCK.isoformat(),'inputs':original,'verification_sources':sources,
              'cases':[],'passed':False,
              'manual_review':'Inspect the selected actual PNG pairs separately; no physical-device or live Notion claim.'}
    before_server,before_origin=closed.serve(before)
    after_server,after_origin=closed.serve(root)
    def save(case=None):
        if case:
            report['cases'].append(case)
            print(json.dumps({'id':case['id'],'passed':case['passed'],
                              'failed':[c['name']for c in case['checks']if not c['passed']]},ensure_ascii=False),flush=True)
        (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    try:
        with sync_playwright()as p:
            browser=p.chromium.launch(executable_path=args.browser_executable,args=['--no-sandbox'])
            for kind,entry,width,height in PROFILES:
                save(profile(browser,before_origin,after_origin,entry,width,height,kind,screens))
            browser.close()
    finally:
        before_server.shutdown();after_server.shutdown()
    report.update(complete=len(report['cases'])==8,
                  assertions=sum(len(c['checks'])for c in report['cases']),
                  inputs_unchanged=original=={'before':hashes(before),'after':hashes(root)},
                  verification_sources_unchanged=sources=={p:old.digest((REPO/'scripts'/p).read_bytes())for p in SOURCES},
                  delivery_under_1MiB=all(x['bytes']<=1048576 for inputs in original.values()for x in inputs.values()))
    report['passed']=all(report[k]for k in ('complete','inputs_unchanged','verification_sources_unchanged','delivery_under_1MiB'))and all(c['passed']for c in report['cases'])
    save();print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'assertions':report['assertions']}))
    raise SystemExit(0 if report['passed']else 1)


if __name__ == '__main__':main()
