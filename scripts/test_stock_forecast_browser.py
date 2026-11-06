"""Exercise actual generated output in desktop and mobile; no mock live prices."""
import json
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in [1280, 390]:
        page = browser.new_page(viewport={'width': width, 'height': 900})
        errors = []
        json_response_statuses = []
        failed_resource_types = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        # Log status and type only: no URL query strings or credentials.
        page.on('response', lambda response: json_response_statuses.append(response.status)
                if '/stock-direction-forecast.json' in response.url else None)
        page.on('requestfailed', lambda request: failed_resource_types.append(request.resource_type))
        page.goto('http://127.0.0.1:8769/stock-forecast.html', wait_until='domcontentloaded')
        try:
            page.locator('.fc-tabs').wait_for(timeout=30000)
        except PlaywrightTimeoutError:
            try:
                fallback = page.locator('#directionForecast').inner_text(timeout=1000)[:300]
            except Exception:
                fallback = 'forecast panel unavailable'
            print('FORECAST_BROWSER_TIMEOUT_DIAGNOSTIC ' + json.dumps({
                'viewport_width': width,
                'json_response_statuses': json_response_statuses,
                'failed_resource_types': failed_resource_types,
                'page_errors': errors,
                'visible_panel_text': fallback,
            }, ensure_ascii=False), flush=True)
            raise
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
