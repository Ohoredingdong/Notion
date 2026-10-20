"""Build the compact radar from the repository's dated market snapshots."""
import json
from datetime import datetime, timezone
from pathlib import Path

from market_data_utils import yahoo_chart, chart_points, finite

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'market-radar-data.json'


def read(name):
    return json.loads((ROOT / name).read_text())


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def build():
    old = read(OUT.name) if OUT.exists() else {}
    previous = {q['key']: q for q in old.get('quotes', [])}
    quotes, errors = [], []

    def add(key, fn):
        try:
            quote = fn()
            if finite(quote.get('price')) is None or not quote.get('source_time'):
                raise ValueError('Missing value or source time')
            quotes.append({'key': key, 'ok': True, 'decimals': 2, **quote})
        except Exception as exc:
            quotes.append({**previous.get(key, {'key': key, 'ok': False}), 'stale': True, 'error': str(exc)[:160]})
            errors.append(f'{key}: {exc}')

    def stock(market):
        data = read('stocks-dashboard-data.json')
        row = data['datasets'][market]['main']
        return {'price': row['raw_price'], 'diff': row['raw_price'] - row['previous_close'],
                'pct': row['change_pct'], 'source_time': row['market_time'], 'source': data['source'],
                'stale': data.get('stale', False), 'source_note': '거래소 지연 시세·휴장 중 최근 종가'}

    def extra(symbol):
        result = yahoo_chart(symbol, '5d', '1d')
        points, meta = chart_points(result), result.get('meta') or {}
        price = finite(meta.get('regularMarketPrice'))
        ts = meta.get('regularMarketTime')
        if price is None or not ts or len(points) < 2:
            raise ValueError('Incomplete source quote')
        previous_price = points[-2][1]
        return {'price': price, 'diff': price - previous_price,
                'pct': (price / previous_price - 1) * 100, 'source_time': iso(ts),
                'source': 'Yahoo Finance chart API', 'source_note': '거래소 지연 시세·휴장 중 최근 종가', 'stale': False}

    def bond():
        data = read('bond-yields-data.json')
        country = data['countries']['US']
        row = country['yields']['10Y']
        history = country.get('history') or country.get('history_10y') or []
        source_time = iso(history[-1][0]) if history else None
        return {'price': row['yield'], 'diff': row['change_bp'], 'diff_unit': 'bp', 'suffix': '%',
                'decimals': 3, 'source_time': source_time, 'time_label': '수집', 'source': data['source'],
                'source_note': '지연 참고 수익률·변동은 bp', 'stale': data.get('stale', False)}

    def fx():
        data = read('exchange-rates-data.json')
        row = data['usdkrw']
        return {'price': row['price'], 'diff': row['change'], 'pct': row['change_pct'],
                'source_time': data['reference_date'], 'source': 'ECB daily reference rate',
                'source_note': 'ECB 일별 기준환율', 'stale': data.get('stale', False)}

    def commodity(ident):
        data = read('commodities-data.json')
        row = next(x for x in data['items'] if x['id'] == ident)
        pct = row['change_pct']
        return {'price': row['price'], 'diff': row['price'] - row['price'] / (1 + pct / 100),
                'pct': pct, 'source_time': iso(row['source_timestamp']), 'source': 'Yahoo Finance futures',
                'source_note': row['unit'] + ' · 선물 지연 시세', 'stale': row.get('stale', False)}

    def bitcoin():
        data = read('cryptocurrency-data.json')
        row = next(x for x in data['coins'] if x['symbol'] == 'BTC')
        return {'price': row['price_krw'], 'diff': row['change_krw'], 'pct': row['change_pct'],
                'decimals': 0, 'source_time': data['generated_at'], 'time_label': '수집', 'source': 'Upbit KRW spot',
                'source_note': '업비트 원화 현물', 'label': 'Bitcoin (KRW)', 'stale': data.get('stale', False)}

    for key, fn in [('KOSPI', lambda: stock('KOR')), ('KOSDAQ', lambda: extra('^KQ11')),
                    ('S&P500', lambda: stock('US')), ('Nasdaq', lambda: extra('^IXIC')),
                    ('US10Y', bond), ('USD/KRW', fx), ('DXY', lambda: extra('DX-Y.NYB')),
                    ('Gold', lambda: commodity('gold')), ('Bitcoin', bitcoin), ('WTI', lambda: commodity('wti'))]:
        add(key, fn)
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'quotes': quotes,
            'stale': bool(errors or any(q.get('stale') for q in quotes)), 'last_errors': errors,
            'note': '항목별 원본 관측시각이 다릅니다. 시세·금리·환율은 각각 지연 시세·참고값입니다.'}


if __name__ == '__main__':
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    for error in data['last_errors']:
        print(f'::warning::{error}')
