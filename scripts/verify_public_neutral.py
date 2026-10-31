"""Read-only public HTTPS UI checks; publishes only synthetic validation evidence."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);args=parser.parse_args();SOURCE=args.source
if len(SOURCE)!=40 or any(c not in '0123456789abcdef' for c in SOURCE):raise SystemExit('Use a pinned commit')
OUT=Path('/tmp/neutral-kitchen-public');OUT.mkdir(exist_ok=True)
result={'source':SOURCE,'run_url':f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}','cases':[],'scope':'Real public HTTPS HTMLPreview execution in fresh desktop and mobile Chromium contexts; mobile uses touch. No proxy/stub, physical iPhone/Safari or Notion claim.'}
try:
 with sync_playwright() as p:
  chrome=shutil.which('google-chrome') or shutil.which('chromium')
  if not chrome:raise RuntimeError('No Chromium browser installed')
  browser=p.chromium.launch(executable_path=chrome,args=['--no-sandbox'])
  for mode in ['app','widget']:
   raw=f'https://raw.githubusercontent.com/Ohoredingdong/Notion/{SOURCE}/previews/mobile/{mode}.html';url='https://htmlpreview.github.io/?'+raw
   expected_hash=hashlib.sha256(subprocess.run(['git','show',f'{SOURCE}:previews/mobile/{mode}.html'],check=True,capture_output=True).stdout).hexdigest()
   for profile,width,height in [('desktop',649,900),('phone',390,844)]:
    label=mode+'-'+profile;case={'mode':mode,'profile':profile,'url':url,'passed':False};ctx=browser.new_context(viewport={'width':width,'height':height},has_touch=True,is_mobile=profile=='phone',device_scale_factor=2,reduced_motion='reduce',timezone_id='Asia/Seoul');page=ctx.new_page();errors=[];sources=[]
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:sources.append(r) if r.url==raw else None)
    try:
     response=page.goto(url,wait_until='domcontentloaded',timeout=45000);case['http_status']=response.status;assert response.status==200
     wrapper=page.locator('iframe[sandbox="allow-scripts allow-forms"]');expect(wrapper).to_be_attached(timeout=45000);frame=wrapper.element_handle().content_frame();frame.wait_for_function('window.MiniKitchen && window.KitchenJournal && window.KitchenWorkflows',timeout=30000)
     assert frame.locator('body').get_attribute('data-mode')==mode
     assert frame.locator('[data-balance]').count()==3
     assert frame.locator('.door').count()==4 and all(frame.evaluate('MiniKitchen.getSnapshot().doors').values())
     assert frame.evaluate('KitchenJournal.status')=='temporary'
     assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
     assert frame.locator('.door-label').count()==0
     assert sources,'No actual raw source response';case['source_sha256']=hashlib.sha256(sources[0].body()).hexdigest();assert case['source_sha256']==expected_hash
     page.screenshot(path=str(OUT/(label+'-initial.png')),full_page=True)
     # Real gesture on the empty inner door surface; then repeat on the closed door.
     door=frame.locator('[data-door="freshLeft"]');b=door.bounding_box();(page.touchscreen.tap if profile=='phone' else page.mouse.click)(b['x']+b['width']*.12,b['y']+b['height']*.12)
     frame.wait_for_function('MiniKitchen.getSnapshot().doors.freshLeft===false');expect(frame.locator('[data-lcd="freshLeft"]')).to_be_visible()
     (door.tap if profile=='phone' else door.click)();frame.wait_for_function('MiniKitchen.getSnapshot().doors.freshLeft===true');case['real_door_gestures']=True
     condiment=frame.locator('[data-item="spice0"]');(condiment.tap if profile=='phone' else condiment.click)();expect(frame.locator('#ingredientForm')).to_be_visible();frame.locator('#ingredientForm [name="expiry"]').fill('2027-03-01');frame.locator('#ingredientForm [type="submit"]').click();assert frame.evaluate('MiniKitchen.exportWorld().items.find(i=>i.id==="spice0").expiry')=='2027-03-01';case['condiment_expiry_form']=True
     frame.locator('#openRecords').click();expect(frame.locator('#tray')).to_be_visible();assert frame.locator('#tray .workflow-card').count()==10;frame.locator('#closeTray').click();frame.locator('#addFood').click();frame.locator('[data-wf="photos"]').click();assert frame.locator('[data-photo]').count()==2;expect(frame.locator('button:disabled')).to_contain_text('연결 전');case['photo_registration_is_honest']=True
     page.screenshot(path=str(OUT/(label+'-photo.png')));assert not errors,errors;case['runtime_errors']=errors;case['passed']=True
    except Exception as e:
     case['error']=str(e);case['trace']=traceback.format_exc();case['runtime_errors']=errors;page.screenshot(path=str(OUT/(label+'-failure.png')))
    result['cases'].append(case);ctx.close()
  browser.close()
except Exception:result['setup_error']=traceback.format_exc()
finally:
 result['passed']=len(result['cases'])==4 and all(c['passed'] for c in result['cases']);(OUT/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
 branch='preview/neutral-kitchen-validation-20261031'
 def git(*a,env=None):return subprocess.run(['git',*a],env=env,check=True,capture_output=True,text=True).stdout.strip()
 parent=git('ls-remote','--heads','origin','refs/heads/'+branch).split()
 if parent:git('fetch','origin','refs/heads/'+branch)
 with tempfile.TemporaryDirectory(prefix='neutral-kitchen-result-') as folder:
  env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'));git('read-tree',parent[0] if parent else '--empty',env=env)
  for path in OUT.iterdir():
   if path.suffix not in ['.png','.json']:continue
   blob=git('hash-object','-w',str(path));git('update-index','--add','--cacheinfo','100644,'+blob+','+path.name,env=env)
  tree=git('write-tree',env=env);a=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree]
  if parent:a+=['-p',parent[0]]
  commit=git(*a,'-m','Record neutral kitchen public preview browser verification');git('push','origin',commit+':refs/heads/'+branch)
 if not result['passed']:raise SystemExit(1)
