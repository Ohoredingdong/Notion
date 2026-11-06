"""Seal existing technical inputs and independently recheck displayed results.

No prices are fetched here. Compact JSON strings keep the original float values
through the outer eight-decimal serializer without duplicating a full chart.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from statistics import mean

from market_data_utils import exchange_calendar, finite, market_session_clock, session_date, utc_stamp
from stock_price_evidence import response_identity

VERSION = 'technical-window-evidence-v1'
BAR_FIELDS = ('date', 'open', 'high', 'low', 'close', 'volume', 'split')
BENCH_FIELDS = ('date', 'close')
METRICS = ('close', 'volume', 'avg_volume20', 'volume_ratio', 'ma20', 'ma60', 'atr14',
           'prior_high20', 'return20_pct', 'relative20_pp', 'support10', 'resistance_1y',
           'support_loss_pct', 'reward_risk')
WINDOWS = {'minimum_consecutive_sessions': 61, 'ma20': 20, 'ma60': 60,
           'atr14': 14, 'prior_high20': 20, 'return_sessions': 20,
           'support_prior_sessions': 10, 'resistance_max_prior_sessions': 252,
           'recent_split_sessions': 30}


class ObservedBars(list):
    """A normal bar list carrying its already-fetched response provenance."""
    def __init__(self, rows=(), source_evidence=None):
        super().__init__(rows)
        self.source_evidence = copy.deepcopy(source_evidence or {})


def _pack(rows, fields, source, original_count):
    wire = json.dumps([[row.get(field) for field in fields] for row in rows],
                      ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return {'columns': list(fields), 'rows_json': wire,
            'rows_sha256': hashlib.sha256(wire.encode()).hexdigest(),
            'stored_count': len(rows), 'original_count': original_count,
            'source': copy.deepcopy(source or {})}


def seal_technical_inputs(bars, benchmark, market):
    stock_rows = bars[-254:]
    end = bars[-1]['date'] if bars else None
    bench_rows = [row for row in benchmark if end and row['date'] <= end][-21:]
    return {'version': VERSION, 'market': market,
            'formula_version': 'existing-technical-v7.1',
            'stock': _pack(stock_rows, BAR_FIELDS, getattr(bars, 'source_evidence', {}), len(bars)),
            'benchmark': _pack(bench_rows, BENCH_FIELDS, getattr(benchmark, 'source_evidence', {}), len(benchmark)),
            'windows': dict(WINDOWS),
            'basis': 'original provider OHLCV, auto_adjust=False; resistance uses available prior sessions up to 252',
            'limitations': 'Historical extrema and ratios are not executable prices, a probability, or a loss guarantee.'}


def _recent_sessions(market, end, count):
    cal = exchange_calendar(market, int(end[:4]))
    if not cal.is_session(end):
        raise ValueError('end_not_exchange_session')
    dates = [end]
    for _ in range(count-1):
        dates.append(session_date(cal.previous_session(dates[-1])))
    return list(reversed(dates))


def recalculate_technical(bars, benchmark, market):
    """Read the saved OHLCV observations, not the publisher's derived fields."""
    if len(bars) < 61:
        return {'status': 'missing', 'reason': 'fewer_than_61_sessions'}
    expected = _recent_sessions(market, bars[-1]['date'], 61)
    if [row['date'] for row in bars[-61:]] != expected:
        return {'status': 'missing', 'reason': 'recent_exchange_session_missing'}
    last = bars[-1]
    close = last['close']
    prior20 = bars[-21:-1]
    ranges = [max(row['high']-row['low'], abs(row['high']-bars[i-1]['close']),
                  abs(row['low']-bars[i-1]['close'])) for i, row in enumerate(bars) if i]
    average_volume = mean(row['volume'] for row in prior20)
    change = lambda current, prior: (current/prior-1)*100 if prior > 0 else None
    bench_by = {row['date']: row['close'] for row in benchmark}
    start, end = bars[-21]['date'], last['date']
    relative = (change(close, bars[-21]['close']) - change(bench_by[end], bench_by[start])
                if start in bench_by and end in bench_by else None)
    support = min(row['low'] for row in bars[-11:-1])
    resistance = max(row['high'] for row in bars[-253:-1])
    risk, reward = close-support, resistance-close
    return {'status': 'ok', 'date': end, 'close': close, 'volume': last['volume'],
            'avg_volume20': average_volume,
            'volume_ratio': last['volume']/average_volume if average_volume > 0 else None,
            'ma20': mean(row['close'] for row in bars[-20:]),
            'ma60': mean(row['close'] for row in bars[-60:]), 'atr14': mean(ranges[-14:]),
            'prior_high20': max(row['high'] for row in prior20),
            'return20_pct': change(close, bars[-21]['close']), 'relative20_pp': relative,
            'support10': support, 'resistance_1y': resistance,
            'support_loss_pct': risk/close*100 if risk > 0 else None,
            'reward_risk': reward/risk if risk > 0 and reward > 0 else None,
            'recent_split': any(row['split'] != 0 for row in bars[-30:])}


