"""Prospective price-direction research. No broker orders or diligence overrides.

Train/calibration/test are disjoint chronological SESSION groups. Past evaluation
uses currently retrieved historical prices, not point-in-time vintage prices.
Probabilities are statistical estimates, never investment success probabilities.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

UTC = timezone.utc
VERSION = 'direction-forecast-1.0'
CLASSES = ['down', 'flat', 'up']
FEATURES = ['r1', 'r3', 'r6', 'r12', 'r20', 'vol20', 'ma5', 'ma20',
            'range', 'body', 'drawdown20', 'rebound20']
POLICY = {'daily_floor_pct': 0.30, 'intraday_floor_pct': 0.15,
          'volatility_band_factor': 0.35, 'intraday_gap_minutes': 5,
          'intraday_target_minutes': 30, 'minimum_sessions_intraday': 30,
          'minimum_daily_samples': 500, 'minimum_independent_test_samples': 40,
          'minimum_test_sessions': 6, 'logistic_C': 0.2,
          'research_only': True, 'live_order_enabled': False,
          'thresholds_are_unvalidated_policy': True}


def stamp(value):
    t = pd.Timestamp(value)
    if t.tzinfo is None:
        raise ValueError('timezone_required')
    return t.tz_convert('UTC')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@lru_cache(maxsize=20)
def calendar(market, year):
    import exchange_calendars as xc
    return xc.get_calendar({'KR': 'XKRX', 'US': 'XNYS'}[market],
                           start=f'{year-8}-01-01', end=f'{year+2}-12-31')


def normalise_history(frame, market, mode, received_at):
    """Only completed regular-session bars. Never mark a live daily bar closed."""
    received = stamp(received_at)
    cal = calendar(market, received.year)
    zone = 'Asia/Seoul' if market == 'KR' else 'America/New_York'
    rows = []
    for idx, row in frame.iterrows():
        t = pd.Timestamp(idx)
        if mode == 'intraday' and t.tzinfo is None:
            raise ValueError('intraday_timezone_missing')
        day = (t.tz_convert(zone) if t.tzinfo else t).date().isoformat()
        try:
            session = cal.date_to_session(day, direction='none')
            opened, closed = cal.session_open(session), cal.session_close(session)
        except (ValueError, KeyError):
            continue
        start = opened if mode == 'daily' else t.tz_convert('UTC')
        end = closed if mode == 'daily' else start + pd.Timedelta(minutes=5)
        if start < opened or end > closed or end > received-pd.Timedelta(seconds=5):
            continue
        values = {k: float(row[k.capitalize()]) for k in ['open', 'high', 'low', 'close']}
        if not all(np.isfinite(x) and x > 0 for x in values.values()):
            continue
        if (values['high'] < max(values['open'], values['close']) or
                values['low'] > min(values['open'], values['close'])):
            continue
        rows.append({**values, 'start': start, 'end': end, 'session': day})
    if not rows:
        raise ValueError('no_completed_regular_session_bars')
    data = pd.DataFrame(rows).sort_values('start').reset_index(drop=True)
    if data['start'].duplicated().any():
        raise ValueError('duplicate_bar_timestamp')
    return data


def features(bars, mode):
    """All feature values depend on row t and earlier only; no bfill or shift(-1)."""
    c = bars['close'].astype(float)
    f = pd.DataFrame(index=bars.index)
    for k in (1, 3, 6, 12, 20):
        f[f'r{k}'] = c.pct_change(k)
    f['vol20'] = c.pct_change().rolling(20, min_periods=20).std(ddof=0)
    for k in (5, 20):
        f[f'ma{k}'] = c/c.rolling(k, min_periods=k).mean()-1
    f['range'] = (bars['high']-bars['low'])/c
    f['body'] = (c-bars['open'])/bars['open']
    f['drawdown20'] = c/bars['high'].rolling(20, min_periods=20).max()-1
    f['rebound20'] = c/bars['low'].rolling(20, min_periods=20).min()-1
    floor = POLICY['daily_floor_pct'] if mode == 'daily' else POLICY['intraday_floor_pct']
    scale = 1 if mode == 'daily' else np.sqrt(6)
    band = np.maximum(floor/100, f['vol20']*scale*POLICY['volatility_band_factor'])
    return f[FEATURES].replace([np.inf, -np.inf], np.nan), band


def target_rows(bars, mode):
    """Intraday: one full 5m gap, then 6 bars (30m), without crossing a session."""
    first, last = (1, 1) if mode == 'daily' else (2, 7)
    future_open = bars['open'].shift(-first)
    future_close = bars['close'].shift(-last)
    valid = future_open.notna() & future_close.notna()
    if mode == 'intraday':
        for k in range(1, last+1):
            valid &= bars['session'].eq(bars['session'].shift(-k))
            valid &= (bars['start'].shift(-k)-bars['start']).eq(pd.Timedelta(minutes=5*k))
    return pd.DataFrame({'target_start': bars['start'].shift(-first),
                         'target_end': bars['end'].shift(-last),
                         'return': future_close/future_open-1,
                         'valid': valid})


def samples(bars, mode):
    x, band = features(bars, mode)
    target = target_rows(bars, mode)
    usable = x.notna().all(axis=1) & target['valid']
    # Unresolved extreme OHLC discontinuities are excluded, not treated as alpha.
    jumps = bars['close'].pct_change().abs().rolling(21, min_periods=1).max() > .40
    usable &= ~jumps
    y = np.where(target['return'] > band, 2, np.where(target['return'] < -band, 0, 1))
    selected = bars.index[usable]
    out = x.loc[selected].copy()
    out['y'] = y[usable]
    out['origin'] = bars.loc[selected, 'end']
    out['session'] = bars.loc[selected, 'session']
    out['target_start'] = target.loc[selected, 'target_start']
    out['target_end'] = target.loc[selected, 'target_end']
    out['return'] = target.loc[selected, 'return']
    out['band'] = band.loc[selected]
    return out.reset_index(drop=True), x, band


def chronological_split(data):
    sessions = sorted(data['session'].unique())
    a, b = int(len(sessions)*.60), int(len(sessions)*.80)
    if not 0 < a < b < len(sessions):
        raise ValueError('insufficient_session_splits')
    cal, test = data[data.session.isin(sessions[a:b])], data[data.session.isin(sessions[b:])]
    train = data[data.session.isin(sessions[:a])]
    # Purge labels that were not resolved BEFORE the following split begins.
    train = train[train.target_end < cal.origin.min()]
    cal = cal[cal.target_end < test.origin.min()]
    if len(train) < 150 or len(cal) < 40 or len(test) < 40:
        raise ValueError('insufficient_train_calibration_test')
    if set(train.y) != {0, 1, 2} or len(set(cal.y)) < 2:
        raise ValueError('insufficient_direction_classes')
    return train.copy(), cal.copy(), test.copy()


def temperature_scale(p, temperature):
    z = np.log(np.clip(np.asarray(p), 1e-9, 1))/temperature
    z -= z.max(axis=1, keepdims=True)
    q = np.exp(z)
    return q/q.sum(axis=1, keepdims=True)


def logloss(y, p):
    return float(-np.log(np.clip(p[np.arange(len(y)), np.asarray(y, dtype=int)], 1e-9, 1)).mean())


def nonoverlapping_positions(test):
    selected, last_end = [], None
    for i, row in enumerate(test.itertuples()):
        if last_end is None or row.target_start >= last_end:
            selected.append(i)
            last_end = row.target_end
    return np.array(selected, dtype=int)


def evaluate_model(y, p, baseline, test):
    picked = nonoverlapping_positions(test)
    t = test.iloc[picked]
    y, p = np.asarray(y)[picked], p[picked]
    q = np.repeat(baseline[None, :], len(y), axis=0)
    onehot = np.eye(3)[y]
    loss, bl = ((p-onehot)**2).sum(axis=1), ((q-onehot)**2).sum(axis=1)
    days = pd.DataFrame({'session': t.session.to_numpy(), 'edge': bl-loss}).groupby('session').edge.mean().to_numpy()
    rng = np.random.default_rng(11029)
    boot = rng.choice(days, size=(500, len(days)), replace=True).mean(axis=1)
    lower, upper = np.quantile(boot, [.025, .975]).tolist()
    prediction = p.argmax(axis=1)
    baseline_class = int(baseline.argmax())
    accuracy = float((prediction == y).mean())
    baseline_accuracy = float((y == baseline_class).mean())
    ece = 0.0
    for lo, hi in zip(np.arange(0, 1, .1), np.arange(.1, 1.1, .1)):
        mask = (p.max(axis=1) >= lo) & (p.max(axis=1) < hi+1e-12)
        if mask.any():
            ece += float(mask.mean()*abs(p[mask].max(axis=1).mean()-(prediction[mask] == y[mask]).mean()))
    enough = len(y) >= POLICY['minimum_independent_test_samples'] and len(days) >= POLICY['minimum_test_sessions']
    evidence = bool(enough and lower > 0 and accuracy > baseline_accuracy and logloss(y, p) < logloss(y, q))
    return {'test_samples': len(y), 'test_sessions': len(days),
            'accuracy': accuracy, 'baseline_accuracy': baseline_accuracy,
            'brier_loss': float(loss.mean()), 'baseline_brier_loss': float(bl.mean()),
            'log_loss': logloss(y, p), 'baseline_log_loss': logloss(y, q),
            'brier_improvement': float((bl-loss).mean()),
            'session_bootstrap_95pct_interval': [float(lower), float(upper)],
            'confidence_interval_limitation': 'Session-resampling diagnostic; not multiple-testing corrected or live-proven.',
            'calibration_ece': ece,
            'test_start': t.origin.min().isoformat(), 'test_end': t.target_end.max().isoformat(),
            'above_baseline_in_this_holdout': evidence,
            'validation_status': 'historical_edge_only' if evidence else 'no_reliable_edge',
            'live_success_rate': None, 'live_validated': False,
            'confusion_matrix': [[int(((y == i) & (prediction == j)).sum()) for j in range(3)] for i in range(3)]}


def fit_model(bars, mode):
    data, x, bands = samples(bars, mode)
    if mode == 'daily' and len(data) < POLICY['minimum_daily_samples']:
        raise ValueError('fewer_than_500_daily_training_samples')
    if mode == 'intraday' and data.session.nunique() < POLICY['minimum_sessions_intraday']:
        raise ValueError('fewer_than_30_intraday_sessions')
    train, cal, test = chronological_split(data)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=POLICY['logistic_C'], max_iter=1000, solver='lbfgs'))
    model.fit(train[FEATURES], train.y)
    cp = model.predict_proba(cal[FEATURES])
    temperature = float(minimize_scalar(lambda v: logloss(cal.y.to_numpy(), temperature_scale(cp, v)),
                                       bounds=(.5, 5), method='bounded').x)
    p = temperature_scale(model.predict_proba(test[FEATURES]), temperature)
    baseline = (np.bincount(train.y, minlength=3)+1)/(len(train)+3)
    metrics = evaluate_model(test.y.to_numpy(), p, baseline, test)
    scaler, logistic = model.steps[0][1], model.steps[-1][1]
    fingerprint = digest({'version': VERSION, 'coef': logistic.coef_.tolist(),
                          'intercept': logistic.intercept_.tolist(), 'mean': scaler.mean_.tolist(),
                          'scale': scaler.scale_.tolist(), 'temperature': temperature})
    return {'model': model, 'temperature': temperature, 'metrics': metrics,
            'features': x, 'bands': bands, 'baseline': baseline,
            'trained_through': train.target_end.max().isoformat(),
            'calibrated_through': cal.target_end.max().isoformat(),
            'training_samples': len(train), 'calibration_samples': len(cal),
            'model_sha256': fingerprint}


def future_target(last, market, mode, issued_at):
    issued = stamp(issued_at)
    cal = calendar(market, issued.year)
    current_session = cal.date_to_session(last['session'], direction='none')
    if mode == 'daily':
        next_session = cal.next_session(current_session)
        start, end = cal.session_open(next_session), cal.session_close(next_session)
    else:
        start = last['end'] + pd.Timedelta(minutes=5)
        end = start + pd.Timedelta(minutes=30)
        if end > cal.session_close(current_session):
            return None, 'insufficient_regular_session_time'
    if start <= issued + pd.Timedelta(seconds=20):
        return None, 'target_already_started_or_delivery_window_too_short'
    if mode == 'intraday' and issued-last['end'] > pd.Timedelta(minutes=5):
        return None, 'intraday_source_stale'
    return {'start': start.isoformat(), 'end': end.isoformat()}, None


def make_prediction(bars, fitted, symbol, market, mode, received_at, issued_at=None):
    issued = stamp(issued_at or datetime.now(UTC))
    received = stamp(received_at)
    last = bars.iloc[-1]
    base = {'symbol': symbol, 'market': market, 'mode': mode, 'version': VERSION,
            'issued_at': issued.isoformat(), 'received_at': received.isoformat(),
            'observed_until': last['end'].isoformat(), 'origin_session': last['session'],
            'model_sha256': fitted['model_sha256'], 'trained_through': fitted['trained_through'],
            'calibrated_through': fitted['calibrated_through'],
            'training_samples': fitted['training_samples'], 'calibration_samples': fitted['calibration_samples'],
            'validation': fitted['metrics'], 'recommendation': False, 'strict_green_override': False,
            'status': 'no_call', 'probabilities': None, 'direction': None,
            'delivery_verified': False, 'source_type': 'provider_historical_prices',
            'history_is_point_in_time_vintage': False,
            'limitations': ['가격 기반 연구 모델', '이벤트·수급·호가 미포함',
                           '재수집한 과거자료의 시간순 검증이며 실거래 성과 아님',
                           '실사 통과·상승수익 보장 아님']}
    target, reason = future_target(last, market, mode, issued)
    if received > issued or last['end'] > received:
        reason = 'future_input_timestamp'
    if (bars['close'].pct_change().tail(21).abs() > .40).any():
        reason = 'unresolved_price_discontinuity'
    if reason:
        return {**base, 'reason': reason, 'target': target}
    vals = fitted['features'].iloc[[-1]]
    if vals.isna().any(axis=None):
        return {**base, 'reason': 'latest_features_missing', 'target': target}
    prob = temperature_scale(fitted['model'].predict_proba(vals), fitted['temperature'])[0]
    band = float(fitted['bands'].iloc[-1])
    features_record = {key: float(vals.iloc[0][key]) for key in FEATURES}
    base.update(status='research_prediction', reason=None, target=target,
                probabilities={key: float(p) for key, p in zip(CLASSES, prob)},
                direction=CLASSES[int(np.argmax(prob))], neutral_band_pct=band*100,
                origin_reference_price=float(last['close']),
                target_price_basis='미래 target.start 시각의 정규장 봉 시가 → target.end 종가; 현재가 수익 예측 아님',
                feature_values=features_record,
                input_sha256=digest({'origin': last['end'].isoformat(), 'features': features_record,
                                     'received_at': received.isoformat()}))
    base['id'] = digest({'symbol': symbol, 'mode': mode, 'origin': base['observed_until'],
                         'target': target, 'model': base['model_sha256'], 'version': VERSION})
    return base


def score_prediction(record, bars, now, delivery_at=None):
    """Future observations can score only previously issued genuine predictions."""
    if record.get('status') != 'research_prediction':
        return None
    issued = stamp(record['issued_at'])
    start, end = stamp(record['target']['start']), stamp(record['target']['end'])
    current = stamp(now)
    if not (stamp(record['observed_until']) <= stamp(record['received_at']) <= issued < start < end):
        return {'id': record['id'], 'status': 'invalid_time_contract'}
    if current < end:
        return {'id': record['id'], 'status': 'pending'}
    first, final = bars[bars.start == start], bars[bars.end == end]
    if first.empty or final.empty:
        return {'id': record['id'], 'status': 'target_prices_missing'}
    opened, closed = float(first.iloc[0]['open']), float(final.iloc[-1]['close'])
    ret = closed/opened-1
    band = record['neutral_band_pct']/100
    actual = 'up' if ret > band else 'down' if ret < -band else 'flat'
    p = np.array([record['probabilities'][key] for key in CLASSES])
    if not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1):
        return {'id': record['id'], 'status': 'invalid_probabilities'}
    delivered = stamp(delivery_at) if delivery_at else None
    return {'id': record['id'], 'symbol': record['symbol'], 'mode': record['mode'],
            'status': 'observed', 'issued_at': record['issued_at'], 'evaluated_at': current.isoformat(),
            'target': record['target'], 'target_open': opened, 'target_close': closed,
            'return_pct': ret*100, 'actual': actual, 'predicted': record['direction'],
            'correct': record['direction'] == actual,
            'brier_loss': float(((p-np.eye(3)[CLASSES.index(actual)])**2).sum()),
            'public_before_target_verified': bool(delivered is not None and issued <= delivered < start),
            'delivery_verified_at': delivered.isoformat() if delivered is not None else None,
            'price_observation_not_execution_return': True}
