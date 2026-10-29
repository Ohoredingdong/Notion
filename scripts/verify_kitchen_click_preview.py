import hashlib,json,os,shutil,subprocess,tempfile,time,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

SOURCE='2e08219869c2493c04436eecfd0828da282a14d7'
OUT=Path('/tmp/kitchen-click-preview');OUT.mkdir(exist_ok=True)
RESULT=OUT/'status.json'
result={'source':SOURCE,'run_url':f'https://github.com/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{os.environ["GITHUB_RUN_ID"]}','cases':[],'scope':'Actual public HTTPS HTMLPreview execution in fresh Chromium desktop/mobile contexts, not a local proxy or stub; no physical-device claim.'}
try:
 with sync_playwright() as p:
  chrome=shutil.which('google-chrome') or shutil.which('chromium')
  if not chrome:raise RuntimeError('No installed Chromium browser on the runner')
  browser=p.chromium.launch(executable_path=chrome,args=['--no-sandbox'])
  for mode in ('app','widget'):
   raw=f'https://raw.githubusercontent.com/Ohoredingdong/Notion/{SOURCE}/previews/mobile/{mode}.html'
   url='https://htmlpreview.github.io/?'+raw
   for profile,width,height in [('desktop',649,900),('phone',390,844)]:
    label=f'{mode}-{profile}';case={'mode':mode,'profile':profile,'url':url,'passed':False};ctx=browser.new_context(viewport={'width':width,'height':height},has_touch=True,is_mobile=profile=='phone',device_scale_factor=2,reduced_motion='no-preference',timezone_id='Asia/Seoul');page=ctx.new_page();errors=[];sources=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:sources.append(r) if r.url==raw else None)
    try:
     response=page.goto(url,wait_until='domcontentloaded',timeout=45000)
     case['http_status']=response.status
     assert response.status==200
     wrapper=page.locator('iframe[sandbox="allow-scripts"]');expect(wrapper).to_be_attached(timeout=45000)
     frame=wrapper.element_handle().content_frame();frame.wait_for_function('window.MiniKitchen && window.KitchenJournal',timeout=30000)
     assert frame.locator('body').get_attribute('data-mode')==mode
     expect(frame.locator('[data-lcd="freshLeft"] .lcd-title')).to_have_text('유통기한 임박')
     expect(frame.locator('[data-lcd="freshRight"] .lcd-title')).to_have_text('오늘의 추천메뉴')
     expect(frame.locator('.lcd-dish')).to_be_visible()
     assert not frame.evaluate('document.documentElement.scrollWidth>innerWidth')
     expect(frame.locator('.door-label')).to_have_count(0)
     frame.locator('[data-door="freshLeft"]').evaluate("""e=>{e.click();const a=e.getAnimations().find(a=>a.transitionProperty==='transform');if(!a)throw new Error('Missing real opening transition');a.pause();a.currentTime=0;}""")
     hit=frame.evaluate("""()=>{const r=document.querySelector('[data-item="broccoli"]').getBoundingClientRect(),e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return {door:e?.closest('[data-door]')?.dataset.door||null,item:e?.closest('[data-item]')?.dataset.item||null}}""")
     assert hit=={'door':'freshLeft','item':None},hit
     frame.locator('[data-door="freshLeft"]').evaluate("e=>e.getAnimations().forEach(a=>a.play())")
     frame.wait_for_function("document.querySelector('[data-door=\"freshLeft\"]').getAnimations().every(a=>a.playState==='finished')")
     frame.locator('[data-door="freshLeft"]').evaluate('e=>e.click()')
     frame.wait_for_function("!MiniKitchen.isDoorClosing('freshLeft')")
     expect(frame.locator('[data-lcd="freshLeft"]')).to_be_visible()
     case['opening_food_occluded_at_first_frame']=True
     case['door_surface_labels_removed']=True
     frame.locator('#expandDisplays').click();expect(frame.locator('.display-inspector .fridge-lcd')).to_have_count(2);frame.locator('#closeTray').click()
     assert sources,'No real public raw source response observed'
     case['source_sha256']=hashlib.sha256(sources[0].body()).hexdigest()
     case['window_and_dialog_work']=True;case['runtime_errors']=errors;assert not errors,errors
     page.screenshot(path=str(OUT/(label+'.png')))
     case['passed']=True
    except Exception as e:
     case['error']=str(e);case['runtime_errors']=errors
     page.screenshot(path=str(OUT/(label+'-failure.png')))
    result['cases'].append(case);ctx.close()
  browser.close()
except Exception:
 result['setup_error']=traceback.format_exc()
finally:
 result['passed']=len(result['cases'])==4 and all(c['passed'] for c in result['cases'])
 RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
 # Publish only public validation evidence to a dedicated branch. No main or
 # Pages settings writes, credentials, personal records, or force pushes.
 branch='preview/kitchen-click-validation-20261029'
 def git(*args,env=None,check=True):return subprocess.run(['git',*args],env=env,check=check,capture_output=True,text=True).stdout.strip()
 parent=git('ls-remote','--heads','origin','refs/heads/'+branch).split()
 if parent:git('fetch','origin','refs/heads/'+branch)
 with tempfile.TemporaryDirectory(prefix='kitchen-result-index-') as folder:
  env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
  git('read-tree',parent[0] if parent else '--empty',env=env)
  for path in OUT.iterdir():
   if path.suffix not in ('.json','.png'):continue
   blob=git('hash-object','-w',str(path));git('update-index','--add','--cacheinfo','100644,'+blob+','+path.name,env=env)
  tree=git('write-tree',env=env)
  args=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree]
  if parent:args+=['-p',parent[0]]
  commit=git(*args,'-m','Record actual public kitchen preview browser checks')
  git('push','origin',commit+':refs/heads/'+branch)
 if not result['passed']:raise SystemExit(1)
