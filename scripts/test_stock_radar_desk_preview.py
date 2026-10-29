"""Browser interaction regression for a design-only preview, never market validation."""
from playwright.sync_api import sync_playwright
import argparse,json
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8768/stock-radar-ui-preview.html');args=parser.parse_args()
out=Path('desk-preview-evidence');out.mkdir(exist_ok=True)
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for width in (1280,390,768):
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        page=context.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'#/home',wait_until='networkidle')
        page.locator('.desk-home').wait_for()
        assert page.locator('#globe,canvas,.globe-stage').count()==0
        assert '오늘, 무엇을 볼까요?' in page.locator('h1').inner_text()
        assert page.locator('.desk-shortcut').count()==4
        assert page.locator('.desk-stock').count()==3
        page.screenshot(path=str(out/f'home-{width}.png'),full_page=True)
        for route in ('discover','forecast','alerts','results'):
            page.locator(f'.desk-shortcut[data-go="{route}"]').click()
            assert page.url.split('#/')[1].split('/')[0]==route
            page.locator('.back').click();page.locator('.desk-home').wait_for()
        page.locator('[data-desk-index="코스닥"]').click()
        assert page.locator('.desk-index-name').inner_text()=='KOSDAQ'
        before=page.locator('.desk-series').get_attribute('d')
        page.locator('[data-desk-range="1주"]').click()
        assert before!=page.locator('.desk-series').get_attribute('d')
        page.locator('[data-homemarket="미국"]').click()
        assert page.locator('.desk-index-name').inner_text()=='NASDAQ'
        page.locator('.desk-card-foot [data-market]').click()
        assert page.locator('#stockList .listrow').count()==2
        page.locator('[data-filter="전체"]').click()
        page.locator('#stockSearch').fill('삼성')
        assert page.locator('#stockList .listrow').count()==1
        page.locator('#stockList .listrow').click()
        page.locator('.star').click();assert page.locator('.star').get_attribute('aria-pressed')=='false'
        page.locator('.star').click();assert page.locator('.star').get_attribute('aria-pressed')=='true'
        page.locator('[data-period="1주"]').click()
        assert '1주' in page.locator('.chart svg').get_attribute('aria-label')
        page.screenshot(path=str(out/f'detail-{width}.png'),full_page=True)
        page.locator('.flow[data-go="alert"]').click()
        page.locator('input[name=price]').fill('80000');page.locator('[type=submit]').click()
        assert page.locator('.alertcard').count()==1
        page.reload();page.locator('.alertcard').wait_for()
        assert '80,000' in page.locator('.alertcard').inner_text()
        page.goto(args.url+'#/home');page.locator('.desk-condition').wait_for()
        assert '80,000' in page.locator('.desk-condition').inner_text()
        page.locator('.desk-condition').click()
        page.locator('input[value="근거 변화"]').check();assert not page.locator('#priceField').is_visible()
        page.locator('[type=submit]').click()
        page.locator('[data-toggle]').click();assert page.locator('[data-toggle]').get_attribute('aria-checked')=='false'
        page.locator('[data-delete]').click();assert page.locator('.alertcard').count()==0
        page.goto(args.url+'#/watchlist')
        for _ in range(page.locator('[data-remove-watch]').count()):page.locator('[data-remove-watch]').first.click()
        page.goto(args.url+'#/home')
        assert page.locator('.desk-watch-empty').count()==1
        page.locator('.desk-add').click();assert '#/discover' in page.url
        for route in ('home','discover','stock/005930','forecast/005930','watchlist','alerts','alert/005930','news','results','settings'):
            page.goto(args.url+'#/'+route);page.locator('h1').wait_for()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(width,route)
        page.locator('[data-action="connection"]').click();assert page.locator('dialog').is_visible()
        assert page.locator('input[type=password]').count()==0
        page.keyboard.press('Escape');assert not page.locator('dialog').is_visible()
        page.goto(args.url+'#/home');page.locator('.desk-search').click()
        page.go_back();page.locator('.desk-home').wait_for()
        page.go_forward();page.locator('#stockList').wait_for()
        assert not errors,errors
        checks.append({'width':width,'navigation':'pass','market_switch':'pass','period_switch':'pass','stored_watch':'pass','condition_create_edit_delete':'pass','empty_state':'pass','back_forward':'pass','overflow':'pass','page_errors':errors})
        context.close()
    browser.close()
(out/'checks.json').write_text(json.dumps({'url':args.url,'checks':checks,'market_data_connected':False,'orders':False},ensure_ascii=False,indent=2))
print('DESK_PREVIEW_DESKTOP_MOBILE_NAVIGATION_AND_STORAGE_PASS')
