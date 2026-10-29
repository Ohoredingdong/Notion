"""Collect real historical candles, train direction models, freeze future calls.
Failure never falls back to fabricated candles or a newly dated cached quote.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import numpy as np
import pandas as pd
from stock_forecast_model import (VERSION, POLICY, normalise_history, fit_model,
                                  make_prediction, score_prediction, stamp, digest)
UTC = timezone.utc
DEFAULT = [
    ('^KS11', '코스피', 'KR'), ('^KQ11', '코스닥', 'KR'),
    ('^GSPC', 'S&P 500', 'US'), ('^IXIC', '나스닥 종합', 'US'),
    ('005930.KS', '삼성전자', 'KR'), ('000660.KS', 'SK하이닉스', 'KR'),
    ('035420.KS', 'NAVER', 'KR'), ('403870.KQ', 'HPSP', 'KR'),
    ('AAPL', 'Apple', 'US'), ('MSFT', 'Microsoft', 'US'),
    ('NVDA', 'NVIDIA', 'US'), ('ON', 'ON Semiconductor', 'US')]


def write(path, value):
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temp.replace(path)


def readlines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def freeze(path, records):
    existing = readlines(path)
    by_id = {r['id']: r for r in existing}
    new = []
    for r in records:
        if r.get('status') != 'research_prediction':
            continue
        if r['id'] not in by_id:
            by_id[r['id']] = r
            new.append(r)
    if new:
        with path.open('a') as out:
            for r in new:
                out.write(json.dumps(r, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n')
    return by_id


def collect(spec, mode):
    symbol, name, market = spec
    import yfinance as yf
    raw = yf.Ticker(symbol).history(period='5y' if mode == 'daily' else '60d',
                                   interval='1d' if mode == 'daily' else '5m',
                                   auto_adjust=False, actions=True, prepost=False,
                                   timeout=18, raise_errors=True)
    received = datetime.now(UTC)
    if raw is None or raw.empty:
        raise ValueError('provider_returned_no_candles')
    # Explicit unresolved corporate actions are not allowed inside a target bar.
    bars = normalise_history(raw, market, mode, received)
    if 'Stock Splits' in raw.columns:
        for idx, val in raw['Stock Splits'].items():
            if val and np.isfinite(val):
                split_day = pd.Timestamp(idx).date().isoformat()
                if split_day == bars.iloc[-1]['session']:
                    raise ValueError('latest_session_split_review_required')
    return bars, received


def process(spec, mode):
    symbol, name, market = spec
    try:
        bars, received = collect(spec, mode)
        fitted = fit_model(bars, mode)
        record = make_prediction(bars, fitted, symbol, market, mode, received)
        record.update(name=name, source_url='https://finance.yahoo.com/quote/'+symbol,
                      collector='yfinance', provider_is_official_exchange=False,
                      source_run_id=os.environ.get('GITHUB_RUN_ID'),
                      source_commit=os.environ.get('GITHUB_SHA'),
                      history_sha256=digest([{'t': row.start.isoformat(), 'o': row.open,
                                             'h': row.high, 'l': row.low, 'c': row.close}
                                            for row in bars.itertuples()]))
        return record, bars
    except Exception as exc:
        # Do not print request URLs or credentials if a provider fails.
        return {'symbol': symbol, 'name': name, 'market': market, 'mode': mode,
                'status': 'no_call', 'probabilities': None, 'direction': None,
                'reason': type(exc).__name__+': '+str(exc).split('https:')[0][:140],
                'issued_at': datetime.now(UTC).isoformat(), 'recommendation': False}, None


def run(root=Path('.'), specs=None, modes=('daily', 'intraday')):
    specs = specs or DEFAULT
    all_records, histories = [], {}
    # Network+model tasks are independent. Native BLAS threads should be set to 1.
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(process, spec, mode): (spec[0], mode) for spec in specs for mode in modes}
        for future in as_completed(jobs):
            record, bars = future.result()
            all_records.append(record)
            if bars is not None:
                histories[jobs[future]] = bars
            print(record['symbol'], record['mode'], record['status'],
                  record.get('validation', {}).get('validation_status', record.get('reason')), flush=True)
    now = stamp(datetime.now(UTC))
    ledger = root/'stock-forecast-ledger.jsonl'
    previous = {r['id']: r for r in readlines(ledger)}
    ready = []
    for r in all_records:
        if r.get('status') == 'research_prediction' and r['id'] in previous:
            # Never move an old issue timestamp forward to make it look new.
            r = previous[r['id']]
        elif r.get('status') == 'research_prediction' and stamp(r['target']['start']) <= now+pd.Timedelta(seconds=45):
            r = {**r, 'status': 'no_call', 'reason': 'publication_window_missed',
                 'probabilities': None, 'direction': None}
        ready.append(r)
    ready.sort(key=lambda r: (r['mode'], r['market'], r['symbol']))
    frozen = freeze(ledger, ready)
    deliveries = readlines(root/'stock-forecast-deliveries.jsonl')
    delivery_times = {}
    for d in deliveries:
        if d.get('status') == 'public_verified':
            for rid in d.get('prediction_ids', []):
                delivery_times.setdefault(rid, d['verified_at'])
    prior_outcomes = {r['id']: r for r in readlines(root/'stock-forecast-outcomes.jsonl') if r.get('status') == 'observed'}
    fresh_outcomes = []
    pending = 0
    for old in frozen.values():
        if old['id'] in prior_outcomes:
            continue
        bars = histories.get((old['symbol'], old['mode']))
        if bars is None:
            pending += 1
            continue
        outcome = score_prediction(old, bars, now, delivery_times.get(old['id']))
        if outcome and outcome['status'] == 'observed':
            fresh_outcomes.append(outcome)
            prior_outcomes[old['id']] = outcome
        else:
            pending += 1
    if fresh_outcomes:
        with (root/'stock-forecast-outcomes.jsonl').open('a') as f:
            for outcome in fresh_outcomes:
                f.write(json.dumps(outcome, ensure_ascii=False, allow_nan=False)+'\n')
    # Ensure publication has all append-only files even on the initial no-call run.
    for path in [ledger, root/'stock-forecast-outcomes.jsonl', root/'stock-forecast-deliveries.jsonl']:
        path.touch(exist_ok=True)
    verified = [v for v in prior_outcomes.values() if v['public_before_target_verified']]
    summary = {'recorded_predictions': len(frozen), 'matured_observations': len(prior_outcomes),
               'publicly_timely_observations': len(verified), 'pending_or_unavailable': pending,
               'live_accuracy': float(np.mean([v['correct'] for v in verified])) if verified else None,
               'baseline_comparison': 'historical holdout shown per model; forward baseline pending',
               'not_trade_returns': True}
    artifact = {'version': VERSION, 'generated_at': now.isoformat(),
                'source_run_id': os.environ.get('GITHUB_RUN_ID'), 'policy': POLICY,
                'status': 'research_only', 'real_time_connected': False,
                'refresh_mode': 'scheduled_best_effort_not_realtime',
                'coverage': len(specs), 'counts': dict(Counter(r['status'] for r in ready)),
                'records': ready, 'forward_evaluation': summary,
                'disclosures': ['실제 과거 OHLC로 학습한 모델 추정치',
                                '수익확률·매수승인 아님; strict-green 변경 없음',
                                '지연·유실·휴장 시 예측 보류', '다수 모델 중 우연한 성과 가능; 미래 검증 전'],
                'schedule_note': 'Actions 지연 가능. 장중 예측은 표시된 미래 시간 구간에만 유효.'}
    write(root/'stock-direction-forecast.json', artifact)
    print(json.dumps({'counts': artifact['counts'], 'evaluation': summary}, ensure_ascii=False), flush=True)
    return artifact


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=len(DEFAULT))
    parser.add_argument('--mode', choices=['daily', 'intraday', 'both'], default='both')
    args = parser.parse_args()
    run(specs=DEFAULT[:args.limit], modes=('daily', 'intraday') if args.mode == 'both' else (args.mode,))
