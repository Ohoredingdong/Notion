#!/usr/bin/env python3
"""Exercise the neutral open-fridge preview; no production records or live services."""
import argparse, json, functools, threading, traceback, base64
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from datetime import datetime
from html import escape
from playwright.sync_api import sync_playwright, expect

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); root=args.root.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if out.is_relative_to(Path(__file__).resolve().parents[1]):raise SystemExit('Keep browser output outside checkout')
    report={'scope':'Local Chromium; new preview only; photo OCR and live nutrition are not connected','passed':[],'failures':[]}
    def passed(name):report['passed'].append(name);print('PASS '+name,flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    errors=[]
    with sync_playwright() as p:
      browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
      def new(mode='app',width=390,height=844,opaque=False,init=None,motion='reduce',touch=False):
        ctx=browser.new_context(viewport={'width':width,'height':height},timezone_id='Asia/Seoul',reduced_motion=motion,has_touch=touch,is_mobile=touch)
        page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.clock.install(time=datetime.fromisoformat('2026-10-31T03:00:00+00:00'))
        if init:page.add_init_script(init)
        url=origin+f'/miniature-kitchen-{mode}.html'
        if opaque:
          source=(root/f'miniature-kitchen-{mode}.html').read_text()
          page.set_content('<style>html,body{margin:0}iframe{border:0;width:100vw;height:100vh}</style><iframe sandbox="allow-scripts" srcdoc="'+escape(source,quote=True)+'"></iframe>')
          frame=page.frames[1]
        else:page.goto(url);frame=page
        frame.wait_for_function('window.MiniKitchen && window.KitchenJournal && window.KitchenWorkflows')
        return ctx,page,frame
      def show(frame,name):
        frame.evaluate('(name)=>KitchenWorkflows.show(name)',name)
        expect(frame.locator('#tray')).to_be_visible()
      def stock(frame,item='egg'):
        return frame.evaluate('(id)=>MiniKitchen.exportWorld().items.find(i=>i.id===id).quantity',item)
      try:
        for mode,width,height,opaque in [('app',390,844,False),('app',320,568,False),('app',649,900,False),('app',1120,1000,False),('widget',390,844,False),('widget',320,660,False),('app',390,844,True),('widget',390,844,True)]:
          touch=opaque
          ctx,page,f=new(mode,width,height,opaque,touch=touch)
          assert not f.evaluate('document.documentElement.scrollWidth>innerWidth')
          assert f.locator('.door').count()==4
          assert f.locator('[data-balance]').count()==3
          assert all(f.evaluate('MiniKitchen.getSnapshot().doors').values())
          show(f,'settings');expect(f.locator('[data-wf-form="targets"]')).to_be_visible()
          if opaque:assert f.evaluate('KitchenJournal.status')=='temporary'
          f.evaluate('MiniKitchen.closeTray()')
          # Actual door-surface gesture, away from the separately interactive condiment.
          door=f.locator('[data-door="freshLeft"]');box=door.bounding_box()
          (page.touchscreen.tap if touch else page.mouse.click)(box['x']+box['width']*.12,box['y']+box['height']*.12)
          f.wait_for_function('MiniKitchen.getSnapshot().doors.freshLeft===false')
          (door.tap if touch else door.click)();f.wait_for_function('MiniKitchen.getSnapshot().doors.freshLeft===true')
          page.screenshot(path=str(out/(f'{mode}-{width}-'+('opaque' if opaque else 'native')+'.png')),full_page=True)
          passed(f'layout and real door gestures {mode} {width}x{height} '+('opaque touch' if opaque else 'native mouse'))
          ctx.close()
        # The first animated frame must keep food occluded by the front door.
        ctx,page,f=new(motion='no-preference')
        f.evaluate('''()=>{const w=MiniKitchen.exportWorld();w.doors.freshLeft=false;MiniKitchen.restoreWorld(w)}''')
        f.locator('[data-door="freshLeft"]').evaluate('e=>e.click()')
        sample=f.evaluate('''()=>{const d=document.querySelector('[data-door="freshLeft"]');for(const a of d.getAnimations()){a.pause();a.currentTime=0;}const r=document.querySelector('[data-item="egg"]').getBoundingClientRect();const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {door:hit?.closest('[data-door]')?.dataset.door,item:hit?.closest('[data-item]')?.dataset.item};}''')
        assert sample['door']=='freshLeft' and sample['item'] is None,sample
        f.locator('[data-door="freshLeft"]').evaluate('e=>e.getAnimations().forEach(a=>a.finish())')
        passed('opening identity frame occludes ingredients');ctx.close()
        # Complete connected task flow with real form interactions and real storage.
        ctx,page,f=new()
        original_keys=['use-me-first-state-v5','use-me-first-v4','use-me-first-life-v1','use-me-first-kitchen-view-v1','umf-seasoning-layout-v3']
        f.evaluate('(keys)=>keys.forEach(k=>localStorage.setItem(k,"SENTINEL-"+k))',original_keys)
        f.locator('[data-item="egg"]').click()
        f.locator('#ingredientForm [name="quantity"]').fill('8개');f.locator('#ingredientForm [name="expiry"]').fill('2026-11-02');f.locator('#ingredientForm [type="submit"]').click()
        assert stock(f)=='8개';passed('ingredient quantity and original expiry explicitly editable')
        # Native drag to a different actual shelf.
        source=f.locator('[data-item="egg"]').bounding_box();target=f.locator('.fridge-interiors [data-zone="freshRight"]').bounding_box()
        page.mouse.move(source['x']+source['width']/2,source['y']+source['height']/2);page.mouse.down();page.mouse.move(target['x']+target['width']*.5,target['y']+target['height']*.75,steps=16);page.mouse.up()
        assert f.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="egg").zone')=='freshRight';passed('ingredient drag across cold compartments')
        f.locator('[data-item="spice0"]').click();f.locator('#ingredientForm [name="expiry"]').fill('2027-03-01');f.locator('#ingredientForm [name="opened"]').fill('2026-10-31');f.locator('#ingredientForm [type="submit"]').click()
        spice=f.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="spice0")');assert spice['expiry']=='2027-03-01' and spice['opened']=='2026-10-31';passed('condiment expiry and opening date persist')
        show(f,'settings');form=f.locator('[data-wf-form="targets"]')
        for name,value in [('carb','230'),('protein','70'),('fat','60'),('calcium','700')]:form.locator(f'[name="{name}"]').fill(value)
        form.locator('[type="submit"]').click();assert f.evaluate('KitchenJournal.getSnapshot().targets.carb')==230
        f.evaluate('KitchenWorkflows.show("recipes")');f.locator('#tray [data-wf="recipe"][data-arg="recipe-1"]').click();f.locator('[data-wf="recipeFacts"]').click()
        form=f.locator('[data-wf-form="facts"]')
        for name,value in [('kcal','458'),('carb','65'),('protein','18'),('fat','14'),('cost','2300'),('calcium','30')]:form.locator(f'[name="{name}"]').fill(value)
        form.locator('[name="source"]').fill('검사용 직접 입력 · 1회분');form.locator('[type="submit"]').click();passed('recipe nutrition/cost are explicit inputs, not fabricated data')
        f.locator('[data-wf="logMeal"]').click();form=f.locator('[data-wf-form="meal"]')
        form.locator('[name="portions"]').fill('0.5');form.locator('[name="portions"]').dispatch_event('change');assert form.locator('[name="calcium"]').input_value()=='15'
        form.locator('[name="portions"]').fill('1');form.locator('[name="portions"]').dispatch_event('change');assert form.locator('[name="calcium"]').input_value()=='30'
        form.locator('[name="qty0"]').fill('2개');form.locator('[type="submit"]').click()
        assert stock(f)=='6개';assert f.evaluate('KitchenJournal.summary("2026-10-31").nutrients.carb.value')==65
        assert f.evaluate('KitchenJournal.getWorkflow().extraNutrients[KitchenJournal.getSnapshot().meals[0].id].calcium')==30
        passed('meal commit updates entered nutrition, micronutrients and confirmed inventory atomically')
        f.locator('[data-remove-meal]').click();f.locator('[data-wf="confirmCancelMeal"]').click();assert stock(f)=='8개';assert f.evaluate('KitchenJournal.getSnapshot().meals.length')==0
        f.locator('[data-undo-meal]').click();assert stock(f)=='6개';assert f.evaluate('KitchenJournal.getSnapshot().meals.length')==1;assert f.evaluate('KitchenJournal.getSnapshot().awarded.length')==1;passed('meal cancellation and restore include stock, nutrition and no reward farming')
        f.locator('[data-wf="editMeal"]').click();form=f.locator('[data-wf-form="meal"]');assert form.locator('[name="qty0"]').input_value()=='2개';form.locator('[name="qty0"]').fill('3개');form.locator('[name="protein"]').fill('20');form.locator('[type="submit"]').click()
        assert stock(f)=='5개';assert f.evaluate('KitchenJournal.summary("2026-10-31").nutrients.protein.value')==20;passed('meal edits reverse only the old transaction before applying new use')
        before=f.evaluate('KitchenJournal.getEnvelope()');f.locator('[data-wf="editMeal"]').click();form=f.locator('[data-wf-form="meal"]');form.locator('[name="qty0"]').fill('99개');form.locator('[type="submit"]').click();assert f.evaluate('KitchenJournal.getEnvelope()')==before;passed('insufficient-stock meal edits leave all records unchanged')
        show(f,'plan');form=f.locator('[data-wf-form="plan"]');form.locator('[type="submit"]').click();assert stock(f)=='5개';assert f.evaluate('KitchenJournal.getSnapshot().meals.length')==1;passed('meal planning does not consume stock or add spending')
        show(f,'shopping');form=f.locator('[data-wf-form="shopping"]');form.locator('[name="name"]').fill('양파');form.locator('[name="quantity"]').fill('1개');form.locator('[name="estimate"]').fill('600');form.locator('[type="submit"]').click()
        f.locator('[data-wf="purchase"]').click();form=f.locator('[data-wf-form="purchase"]');form.locator('[name="paid"]').fill('700');form.locator('[name="expiry"]').fill('2026-11-10');form.locator('[type="submit"]').click()
        assert f.evaluate('KitchenJournal.getWorkflow().expenses[0].amount')==700
        assert f.evaluate('MiniKitchen.exportWorld().items.some(i=>i.name==="양파"&&i.quantity==="1개"&&i.expiry==="2026-11-10")')
        show(f,'budget');form=f.locator('[data-wf-form="budget"]');form.locator('[name="budget"]').fill('400000');form.locator('[type="submit"]').click();assert f.evaluate('KitchenJournal.getWorkflow().expenses.length')==1;passed('shopping purchase separately confirms real expense and dated inventory without double counting')
        f.locator('[data-wf="editExpense"]').click();form=f.locator('[data-wf-form="editExpense"]');form.locator('[name="amount"]').fill('900');form.locator('[type="submit"]').click();assert f.evaluate('KitchenJournal.getWorkflow().expenses[0].amount')==900;passed('cash expense can be corrected independently of inventory')
        show(f,'supplements');form=f.locator('[data-wf-form="supplement"]');form.locator('[name="name"]').fill('내 비타민');form.locator('[name="amount"]').fill('제품 표시량');form.locator('[name="schedule"]').fill('내 일정');form.locator('[name="ingredients"]').fill('비타민D');form.locator('[type="submit"]').click();f.locator('[data-supplement-check]').check();assert f.evaluate('KitchenJournal.getWorkflow().supplements[0].days')==['2026-10-31'];passed('supplement schedule and selected-day checks are stored without inferred dosage')
        f.locator('[data-wf="editSupplement"]').click();form=f.locator('[data-wf-form="editSupplement"]');form.locator('[name="remaining"]').fill('29정');form.locator('[type="submit"]').click();assert f.evaluate('KitchenJournal.getWorkflow().supplements[0].days')==['2026-10-31'];assert f.evaluate('KitchenJournal.getWorkflow().supplements[0].remaining')=='29정'
        show(f,'monthly');expect(f.locator('.workflow-month')).to_be_visible();assert f.locator('.workflow-month>div').count()==31;passed('monthly calendar uses actual month and recorded data')
        # Real local image decoding/compression, paired-photo review and explicit manual registration.
        show(f,'photos');assert f.locator('[data-photo]').count()==2;expect(f.locator('button:disabled')).to_contain_text('연결 전')
        image_bytes=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jrGQAAAAASUVORK5CYII=')
        for slot in ['product','expiry']:
          f.locator(f'[data-photo="{slot}"]').set_input_files({'name':slot+'.png','mimeType':'image/png','buffer':image_bytes})
          expect(f.locator(f'img[alt="선택한 {"제품 사진" if slot=="product" else "기한 사진"}"]')).to_be_visible()
        f.locator('[data-wf="manualAdd"]').click();form=f.locator('[data-wf-form="add"]');form.locator('[name="name"]').fill('사진 확인 재료');form.locator('[name="quantity"]').fill('250g');form.locator('[name="expiry"]').fill('2026-11-12');form.locator('[name="picture"]').select_option('photo');form.locator('[type="submit"]').click()
        photo_item=f.evaluate('MiniKitchen.exportWorld().items.find(i=>i.name==="사진 확인 재료")');assert photo_item['expiry']=='2026-11-12' and photo_item['photo'].startswith('data:image/jpeg;base64,') and photo_item['expiryPhoto'].startswith('data:image/jpeg;base64,')
        passed('two local photos require manual confirmation and can create a dated stock item with a compressed product photo')
        # Save, reload, and verify native persistence plus preservation of original app keys.
        f.evaluate('MiniKitchen.closeTray()');snapshot=f.evaluate('KitchenJournal.getEnvelope()');page.reload();f.wait_for_function('window.KitchenWorkflows');assert f.evaluate('KitchenJournal.getEnvelope()')==snapshot
        assert f.evaluate('(keys)=>keys.every(k=>localStorage.getItem(k)==="SENTINEL-"+k)',original_keys);passed('native reload preserves records and leaves all original app keys unchanged')
        show(f,'settings');raw=f.locator('#journalExport').input_value();assert json.loads(raw)==snapshot
        form=f.locator('[data-wf-form="import"]');form.locator('[name="backup"]').fill('{bad');form.locator('[type="submit"]').click();assert f.evaluate('KitchenJournal.getEnvelope()')==snapshot
        modified=json.loads(raw);modified['world']['items'][0]['quantity']='9개';form.locator('[name="backup"]').fill(json.dumps(modified));form.locator('[type="submit"]').click();assert f.evaluate('KitchenJournal.getEnvelope()')==snapshot
        f.locator('[data-wf="confirmImport"]').click();assert stock(f)=='9개';assert f.evaluate('JSON.parse(localStorage.getItem(KitchenJournal.storageKey+"-recovery"))')==snapshot
        passed('backup import previews changes, rejects malformed data and preserves pre-import raw recovery')
        page.screenshot(path=str(out/'app-connected-settings.png'),full_page=True);ctx.close()
        # Legacy version-1 envelope has no workflow field; dates/positions must survive.
        legacy_world=json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/miniature-legacy-world-v1.json').read_text())
        legacy_world['items'][0]['expiry']='2000-01-01';legacy_world['items'][0]['quantity']='125ml'
        legacy_play={'version':1,'meals':[],'targets':{k:None for k in ['kcal','carb','protein','fat','fiber','water']},'discovered':[],'awarded':[],'owned':[],'equipped':{'frozenLeft':None,'frozenRight':None},'goal':'collection','plateLabel':'우리 집 부엌'}
        raw=json.dumps({'version':1,'world':legacy_world,'play':legacy_play},ensure_ascii=False)
        ctx,page,f=new(init='localStorage.setItem("miniature-kitchen-preview-v1",'+json.dumps(raw)+')')
        assert f.evaluate('MiniKitchen.exportWorld()')==legacy_world;assert f.evaluate('KitchenJournal.getSnapshot()')==legacy_play
        passed('legacy envelope reads without date refresh or coordinate changes');ctx.close()
        assert not errors,errors
        passed('no JavaScript exceptions in any exercised context')
      except Exception as e:
        report['failures'].append({'message':str(e),'trace':traceback.format_exc()})
        try:page.screenshot(path=str(out/'failure.png'),full_page=True)
        except Exception:pass
        raise
      finally:
        report['javascript_errors']=errors;(out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        browser.close();server.shutdown()
    print(json.dumps({'passed':len(report['passed']),'failed':len(report['failures'])}))
if __name__=='__main__':main()
