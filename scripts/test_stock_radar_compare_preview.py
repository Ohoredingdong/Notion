"""UI-only regression. No quotes, predictions, credentials, or production writes."""
from pathlib import Path
import argparse, json, shutil
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8768/stock-radar-ui-preview.html')
parser.add_argument('--html',type=Path)
parser.add_argument('--output',type=Path,default=Path('compare-preview-evidence'))
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
checks=[]
with sync_playwright() as p:
    options={'headless':True}
    if args.html: options.update(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
    browser=p.chromium.launch(**options)
    for width in (390,768,1280):
        context=browser.new_context(viewport={'width':width,'height':950},reduced_motion='no-preference')
        page=context.new_page();page.set_default_timeout(10000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        def load(route='home'):
            if args.html:
                page.set_content(args.html.read_text())
                if route!='home':page.evaluate('(route)=>{location.hash="#/"+route}',route)
            else:page.goto(args.url+'#/'+route,wait_until='networkidle')
        load();page.locator('.cx-home').wait_for()
        assert page.locator('.cx-markets .cx-market').count()==4
        assert page.locator('.cx-stockchip').count()==6
        assert page.locator('[data-cx-line]').count()==3
        assert page.locator('input[type=password]').count()==0
        assert page.locator('#globe').count()==0
        assert '실제 주가 아님' in page.locator('#cxDemoNote').inner_text()
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        if width==1280:
            box=page.locator('.cx-comparison').bounding_box()
            assert box['y']+box['height']<=900,box
            assert page.locator('#cxFocus').is_visible()
        page.screenshot(path=str(args.output/f'home-{width}.png'),full_page=True)
        old_url=page.url
        page.locator('.cx-stockpicker [data-cx-focus=NVDA]').click()
        assert 'NVIDIA' in page.locator('#cxFocus h3').inner_text()
        assert page.url==old_url
        assert page.locator('.cx-table thead th').count()==4
        page.locator('[data-cx-pin="035420"]').click()
        assert page.locator('[data-cx-line="035420"]').count()==1
        assert page.locator('[data-cx-line=NVDA]').count()==0
        assert 'NAVER' in page.locator('.cx-table thead').inner_text()
        for symbol in ('000660','035420'):page.locator(f'[data-cx-pin="{symbol}"]').click()
        page.locator('[data-cx-pin="005930"]').click()
        assert page.locator('[data-cx-line]').count()==1
        for symbol in ('000660','NVDA'):page.locator(f'[data-cx-pin="{symbol}"]').click()
        page.locator('#cxScrub').fill('15')
        assert abs(float(page.locator('[data-cx-cursor]').get_attribute('x1'))-98)<.01
        page.locator('#cxScrub').focus();page.keyboard.press('ArrowRight')
        assert page.locator('#cxScrub').input_value()=='16'
        before=page.locator('[data-cx-cursor]').get_attribute('x1')
        page.locator('[data-cx-play]').click();page.wait_for_timeout(450)
        assert before!=page.locator('[data-cx-cursor]').get_attribute('x1')
        page.locator('[data-cx-play]').click();before=page.locator('[data-cx-cursor]').get_attribute('x1')
        page.wait_for_timeout(250);assert before==page.locator('[data-cx-cursor]').get_attribute('x1')
        page.emulate_media(reduced_motion='reduce')
        page.wait_for_function("document.querySelector('[data-cx-play]').textContent.includes('다음 장면')")
        page.locator('[data-cx-play]').click();before=page.locator('[data-cx-cursor]').get_attribute('x1')
        page.wait_for_timeout(250);assert before==page.locator('[data-cx-cursor]').get_attribute('x1')
        page.locator('.cx-stockpicker [data-cx-focus="000660"]').click()
        assert page.locator('.cx-addcondition').get_attribute('data-symbol')=='000660'
        page.locator('#cxFocus [data-go=stock]').click()
        page.locator('.companytitle h2').wait_for();assert 'SK하이닉스' in page.locator('.companytitle h2').inner_text()
        page.locator('.back').click();page.locator('.cx-home').wait_for()
        page.locator('#cxFocus [data-go=alert]').click()
        page.locator('input[name=price]').fill('80000');page.locator('[type=submit]').click()
        assert page.locator('.alertcard').count()==1
        if not args.html:
            page.reload();page.locator('.alertcard').wait_for()
            assert '80,000' in page.locator('.alertcard').inner_text()
        page.locator('[data-edit]').click();page.locator('input[value="근거 변화"]').check()
        assert not page.locator('#priceField').is_visible()
        page.locator('[type=submit]').click();assert '근거 변화' in page.locator('.alertcard').inner_text()
        page.locator('[data-toggle]').click();assert page.locator('[data-toggle]').get_attribute('aria-checked')=='false'
        page.locator('[data-delete]').click();assert page.locator('.alertcard').count()==0
        load('discover');page.locator('#stockSearch').fill('삼성');assert page.locator('#stockList .listrow').count()==1
        page.locator('#stockList .listrow').click();page.locator('.star').click()
        assert page.locator('.star').get_attribute('aria-pressed')=='false'
        page.locator('.star').click();assert page.locator('.star').get_attribute('aria-pressed')=='true'
        page.locator('[data-period="1주"]').click();assert '1주' in page.locator('.chart svg').get_attribute('aria-label')
        page.screenshot(path=str(args.output/f'detail-{width}.png'),full_page=True)
        for route in ('home','discover','stock/005930','forecast/005930','watchlist','alerts','alert/005930','news','results','settings'):
            load(route);page.locator('h1').wait_for()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(width,route)
        page.locator('[data-action=connection]').click();assert page.locator('dialog').is_visible()
        page.keyboard.press('Escape');assert not page.locator('dialog').is_visible()
        assert not errors,errors
        checks.append({'width':width,'simultaneous_markets':'pass','comparison_and_inline_focus':'pass','motion_and_reduced_motion':'pass','routes_and_conditions':'pass','persistent_reload':'pass' if not args.html else 'not_checked_local_html','page_errors':errors})
        context.close()
    browser.close()
(args.output/'checks.json').write_text(json.dumps({'source':str(args.html or args.url),'checks':checks,'live_data_connected':False,'orders_enabled':False},ensure_ascii=False,indent=2))
print('COMPARE_DESK_UI_CHECKS_PASS',json.dumps(checks,ensure_ascii=False))
