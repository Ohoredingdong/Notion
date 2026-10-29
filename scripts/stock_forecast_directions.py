"""Direction-balanced challengers and per-direction forward promotion gates.

No target band changes, synthetic production data, retrospective approvals or orders.
New models are frozen alongside the incumbent and remain shadow until forward gates pass.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from stock_forecast_cascade import MovementThenDirection, RECIPE as CASCADE_RECIPE
import stock_forecast_model as base
import stock_forecast_learning as online

VERSION = 'direction-specialists-1.0'
SPECIALISTS = ('balanced_linear', 'balanced_nonlinear', 'movement_then_direction')
VARIANTS = ('adaptive',) + SPECIALISTS
CLASSES = base.CLASSES
POLICY = {
    'minimum_paired_targets': 120, 'minimum_sessions': 20,
    'minimum_each_actual_class': 10, 'minimum_each_direction_call': 10,
    'minimum_direction_recall_gain': .03, 'minimum_balanced_accuracy_gain': .03,
    'minimum_precision_above_prevalence': .02,
    'minimum_brier_gain': .01, 'minimum_logloss_gain': .005,
    'rollback_targets': 40, 'rollback_sessions': 5,
    'three_challenger_interval_tail': .05/(2*len(VARIANTS)),
    'uncertain_max_probability': .50, 'uncertain_top_two_margin': .10,
    'target_bands_unchanged': True, 'orders_enabled': False,
    'guaranteed_accuracy': None, 'promotion_is_policy_not_proof': True,
}
EXTRA = ['acceleration', 'range_position20', 'session_drawdown',
         'session_rebound', 'from_session_open', 'elapsed_minutes',
         'up_body_in_downtrend', 'down_body_in_uptrend']


def metrics(y, p):
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    if p.shape != (len(y), 3) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('invalid_direction_probabilities')
    if not np.allclose(p.sum(axis=1), 1, atol=1e-7, rtol=0):
        raise ValueError('probability_sum')
    if len(y) and not np.isin(y, [0, 1, 2]).all():
        raise ValueError('invalid_actual_direction')
    pred = p.argmax(axis=1) if len(y) else np.array([], dtype=int)
    cm = [[int(((y == i) & (pred == j)).sum()) for j in range(3)] for i in range(3)]
    result = {}
    for i, name in enumerate(CLASSES):
        actual, called, tp = int((y == i).sum()), int((pred == i).sum()), cm[i][i]
        result[name] = {'actual': actual, 'calls': called, 'correct': tp,
                        'missed': actual-tp, 'false_calls': called-tp,
                        'recall': tp/actual if actual else None,
                        'precision': tp/called if called else None,
                        'prevalence': actual/len(y) if len(y) else None,
                        'f1': 2*tp/(actual+called) if actual+called else None}
    recalls = [result[k]['recall'] for k in CLASSES]
    onehot = np.eye(3)[y]
    return {'samples': len(y), 'correct': int((pred == y).sum()),
            'accuracy': float(np.mean(pred == y)) if len(y) else None,
            'balanced_accuracy': float(np.mean(recalls)) if all(v is not None for v in recalls) else None,
            'directions': result, 'confusion_matrix': cm,
            'brier_loss': float(np.mean(((p-onehot)**2).sum(axis=1))) if len(y) else None,
            'log_loss': base.logloss(y, p) if len(y) else None,
            'single_class_collapse': bool(len(y) and len(set(pred.tolist())) == 1),
            'collapsed_to': CLASSES[int(pred[0])] if len(y) and len(set(pred.tolist())) == 1 else None}


def expanded_features(bars, mode):
    """Cumulative session references only; future rows cannot change past features."""
    x, _ = base.features(bars, mode)
    c = bars.close
    high = bars.high.rolling(20, min_periods=20).max()
    low = bars.low.rolling(20, min_periods=20).min()
    span = (high-low).replace(0, np.nan)
    x['acceleration'] = x.r3-x.r12/4
    x['range_position20'] = ((c-low)/span).fillna(.5)
    g = bars.groupby('session', sort=False)
    x['session_drawdown'] = c/g.high.cummax()-1
    x['session_rebound'] = c/g.low.cummin()-1
    x['from_session_open'] = c/g.open.transform('first')-1
    x['elapsed_minutes'] = (bars.end-g.start.transform('first')).dt.total_seconds()/60
    x['up_body_in_downtrend'] = x.body.clip(lower=0)*(-x.ma20).clip(lower=0)
    x['down_body_in_uptrend'] = (-x.body).clip(lower=0)*x.ma20.clip(lower=0)
    return x.replace([np.inf, -np.inf], np.nan)


def fit(bars, mode, incumbent):
    """Fixed preregistered candidates; all fitting/calibration precedes untouched test.

