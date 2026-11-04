"""Pinned delivery and view-only smoke of the actual full-flow application."""
import argparse,ast,base64,copy,hashlib,html,importlib.util,json,os,re,shutil,struct,subprocess,tempfile,traceback
from functools import lru_cache
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
OUT=Path('/tmp/kitchen-fridge-redo-public');RESULT_BRANCH='preview/kitchen-fridge-redo-20261104'
PROFILES=[('small-phone',320,568),('phone',390,844),('user-size',801,782)]
def git(*args,env=None):return subprocess.run(['git',*args],env=env,check=True,capture_output=True).stdout
@lru_cache(maxsize=64)
def source_bytes(source,path):return git('show',source+':'+path)
def source_read(source,path,local=False):return (Path('/workspace/Notion')/path).read_bytes()if local else source_bytes(source,path)
def contract(native,source,local=False):
 paths=[Path(__file__).with_name('build_miniature_kitchen_preview.py'),Path('/workspace/Notion/scripts/build_miniature_kitchen_preview.py')];path=next(p for p in paths if p.is_file());spec=importlib.util.spec_from_file_location('release_builder',path);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);original=b.unpack_document(native.decode());scripts=re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>',original);styles=re.findall(r'<style(?:\s[^>]*)?>([\s\S]*?)</style>',original)
 template=source_read(source,'designs/miniature-kitchen/scene.html',local).decode();expected_scripts=len(re.findall(r'<script defer src=',template));expected_styles=len(re.findall(r'<link rel="stylesheet"',template));assert len(scripts)==expected_scripts and len(styles)==expected_styles,(len(scripts),expected_scripts,len(styles),expected_styles)
 tree=ast.parse(source_read(source,'scripts/build_miniature_kitchen_preview.py',local).decode());variants=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='COMPACT_AVIF'for t in n.targets));assets=[]
 for png,avif in variants.items():
  data=source_read(source,avif,local);url='data:image/avif;base64,'+base64.b64encode(data).decode();assert url in original,'Missing final source asset '+avif;raw=source_read(source,png,local);assert raw[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',raw[16:24]);assets.append({'url':url,'file':avif,'sha256':hashlib.sha256(data).hexdigest(),'width':w,'height':h})
 return {'scripts':scripts,'styles':styles,'assets':assets,'decoded_sha256':hashlib.sha256(original.encode()).hexdigest(),'script_count':expected_scripts,'style_count':expected_styles}
def painted(node):
 return node.evaluate('''e=>{const r=e.getBoundingClientRect();for(const fy of [.5,.2,.8,.1,.9])for(const fx of [.5,.2,.8,.1,.9]){const x=r.x+r.width*fx,y=r.y+r.height*fy;if(x>=0&&y>=0&&x<innerWidth&&y<innerHeight&&document.elementFromPoint(x,y)?.closest('button')===e)return {x,y};}return null;}''')
def click(page,frame,selector,touch=False):
 nodes=frame.locator(selector)
 for index in range(nodes.count()):
  node=nodes.nth(index)
  if not node.is_visible():continue
  point=painted(node)
  if point:
   offset=frame.frame_element().bounding_box();(page.touchscreen.tap if touch else page.mouse.click)(point['x']+offset['x'],point['y']+offset['y']);return node
 raise AssertionError('No painted reachable control: '+selector)
def close(page,frame,touch=False):
 for _ in range(8):
  if not frame.locator('#tray').is_visible():return
  click(page,frame,'#closeTray,#tray[open] [data-wf="back"],#tray[open] [data-growth-back]',touch)
 raise AssertionError('Dialog did not close through real visible controls')
def state(frame,id):frame.wait_for_function('id=>document.body.dataset.screenId===id',arg=id)
def bounds(frame):
 d=frame.evaluate('''()=>({width:innerWidth,height:innerHeight,docWidth:document.documentElement.scrollWidth,docHeight:document.documentElement.scrollHeight,x:scrollX,y:scrollY,screen:document.body.dataset.screenId,nav:[...document.querySelectorAll('.home-shortcuts button')].map(e=>{const r=e.getBoundingClientRect();return {id:e.dataset.homeTab,width:r.width,height:r.height,visible:r.width>0&&r.height>0};})})''');assert d['docWidth']<=d['width']+1 and d['x']==0,d;return d
def cap(page,frame,label,screen,rows):
 frame.evaluate('async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));}');rows.append({'screen':screen,'geometry':bounds(frame)});
 if screen in ['A1','A5','D1','D5','D6']:frame.locator('.shell').screenshot(path=str(OUT/(label+'-'+screen+'.png')))
def smoke(page,frame,label,touch,data):
 decoded=frame.evaluate('async rows=>Promise.all(rows.map(async row=>{const image=new Image();image.src=row.url;await image.decode();return {file:row.file,width:image.naturalWidth,height:image.naturalHeight};}))',data['assets']);assert all((a['width'],a['height'])==(b['width'],b['height'])for a,b in zip(decoded,data['assets']));rows=[];before=frame.evaluate('KitchenJournal.getEnvelope()');assert before['version']==1 and frame.evaluate('KitchenJournal.storageKey')=='miniature-kitchen-preview-v1';state(frame,'A1');cap(page,frame,label,'A1',rows)
 nav=frame.locator('.home-shortcuts button').evaluate_all('nodes=>nodes.map(e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height};})');assert len(nav)==4 and all(r['width']>=44 and r['height']>=44 for r in nav),nav;expect(frame.locator('[data-home-tab="meals"]')).to_have_text('레시피')
 click(page,frame,'#addFood',touch);state(frame,'A2');cap(page,frame,label,'A2',rows);click(page,frame,'#tray [data-wf="photos"]',touch);state(frame,'A3');expect(frame.locator('[data-photo="product"]')).to_be_attached();expect(frame.locator('[data-photo="expiry"]')).to_be_attached();assert frame.locator('[data-wf="readPhotos"]').is_disabled();cap(page,frame,label,'A3',rows);close(page,frame,touch);assert frame.evaluate('KitchenJournal.getEnvelope()')==before,'Registration view must not change data'
 click(page,frame,'[data-home-tab="meals"]',touch);state(frame,'B1');cap(page,frame,label,'B1',rows);recipe=frame.locator('#homeRecommendation [data-wf="recipe"]').first;recipe_id=recipe.get_attribute('data-arg');click(page,frame,'#homeRecommendation [data-wf="recipe"]',touch);state(frame,'B2');after=frame.evaluate('KitchenJournal.getEnvelope()');expected=copy.deepcopy(before)
 assert after==before,'Recipe detail view must preserve the entire envelope';before=after;cap(page,frame,label,'B2',rows);click(page,frame,'#tray [data-wf="planRecipe"]',touch);state(frame,'B3');expect(frame.locator('[data-wf-form="plan"]')).to_be_visible();fonts=frame.locator('[data-wf-form="plan"] input,[data-wf-form="plan"] select').evaluate_all('nodes=>nodes.filter(e=>e.getClientRects().length).map(e=>({name:e.name,font:getComputedStyle(e).fontSize}))');cap(page,frame,label,'B3',rows);close(page,frame,touch);assert frame.evaluate('KitchenJournal.getEnvelope()')==before,'Plan view must not save, consume stock, or add a meal'
 click(page,frame,'[data-home-tab="records"]',touch);state(frame,'C1');cap(page,frame,label,'C1',rows);click(page,frame,'[data-home-subtab="monthly"]',touch);state(frame,'C3');cap(page,frame,label,'C3',rows);assert frame.evaluate('KitchenJournal.getEnvelope()')==before,'Record/calendar navigation must retain data'
 click(page,frame,'[data-home-tab="kitchen"]',touch);state(frame,'D1');cap(page,frame,label,'D1',rows);click(page,frame,'#homeGrowth [data-workflow="book"]',touch);state(frame,'D2');cap(page,frame,label,'D2',rows);close(page,frame,touch);click(page,frame,'#homeGrowth [data-home-open="decor"]',touch);state(frame,'D5');cap(page,frame,label,'D5',rows);click(page,frame,'.decor-footer [data-decor-cancel]',touch);state(frame,'D1');assert frame.evaluate('KitchenJournal.getEnvelope()')==before,'Cookbook/decor Cancel must not charge or save';return {'decoded_assets':decoded,'screens':rows,'main_nav_targets':nav,'plan_native_input_fonts':fonts,'exact_data_preserved_on_all_views':True,'scope':'Read-only actual control navigation; no saves, stock changes, rewards, OCR, or synthetic records.'}
def reveal(node):
 details=node.locator('xpath=ancestor::details').all();details=sorted(details,key=lambda d:d.evaluate('e=>{let n=0;for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")n++;return n;}'))
 for d in details:
  if d.get_attribute('open')is None:d.locator('summary').first.click()
 node.scroll_into_view_if_needed()
def room_geometry(frame,screen):
 value=frame.evaluate("""screen=>{const panorama=document.querySelector(screen==='D1'?'#homeGrowth .growth-preview':'.room'),fridge=document.querySelector(screen==='D1'?'#homeGrowth .home-fridge-art':'.room .decor-fridge-backdrop'),p=panorama.getBoundingClientRect(),f=fridge.getBoundingClientRect(),css=getComputedStyle(fridge);return {panorama:{width:p.width,height:p.height},fridge:{width:f.width,height:f.height},widthShare:f.width/p.width,panoramaRatio:p.width/p.height,fridgeRatio:f.width/f.height,visible:css.display!=='none'&&css.visibility!=='hidden'&&Number(css.opacity)>0};}""",screen)
 assert value['visible']and abs(value['panoramaRatio']-2)<.05 and abs(value['widthShare']-.285)<.02 and abs(value['fridgeRatio']-812/1344)<.025,value
 return value
def focused(page,frame,label,touch,data):
 result=smoke(page,frame,label,touch,data);result['read_only_smoke_scope']=result.pop('scope');result['read_only_smoke_exact_envelope']=result.pop('exact_data_preserved_on_all_views');result['scope']='Read-only four-area navigation followed by explicit disposable-context A5 save and D6 Apply rendering. Fixture actions are documented separately.';rows=result['screens'];geometry={'D1':room_geometry(frame,'D1')};click(page,frame,'[data-home-tab="fridge"]',touch);before=frame.evaluate('KitchenJournal.getEnvelope()');milk=next(i for i in before['world']['items']if i['id']=='milk');base_amount=frame.evaluate('q=>KitchenWorkflowModel.parseQuantity(q).baseAmount',milk['quantity'])
 click(page,frame,'#addFood',touch);state(frame,'A2');click(page,frame,'#tray [data-wf="manualAdd"]',touch);state(frame,'A4');form=frame.locator('#addIngredientForm');form.locator('[name="name"]').fill(milk['name']);form.locator('[name="quantity"]').fill('100mL');form.locator('[name="expiry"]').fill(milk['expiry']);opened=form.locator('[name="opened"]');reveal(opened);opened.fill(milk.get('opened',''));form.locator('[name="zone"]').select_option(milk['zone']);merge=form.locator('[name="mergeId"]');expect(merge).to_be_attached();reveal(merge);merge.select_option(milk['id']);save=form.locator('[type="submit"]');reveal(save);save.click();frame.wait_for_function('!document.querySelector("#tray").open');state(frame,'A5');after=frame.evaluate('KitchenJournal.getEnvelope()');updated=next(i for i in after['world']['items']if i['id']=='milk');new_amount=frame.evaluate('q=>KitchenWorkflowModel.parseQuantity(q).baseAmount',updated['quantity']);assert new_amount==base_amount+100 and len(after['world']['items'])==len(before['world']['items']);assert [i for i in after['world']['items']if i['id']!='milk']==[i for i in before['world']['items']if i['id']!='milk'];assert after['play']==before['play']and after['workflow']==before['workflow'];cap(page,frame,label,'A5',rows);frame.wait_for_function('!document.querySelector("#liveMessage").textContent',timeout=6000)
 click(page,frame,'[data-home-tab="kitchen"]',touch);state(frame,'D1');cap(page,frame,label,'D1',rows);geometry['D1']=room_geometry(frame,'D1');click(page,frame,'#homeGrowth [data-home-open="decor"]',touch);state(frame,'D5');click(page,frame,'#decorStage [data-item="cup"]',touch);assert frame.evaluate('KitchenJournal.getEnvelope()')==after;cap(page,frame,label,'D5',rows);geometry['D5']=room_geometry(frame,'D5');click(page,frame,'[data-decor-apply]',touch);state(frame,'D6');applied=frame.evaluate('KitchenJournal.getEnvelope()');assert applied['world']['items']==after['world']['items']and applied['play']==after['play']and applied['workflow']==after['workflow'];assert not any(applied['world']['doors'].values());cap(page,frame,label,'D6',rows);geometry['D6']=room_geometry(frame,'D6');result.update({'focused_panorama_geometry':geometry,'fixture_actions':{'scope':'Isolated opaque browser example only; no actual user storage. A5 is a real native form save, D6 is a real Apply of already-owned scene objects.','A5':{'mergedId':'milk','added':'100mL','before':base_amount,'after':new_amount,'sameStockLotCount':True,'allOtherStockAndPlayFlowUnchanged':True},'D6':{'existingOwnedCupSelected':True,'sameItemsPlayAndFlow':True,'doorsClosed':True}},'element_screenshots':['A1','A5','D1','D5','D6']});return result

def publish_results():
 old=git('ls-remote','--heads','origin','refs/heads/'+RESULT_BRANCH).decode().split()
 if old:git('fetch','--no-write-fetch-head','origin','refs/heads/'+RESULT_BRANCH)
 with tempfile.TemporaryDirectory(prefix='fullflow-result-')as folder:
  env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'));git('read-tree','--empty',env=env)
  for path in OUT.iterdir():
   if path.is_file()and path.suffix in ('.png','.json'):
    blob=git('hash-object','-w',str(path)).decode().strip();git('update-index','--add','--cacheinfo','100644,'+blob+','+path.name,env=env)
  tree=git('write-tree',env=env).decode().strip();parents=['-p',old[0]]if old else[];commit=git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree,*parents,'-m','Record actual fridge redo widget element screenshots').decode().strip();git('push','origin',commit+':refs/heads/'+RESULT_BRANCH);return commit
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--local-root',type=Path);p.add_argument('--publish-results',action='store_true');a=p.parse_args();assert re.fullmatch('[0-9a-f]{40}',a.source);assert not(a.local_root and a.publish_results);OUT.mkdir(exist_ok=True);server=None;run=os.environ.get('GITHUB_RUN_ID');result={'source':a.source,'verifier_commit':os.environ.get('GITHUB_SHA'),'run_url':f'https://github.com/Ohoredingdong/Notion/actions/runs/{run}'if run else None,'scope':'Actual pinned HTTPS rendering in three fresh opaque widget contexts. Four-area navigation is read-only. Focused A5 uses an explicitly labelled browser-only100mL milk merge through the real form; D6 applies existing owned decor and closes doors. No real-user, meal/purchase/reward/OCR, physical-device/Safari/Notion or persistence claim.','cases':[]}
 try:
  if a.local_root:
   from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
   from functools import partial
   import threading
   class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
   server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(a.local_root)));threading.Thread(target=server.serve_forever,daemon=True).start();result['scope']='LOCAL HTTP calibration of candidate bytes only; not public HTTPS proof.';result['candidate']=str(a.local_root)
  with sync_playwright()as p:
   b=p.chromium.launch(executable_path=shutil.which('google-chrome')or shutil.which('chromium'),args=['--no-sandbox'])
   for mode in ['widget']:
    native=(a.local_root/f'miniature-kitchen-{mode}.html').read_bytes()if a.local_root else source_bytes(a.source,f'previews/miniature-kitchen-{mode}.html');mobile=(a.local_root/'mobile'/f'{mode}.html').read_bytes()if a.local_root else source_bytes(a.source,f'previews/mobile/{mode}.html');data=contract(native,a.source,bool(a.local_root));payload=re.search(r'<template id="kitchenSource">([\s\S]*?)</template>',mobile.decode());assert payload and html.unescape(payload[1]).encode()==native
    for name,width,height in PROFILES:
     label=mode+'-'+name;raw=f'http://127.0.0.1:{server.server_port}/mobile/{mode}.html'if server else f'https://raw.githubusercontent.com/Ohoredingdong/Notion/{a.source}/previews/mobile/{mode}.html';url=raw if server else 'https://htmlpreview.github.io/?'+raw;row={'mode':mode,'profile':name,'viewport':[width,height],'url':url,'passed':False};ctx=b.new_context(viewport={'width':width,'height':height},has_touch=width<500,is_mobile=width<500,reduced_motion='reduce',locale='ko-KR',timezone_id='Asia/Seoul');page=ctx.new_page();page.set_default_timeout(20000);errors=[];responses=[];page.on('pageerror',lambda e,bucket=errors:bucket.append(str(e)));page.on('response',lambda r,bucket=responses:bucket.append(r))
     try:
      response=page.goto(url,wait_until='domcontentloaded',timeout=45000);assert response.status==200;iframe=page.locator('iframe[sandbox="allow-scripts allow-forms"]');expect(iframe).to_be_attached(timeout=45000);frame=iframe.element_handle().content_frame();frame.wait_for_function('window.KitchenHome&&window.KitchenJournal&&window.MiniKitchen&&window.KitchenWorkflows',timeout=30000);got=[r for r in responses if r.url==raw];assert got and got[-1].status==200 and got[-1].body()==mobile;assert iframe.get_attribute('srcdoc').encode()==native;assert frame.locator('script:not([src])').evaluate_all('nodes=>nodes.map(n=>n.textContent)')==data['scripts'];assert frame.locator('style').evaluate_all('nodes=>nodes.map(n=>n.textContent)')==data['styles'];row.update({'http_status':response.status,'mobile_sha256':hashlib.sha256(mobile).hexdigest(),'native_sha256':hashlib.sha256(native).hexdigest(),'decoded_sha256':data['decoded_sha256'],'exact_inline_modules':data['script_count'],'exact_styles':data['style_count'],'inline_asset_files':[{'file':asset['file'],'sha256':asset['sha256'],'width':asset['width'],'height':asset['height']}for asset in data['assets']]});row['visual']=focused(page,frame,label,width<500,data);assert not errors,errors;row['passed']=True
     except Exception as e:
      row.update({'error':str(e),'trace':traceback.format_exc()})
      try:page.screenshot(path=str(OUT/(label+'-failure.png')))
      except Exception:pass
     finally:row['runtime_errors']=errors;result['cases'].append(row);print(label,row['passed'],row.get('error',''),flush=True);ctx.close()
   b.close()
 except Exception:result['setup_error']=traceback.format_exc()
 finally:
  if server:server.shutdown()
  result['passed']=len(result['cases'])==3 and all(row['passed']for row in result['cases']);(OUT/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'source':a.source,'passed':result['passed'],'run_url':result['run_url'],'setup_error':result.get('setup_error')},ensure_ascii=False),flush=True)
  if a.publish_results:print('Evidence commit '+publish_results(),flush=True)
 if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
