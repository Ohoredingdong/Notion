"""Read-only independent arithmetic/timing audit; never trains or changes forecasts.
An internally consistent outcome is NOT independent verification of exchange prices.
"""
from __future__ import annotations
import argparse
import hashlib
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import unittest

CLASSES = ('down', 'flat', 'up')

def ts(value):
    d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('timezone_required')
    return d.astimezone(timezone.utc)

def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('finite_number_required')
    return float(value)

def classify(change_pct, band_pct):
    change, band = finite(change_pct), finite(band_pct)
    if band < 0:
        raise ValueError('negative_band')
    return 'up' if change > band else 'down' if change < -band else 'flat'

def audit_digest(value):
    # Canonical schema fingerprint, recomputed independently of model output.
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8')).hexdigest()

def event_key(r):
    return (r['symbol'], r['market'], r['mode'], r['target']['start'], r['target']['end'])

def validate(r):
    p = [finite(r['probabilities'][k]) for k in CLASSES]
    if any(x < 0 or x > 1 for x in p) or abs(sum(p)-1) > 1e-6:
        raise ValueError('invalid_probabilities')
    if r['direction'] not in CLASSES or abs(p[CLASSES.index(r['direction'])]-max(p)) > 1e-12:
        raise ValueError('direction_not_maximum_probability')
    # Independently validate frozen research-only challengers as evidence,
    # without promoting them or rescoring any historical outcome.
    specialists = r.get('directional_specialists')
    if specialists is not None:
        if not isinstance(specialists, dict):
            raise ValueError('invalid_shadow_candidate_structure')
        candidates = specialists.get('candidates', {})
        if not isinstance(candidates, dict):
            raise ValueError('invalid_shadow_candidate_structure')
        for candidate_name, candidate in candidates.items():
            if not isinstance(candidate_name, str) or not isinstance(candidate, dict):
                raise ValueError('invalid_shadow_candidate_structure')
            distribution = candidate.get('probabilities')
            if not isinstance(distribution, dict):
                raise ValueError('invalid_shadow_candidate_structure')
            cp = [finite(distribution[k]) for k in CLASSES]
            if any(x < 0 or x > 1 for x in cp) or abs(sum(cp)-1) > 1e-6:
                raise ValueError('invalid_shadow_probabilities')
            direction = candidate.get('direction')
            if direction not in CLASSES or abs(cp[CLASSES.index(direction)]-max(cp)) > 1e-12:
                raise ValueError('shadow_direction_not_maximum_probability')

    # Online-learning metadata freezes the incumbent/adaptive probabilities and
    # the first issuance ID. The specialist selector, when present, wraps that
    # ID into a second immutable ID and may choose a preregistered shadow model.
    # Older records without online_learning retain their historical audit path.
    online = r.get('online_learning')
    if online is not None:
        if not isinstance(online, dict) or online.get('version') != 'delayed-forward-learning-1.0':
            raise ValueError('invalid_online_learning_structure')
        if online.get('trading_enabled') is not False:
            raise ValueError('invalid_online_learning_structure')
        base_variant = online.get('active_variant')
        if base_variant not in ('incumbent', 'adaptive'):
            raise ValueError('unknown_online_variant')
        choices = {}
        for variant, name in (('incumbent', 'incumbent_probabilities'),
                              ('adaptive', 'challenger_probabilities')):
            distribution = online.get(name)
            if not isinstance(distribution, dict) or set(distribution) != set(CLASSES):
                raise ValueError('invalid_online_distribution')
            values = [finite(distribution[k]) for k in CLASSES]
            if any(x < 0 or x > 1 for x in values) or abs(sum(values)-1) > 1e-6:
                raise ValueError('invalid_online_distribution')
            choices[variant] = values
        prior_id = audit_digest({
            'event': audit_digest({k: r[k] for k in
                                   ('symbol', 'market', 'mode', 'target')}),
            'policy': r.get('policy_revision'),
            'base_model': r['model_sha256'],
            'online': online})
        selector = r.get('directional_selection')
        if selector is None:
            chosen = base_variant
            expected_id = prior_id
        else:
            if not isinstance(selector, dict) or selector.get('version') != 'direction-specialists-1.0':
                raise ValueError('invalid_directional_selector')
            if selector.get('orders_enabled') is not False or selector.get('strict_green_override') is not False:
                raise ValueError('invalid_directional_selector')
            chosen = selector.get('active')
            if chosen not in ('incumbent', 'adaptive', 'balanced_linear',
                              'balanced_nonlinear', 'movement_then_direction'):
                raise ValueError('unknown_directional_selector_variant')
            if chosen not in choices:
                suites = r.get('directional_specialists')
                candidate = (suites.get('candidates', {}).get(chosen)
                             if isinstance(suites, dict) else None)
                if not isinstance(candidate, dict):
                    raise ValueError('selected_directional_candidate_missing')
                distribution = candidate.get('probabilities')
                if not isinstance(distribution, dict) or set(distribution) != set(CLASSES):
                    raise ValueError('invalid_online_distribution')
                values = [finite(distribution[k]) for k in CLASSES]
                if any(x < 0 or x > 1 for x in values) or abs(sum(values)-1) > 1e-6:
                    raise ValueError('invalid_online_distribution')
                choices[chosen] = values
            expected_id = audit_digest({
                'prior_id': prior_id, 'selection': selector,
                'specialists': r.get('directional_specialists'),
                'issued': r['issued_at']})
        if any(abs(expected-actual) > 1e-12
               for expected, actual in zip(choices[chosen], p)):
            raise ValueError('online_frozen_probabilities_mismatch')
        if r.get('id') != expected_id:
            raise ValueError('online_issuance_id_mismatch')

    if not (ts(r['observed_until']) <= ts(r['received_at']) <= ts(r['issued_at']) <
            ts(r['target']['start']) < ts(r['target']['end'])):
        raise ValueError('nonprospective_timing')
    if r['mode'] == 'intraday' and (ts(r['target']['end'])-ts(r['target']['start'])).total_seconds() != 1800:
        raise ValueError('intraday_target_not_30_minutes')
    for field in ('trained_through', 'calibrated_through'):
        if r.get(field) and ts(r[field]) > ts(r['issued_at']):
            raise ValueError('future_training_label')
    classify(0.0, r['neutral_band_pct'])

