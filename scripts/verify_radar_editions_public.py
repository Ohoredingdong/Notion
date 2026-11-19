"""Verify exact new edition assets, not commercial permission or prediction performance."""
import hashlib
import json
import os
import shutil
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('RADAR_EDITIONS_EVIDENCE',str(ROOT/'evidence')))
OUT.mkdir(parents=True,exist_ok=True)
BASE='https://ohoredingdong.github.io/Notion/'
NAMES=['stock-radar-research.html','stock-radar-editions.json','radar-public/index.html','radar-public/styles.css','radar-public/app.js']
NAMES += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'assets').glob('radar-cohesive*')) if p.suffix in ('.js','.css')]
expected={name:(ROOT/name).read_bytes() for name in NAMES}
proof={'commit':os.environ.get('GITHUB_SHA'),'files':{},'commercial_ready':False,'research_private_access_configured':False}
last='not_checked'
for attempt in range(36):
    try:
        rows={}
        for name,body in expected.items():
            req=urllib.request.Request(BASE+name+'?verify=editions-1',headers={'Cache-Control':'no-cache','User-Agent':'RadarEditionAudit/1.0'})
            with urllib.request.urlopen(req,timeout=15) as response:
                data=response.read()
                if response.status!=200 or data!=body:raise ValueError('public_bytes_not_current:'+name)
                rows[name]={'sha256':hashlib.sha256(data).hexdigest(),'http_status':response.status}
        proof['files']=rows
        proof['verified_at']=datetime.now(timezone.utc).isoformat()
        break
    except Exception as exc:
        last=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
        if attempt<35:time.sleep(10)
else:
    raise RuntimeError('RADAR_EDITIONS_PUBLIC_UNVERIFIED:'+last)

with sync_playwright() as p:
    exe=os.environ.get('BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
    browser=p.chromium.launch(headless=True,executable_path=exe,args=['--no-sandbox'])
    proof['public_browser']=[]
    for width,height in [(1440,950),(390,844)]:
        ctx=browser.new_context(viewport={'width':width,'height':height})
        page=ctx.new_page();requests=[];errors=[]
        page.on('request',lambda r:requests.append((r.url,r.resource_type)))
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'radar-public/',wait_until='networkidle',timeout=60000)
        assert page.locator('[data-company]').count()==3
        assert page.locator('.index small').all_text_contents()==['시세 미연결']*5
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('[data-tab="compare"]').click()
        assert page.locator('#ratioOutput strong').all_text_contents()==['20배','1.25배','10%']
        page.locator('[data-tab="home"]').click()
        assert not errors,errors
        allowed={'/Notion/radar-public/','/Notion/radar-public/app.js','/Notion/radar-public/styles.css','/favicon.ico','/Notion/favicon.ico'}
        assert all(urlparse(url).hostname=='ohoredingdong.github.io' and urlparse(url).path in allowed for url,kind in requests),requests
        assert not any(kind in ['xhr','fetch','websocket','eventsource'] for url,kind in requests)
        page.screenshot(path=str(OUT/f'public-live-{width}.png'),full_page=True)
        proof['public_browser'].append({'width':width,'requests':requests,'no_research_or_external_requests':True,'errors':errors})
        ctx.close()
    ctx=browser.new_context(viewport={'width':1440,'height':950});page=ctx.new_page()
    page.goto(BASE+'stock-radar-research.html',wait_until='domcontentloaded',timeout=60000)
    assert '웹 접근제어 없음' in page.locator('.rc-footer').inner_text()
    assert page.locator('#rc-engine').get_attribute('src')=='./stock-value-radar.html'
    assert page.locator('.rc-footer a[href="./stock-value-radar.html"]').is_visible()
    page.locator('#rc-home-rows .rc-stockrow').first.wait_for(state='visible',timeout=60000)
    assert page.locator('.rc-primary button').count()==5
    assert page.locator('.rc-view[data-rc-page="home"]').is_visible()
    assert page.evaluate('document.documentElement.scrollHeight <= innerHeight+2')
    page.locator('header').screenshot(path=str(OUT/'research-live-entry-header.png'))
    proof['research_entry']={'cohesive_research_visible':True,'legacy_entry_link_visible':True,'no_access_control_disclaimer_visible':True,'underlying_forecast_quality_retested':False}
    ctx.close();browser.close()
(OUT/'public-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
print('RADAR_EDITION_PUBLIC_BYTES_AND_BROWSERS_VERIFIED',json.dumps(proof,ensure_ascii=False))