Class balancing can worsen probability calibration; no candidate is promoted
on its historical scores. The existing target rows and neutral bands stay fixed.
"""
    data, _, _ = base.samples(bars, mode)
    x = expanded_features(bars, mode)
    at_origin = x.set_axis(pd.DatetimeIndex(bars.end))
    for name in EXTRA:
        data[name] = at_origin[name].reindex(pd.DatetimeIndex(data.origin)).to_numpy()
    columns = base.FEATURES + EXTRA
    if data[columns].isna().any(axis=None):
        raise ValueError('specialist_feature_missing')
    train, calibration, test = base.chronological_split(data)
    calibration = calibration.iloc[base.nonoverlapping_positions(calibration)]
    test = test.iloc[base.nonoverlapping_positions(test)]
    if len(calibration) < 40 or len(test) < 40:
        raise ValueError('specialist_independent_samples_short')
    if train.target_end.max() >= calibration.origin.min() or calibration.target_end.max() >= test.origin.min():
        raise ValueError('specialist_chronology_overlap')
    bp = base.temperature_scale(incumbent['model'].predict_proba(test[base.FEATURES]), incumbent['temperature'])
    reference = metrics(test.y, bp)
    model_specs = {
        'movement_then_direction': MovementThenDirection(),
        'balanced_linear': make_pipeline(StandardScaler(), LogisticRegression(
            C=.2, class_weight='balanced', max_iter=1000, solver='lbfgs')),
        'balanced_nonlinear': HistGradientBoostingClassifier(
            max_iter=80, max_leaf_nodes=7, max_depth=3, min_samples_leaf=30,
            l2_regularization=10., learning_rate=.05, early_stopping=False, random_state=29),
    }
    out = {'version': VERSION, 'status': 'shadow_only', 'history_is_live_proof': False,
           'features': columns, 'train_end': train.target_end.max().isoformat(),
           'calibration_end': calibration.target_end.max().isoformat(),
           'test_start': test.origin.min().isoformat(), 'test_end': test.target_end.max().isoformat(),
           'test_sessions': int(test.session.nunique()), 'reference': reference,
           'candidates': {}, 'errors': []}
    latest = x.iloc[[-1]][columns]
    if latest.isna().any(axis=None):
        raise ValueError('specialist_latest_features_missing')
    input_hash = base.digest({'version': VERSION, 'mode': mode,
                             'training': train[columns+['y']].to_numpy().tolist(),
                             'calibration': calibration[columns+['y']].to_numpy().tolist()})
    for name, model in model_specs.items():
        if name == 'balanced_nonlinear':
            model.fit(train[columns], train.y, sample_weight=compute_sample_weight('balanced', train.y))
        else:
            model.fit(train[columns], train.y)
        if list(model.classes_) != [0, 1, 2]:
            raise ValueError('specialist_class_order')
        cp = model.predict_proba(calibration[columns])
        temp = float(minimize_scalar(lambda t: base.logloss(calibration.y.to_numpy(), base.temperature_scale(cp, t)),
                                     bounds=(.5, 5), method='bounded').x)
        tp = base.temperature_scale(model.predict_proba(test[columns]), temp)
        p = base.temperature_scale(model.predict_proba(latest), temp)[0]
        report = metrics(test.y, tp)
        model_id = base.digest({'inputs': input_hash, 'name': name, 'temperature': temp,
                                'policy_version': VERSION,
                                'recipe': CASCADE_RECIPE if name == 'movement_then_direction' else name})
        out['candidates'][name] = {'model_sha256': model_id, 'probabilities': online.pdict(p),
                                  'direction': CLASSES[int(p.argmax())], 'temperature': temp,
                                  'validation': report, 'recommendation': False,
                                  'historical_test_used_for_promotion': False,
                                  'test_actual_counts': {k:report['directions'][k]['actual'] for k in CLASSES}}
    return out


def variants(record):
    v = record.get('online_learning') or {}
    result = {'incumbent': v.get('incumbent_probabilities', record.get('probabilities'))}
    if v.get('version') == online.VERSION and v.get('challenger_probabilities'):
        result['adaptive'] = v['challenger_probabilities']
    suite = record.get('directional_specialists') or {}
    if suite.get('version') == VERSION:
        for name in SPECIALISTS:
            value = (suite.get('candidates') or {}).get(name, {}).get('probabilities')
            if value is not None:
                result[name] = value
    return {k: online.probability(v) for k,v in result.items()}


def direction_guard(reference, candidate):
    reasons = []
    for name in CLASSES:
        if candidate['directions'][name]['actual'] < POLICY['minimum_each_actual_class']:
            reasons.append('insufficient_actual_'+name)
    for name in ('down', 'up'):
        d, old = candidate['directions'][name], reference['directions'][name]
        if d['calls'] < POLICY['minimum_each_direction_call']:
            reasons.append('insufficient_calls_'+name)
        if d['recall'] is None or old['recall'] is None or d['recall'] < old['recall']+POLICY['minimum_direction_recall_gain']:
            reasons.append('recall_not_improved_'+name)
        if d['precision'] is None or d['prevalence'] is None or d['precision'] < d['prevalence']+POLICY['minimum_precision_above_prevalence']:
            reasons.append('precision_below_base_rate_'+name)
    if candidate['single_class_collapse']:
        reasons.append('single_class_collapse')
    if candidate['balanced_accuracy'] is None or reference['balanced_accuracy'] is None or candidate['balanced_accuracy'] < reference['balanced_accuracy']+POLICY['minimum_balanced_accuracy_gain']:
        reasons.append('balanced_accuracy_not_improved')
    return sorted(set(reasons))


def compare(pool, candidate):
    truth = np.array([CLASSES.index(o['actual']) for r,o in pool])
    a = np.array([variants(r)['incumbent'] for r,o in pool])
    b = np.array([variants(r)[candidate] for r,o in pool])
    ref, alt = metrics(truth, a), metrics(truth, b)
    onehot = np.eye(3)[truth]
    diffs = ((a-onehot)**2).sum(axis=1)-((b-onehot)**2).sum(axis=1)
    dates = defaultdict(list)
    for (r,_), difference in zip(pool, diffs):
        dates[r['target']['start'][:10]].append(float(difference))
    ci = None
    if len(dates) >= 5:
        means = np.array([np.mean(v) for v in dates.values()])
        rng = np.random.default_rng(291031)
        draws = rng.choice(means, size=(2000, len(means)), replace=True).mean(axis=1)
        tail = POLICY['three_challenger_interval_tail']
        ci = np.quantile(draws, [tail, 1-tail]).tolist()
    return {'samples': len(pool), 'sessions': len(dates), 'reference': ref, 'candidate': alt,
            'brier_gain': ref['brier_loss']-alt['brier_loss'],
            'logloss_gain': ref['log_loss']-alt['log_loss'],
            'day_cluster_gain_interval': ci,
            'direction_blocks': direction_guard(ref, alt),
            'interval_is_diagnostic_not_sequential_proof': True}


def select_variants(state, pairs, now):
    """Both rise and fall must improve on the same published future events."""
    pools = defaultdict(list)
    for r,o in pairs:
        if not online.contract(r) or base.stamp(o['evaluated_at']) > base.stamp(now):
            continue
        try:
            choices = variants(r)
        except (ValueError, TypeError):
            continue
        if set(choices) == {'incumbent', *VARIANTS}:
            pools[online.group(r)].append((r,o))
    events = []
    for name, pool in pools.items():
        s = online.ensure(state, pool[0][0])
        active = s.get('directional_active', s.get('active','incumbent'))
        cursor = s.get('directional_checkpoint')
        rows = sorted((v for v in pool if not cursor or base.stamp(v[0]['target']['start']) >= base.stamp(cursor)),
                      key=lambda v:(v[0]['target']['start'], v[0]['id']))
        rollback = active != 'incumbent'
        need = POLICY['rollback_targets'] if rollback else POLICY['minimum_paired_targets']
        days = POLICY['rollback_sessions'] if rollback else POLICY['minimum_sessions']
        if len(rows) < need:
            continue
        n = need
        while n < len(rows) and len({r['target']['start'][:10] for r,_ in rows[:n]}) < days:
            n += 1
        block = rows[:n]
        if len({r['target']['start'][:10] for r,_ in block}) < days:
            continue
        checks = {k:compare(block,k) for k in ([active] if rollback else VARIANTS)}
        chosen, kind = active, 'directional_checkpoint_no_change'
        if rollback:
            c = checks[active]
            directional_regression = any(
                c['candidate']['directions'][k]['actual'] >= 10 and
                c['candidate']['directions'][k]['recall'] < c['reference']['directions'][k]['recall']-.15
                for k in ('down','up'))
            if (c['brier_gain'] < -.01 and c['logloss_gain'] < -.005) or directional_regression:
                chosen, kind = 'incumbent', 'directional_rollback'
                s['rollbacks'] += 1
        else:
            eligible = [(k,c) for k,c in checks.items() if not c['direction_blocks'] and
                        c['day_cluster_gain_interval'] and c['day_cluster_gain_interval'][0] > 0 and
                        c['brier_gain'] > POLICY['minimum_brier_gain'] and
                        c['logloss_gain'] > POLICY['minimum_logloss_gain']]
            if eligible:
                chosen = max(eligible, key=lambda v:v[1]['brier_gain'])[0]
                kind = 'directional_research_promotion'
                s['promotions'] += 1
        s['directional_active'] = chosen
        s['active'] = 'adaptive' if chosen == 'adaptive' else 'incumbent'
        s['directional_checkpoint'] = block[-1][0]['target']['end']
        s['gate_checks'] += 1
        e = {'kind':kind, 'version':VERSION, 'group':name, 'old':active, 'new':chosen,
             'evaluated_at':base.stamp(now).isoformat(), 'comparison':checks,
             'strict_green_override':False, 'orders_enabled':False}
        e['id'] = base.digest(e)
        events.append(e)
    return events


def apply_variant(record, state):
    if record.get('status') != 'research_prediction':
        return record
    r = deepcopy(record)
    s = online.ensure(state, r)
    choices = variants(r)
    requested = s.get('directional_active', s.get('active','incumbent'))
    active = requested if requested in choices else 'incumbent'
    p = choices[active]
    r['probabilities'] = online.pdict(p)
    r['direction'] = CLASSES[int(p.argmax())]
    r['directional_selection'] = {'version':VERSION, 'active':active,
        'fallback_reason':None if active == requested else 'active_specialist_unavailable',
        'orders_enabled':False, 'strict_green_override':False}
    ranked = sorted(p, reverse=True)
    r['directional_signal'] = {'uncertain': bool(ranked[0] < POLICY['uncertain_max_probability'] or
                                               ranked[0]-ranked[1] < POLICY['uncertain_top_two_margin']),
        'uncertainty_is_not_flat':True, 'all_original_predictions_still_scored':True,
        'thresholds_are_policy_not_success_probabilities':True}
    if active in SPECIALISTS:
        r['incumbent_historical_validation'] = r.get('validation',{})
        r['validation'] = {'validation_status':'specialist_forward_research_only', 'test_samples':0,
                           'test_sessions':0, 'above_baseline_in_this_holdout':False,
                           'accuracy':None,'baseline_accuracy':None,'live_validated':False}
    r['id'] = base.digest({'prior_id':r['id'],'selection':r['directional_selection'],
                           'specialists':r.get('directional_specialists'), 'issued':r['issued_at']})
    return r


def report(records, outcomes, deliveries, current, state, now):
    pairs, counts = online.joined(records, outcomes, deliveries, now)
    y = [CLASSES.index(o['actual']) for r,o in pairs]
    p = np.array([online.probability(r['probabilities']) for r,o in pairs]).reshape(-1,3)
    actual = metrics(y, p)
    complete = []
    for pair in pairs:
        try:
            if set(variants(pair[0])) == {'incumbent', *VARIANTS}:
                complete.append(pair)
        except (ValueError,TypeError):
            pass
    paired = {k:compare(complete,k) for k in VARIANTS} if complete else {}
    latest = []
    for r in current:
        suite = r.get('directional_specialists') or {}
        if suite.get('version') == VERSION:
            latest.append({'symbol':r['symbol'],'name':r.get('name'),'mode':r['mode'],
                           'reference':suite.get('reference'), 'candidates':suite.get('candidates'),
                           'test_sessions':suite.get('test_sessions'),
                           'historical_not_forward_proof':True})
    return {'version':VERSION,'policy':POLICY,'actual_direction_quality':actual,
            'paired_future_events':len(complete),'paired_candidate_comparisons':paired,
            'historical_models':latest,
            'active_specialist_groups':sum(s.get('directional_active') in SPECIALISTS for s in state['groups'].values()),
            'no_probability_or_target_backfill':True,'real_time_connected':False,
            'all_directions_proven':False,'guaranteed_accuracy':None}
