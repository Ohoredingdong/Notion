"""Browser acceptance gate for the current clean-bridge/flow-v2 operating radar.

Runs on four real-data viewport widths. Does NOT prove trading usefulness, source
exchange authenticity, user receipt, or filled orders. Replaces the retired
StockNeutral/.nr-rail selectors with assertions against the actual deployed
page contract; keeps source, safety, navigation and layout coverage.
"""
import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright


def test(url='http://127.0.0.1:8770/stock-value-radar.html', public=False):
    root = Path(__file__).resolve().parents[1]
    out = root / 'neutral-ui-evidence'
    out.mkdir(exist_ok=True)
    reports = []
    with sync_playwright() as play:
        browser = play.chromium.launch(
            headless=True,
            executable_path=os.environ.get('CHROMIUM_PATH')
        )
        try:
            for width in (1440, 1280, 768, 390):
                context = browser.new_context(
                    viewport={'width': width, 'height': 1000},
                    reduced_motion='reduce'
                )
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    page.locator('.fx-topbar').wait_for(timeout=25000)
                    page.wait_for_function(
                        "() => !!(window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length)",
                        timeout=35000
                    )
                    data = page.evaluate("window.StockRadarV2Bridge.snapshot()")
                    assert len(data['data']['raw']['companies']) > 0
                    assert data['data']['autopilot']['orders_enabled'] is False
                    assert data['data']['direction']['policy']['live_order_enabled'] is False
                    assert page.locator('#view-home').is_visible()
                    assert page.locator('.fx-v5-markets .nr-index').count() == 4
                    assert page.locator('.fx-nav [data-nr-screen]').count() >= 7
                    assert page.locator('.fx-v5-main .fx-list-panel').count() == 1
                    assert page.locator('.fx-v5-main .fx-v5-cockpit').count() == 1
                    assert page.locator('.fx-v5-main .fx-v5-aside').count() == 1
                    assert page.locator('.fx-v5-aside .fx-v5-sidecard').count() == 4
                    assert '실시간 시세 아님' in page.locator('.fx-mode-badge').inner_text() or '실시간 시세 아님' in page.locator('#source-status').inner_text()
                    assert '연구용' in page.locator('.fx-v5-cockpit .fx-v5-ai').inner_text()
                    no_overflow(page)
                    page.screenshot(path=str(out / f'home-{width}.png'), full_page=True)

                    # Stock list: changing selection updates the matching focus.
                    nav(page, 'stocks')
                    rows = page.locator('.fx-page-grid .fx-row[data-nr-select]')
                    assert rows.count() > 0
                    first = rows.first
                    ticker = first.get_attribute('data-nr-select')
                    assert ticker
                    first.click()
                    assert ticker in page.locator('.fx-focus-head').inner_text()
                    page.locator('.fx-focus-actions [data-nr-detail]').click()
                    assert page.locator('.fx-stage[data-screen="stockdetail"]').count() == 1
                    assert page.locator('.fx-detail-content').is_visible()
                    no_overflow(page)

                    nav(page, 'monitor')
                    assert page.locator('#radar-rule-form').is_visible()
                    assert '실시간' in page.locator('.fx-stage').inner_text()
                    no_overflow(page)

                    nav(page, 'scenario')
                    assert page.locator('.fx-scenario-v4').is_visible()
                    assert page.locator('.fx-scenario-option').count() == 3
                    no_overflow(page)

                    nav(page, 'portfolio')
                    assert '모의' in page.locator('.fx-stage').inner_text()
                    assert page.locator('.nr-screen-head').is_visible()
                    no_overflow(page)

                    page.locator('.fx-nav-tools [data-nr-screen="news"]').click()
                    assert page.locator('.nr-news-grid').is_visible()
                    no_overflow(page)

                    nav(page, 'performance')
                    assert page.locator('.nr-performance-grid').count() == 1
                    assert page.locator('.nr-performance-grid .nr-panel').count() == 4
                    assert '미입증' in page.locator('.fx-stage').inner_text()
                    no_overflow(page)

                    page.locator('.fx-nav-tools [data-nr-screen="settings"]').click()
                    assert page.locator('.nr-setting-row').count() >= 3
                    settings = page.locator('.fx-stage').inner_text()
                    assert '자동 주문' in settings and '비활성' in settings
                    assert page.locator('a[href="./stock-value-radar-advanced.html"]').count() >= 1
                    no_overflow(page)

                    nav(page, 'home')
                    assert page.locator('.fx-v5-cockpit').is_visible()
                    no_overflow(page)
                    assert not errors, errors
                    reports.append({
                        'width': width,
                        'operating_home': True,
                        'loaded_companies': len(data['data']['raw']['companies']),
                        'navigation': 'pass',
                        'screens': [
                            'home', 'stocks', 'stockdetail', 'monitor',
                            'scenario', 'portfolio', 'news', 'performance',
                            'settings', 'advanced-link'
                        ],
                        'orders_enabled': False,
                        'errors': errors
                    })
                finally:
                    context.close()
        finally:
            browser.close()
    (out / 'checks.json').write_text(
        json.dumps({'url': url, 'public': public, 'checks': reports},
                   ensure_ascii=False, indent=2)
    )
    assert len(reports) == 4, 'Every required viewport must pass the same assertions'
    print('CURRENT_CLEAN_BRIDGE_RADAR_UI_PASS', reports)


def nav(page, screen):
    page.locator(f'.fx-nav [data-nr-screen="{screen}"]').click()
    assert page.locator(f'.fx-stage[data-screen="{screen}"]').count() == 1


def no_overflow(page):
    assert page.evaluate(
        'document.documentElement.scrollWidth <= innerWidth + 1 && document.body.scrollWidth <= innerWidth + 1'
    ), 'Horizontal overflow is not permitted at this width or screen'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8770/stock-value-radar.html')
    parser.add_argument('--public', action='store_true')
    args = parser.parse_args()
    test(args.url, args.public)
