"""Isolated one-recipe model experiment; never writes the production forecast ledger.
Historical diagnostics are not issued predictions or proof of future usefulness.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import stock_forecast_model as base
from stock_forecast_cascade import MovementThenDirection
from stock_forecast_directions import expanded_features, EXTRA, metrics

PIN = '9814e420317ba7a3506583b4370b3ea9184a2196'
RECIPE = {'name': 'recent_daily_logistic_v1', 'training_sessions': 756,
          'calibration_sessions': 60, 'minimum_training_rows': 500,
          'minimum_calibration_rows': 40, 'diagnostic_targets': 126,
          'refit_every_sessions': 21, 'C': .2, 'temperature_bounds': [.5, 5.],
          'features': list(base.FEATURES), 'mode': 'daily', 'shadow_only': True,
          'orders_enabled': False, 'automatic_promotion': False}
UTC = timezone.utc


def validate_samples(data):
    required = set(base.FEATURES) | {'origin', 'target_start', 'target_end', 'session', 'y', 'band'}
    if not required.issubset(data.columns) or data.empty:
        raise ValueError('recent_samples_missing')
    if not data.origin.is_monotonic_increasing or data.origin.duplicated().any() or data.session.duplicated().any():
        raise ValueError('recent_daily_origin_order')
    for col in ('origin', 'target_start', 'target_end'):
        if pd.DatetimeIndex(data[col]).tz is None:
            raise ValueError('recent_timezone_required')
    if not ((data.origin < data.target_start) & (data.target_start < data.target_end)).all():
        raise ValueError('recent_target_chronology')
    if not np.isfinite(data[base.FEATURES+['band']].to_numpy()).all() or (data.band <= 0).any():
        raise ValueError('recent_nonfinite_features_or_band')
    if not data.y.isin([0, 1, 2]).all():
        raise ValueError('recent_class_invalid')


def split_asof(data, origin):
    validate_samples(data)
    origin = base.stamp(origin)
    available = data[data.target_end < origin]
    days = sorted(available.session.unique())
    n = RECIPE['calibration_sessions']
    if len(days) < n + RECIPE['minimum_training_rows']:
        raise ValueError('recent_history_short')
    calibration = available[available.session.isin(days[-n:])].copy()
    training = available[available.session.isin(days[-n-RECIPE['training_sessions']:-n])].copy()
    training = training[training.target_end < calibration.origin.min()]
    calibration = calibration.iloc[base.nonoverlapping_positions(calibration)]
    if len(training) < RECIPE['minimum_training_rows'] or len(calibration) < RECIPE['minimum_calibration_rows']:
        raise ValueError('recent_purged_samples_short')
    if set(training.y) != {0, 1, 2} or len(set(calibration.y)) < 2:
        raise ValueError('recent_class_samples_short')
    if not training.target_end.max() < calibration.origin.min() or not calibration.target_end.max() < origin:
        raise ValueError('recent_split_overlap')
    return training, calibration


def fit_asof(data, origin):
    training, calibration = split_asof(data, origin)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=RECIPE['C'], max_iter=1000, solver='lbfgs'))
    model.fit(training[base.FEATURES], training.y)
    if list(model.classes_) != [0, 1, 2]:
        raise ValueError('recent_class_order')
    cp = model.predict_proba(calibration[base.FEATURES])
    result = minimize_scalar(lambda t: base.logloss(calibration.y.to_numpy(), base.temperature_scale(cp, t)),
                             bounds=tuple(RECIPE['temperature_bounds']), method='bounded')
    if not result.success or not np.isfinite(result.fun):
        raise ValueError('recent_calibration_failed')
    scaler, fitted = model.steps[0][1], model.steps[-1][1]
    metadata = {'recipe_sha256': base.digest(RECIPE), 'origin': base.stamp(origin).isoformat(),
                'training_rows': len(training), 'calibration_rows': len(calibration),
                'trained_through': training.target_end.max().isoformat(),
                'calibrated_through': calibration.target_end.max().isoformat(),
                'calibration_origin_start': calibration.origin.min().isoformat(),
                'training_session_start': training.session.min(),
                'temperature': float(result.x)}
    metadata['model_sha256'] = base.digest({'recipe': RECIPE, 'metadata': metadata,
         'coefficients': fitted.coef_.tolist(), 'intercept': fitted.intercept_.tolist(),
         'scaler_mean': scaler.mean_.tolist(), 'scaler_scale': scaler.scale_.tolist()})
    return model, metadata


def predict(model, metadata, x):
    values = x[base.FEATURES]
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError('recent_prediction_nonfinite')
    return base.temperature_scale(model.predict_proba(values), metadata['temperature'])


def cascade_reference(bars, data, incumbent):
    expanded = expanded_features(bars, 'daily')
    by_origin = expanded.set_axis(pd.DatetimeIndex(bars.end))
    source = data.copy()
    for name in EXTRA:
        source[name] = by_origin[name].reindex(pd.DatetimeIndex(source.origin)).to_numpy()
    cols = base.FEATURES + EXTRA
    train, calibration, _ = base.chronological_split(source)
    calibration = calibration.iloc[base.nonoverlapping_positions(calibration)]
    model = MovementThenDirection().fit(train[cols], train.y)
    cp = model.predict_proba(calibration[cols])
    temperature = float(minimize_scalar(lambda t: base.logloss(calibration.y.to_numpy(), base.temperature_scale(cp, t)),
                                         bounds=(.5, 5), method='bounded').x)
    return model, temperature, source, expanded


def diagnose(bars):
    if bars.attrs.get('mode') != 'daily':
        raise ValueError('recent_daily_only')
    data, x, bands = base.samples(bars, 'daily')
    validate_samples(data)
    incumbent = base.fit_model(bars, 'daily')
    _, _, original_test = base.chronological_split(data)
    wanted = RECIPE['diagnostic_targets']
    if len(original_test) < wanted:
        raise ValueError('recent_original_holdout_short')
    test = original_test.tail(wanted).copy()
    candidate_probabilities, folds = [], []
    for offset in range(0, wanted, RECIPE['refit_every_sessions']):
        block = test.iloc[offset:offset+RECIPE['refit_every_sessions']]
        model, metadata = fit_asof(data, block.origin.iloc[0])
        candidate_probabilities.extend(predict(model, metadata, block).tolist())
        folds.append({**metadata, 'diagnostic_first_target': block.target_start.iloc[0].isoformat(),
                      'diagnostic_last_target': block.target_end.iloc[-1].isoformat(), 'targets': len(block)})
    oldp = base.temperature_scale(incumbent['model'].predict_proba(test[base.FEATURES]), incumbent['temperature'])
    baselinep = np.repeat(incumbent['baseline'][None, :], len(test), axis=0)
    cascade, temperature, expanded_data, latest_expanded = cascade_reference(bars, data, incumbent)
    cols = base.FEATURES + EXTRA
    casc_p = base.temperature_scale(cascade.predict_proba(expanded_data.loc[test.index, cols]), temperature)
    probabilities = {'incumbent': oldp, 'frozen_training_frequency': baselinep,
                     'movement_then_direction': casc_p, 'recent_daily_logistic_v1': np.asarray(candidate_probabilities)}
    rows = [{'target_start': row.target_start.isoformat(), 'target_end': row.target_end.isoformat(),
             'origin_session': row.session, 'actual': base.CLASSES[int(row.y)],
             'neutral_band_pct': float(row.band)*100,
             'diagnostic_only_not_issued_forecast': True,
             'probabilities': {name: dict(zip(base.CLASSES, map(float, values[i]))) for name, values in probabilities.items()}}
             for i, row in enumerate(test.itertuples())]
    report = {'diagnostic': {name: metrics(test.y, values) for name, values in probabilities.items()},
              'folds': folds, 'diagnostic_rows': rows,
              'incumbent_trained_through': incumbent['trained_through'],
              'incumbent_calibrated_through': incumbent['calibrated_through'],
              'untouched_confirmation': False, 'history_is_point_in_time_vintage': False}
    model, meta = fit_asof(data, bars.end.iloc[-1])
    live_choices = {'recent_daily_logistic_v1': predict(model, meta, x.iloc[[-1]])[0],
                    'incumbent': base.temperature_scale(incumbent['model'].predict_proba(x.iloc[[-1]]), incumbent['temperature'])[0],
                    'movement_then_direction': base.temperature_scale(cascade.predict_proba(latest_expanded.iloc[[-1]][cols]), temperature)[0]}
    return report, meta, live_choices, float(bands.iloc[-1])*100


def process(spec):
    from run_stock_forecasts import collect
    symbol, name, market = spec
    bars, received = collect(spec, 'daily')
    report, metadata, choices, band = diagnose(bars)
    issued = datetime.now(UTC)
    if not base.stamp(bars.end.iloc[-1]) <= base.stamp(received) <= base.stamp(issued):
        raise ValueError('recent_forward_time_contract')
    target, reason = base.future_target(bars.iloc[-1], market, 'daily', issued)
    provenance = {'symbol': symbol, 'market': market, 'mode': 'daily', 'name': name,
                  'history_sha256': base.digest([{'start': r.start.isoformat(), 'end': r.end.isoformat(),
                      'open': r.open, 'high': r.high, 'low': r.low, 'close': r.close} for r in bars.itertuples()]),
                  'observed_until': bars.end.iloc[-1].isoformat(), 'received_at': received.isoformat(),
                  'source_commit': os.environ.get('GITHUB_SHA'), 'source_run_id': os.environ.get('GITHUB_RUN_ID')}
    p = choices['recent_daily_logistic_v1']
    shadow = {**provenance, **metadata, 'issued_at': issued.isoformat(),
              'candidate': RECIPE['name'], 'status': 'no_call' if reason else 'shadow_prediction',
              'target': None if reason else target, 'reason': reason,
              'probabilities': None if reason else dict(zip(base.CLASSES, map(float, p))),
              'direction': None if reason else base.CLASSES[int(p.argmax())],
              'neutral_band_pct': band,
              'contemporaneous_references': {} if reason else {k: dict(zip(base.CLASSES, map(float, v))) for k, v in choices.items() if k != RECIPE['name']},
              'public_before_target_verified': False, 'human_receipt_verified': False,
              'external_exchange_price_verified': False, 'recommendation': False,
              'strict_green_override': False, 'orders_enabled': False,
              'forward_scored': 0, 'timing_utility': 'not_proven'}
    shadow['id'] = base.digest(shadow)
    return {**provenance, **report, 'status': 'diagnostic_completed', 'fresh_shadow': shadow}


def aggregate(groups):
    rows = [dict(row, symbol=g['symbol'], market=g['market']) for g in groups if g['status']=='diagnostic_completed' for row in g['diagnostic_rows']]
    result = {'targets': len(rows), 'groups': sum(g['status']=='diagnostic_completed' for g in groups),
              'failed_groups': [g['symbol'] for g in groups if g['status']!='diagnostic_completed']}
    if not rows:
        result['status'] = 'no_real_comparison'; return result
    truth = np.array([base.CLASSES.index(r['actual']) for r in rows])
    scores = {name: metrics(truth, np.array([[r['probabilities'][name][k] for k in base.CLASSES] for r in rows])) for name in rows[0]['probabilities']}
    result['metrics'] = scores
    old, new = scores['incumbent'], scores[RECIPE['name']]
    conditions = {'accuracy_improved': new['accuracy'] > old['accuracy'],
                  'balanced_accuracy_improved': new['balanced_accuracy'] > old['balanced_accuracy'],
                  'up_recall_nonworse': new['directions']['up']['recall'] >= old['directions']['up']['recall'],
                  'down_recall_nonworse': new['directions']['down']['recall'] >= old['directions']['down']['recall'],
                  'brier_improved': new['brier_loss'] < old['brier_loss'],
                  'logloss_improved': new['log_loss'] < old['log_loss'],
                  'all_requested_groups_completed': not result['failed_groups']}
    result['historical_conditions'] = conditions
    result['historical_criteria_passed'] = all(conditions.values())
    daily = {}
    for r in rows:
        y = base.CLASSES.index(r['actual'])
        oldp = np.array([r['probabilities']['incumbent'][k] for k in base.CLASSES])
        newp = np.array([r['probabilities'][RECIPE['name']][k] for k in base.CLASSES])
        # Same target-date cluster includes US/KR and all symbols. Diagnostic only.
        daily.setdefault(r['target_start'][:10], []).append([float(newp.argmax()==y)-float(oldp.argmax()==y),
                                                          float(((oldp-np.eye(3)[y])**2).sum()-((newp-np.eye(3)[y])**2).sum())])
    means = np.array([np.mean(v, axis=0) for v in daily.values()])
    draws = np.random.default_rng(20261110).integers(0, len(means), size=(2000, len(means)))
    intervals = np.quantile(means[draws].mean(axis=1), [.025, .975], axis=0)
    result['date_equal_weight_diagnostic'] = {'dates': len(daily), 'accuracy_gain_interval': intervals[:,0].tolist(),
        'brier_gain_interval': intervals[:,1].tolist(), 'serial_dependence_not_resolved': True, 'not_promotion_evidence': True}
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True); args = parser.parse_args()
    root, output = Path.cwd().resolve(), Path(args.output).resolve()
    if output == root or root in output.parents:
        raise SystemExit('research_output_must_be_outside_repository')
    output.mkdir(parents=True, exist_ok=False)
    tracked = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
    before = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in tracked if Path(p).is_file()}
    from run_stock_forecasts import DEFAULT
    from stock_forecast_sources import prepare_sessions
    prepare_sessions()
    groups = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(process, spec): spec for spec in DEFAULT}
        for future in as_completed(futures):
            spec = futures[future]
            try: group = future.result()
            except Exception as exc: group = {'symbol': spec[0], 'market': spec[2], 'status': 'group_failed', 'error_type': type(exc).__name__, 'reason': str(exc).split('https:')[0][:160]}
            groups.append(group)
            (output/(spec[0].replace('^','INDEX_')+'.json')).write_text(json.dumps(group, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
            print('RECENT_GROUP', spec[0], group['status'], flush=True)
    groups.sort(key=lambda g:g['symbol'])
    changed = [p for p,h in before.items() if not Path(p).exists() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    if changed:
        raise RuntimeError('original_source_mutated:'+','.join(changed))
    report = {'version': 'recent-daily-experiment-1.0', 'generated_at': datetime.now(UTC).isoformat(),
              'pinned_main': PIN, 'code_commit': os.environ.get('GITHUB_SHA'), 'run_id': os.environ.get('GITHUB_RUN_ID'),
              'recipe': RECIPE, 'recipe_trials': 1, 'hyperparameter_search_trials': 0,
              'requested_groups': len(DEFAULT), 'comparison': aggregate(groups),
              'original_files_unchanged': len(before), 'original_scored_accuracy_changed': False,
              'new_forward_outcomes': 0, 'candidate_forward_accuracy': None,
              'automatic_promotion': False, 'timing_utility': 'not_proven',
              'history_is_point_in_time_vintage': False, 'orders_enabled': False,
              'groups': [{k:v for k,v in g.items() if k!='diagnostic_rows'} for g in groups]}
    (output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print('RECENT_DAILY_EXPERIMENT', json.dumps({k:v for k,v in report.items() if k!='groups'}, ensure_ascii=False), flush=True)
    if report['comparison']['failed_groups']:
        raise SystemExit('incomplete_source_groups_recorded_not_passed')


if __name__ == '__main__':
    main()
