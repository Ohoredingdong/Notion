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
import stock_forecast_learning as learning
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
    from stock_forecast_sources import history
    raw = history(symbol, mode)
    received = datetime.now(UTC)
    if raw is None or raw.empty:
        raise ValueError('provider_returned_no_candles')
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
    bars = None
    try:
        bars, received = collect(spec, mode)
        fitted = fit_model(bars, mode)
        record = make_prediction(bars, fitted, symbol, market, mode, received)
        record['frozen_baseline_probabilities'] = learning.pdict(fitted['baseline'])
        record.update(name=name, source_url='https://finance.yahoo.com/quote/'+symbol,
                      collector='yfinance', provider_is_official_exchange=False,
                      source_run_id=os.environ.get('GITHUB_RUN_ID'),
                      source_commit=os.environ.get('GITHUB_SHA'),
                      history_sha256=digest([{'t': row.start.isoformat(), 'o': row.open,
                                             'h': row.high, 'l': row.low, 'c': row.close}
                                            for row in bars.itertuples()]))
        return record, bars
    except Exception as exc:
        return {'symbol': symbol, 'name': name, 'market': market, 'mode': mode,
                'status': 'no_call', 'probabilities': None, 'direction': None,
                'reason': type(exc).__name__+': '+str(exc).split('https:')[0][:140],
                'issued_at': datetime.now(UTC).isoformat(), 'recommendation': False}, bars


def label_validation(record):
    """An adaptive model must not inherit the incumbent's historical score."""
    if (record.get('online_learning') or {}).get('active_variant') != 'adaptive':
        return record
    out = dict(record)
    out['incumbent_historical_validation'] = record.get('incumbent_historical_validation', record.get('validation', {}))
    out['validation'] = {'validation_status':'adaptive_forward_research_only',
                         'test_samples':0, 'test_sessions':0, 'accuracy':None,
                         'baseline_accuracy':None, 'above_baseline_in_this_holdout':False,
                         'live_validated':False, 'forward_report':learning.REPORT_FILE}
    return out


def complete_target(record, bars):
    if record['mode'] != 'intraday':
        return True
    start, end = stamp(record['target']['start']), stamp(record['target']['end'])
    segment = bars[(bars.start >= start) & (bars.end <= end)].sort_values('start')
    expected = int((end-start).total_seconds()/300)
    return bool(expected == 6 and len(segment) == expected and
                list(segment.start) == list(pd.date_range(start, periods=expected, freq='5min')) and
                segment.session.nunique() == 1)


