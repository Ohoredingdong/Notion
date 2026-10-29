"""Render actual evaluation JSON; check no error and no horizontal overflow."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
expected=json.loads(Path('stock-forecast-learning.json').read_text())
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in (1280,390):
        page=browser.new_page(viewport={'width':width,'height':1000});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8769/stock-forecast.html',wait_until='domcontentloaded')
        page.wait_for_selector('#forecastLearning .fl-grid',timeout=30000)
        text=page.locator('#forecastLearning').inner_text()
        assert '100%' in text and '실시간 연결 미완료' in text
        assert str(expected['overall']['correct']) in text
        page.locator('#forecastLearning summary').first.click()
        assert '예약 실행 시도 기준' in page.locator('#forecastLearning').inner_text()
        bounds=page.locator('#forecastLearning').bounding_box()
        assert bounds['x']>=-1 and bounds['x']+bounds['width']<=width+1
        assert not errors,errors
        page.screenshot(path=f'forecast-learning-{width}.png',full_page=True)
        page.close()
    browser.close()
print('Actual learning report: desktop/mobile, empty/observed counts, no runtime errors passed')
