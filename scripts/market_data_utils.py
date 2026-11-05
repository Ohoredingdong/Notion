"""Read public market snapshots with bounded retries and source timestamps."""
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

UTC = timezone.utc
MARKETS = {'KR': ('XKRX', 'Asia/Seoul'), 'US': ('XNYS', 'America/New_York')}


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def utc_stamp(value):
    """Reject undated/naive values instead of guessing the producer's timezone."""
    if hasattr(value, 'to_pydatetime'):
        value = value.to_pydatetime()
    try:
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return stamp.astimezone(UTC) if stamp.tzinfo is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def session_date(value):
    return value.date().isoformat() if hasattr(value, 'date') else str(value)[:10]


@lru_cache(maxsize=8)
def exchange_calendar(market, year):
    """A missing calendar is an explicit failure, never a weekday-only fallback."""
    import exchange_calendars as xc
    name, _ = MARKETS[market]
    return xc.get_calendar(name, start=f'{year - 1}-01-01', end=f'{year + 1}-12-31')


def market_session_clock(market, now=None, delay_minutes=30, calendar=None):
    """Latest *completed* regular session, including holidays, DST and short days.

    The provider delay is a collection policy, not a real-time-feed guarantee.
    ``calendar`` makes time-boundary regression tests deterministic and offline.
    """
    now = utc_stamp(now or datetime.now(UTC))
    if now is None or market not in MARKETS or delay_minutes < 0:
        raise ValueError('invalid_market_clock')
    name, zone = MARKETS[market]
    cal = calendar if calendar is not None else exchange_calendar(market, now.year)
    day = now.astimezone(ZoneInfo(zone)).date().isoformat()
    current = cal.date_to_session(day, direction='previous')
    current_close = utc_stamp(cal.session_close(current))
    current_open = utc_stamp(cal.session_open(current))
    if current_close is None or current_open is None:
        raise ValueError('calendar_session_timestamp_missing')
    label = current
    if current_close + timedelta(minutes=delay_minutes) > now:
        label = cal.previous_session(current)
    close = utc_stamp(cal.session_close(label))
    following = cal.next_session(label)
    return {
        'market': market, 'calendar': name, 'timezone': zone,
        'expected_session': session_date(label),
        'closed_at': close.isoformat(),
        'available_at': (close + timedelta(minutes=delay_minutes)).isoformat(),
        'delay_minutes': delay_minutes,
        'next_session': session_date(following),
        'next_open': utc_stamp(cal.session_open(following)).isoformat(),
        'next_close': utc_stamp(cal.session_close(following)).isoformat(),
        'market_open': current_open <= now < current_close,
        'calendar_note': '거래소 일정 라이브러리 기준; 임시휴장은 거래소 원문 확인 필요',
    }


def completed_daily_points(points, market, now=None, calendar=None):
    """Keep dated positive closes only after the corresponding session has ended."""
    now = utc_stamp(now or datetime.now(UTC))
    if now is None:
        raise ValueError('timezone_required')
    if market == 'FX':
        # A provider FX daily bar has no single KR/US exchange closing auction.
        # Keep only fully elapsed UTC dates and label that conservative basis.
        cutoff = (now.date() - timedelta(days=1)).isoformat()
        clock = {'expected_session': None, 'completed_through': cutoff,
                 'calendar': 'elapsed_UTC_provider_dates', 'delay_minutes': None}
        is_session = lambda day: True
    else:
        cal = calendar if calendar is not None else exchange_calendar(market, now.year)
        clock = market_session_clock(market, now, calendar=cal)
        cutoff = clock['expected_session']
        is_session = cal.is_session
    output = {}
    for date, value in points:
        day = session_date(date)
        try:
            datetime.strptime(day, '%Y-%m-%d')
        except (TypeError, ValueError):
            continue
        close = finite(value)
        if day <= cutoff and close is not None and close > 0 and is_session(day):
            output[day] = close
    return sorted(output.items()), clock


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

