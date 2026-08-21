from __future__ import annotations

import json
import math
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from curl_cffi import requests

OUT = Path('stocks-dashboard-data.json')
KST = ZoneInfo('Asia/Seoul')
BASES = ['https://query2.finance.yahoo.com/v8/finance/chart/', 'https://query1.finance.yahoo.com/v8/finance/chart/']

MARKETS = {
    'US': {
        'main': ('^GSPC', 'S&P 500'),
        'rows': [
            ('AAPL', 'Apple Inc.'), ('TSLA', 'Tesla Inc.'), ('NVDA', 'NVIDIA Corp.'),
            ('MSFT', 'Microsoft Corp.'), ('AMZN', 'Amazon.com Inc.'),
        ],
    },
    'KOR': {
        'main': ('^KS11', 'KOSPI'),
        'rows': [
            ('005930.KS', 'Samsung Electronics'), ('000660.KS', 'SK hynix'),
            ('035420.KS', 'NAVER'), ('207940.KS', 'Samsung Biologics'),
            ('005380.KS', 'Hyundai Motor'),
        ],
    },
    'EU': {
        'main': ('^STOXX', 'STOXX Europe 600'),
        'rows': [
            ('SHEL.L', 'Shell plc'), ('ASML.AS', 'ASML Holding'), ('MC.PA', 'LVMH'),
            ('SAP.DE', 'SAP SE'), ('NESN.SW', 'Nestlé'),
        ],
    },
    'ASIA': {
        'main': ('^N225', 'Nikkei 225'),
        'rows': [
            ('7203.T', 'Toyota Motor'), ('9988.HK', 'Alibaba'), ('005930.KS', 'Samsung Electronics'),
            ('6758.T', 'Sony Group'), ('9618.HK', 'JD.com'),
        ],
    },
}

RANGES = ['1D', '1W', '1M', '3M', 'YTD', '1Y']
_cache: dict[tuple[str, str, str], dict] = {}


def fetch_chart(symbol: str, rng: str, interval: str) -> dict:
    key = (symbol, rng, interval)
    if key in _cache:
        return _cache[key]
    last_exc = None
    for base in BASES:
        url = base + urllib.parse.quote(symbol, safe='')
        for attempt in range(3):
            try:
                r = requests.get(
                    url,
                    params={'range': rng, 'interval': interval, 'includePrePost': 'false'},
                    timeout=25,
                    impersonate='chrome',
                    headers={'Accept-Language': 'en-US,en;q=0.9'},
                )
                if r.status_code == 429:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                r.raise_for_status()
                payload = r.json()
                break
            except Exception as exc:
                last_exc = exc
                time.sleep(0.8 * (attempt + 1))
        else:
            continue
        break
    else:
        raise RuntimeError(f'{symbol}: Yahoo request failed: {last_exc}')
    err = payload.get('chart', {}).get('error')
    if err:
        raise RuntimeError(f'{symbol}: {err}')
    result = (payload.get('chart', {}).get('result') or [None])[0]
    if not result:
        raise RuntimeError(f'{symbol}: no chart result')
    _cache[key] = result
    time.sleep(0.08)
    return result


def valid_closes(result: dict) -> list[tuple[int, float]]:
    ts = result.get('timestamp') or []
    quote = ((result.get('indicators') or {}).get('quote') or [{}])[0]
    closes = quote.get('close') or []
    out = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        try:
            c = float(c)
        except Exception:
            continue
        if math.isfinite(c):
            out.append((int(t), c))
    return out


def sample(vals: list[float], n: int = 18) -> list[float]:
    if len(vals) <= n:
        return [round(v, 4) for v in vals]
    idx = [round(i * (len(vals) - 1) / (n - 1)) for i in range(n)]
    return [round(vals[i], 4) for i in idx]


def price_format(price: float, currency: str | None) -> str:
    currency = (currency or '').upper()
    if currency == 'USD':
        return f'${price:,.2f}'
    if currency == 'KRW':
        return f'₩{price:,.0f}'
    if currency == 'EUR':
        return f'€{price:,.2f}'
    if currency == 'JPY':
        return f'¥{price:,.0f}'
    if currency == 'HKD':
        return f'HK${price:,.2f}'
    if currency == 'CHF':
        return f'CHF {price:,.2f}'
    return f'{price:,.2f}'


