"""Read-only independent arithmetic/timing audit; never trains or changes forecasts.
An internally consistent outcome is NOT independent verification of exchange prices.
"""
from __future__ import annotations
import argparse
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

def event_key(r):
    return (r['symbol'], r['market'], r['mode'], r['target']['start'], r['target']['end'])

def validate(r):
    p = [finite(r['probabilities'][k]) for k in CLASSES]
    if any(x < 0 or x > 1 for x in p) or abs(sum(p)-1) > 1e-6:
        raise ValueError('invalid_probabilities')
    if r['direction'] not in CLASSES or abs(p[CLASSES.index(r['direction'])]-max(p)) > 1e-12:
        raise ValueError('direction_not_maximum_probability')
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
    for d in deliveries:
        if d.get('status') != 'public_verified':
            continue
        seen = ts(d['verified_at'])
        for rid in d.get('prediction_ids', []):
            if rid not in public or seen < public[rid]:
                public[rid] = seen
    actuals = {}
    for o in outcomes:
        if o.get('status') != 'observed':
            continue
        if o['id'] in actuals and o != actuals[o['id']]:
            errors.append({'id': o['id'], 'error': 'conflicting_outcome_id'})
            continue
        actuals.setdefault(o['id'], o)
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
        try:
            if o['target'] != r['target'] or o['symbol'] != r['symbol'] or o['mode'] != r['mode']:
                raise ValueError('outcome_target_mismatch')
            if not end <= ts(o['evaluated_at']) <= cutoff:
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
            rows.append({'id': r['id'], 'symbol': r['symbol'], 'name': r.get('name', r['symbol']),
                         'issued_at': r['issued_at'], 'public_at': seen.isoformat(),
                         'target': r['target'], 'opening': opening, 'closing': closing,
                         'change_pct': change, 'band_pct': r['neutral_band_pct'],
                         'predicted': r['direction'], 'actual': label, 'correct': correct,
                         'brier_loss': loss,
                         'frozen_baseline_available': 'frozen_baseline_probabilities' in r})
        except (KeyError, ValueError, TypeError) as exc:
            errors.append({'id': r['id'], 'error': str(exc)})
    n = len(rows); correct = sum(r['correct'] for r in rows)
    direction = {}
    for c in CLASSES:
        actual = sum(r['actual'] == c for r in rows)
        calls = sum(r['predicted'] == c for r in rows)
        hits = sum(r['actual'] == c and r['predicted'] == c for r in rows)
        direction[c] = {'actual': actual, 'calls': calls, 'hits': hits, 'missed': actual-hits,
                        'false_calls': calls-hits, 'recall': hits/actual if actual else None,
                        'precision': hits/calls if calls else None}
    return {'version': 'independent-forecast-audit-1.0', 'audit_cutoff': cutoff.isoformat(),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'integrity_errors' if errors else 'ledger_arithmetic_consistent',
            'prediction_rows': len(records), 'unique_events': len(originals), 'counts': dict(counts),
            'scored': n, 'correct': correct, 'accuracy': correct/n if n else None,
            'directions': direction, 'rows': rows, 'errors': errors,
            'retrospective_constant_flat_accuracy': sum(r['actual'] == 'flat' for r in rows)/n if n else None,
            'constant_flat_is_diagnostic_not_preregistered_benchmark': True,
            'externally_verified_candles': False, 'human_push_delivery_verified': False,
            'proven_predictive_edge': False, 'perfect_future_prediction_proven': False,
            'scope': 'Recomputes stored open/close arithmetic and timing; does not verify raw exchange candles or execution.'}

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
        d = {'status': 'public_verified', 'verified_at': '2026-10-29T13:37:00Z', 'prediction_ids': ['test-only']}
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
