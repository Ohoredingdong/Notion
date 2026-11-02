"""Verify actual public storyboard image delivery; publish only synthetic evidence."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect

OUT = Path('/tmp/kitchen-storyboards-public')
RESULT_BRANCH = 'preview/kitchen-storyboards-display-20261102'
ASSET_DIR = 'designs/kitchen-ux-storyboards/'
VIEWER = 'previews/kitchen-ux-storyboards.html'
PROFILES = [('phone',390,844),('desktop',1120,1000),('short-phone',320,568)]


def git(*args,env=None):
    return subprocess.run(['git',*args],env=env,check=True,capture_output=True,text=True).stdout.strip()


def source_bytes(source,path):
    return subprocess.run(['git','show',source+':'+path],check=True,capture_output=True).stdout


def display_frame(page):
    end=time.monotonic()+45
    while time.monotonic()<end:
        for frame in page.frames:
            if frame.locator('#boardImage').count():
                return frame
        page.wait_for_timeout(100)
    raise AssertionError('No visible storyboard viewer frame was created')


def geometry(frame):
    return frame.evaluate('''()=>({width:innerWidth,height:innerHeight,
      bodyWidth:document.documentElement.scrollWidth,
      imageCount:document.querySelectorAll('img').length,
      tabs:[...document.querySelectorAll('[data-board]')].map(e=>{const r=e.getBoundingClientRect();
        return {id:e.dataset.board,width:r.width,height:r.height,visible:r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth,
          reachable:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('[data-board]')===e};})})''')


def publish_results():
    previous=git('ls-remote','--heads','origin','refs/heads/'+RESULT_BRANCH).split()
    if previous:git('fetch','origin','refs/heads/'+RESULT_BRANCH)
    with tempfile.TemporaryDirectory(prefix='kitchen-storyboards-results-') as folder:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(folder)/'index'))
        git('read-tree',previous[0] if previous else '--empty',env=env)
        for path in OUT.iterdir():
            if path.is_file() and path.suffix in ('.png','.json'):
                blob=git('hash-object','-w',str(path))
                git('update-index','--add','--cacheinfo','100644,'+blob+','+path.name,env=env)
        tree=git('write-tree',env=env)
        args=['-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit-tree',tree]
        if previous:args+=['-p',previous[0]]
        commit=git(*args,'-m','Verify public kitchen storyboard image delivery')
        git('push','origin',commit+':refs/heads/'+RESULT_BRANCH)
        return commit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--publish-results',action='store_true')
    args=parser.parse_args();source=args.source
    if len(source)!=40 or any(c not in '0123456789abcdef'for c in source):raise SystemExit('Exact lowercase40-character source commit required')
    OUT.mkdir(parents=True,exist_ok=True)
    repo=os.environ.get('GITHUB_REPOSITORY','Ohoredingdong/Notion');run=os.environ.get('GITHUB_RUN_ID')
    raw=f'https://raw.githubusercontent.com/{repo}/{source}/{VIEWER}';url='https://htmlpreview.github.io/?'+raw
    manifest=json.loads(source_bytes(source,ASSET_DIR+'manifest.json'));boards=manifest['boards']
    assert len(boards)==5 and [b['id']for b in boards]==['00','01','02','03','04']
    for b in boards:
        data=source_bytes(source,ASSET_DIR+b['file'])
        assert len(data)==b['bytes'] and hashlib.sha256(data).hexdigest()==b['sha256']
        assert b['width']==1448 and b['height']==1086
    result={'source':source,'run_url':f'https://github.com/{repo}/actions/runs/{run}'if run else None,
      'scope':'Actual HTTPS HTMLPreview image delivery in fresh Chromium phone/desktop/short-phone profiles. Checks original image bytes, decoding dimensions, one-at-a-time network loading, real tab clicks, zoom and original links. No claim to repair ChatGPT client rendering or to physical-device/Safari validation.',
      'url':url,'manifest':manifest,'cases':[],'passed':False}
    try:
        with sync_playwright() as p:
            executable=shutil.which('google-chrome')or shutil.which('chromium')
            if not executable:raise RuntimeError('Chromium unavailable')
            browser=p.chromium.launch(executable_path=executable,args=['--no-sandbox'])
            for label,width,height in PROFILES:
                case={'profile':label,'viewport':[width,height],'passed':False,'boards':[]};errors=[];requests=[];responses=[]
                ctx=browser.new_context(viewport={'width':width,'height':height},has_touch=label!='desktop',is_mobile=label!='desktop',reduced_motion='reduce',timezone_id='Asia/Seoul')
                page=ctx.new_page();page.set_default_timeout(30000)
                page.on('pageerror',lambda e,bucket=errors:bucket.append(str(e)))
                ctx.on('request',lambda request,bucket=requests:bucket.append({'url':request.url,'type':request.resource_type,'method':request.method}))
                page.on('response',lambda response,bucket=responses:bucket.append(response))
                try:
                    response=page.goto(url,wait_until='domcontentloaded',timeout=45000);assert response and response.status==200
                    case['http_status']=response.status
                    frame=display_frame(page)
                    frame.wait_for_function('document.querySelector("#boardImage").complete&&document.querySelector("#boardImage").naturalWidth===1448',timeout=45000)
                    raw_responses=[r for r in responses if r.url==raw];assert raw_responses,'HTMLPreview never fetched pinned viewer'
                    actual=raw_responses[-1].body();expected=source_bytes(source,VIEWER)
                    assert raw_responses[-1].status==200 and actual==expected
                    case['viewer_sha256']=hashlib.sha256(actual).hexdigest()
                    initial=[r for r in requests if '/'+ASSET_DIR in r['url'] and r['url'].split('?')[0].endswith('.png')]
                    assert len(initial)==1,initial
                    case['initial_image_requests']=initial
                    expect(frame.locator('#boardImage')).to_be_visible()
                    expect(frame.locator('[data-board]')).to_have_count(5)
                    for index,b in enumerate(boards):
                        frame.locator(f'[data-board="{index}"]').click()
                        frame.wait_for_function('name=>{const i=document.querySelector("#boardImage");return i.complete&&i.naturalWidth===1448&&i.naturalHeight===1086&&i.currentSrc.endsWith("/"+name)}',arg=b['file'],timeout=45000)
                        image=frame.locator('#boardImage');src=image.evaluate('e=>e.currentSrc')
                        parsed=urlparse(src);parts=parsed.path.split('/')
                        assert parsed.scheme=='https'and parsed.netloc=='raw.githubusercontent.com'
                        assert parts[1:3]==['Ohoredingdong','Notion']and len(parts[3])==40
                        assert parsed.path.endswith('/'+ASSET_DIR+b['file'])
                        fetched=ctx.request.get(src,timeout=45000);assert fetched.status==200
                        data=fetched.body();assert len(data)==b['bytes']and hashlib.sha256(data).hexdigest()==b['sha256']
                        expect(frame.locator('#openOriginal')).to_have_attribute('href',src)
                        assert not frame.locator('#retryImage').is_visible()
                        metrics=geometry(frame);assert metrics['imageCount']==1 and metrics['bodyWidth']<=metrics['width']+1,metrics
                        assert all(t['width']>=44 and t['height']>=44 and t['visible']and t['reachable']for t in metrics['tabs']),metrics
                        case['boards'].append({'id':b['id'],'url':src,'http_status':fetched.status,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                          'naturalWidth':image.evaluate('e=>e.naturalWidth'),'naturalHeight':image.evaluate('e=>e.naturalHeight'),'status':frame.locator('#imageStatus').inner_text(),'geometry':metrics})
                        page.wait_for_timeout(100);page.screenshot(path=str(OUT/f'{label}-board-{b["id"]}.png'))
                    frame.locator('#zoomImage').click();expect(frame.locator('#zoomImage')).to_have_attribute('aria-pressed','true')
                    zoom=frame.evaluate('''()=>{const i=document.querySelector('#boardImage'),c=document.querySelector('.canvas');return{imageWidth:i.getBoundingClientRect().width,scrollWidth:c.scrollWidth,canvasWidth:c.clientWidth,bodyWidth:document.documentElement.scrollWidth,viewport:innerWidth}}''')
                    assert abs(zoom['imageWidth']-1448)<=1 and zoom['scrollWidth']>=1448 and zoom['bodyWidth']<=zoom['viewport']+1,zoom
                    assert zoom['scrollWidth']>zoom['canvasWidth'],zoom
                    case['zoom']=zoom;page.screenshot(path=str(OUT/f'{label}-zoom.png'))
                    frame.locator('#zoomImage').click();expect(frame.locator('#zoomImage')).to_have_attribute('aria-pressed','false')
                    assert not errors,errors
                    case['runtime_errors']=errors;case['passed']=True
                except Exception as error:
                    case['error']=str(error);case['trace']=traceback.format_exc();case['runtime_errors']=errors
                    try:page.screenshot(path=str(OUT/f'{label}-failure.png'),full_page=True)
                    except Exception:pass
                finally:
                    result['cases'].append(case);ctx.close()
            browser.close()
    except Exception:result['setup_error']=traceback.format_exc()
    finally:
        result['passed']=len(result['cases'])==3 and all(c['passed']for c in result['cases'])
        (OUT/'status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'source':source,'passed':result['passed'],'run_url':result['run_url'],'cases':[{'profile':c['profile'],'passed':c['passed'],'boards':len(c['boards']),'error':c.get('error')}for c in result['cases']]},ensure_ascii=False),flush=True)
        if args.publish_results:print('Published evidence commit '+publish_results(),flush=True)
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