def audit(records, outcomes, deliveries, cutoff):
    counts = Counter(); errors = []; by_id = {}; originals = {}
    for r in records:
        if r.get('status') != 'research_prediction':
            continue
        try:
            validate(r)
            if r['id'] in by_id and by_id[r['id']] != r:
                raise ValueError('conflicting_prediction_id')
            by_id[r['id']] = r
            key = event_key(r)
            old = originals.get(key)
            if old is not None:
                counts['duplicate_issuances'] += 1
            if old is None or ts(r['issued_at']) < ts(old['issued_at']):
                originals[key] = r
        except (KeyError, ValueError, TypeError) as exc:
            errors.append({'id': r.get('id'), 'error': str(exc)})
    public = {}
    valid_public_times = []  # verified snapshots, distinct from first public time per forecast
    for d in deliveries:
        if d.get('status') != 'public_verified':
            continue
        # Public verification cannot predate the snapshot nor prove a forecast
        # that did not yet exist when that snapshot was generated.
        try:
            seen = ts(d['verified_at'])
            snapshot = ts(d['snapshot_generated_at'])
        except (KeyError, ValueError, TypeError):
            errors.append({'id': d.get('verification_id'), 'error': 'invalid_public_snapshot_timestamp'})
            continue
        if snapshot > seen:
            errors.append({'id': d.get('verification_id'), 'error': 'snapshot_generated_after_verification'})
            continue
        at_least_one_valid_id = False
        for rid in d.get('prediction_ids', []):
            forecast = by_id.get(rid)
            if forecast is None:
                errors.append({'id': rid, 'error': 'public_snapshot_unknown_prediction_id'})
                continue
            if ts(forecast['issued_at']) > snapshot:
                errors.append({'id': rid, 'error': 'prediction_issued_after_public_snapshot'})
                continue
            at_least_one_valid_id = True
            if rid not in public or seen < public[rid]:
                public[rid] = seen
        if at_least_one_valid_id and seen <= cutoff:
            valid_public_times.append(seen)
    actuals = {}
    for o in outcomes:
        if o.get('status') != 'observed':
            continue
        if o['id'] in actuals and o != actuals[o['id']]:
            errors.append({'id': o['id'], 'error': 'conflicting_outcome_id'})
            continue
        actuals.setdefault(o['id'], o)
    # Validate every stored observed result, including events excluded for
    # overlapping targets or non-timely publication. Scoring stays separate.
    verified_outcomes = {}
    for o in actuals.values():
        r = by_id.get(o['id'])
        if r is None:
            errors.append({'id': o['id'], 'error': 'outcome_unknown_prediction_id'})
            continue
        try:
            if o['target'] != r['target'] or o['symbol'] != r['symbol'] or o['mode'] != r['mode']:
                raise ValueError('outcome_target_mismatch')
            if not ts(r['target']['end']) <= ts(o['evaluated_at']) <= cutoff:
                raise ValueError('outcome_timestamp_not_eligible')
            opening, closing = finite(o['target_open']), finite(o['target_close'])
            if min(opening, closing) <= 0:
                raise ValueError('nonpositive_price')
            change = 100*(closing/opening-1)
            label = classify(change, r['neutral_band_pct'])
            correct = label == r['direction']
            loss = sum((finite(r['probabilities'][k])-(k == label))**2 for k in CLASSES)
            if abs(finite(o['return_pct'])-change) > 1e-8 or o['actual'] != label:
                raise ValueError('stored_return_or_label_wrong')
            if o['predicted'] != r['direction'] or o['correct'] is not correct:
                raise ValueError('stored_score_wrong')
            if abs(finite(o['brier_loss'])-loss) > 1e-8:
                raise ValueError('stored_brier_wrong')
            verified_outcomes[o['id']] = (opening, closing, change, label, correct, loss)
        except (KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
            errors.append({'id': o.get('id'), 'error': str(exc)})
    rows = []; last_end = {}
    # Selection is chronological and independent of the observed correctness.
    for r in sorted(originals.values(), key=lambda x: (event_key(x)[:3], ts(x['target']['start']), ts(x['issued_at']))):
        group = event_key(r)[:3]; start = ts(r['target']['start']); end = ts(r['target']['end'])
        if group in last_end and start < last_end[group]:
            counts['overlap_excluded'] += 1; continue
        last_end[group] = end
        counts['nonoverlapping_targets'] += 1
        if end > cutoff:
            counts['pending_targets'] += 1; continue
        seen = public.get(r['id'])
        if seen is None or not ts(r['issued_at']) <= seen < start:
            counts['public_not_timely'] += 1; continue
        o = actuals.get(r['id'])
        if o is None:
            counts['missing_outcomes'] += 1; continue
        if r['id'] not in verified_outcomes:
            continue  # An invalid stored outcome never contributes to performance.
        opening, closing, change, label, correct, loss = verified_outcomes[r['id']]
        rows.append({'id': r['id'], 'symbol': r['symbol'], 'name': r.get('name', r['symbol']),
                         'issued_at': r['issued_at'], 'public_at': seen.isoformat(),
                         'target': r['target'], 'opening': opening, 'closing': closing,
                         'change_pct': change, 'band_pct': r['neutral_band_pct'],
                         'predicted': r['direction'], 'actual': label, 'correct': correct,
                         'brier_loss': loss,
                         'frozen_baseline_available': 'frozen_baseline_probabilities' in r})
    n = len(rows); correct = sum(r['correct'] for r in rows)
    direction = {}
    for c in CLASSES:
        actual = sum(r['actual'] == c for r in rows)
        calls = sum(r['predicted'] == c for r in rows)
        hits = sum(r['actual'] == c and r['predicted'] == c for r in rows)
        direction[c] = {'actual': actual, 'calls': calls, 'hits': hits, 'missed': actual-hits,
                        'false_calls': calls-hits, 'recall': hits/actual if actual else None,
                        'precision': hits/calls if calls else None}
    # This is evidence age only. Neither exchange-session freshness nor human
    # notification delivery can be certified from this repository snapshot.
    def newest(field):
        values = [ts(r[field]) for r in by_id.values() if r.get(field) and ts(r[field]) <= cutoff]
        return max(values).isoformat() if values else None
    last_public = max(valid_public_times) if valid_public_times else None
    freshness = {
        'last_observed_until': newest('observed_until'),
        'last_received_at': newest('received_at'),
        'last_issued_at': newest('issued_at'),
        'last_public_verified_at': last_public.isoformat() if last_public else None,
        'public_age_minutes': (cutoff-last_public).total_seconds()/60 if last_public else None,
        'exchange_session_freshness_verified': False,
        'human_delivery_verified': False,
        'scope': 'Ages of immutable repository evidence; not live quote/session/receipt validation.'
    }
    return {'version': 'independent-forecast-audit-1.0', 'audit_cutoff': cutoff.isoformat(),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'integrity_errors' if errors else 'ledger_arithmetic_consistent',
            'prediction_rows': len(records), 'unique_events': len(originals), 'counts': dict(counts),
            'outcome_rows_seen': len(actuals), 'outcome_rows_verified': len(verified_outcomes),
            'scored': n, 'correct': correct, 'accuracy': correct/n if n else None,
            'directions': direction, 'rows': rows, 'errors': errors,
            'retrospective_constant_flat_accuracy': sum(r['actual'] == 'flat' for r in rows)/n if n else None,
            'constant_flat_is_diagnostic_not_preregistered_benchmark': True,
            'externally_verified_candles': False, 'human_push_delivery_verified': False,
            'proven_predictive_edge': False, 'perfect_future_prediction_proven': False,
            'scope': 'Recomputes stored open/close arithmetic and timing; does not verify raw exchange candles or execution.',
            'freshness_evidence': freshness}

def read_lines(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

class SelfTests(unittest.TestCase):
    def test_bands_fixed(self):
        self.assertEqual(classify(-.3, .3), 'flat')
        self.assertEqual(classify(.3, .3), 'flat')
        self.assertEqual(classify(-.3001, .3), 'down')
        self.assertEqual(classify(.3001, .3), 'up')
    def test_bad_numbers(self):
        for x in (float('nan'), float('inf'), True, '1'):
            with self.assertRaises(ValueError): finite(x)
        with self.assertRaises(ValueError): classify(0, -.1)
    def test_timezone_required(self):
        with self.assertRaises(ValueError): ts('2026-10-29T10:00:00')
    def test_empty_does_not_claim_perfection(self):
        result = audit([], [], [], ts('2026-10-29T10:00:00Z'))
        self.assertIsNone(result['accuracy'])
        self.assertFalse(result['perfect_future_prediction_proven'])
    def test_first_issue_and_timing(self):
        base = {'id': 'test-only', 'symbol': 'TEST', 'market': 'US', 'mode': 'intraday',
                'status': 'research_prediction', 'observed_until': '2026-10-29T13:35:00Z',
                'received_at': '2026-10-29T13:35:10Z', 'issued_at': '2026-10-29T13:36:00Z',
                'target': {'start': '2026-10-29T14:00:00Z', 'end': '2026-10-29T14:30:00Z'},
                'probabilities': {'down': .2, 'flat': .6, 'up': .2}, 'direction': 'flat', 'neutral_band_pct': .3}
        validate(base)
        with self.assertRaises(ValueError): validate({**base, 'issued_at': '2026-10-29T14:01:00Z'})
        o = {'id': 'test-only', 'symbol': 'TEST', 'mode': 'intraday', 'status': 'observed',
             'target': base['target'], 'evaluated_at': '2026-10-29T14:31:00Z', 'target_open': 100.,
             'target_close': 99., 'return_pct': -1., 'actual': 'down', 'predicted': 'flat',
             'correct': False, 'brier_loss': 1.04}
        d = {'status': 'public_verified', 'snapshot_generated_at': '2026-10-29T13:36:30Z',
             'verified_at': '2026-10-29T13:37:00Z', 'prediction_ids': ['test-only']}
        now = ts('2026-10-29T15:00:00Z')
        good = audit([base], [o], [d], now)
        self.assertEqual(good['scored'], 1); self.assertEqual(good['correct'], 0)
        self.assertEqual(audit([base], [{**o, 'correct': True}], [d], now)['status'], 'integrity_errors')
        self.assertEqual(audit([base], [o], [{**d, 'verified_at': '2026-10-29T14:01:00Z'}], now)['scored'], 0)
        later = {**base, 'id': 'later', 'issued_at': '2026-10-29T13:38:00Z'}
        duplicate = audit([later, base], [o], [d], now)
        self.assertEqual(duplicate['scored'], 1); self.assertEqual(duplicate['rows'][0]['id'], 'test-only')
        overlapping = {**base, 'id': 'overlap', 'target': {'start': '2026-10-29T14:05:00Z', 'end': '2026-10-29T14:35:00Z'}}
        self.assertEqual(audit([base, overlapping], [o], [d], now)['counts']['overlap_excluded'], 1)


    def test_corrupt_overlapping_outcome_is_an_integrity_error(self):
        # Synthetic data only. Overlap exclusion cannot hide a malformed outcome.
        first = {'id': 'synthetic-first', 'symbol': 'TEST', 'market': 'US',
                 'mode': 'intraday', 'status': 'research_prediction',
                 'observed_until': '2026-10-29T13:30:00Z',
                 'received_at': '2026-10-29T13:31:00Z',
                 'issued_at': '2026-10-29T13:36:00Z',
                 'target': {'start': '2026-10-29T14:00:00Z',
                            'end': '2026-10-29T14:30:00Z'},
                 'probabilities': {'down': .2, 'flat': .6, 'up': .2},
                 'direction': 'flat', 'neutral_band_pct': .3}
        second = {**first, 'id': 'synthetic-overlap',
                  'target': {'start': '2026-10-29T14:05:00Z',
                             'end': '2026-10-29T14:35:00Z'}}
        first_outcome = {'id': first['id'], 'symbol': 'TEST', 'mode': 'intraday',
                         'status': 'observed', 'target': first['target'],
                         'evaluated_at': '2026-10-29T14:40:00Z',
                         'target_open': 100., 'target_close': 99.,
                         'return_pct': -1., 'actual': 'down', 'predicted': 'flat',
                         'correct': False, 'brier_loss': 1.04}
        # Fabrication: the source prices imply UP, not the frozen DOWN label.
        bad_overlap = {**first_outcome, 'id': second['id'],
                       'target': second['target'], 'target_close': 101.}
        publication = {'status': 'public_verified',
                       'snapshot_generated_at': '2026-10-29T13:37:00Z',
                       'verified_at': '2026-10-29T13:38:00Z',
                       'prediction_ids': [first['id'], second['id']]}
        cutoff = ts('2026-10-29T15:00:00Z')
        good = audit([first, second], [first_outcome, {**bad_overlap,
            'target_close': 99.}], [publication], cutoff)
        self.assertEqual(good['scored'], 1)
        self.assertEqual(good['counts']['overlap_excluded'], 1)
        self.assertEqual(good['status'], 'ledger_arithmetic_consistent')
        bad = audit([first, second], [first_outcome, bad_overlap],
                    [publication], cutoff)
        self.assertEqual(bad['scored'], 1)
        self.assertEqual(bad['status'], 'integrity_errors')
        self.assertTrue(any(e.get('id') == second['id'] for e in bad['errors']))

    def test_latest_evidence_timestamp_never_claims_trading_freshness(self):
        # Synthetic-only red/green test: a past verified snapshot can be old
        # even if all immutable prediction/outcome arithmetic is valid.
        row = {'id':'synthetic-freshness', 'symbol':'TEST', 'market':'US',
               'mode':'intraday', 'status':'research_prediction',
               'observed_until':'2026-10-29T13:30:00Z',
               'received_at':'2026-10-29T13:31:00Z',
               'issued_at':'2026-10-29T13:36:00Z',
               'target':{'start':'2026-10-29T14:00:00Z',
                         'end':'2026-10-29T14:30:00Z'},
               'probabilities':{'down':.2,'flat':.6,'up':.2},
               'direction':'flat','neutral_band_pct':.3}
        delivery = {'status':'public_verified',
                    'snapshot_generated_at':'2026-10-29T13:36:20Z',
                    'verified_at':'2026-10-29T13:36:25Z',
                    'prediction_ids':[row['id']]}
        result = audit([row], [], [delivery], ts('2026-10-29T16:13:11Z'))
        self.assertEqual(result['status'], 'ledger_arithmetic_consistent')
        meta = result['freshness_evidence']
        self.assertEqual(meta['last_observed_until'], '2026-10-29T13:30:00+00:00')
        self.assertEqual(meta['last_received_at'], '2026-10-29T13:31:00+00:00')
        self.assertEqual(meta['last_issued_at'], '2026-10-29T13:36:00+00:00')
        self.assertEqual(meta['last_public_verified_at'], '2026-10-29T13:36:25+00:00')
        self.assertGreater(meta['public_age_minutes'], 150)
        self.assertFalse(meta['exchange_session_freshness_verified'])
        self.assertFalse(meta['human_delivery_verified'])

    def test_shadow_candidate_probability_corruption_must_be_reported(self):
        # Synthetic-only red/green test. No real predictions or outcomes are changed.
        record = {'id': 'synthetic-shadow', 'symbol': 'TEST', 'market': 'US',
                  'mode': 'intraday', 'status': 'research_prediction',
                  'observed_until': '2026-10-29T13:30:00Z',
                  'received_at': '2026-10-29T13:31:00Z',
                  'issued_at': '2026-10-29T13:36:00Z',
                  'target': {'start': '2026-10-29T14:00:00Z',
                             'end': '2026-10-29T14:30:00Z'},
                  'probabilities': {'down': .2, 'flat': .6, 'up': .2},
                  'direction': 'flat', 'neutral_band_pct': .3}
        cutoff = ts('2026-10-29T15:00:00Z')
        good = {**record, 'directional_specialists': {
            'status': 'shadow_only',
            'candidates': {'movement_then_direction': {
                'probabilities': {'down': .5, 'flat': .2, 'up': .3},
                'direction': 'down'}}}}
        self.assertEqual(audit([good], [], [], cutoff)['status'],
                         'ledger_arithmetic_consistent')
        bad_probability = {**good, 'directional_specialists': {
            'status': 'shadow_only',
            'candidates': {'movement_then_direction': {
                'probabilities': {'down': 1.1, 'flat': -.1, 'up': 0.0},
                'direction': 'down'}}}}
        self.assertEqual(audit([bad_probability], [], [], cutoff)['status'],
                         'integrity_errors')
        bad_direction = {**good, 'directional_specialists': {
            'status': 'shadow_only',
            'candidates': {'movement_then_direction': {
                'probabilities': {'down': .5, 'flat': .2, 'up': .3},
                'direction': 'up'}}}}
        self.assertEqual(audit([bad_direction], [], [], cutoff)['status'],
                         'integrity_errors')

    def test_frozen_online_issuance_binding_is_fail_closed(self):
        # Synthetic fixture, not a historical quote or model candidate trial.
        row = {'symbol': 'TEST', 'market': 'US', 'mode': 'intraday',
               'status': 'research_prediction',
               'observed_until': '2026-10-29T13:30:00Z',
               'received_at': '2026-10-29T13:31:00Z',
               'issued_at': '2026-10-29T13:36:00Z',
               'target': {'start': '2026-10-29T14:00:00Z',
                          'end': '2026-10-29T14:30:00Z'},
               'policy_revision': 'provider-latency-30m-v1',
               'model_sha256': 'b'*64, 'neutral_band_pct': .3,
               'probabilities': {'down': .2, 'flat': .6, 'up': .2},
               'direction': 'flat',
               'online_learning': {
                   'version': 'delayed-forward-learning-1.0',
                   'active_variant': 'incumbent',
                   'learned_before_issuance': 0,
                   'weights_sha256': 'a'*64,
                   'label_available_through': None,
                   'incumbent_probabilities': {'down': .2, 'flat': .6, 'up': .2},
                   'challenger_probabilities': {'down': .3, 'flat': .4, 'up': .3},
                   'challenger_calibration': 'not_yet_forward_validated',
                   'trading_enabled': False}}
        def frozen_hash(value):
            return hashlib.sha256(json.dumps(
                value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                separators=(',', ':')).encode('utf-8')).hexdigest()
        row['id'] = frozen_hash({
            'event': frozen_hash({k: row[k] for k in
                                  ('symbol','market','mode','target')}),
            'policy': row['policy_revision'],
            'base_model': row['model_sha256'],
            'online': row['online_learning']})
        validate(row)
        # Both below pass the old auditor: a forged primary probability/direction
        # and a forged issuance ID can appear internally valid without binding.
        changed = {**row, 'probabilities': {'down': .7, 'flat': .2, 'up': .1},
                   'direction': 'down'}
        with self.assertRaisesRegex(ValueError, 'online_frozen_probabilities_mismatch'):
            validate(changed)
        with self.assertRaisesRegex(ValueError, 'online_issuance_id_mismatch'):
            validate({**row, 'id': '0'*64})
        malformed = {**row, 'online_learning': {**row['online_learning'],
                     'challenger_probabilities': {'down': 1.1, 'flat': -.1, 'up': 0.}}}
        with self.assertRaisesRegex(ValueError, 'invalid_online_distribution'):
            validate(malformed)

    def test_wrapped_specialist_issuance_binding(self):
        # Post-recipe synthetic reference: second-stage selection wraps prior ID.
        row = {'symbol': 'TEST', 'market': 'US', 'mode': 'intraday',
               'status': 'research_prediction',
               'observed_until':'2026-10-29T13:30:00Z',
               'received_at':'2026-10-29T13:31:00Z',
               'issued_at':'2026-10-29T13:36:00Z',
               'target':{'start':'2026-10-29T14:00:00Z',
                         'end':'2026-10-29T14:30:00Z'},
               'policy_revision':'provider-latency-30m-v1',
               'model_sha256':'f'*64, 'neutral_band_pct':.3,
               'probabilities':{'down':.2,'flat':.6,'up':.2}, 'direction':'flat',
               'online_learning':{
                   'version':'delayed-forward-learning-1.0',
                   'active_variant':'incumbent','trading_enabled':False,
                   'incumbent_probabilities':{'down':.2,'flat':.6,'up':.2},
                   'challenger_probabilities':{'down':.4,'flat':.4,'up':.2}},
               'directional_selection':{
                   'version':'direction-specialists-1.0','active':'incumbent',
                   'fallback_reason':None,'orders_enabled':False,
                   'strict_green_override':False},
               'directional_specialists':{
                   'version':'direction-specialists-1.0',
                   'status':'shadow_only',
                   'candidates':{'movement_then_direction':{
                       'probabilities':{'down':.6,'flat':.2,'up':.2},
                       'direction':'down'}}}}
        prior = audit_digest({'event':audit_digest({k:row[k] for k in
                              ('symbol','market','mode','target')}),
                              'policy':row['policy_revision'],
                              'base_model':row['model_sha256'],
                              'online':row['online_learning']})
        row['id'] = audit_digest({
            'prior_id':prior,'selection':row['directional_selection'],
            'specialists':row['directional_specialists'],'issued':row['issued_at']})
        validate(row)
        tampered = {**row, 'probabilities':{'down':.6,'flat':.2,'up':.2},
                    'direction':'down'}
        with self.assertRaisesRegex(ValueError,'online_frozen_probabilities_mismatch'):
            validate(tampered)
        with self.assertRaisesRegex(ValueError,'online_issuance_id_mismatch'):
            validate({**row,'id':'1'*64})
        alternate = {**row, 'directional_selection':{
            **row['directional_selection'], 'active':'movement_then_direction'}}
        with self.assertRaisesRegex(ValueError,'online_frozen_probabilities_mismatch'):
            validate(alternate)

    def test_snapshot_created_before_forecast_cannot_be_claimed_as_public(self):
        # Deliberately inconsistent synthetic publication, not a market observation.
        record = {'id': 'synthetic-late-issue', 'symbol': 'TEST', 'market': 'US',
                  'mode': 'intraday', 'status': 'research_prediction',
                  'observed_until': '2026-10-29T13:35:00Z',
                  'received_at': '2026-10-29T13:35:10Z',
                  'issued_at': '2026-10-29T13:36:00Z',
                  'target': {'start': '2026-10-29T14:00:00Z',
                             'end': '2026-10-29T14:30:00Z'},
                  'probabilities': {'down': .2, 'flat': .6, 'up': .2},
                  'direction': 'flat', 'neutral_band_pct': .3}
        outcome = {'id': record['id'], 'symbol': 'TEST', 'mode': 'intraday',
                   'status': 'observed', 'target': record['target'],
                   'evaluated_at': '2026-10-29T14:31:00Z',
                   'target_open': 100., 'target_close': 99.,
                   'return_pct': -1., 'actual': 'down', 'predicted': 'flat',
                   'correct': False, 'brier_loss': 1.04}
        pub = {'status': 'public_verified',
               'snapshot_generated_at': '2026-10-29T13:35:00Z',
               'verified_at': '2026-10-29T13:37:00Z',
               'prediction_ids': [record['id']]}
        cutoff = ts('2026-10-29T15:00:00Z')
        # verified_at alone cannot prove a forecast appeared in an earlier snapshot.
        old_snapshot = audit([record], [outcome], [pub], cutoff)
        self.assertEqual(old_snapshot['scored'], 0)
        self.assertEqual(old_snapshot['status'], 'integrity_errors')
        backwards_clock = audit([record], [outcome], [
            {**pub, 'snapshot_generated_at': '2026-10-29T13:38:00Z'}
        ], cutoff)
        self.assertEqual(backwards_clock['scored'], 0)
        self.assertEqual(backwards_clock['status'], 'integrity_errors')
        proper = audit([record], [outcome], [
            {**pub, 'snapshot_generated_at': '2026-10-29T13:36:30Z'}
        ], cutoff)
        self.assertEqual(proper['scored'], 1)
        self.assertEqual(proper['status'], 'ledger_arithmetic_consistent')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, default=Path('stock-forecast-independent-audit.json'))
    parser.add_argument('--cutoff')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SelfTests))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    result = audit(read_lines(args.root/'stock-forecast-ledger.jsonl'),
                   read_lines(args.root/'stock-forecast-outcomes.jsonl'),
                   read_lines(args.root/'stock-forecast-deliveries.jsonl'),
                   ts(args.cutoff) if args.cutoff else datetime.now(timezone.utc))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'scored', 'correct', 'accuracy', 'directions', 'errors')}, ensure_ascii=False))
    raise SystemExit(1 if result['errors'] else 0)
