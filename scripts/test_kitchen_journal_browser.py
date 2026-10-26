#!/usr/bin/env python3
"""Exercise sharp LCDs, preview persistence and the manual nutrition/collection/reward loop."""
import argparse,functools,http.server,json,threading,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_fridge_four_door_browser import QuietHandler

KEY='miniature-kitchen-preview-v1'
SEED="""(() => {const get=Storage.prototype.getItem,set=Storage.prototype.setItem;const keys=['use-me-first-state-v5','use-me-first-kitchen-view-v1','umf-seasoning-layout-v3','use-me-first-life-v1'];for(const k of keys)set.call(localStorage,k,' ORIGINAL '+k+' ');window.__original=()=>keys.map(k=>get.call(localStorage,k));window.__access=[];for(const method of ['getItem','setItem','removeItem','clear']){const fn=Storage.prototype[method];Storage.prototype[method]=function(...args){__access.push({method,key:args[0]});return fn.apply(this,args)}}})();"""

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(args.root.resolve())));threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
 result={'scope':'Local Chromium; manual values; separate preview key; no real nutrition provider or production writes','cases':[],'errors':[]}
 def passed(label):result['cases'].append(label);print('PASS '+label,flush=True)
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
   for mode,width in [('app',649),('widget',390)]:
    ctx=browser.new_context(viewport={'width':width,'height':900},device_scale_factor=2,has_touch=True,reduced_motion='reduce',timezone_id='Asia/Seoul');page=ctx.new_page();page.set_default_timeout(10000);page.add_init_script(SEED);errors=[];external=[];page.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
     if r.request.url.startswith(origin) and r.request.resource_type=='document':r.continue_()
     else:external.append(r.request.url);r.abort()
    page.route('**/*',route);page.clock.set_fixed_time('2026-10-26T03:00:00Z');label=f'{mode}-{width}'
    try:
     page.goto(f'{origin}/miniature-kitchen-{mode}.html',wait_until='networkidle');page.wait_for_function('window.KitchenJournal');original=page.evaluate('__original()')
     assert page.evaluate('KitchenJournal.status')=='saved'
     assert page.locator('.door-controls').count()==0
     page.locator('[data-door="freshLeft"]').click()
     expect(page.locator('[data-lcd="freshLeft"]')).to_be_visible()
     info=page.locator('[data-lcd="freshLeft"]').evaluate("""e=>{const chain=[];for(let n=e;n;n=n.parentElement)chain.push({transform:getComputedStyle(n).transform,filter:getComputedStyle(n).filter});return {chain,font:parseFloat(getComputedStyle(e.querySelector('.lcd-row b')).fontSize),bounds:[e.getBoundingClientRect().x,e.getBoundingClientRect().y,e.getBoundingClientRect().width,e.getBoundingClientRect().height]}}""")
     assert all(x['transform']=='none' and x['filter']=='none' for x in info['chain']),info
     assert info['font']>=11 and all(abs(x-round(x))<.01 for x in info['bounds']),info
     page.screenshot(path=str(out/f'{label}-sharp-closed.png'))
     for key in ['freshLeft','freshRight','frozenLeft','frozenRight']:
      door=page.locator(f'[data-door="{key}"]');before=door.get_attribute('aria-expanded');door.tap() if mode=='widget' else door.click();assert door.get_attribute('aria-expanded')!=before;door.tap() if mode=='widget' else door.click();assert door.get_attribute('aria-expanded')==before
     passed(label+': pixel-aligned native-size LCD text and direct mouse/touch door toggle, with no bottom door buttons')
     page.locator('#openJournal').click();expect(page.locator('[data-nutrient="protein"] strong')).to_have_text('미입력')
     page.locator('summary').click();page.locator('#targetsForm [name="protein"]').fill('40');page.locator('#targetsForm [name="kcal"]').fill('2000');page.locator('#targetsForm [type="submit"]').click()
     page.locator('[data-journal="book"]').click();expect(page.locator('.book-card')).to_have_count(8);page.locator('[data-book-recipe="recipe-1"]').click();page.locator('[data-log="recipe-1"]').click()
     for key,value in {'protein':'25','carb':'50','fat':'10','kcal':'400','fiber':'3'}.items():page.locator(f'#mealForm [name="{key}"]').fill(value)
     page.locator('#mealForm [name="portion"]').fill('1인분');page.locator('#mealForm [type="submit"]').click()
     report=page.evaluate("KitchenJournal.summary('2026-10-26')");assert report['tickets']==1 and report['cooked']==['recipe-1'];assert report['nutrients']['protein']['value']==25 and report['nutrients']['protein']['percent']==62.5 and report['nutrients']['water']['value'] is None
     page.screenshot(path=str(out/f'{label}-nutrition.png'),full_page=True)
     page.locator('[data-log]').click();page.locator('#mealForm [name="recipeId"]').select_option('recipe-1');page.locator('#mealForm [name="protein"]').fill('10');page.locator('#mealForm [type="submit"]').click()
     assert page.evaluate("KitchenJournal.summary('2026-10-26').tickets")==1
     assert page.evaluate("KitchenJournal.summary('2026-10-26').nutrients.protein.value")==35
     page.locator('[data-remove-meal]').last.click();assert page.evaluate("KitchenJournal.summary('2026-10-26').nutrients.protein.value")==25
     page.locator('[data-undo-meal]').click();assert page.evaluate("KitchenJournal.summary('2026-10-26').nutrients.protein.value")==35
     page.locator('[data-remove-meal]').last.click()
     passed(label+': manual nutrition totals, missing values, user targets, first recipe unlock and one-time reward; meal cancel/undo recalculates')
     page.locator('[data-journal="book"]').click();expect(page.locator('[data-book-recipe="recipe-1"]')).to_have_class('book-card is-cooked');page.screenshot(path=str(out/f'{label}-book.png'),full_page=True)
     page.locator('[data-journal="rewards"]').click();assert page.locator('[data-reward="daisy"]').is_disabled();page.locator('#rewardSlot').select_option('frozenRight');page.locator('[data-reward="tile"]').click()
     leakage=page.locator('.reward-art .magnet-art').evaluate_all("""async nodes=>{const values=[];for(const node of nodes){const svg=node.cloneNode(true);svg.setAttribute('width','240');svg.setAttribute('height','100');const image=new Image();image.src='data:image/svg+xml;base64,'+btoa(new XMLSerializer().serializeToString(svg));await image.decode();const canvas=document.createElement('canvas');canvas.width=240;canvas.height=100;const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);const data=ctx.getImageData(0,0,240,100).data;let outside=0,inside=0;for(let y=0;y<100;y++)for(let x=0;x<240;x++)if(data[(y*240+x)*4+3]>10){if(x<60||x>180)outside++;else inside++;}values.push({outside,inside});}return values}""")
     assert len(leakage)==3 and all(x['outside']==0 and x['inside']>100 for x in leakage),leakage
     passed(label+': each cosmetic sprite is clipped to its own cell without neighboring artwork')
     state=page.evaluate('KitchenJournal.getSnapshot()');assert state['owned']==['tile'] and state['equipped']['frozenRight']=='tile';assert page.evaluate('KitchenJournal.summary().tickets')==0
     page.screenshot(path=str(out/f'{label}-rewards.png'),full_page=True);page.locator('[data-see-fridge]').click();expect(page.locator('[data-charm="tile"]')).to_be_visible()
     page.locator('[data-door="frozenRight"]').click();expect(page.locator('[data-charm="tile"]')).to_have_count(0);page.locator('[data-door="frozenRight"]').click();expect(page.locator('[data-charm="tile"]')).to_be_visible();page.screenshot(path=str(out/f'{label}-equipped.png'))
     passed(label+': earned cosmetic selection, insufficient-ticket gate and visible fridge magnet hide/show with its door')
     saved=page.evaluate('KitchenJournal.getSnapshot()');world=page.evaluate('MiniKitchen.exportWorld()');page.reload(wait_until='networkidle');page.wait_for_function('window.KitchenJournal');assert page.evaluate('KitchenJournal.getSnapshot()')==saved;assert page.evaluate('MiniKitchen.exportWorld()')==world
     page.locator('#openJournal').click();page.locator('[data-journal="backup"]').click();exported=page.locator('#journalExport').input_value();assert json.loads(exported)['play']==saved
     page.locator('[data-journal="book"]').click();page.locator('#journalGoal').select_option('recording');page.locator('[data-journal="backup"]').click();page.locator('#importForm textarea').fill(exported);page.locator('#importForm [type="submit"]').click();assert page.evaluate('KitchenJournal.getSnapshot()')==saved;page.locator('#closeTray').click()
     assert page.evaluate('__original()')==original and not page.evaluate(f"__access.some(e=>e.key!=='{KEY}'||!['getItem','setItem'].includes(e.method))")
     assert not errors and not external,(errors,external)
     other=ctx.new_page();other.clock.set_fixed_time('2026-10-26T03:00:00Z');other.goto(f'{origin}/miniature-kitchen-widget.html',wait_until='networkidle');other.wait_for_function('window.KitchenJournal');assert other.evaluate('KitchenJournal.getSnapshot()')==saved
     other.locator('#openJournal').click();other.locator('[data-journal="book"]').click();other.locator('#journalGoal').select_option('recording');other.wait_for_function('KitchenJournal.getSnapshot().goal === "recording"');page.wait_for_function('KitchenJournal.status === "conflict"')
     remote=other.evaluate(f'localStorage.getItem("{KEY}")');page.locator('[data-door="freshLeft"]').click();assert other.evaluate(f'localStorage.getItem("{KEY}")')==remote
     passed(label+': separate preview persistence, same-origin app/widget read and stale-write protection; all production keys preserved')
    except Exception as e:result['errors'].append(label+': '+str(e));traceback.print_exc();page.screenshot(path=str(out/f'failure-{label}.png'),full_page=True)
    finally:ctx.close()
   for scenario in ['opaque','corrupt','quota']:
    ctx=browser.new_context(viewport={'width':390,'height':900},reduced_motion='reduce');page=ctx.new_page();page.set_default_timeout(10000)
    try:
     if scenario=='opaque':
      page.goto(origin+'/miniature-kitchen-board.html',wait_until='networkidle');frame=page.frames[1];frame.wait_for_function('window.KitchenJournal');assert frame.evaluate('KitchenJournal.status')=='temporary';frame.locator('#openJournal').click();frame.locator('[data-journal="backup"]').click();assert json.loads(frame.locator('#journalExport').input_value())['version']==1
     else:
      page.add_init_script(SEED)
      if scenario=='corrupt':page.add_init_script(f"localStorage.setItem('{KEY}','KEEP CORRUPT ORIGINAL');")
      else:page.add_init_script(f"(() => {{const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){{if(k==='{KEY}')throw new DOMException('quota','QuotaExceededError');return set.call(this,k,v);}}}})();")
      page.goto(origin+'/miniature-kitchen-app.html',wait_until='networkidle');page.wait_for_function('window.KitchenJournal');page.locator('[data-door="freshLeft"]').click();assert page.evaluate('KitchenJournal.status')==('blocked' if scenario=='corrupt' else 'temporary')
      if scenario=='corrupt':assert page.evaluate(f'localStorage.getItem("{KEY}")')=='KEEP CORRUPT ORIGINAL'
      page.locator('#openJournal').click();page.locator('[data-journal="backup"]').click();before=page.evaluate('MiniKitchen.exportWorld()');page.locator('#importForm textarea').fill('{"version":1,"world":{},"play":{}}');page.locator('#importForm [type="submit"]').click();assert page.evaluate('MiniKitchen.exportWorld()')==before
      bad=json.loads(page.locator('#journalExport').input_value());bad['world']['items'][0]['id']='bad" onfocus=alert(1) x="';page.locator('#importForm textarea').fill(json.dumps(bad));page.locator('#importForm [type="submit"]').click();assert page.evaluate('MiniKitchen.exportWorld()')==before
     passed(scenario+': clear fallback status, valid export and preservation on unavailable, corrupt or failing storage')
    except Exception as e:result['errors'].append(scenario+': '+str(e));traceback.print_exc()
    finally:ctx.close()
   browser.close()
 finally:server.shutdown()
 result['passed']=not result['errors'];result['passed_cases']=len(result['cases']);(out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