def current_snapshot(symbol: str) -> dict:
    result = fetch_chart(symbol, '1d', '5m')
    meta = result.get('meta') or {}
    points = valid_closes(result)
    if not points:
        result = fetch_chart(symbol, '5d', '1h')
        meta = result.get('meta') or {}
        points = valid_closes(result)
    if not points:
        raise RuntimeError(f'{symbol}: no price points')

    price = meta.get('regularMarketPrice')
    if price is None:
        price = points[-1][1]
    price = float(price)

    prev = meta.get('chartPreviousClose')
    if prev is None:
        prev = meta.get('previousClose')
    if prev is None:
        daily = valid_closes(fetch_chart(symbol, '5d', '1d'))
        prev = daily[-2][1] if len(daily) >= 2 else price
    prev = float(prev)

    change = price - prev
    pct = (change / prev * 100.0) if prev else 0.0
    regular_time = meta.get('regularMarketTime') or points[-1][0]
    return {
        'price': price,
        'previous': prev,
        'change': change,
        'pct': pct,
        'currency': meta.get('currency'),
        'exchange': meta.get('exchangeName') or meta.get('fullExchangeName'),
        'market_time': int(regular_time),
        'intraday': sample([p[1] for p in points]),
    }


def main_series(symbol: str) -> dict[str, list[float]]:
    intraday = current_snapshot(symbol)['intraday']
    daily_result = fetch_chart(symbol, '1y', '1d')
    daily = valid_closes(daily_result)
    if not daily:
        raise RuntimeError(f'{symbol}: no daily history')

    vals = [v for _, v in daily]
    now = datetime.now(timezone.utc)
    year_start = int(datetime(now.year, 1, 1, tzinfo=timezone.utc).timestamp())
    ytd_vals = [v for t, v in daily if t >= year_start] or vals
    return {
        '1D': intraday,
        '1W': sample(vals[-5:]),
        '1M': sample(vals[-22:]),
        '3M': sample(vals[-66:]),
        'YTD': sample(ytd_vals),
        '1Y': sample(vals),
    }


def read_old() -> dict:
    try:
        return json.loads(OUT.read_text(encoding='utf-8'))
    except Exception:
        return {}


def build_market(key: str, cfg: dict) -> tuple[dict, int]:
    main_symbol, main_name = cfg['main']
    snap = current_snapshot(main_symbol)
    series = main_series(main_symbol)
    latest_ts = snap['market_time']
    main = {
        'symbol': main_symbol,
        'name': main_name,
        'display': f'{snap["price"]:,.2f}',
        'raw_price': round(snap['price'], 6),
        'change_pct': round(snap['pct'], 4),
        'change_abs': f'{abs(snap["change"]):,.2f}',
        'previous_close': round(snap['previous'], 6),
        'currency': snap['currency'],
        'market_time': datetime.fromtimestamp(snap['market_time'], timezone.utc).isoformat(),
        'series': series,
    }
    rows = []
    for symbol, fallback_name in cfg['rows']:
        rs = current_snapshot(symbol)
        latest_ts = max(latest_ts, rs['market_time'])
        rows.append({
            'symbol': symbol.replace('.KS', '').replace('.T', '').replace('.HK', '').replace('.L', '').replace('.AS', '').replace('.PA', '').replace('.DE', '').replace('.SW', ''),
            'source_symbol': symbol,
            'company': fallback_name,
            'price': price_format(rs['price'], rs['currency']),
            'raw_price': round(rs['price'], 6),
            'change': round(rs['change'], 4),
            'pct': round(rs['pct'], 4),
            'currency': rs['currency'],
            'market_time': datetime.fromtimestamp(rs['market_time'], timezone.utc).isoformat(),
        })
    return {'main': main, 'rows': rows}, latest_ts


def main() -> None:
    old = read_old()
    datasets = dict(old.get('datasets') or {})
    errors = []
    latest = 0

    for key, cfg in MARKETS.items():
        try:
            datasets[key], market_ts = build_market(key, cfg)
            latest = max(latest, market_ts)
        except Exception as exc:
            errors.append(f'{key}: {exc}')
            if key not in datasets:
                raise

    now = datetime.now(KST)
    out = {
        'generated_at': now.isoformat(),
        'updated_at': datetime.fromtimestamp(latest, timezone.utc).isoformat() if latest else now.isoformat(),
        'source': 'Yahoo Finance chart API',
        'source_label': 'Yahoo Finance · delayed/indicative',
        'accuracy_note': 'Quotes may be delayed by exchange. Informational use only.',
        'stale': bool(errors),
        'last_errors': errors,
        'activeMarket': 'US',
        'activeRange': '1D',
        'markets': list(MARKETS),
        'ranges': RANGES,
        'datasets': datasets,
        'ticker_validation': {
            'US': '^GSPC', 'KOR': '^KS11', 'EU': '^STOXX', 'ASIA': '^N225'
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
