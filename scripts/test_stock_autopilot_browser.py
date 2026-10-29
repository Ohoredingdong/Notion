"""Render actual generated controller JSON; no simulated production prices."""
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (1280,390):
            page=browser.new_page(viewport={'width':width,'height':900})
            page.goto('http://127.0.0.1:8769/stock-forecast.html',wait_until='domcontentloaded')
            if not page.locator('script[src*="stock-forecast-autopilot.js"]').count():
                page.add_script_tag(url='http://127.0.0.1:8769/assets/stock-forecast-autopilot.js')
            page.locator('#forecastAutopilot .ap-badges').wait_for(timeout=30000)
            text=page.locator('#forecastAutopilot').inner_text()
            assert '자동 주문은 꺼져' in text
            assert '미입증' in text
            rect=page.locator('#forecastAutopilot').bounding_box()
            assert rect['x']>=-1 and rect['x']+rect['width']<=width+1
            page.screenshot(path=f'forecast-autopilot-{width}.png',full_page=True)
            page.close()
        browser.close()
    print('Actual autopilot desktop/mobile screen and truthful status checks passed')

if __name__=='__main__':main()
