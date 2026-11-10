"""Exercise the isolated demo. Browser proxies are not real mobile-device tests."""
import functools
import http.server
import json
import os
import shutil
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('RADAR_EDITIONS_EVIDENCE',str(ROOT/'evidence')))
OUT.mkdir(parents=True,exist_ok=True)
checks=[]

def check(name, condition, detail=None):
    checks.append({'name':name,'passed':bool(condition),'detail':detail})
    if not condition: raise AssertionError(name+': '+repr(detail))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        executable=os.environ.get('BROWSER_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
        browser=p.chromium.launch(headless=True,executable_path=executable,args=['--no-sandbox'])
        for width,height in [(1440,950),(1280,800),(844,390),(390,844)]:
            ctx=browser.new_context(viewport={'width':width,'height':height},accept_downloads=True)
            page=ctx.new_page();requests=[];errors=[]
            page.on('request',lambda r:requests.append({'url':r.url,'type':r.resource_type}))
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/radar-public/',wait_until='networkidle')
            check(f'{width}: 3 fictional companies',page.locator('[data-company]').count()==3)
            check(f'{width}: 5 indices remain unconnected',page.locator('.index small').all_text_contents()==['시세 미연결']*5)
            check(f'{width}: no document horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            check(f'{width}: home shows default math',page.locator('#metrics strong').all_text_contents()==['20배','1.25배','10%'])
            page.locator('[data-company="DEMO-B"]').click()
            check(f'{width}: company selection math',page.locator('#metrics strong').all_text_contents()==['16배','1.25배','15%'])
            page.locator('[data-company="DEMO-C"]').click()
            check(f'{width}: negative EPS not false ratio',page.locator('#metrics strong').all_text_contents()==['산출 안 함','1.5배','-5%'])
            page.locator('#search').fill('not-a-company')
            check(f'{width}: empty search',page.locator('[data-company]').count()==0)
            page.locator('#search').fill('');page.locator('[data-company="DEMO-A"]').click()
            if width in [1440,390]:page.screenshot(path=str(OUT/f'public-demo-{width}.png'),full_page=True)
            page.locator('[data-tab="compare"]').click()
            check(f'{width}: compare tab visible',page.locator('#compare').is_visible() and page.locator('#home').is_hidden())
            page.locator('[name="price"]').fill('12000');page.locator('[name="eps"]').fill('600')
            page.locator('[name="bps"]').fill('10000');page.locator('[name="net"]').fill('20000000')
            page.locator('[name="equity"]').fill('200000000');page.locator('#ratioForm [type=submit]').click()
            check(f'{width}: independent ratio arithmetic',page.locator('#ratioOutput strong').all_text_contents()==['20배','1.2배','10%'])
            for name in ['eps','bps','equity']:page.locator('[name="'+name+'"]').fill('0')
            page.locator('#ratioForm [type=submit]').click()
            check(f'{width}: zero denominators rejected',page.locator('#ratioOutput strong').all_text_contents()==['산출 안 함']*3)
            page.locator('[data-tab="journal"]').click()
            page.locator('#notes').fill('시험 메모 <script>window.bad=true</script>')
            page.locator('#saveNote').click()
            check(f'{width}: explicit saved status','이 브라우저에 저장' in page.locator('#saveStatus').inner_text())
            check(f'{width}: no HTML execution',page.evaluate('window.bad === undefined'))
            page.reload(wait_until='networkidle');page.locator('[data-tab="journal"]').click()
            check(f'{width}: journal survives reload','시험 메모' in page.locator('#notes').input_value())
            page.locator('#notes').fill('미저장 백업 테스트')
            with page.expect_download() as dl:page.locator('#exportNotes').click()
            with TemporaryDirectory() as tmp:
                dest=Path(tmp)/'notes.json';dl.value.save_as(str(dest));saved=json.loads(dest.read_text())
                check(f'{width}: backup separates unsaved draft',saved['unsaved_draft']['text']=='미저장 백업 테스트' and saved['contains_real_market_data'] is False)
            page.locator('#saveNote').click()
            page.locator('[data-tab="release"]').click()
            check(f'{width}: commercial readiness is not asserted','현재는 시연판' in page.locator('#release').inner_text())
            check(f'{width}: only isolated app resources requested',all(urlparse(r['url']).path in ['/radar-public/','/radar-public/app.js','/radar-public/styles.css','/favicon.ico'] for r in requests),requests)
            check(f'{width}: no data traffic',not any(r['type'] in ['xhr','fetch','websocket','eventsource'] for r in requests))
            check(f'{width}: no script errors',not errors,errors)
            ctx.close()
        # Cross-tab overwrite protection and quota errors preserve the input.
        ctx=browser.new_context();page=ctx.new_page();page.goto(base+'/radar-public/')
        page.locator('[data-tab="journal"]').click();page.locator('#notes').fill('내가 입력한 초안')
        page.evaluate("localStorage.setItem('radar-public-demo:journal:v1',JSON.stringify({'DEMO-A':'다른 탭 원본'}))")
        page.locator('#saveNote').click()
        check('concurrent note never overwritten','다른 탭의 기록' in page.locator('#saveStatus').inner_text())
        check('concurrent original remains',json.loads(page.evaluate("localStorage.getItem('radar-public-demo:journal:v1')"))['DEMO-A']=='다른 탭 원본')
        check('draft remains after conflict',page.locator('#notes').input_value()=='내가 입력한 초안');ctx.close()
        ctx=browser.new_context();ctx.add_init_script("Storage.prototype.setItem=function(){throw new DOMException('blocked','QuotaExceededError')}")
        page=ctx.new_page();page.goto(base+'/radar-public/');page.locator('[data-tab="journal"]').click();page.locator('#notes').fill('보존할 초안');page.locator('#saveNote').click()
        check('quota error not false save','저장하지 못했습니다' in page.locator('#saveStatus').inner_text())
        check('quota error preserves draft',page.locator('#notes').input_value()=='보존할 초안');ctx.close()
        browser.close()
finally:
    server.shutdown();server.server_close()
    (OUT/'browser-report.json').write_text(json.dumps({'tests':len(checks),'passed':sum(x['passed'] for x in checks),'checks':checks},ensure_ascii=False,indent=2))
print('RADAR_EDITION_BROWSER_PASS',len(checks))
