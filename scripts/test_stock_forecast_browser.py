"""Exercise actual generated output in desktop and mobile; no mock live prices."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in [1280, 390]:
        page = browser.new_page(viewport={'width': width, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('http://127.0.0.1:8769/stock-forecast.html', wait_until='domcontentloaded')
        page.locator('.fc-tabs').wait_for(timeout=30000)
        page.locator('[data-fc="intraday"]').click()
        page.locator('.fc-card').first.wait_for()
        page.locator('[data-fc="daily"]').click()
        assert page.locator('.fc-card').count() > 0
        assert not errors, errors
        bounds = page.locator('#directionForecast').bounding_box()
        assert bounds['x'] >= 0 and bounds['x']+bounds['width'] <= width+1
        page.screenshot(path=f'forecast-{width}.png', full_page=True)
        page.close()
    browser.close()
print('Desktop/mobile actual forecast display passed')
