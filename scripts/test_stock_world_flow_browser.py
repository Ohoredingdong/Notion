"""Independent actual-feed UI acceptance for the world-market summary.

Uses saved source bytes and the actual clock. Synthetic adversarial contracts are
covered separately by test_stock_world_flow.cjs; no fixture is published here.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

IDS = ('kospi', 'kosdaq', 'sp500', 'nasdaq', 'dax', 'shanghai', 'nikkei225',
       'hang_seng', 'usdkrw', 'dxy', 'us10y', 'wti', 'gold', 'vix')
REGIONS = {'KR': ('kospi', 'kosdaq'), 'US': ('sp500', 'nasdaq'), 'EU': ('dax',),
           'CN': ('shanghai',), 'JP': ('nikkei225',), 'HK': ('hang_seng',)}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.timestamp() if parsed.tzinfo else float('nan')
    except (ValueError, TypeError):
        return float('nan')


def oracle(feed, now):
    assert feed.get('version') == 'stock-world-flow-v1'
    assert finite(timestamp(feed.get('generated_at'))) and timestamp(feed['generated_at']) <= now + 300
    rows = feed.get('indicators', [])
    assert len(rows) == len(IDS) and {row.get('id') for row in rows} == set(IDS), 'Exactly fourteen unique source identities required'
    observed = {}
    for row in rows:
        key = row['id']
        if row.get('status') == 'unavailable':
            observed[key] = {'current': False, 'value': None, 'change': None, 'direction': 'unknown'}
            continue
        source = row.get('source', {})
        assert source.get('identity_verified') is True and source.get('provider_symbol') == source.get('response_symbol'), key
        assert urlsplit(source.get('url', '')).scheme == 'https', key
        assert finite(row.get('value')) and row['value'] > 0, key
        assert finite(timestamp(row.get('received_at'))) and timestamp(row['received_at']) <= now + 300, key
        precision = row.get('observed_at_precision')
        if precision == 'source_date':
            assert row.get('observed_at') is None, key + ': date-only observation must not invent a clock'
        else:
            assert precision == 'exchange_close' and finite(timestamp(row.get('observed_at'))) and timestamp(row['observed_at']) <= now + 300, key
        if key == 'us10y':
            assert precision == 'source_date' and source.get('provider_symbol') == 'BC_10YEAR' and source.get('field') == 'BC_10YEAR' and source.get('source_unit') == 'percent', key
            assert row.get('session', '') <= datetime.fromtimestamp(now, ZoneInfo('America/New_York')).date().isoformat(), 'Treasury source date must not be in the future in New York'
        delta = pct = bp = None
        verified = row.get('comparison_verified') is True
        if verified:
            assert finite(row.get('previous_value')) and row['previous_value'] > 0, key
            assert row.get('previous_session', '') < row.get('session', ''), key
            delta = row['value'] - row['previous_value']
            assert math.isclose(row['change_value'], delta, abs_tol=1e-5, rel_tol=1e-8), key
            if key == 'us10y':
                bp = delta * 100
                assert row.get('change_pct') is None and math.isclose(row['change_bp'], bp, abs_tol=1e-5, rel_tol=1e-8), key
            else:
                pct = delta / row['previous_value'] * 100
                assert math.isclose(row['change_pct'], pct, abs_tol=1e-5, rel_tol=1e-8) and row.get('change_bp') is None, key
            direction = 'up' if delta > 0 else 'down' if delta < 0 else 'flat'
            assert row.get('direction') == direction, key
        else:
            direction = 'unknown'
        freshness = row.get('freshness', {})
        expected = row.get('expected_session')
        next_day, next_time = freshness.get('next_expected_session'), timestamp(freshness.get('next_check_after'))
        clock = bool(expected and next_day and next_day > expected and next_day > row.get('session', '') and finite(next_time))
        if clock and now >= next_time:
            expected = max(expected, next_day)
        matching = row.get('session') >= expected if key == 'us10y' and expected else row.get('session') == expected
        current = bool(verified and clock and row.get('status') == 'current'
                       and freshness.get('status') == 'current' and matching)
        observed[key] = {'current': current, 'value': row['value'], 'change': bp if key == 'us10y' else pct,
                         'direction': direction, 'precision': precision, 'session': row.get('session')}
    regions = {}
    counts = {'up': 0, 'down': 0, 'flat': 0, 'mixed': 0, 'unknown': 0}
    for key, members in REGIONS.items():
        basis = [observed[name] for name in members if observed[name]['current']]
        moves = {row['direction'] for row in basis}
        move = next(iter(moves)) if len(moves) == 1 else 'mixed' if moves else 'unknown'
        complete = len(basis) == len(members)
        regions[key] = {'direction': move, 'complete': complete}
        counts[move if complete else 'unknown'] += 1
    return {'rows': observed, 'regions': regions, 'counts': counts,
            'current': sum(row['current'] for row in observed.values()), 'total': len(IDS)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root', type=Path, default=Path('.'))
    parser.add_argument('--base', default='http://127.0.0.1:8765/stock-value-radar.html')
    parser.add_argument('--out', type=Path, default=Path('radar-world-flow-evidence'))
    parser.add_argument('--oracle-only', action='store_true')
    args = parser.parse_args()
    root, out = args.data_root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    data = (root / 'stock-world-flow.json').read_bytes()
    feed = json.loads(data)
    report = {'source_sha256': hashlib.sha256(data).hexdigest(), 'generated_at': feed.get('generated_at'),
              'checks': [], 'screenshots': [], 'source': None,
              'limitations': ['Saved completed-session observations; no live quote or investment recommendation.']}

    def check(name, passed, detail=None):
        report['checks'].append({'name': name, 'pass': bool(passed), 'detail': detail})
        if not passed:
            raise AssertionError(f'{name}: {detail}')

    def route_saved(route):
        path = unquote(urlsplit(route.request.url).path).lstrip('/')
        file = (root / path).resolve()
        if path.endswith(('.json', '.jsonl')) and file.is_relative_to(root) and file.is_file():
            route.fulfill(status=200, body=file.read_bytes(), content_type='application/json' if path.endswith('.json') else 'application/x-ndjson')
        else:
            route.continue_()

    try:
        report['source'] = oracle(feed, datetime.now(timezone.utc).timestamp())
        check('All fourteen actual-source records pass independent arithmetic and provenance checks', True)
        if args.oracle_only:
            report['browser_executed'] = False
            print('WORLD_FLOW_SOURCE_ORACLE', json.dumps(report['source'], ensure_ascii=False))
            return
        from playwright.sync_api import sync_playwright
        report['browser_executed'] = True
        with sync_playwright() as play:
            browser = play.chromium.launch(headless=True)
            try:
                for width, height in ((1440, 900), (1366, 768), (920, 680), (390, 844), (360, 640)):
                    context = browser.new_context(viewport={'width': width, 'height': height}, color_scheme='light', reduced_motion='reduce')
                    context.route('**/*', route_saved)
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    try:
                        page.goto(args.base, wait_until='domcontentloaded')
                        page.wait_for_function("() => !!window.StockRadarV2Bridge?.snapshot()?.data?.raw?.companies?.length && window.StockRadarV2Bridge.snapshot().data.worldFlow?.version==='stock-world-flow-v1'", timeout=45000)
                        expected = oracle(feed, datetime.now(timezone.utc).timestamp())
                        card = page.locator('.fx-worldflow')
                        check(f'{width}: one world summary and six regional directions', card.count() == 1 and card.locator('[data-worldflow-region]').count() == 6)
                        check(f'{width}: current count uses per-market observation clocks', card.locator('[data-worldflow-current]').get_attribute('data-worldflow-current') == str(expected['current'])
                              and f"확인 {expected['current']}/14" in card.locator('[data-worldflow-current]').inner_text())
                        for key, region in expected['regions'].items():
                            chip = card.locator(f'[data-worldflow-region="{key}"]')
                            check(f'{width}: {key} regional direction agrees with its source signs', chip.get_attribute('data-direction') == region['direction'])
                        check(f'{width}: no unsupported aggregate world score', '종합 점수' not in card.locator('.fx-worldflow-head').inner_text())
                        closed = page.evaluate("""() => {
                            const b=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,bottom:r.bottom}};
                            const card=document.querySelector('.fx-worldflow'),strip=document.querySelector('.fx-v5-marketline'),main=document.querySelector('.fx-v5-main');
                            return {card:b(card),strip:b(strip),main:b(main),inner:innerWidth,scroll:document.documentElement.scrollWidth,
                              contentHeight:card.scrollHeight,clientHeight:card.clientHeight};
                        }""")
                        check(f'{width}: closed summary fits without clipped content or horizontal overflow',
                              closed['scroll'] <= width + 2 and closed['card']['x'] >= -1
                              and closed['card']['x'] + closed['card']['w'] <= width + 1
                              and closed['contentHeight'] <= closed['clientHeight'] + 2, closed)
                        check(f'{width}: market strip does not overlap research workspace', closed['main']['y'] >= closed['strip']['bottom'] - 1, closed)
                        if width >= 1180:
                            check(f'{width}: desktop strip preserves its bounded height', closed['strip']['h'] <= 150, closed)
                        shot = out / f'world-flow-{width}-summary.png'
                        page.screenshot(path=str(shot), full_page=True)
                        report['screenshots'].append(str(shot))
                        card.locator('[data-worldflow-open]').click()
                        dialog = page.locator('.fx-worldflow-dialog[open]')
                        check(f'{width}: source details open accessibly', dialog.count() == 1 and dialog.get_attribute('aria-labelledby') == 'fx-worldflow-dialog-title')
                        check(f'{width}: all fourteen observations remain available in details', dialog.locator('[data-worldflow-indicator]').count() == 14)
                        for key, row in expected['rows'].items():
                            detail = dialog.locator(f'[data-worldflow-indicator="{key}"]')
                            shown = detail.locator('[data-worldflow-value]').inner_text()
                            if row['value'] is None:
                                check(f'{width}: {key} unavailable value is not invented', shown == '미확인', shown)
                            else:
                                number = re.search(r'-?[\d,]+(?:\.\d+)?', shown)
                                check(f'{width}: {key} displayed value matches its actual source', number is not None and abs(float(number.group().replace(',', '')) - row['value']) <= .0051, {'displayed': shown, 'source': row['value']})
                                if row.get('change') is not None:
                                    text = detail.locator('[data-worldflow-change]').inner_text()
                                    number = re.search(r'[+-]?[\d,]+(?:\.\d+)?', text)
                                    check(f'{width}: {key} change value and unit match independently computed source', number is not None and abs(float(number.group().replace(',', '')) - row['change']) <= .0051 and ('bp' in text if key == 'us10y' else '%' in text), text)
                                if row.get('precision') == 'source_date':
                                    check(f'{width}: {key} date-only source has no invented observation clock', row['session'] + ' 자료 · 발표 시각 미제공' in detail.inner_text())
                                source_link = detail.locator('.fx-worldflow-source a')
                                check(f'{width}: {key} source opens its saved HTTPS URL', source_link.get_attribute('href') == next(item['source']['url'] for item in feed['indicators'] if item['id'] == key))
                                check(f'{width}: {key} source link is rendered visibly', source_link.is_visible())
                                source_link.scroll_into_view_if_needed()
                                # Trial click checks real pointer actionability without opening the provider.
                                source_link.click(trial=True, timeout=5000)
                                source_link.focus()
                                check(f'{width}: {key} source link accepts focus and keyboard navigation', source_link.evaluate('(link) => document.activeElement === link && link.tabIndex >= 0'))
                        check(f'{width}: dialog fits the viewport and its own body scrolls', page.evaluate("""() => {
                            const d=document.querySelector('.fx-worldflow-dialog'),b=d.getBoundingClientRect(),body=d.querySelector('.fx-worldflow-dialog-body');
                            return b.x>=0&&b.right<=innerWidth+1&&b.y>=0&&b.bottom<=innerHeight+1&&body.clientHeight>0&&body.scrollWidth<=body.clientWidth+1;
                        }"""))
                        dialog.locator('[data-worldflow-close]').focus()
                        dialog.locator('.fx-worldflow-dialog-body').evaluate('(body) => { body.scrollTop = 0; }')
                        shot = out / f'world-flow-{width}-sources.png'
                        page.screenshot(path=str(shot), full_page=True)
                        report['screenshots'].append(str(shot))
                        page.keyboard.press('Escape')
                        check(f'{width}: Escape closes source details', page.locator('.fx-worldflow-dialog[open]').count() == 0)
                        check(f'{width}: no runtime errors', not errors, errors)
                    except Exception:
                        shot = out / f'world-flow-{width}-failure.png'
                        page.screenshot(path=str(shot), full_page=True)
                        report['screenshots'].append(str(shot))
                        raise
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WORLD_FLOW_BROWSER_ACCEPTANCE', len(report['checks']), 'checks')


if __name__ == '__main__':
    main()
