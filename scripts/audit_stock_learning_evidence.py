"""Read-only, producer-independent audit of frozen learning events.

This protects evidence provenance. It does not retrain models, validate live
exchange prices or certify investment usefulness. All tests use synthetic rows.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unittest

from audit_stock_forecast_independent import audit, read_lines, ts

VERSION = 'delayed-forward-learning-1.0'
SHA = re.compile(r'^[a-f0-9]{64}$')


def digest(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8')).hexdigest()


def forecast_key(r):
    return digest({key: r[key] for key in ('symbol', 'market', 'mode', 'target')})


def examine(records, outcomes, deliveries, events, state, cutoff):
    """Audit only already-saved evidence; never modify data or infer a fill."""
    cutoff = ts(cutoff.isoformat() if hasattr(cutoff, 'isoformat') else cutoff)
    source = audit(records, outcomes, deliveries, cutoff)
    errors = []
    by_id = {r['id']: r for r in records if r.get('status') == 'research_prediction'}
    actuals = {r['id']: r for r in outcomes if r.get('status') == 'observed'}
    eligible = {r['id']: r for r in source['rows']}
    used_keys, used_ids = set(), set()
    learning_rows = [e for e in events if e.get('kind') == 'learn_after_score']
    for index, event in enumerate(learning_rows):
        ident = event.get('prediction_id')
        try:
            rid = event['id']
            eid = event['event_key']
            if rid in used_ids:
                raise ValueError('duplicate_learning_event_id')
            used_ids.add(rid)
            if eid in used_keys:
                raise ValueError('duplicate_learning_event_key')
            used_keys.add(eid)
            r = by_id.get(ident)
            o = actuals.get(ident)
            accepted = eligible.get(ident)
            if r is None or o is None or accepted is None:
                raise ValueError('learning_without_eligible_public_outcome')
            true_key = forecast_key(r)
            if eid != true_key:
                raise ValueError('learning_event_key_does_not_match_frozen_target')
            if rid != digest({'version': VERSION, 'trained_event': true_key}):
                raise ValueError('learning_event_id_fingerprint_mismatch')
            if event['group'] != '|'.join((
                r['symbol'], r['mode'], r.get('policy_revision', 'legacy'))):
                raise ValueError('learning_group_mismatch')
            if event['actual'] != accepted['actual'] or event['actual'] != o['actual']:
                raise ValueError('learning_label_mismatch')
            available = ts(event['available_at'])
            learned = ts(event['learned_at'])
            evaluated = ts(o['evaluated_at'])
            if available != evaluated:
                raise ValueError('learning_available_at_mismatch')
            if not (ts(r['target']['end']) <= available <= learned <= cutoff):
                raise ValueError('learning_before_outcome_or_in_future')
            if learned < ts(accepted['public_at']):
                raise ValueError('learning_before_public_snapshot')
            if event.get('not_rescored') is not True:
                raise ValueError('learning_original_score_not_preserved')
            for name in ('weights_before', 'weights_after'):
                if not isinstance(event.get(name), str) or SHA.fullmatch(event[name]) is None:
                    raise ValueError('learning_weight_fingerprint_invalid')
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            errors.append({'index': index, 'id': ident, 'error': str(exc)})
    # The SHA-shaped event strings must reconcile with the persisted weight
    # vectors and with earlier updates in the same append-only event stream.
    per_group = {}
    for event in learning_rows:
        name = event.get('group')
        if isinstance(name, str):
            per_group.setdefault(name, []).append(event)
    try:
        saved_groups = state['groups']
        if not isinstance(saved_groups, dict):
            raise ValueError('learning_groups_not_dictionary')
        for name in per_group:
            if name not in saved_groups:
                errors.append({'index': None, 'id': name,
                               'error': 'learning_event_group_missing_from_saved_state'})
        for name, saved in saved_groups.items():
            try:
                if not isinstance(saved, dict):
                    raise ValueError('learning_saved_group_not_dictionary')
                history = per_group.get(name, [])
                if type(saved.get('learned')) is not int or saved['learned'] != len(history):
                    raise ValueError('learning_group_count_disagrees_with_event_history')
                if not history:
                    # An untrained group has no terminal event hash, but its
                    # producer-defined initial 3-class/13-feature correction
                    # is exactly zero. Never accept an undocumented correction.
                    weights = saved.get('weights')
                    if (not isinstance(weights, list) or len(weights) != 3
                            or any(not isinstance(row, list) or len(row) != 13
                                   or any(type(v) not in (int, float) or v != 0
                                          for v in row)
                                   for row in weights)):
                        raise ValueError('untrained_group_weights_not_zero')
                    continue  # No older weight updates can be inferred.
                for prior, following in zip(history, history[1:]):
                    if prior['weights_after'] != following['weights_before']:
                        raise ValueError('learning_weight_hash_chain_broken')
                    if ts(prior['learned_at']) > ts(following['learned_at']):
                        raise ValueError('learning_weight_event_order_reversed')
                if digest(saved['weights']) != history[-1]['weights_after']:
                    raise ValueError('learning_terminal_weights_do_not_match_saved_state')
                last_record = by_id[history[-1]['prediction_id']]
                if saved.get('last_train_end') != last_record['target']['end']:
                    raise ValueError('learning_last_target_mismatch')
            except (KeyError, ValueError, TypeError, AttributeError) as exc:
                errors.append({'index': None, 'id': name, 'error': str(exc)})
    except (KeyError, ValueError, TypeError) as exc:
        errors.append({'index': None, 'id': 'learning-groups', 'error': str(exc)})
    try:
        trained = state['trained_events']
        if not isinstance(trained, list) or len(trained) != len(set(trained)):
            raise ValueError('learning_state_duplicate_trained_event')
        if not all(isinstance(k, str) and SHA.fullmatch(k) for k in trained):
            raise ValueError('learning_state_bad_event_key')
        if set(trained) != used_keys:
            raise ValueError('learning_state_events_do_not_match_immutable_history')
        if type(state.get('training_updates')) is not int or state['training_updates'] != len(learning_rows):
            raise ValueError('learning_updates_disagree_with_event_history')
        if learning_rows:
            available_max = max(ts(e['available_at']) for e in learning_rows)
            if state.get('last_outcome_available_at') is None or ts(state['last_outcome_available_at']) != available_max:
                raise ValueError('learning_latest_available_time_mismatch')
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        errors.append({'index': None, 'id': 'learning-state', 'error': str(exc)})
    return {
        'version': 'independent-learning-evidence-1.0',
        'status': 'integrity_errors' if source['errors'] or errors else 'learning_evidence_consistent',
        'audit_cutoff': cutoff.isoformat(),
        'source_integrity_errors': len(source['errors']),
        'learning_event_rows': len(learning_rows),
        'frozen_scored_results': source['scored'],
        'frozen_correct_results': source['correct'],
        'learning_updates_recorded': state.get('training_updates'),
        'errors': errors,
        'external_exchange_candles_verified': False,
        'human_push_delivery_verified': False,
        'post_cost_usefulness_verified': False,
        'model_or_approval_changed': False,
        'scope': 'Independent chronology/fingerprint consistency of immutable learning events; no execution or signal-quality proof.'
    }


def synthetic():
    r = {'id':'synthetic-forecast','symbol':'TEST','market':'US','mode':'intraday',
         'status':'research_prediction','observed_until':'2026-10-29T13:30:00Z',
         'received_at':'2026-10-29T13:31:00Z','issued_at':'2026-10-29T13:36:00Z',
         'target':{'start':'2026-10-29T14:00:00Z','end':'2026-10-29T14:30:00Z'},
         'probabilities':{'down':.2,'flat':.6,'up':.2},
         'direction':'flat','neutral_band_pct':.3}
    o = {'id':r['id'],'symbol':'TEST','mode':'intraday','status':'observed',
         'target':r['target'],'evaluated_at':'2026-10-29T14:35:00Z',
         'target_open':100.,'target_close':99.,'return_pct':-1.,
         'actual':'down','predicted':'flat','correct':False,'brier_loss':1.04}
    d = {'status':'public_verified','snapshot_generated_at':'2026-10-29T13:36:10Z',
         'verified_at':'2026-10-29T13:36:15Z','prediction_ids':[r['id']]}
    k = forecast_key(r)
    before = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    after = [[0.05, 0.0], [-0.05, 0.0], [0.0, 0.0]]
    group_name = 'TEST|intraday|legacy'
    e = {'kind':'learn_after_score','prediction_id':r['id'],
         'event_key':k,'available_at':o['evaluated_at'],
         'learned_at':'2026-10-29T14:36:00Z','group':group_name,
         'actual':'down','weights_before':digest(before),'weights_after':digest(after),
         'not_rescored':True,'id':digest({'version':VERSION,'trained_event':k})}
    state = {'trained_events':[k],'training_updates':1,
             'last_outcome_available_at':o['evaluated_at'],
             'groups':{group_name:{'weights':after,'learned':1,
                                   'last_train_end':r['target']['end']}}}
    return [r], [o], [d], [e], state, ts('2026-10-29T15:00:00Z')


class Tests(unittest.TestCase):
    def test_baseline_three_stream_audit_does_not_consider_learning(self):
        r,o,d,e,s,t = synthetic()
        self.assertEqual(audit(r,o,d,t)['status'], 'ledger_arithmetic_consistent')
        self.assertEqual(audit(r,o,d,t)['scored'], 1)
        # Corrupt the independent learning stream while keeping the old three
        # input streams identical. Baseline still passes; new gate rejects replay.
        duplicate=e+e
        self.assertEqual(audit(r,o,d,t)['status'], 'ledger_arithmetic_consistent')
        self.assertEqual(examine(r,o,d,duplicate,s,t)['status'], 'integrity_errors')

    def test_reference_passes(self):
        self.assertEqual(examine(*synthetic())['status'], 'learning_evidence_consistent')

    def test_duplicate_learning_event_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,d,e+e,s,t)['status'], 'integrity_errors')

    def test_wrong_actual_label_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,d,[{**e[0],'actual':'up'}],s,t)['status'], 'integrity_errors')

    def test_learning_before_label_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,d,[{**e[0],'learned_at':'2026-10-29T14:34:00Z'}],s,t)['status'], 'integrity_errors')

    def test_unknown_forecast_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,d,[{**e[0],'prediction_id':'unknown'}],s,t)['status'], 'integrity_errors')

    def test_corrupt_fingerprint_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,d,[{**e[0],'event_key':'0'*64}],s,t)['status'], 'integrity_errors')

    def test_state_out_of_sync_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,d,e,{**s,'trained_events':[]},t)['status'], 'integrity_errors')

    def test_missing_publication_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,[],e,s,t)['status'], 'integrity_errors')

    def test_untrained_group_zero_weights_baseline_and_forgery_rejected(self):
        # A group with no learning events must retain the exact initial
        # all-zero correction, even though no terminal event SHA exists.
        r, o, d, e, s, t = synthetic()
        name = 'UNTRAINED|daily|provider-latency-30m-v1'
        s['groups'][name] = {'weights': [[0.0] * 13 for _ in range(3)],
                             'learned': 0, 'active': 'incumbent',
                             'last_train_end': None}
        self.assertEqual(examine(r, o, d, e, s, t)['status'],
                         'learning_evidence_consistent')
        s['groups'][name]['weights'][0][0] = 0.125
        result = examine(r, o, d, e, s, t)
        self.assertEqual(result['status'], 'integrity_errors')
        self.assertIn('untrained_group_weights_not_zero',
                      [item['error'] for item in result['errors']])

    def test_terminal_weight_hash_forgery_rejected(self):
        # Research-only negative fixture: valid-looking hash differs from the saved state.
        # Prior independent gate accepts this, demonstrating the coverage gap.
        r,o,d,e,s,t=synthetic()
        forged=[{**e[0], 'weights_after':'c'*64}]
        self.assertEqual(examine(r,o,d,forged,s,t)['status'], 'integrity_errors')

    def test_saved_learning_count_forgery_rejected(self):
        r,o,d,e,s,t=synthetic()
        name=e[0]['group']
        s['groups'][name]['learned']=2
        self.assertEqual(examine(r,o,d,e,s,t)['status'], 'integrity_errors')

    def test_terminal_saved_weights_tamper_rejected(self):
        r,o,d,e,s,t=synthetic()
        name=e[0]['group']
        s['groups'][name]['weights'][0][0] += 0.01
        self.assertEqual(examine(r,o,d,e,s,t)['status'], 'integrity_errors')

    def test_two_updates_link_with_saved_terminal_weights(self):
        # Both events are prospective and the second begins after the first
        # target ends. A changed but SHA-shaped intermediate hash must fail.
        r,o,d,e,s,_=synthetic()
        next_r={**r[0], 'id':'synthetic-next',
                'observed_until':'2026-10-29T14:30:00Z',
                'received_at':'2026-10-29T14:32:00Z',
                'issued_at':'2026-10-29T14:38:00Z',
                'target':{'start':'2026-10-29T15:00:00Z',
                          'end':'2026-10-29T15:30:00Z'}}
        next_o={**o[0], 'id':next_r['id'], 'target':next_r['target'],
                'evaluated_at':'2026-10-29T15:35:00Z'}
        next_delivery={**d[0],
                       'snapshot_generated_at':'2026-10-29T14:39:00Z',
                       'verified_at':'2026-10-29T14:40:00Z',
                       'prediction_ids':[next_r['id']]}
        key2=forecast_key(next_r)
        next_weights=[[0.06,0.0],[-0.06,0.0],[0.0,0.0]]
        next_event={**e[0], 'prediction_id':next_r['id'],
                    'event_key':key2,
                    'available_at':next_o['evaluated_at'],
                    'learned_at':'2026-10-29T15:36:00Z',
                    'weights_before':e[0]['weights_after'],
                    'weights_after':digest(next_weights),
                    'id':digest({'version':VERSION,'trained_event':key2})}
        name=e[0]['group']
        s['groups'][name].update(weights=next_weights,learned=2,
                                 last_train_end=next_r['target']['end'])
        s['trained_events']=sorted([e[0]['event_key'],key2])
        s['training_updates']=2
        s['last_outcome_available_at']=next_o['evaluated_at']
        inputs=(r+[next_r],o+[next_o],d+[next_delivery])
        cutoff=ts('2026-10-29T16:00:00Z')
        self.assertEqual(examine(*inputs,e+[next_event],s,cutoff)['status'],
                         'learning_evidence_consistent')
        forged={**next_event,'weights_before':'f'*64}
        bad=examine(*inputs,e+[forged],s,cutoff)
        self.assertEqual(bad['status'],'integrity_errors')
        self.assertIn('learning_weight_hash_chain_broken',
                      [x['error'] for x in bad['errors']])

    def test_unknown_learning_group_is_not_accepted(self):
        r,o,d,e,s,t=synthetic()
        s['groups']={}
        self.assertEqual(examine(r,o,d,e,s,t)['status'], 'integrity_errors')

    def test_future_learning_rejected(self):
        r,o,d,e,s,t=synthetic()
        self.assertEqual(examine(r,o,d,[{**e[0],'learned_at':'2026-10-29T15:01:00Z'}],s,t)['status'], 'integrity_errors')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path('stock-forecast-learning-evidence.json'))
    parser.add_argument('--cutoff')
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:
        result=unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        raise SystemExit(0 if result.wasSuccessful() else 1)
    source=args.root
    state=json.loads((source/'stock-forecast-learning-state.json').read_text())
    result=examine(read_lines(source/'stock-forecast-ledger.jsonl'),
                   read_lines(source/'stock-forecast-outcomes.jsonl'),
                   read_lines(source/'stock-forecast-deliveries.jsonl'),
                   read_lines(source/'stock-forecast-learning-events.jsonl'),
                   state,ts(args.cutoff) if args.cutoff else datetime.now(timezone.utc))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','learning_event_rows','learning_updates_recorded','frozen_scored_results','frozen_correct_results','errors')},ensure_ascii=False))
    raise SystemExit(1 if result['status']!='learning_evidence_consistent' else 0)