def validate_technical_evidence(row, now=None):
    """Return evidence/row binding and independent arithmetic errors for one row."""
    now = now or datetime.now(timezone.utc)
    technical = row.get('technical') or {}
    evidence = technical.get('evidence') or {}
    errors, checks = [], 0
    def check(condition, issue, **details):
        nonlocal checks
        checks += 1
        if not condition:
            errors.append({'issue': issue, **details})
    def same_number(actual, expected):
        if expected is None:
            return actual is None
        return finite(actual) is not None and finite(actual) == round(expected, 8)
    check(evidence.get('version') == VERSION, 'technical_evidence_missing_or_unknown')
    if not evidence or evidence.get('version') != VERSION:
        return {'status': 'failed', 'checks': checks, 'errors': errors, 'recalculated': {}, 'coverage': {}}
    market = row.get('market')
    check(market in ('KR', 'US') and evidence.get('market') == market, 'technical_market_mismatch')
    check(evidence.get('formula_version') == 'existing-technical-v7.1', 'technical_formula_version_mismatch')
    check(evidence.get('windows') == WINDOWS, 'technical_window_contract_mismatch')

    def unpack(block, fields, label, maximum):
        if not isinstance(block, dict):
            check(False, label+'_block_missing'); return []
        wire = block.get('rows_json')
        check(block.get('columns') == list(fields), label+'_columns_mismatch')
        if not isinstance(wire, str):
            check(False, label+'_rows_missing'); return []
        check(hashlib.sha256(wire.encode()).hexdigest() == block.get('rows_sha256'), label+'_rows_digest_mismatch')
        try:
            array = json.loads(wire)
            valid = isinstance(array, list) and len(array) <= maximum and all(isinstance(x, list) and len(x) == len(fields) for x in array)
        except (ValueError, TypeError):
            valid, array = False, []
        check(valid, label+'_rows_invalid')
        if not valid:
            return []
        check(block.get('stored_count') == len(array), label+'_stored_count_mismatch')
        count = block.get('original_count')
        check(isinstance(count, int) and not isinstance(count, bool) and count >= len(array), label+'_original_count_invalid')
        if label == 'stock' and isinstance(count, int):
            check(len(array) == min(count, maximum), 'stock_window_was_truncated_before_cap')
        points = [dict(zip(fields, values)) for values in array]
        dates = [p['date'] for p in points]
        valid_dates = all(isinstance(day, str) and len(day) == 10 for day in dates)
        check(valid_dates and dates == sorted(set(dates)), label+'_dates_not_unique_ordered')
        try:
            if not valid_dates:
                raise ValueError('invalid_session_date')
            cal = exchange_calendar(market, int(dates[-1][:4])) if dates else None
            check(all(cal.is_session(day) for day in dates), label+'_nonexchange_session')
        except (ValueError, TypeError, KeyError, IndexError):
            check(False, label+'_invalid_session_date')
        for point in points:
            numeric = all(finite(point[k]) is not None for k in fields if k != 'date')
            check(numeric and finite(point['close']) is not None and point['close'] > 0,
                  label+'_invalid_numeric_observation', date=point['date'])
            if numeric and label == 'stock':
                check(point['open'] > 0 and point['low'] > 0 and point['volume'] >= 0 and point['split'] >= 0 and
                      point['high'] >= max(point['open'], point['close']) and point['low'] <= min(point['open'], point['close']),
                      'stock_invalid_ohlcv_geometry', date=point['date'])
        return points

    stock_block, bench_block = evidence.get('stock') or {}, evidence.get('benchmark') or {}
    bars = unpack(stock_block, BAR_FIELDS, 'stock', 254)
    benchmark = unpack(bench_block, BENCH_FIELDS, 'benchmark', 21)
    source = stock_block.get('source') or {}
    bench_source = bench_block.get('source') or {}
    symbol = row.get('symbol') or ''
    provider = row.get('source_symbol') or (symbol+'.KS' if market == 'KR' else symbol)
    cutoff = (row.get('expected_session') or {}).get('date')

    def verify_source(proof, points, label, provider_symbol, instrument_type):
        if not points:
            return
        check(proof.get('provider_symbol') == provider_symbol and proof.get('market') == market and
              proof.get('currency') == row.get('currency') and proof.get('source_identity_verified') is True,
              label+'_source_identity_mismatch')
        try:
            response_identity(proof.get('source_metadata') or {}, provider_symbol, market, row.get('currency'), instrument_type)
        except (ValueError, TypeError, KeyError):
            check(False, label+'_response_metadata_invalid')
        else:
            check(True, label+'_response_metadata_invalid')
        check(proof.get('basis') == 'provider_close_auto_adjust_false', label+'_adjustment_basis_mismatch')
        check(isinstance(cutoff, str) and proof.get('expected_session') == cutoff and
              all(isinstance(p['date'], str) and p['date'] <= cutoff for p in points),
              label+'_cutoff_mismatch')
        attempts = proof.get('attempts') or []
        selected = proof.get('selected_attempt')
        valid = isinstance(selected, int) and not isinstance(selected, bool) and 1 <= selected <= len(attempts)
        check(valid, label+'_selected_response_missing')
        if valid:
            attempt = attempts[selected-1]
            observed = utc_stamp(attempt.get('received_at'))
            check(attempt.get('status') == 'verified_response' and observed is not None and observed <= now,
                  label+'_observation_time_invalid')
            request = attempt.get('request') or {}
            check(request.get('period') == '1y' or (bool(request.get('start')) and bool(request.get('end'))),
                  label+'_source_window_missing')
            if observed is not None and observed <= now:
                try:
                    completed = market_session_clock(market, observed)['expected_session']
                    check(bool(cutoff) and cutoff <= completed, label+'_uncompleted_cutoff')
                except (ValueError, TypeError, KeyError):
                    check(False, label+'_source_clock_invalid')
        if label == 'stock':
            check(proof == (row.get('price_source') or {}), 'technical_quote_source_mismatch')
            check(proof.get('latest_completed_session') == points[-1]['date'], 'technical_source_endpoint_mismatch')

    verify_source(source, bars, 'stock', provider, 'EQUITY')
    bench_symbol = technical.get('benchmark_symbol') or bench_source.get('provider_symbol')
    allowed_benchmarks = ('SPY',) if market == 'US' else ('^KS11', '^KQ11')
    check(not benchmark or bench_symbol in allowed_benchmarks, 'benchmark_market_mismatch')
    verify_source(bench_source, benchmark, 'benchmark', bench_symbol, 'ETF' if bench_symbol == 'SPY' else 'INDEX')
    if bars:
        check(bars[-1]['date'] == row.get('price_session'), 'technical_quote_session_mismatch')
        check(same_number(row.get('price'), bars[-1]['close']), 'technical_quote_close_mismatch')
    else:
        check(row.get('price') is None, 'technical_inputs_missing_for_saved_quote')
    # Reject bad input contracts before allowing a recomputation to certify them.
    recalculated = {}
    if not errors:
        try:
            recalculated = recalculate_technical(bars, benchmark, market)
        except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError):
            check(False, 'technical_recalculation_failed')
    if recalculated:
        check(technical.get('status') == recalculated['status'], 'technical_eligibility_mismatch')
        for field in METRICS:
            check(same_number(technical.get(field), recalculated.get(field)),
                  'technical_value_mismatch', field=field,
                  published=technical.get(field), recalculated=recalculated.get(field))
        if isinstance(row.get('liquidity'), dict):
            expected_turnover = mean(p['close']*p['volume'] for p in bars[-20:]) if recalculated['status'] == 'ok' else None
            check(same_number(row['liquidity'].get('avg_turnover20'), expected_turnover),
                  'liquidity_value_mismatch', field='liquidity.avg_turnover20',
                  published=row['liquidity'].get('avg_turnover20'), recalculated=expected_turnover)
        if recalculated['status'] == 'ok':
            check(technical.get('date') == recalculated['date'], 'technical_date_mismatch')
            check(technical.get('recent_split') is recalculated['recent_split'], 'technical_split_flag_mismatch')
            if technical.get('relative20_pp') is not None:
                expected_bench = _recent_sessions(market, bars[-1]['date'], 21)
                check([p['date'] for p in benchmark] == expected_bench, 'benchmark_comparison_sessions_missing')
        else:
            check(technical.get('date') is None and technical.get('recent_split') is None,
                  'technical_missing_state_contains_unsupported_fields')
    return {'status': 'failed' if errors else 'verified' if recalculated.get('status') == 'ok' else 'verified_withheld',
            'checks': checks, 'errors': errors, 'recalculated': recalculated,
            'coverage': {'stock_stored_sessions': len(bars), 'stock_available_sessions': stock_block.get('original_count'),
                         'benchmark_stored_sessions': len(benchmark),
                         'resistance_available_prior_sessions': max(0, min(252, len(bars)-1)),
                         'numeric_fields': len(METRICS)}}
