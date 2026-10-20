"""Read public market snapshots with bounded retries and source timestamps."""
import json
import math
import time
import urllib.parse
import urllib.request


def finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def get_json(url, timeout=25):
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def yahoo_chart(symbol, period='6mo', interval='1d'):
    """Try both quote hosts; never turn a failed request into a zero quote."""
    errors = []
    query = urllib.parse.urlencode({'range': period, 'interval': interval, 'includePrePost': 'false'})
    for host in ('query2', 'query1'):
        url = f'https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol, safe="")}?{query}'
        for attempt in range(2):
            try:
                # The existing stocks collector uses this transport in Actions.
                # urllib remains sufficient for local installs without curl_cffi.
                try:
                    from curl_cffi import requests
                except ImportError:
                    payload = get_json(url)
                else:
                    response = requests.get(url, timeout=25, impersonate='chrome')
                    response.raise_for_status()
                    payload = response.json()
                chart = payload.get('chart') or {}
                result = (chart.get('result') or [None])[0]
                if chart.get('error') or not result:
                    raise ValueError(f'{symbol}: no chart result')
                return result
            except Exception as exc:
                errors.append(f'{host}: {type(exc).__name__}: {exc}')
                if attempt == 0:
                    time.sleep(1)
    raise RuntimeError('; '.join(errors)[-300:])


def chart_points(result):
    times = result.get('timestamp') or []
    closes = (((result.get('indicators') or {}).get('quote') or [{}])[0].get('close') or [])
    return [(int(t), finite(v)) for t, v in zip(times, closes)
            if t is not None and finite(v) is not None]
