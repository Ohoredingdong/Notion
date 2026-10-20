"""Upbit KRW / Coinbase USD premium using the dated ECB reference FX rate."""
import json
from datetime import datetime, timezone
from pathlib import Path

from market_data_utils import get_json, finite

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'bitcoin-korea-premium-data.json'


def now():
    return datetime.now(timezone.utc).isoformat()


def collect():
    fx_data = json.loads((ROOT / 'exchange-rates-data.json').read_text())
    fx = finite((fx_data.get('usdkrw') or {}).get('price'))
    fx_date = fx_data.get('reference_date')
    if not fx or not fx_date:
        raise ValueError('Dated USD/KRW reference rate unavailable')
    if (datetime.now(timezone.utc).date() - datetime.fromisoformat(fx_date).date()).days > 7:
        raise ValueError('USD/KRW reference rate is more than 7 days old')
    local = {row['market']: row for row in get_json('https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH')}
    rows = []
    source_times = []
    for symbol in ('BTC', 'ETH'):
        krw = local.get('KRW-' + symbol) or {}
        global_quote = get_json(f'https://api.exchange.coinbase.com/products/{symbol}-USD/ticker')
        local_price, global_price = finite(krw.get('trade_price')), finite(global_quote.get('price'))
        if not local_price or not global_price or not krw.get('timestamp') or not global_quote.get('time'):
            raise ValueError(f'{symbol}: missing price or source timestamp')
        local_time = datetime.fromtimestamp(krw['timestamp'] / 1000, timezone.utc).isoformat()
        global_time = global_quote['time']
        source_times.extend([local_time, global_time])
        rows.append({'symbol': symbol, 'local_krw': local_price, 'global_usd': global_price,
                     'premium_pct': round((local_price / (global_price * fx) - 1) * 100, 4),
                     'local_source_time': local_time, 'global_source_time': global_time})
    times = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in source_times]
    if (datetime.now(timezone.utc) - min(times)).total_seconds() > 3600:
        raise ValueError('One of the exchange quotes is more than one hour old')
    premium = rows[0]['premium_pct']
    return {'generated_at': now(), 'checked_at': now(), 'updated_at': min(times).isoformat(),
            'source': 'Upbit KRW spot / Coinbase Exchange USD spot / ECB daily reference FX',
            'source_url': 'https://docs.upbit.com/kr/reference/ticker',
            'sources': {'local': 'https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH',
                        'global': 'https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-ticker',
                        'fx': fx_data.get('source_url')},
            'update_interval_sec': 1800, 'usdkrw': fx, 'fx_reference_date': fx_date,
            'premium_pct': premium, 'premium_label': 'BTC 참고 프리미엄',
            'summary': '업비트가 환산 가격보다 ' + ('높습니다' if premium >= 0 else '낮습니다') + '. ECB 일별 기준환율로 계산합니다.',
            'rows': rows, 'stale': bool(fx_data.get('stale')), 'status': 'reference',
            'accuracy_note': '거래소별 시세 시각이 다르고 환율은 ECB 일별 기준값입니다. 실시간 차익거래 수익률이 아닙니다.'}


def main():
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    try:
        data = collect()
    except Exception as exc:
        data = {**old, 'checked_at': now(), 'stale': True, 'status': 'stale', 'error': str(exc)[:250]}
        print(f'::warning::Bitcoin premium kept its last valid snapshot: {exc}')
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
