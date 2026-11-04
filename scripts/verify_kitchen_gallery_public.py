"""Actual HTTPS display of the 24 captured implementation screens; no app writes."""
import argparse,hashlib,json,os,re,shutil,struct,subprocess,tempfile,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
OUT=Path('/tmp/kitchen-fullflow-gallery-public');RESULT_BRANCH='preview/kitchen-fullflow-gallery-20261104';BASE='previews/kitchen-full-flow-actual-20261104/';PROFILES=[('phone',390,844),('desktop',1120,1000),('small-phone',320,568)]
def git(*args,env=None):return subprocess.run(['git',*args],env=env,check=True,capture_output=True).stdout

def publish():
 old=git('ls-remote','--heads','origin','refs/heads/'+RESULT_BRANCH).decode().split()
 if old:git('fetch','--no-write-fetch-head','origin','refs/heads/'+RESULT_BRANCH)
 with tempfile.TemporaryDirectory(prefix='fullflow-gallery-proof-')as folder:
  env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'));git('read-tree','--empty',env=env)
  for path in OUT.iterdir():
   if path.is_file()and path.suffix in('.png','.json'):
    blob=git('hash-object','-w',str(path)).decode().strip();git('update-index','--add','--cacheinfo','100644,'+blob+','+path.name,env=env)
  tree=git('write-tree',env=env).decode().strip();parents=['-p',old[0]]if old else[];commit=git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree,*parents,'-m','Record actual HTTPS display of 24 implementation captures').decode().strip();git('push','origin',commit+':refs/heads/'+RESULT_BRANCH);return commit

def metrics(f):
 d=f.evaluate('''()=>({width:innerWidth,height:innerHeight,docWidth:document.documentElement.scrollWidth,docHeight:document.documentElement.scrollHeight,imageCount:document.querySelectorAll('#stage img').length,focus:document.querySelector('#stage').classList.contains('focus'),tabs:[...document.querySelectorAll('[data-group]')].map(e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height,reachable:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===e};})})''');assert d['docWidth']<=d['width']+1 and d['docHeight']<=d['height']+1,d;assert len(d['tabs'])==4 and all(t['width']>=44 and t['height']>=44 and t['reachable']for t in d['tabs']),d;return d

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--images-source',required=True);p.add_argument('--publish-results',action='store_true');a=p.parse_args();assert all(re.fullmatch('[0-9a-f]{40}',v)for v in[a.source,a.images_source]);OUT.mkdir(exist_ok=True);raw=f'https://raw.githubusercontent.com/Ohoredingdong/Notion/{a.source}/{BASE}index.html';url='https://htmlpreview.github.io/?'+raw;expected=git('show',a.source+':'+BASE+'index.html');data=json.loads(re.search(r'<script id="galleryData" type="application/json">([\s\S]*?)</script>',expected.decode())[1]);screens={s['id']:s for s in data['screens']};assert set(screens)=={g+str(n)for g in'ABCD'for n in range(1,7)};assert [g['id']for g in data['groups']]==list('ABCD');assert data['assetBase']==f'https://raw.githubusercontent.com/Ohoredingdong/Notion/{a.images_source}/{BASE}'
 for s in screens.values():
  b=git('show',a.images_source+':'+BASE+s['file']);assert b[:8]==b'\x89PNG\r\n\x1a\n'and struct.unpack('>II',b[16:24])==(s['width'],s['height'])and len(b)==s['bytes']and hashlib.sha256(b).hexdigest()==s['sha256']
 run=os.environ.get('GITHUB_RUN_ID');result={'source':a.source,'images_source':a.images_source,'verifier':os.environ.get('GITHUB_SHA'),'url':url,'run_url':f'https://github.com/Ohoredingdong/Notion/actions/runs/{run}'if run else None,'scope':'Actual HTTPS image gallery only, 24 unchanged captured PNGs. Captures contain clearly labelled example data; this test does not run or write application records.','cases':[]}
 try:
  with sync_playwright()as p:
   b=p.chromium.launch(executable_path=shutil.which('google-chrome')or shutil.which('chromium'),args=['--no-sandbox'])
   for name,w,h in PROFILES:
    c=b.new_context(viewport={'width':w,'height':h},has_touch=w<900,is_mobile=w<900,reduced_motion='reduce',locale='ko-KR');page=c.new_page();page.set_default_timeout(30000);errors=[];responses=[];page.on('pageerror',lambda e,q=errors:q.append(str(e)));page.on('response',lambda r,q=responses:q.append(r));case={'profile':name,'viewport':[w,h],'passed':False,'images':[],'groups':[]}
    try:
     response=page.goto(url,wait_until='domcontentloaded',timeout=45000);assert response.status==200;page.wait_for_timeout(300);f=next((f for f in page.frames if f.locator('#galleryData').count()),None);assert f;f.wait_for_function('document.querySelector("#stage img")&&document.querySelector("#stage img").complete&&document.querySelector("#stage img").naturalWidth>0',timeout=45000);got=[r for r in responses if r.url==raw];assert got and got[-1].status==200 and got[-1].body()==expected;case['viewer_sha256']=hashlib.sha256(expected).hexdigest()
     for group in'ABCD':
      f.locator(f'[data-group="{group}"]').click();expected_count=1 if w<900 else 6;expect(f.locator('#stage img')).to_have_count(expected_count);d=metrics(f);assert d['imageCount']==expected_count and d['focus']==(w<900),d;case['groups'].append({'id':group,'geometry':d})
      batches=[[group+str(n)]for n in range(1,7)]if w<900 else[[group+str(n)for n in range(1,7)]]
      for batch in batches:
       if w<900:f.locator(f'[data-pick="{batch[0]}"]').click()
       for id in batch:
        s=screens[id];image=f.locator(f'[data-screen="{id}"] img');image.evaluate('e=>e.decode()');src=image.get_attribute('src');assert src==data['assetBase']+s['file'];assert image.evaluate('e=>[e.naturalWidth,e.naturalHeight]')==[s['width'],s['height']];expect(image).to_be_visible();expect(f.locator(f'[data-screen="{id}"] .original')).to_have_attribute('href',src);r=c.request.get(src,timeout=45000);body=r.body();assert r.status==200 and len(body)==s['bytes']and hashlib.sha256(body).hexdigest()==s['sha256'];assert not f.locator('.shot-error').count();case['images'].append({'id':id,'url':src,'http_status':r.status,'sha256':s['sha256'],'bytes':len(body),'width':s['width'],'height':s['height']});metrics(f)
      page.screenshot(path=str(OUT/f'{name}-{group}.png'))
     assert len(case['images'])==24 and not errors;case['passed']=True
    except Exception as e:
     case.update({'error':str(e),'trace':traceback.format_exc()});page.screenshot(path=str(OUT/f'{name}-failure.png'))
    finally:case['runtime_errors']=errors;result['cases'].append(case);print(name,case['passed'],len(case['images']),case.get('error',''),flush=True);c.close()
   b.close()
 except Exception:result['setup_error']=traceback.format_exc()
 finally:
  result['passed']=len(result['cases'])==3 and all(c['passed']for c in result['cases']);(OUT/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'source':a.source,'run_url':result['run_url'],'setup_error':result.get('setup_error')},ensure_ascii=False),flush=True)
  if a.publish_results:print('Evidence commit '+publish(),flush=True)
 if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
