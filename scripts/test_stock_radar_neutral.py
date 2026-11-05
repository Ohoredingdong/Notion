"""Exercise the canonical operating radar on repository or public data.

The historical filename is retained for existing workflow callers. Assertions
cover the current independent dashboard, including actual user actions; the
removed StockNeutral renderer is deliberately not loaded or reinstalled.
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
        browser = play.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH'))
        try:
            for width, height in [(1440, 900), (1280, 800), (768, 1000), (390, 844)]:
                context = browser.new_context(viewport={'width': width, 'height': height}, reduced_motion='reduce')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url, wait_until='domcontentloaded')
                page.wait_for_function('() => window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length > 0', timeout=60000)
                assert page.locator('.fx-stage-home').is_visible()
                assert page.locator('.fx-v5-markets .nr-index').count() == 4
                assert page.locator('.fx-nav [data-nr-screen]').count() == 7
                assert page.locator('.fx-v5-chartarea .fx-chart-svg polyline').count() >= 1
                assert page.locator('.nr-rail').count() == 0
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 3')
                if width >= 1024:
                    assert page.evaluate('document.documentElement.scrollHeight <= innerHeight + 3')
                source = page.evaluate('''() => {
                    const data = window.StockRadarV2Bridge.snapshot().data;
                    return {company_count:data.raw.companies.length,
                      generated_at:data.raw.generated_at,
                      forecasts_generated_at:data.direction?.generated_at,
                      real_time_connected:data.direction?.real_time_connected};
                }''')
                assert source['real_time_connected'] is False
                page.screenshot(path=str(out / f'home-{width}.png'), full_page=True)

                # Search, selection, and detailed analysis retain the selected issuer.
                page.locator('.fx-nav [data-nr-screen="stocks"]').click()
                first = page.locator('.fx-page-grid .fx-row[data-nr-select]').first
                symbol = first.get_attribute('data-nr-select')
                assert symbol
                page.locator('#fx-search-input').fill(symbol)
                row = page.locator('.fx-row[data-nr-select="' + symbol + '"]')
                assert row.count() == 1
                row.click()
                assert symbol in page.locator('.fx-focus-head').inner_text()
                page.locator('.fx-focus-actions [data-nr-detail]').click()
                assert symbol in page.locator('.fx-detail-v6 .fx-d-security small').inner_text()
                assert page.locator('.fx-detail-primary .fx-chart-svg polyline').count() >= 1
                for period in ('1W', '1M', '3M', '6M'):
                    button = page.locator('[data-fx-period="' + period + '"]').first
                    button.click()
                    assert 'active' in (page.locator('[data-fx-period="' + period + '"]').first.get_attribute('class') or '')
                    assert page.locator('.fx-detail-primary .fx-chart-svg polyline').count() >= 1
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 3')

                page.locator('.fx-nav [data-nr-screen="scenario"]').click()
                assert page.locator('.fx-scenario-v4').is_visible()
                assert page.locator('.fx-scenario-option').count() == 3
                assert '미래 경로' in page.locator('.fx-scenario-v4').inner_text()

                # Conditions and paper holdings are local records, with add/remove behavior.
                page.locator('.fx-nav [data-nr-screen="monitor"]').click()
                assert '실시간' in page.locator('.fx-stage').inner_text()
                page.locator('#radar-rule-value').fill('1')
                page.locator('#radar-rule-form button[type="submit"]').click()
                assert page.locator('.nr-manual-row').count() == 1
                page.locator('[data-nr-rule-remove]').click()
                assert page.locator('.nr-manual-row').count() == 0
                page.locator('.fx-nav [data-nr-screen="portfolio"]').click()
                assert '모의투자' in page.locator('.fx-stage').inner_text()
                page.locator('#radar-paper-qty').fill('2')
                page.locator('#radar-paper-cost').fill('100')
                page.locator('#radar-paper-form button[type="submit"]').click()
                assert page.locator('.nr-paper-overview').count() == 1
                assert page.evaluate('JSON.parse(localStorage.getItem("radar-paper-holdings-v2"))[0].qty') == 2
                page.locator('[data-nr-paper-remove]').click()
                assert page.locator('.nr-paper-overview').count() == 0

                page.locator('.fx-nav-tools [data-nr-screen="news"]').click()
                assert page.locator('.fx-world-panel').count() == 3
                assert page.locator('.fx-world-metric a').count() >= 3
                assert page.locator('.fx-world-article a').count() >= 3
                page.locator('.fx-nav [data-nr-screen="performance"]').click()
                assert page.locator('.fx-audit').is_visible()
                assert '수익성 미입증' in page.locator('.fx-validation-grid').inner_text()
                assert '독립 평가' in page.locator('.fx-table-hint').inner_text()
                page.locator('.fx-nav-tools [data-nr-screen="settings"]').click()
                settings = page.locator('.fx-stage').inner_text()
                assert '자동 주문' in settings and '비활성' in settings
                assert page.locator('a[href="./stock-value-radar-advanced.html"]').count() == 1
                page.locator('.fx-nav [data-nr-screen="home"]').click()
                assert page.locator('.fx-stage-home').is_visible()
                assert page.locator('#fx-search-input').input_value() == ''
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 3')
                assert not errors, errors
                reports.append({'width': width, 'height': height, 'source': source,
                                'navigation': 'pass', 'local_conditions': 'pass',
                                'local_paper_records': 'pass', 'errors': errors})
                context.close()
        finally:
            browser.close()
            (out / 'checks.json').write_text(json.dumps({'url': url, 'public': public, 'checks': reports}, ensure_ascii=False, indent=2))
    print('CANONICAL_OPERATING_RADAR_UI_PASS', reports)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8770/stock-value-radar.html')
    parser.add_argument('--public', action='store_true')
    args = parser.parse_args()
    test(args.url, args.public)
