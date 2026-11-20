import os,re
from pathlib import Path
from playwright.sync_api import expect, sync_playwright
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
 def check_home_heading():
  assert page.locator('main .rc-title').count()==0
  assert page.get_by_role('heading',name='홈',exact=True).count()==1
  date=page.locator('.rc-primaryline .rc-nav-date')
  expect(date).to_have_text(re.compile(r'^저장 연구 자료 · \d{4}-\d{2}-\d{2}$'),timeout=15000)
  nav=page.locator('.rc-primary').bounding_box()
  badge=date.bounding_box()
  assert badge['x']>=nav['x']+nav['width']-1
  assert abs(badge['y']+badge['height']/2-nav['y']-nav['height']/2)<=1
  assert badge['x']+badge['width']<=page.viewport_size['width']
  assert page.locator('.rc-home').bounding_box()['y']-page.locator('#rc-header').bounding_box()['height']<=14
 def check_macro_cards():
  cards=page.locator('.rc-home-top .rc-macro-card')
  assert cards.count()==2
  assert cards.locator('thead th').all_text_contents()==['경제 지표 변화','연결','산업 영향']*2
  assert cards.locator('h2').all_text_contents()==['세계 경제','한국 경제']
  assert cards.locator('tbody tr').count()==6
  assert cards.locator('.rc-macro-row-icon').count()==6
  assert cards.locator('tbody .rc-macro-arrow').all_text_contents()==['→']*6
  assert cards.evaluate_all("""els=>els.every(card=>{
    const arr=[...card.querySelectorAll('.rc-macro-arrow')].map(x=>x.getBoundingClientRect());
    const impacts=[...card.querySelectorAll('.rc-macro-impact')].map(x=>x.getBoundingClientRect());
    return arr.length===3&&arr.every((a,i)=>a.width>=12&&Math.abs(a.left-arr[0].left)<=1&&a.right<=impacts[i].left+1);
  })""")
  assert all(x for x in cards.locator('.rc-macro-value strong').all_text_contents())
  assert cards.evaluate_all("""els=>els.every(el=>el.scrollWidth<=el.clientWidth+1)""")
  for i,labels in enumerate((('미국 기준금리','미국 10년물','미국 물가'),('한국 기준금리','원/달러','코스피'))):
   rows=cards.nth(i).locator('tbody tr')
   for j,label in enumerate(labels):
    expect(rows.nth(j)).to_contain_text(label)
    expect(rows.nth(j).locator('.rc-macro-value')).to_contain_text(re.compile(r'\d{4}-\d{2}-\d{2}'))
    assert rows.nth(j).locator('a[href^="https://"]').count()>=1,(label,'source link missing')
    assert rows.nth(j).locator('.rc-compare').count()>=1,(label,'numeric direction status missing')
 def check_candidate_width():
  card=page.locator('.rc-home .rc-candidate')
  table=card.locator('table')
  assert table.locator('tbody tr').count()==7
  assert table.locator('td .rc-compare').count()==11
  for label in ['매출','영업이익','영업이익률','영업현금흐름','매출채권 / 재고','부채 / 현금','PER / PBR / ROE']:
   expect(table).to_contain_text(label)
  rects=card.evaluate("""el=>{
    const table=el.querySelector('table'), factors=el.querySelector('.rc-candidate-factors');
    const data=table.getBoundingClientRect(), wrap=el.getBoundingClientRect(), supplementary=factors.getBoundingClientRect();
    const labels=[...table.querySelectorAll('tbody th')].map(x=>x.getBoundingClientRect().width);
    return {fill:data.width/wrap.width, bottom:data.bottom, factorsTop:supplementary.top, labels};
  }""")
  assert rects['fill']>=.87 and rects['factorsTop']>=rects['bottom']-1,rects
  assert all(x>=85 for x in rects['labels']),rects
  for label in ['전망','산업','핵심 성장','협력업체']:
   expect(card.locator('.rc-candidate-factors')).to_contain_text(label)
  if page.viewport_size['height']>=850:
   button=card.locator(':scope > [data-rc-stock]')
   assert button.bounding_box()['y']+button.bounding_box()['height']<=card.bounding_box()['y']+card.bounding_box()['height']+1
 check_home_heading()
 check_macro_cards()
 check_candidate_width()
 assert page.locator('.rc-candidate').inner_text().find('오늘의 매수후보 검토')>=0
 assert page.locator('.rc-industry-list article').count()>0
 assert '전체 업종 지수 아님' in page.locator('.rc-industry-list').locator('..').inner_text()
 assert page.locator('.rc-headline-list article').count()<=10
 more=page.locator('[data-rc-news-more]')
 if more.count():
  more.click()
  assert more.get_attribute('aria-expanded')=='true'
  assert page.locator('.rc-headline-list article').count()>10
  assert page.evaluate('document.documentElement.scrollHeight <= innerHeight+2')
  more.click()
  assert page.locator('.rc-headline-list article').count()==10
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
   if key=='home':
    check_home_heading()
    check_macro_cards()
 # A fixed outer page alone is not enough: every dashboard card must still
 # fit in the view, including the bottom row at short Windows notebook sizes.
 keys=['home','market','quality','finance','value','filings','chart']
 for width,height in [(1600,900),(1331,894),(1366,650),(1024,600)]:
  page.set_viewport_size({'width':width,'height':height})
  page.goto(base+'?tab=home&country=KR&stock=005930',wait_until='domcontentloaded')
  page.locator('#rc-home-rows [data-rc-stock]').first.wait_for(timeout=35000)
  for key in keys:
   if key in ('quality','finance','value','filings','chart'):
    loc=page.locator('.rc-subnav [data-rc-tab="'+key+'"]')
    if not loc.count():
     page.locator('.rc-primary [data-rc-tab="'+('quality' if key in ('finance','value') else key)+'"]').click()
    else: loc.click()
   else: page.locator('.rc-primary [data-rc-tab="'+key+'"]').click()
   view=page.locator('.rc-view[data-rc-page="'+key+'"]')
   view.wait_for()
   metrics=view.evaluate("""el=>{
    const v=el.getBoundingClientRect(), cards=[...el.querySelectorAll('.rc-card,.rcm-card')].map(x=>{
      const r=x.getBoundingClientRect();
      return {top:Math.round(r.top-v.top),bottom:Math.round(r.bottom-v.bottom),height:Math.round(r.height),title:x.querySelector('h2,h3,h4')?.textContent};
    });
    return {h:innerHeight,width:innerWidth,doc:document.documentElement.scrollHeight,docWidth:document.documentElement.scrollWidth,
       stage:el.clientHeight,content:el.scrollHeight,cards};
   }""")
   assert metrics['doc']<=height+2 and metrics['docWidth']<=width+2,(width,height,key,metrics)
   assert metrics['content']<=metrics['stage']+2,(width,height,key,'whole tab overflows',metrics)
   count={'home':7,'market':5,'quality':5,'finance':9,'value':9,'filings':4,'chart':7}[key]
   assert len(metrics['cards'])>=count,(width,height,key,'missing cards',metrics)
   assert all(x['top']>=-2 and x['bottom']<=2 and x['height']>=25 for x in metrics['cards']),(width,height,key,'a card is clipped',metrics)
   if key=='home': check_macro_cards()
   if key=='home' and width>=1280: check_candidate_width()
   if key=='home' and height>=850:
    for selector in ('.rc-headline-list','.rc-industry-list'):
     count=page.locator(selector).evaluate("""list=>{
       const box=list.getBoundingClientRect(), rows=[...list.querySelectorAll('article')];
       return {count:rows.length, visible:rows.filter(r=>{const b=r.getBoundingClientRect();return b.top>=box.top-1&&b.bottom<=box.bottom+1}).length};
     }""")
     assert count['visible']>=min(5,count['count']),(width,height,selector,'not enough rows visible on arrival',count)

   if key=='chart':
    assert all(s.bounding_box()['height']>=40 for s in page.locator('.rcc-main svg').all())
    details=page.locator('.rcc details').first
    details.locator('summary').click()
    assert details.get_attribute('open') is not None
    assert page.evaluate('document.documentElement.scrollHeight <= innerHeight+2')
    details.locator('summary').click()
  print(f'PASS: all seven tabs fit without page or tab scrolling at {width}×{height}')
 assert not errors,errors
 print('PASS: seven pages, 4 indices, 10 countries, search, watchlist, company carry, Back/reload, country switch, chart, desktop/mobile/iframe viewport proxy')
 print('HTTP failures:',bad)
