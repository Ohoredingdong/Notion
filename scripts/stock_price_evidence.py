"""Dated provider closes and an explicit, exchange-session daily-change proof.

This is display evidence, not an execution quote.  The Yahoo history metadata is
read from the SAME response (pinned yfinance 0.2.66).  Its public metadata getter
can issue a different intraday request and is deliberately not used here.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

try:
    from .market_data_utils import exchange_calendar, finite, session_date
except ImportError:
    from market_data_utils import exchange_calendar, finite, session_date

UTC = timezone.utc
VERSION = 'completed-session-change-v1'
LOOKBACK_DAYS = {'1y': 370, '6mo': 190, '3mo': 100}
INDEX_EXCHANGES = {'^KS11': {'KSC'}, '^KQ11': {'KOE'},
                   '^GSPC': {'SNP'}, '^IXIC': {'NIM', 'NAS'}}
US_EXCHANGES = {'NMS', 'NGM', 'NCM', 'NAS', 'NASDAQ', 'NASDAQGS',
                'NASDAQGM', 'NASDAQCM', 'NYQ', 'NYSE', 'ASE', 'AMEX',
                'NYSEAMERICAN', 'PCX', 'NYSEARCA', 'BTS', 'BATS', 'CBOE'}


def response_identity(metadata, symbol, market, currency, instrument_type=None):
    """Fail closed on a wrong issuer/market/currency in the actual price reply."""
    fields = ('symbol', 'exchangeName', 'exchangeTimezoneName', 'currency', 'instrumentType')
    observed = {key: (metadata or {}).get(key) for key in fields}
    kind = instrument_type or ('INDEX' if symbol in INDEX_EXCHANGES else
                               'CURRENCY' if market == 'FX' else 'EQUITY')
    if observed['symbol'] != symbol:
        raise ValueError('provider_history_symbol_mismatch')
    if observed['instrumentType'] != kind:
        raise ValueError('provider_history_instrument_mismatch')
    if not currency or observed['currency'] != currency:
        raise ValueError('provider_history_currency_mismatch')
    zones = {'KR': {'Asia/Seoul'}, 'US': {'America/New_York'},
             'FX': {'Europe/London', 'UTC', 'Etc/UTC'}}
    if observed['exchangeTimezoneName'] not in zones.get(market, set()):
        raise ValueError('provider_history_timezone_mismatch')
    if symbol in INDEX_EXCHANGES:
        exchanges = INDEX_EXCHANGES[symbol]
    elif market == 'KR':
        exchanges = {'KOE', 'KOSDAQ'} if symbol.endswith('.KQ') else {'KSC', 'KOSPI'}
    elif market == 'US':
        exchanges = US_EXCHANGES
    else:
        exchanges = {'CCY'}
    if str(observed['exchangeName']).upper() not in exchanges:
        raise ValueError('provider_history_exchange_mismatch')
    return {'source_identity_verified': True, 'provider_symbol': symbol,
            'market': market, 'currency': currency, 'source_metadata': observed}


def _latest_close(frame, cutoff, calendar):
    latest = None
    if frame is None:
        return None
    for stamp, row in frame.iterrows():
        day = session_date(stamp)
        value = finite(row.get('Close'))
        if value is not None and value > 0 and day <= cutoff and (calendar is None or calendar.is_session(day)):
            latest = max(latest or day, day)
    return latest


def fetch_daily_history(ticker, symbol, market, expected_session, *, currency=None,
                        period='1y', calendar=None, instrument_type=None):
    """Fetch once; only a stale valid reply gets one absolute-window retry.

    A second fetch cannot make old bars current by changing a timestamp.  If it
    fails or returns older data, the first verified historical reply is retained
    with its original observed session and a recorded failed retry.
    """
    if period not in LOOKBACK_DAYS:
        raise ValueError('unsupported_bounded_history_period')
    date.fromisoformat(expected_session)
    currency = currency or ('KRW' if market == 'KR' else 'USD' if market == 'US' else None)
    cal = calendar
    if market in ('KR', 'US') and cal is None:
        cal = exchange_calendar(market, int(expected_session[:4]))
    common = {'interval': '1d', 'auto_adjust': False, 'actions': True,
              'repair': False, 'prepost': False, 'timeout': 12, 'raise_errors': True}
    attempts = []

    def request(window):
        frame = ticker.history(**common, **window)
        # Accessing the cached metadata does not perform a second HTTP request.
        metadata = dict(getattr(getattr(ticker, '_price_history', None), '_history_metadata', None) or {})
        identity = response_identity(metadata, symbol, market, currency, instrument_type)
        last = _latest_close(frame, expected_session, cal)
        attempts.append({'request': window, 'received_at': datetime.now(UTC).isoformat(),
                         'latest_completed_session': last, 'status': 'verified_response'})
        return frame, identity, last

    frame, identity, last = request({'period': period})
    selected_attempt = 1
    if last != expected_session:
        end = date.fromisoformat(expected_session) + timedelta(days=1)
        window = {'start': (end - timedelta(days=LOOKBACK_DAYS[period])).isoformat(), 'end': end.isoformat()}
        try:
            retry_frame, retry_identity, retry_last = request(window)
            if retry_last is not None and (last is None or retry_last >= last):
                frame, identity, last = retry_frame, retry_identity, retry_last
                selected_attempt = 2
        except Exception as exc:
            attempts.append({'request': window, 'received_at': datetime.now(UTC).isoformat(),
                             'status': 'failed', 'error': type(exc).__name__ + ': ' + str(exc)[:140]})
    return frame, {**identity, 'expected_session': expected_session,
                   'latest_completed_session': last, 'selected_attempt': selected_attempt,
                   'collection_attempts': len(attempts), 'stale_retry_attempted': len(attempts) > 1,
                   'attempts': attempts, 'basis': 'provider_close_auto_adjust_false'}


def daily_change(bars, market, provider_symbol, currency, evidence, *, calendar=None):
    """A missing exchange session must never turn a multi-day move into 1-day %."""
    rows = sorted(bars or [], key=lambda row: row.get('date', ''))
    current = rows[-1] if rows else {}
    previous = rows[-2] if len(rows) > 1 else {}
    value, prior = finite(current.get('close')), finite(previous.get('close'))
    result = {'version': VERSION, 'status': 'unavailable', 'market': market,
              'provider_symbol': provider_symbol, 'currency': currency,
              'source_identity_verified': evidence.get('source_identity_verified') is True,
              'price_session': current.get('date'), 'close': value,
              'previous_session': previous.get('date'), 'previous_close': prior,
              'expected_previous_session': None, 'consecutive_sessions': False,
              'change_1d_pct': None, 'basis': 'provider_close_auto_adjust_false', 'reason': None}
    if (not result['source_identity_verified'] or evidence.get('provider_symbol') != provider_symbol or
            evidence.get('market') != market or not currency or evidence.get('currency') != currency):
        result['reason'] = 'source_identity_or_currency_unverified'
        return result
    if market not in ('KR', 'US'):
        result['reason'] = 'no_single_exchange_session_basis'
        return result
    if not rows or value is None or value <= 0:
        result['reason'] = 'current_close_unavailable'
        return result
    try:
        cal = calendar or exchange_calendar(market, int(current['date'][:4]))
        if not cal.is_session(current['date']):
            raise ValueError('not_an_exchange_session')
        result['expected_previous_session'] = session_date(cal.previous_session(current['date']))
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        result['reason'] = 'exchange_session_unverified'
        return result
    result['consecutive_sessions'] = previous.get('date') == result['expected_previous_session']
    if not result['consecutive_sessions']:
        result['reason'] = 'previous_exchange_session_missing'
    elif prior is None or prior <= 0:
        result['reason'] = 'previous_close_unavailable'
    elif finite(current.get('split')) not in (None, 0):
        result['reason'] = 'latest_session_split_requires_basis_review'
    else:
        result.update(status='verified', change_1d_pct=(value / prior - 1) * 100)
    return result
