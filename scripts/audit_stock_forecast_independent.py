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
# Shadow-only model catalogue was fixed before forward evidence accrued.
REVIEWED_SHADOW_CANDIDATES = frozenset(('balanced_linear', 'balanced_nonlinear',
                                       'movement_then_direction'))

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
    # A baseline frozen at issuance may be used for paired performance
    # comparison; malformed vectors must not silently enter that comparison.
    # Absence in legacy forecasts is not an authorization to backfill one.
    if 'frozen_baseline_probabilities' in r:
        baseline = r['frozen_baseline_probabilities']
        if not isinstance(baseline, dict) or set(baseline) != set(CLASSES):
            raise ValueError('invalid_frozen_baseline_distribution')
        bp = [finite(baseline[k]) for k in CLASSES]
        if any(x < 0 or x > 1 for x in bp) or abs(sum(bp) - 1) > 1e-6:
            raise ValueError('invalid_frozen_baseline_distribution')
    if r['direction'] not in CLASSES or abs(p[CLASSES.index(r['direction'])]-max(p)) > 1e-12:
        raise ValueError('direction_not_maximum_probability')
    # The published research-uncertainty flag is part of the frozen signal,
    # not a free-text display hint. Independently recompute it from the
    # applied three-class distribution using the *existing* 0.50/0.10 policy.
    # A mismatched flag could disguise an uncertain call as a confident one.
    # Legacy rows issued without direction selection contain no signal.
    selector_present = r.get('directional_selection') is not None
    signal_present = 'directional_signal' in r
    if selector_present and not signal_present:
        raise ValueError('directional_signal_missing')
    if signal_present:
        if not selector_present:
            raise ValueError('invalid_directional_signal')
        signal = r['directional_signal']
        required = ('uncertain', 'uncertainty_is_not_flat',
                    'all_original_predictions_still_scored',
                    'thresholds_are_policy_not_success_probabilities')
        if (not isinstance(signal, dict) or
                any(name not in signal for name in required) or
                type(signal['uncertain']) is not bool or
                any(signal[name] is not True for name in required[1:])):
            raise ValueError('invalid_directional_signal')
        ranked = sorted(p, reverse=True)
        originally_uncertain = ranked[0] < 0.50 or ranked[0] - ranked[1] < 0.10
        if signal['uncertain'] is not originally_uncertain:
            raise ValueError('directional_uncertainty_mismatch')

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
            if candidate_name not in REVIEWED_SHADOW_CANDIDATES:
                raise ValueError('unreviewed_shadow_candidate')
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
    # The declared observation is the as-of boundary for all model data
    # used to issue this forecast, not merely the issuance timestamp. This
    # protects frozen provenance; it does not authenticate provider history.
    observed = ts(r['observed_until'])
    trained = ts(r['trained_through']) if r.get('trained_through') else None
    calibrated = ts(r['calibrated_through']) if r.get('calibrated_through') else None
    if trained and trained > observed:
        raise ValueError('model_training_after_observed_input')
    if calibrated and calibrated > observed:
        raise ValueError('model_calibration_after_observed_input')
    if trained and calibrated and trained > calibrated:
        raise ValueError('model_training_after_calibration')
    validation = r.get('validation')
    if isinstance(validation, dict) and validation.get('test_end') is not None:
        if ts(validation['test_end']) > observed:
            raise ValueError('model_validation_after_observed_input')
    classify(0.0, r['neutral_band_pct'])
    # Independently reconstruct the precommitted neutral band for modern
    # provider-latency forecasts, instead of trusting the number that itself
    # decides whether a stored return is up, down, or flat. Older unknown
    # policies keep their historical path; no old forecast is backfilled.
    if (r.get('version') == 'direction-forecast-1.0' and
            r.get('policy_revision') == 'provider-latency-30m-v1'):
        mode = r.get('mode')
        if mode not in ('daily', 'intraday'):
            raise ValueError('unknown_frozen_band_mode')
        features = r.get('feature_values')
        if not isinstance(features, dict) or 'vol20' not in features:
            raise ValueError('missing_frozen_band_feature')
        volatility = finite(features['vol20'])
        if volatility < 0:
            raise ValueError('negative_frozen_volatility')
        expected = max(0.30 if mode == 'daily' else 0.15,
                       volatility * (1 if mode == 'daily' else math.sqrt(6))
                       * 0.35 * 100)
        if abs(finite(r['neutral_band_pct']) - expected) > 1e-9:
            raise ValueError('neutral_band_policy_mismatch')

