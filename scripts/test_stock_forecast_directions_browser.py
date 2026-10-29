"""Browser assertions read the actual newly generated JSON, never fixture scores."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

source=json.loads(Path('stock-forecast-learning.json').read_text())
audit=source['directional_research']
assert audit['version']=='direction-specialists-1.0'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    try:
        for width in (1280,390):
            page=browser.new_page(viewport={'width':width,'height':1000})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto('http://127.0.0.1:8769/stock-forecast.html',wait_until='domcontentloaded')
            expect(page.locator('#directionQuality [data-direction]')).to_have_count(3)
            for direction in ('up','down','flat'):
                row=audit['actual_direction_quality']['directions'][direction]
                expect(page.locator(f'#directionQuality [data-direction="{direction}"] .dq-main')).to_have_text(f"{row['correct']:,} / {row['actual']:,}")
            page.locator('#directionQuality details').first.locator('summary').click()
            expect(page.locator('#directionQuality .dq-scroll')).to_be_visible()
            box=page.locator('#directionQuality').bounding_box()
            assert box['x']>=-1 and box['x']+box['width']<=width+1
            assert not errors,errors
            page.locator('#directionQuality').screenshot(path=f'forecast-directions-{width}.png')
            page.close()
        print('Actual per-direction data, absent classes and 1280/390 layouts verified')
    finally:
        browser.close()
