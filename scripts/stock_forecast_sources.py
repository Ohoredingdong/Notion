"""Yahoo source adapter, including a strict raw-chart parser for index OHLC.
This is the SAME unofficial provider, not an independent-source cross-check.
"""
from urllib.parse import quote
import pandas as pd


def parse_chart(payload):
    chart = payload.get('chart') or {}
    if chart.get('error'):
        raise ValueError('provider_chart_error')
    results = chart.get('result') or []
    if len(results) != 1:
        raise ValueError('provider_chart_result_count')
    result = results[0]
    times = result.get('timestamp') or []
    quotes = (result.get('indicators') or {}).get('quote') or []
    if not times or len(quotes) != 1:
        raise ValueError('provider_chart_ohlc_missing')
    values = quotes[0]
    if any(len(values.get(k) or []) != len(times) for k in ('open', 'high', 'low', 'close')):
        raise ValueError('provider_chart_array_length_mismatch')
    index = pd.to_datetime(times, unit='s', utc=True)
    if index.duplicated().any():
        raise ValueError('provider_chart_duplicate_timestamp')
    frame = pd.DataFrame({k.capitalize(): values[k] for k in ('open', 'high', 'low', 'close')}, index=index)
    frame = frame.dropna(subset=['Open', 'High', 'Low', 'Close']).sort_index()
    if frame.empty:
        raise ValueError('provider_chart_no_complete_ohlc')
    return frame


def history(symbol, mode):
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    if symbol == '^KS11':
        # Avoid the provider-library index/live-row merge bug. Never truncate
        # unequal arrays to force alignment; reject them in parse_chart instead.
        payload = ticker._data.get_raw_json(
            'https://query1.finance.yahoo.com/v8/finance/chart/'+quote(symbol, safe=''),
            params={'range': '5y' if mode == 'daily' else '60d',
                    'interval': '1d' if mode == 'daily' else '5m',
                    'includePrePost': 'false'}, timeout=18)
        return parse_chart(payload)
    return ticker.history(period='5y' if mode == 'daily' else '60d',
                          interval='1d' if mode == 'daily' else '5m',
                          auto_adjust=False, actions=True, prepost=False,
                          timeout=18, raise_errors=True)


def self_test():
    import copy
    p = {'chart': {'result': [{'timestamp': [1793232000, 1793232300],
         'indicators': {'quote': [{'open': [100, 101], 'high': [102, 103],
                                  'low': [99, 100], 'close': [101, 102]}]}}]}}
    frame = parse_chart(p)
    assert len(frame) == 2 and str(frame.index.tz) == 'UTC'
    for changed in ('duplicate', 'length', 'error'):
        q = copy.deepcopy(p)
        if changed == 'duplicate': q['chart']['result'][0]['timestamp'][1] = q['chart']['result'][0]['timestamp'][0]
        if changed == 'length': q['chart']['result'][0]['indicators']['quote'][0]['close'].pop()
        if changed == 'error': q['chart']['error'] = {'code': 'test'}
        try:
            parse_chart(q)
        except ValueError:
            pass
        else:
            raise AssertionError(changed+' must reject')
    print('Raw index parser: valid OHLC, UTC, duplicate, unequal array and error guards passed')

if __name__ == '__main__':
    self_test()
