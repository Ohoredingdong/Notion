"""Real Yahoo OHLC, protected session initialization and strict bar boundaries.
Same unofficial provider, not an independent-source cross-check.
"""
from datetime import datetime, timezone
import threading
import pandas as pd

_CALENDAR_LOCK = threading.Lock()
_PREPARED_YEAR = None


def prepare_sessions(year=None):
    """XKRX holiday construction mutates pandas objects: never initialize in parallel.

The actual length/boolean-mask failure was reproduced with concurrent calendar
construction. Warm the model's cached KR/US calendars BEFORE any worker uses them.
"""
    global _PREPARED_YEAR
    year = year or datetime.now(timezone.utc).year
    with _CALENDAR_LOCK:
        if _PREPARED_YEAR != year:
            from stock_forecast_model import calendar
            for market in ('KR', 'US'):
                calendar(market, year)
            _PREPARED_YEAR = year


def regular_grid(frame, mode):
    if mode == 'daily':
        return frame
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError('intraday_timezone_missing')
    # Some provider responses append a live point such as 13:50:10. This is not
    # a completed 5m candle. Drop it; never round its timestamp or invent OHLC.
    idx = frame.index
    aligned = (idx.minute % 5 == 0) & (idx.second == 0) & (idx.microsecond == 0) & (idx.nanosecond == 0)
    output = frame.loc[aligned].copy()
    if output.index.duplicated().any():
        raise ValueError('duplicate_bar_timestamp')
    if output.empty:
        raise ValueError('no_grid_aligned_five_minute_candles')
    return output


def history(symbol, mode):
    prepare_sessions()
    import yfinance as yf
    frame = yf.Ticker(symbol).history(period='5y' if mode == 'daily' else '60d',
                                    interval='1d' if mode == 'daily' else '5m',
                                    auto_adjust=False, actions=True, prepost=False,
                                    timeout=18, raise_errors=True)
    return regular_grid(frame, mode)


def self_test():
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: prepare_sessions(2026), range(32)))
    from stock_forecast_model import calendar
    assert str(calendar('KR', 2026).date_to_session('2026-10-28', direction='none'))[:10] == '2026-10-28'
    index = pd.to_datetime(['2026-10-29T00:00:00Z', '2026-10-29T00:05:00Z', '2026-10-29T00:05:10Z'])
    frame = pd.DataFrame({'Open': [100, 101, 102], 'High': [102, 103, 104],
                          'Low': [99, 100, 101], 'Close': [101, 102, 103]}, index=index)
    clean = regular_grid(frame, 'intraday')
    assert len(clean) == 2 and clean.index[-1] == index[1]
    assert regular_grid(frame, 'daily') is frame
    try:
        regular_grid(frame.set_axis(index.tz_localize(None)), 'intraday')
    except ValueError:
        pass
    else:
        raise AssertionError('timezone must be explicit')
    try:
        regular_grid(pd.concat([frame.iloc[:1], frame.iloc[:1]]), 'intraday')
    except ValueError:
        pass
    else:
        raise AssertionError('duplicate bars must be rejected')
    print('Source guards passed: 32 concurrent initializations; off-grid, UTC and duplicate checks')

if __name__ == '__main__':
    self_test()
