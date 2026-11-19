import os,re
from pathlib import Path
from playwright.sync_api import sync_playwright
base=os.environ.get('RADAR_URL','http://127.0.0.1:4187/stock-radar-research.html')
with sync_playwright() as pw:
 exe=os.environ.get('BROWSER_EXECUTABLE')
 b=pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
 page=b.new_page(viewport={'width':1600,'height':900})
 errors=[]; bad=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.on('response',lambda r:bad.append((r.status,r.url)) if r.status>=400 and '127.0.0.1' in r.url else None)
 page.goto(base,wait_until='domcontentloaded')
 page.wait_for_function("document.querySelector('#rc-engine').contentWindow.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length>0",timeout=35000)
 page.locator('#rc-home-rows [data-rc-stock]').first.wait_for()
 assert page.locator('[data-rc-country]').count()==10
 assert page.locator('.rc-index').count()==4
 assert page.locator('.rc-candidate').inner_text().find('오늘의 매수후보 검토')>=0
 first=page.locator('.rc-candidate h3').inner_text()
 page.locator('[data-rc-choice="1"]').click()
 assert page.locator('.rc-candidate h3').inner_text()!=first
 q=page.locator('#rc-home-search');q.fill('005930')
 row=page.locator('#rc-home-rows .rc-stockrow').first
 assert '삼성전자' in row.inner_text()
 row.locator('[data-rc-star]').click()
 assert page.locator('.rc-home-side').first.inner_text().count('삼성전자')>=2
 row.locator('[data-rc-stock]').click()
 assert '삼성전자' in page.locator('.rc-selection').inner_text()
 assert '질적 분석' == page.locator('main h1').inner_text()
 for key,label in [('finance','재무'),('value','가치·전망'),('filings','공시'),('chart','차트')]:
  page.locator('.rc-subnav [data-rc-tab="'+key+'"]').click()
  assert label == page.locator('main h1').inner_text()
  assert '삼성전자' in page.locator('.rc-selection').inner_text()
  assert page.locator('main .rc-card').count()>=1
  assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+2')
  if key=='filings':
   details=page.locator('main details').first
   details.locator('summary').click()
   assert details.get_attribute('open') is not None
  if key=='chart':
   assert page.locator('main svg').count()>=2
   page.locator('main [data-rcc-span="21"]').click()
  if os.environ.get('RADAR_SCREENSHOTS'): page.screenshot(path=str(Path(os.environ['RADAR_SCREENSHOTS'])/('radar-cohesive-'+key+'.png')),full_page=True)
 page.go_back();assert '공시'==page.locator('main h1').inner_text()
 page.reload(wait_until='domcontentloaded')
 page.wait_for_function("document.querySelector('.rc-selection')?.textContent.includes('삼성전자')")
 page.locator('.rc-primary [data-rc-tab="market"]').click()
 panel=page.locator('.rcm-industry-scroll')
 sector=panel.get_by_role('button',name=re.compile('반도체')).first
 sector_label=sector.inner_text()
 sector.click()
 assert '선택 산업: '+sector_label in page.locator('main').inner_text()
 assert page.locator('main .rcm-card').count()>=1
 page.locator('[data-rc-country="US"]').click()
 assert page.locator('[data-rc-country="US"]').get_attribute('aria-pressed')=='true'
 page.locator('[data-rc-country="JP"]').click()
 assert '삼성전자' not in page.locator('.rc-selection').inner_text()
 page.locator('[data-rc-country="KR"]').click()
 page.locator('.rc-primary [data-rc-tab="home"]').click()
 assert '삼성전자' in page.locator('.rc-home-side').inner_text()
 if os.environ.get('RADAR_SCREENSHOTS'): page.screenshot(path=str(Path(os.environ['RADAR_SCREENSHOTS'])/'radar-cohesive-home.png'),full_page=True)
 for width,height in [(390,844),(850,650)]:
  page.set_viewport_size({'width':width,'height':height})
  for key in ['home','market','quality','finance','value','filings','chart']:
   page.goto(base+'?tab='+key+'&country=KR&stock=005930',wait_until='domcontentloaded')
   page.wait_for_function("document.querySelector('#rc-engine').contentWindow.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length>0",timeout=35000)
   page.wait_for_selector('main .rcm-card' if key=='market' else 'main .rc-card')
   assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+2'),(width,key,page.evaluate('document.documentElement.scrollWidth'))
 assert not errors,errors
 print('PASS: seven pages, 4 indices, 10 countries, search, watchlist, company carry, Back/reload, country switch, chart, desktop/mobile/iframe viewport proxy')
 print('HTTP failures:',bad)
