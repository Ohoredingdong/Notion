"""Exercise actual operating page using real JSON snapshots, never mock financial values."""
import argparse,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright

def test(url='http://127.0.0.1:8770/stock-value-radar.html',public=False):
    root=Path(__file__).resolve().parents[1];out=root/'neutral-ui-evidence';out.mkdir(exist_ok=True)
    reports=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH'))
        for width in [1440,1280,768,390]:
            context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            if not public:
                def source(route):
                    path=route.request.url.split('/main/',1)[-1].split('?',1)[0];f=root/path
                    if f.exists():route.fulfill(path=str(f),content_type='application/json' if path.endswith('.json') else 'text/plain')
                    else:route.fulfill(status=404,body='not included')
                page.route('https://raw.githubusercontent.com/Ohoredingdong/Notion/main/**',source)
            page.goto(url,wait_until='domcontentloaded')
            page.wait_for_function('window.StockNeutral?.snapshot?.company_count > 0',timeout=60000)
            assert page.locator('#view-home').is_visible()
            assert page.locator('.nr-index').count()==4
            assert page.locator('#nr-price-svg [data-series]').count() in [0,3]
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            data=page.evaluate('window.StockNeutral.snapshot');assert data['orders_enabled'] is False
            page.screenshot(path=str(out/f'home-{width}.png'),full_page=True)
            page.locator('[data-nr-select="000660"]').first.click()
            assert 'SK하이닉스' in page.locator('#nr-company').inner_text()
            assert page.locator('#view-home').is_visible()
            old=page.locator('#nr-company [data-nr-star]').get_attribute('aria-pressed')
            page.locator('#nr-company [data-nr-star]').click()
            assert page.locator('#nr-company [data-nr-star]').get_attribute('aria-pressed')!=old
            page.locator('#nr-company [data-nr-star]').click()
            page.locator('[data-nr-range="1M"]').click()
            assert 'active' in page.locator('[data-nr-range="1M"]').get_attribute('class')
            if page.locator('#nr-chart-hit').count():
                page.locator('#nr-chart-hit').focus();page.keyboard.press('ArrowRight')
                assert page.locator('#nr-tooltip').is_visible()
                assert page.locator('#nr-chart-hit').get_attribute('aria-valuenow')=='1'
            page.locator('[data-nr-remove="035420"]').click()
            page.locator('#nr-search').fill('NVIDIA')
            page.locator('input[data-nr-compare="NVDA"]').check()
            page.locator('[data-nr-mode="price"]').click()
            assert page.locator('#nr-dialog').is_visible()
            assert '통화' in page.locator('#nr-dialog').inner_text()
            page.locator('#nr-dialog button').click()
            page.locator('#nr-search').fill('삼성전자')
            assert '삼성전자' in page.locator('#nr-watch-panel').inner_text()
            page.locator('[data-nr-select="005930"]').first.click()
            page.wait_for_function("document.querySelectorAll('#companySelect option').length>0",timeout=45000)
            page.locator('[data-nr-detail="005930"]').click()
            assert page.locator('#view-detail').is_visible()
            assert '삼성전자' in page.locator('#detailBody').inner_text()
            page.locator('.nr-rail [data-nr-view="home"]').click()
            assert page.locator('#view-home').is_visible()
            page.locator('.nr-rail [data-nr-view="discover"]').click()
            assert page.locator('#view-discover').is_visible()
            page.locator('.nr-rail [data-nr-view="system"]').click()
            assert page.locator('#view-system').is_visible()
            page.locator('.nr-rail [data-nr-view="home"]').click()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            assert not errors,errors
            reports.append({'width':width,'operating_home':True,'source':data,'navigation':'pass','watch_sync':'pass','comparison':'pass','mixed_currency_guard':'pass','errors':errors})
            context.close()
        browser.close()
    (out/'checks.json').write_text(json.dumps({'url':url,'public':public,'checks':reports},ensure_ascii=False,indent=2))
    print('ACTUAL_OPERATING_NEUTRAL_UI_INTERACTIONS_PASS',reports)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--url',default='http://127.0.0.1:8770/stock-value-radar.html');a.add_argument('--public',action='store_true');x=a.parse_args();test(x.url,x.public)
