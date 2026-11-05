"""Real-data acceptance for the shared home/AI universe and company selection.

Expected identities, counts, statements and signals come from saved source files,
independently of the browser helpers. No data or clock is fabricated. Notion
coverage is a local iframe, not a signed-in account.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlparse

OUT = Path('radar-universe-evidence')
BASE = 'http://127.0.0.1:8765/stock-value-radar.html'
REPORT = {'checks': [], 'screenshots': [], 'limitations': [
    'Notion: locally simulated iframe, not the live Notion account',
    'AI assertions use the actual clock and saved target periods; expired signals must disappear.']}
FIXTURES = ('KR:0001A0', 'US:KO', 'US:BRK.B', 'KR:000250')


def verify(name, success, details=None):
    REPORT['checks'].append({'name': name, 'pass': bool(success), 'details': details})
    if not success:
        raise AssertionError(f'{name}: {details}')


def identity(row):
    country = str(row.get('country') or row.get('market')).upper()
    symbol = str(row['symbol']).strip().upper()
    if country == 'KR':
        symbol = re.sub(r'\.(KS|KQ)$', '', symbol)
    return country + ':' + symbol


def timestamp(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError):
        return float('nan')


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def load_oracle(root):
    filenames = {'catalog': 'stock-universe-catalog.json', 'raw': 'stock-opportunity-data.json',
                 'financial': 'stock-financial-coverage.json', 'markets': 'stock-market-groups.json',
                 'direction': 'stock-direction-forecast.json', 'extended': 'stock-extended-direction-forecast.json',
                 'charts': 'stock-radar-chart-data.json'}
    source = {name: json.loads((root / file).read_text(encoding='utf-8')) for name, file in filenames.items()}
    source['hashes'] = {file: hashlib.sha256((root / file).read_bytes()).hexdigest() for file in filenames.values()}
    catalog = {identity(row): row for row in source['catalog']['items']}
    raw = {}
    for row in source['raw']['companies']:
        key = identity(row)
        # Provider share-class aliases describe the same issuer, not a new quote.
        if key not in catalog and key.startswith('US:') and key.replace('-', '.') in catalog:
            key = key.replace('-', '.')
        raw[key] = row
    union = {key: {'catalog': catalog.get(key), 'raw': raw.get(key),
                   'selection': raw[key]['symbol'] if key in raw else key}
             for key in catalog.keys() | raw.keys()}
    source.update(catalog_by_key=catalog, raw_by_key=raw, union=union,
                  by_selection={row['selection']: key for key, row in union.items()})
    return source


def statement(key, source):
    item = source['catalog_by_key'].get(key)
    feed = source['financial']
    row = feed.get('records', {}).get(key)
    if not item or not row or feed.get('identity_policy') != 'official-issuer-identity-v2':
        return None
    if feed.get('catalog_generated_at') != source['catalog'].get('generated_at'):
        return None
    if row.get('identity_verified') is not True or row.get('catalog_name') != item['name']:
        return None
    if row.get('country') != item['country'] or row.get('symbol') != item['symbol']:
        return None
    corporate_id = str(row.get('corp_code' if item['country'] == 'KR' else 'cik') or '')
    pattern = r'\d{8}' if item['country'] == 'KR' else r'\d{1,10}'
    return row if re.fullmatch(pattern, corporate_id) else None


def active_forecast(key, source, now):
    def eligible(row):
        probabilities, target = row.get('probabilities') or {}, row.get('target') or {}
        issued, start, end = [timestamp(value) for value in
                              (row.get('issued_at'), target.get('start'), target.get('end'))]
        values = [probabilities.get(name) for name in ('up', 'flat', 'down')]
        return (row.get('status') == 'research_prediction' and row.get('direction') in ('up', 'flat', 'down')
                and all(finite(value) and 0 <= value <= 1 for value in values)
                and abs(sum(values) - 1) < .025 and all(math.isfinite(value) for value in (issued, start, end))
                and issued <= now + 300 and issued <= start < end and end > now)
    for feed in ('direction', 'extended'):
        matching = [row for row in source[feed].get('records', []) if identity(row) == key and eligible(row)]
        if matching:
            return max(matching, key=lambda row: timestamp(row['issued_at']))
    return None


def market_ids(source, market):
    members, dow = source['markets'].get('members', {}), source['markets'].get('dow', {})
    result = set()
    for key, entry in source['union'].items():
        item, raw = entry['catalog'], entry['raw']
        row = raw or item
        venue = item.get('exchange') if item else None
        if not venue:
            for alias in (row.get('source_symbol'), row.get('symbol'), row['symbol'] + '.KS', row['symbol'] + '.KQ'):
                if alias in members:
                    venue = members[alias].get('venue')
                    break
        belongs = market == 'ALL' or venue == market
        if market == 'DOW':
            belongs = key.startswith('US:') and dow.get('status') == 'current' and row['symbol'] in dow.get('symbols', [])
        if belongs:
            result.add(entry['selection'])
    return result


def screenshot(page, name):
    path = OUT / (name + '.png')
    page.screenshot(path=str(path), full_page=True, animations='disabled')
    REPORT['screenshots'].append(str(path))


def capture_browser_failure(browser, error):
    """Preserve an actual blocked interaction; never bypass pointer hit testing."""
    REPORT['checks'].append({'name': 'browser interaction completed without exception',
                             'pass': False, 'details': str(error)})
    try:
        page = browser.contexts[-1].pages[-1]
        REPORT['failure_geometry'] = page.evaluate('''() => {
          const selectors=['.fx-stage','.fx-stock-directory-page','.fx-page-grid',
            '.fx-list-panel','#fx-results','#fx-result-count','[data-fx-more]',
            '.fx-flowbar','.fx-catalog-preview'];
          return {viewport:{width:innerWidth,height:innerHeight},scroll:{x:scrollX,y:scrollY},
            nodes:Object.fromEntries(selectors.map(selector=>{
              const el=document.querySelector(selector);if(!el)return [selector,null];
              const r=el.getBoundingClientRect(),style=getComputedStyle(el);
              const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
              return [selector,{x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,
                scrollHeight:el.scrollHeight,clientHeight:el.clientHeight,
                overflowY:style.overflowY,position:style.position,
                centerHit:hit?{tag:hit.tagName,className:hit.className,id:hit.id}:null}];
            }))};
        }''')
        screenshot(page, 'failure-last-screen')
    except Exception as diagnostic_error:
        REPORT['failure_capture_error'] = str(diagnostic_error)


def context(browser, width, height, root):
    ctx = browser.new_context(viewport={'width': width, 'height': height}, color_scheme='light',
                              reduced_motion='reduce', service_workers='block')
    # Replay exact saved bytes, also when a separate source directory is supplied.
    # No issue times, target dates, forecast probabilities or prices are rewritten.
    def source_route(route):
        name = Path(urlparse(route.request.url).path).name
        path = root / name
        if name.endswith(('.json', '.jsonl')) and path.is_file():
            route.fulfill(path=str(path), content_type='application/json')
        else:
            route.continue_()
    ctx.route('**/*', source_route)
    return ctx


def ready(page):
    page.wait_for_function('''() => {
      const s=window.StockRadarV2Bridge?.snapshot?.(),d=s?.data;
      return !s?.busy && d?.catalog?.items?.length && d?.raw?.companies?.length
        && d?.financial?.records && d?.markets?.members && d?.extended?.records
        && d?.direction?.records && d?.newsLink?.items?.length;
    }''', timeout=60000)


def screen(page, target):
    page.locator(f'.fx-nav [data-nr-screen="{target}"]').click()
    page.locator(f'.fx-stage[data-screen="{target}"]').wait_for()


def reset_list(page):
    page.locator('[data-rf-market="ALL"]').first.click()
    page.locator('[data-fx-filter="all"]').click()
    page.locator('#fx-search-input').fill('')


def visible_ids(page):
    return page.locator('#fx-results .fx-row[data-nr-select]').evaluate_all('rows => rows.map(row => row.dataset.nrSelect)')


def list_count(page):
    text = page.locator('#fx-result-count').inner_text()
    match = re.search(r'([\d,]+)\s*/\s*([\d,]+)개', text)
    verify('result count is explicit and parseable', bool(match), text)
    return tuple(int(number.replace(',', '')) for number in match.groups())


def select_search(page, key, source, label, query=None):
    reset_list(page)
    item = source['catalog_by_key'].get(key) or source['raw_by_key'][key]
    selection = source['union'][key]['selection']
    search = query or item['symbol']
    page.locator('#fx-search-input').fill(search)
    row = page.locator(f'#fx-results .fx-row[data-nr-select="{selection}"]')
    verify(f'{label}: shared search finds exact {key}', row.count() == 1,
           {'query': search, 'visible': visible_ids(page)})
    row.click()
    page.wait_for_function('id => window.StockRadarV2Bridge.snapshot().selected === id', arg=selection)


def catalog_profile(page, key, source, label):
    item = source['catalog_by_key'][key]
    selected = page.evaluate('window.StockRadarV2Bridge.snapshot().selected')
    profile = page.locator('.fx-catalog-preview')
    verify(f'{label}: selection and visible issuer stay aligned', selected == key and profile.count() == 1,
           {'selected': selected, 'expected': key})
    verify(f'{label}: exact issuer name and code', profile.locator('.fx-panel-heading h3').inner_text() == item['name']
           and item['symbol'] in profile.locator('.fx-panel-heading small').inner_text())
    verify(f'{label}: selected profile has no horizontal overflow',
           page.evaluate('document.documentElement.scrollWidth <= innerWidth + 4'))
    quote = profile.locator('.fx-catalog-quote').inner_text()
    verify(f'{label}: missing quote stays explicitly unpriced', '저장 종가 미확인' in quote and '차트 미수집' in quote
           and not re.search(r'\d', quote) and profile.locator('.fx-d-quote,.fx-price-large,.fx-chart-svg').count() == 0, quote)
    verify(f'{label}: catalog does not manufacture detailed raw records',
           page.evaluate('window.StockRadarV2Bridge.snapshot().data.raw.companies.length') == len(source['raw']['companies']))
    headline = profile.locator('.fx-catalog-preview-core strong').inner_text()
    forecast = active_forecast(key, source, page.evaluate('Date.now() / 1000'))
    if forecast:
        expected = forecast['probabilities'][forecast['direction']] * 100
        shown = re.search(r'([\d,.]+)%', headline)
        direction = {'up': '상승', 'flat': '횡보', 'down': '하락'}[forecast['direction']]
        verify(f'{label}: actual active forecast uses its own probability', shown is not None and direction in headline
               and abs(float(shown.group(1).replace(',', '')) - expected) < .001,
               {'headline': headline, 'forecast_id': forecast.get('id'), 'expected_percent': expected})
        detail = profile.locator('.fx-catalog-preview-core').inner_text()
        verify(f'{label}: actual issuance and target period disclosed', forecast['issued_at'] in detail
               and forecast['target']['end'] in detail and '연구용' in detail)
    else:
        verify(f'{label}: no fabricated AI probability', '%' not in headline and
               any(word in headline for word in ('미발행', '미확인', '기간 종료')), headline)
    row = statement(key, source)
    if row and row.get('status') in ('available', 'partial', 'stale'):
        finance = profile.locator('.fx-catalog-finance')
        text = finance.inner_text()
        cells = finance.locator('.fx-catalog-finance-cell').evaluate_all(
            "rows => Object.fromEntries(rows.map(r=>[r.querySelector('small').textContent,r.querySelector('strong').textContent]))")
        verify(f'{label}: actual issuer statement and original source',
               (row.get('period_end') or row.get('period_end_label') or '') in text and '법인 연결 확인' in text and '확인 시각' in text
               and finance.locator('a[href="' + row['source_url'] + '"]').count() == 1,
               {'period': row.get('period_end'), 'source_url': row['source_url']})
        metrics = row.get('metrics') or {}
        for title, field in (('FCF', 'free_cash_flow'), ('공시 EPS', 'reported_eps')):
            if not finite(metrics.get(field)):
                verify(f'{label}: missing {field} remains unknown', cells.get(title) == '미수집·미확인', cells.get(title))
        if finite(metrics.get('revenue')):
            shown = cells['매출액']
            number = re.search(r'[−-]?[\d,]+(?:\.\d+)?', shown)
            scale = 1e12 if '조 원' in shown else 1e8 if '억 원' in shown else 1e9 if 'B ' in shown else 1e6 if 'M ' in shown else 1
            actual = float(number.group().replace(',', '').replace('−', '-')) * scale if number else None
            verify(f'{label}: actual revenue value and reported currency match source',
                   actual is not None and abs(actual - metrics['revenue']) <= scale * .00051
                   and ('원' in shown if row['currency'] == 'KRW' else row['currency'] in shown),
                   {'displayed': shown, 'expected': metrics['revenue'], 'currency': row['currency']})
    else:
        text = profile.inner_text()
        verify(f'{label}: unavailable or no-report finance has no invented numbers',
               profile.locator('.fx-catalog-finance-cell').count() == 0 and '공식 재무제표: 아직 미확인' in text
               and '공시 없음' not in text, row and row.get('status'))


def run_view(browser, width, height, root, source):
    ctx = context(browser, width, height, root)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE, wait_until='domcontentloaded')
    ready(page)
    verify(f'{width}: real source snapshot loaded',
           page.evaluate('window.StockRadarV2Bridge.snapshot().data.catalog.generated_at') == source['catalog']['generated_at'])
    verify(f'{width}: existing market dashboard intact', page.locator('.fx-v5-markets .nr-index').count() == 4
           and page.locator('.fx-sent-v9').count() == 1)
    verify(f'{width}: home denominator is entire union', list_count(page) == (9, len(source['union'])))
    screenshot(page, f'{width}-home')
    screen(page, 'stocks')
    reset_list(page)
    verify(f'{width}: one shared search without separate catalog panel',
           page.locator('#fx-search-input').count() == 1 and page.locator('#fx-catalog-search').count() == 0)
    verify(f'{width}: default AI list exposes entire union', list_count(page) == (36, len(source['union'])))
    before = visible_ids(page)
    page.locator('[data-fx-more]').click()
    after = visible_ids(page)
    verify(f'{width}: next page appends 36 unique companies', len(before) == 36 and len(after) == 72
           and after[:36] == before and len(set(after)) == 72 and set(after) <= source['by_selection'].keys(), after[-4:])
    page.locator('[data-fx-more]').click()
    verify(f'{width}: pagination crosses the old 104-company boundary', len(visible_ids(page)) == 108)
    screenshot(page, f'{width}-full-universe')
    for market in ('KOSPI', 'KOSDAQ', 'NASDAQ', 'DOW', 'ALL'):
        page.locator(f'[data-rf-market="{market}"]').first.click()
        expected = market_ids(source, market)
        shown, total = list_count(page)
        ids = visible_ids(page)
        verify(f'{width}: {market} filter follows independent source membership',
               total == len(expected) and shown == len(ids) and set(ids) <= expected,
               {'expected': len(expected), 'displayed': total, 'first_ids': ids[:4]})
    now = page.evaluate('Date.now() / 1000')
    forecast_keys = {identity(row) for feed in ('direction', 'extended') for row in source[feed].get('records', [])}
    active = {key: active_forecast(key, source, now) for key in forecast_keys if key in source['union']}
    for filter_name in ('ai', 'up', 'down'):
        expected = {source['union'][key]['selection'] for key, row in active.items()
                    if row and (filter_name == 'ai' or row['direction'] == filter_name)}
        page.locator(f'[data-fx-filter="{filter_name}"]').click()
        shown, total = list_count(page)
        ids = visible_ids(page)
        verify(f'{width}: {filter_name} shows only actual period-valid research signals',
               total == len(expected) and shown == len(ids) and set(ids) <= expected,
               {'expected_ids': sorted(expected), 'visible_ids': ids, 'denominator': total})
    reset_list(page)
    # All fixtures are checked against catalog-minus-raw before browser startup.
    # Fabrinet is already a raw company; it cannot prove access beyond raw104.
    for key in FIXTURES:
        for target in ('home', 'stocks'):
            screen(page, target)
            select_search(page, key, source, f'{width}/{target}/{key}')
            catalog_profile(page, key, source, f'{width}/{target}/{key}')
        for target in ('home', 'stockdetail', 'scenario'):
            screen(page, target)
            catalog_profile(page, key, source, f'{width}/{target}-retained/{key}')
        page.reload(wait_until='domcontentloaded')
        ready(page)
        catalog_profile(page, key, source, f'{width}/reload/{key}')
        page.locator('[data-catalog-back]').click()
        verify(f'{width}/{key}: back preserves issuer and returns to stock list',
               page.locator('.fx-stage[data-screen="stocks"]').count() == 1
               and page.evaluate('window.StockRadarV2Bridge.snapshot().selected') == key)
        if key in ('KR:0001A0', 'KR:000250'):
            screenshot(page, f"{width}-{key.replace(':', '-')}-profile")
    select_search(page, 'KR:0001A0', source, f'{width}/issuer-name', query=source['catalog_by_key']['KR:0001A0']['name'])
    page.locator('.fx-catalog-preview [data-nr-star="KR:0001A0"]').click()
    verify(f'{width}: catalog favorite exposes its selected state',
           page.locator('.fx-catalog-preview [data-nr-star="KR:0001A0"]').get_attribute('aria-pressed') == 'true')
    reset_list(page)
    page.locator('[data-fx-filter="star"]').click()
    verify(f'{width}: favorite filter includes catalog-only issuer', visible_ids(page) == ['KR:0001A0'] and list_count(page) == (1, 1))
    page.reload(wait_until='domcontentloaded')
    ready(page)
    screen(page, 'stocks')
    reset_list(page)
    page.locator('[data-fx-filter="star"]').click()
    verify(f'{width}: catalog favorite persists after reload', visible_ids(page) == ['KR:0001A0'])
    page.locator('.fx-catalog-preview [data-nr-star="KR:0001A0"]').click()
    verify(f'{width}: last favorite removal has honest empty state', visible_ids(page) == [] and list_count(page) == (0, 0))
    reset_list(page)
    missing = [key for key, row in source['financial'].get('records', {}).items()
               if row.get('status') == 'no_report' and key in source['catalog_by_key'] and key not in source['raw_by_key']]
    if missing:
        select_search(page, missing[0], source, f'{width}/actual-no-report')
        catalog_profile(page, missing[0], source, f'{width}/actual-no-report')
    else:
        REPORT['limitations'].append(f'{width}: current source has no catalog-only no_report fixture; missing US finance remains tested.')
    screen(page, 'home')
    select_search(page, 'US:NVDA', source, f'{width}/raw-NVDA')
    nvda = source['raw_by_key']['US:NVDA']
    quote = page.locator('.fx-v5-quote strong').inner_text()
    amount = re.search(r'[\d,]+(?:\.\d+)?', quote)
    verify(f'{width}: original NVDA source price and real chart preserved', amount is not None
           and abs(float(amount.group().replace(',', '')) - nvda['price']) <= .0051 and nvda['currency'] in quote
           and page.locator('.fx-v5-chartarea .fx-chart-svg polyline').count() >= 2
           and page.locator('.fx-catalog-preview').count() == 0, {'displayed': quote, 'source_price': nvda['price']})
    screenshot(page, f'{width}-NVDA-preserved')
    page.locator('.fx-nav-tools [data-nr-screen="news"]').click()
    verify(f'{width}: real news and macro links remain available', page.locator('.fx-world-panel').count() == 3
           and page.locator('.fx-world-metric').count() == 6 and page.locator('.fx-world-metric a').count() >= 3
           and page.locator('.fx-world-article a').count() >= 3
           and '자동 매수 신호가 아닙니다' in page.locator('.fx-world-page').inner_text())
    screenshot(page, f'{width}-world-brief')
    verify(f'{width}: no JavaScript exceptions', not errors, errors)
    verify(f'{width}: no horizontal overflow', page.evaluate('document.documentElement.scrollWidth') <= width + 4)
    ctx.close()


def main():
    global OUT, BASE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=BASE)
    parser.add_argument('--data-root', type=Path, default=Path(os.environ.get('RADAR_DATA_DIR', '.')))
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--oracle-only', action='store_true', help='Source assumptions only; does not claim a browser pass')
    args = parser.parse_args()
    OUT, BASE = args.out, args.base
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        source = load_oracle(args.data_root)
        verify('source universe has no duplicate canonical identities',
               len(source['catalog_by_key']) == len(source['catalog']['items'])
               and len(source['raw_by_key']) == len(source['raw']['companies']))
        verify('current source identifier policy', source['catalog'].get('identifier_policy') == 'kr-six-character-alphanumeric-v2')
        verify('real directory contains both markets', all(source['catalog']['counts'][country] > 1000 for country in ('KR', 'US')))
        for key in FIXTURES:
            verify(f'real fixture {key} lies outside raw detailed universe', key in source['catalog_by_key'] and key not in source['raw_by_key'])
        verified = sum(1 for key in source['catalog_by_key'] if (row := statement(key, source))
                       and row.get('status') in ('available', 'partial', 'stale'))
        verify('official statement count uses verified issuer identities', verified > 0
               and verified == sum(source['financial']['financial_available'].values()), verified)
        verify('NVDA is genuinely priced positive control', finite(source['raw_by_key']['US:NVDA'].get('price')))
        now = datetime.now(timezone.utc)
        REPORT['source'] = {'sha256': source['hashes'], 'catalog': len(source['catalog_by_key']),
                            'raw': len(source['raw_by_key']), 'union': len(source['union']), 'verified_financial': verified,
                            'market_counts': {market: len(market_ids(source, market)) for market in ('ALL', 'KOSPI', 'KOSDAQ', 'NASDAQ', 'DOW')},
                            'forecast_clock': now.isoformat(),
                            'active_catalog_fixtures': [key for key in FIXTURES if active_forecast(key, source, now.timestamp())]}
        if args.oracle_only:
            REPORT['browser_executed'] = False
            print('SOURCE_ORACLE_ONLY', json.dumps(REPORT['source'], ensure_ascii=False))
            return
        from playwright.sync_api import sync_playwright
        REPORT['browser_executed'] = True
        with sync_playwright() as play:
            browser = play.chromium.launch(headless=True)
            try:
                for width, height in ((1440, 900), (1366, 768), (390, 844)):
                    run_view(browser, width, height, args.data_root, source)
                for width, height in ((920, 680), (360, 640)):
                    ctx = context(browser, width + 40, height + 60, args.data_root)
                    page = ctx.new_page()
                    page.set_content(f'<iframe name="notion-test" title="Notion-sized embed" src="{BASE}" style="width:{width}px;height:{height}px;border:0"></iframe>')
                    frame = page.frame(name='notion-test')
                    ready(frame)
                    verify(f'embed-{width}: existing index cards intact', frame.locator('.fx-v5-markets .nr-index').count() == 4)
                    select_search(frame, 'KR:0001A0', source, f'embed-{width}/home')
                    catalog_profile(frame, 'KR:0001A0', source, f'embed-{width}/home')
                    screenshot(page, f'embed-{width}-catalog-home')
                    frame.locator('.fx-nav-tools [data-nr-screen="news"]').click()
                    verify(f'embed-{width}: news accessible', frame.locator('.fx-world-page').count() == 1)
                    screenshot(page, f'embed-{width}-news')
                    ctx.close()
            except Exception as error:
                capture_browser_failure(browser, error)
                raise
            finally:
                browser.close()
    finally:
        (OUT / 'report.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print('REAL_UNIVERSE_UI_ACCEPTANCE', len(REPORT['checks']), 'checks',
          sum(1 for item in REPORT['checks'] if not item['pass']), 'failed')


if __name__ == '__main__':
    main()