def audit(records, outcomes, deliveries, cutoff):
    counts = Counter(); errors = []; by_id = {}; originals = {}; issuance_times = {}
    for r in records:
        if r.get('status') != 'research_prediction':
            # Frozen forecast ledger is append-only calls; no-call attempts live
            # in a separate file. Suppressed/unknown rows cannot disappear.
            errors.append({'id': r.get('id'), 'error': 'unexpected_forecast_ledger_status'})
            continue
        try:
            validate(r)
            if r['id'] in by_id and by_id[r['id']] != r:
                raise ValueError('conflicting_prediction_id')
            by_id[r['id']] = r
            key = event_key(r)
            issuance_times.setdefault(key, []).append((ts(r['issued_at']), r['id']))
            old = originals.get(key)
            if old is not None:
                counts['duplicate_issuances'] += 1
            if old is None or ts(r['issued_at']) < ts(old['issued_at']):
                originals[key] = r
        except (KeyError, ValueError, TypeError) as exc:
            errors.append({'id': r.get('id'), 'error': str(exc)})
    # The first issuance is evidence, not a file-order lottery. Distinct
    # forecast IDs issued at the same earliest instant for the same future
    # event are ambiguous: reject the event rather than select the row that
    # happened to appear first in the JSONL file. Repeated identical IDs are
    # allowed; later distinct reissuances remain excluded by first issuance.
    ambiguous_events = set()
    for key, candidates in issuance_times.items():
        earliest = min(moment for moment, _ in candidates)
        first_ids = {ident for moment, ident in candidates if moment == earliest}
        if len(first_ids) > 1:
            ambiguous_events.add(key)
            errors.append({'id': sorted(first_ids)[0],
                           'error': 'ambiguous_first_issuance_tie'})
    public = {}
    valid_public_times = []  # verified snapshots, distinct from first public time per forecast
    seen_verification_ids = {}
    for d in deliveries:
        # A public proof identifier must never resolve to two different events.
        # A conflicting replay could otherwise fabricate an earlier publication.
        proof_id = d.get('verification_id')
        if proof_id is not None:
            if (not isinstance(proof_id, str) or len(proof_id) != 64 or
                    any(ch not in '0123456789abcdef' for ch in proof_id)):
                errors.append({'id': None, 'error': 'invalid_public_verification_id'})
                continue
            previous = seen_verification_ids.get(proof_id)
            if previous is not None and previous != d:
                errors.append({'id': proof_id, 'error': 'conflicting_public_verification_id'})
                continue
            seen_verification_ids[proof_id] = d
            # Publisher freezes its record's canonical hash as verification_id.
            # This detects stale/altered payloads, NOT independent publication
            # time or a human push receipt. Never infer missing legacy IDs.
            frozen_payload = {k: v for k, v in d.items() if k != 'verification_id'}
            if proof_id != audit_digest(frozen_payload):
                errors.append({'id': proof_id, 'error': 'public_verification_fingerprint_mismatch'})
                continue
        if d.get('status') != 'public_verified':
            # This append-only ledger contains successful public proofs only.
            # Unknown/missing statuses must not silently remove issued
            # forecasts from prospective scoring or apparent coverage.
            errors.append({'id': proof_id, 'error': 'unexpected_public_proof_status'})
            continue
        # Website verification is NOT proof of receipt by a specific person.
        # The present public-proof schema has no independently authenticated
        # recipient acknowledgment. Do not accept a boolean/string receipt
        # claim even if the untrusted proof fingerprint was recomputed.
        # Missing historical optional flags remain absent, never backfilled.
        if ('human_notification_received' in d and
                d['human_notification_received'] is not False):
            errors.append({'id': proof_id, 'error': 'unsupported_human_receipt_claim'})
            continue
        # A verified public snapshot must identify a meaningful set of frozen
        # calls. An empty/malformed/repeated membership is not publication proof.
        # Even a recomputed canonical fingerprint cannot make it such proof.
        members = d.get('prediction_ids')
        if (not isinstance(members, list) or not members or
                any(not isinstance(rid, str) or not rid for rid in members) or
                len(set(members)) != len(members)):
            errors.append({'id': proof_id, 'error': 'invalid_public_proof_prediction_ids'})
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
        for rid in members:
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
            # The outcome ledger contains only final observed results. A
            # relabelled evidence row must not vanish into "missing outcomes".
            errors.append({'id': o.get('id'), 'error': 'unexpected_observed_outcome_status'})
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
            # An outcome may report its own issuance time for provenance,
            # but it must not silently change the originally frozen forecast
            # issuance time. Legacy missing copies are not backfilled.
            # Compare absolute UTC instants, not ISO string formatting.
            if 'issued_at' in o and ts(o['issued_at']) != ts(r['issued_at']):
                raise ValueError('outcome_issued_at_mismatch')
            if not ts(r['target']['end']) <= ts(o['evaluated_at']) <= cutoff:
                raise ValueError('outcome_timestamp_not_eligible')
            # A claimed result cannot be evaluated before the provider was
            # checked or before its target window closed. This only validates
            # recorded timestamps, NOT the external price or its feed rights.
            # Absence in legacy records is not retroactively inferred.
            source_checked = o.get('source_checked_at')
            if source_checked is not None and not (
                    ts(r['target']['end']) <= ts(source_checked) <= ts(o['evaluated_at'])):
                raise ValueError('outcome_source_time_inconsistent')
            # An observed provider return is not an order fill or an
            # independently authenticated executable quote. These optional
            # frozen disclosure fields may be absent in legacy rows, but a
            # present contradictory claim must never pass the independent
            # evidence audit merely because its price arithmetic is correct.
            if ('price_observation_not_execution_return' in o and
                    o['price_observation_not_execution_return'] is not True):
                raise ValueError('unsupported_execution_return_claim')
            if ('single_provider_not_execution' in o and
                    o['single_provider_not_execution'] is not True):
                raise ValueError('unsupported_independent_provider_claim')
            # The outcome's pre-target publication assertion is checked
            # against the earliest independent public proof, not trusted as
            # its own verification. A public web proof is not a human receipt.
            if 'public_before_target_verified' in o:
                earliest = public.get(o['id'])
                timely = (earliest is not None and
                          ts(r['issued_at']) <= earliest < ts(r['target']['start']))
                if (type(o['public_before_target_verified']) is not bool or
                        o['public_before_target_verified'] is not timely):
                    raise ValueError('outcome_public_timing_claim_mismatch')
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
            # The copied public-HTML verification time is not a human receipt.
            # When an observed outcome records this optional timestamp, it must
            # agree with the earliest independently logged valid public snapshot.
            # Historic outcomes lacking this copy are neither backfilled nor
            # credited with human notification delivery.
            copied_public = o.get('delivery_verified_at')
            if copied_public is not None:
                first_public = public.get(o['id'])
                if first_public is None or ts(copied_public) != first_public:
                    raise ValueError('outcome_public_timestamp_mismatch')
            verified_outcomes[o['id']] = (opening, closing, change, label, correct, loss)
        except (KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
            errors.append({'id': o.get('id'), 'error': str(exc)})
    rows = []; last_end = {}
    # Selection is chronological and independent of the observed correctness.
    for r in sorted((r for key, r in originals.items() if key not in ambiguous_events),
                    key=lambda x: (event_key(x)[:3], ts(x['target']['start']), ts(x['issued_at']))):
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
    def test_public_proof_cannot_assert_unauthenticated_human_receipt(self):
        # Pre-registered synthetic RED: a canonical self-hash is not a
        # recipient's independent acknowledgment of a pushed signal.
        from copy import deepcopy
        row = {'id': 'synthetic-human-receipt', 'symbol': 'TEST',
               'market': 'US', 'mode': 'intraday', 'status': 'research_prediction',
               'observed_until': '2026-10-29T13:30:00Z',
               'received_at': '2026-10-29T13:31:00Z',
               'issued_at': '2026-10-29T13:36:00Z',
               'target': {'start': '2026-10-29T14:00:00Z',
                          'end': '2026-10-29T14:30:00Z'},
               'probabilities': {'down': .2, 'flat': .6, 'up': .2},
               'direction': 'flat', 'neutral_band_pct': .3}
        original = {'status': 'public_verified',
                    'snapshot_generated_at': '2026-10-29T13:36:20Z',
                    'verified_at': '2026-10-29T13:37:00Z',
                    'prediction_ids': [row['id']],
                    'human_notification_received': False}
        cutoff = ts('2026-10-29T15:00:00Z')
        valid = {**original, 'verification_id': audit_digest(original)}
        self.assertEqual(audit([row], [], [valid], cutoff)['status'],
                         'ledger_arithmetic_consistent')
        # Missing historical optional field is not retroactively invented.
        legacy = {k: v for k, v in original.items()
                  if k != 'human_notification_received'}
        self.assertEqual(audit([row], [],
                              [{**legacy, 'verification_id': audit_digest(legacy)}],
                              cutoff)['status'], 'ledger_arithmetic_consistent')
        # A deliberate false human-delivery claim, even with a new valid
        # self-fingerprint, must NOT pass the independent evidence audit.
        for claimed in (True, 'true'):
            forged = deepcopy(original)
            forged['human_notification_received'] = claimed
            forged['verification_id'] = audit_digest(forged)
            with self.subTest(receipt=claimed):
                result = audit([row], [], [forged], cutoff)
                self.assertEqual(result['status'], 'integrity_errors')
                self.assertTrue(any(
                    e['error'] == 'unsupported_human_receipt_claim'
                    for e in result['errors']))

    def test_frozen_ledger_cannot_falsely_claim_exchange_or_point_in_time_source(self):
        # Pre-registered RED: no independent official-exchange raw candles or
        # original point-in-time provider history are evidenced by yfinance.
        row = {'id': 'synthetic-only-source-claim', 'symbol': 'TEST',
               'market': 'US', 'mode': 'intraday', 'status': 'research_prediction',
               'observed_until': '2026-10-29T13:30:00Z',
               'received_at': '2026-10-29T13:31:00Z',
               'issued_at': '2026-10-29T13:36:00Z',
               'target': {'start': '2026-10-29T14:00:00Z',
                          'end': '2026-10-29T14:30:00Z'},
               'probabilities': {'down': .2, 'flat': .6, 'up': .2},
               'direction': 'flat', 'neutral_band_pct': .3,
               'source_type': 'provider_historical_prices',
               'collector': 'yfinance',
               'source_url': 'https://finance.yahoo.com/quote/TEST',
               'provider_is_official_exchange': False,
               'history_is_point_in_time_vintage': False}
        self.assertIsNone(validate(row))
        legacy = {k: v for k, v in row.items() if k not in (
            'provider_is_official_exchange',
            'history_is_point_in_time_vintage')}
        self.assertIsNone(validate(legacy))
        for field in ('provider_is_official_exchange',
                      'history_is_point_in_time_vintage'):
            for claim in (True, 'true', 1):
                with self.subTest(field=field, claim=claim):
                    forged = {**row, field: claim}
                    with self.assertRaisesRegex(ValueError,
                            'unsupported_ledger_source_claim'):
                        validate(forged)

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
    def test_unknown_or_missing_public_proof_status_must_fail_closed(self):
        # Synthetic-only negative control. A malformed delivery entry must
        # not silently suppress a previously eligible forecast from scoring.
        from copy import deepcopy
        row = {'id': 'synthetic-proof-status', 'symbol': 'TEST', 'market': 'US',
               'mode': 'intraday', 'status': 'research_prediction',
               'observed_until': '2026-10-29T13:30:00Z',
               'received_at': '2026-10-29T13:31:00Z',
               'issued_at': '2026-10-29T13:36:00Z',
               'target': {'start': '2026-10-29T14:00:00Z',
                          'end': '2026-10-29T14:30:00Z'},
               'probabilities': {'down': .2, 'flat': .6, 'up': .2},
               'direction': 'flat', 'neutral_band_pct': .3}
        original_proof = {'status': 'public_verified',
                          'snapshot_generated_at': '2026-10-29T13:36:20Z',
                          'verified_at': '2026-10-29T13:37:00Z',
                          'prediction_ids': [row['id']],
                          'human_notification_received': False}
        cutoff = ts('2026-10-29T15:00:00Z')
        valid = deepcopy(original_proof)
        valid['verification_id'] = audit_digest(valid)
        self.assertEqual(audit([row], [], [valid], cutoff)['status'],
                         'ledger_arithmetic_consistent')
        for malformed in ({**original_proof, 'status': 'not_verified'},
                          {k: v for k, v in original_proof.items()
                           if k != 'status'}):
            # Updating the fingerprint does not authorize an unknown status.
            altered = deepcopy(malformed)
            altered['verification_id'] = audit_digest(altered)
            with self.subTest(status=altered.get('status')):
                result = audit([row], [], [altered], cutoff)
                self.assertEqual(result['status'], 'integrity_errors')

    def test_public_proof_membership_cannot_be_empty_malformed_or_repeated(self):
        # Synthetic-only RED/GREEN control: canonical proof hashes alone do
        # not establish that a public snapshot contains any frozen call.
        row = {'id': 'synthetic-proof-membership', 'symbol': 'TEST', 'market': 'US',
               'mode': 'intraday', 'status': 'research_prediction',
               'observed_until': '2026-10-29T13:30:00Z',
               'received_at': '2026-10-29T13:31:00Z',
               'issued_at': '2026-10-29T13:36:00Z',
               'target': {'start': '2026-10-29T14:00:00Z',
                          'end': '2026-10-29T14:30:00Z'},
               'probabilities': {'down': .2, 'flat': .6, 'up': .2},
               'direction': 'flat', 'neutral_band_pct': .3}
        proof = {'status': 'public_verified',
                 'snapshot_generated_at': '2026-10-29T13:36:20Z',
                 'verified_at': '2026-10-29T13:37:00Z',
                 'prediction_ids': [row['id']],
                 'human_notification_received': False}
        cutoff = ts('2026-10-29T15:00:00Z')
        good = {**proof, 'verification_id': audit_digest(proof)}
        self.assertEqual(audit([row], [], [good], cutoff)['status'],
                         'ledger_arithmetic_consistent')
        malformed_memberships = [[], {}, [row['id'], row['id']]]
        for membership in malformed_memberships:
            payload = {**proof, 'prediction_ids': membership}
            tampered = {**payload, 'verification_id': audit_digest(payload)}
            with self.subTest(membership=membership):
                result = audit([row], [], [tampered], cutoff)
                self.assertEqual(result['status'], 'integrity_errors')
                self.assertTrue(any(e['error'] == 'invalid_public_proof_prediction_ids'
                                    for e in result['errors']))
        missing = {key: value for key, value in proof.items()
                   if key != 'prediction_ids'}
        missing['verification_id'] = audit_digest(missing)
        result = audit([row], [], [missing], cutoff)
        self.assertEqual(result['status'], 'integrity_errors')
        self.assertTrue(any(e['error'] == 'invalid_public_proof_prediction_ids'
                            for e in result['errors']))

    def test_outcome_provenance_assertions_must_be_independently_supported(self):
        # Preregistered research-only negative controls. No operating evidence
        # is changed and a stored price movement is never a paper fill.
        row = {'id': 'synthetic-outcome-claims', 'symbol': 'TEST',
               'market': 'US', 'mode': 'intraday', 'status': 'research_prediction',
               'observed_until': '2026-10-29T13:30:00Z',
               'received_at': '2026-10-29T13:31:00Z',
               'issued_at': '2026-10-29T13:36:00Z',
               'target': {'start': '2026-10-29T14:00:00Z',
                          'end': '2026-10-29T14:30:00Z'},
               'probabilities': {'down': .2, 'flat': .6, 'up': .2},
               'direction': 'flat', 'neutral_band_pct': .3}
        outcome = {'id': row['id'], 'symbol': row['symbol'], 'mode': row['mode'],
                   'status': 'observed', 'issued_at': row['issued_at'],
                   'target': row['target'], 'evaluated_at': '2026-10-29T14:31:00Z',
                   'target_open': 100., 'target_close': 100., 'return_pct': 0.,
                   'actual': 'flat', 'predicted': 'flat', 'correct': True,
                   'brier_loss': .24,
                   'public_before_target_verified': True,
                   'delivery_verified_at': '2026-10-29T13:37:00Z',
                   'price_observation_not_execution_return': True,
                   'single_provider_not_execution': True}
        payload = {'status': 'public_verified',
                   'snapshot_generated_at': '2026-10-29T13:36:30Z',
                   'verified_at': '2026-10-29T13:37:00Z',
                   'prediction_ids': [row['id']],
                   'human_notification_received': False}
        proof = {**payload, 'verification_id': audit_digest(payload)}
        cutoff = ts('2026-10-29T15:00:00Z')
        baseline = audit([row], [outcome], [proof], cutoff)
        self.assertEqual(baseline['status'], 'ledger_arithmetic_consistent')
        self.assertEqual(baseline['scored'], 1)
        cases = (
            ('price_observation_not_execution_return', False,
             'unsupported_execution_return_claim'),
            ('single_provider_not_execution', False,
             'unsupported_independent_provider_claim'),
            ('public_before_target_verified', False,
             'outcome_public_timing_claim_mismatch'),
            ('public_before_target_verified', 'true',
             'outcome_public_timing_claim_mismatch'),
        )
        for field, claimed, reason in cases:
            with self.subTest(field=field, claimed=claimed):
                tampered = {**outcome, field: claimed}
                result = audit([row], [tampered], [proof], cutoff)
                self.assertEqual(result['status'], 'integrity_errors')
                self.assertIn(reason, [x['error'] for x in result['errors']])
        # A false early-publication claim is not rescued by a missing proof;
        # removing its copied timestamp avoids an unrelated identity error.
        without_proof = {k: v for k, v in outcome.items()
                         if k != 'delivery_verified_at'}
        result = audit([row], [without_proof], [], cutoff)
        self.assertEqual(result['status'], 'integrity_errors')
        self.assertIn('outcome_public_timing_claim_mismatch',
                      [x['error'] for x in result['errors']])
        # Older rows without optional assertions must not be retroactively
        # assigned new fields or silently turned into execution claims.
        for field in ('price_observation_not_execution_return',
                      'single_provider_not_execution',
                      'public_before_target_verified'):
            with self.subTest(legacy_missing=field):
                legacy = {k: v for k, v in outcome.items() if k != field}
                preserved = audit([row], [legacy], [proof], cutoff)
                self.assertEqual(preserved['status'], 'ledger_arithmetic_consistent')
                self.assertEqual(preserved['scored'], 1)

    def test_outcome_issuance_timestamp_must_match_frozen_forecast(self):
        # One preregistered synthetic RED/GREEN outcome-lineage negative
        # control. This must not alter or learn from any production outcome.
        row = {'id': 'synthetic-issuance-binding', 'symbol': 'TEST',
               'market': 'US', 'mode': 'intraday', 'status': 'research_prediction',
               'observed_until': '2026-10-29T13:30:00Z',
               'received_at': '2026-10-29T13:31:00Z',
               'issued_at': '2026-10-29T13:36:00Z',
               'target': {'start': '2026-10-29T14:00:00Z',
                          'end': '2026-10-29T14:30:00Z'},
               'probabilities': {'down': .2, 'flat': .6, 'up': .2},
               'direction': 'flat', 'neutral_band_pct': .3}
        outcome = {'id': row['id'], 'symbol': row['symbol'],
                   'mode': row['mode'], 'status': 'observed',
                   'issued_at': row['issued_at'], 'target': row['target'],
                   'evaluated_at': '2026-10-29T14:31:00Z',
                   'target_open': 100., 'target_close': 100.,
                   'return_pct': 0., 'actual': 'flat', 'predicted': 'flat',
                   'correct': True, 'brier_loss': .24}
        payload = {'status': 'public_verified',
                   'snapshot_generated_at': '2026-10-29T13:36:30Z',
                   'verified_at': '2026-10-29T13:37:00Z',
                   'prediction_ids': [row['id']],
                   'human_notification_received': False}
        proof = {**payload, 'verification_id': audit_digest(payload)}
        cutoff = ts('2026-10-29T15:00:00Z')
        good = audit([row], [outcome], [proof], cutoff)
        self.assertEqual(good['status'], 'ledger_arithmetic_consistent')
        self.assertEqual(good['scored'], 1)
        # An equivalent exchange-independent timestamp is legitimate.
        offset = {**outcome, 'issued_at': '2026-10-29T22:36:00+09:00'}
        self.assertEqual(audit([row], [offset], [proof], cutoff)['scored'], 1)
        # A timestamp not frozen at original forecast issuance must be an
        # integrity error, even if score and publication arithmetic agree.
        altered = {**outcome, 'issued_at': '2026-10-29T13:35:00Z'}
        checked = audit([row], [altered], [proof], cutoff)
        self.assertEqual(checked['status'], 'integrity_errors')
        self.assertTrue(any(e['error'] == 'outcome_issued_at_mismatch'
                            for e in checked['errors']))
        no_tz = {**outcome, 'issued_at': '2026-10-29T13:36:00'}
        self.assertEqual(audit([row], [no_tz], [proof], cutoff)['status'],
                         'integrity_errors')
        # Historical missing-field fixtures must not have a timestamp invented.
        legacy = {k: v for k, v in outcome.items() if k != 'issued_at'}
        self.assertEqual(audit([row], [legacy], [proof], cutoff)['scored'], 1)

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

    def test_frozen_baseline_probability_distribution_must_be_valid(self):
        # Synthetic-only negative controls: no changes to original forecasts.
        base = {'id': 'synthetic-baseline', 'symbol': 'TEST', 'market': 'US',
                'mode': 'intraday', 'status': 'research_prediction',
                'observed_until': '2026-10-29T13:30:00Z',
                'received_at': '2026-10-29T13:31:00Z',
                'issued_at': '2026-10-29T13:36:00Z',
                'target': {'start': '2026-10-29T14:00:00Z',
                           'end': '2026-10-29T14:30:00Z'},
                'probabilities': {'down': .2, 'flat': .6, 'up': .2},
                'direction': 'flat', 'neutral_band_pct': .3}
        # Legacy records have no invented baseline; valid original vectors pass.
        validate(base)
        valid = {**base, 'frozen_baseline_probabilities':
                 {'down': .25, 'flat': .5, 'up': .25}}
        validate(valid)
        corruptions = {
            'non_normalized': {'down': .25, 'flat': .5, 'up': .3},
            'negative_with_sum_one': {'down': -.1, 'flat': .9, 'up': .2},
            'nonfinite': {'down': float('nan'), 'flat': .5, 'up': .5},
            'missing_class': {'down': .25, 'flat': .75},
        }
        for label, forged in corruptions.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    validate({**base, 'frozen_baseline_probabilities': forged})

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
               'directional_signal':{
                   'uncertain':False, 'uncertainty_is_not_flat':True,
                   'all_original_predictions_still_scored':True,
                   'thresholds_are_policy_not_success_probabilities':True},
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


    def test_outcome_claimed_public_copy_cannot_precede_real_snapshot(self):
        # Red/green reproduction uses SYNTHETIC outcomes only, never market evidence.
        record = {'id': 'synthetic-public-copy', 'symbol': 'TEST', 'market': 'US',
                  'mode': 'intraday', 'status': 'research_prediction',
                  'observed_until': '2026-10-29T13:35:00Z',
                  'received_at': '2026-10-29T13:35:10Z',
                  'issued_at': '2026-10-29T13:36:00Z',
                  'target': {'start': '2026-10-29T14:00:00Z',
                             'end': '2026-10-29T14:30:00Z'},
                  'probabilities': {'down': .2, 'flat': .6, 'up': .2},
                  'direction': 'flat', 'neutral_band_pct': .3}
        pub = {'status': 'public_verified',
               'snapshot_generated_at': '2026-10-29T13:36:30Z',
               'verified_at': '2026-10-29T13:37:00Z',
               'prediction_ids': [record['id']]}
        outcome = {'id': record['id'], 'symbol': 'TEST', 'mode': 'intraday',
                   'status': 'observed', 'target': record['target'],
                   'evaluated_at': '2026-10-29T14:31:00Z',
                   'target_open': 100., 'target_close': 99.,
                   'return_pct': -1., 'actual': 'down', 'predicted': 'flat',
                   'correct': False, 'brier_loss': 1.04,
                   'delivery_verified_at': '2026-10-29T13:37:00Z'}
        now = ts('2026-10-29T15:00:00Z')
        good = audit([record], [outcome], [pub], now)
        self.assertEqual(good['status'], 'ledger_arithmetic_consistent')
        self.assertEqual((good['scored'], good['correct']), (1, 0))
        tampered = {**outcome, 'delivery_verified_at': '2026-10-29T13:36:01Z'}
        bad = audit([record], [tampered], [pub], now)
        self.assertEqual(bad['status'], 'integrity_errors')
        self.assertTrue(any(e.get('error') == 'outcome_public_timestamp_mismatch'
                            for e in bad['errors']))
        # Older outcomes that have no public-time copy must not be backfilled.
        legacy = {k: v for k, v in outcome.items() if k != 'delivery_verified_at'}
        self.assertEqual(audit([record], [legacy], [pub], now)['scored'], 1)

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
