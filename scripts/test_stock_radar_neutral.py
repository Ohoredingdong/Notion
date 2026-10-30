"""Exercise the actual reference-structured operating radar using repository snapshots."""
import argparse,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright

def test(url='http://127.0.0.1:8770/stock-value-radar.html',public=False):
    root=Path(__file__).resolve().parents[1]
    out=root/'neutral-ui-evidence';out.mkdir(exist_ok=True)
    reports=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH'))
        for width in [1440,1280,768,390]:
            context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            if not public:
                def source(route):
                    path=route.request.url.split('/main/',1)[-1].split('?',1)[0]
                    file=root/path
                    if file.exists():
                        route.fulfill(path=str(file),content_type='application/json' if path.endswith('.json') else 'text/plain')
                    else:
                        route.fulfill(status=404,body='not included')
                page.route('https://raw.githubusercontent.com/Ohoredingdong/Notion/main/**',source)

            page.goto(url,wait_until='domcontentloaded')
            page.wait_for_function('window.StockNeutral?.snapshot?.company_count > 0',timeout=60000)
            assert page.locator('#view-home').is_visible()
            assert page.locator('.nr-index').count()==4
            assert page.locator('.nr-home-actions button').count()>=7
            assert page.locator('#nr-home-alerts').count()==1
            assert page.locator('#nr-home-picks').count()==1
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            data=page.evaluate('window.StockNeutral.snapshot');assert data['orders_enabled'] is False
            page.screenshot(path=str(out/f'home-{width}.png'),full_page=True)

            # Stock list -> deep company detail
            page.locator('.nr-rail [data-nr-screen="stocks"]').click()
            assert page.locator('.nr-stock-list').is_visible()
            first=page.locator('.nr-stock-list [data-nr-detail]').first
            symbol=first.get_attribute('data-nr-detail')
            assert symbol
            first.click()
            assert page.locator('#view-detail').is_visible()
            assert page.locator('#detailBody').inner_text().strip()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')

            # Monitoring screen
            page.locator('.nr-rail [data-nr-screen="home"]').click()
            page.locator('.nr-rail [data-nr-screen="monitor"]').click()
            assert page.locator('.nr-status-banner').is_visible()
            assert page.locator('.nr-monitor-list').is_visible()

            # Scenario screen from the home action
            page.locator('.nr-rail [data-nr-screen="home"]').click()
            page.locator('.nr-home-actions [data-nr-screen="scenario"]').click()
            assert page.locator('.nr-scenario-cards').is_visible()
            assert page.locator('.nr-prob-bars').is_visible()

            # Portfolio/paper screen
            page.locator('.nr-rail [data-nr-screen="home"]').click()
            page.locator('.nr-home-actions [data-nr-screen="portfolio"]').click()
            assert '포트폴리오' in page.locator('#nr-home-content').inner_text()
            assert '모의투자' in page.locator('#nr-home-content').inner_text()

            # News and macro
            page.locator('.nr-rail [data-nr-screen="home"]').click()
            page.locator('.nr-home-actions [data-nr-screen="news"]').click()
            assert '뉴스 & 경제 브리핑' in page.locator('#nr-home-content').inner_text()
            assert page.locator('.nr-news-grid').is_visible()

            # Forecast performance
            page.locator('.nr-rail [data-nr-screen="home"]').click()
            page.locator('.nr-home-actions [data-nr-screen="performance"]').click()
            assert '성과 검증' in page.locator('#nr-home-content').inner_text()
            assert page.locator('.nr-performance-grid').is_visible()

            # Settings -> source verification
            page.locator('.nr-rail [data-nr-screen="settings"]').click()
            assert '설정 & 연결 관리' in page.locator('#nr-home-content').inner_text()
            page.get_by_role('button',name='원자료 검증 화면 열기').click()
            assert page.locator('#view-system').is_visible()
            assert '수집 시각과 기준' in page.locator('#systemBody').inner_text()

            # Legacy research remains reachable.
            page.locator('.nr-rail [data-nr-view="discover"]').click()
            assert page.locator('#view-discover').is_visible()
            page.locator('.nr-rail [data-nr-screen="home"]').click()
            assert page.locator('#view-home').is_visible()

            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            assert not errors,errors
            reports.append({
                'width':width,
                'operating_home':True,
                'source':data,
                'navigation':'pass',
                'screens':['home','stocks','detail','monitor','scenario','portfolio','news','performance','settings','system'],
                'orders_enabled':False,
                'errors':errors
            })
            context.close()
        browser.close()
    (out/'checks.json').write_text(json.dumps({'url':url,'public':public,'checks':reports},ensure_ascii=False,indent=2))
    print('ACTUAL_REFERENCE_STRUCTURED_RADAR_UI_PASS',reports)

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--url',default='http://127.0.0.1:8770/stock-value-radar.html')
    a.add_argument('--public',action='store_true')
    x=a.parse_args()
    test(x.url,x.public)
