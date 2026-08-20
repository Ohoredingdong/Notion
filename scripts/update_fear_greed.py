#!/usr/bin/env python3
import json, math, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
OUT = Path(__file__).resolve().parents[1] / 'fear-greed-data.json'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.cnn.com',
    'Referer': 'https://www.cnn.com/',
}
COMPONENTS = {
    'vix': 'market_volatility_vix',
    'momentum': 'market_momentum_sp500',
    'strength': 'stock_price_strength',
    'put_call': 'put_call_options',
    'junk': 'junk_bond_demand',
}

def safe_num(v):
    try:
        n = float(v)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None

def latest_raw(block):
    rows = (block or {}).get('data') or []
    for row in reversed(rows):
        n = safe_num(row.get('y'))
        if n is not None:
            return n
    return None

def main():
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as res:
        raw = json.load(res)

    fg = raw.get('fear_and_greed') or {}
    hist_block = raw.get('fear_and_greed_historical') or {}
    history = []
    all_rows = hist_block.get('data') or []
    for row in all_rows:
        x, y = row.get('x'), safe_num(row.get('y'))
        if x is None or y is None:
            continue
        history.append({'timestamp': int(x), 'value': y, 'rating': row.get('rating')})
    history = history[-30:]

    values = []
    for row in all_rows:
        n = safe_num(row.get('y'))
        if n is not None:
            values.append(n)
    avg = sum(values) / len(values) if values else None

    components = {}
    for out_key, src_key in COMPONENTS.items():
        block = raw.get(src_key) or {}
        components[out_key] = {
            'score': safe_num(block.get('score')),
            'rating': block.get('rating'),
            'raw_value': latest_raw(block),
        }

    out = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'source_timestamp': fg.get('timestamp'),
        'headline': {
            'score': safe_num(fg.get('score')),
            'rating': fg.get('rating'),
            'timestamp': fg.get('timestamp'),
            'previous_close': safe_num(fg.get('previous_close')),
            'previous_1_week': safe_num(fg.get('previous_1_week')),
            'previous_1_month': safe_num(fg.get('previous_1_month')),
            'previous_1_year': safe_num(fg.get('previous_1_year')),
        },
        'one_year_average': avg,
        'history': history,
        'components': components,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'updated {OUT} | score={out["headline"]["score"]}')

if __name__ == '__main__':
    main()