def run(root=Path('.'), specs=None, modes=('daily', 'intraday')):
    specs = specs or DEFAULT
    state, parent_hash = learning.load_state(root)
    ledger = root/'stock-forecast-ledger.jsonl'
    old_records = readlines(ledger)
    old_outcomes = readlines(root/'stock-forecast-outcomes.jsonl')
    deliveries = readlines(root/'stock-forecast-deliveries.jsonl')
    all_records, histories = [], {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(process, spec, mode): (spec[0], mode) for spec in specs for mode in modes}
        for future in as_completed(jobs):
            record, bars = future.result()
            all_records.append(record)
            if bars is not None: histories[jobs[future]] = bars
            print(record['symbol'], record['mode'], record['status'], flush=True)
    now = stamp(datetime.now(UTC))
    prior_outcomes = {r['id']: r for r in old_outcomes if r.get('status') == 'observed'}
    public = learning.delivery_map(deliveries)
    fresh = []
    for r in old_records:
        if r['id'] in prior_outcomes: continue
        bars = histories.get((r['symbol'], r['mode']))
        if bars is None or not complete_target(r, bars): continue
        outcome = score_prediction(r, bars, now, public.get(r['id']))
        if outcome and outcome['status'] == 'observed':
            outcome['source_checked_at'] = now.isoformat()
            outcome['single_provider_not_execution'] = True
            fresh.append(outcome); prior_outcomes[r['id']] = outcome
    learning.append_unique(root/'stock-forecast-outcomes.jsonl', fresh)
    outcomes = list(prior_outcomes.values())
    pairs, _ = learning.joined(old_records, outcomes, deliveries, now)
    events = learning.select_variant(state, pairs, now)
    events += learning.learn(state, pairs, now)
    ready, attempts = [], []
    first_by_event = {}
    for r in sorted(old_records, key=lambda r:r.get('issued_at','')):
        if learning.contract(r): first_by_event.setdefault(learning.key(r),r)
    run_id = str(os.environ.get('GITHUB_RUN_ID') or now.isoformat())
    for r in all_records:
        if r.get('status') == 'research_prediction':
            existing = first_by_event.get(learning.key(r))
            if existing is not None:
                r = existing
            elif stamp(r['target']['start']) <= stamp(datetime.now(UTC))+pd.Timedelta(seconds=45):
                r = {**r, 'status':'no_call', 'probabilities':None, 'direction':None,
                     'reason':'publication_window_missed'}
            else:
                r = learning.augment(r, state, datetime.now(UTC))
        ready.append(label_validation(r))
        attempt={'version':learning.VERSION, 'run_id':run_id, 'symbol':r['symbol'],
                 'mode':r['mode'], 'checked_at':now.isoformat(), 'status':r['status'],
                 'prediction_id':r.get('id') if r['status']=='research_prediction' else None,
                 'reason':r.get('reason') if r['status']!='research_prediction' else None}
        attempt['id']=digest({'run':run_id,'attempt':os.environ.get('GITHUB_RUN_ATTEMPT','1'),
                              'symbol':r['symbol'],'mode':r['mode'],'version':learning.VERSION})
        attempts.append(attempt)
    ready.sort(key=lambda r:(r['mode'],r['market'],r['symbol']))
    frozen = freeze(ledger, ready)
    attempts_by_id = learning.append_unique(root/learning.ATTEMPTS_FILE, attempts)
    learning.append_unique(root/learning.EVENTS_FILE, events)
    state.update(revision=state['revision']+1, updated_at=stamp(datetime.now(UTC)).isoformat(),
                 parent_sha256=parent_hash)
    write(root/learning.STATE_FILE, state)
    evaluation = learning.report(list(frozen.values()), outcomes, deliveries,
                                  list(attempts_by_id.values()), state, events, datetime.now(UTC))
    write(root/learning.REPORT_FILE, evaluation)
    for path in [ledger, root/'stock-forecast-outcomes.jsonl', root/'stock-forecast-deliveries.jsonl']:
        path.touch(exist_ok=True)
    counts=evaluation['evaluation_counts']; performance=evaluation['overall']
    summary={'recorded_predictions':len(frozen), 'matured_observations':len(prior_outcomes),
             'publicly_timely_observations':performance['samples'],
             'pending_or_unavailable':counts.get('pending_targets',0)+counts.get('outcome_missing',0),
             'live_accuracy':performance['accuracy'], 'accuracy_interval':performance['wilson_95_interval'],
             'independent_deduplicated':True, 'baseline_comparison':evaluation['baseline_paired'],
             'not_trade_returns':True, 'human_push_receipt_verified':False}
    artifact={'version':VERSION, 'generated_at':evaluation['generated_at'],
              'source_run_id':os.environ.get('GITHUB_RUN_ID'), 'policy':POLICY,
              'status':'research_only', 'real_time_connected':False,
              'refresh_mode':'scheduled_best_effort_not_realtime',
              'coverage':len(specs), 'counts':dict(Counter(r['status'] for r in ready)),
              'records':ready,'forward_evaluation':summary,
              'learning_evaluation':{'version':learning.VERSION,'training_updates':state['training_updates'],
                  'adaptive_groups':evaluation['learning']['adaptive_groups'],'report':learning.REPORT_FILE},
              'disclosures':['실제 과거 OHLC로 학습한 모델 추정치',
                  '공개 확인된 과거 예측을 채점한 뒤 새 예측에만 학습 반영',
                  '100% 적중·수익 보장 아님; strict-green 변경 없음',
                  '지연·누락·미래 타깃 종료 전에는 채점하지 않음'],
              'schedule_note':'정기 실행은 지연 가능. 실시간 연결과 사용자 푸시 수신은 미확인.'}
    write(root/'stock-direction-forecast.json',artifact)
    print(json.dumps({'counts':artifact['counts'],'scored':performance['samples'],
                      'correct':performance['correct'],'training_updates':state['training_updates'],
                      'promotions':evaluation['learning']['promotions']},ensure_ascii=False),flush=True)
    return artifact


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=len(DEFAULT))
    parser.add_argument('--mode', choices=['daily', 'intraday', 'both'], default='both')
    args = parser.parse_args()
    run(specs=DEFAULT[:args.limit], modes=('daily', 'intraday') if args.mode == 'both' else (args.mode,))
