"""Synthetic fixtures only; production predictions always use real collected OHLC."""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import stock_forecast_autopilot as a
from stock_forecast_cascade import MovementThenDirection, RECIPE
import stock_forecast_directions as d
import stock_forecast_learning as l

NOW=datetime(2026,10,29,11,tzinfo=timezone.utc)
SPEC=('TEST','Synthetic','US')

def failure(reason):
    return {'status':'no_call','reason':reason,'symbol':'TEST','market':'US','mode':'daily','name':'Synthetic'},None

def successful():
    return {'status':'no_call','reason':'insufficient_regular_session_time','symbol':'TEST',
            'market':'US','mode':'daily','observed_until':NOW.isoformat(),'received_at':NOW.isoformat()},object()

class SourceTests(unittest.TestCase):
    def test_known_transient_is_retried_once(self):
        calls=[]
        def process(*_):
            calls.append(1)
            return failure('ConnectionError: test') if len(calls)==1 else successful()
        c=a.SafeCollector(process,{'cooldowns':{}},clock=lambda:NOW,sleep=lambda _:None)
        self.assertIsNotNone(c(SPEC,'daily')[1]);self.assertEqual(len(calls),2)
    def test_retry_budget_is_finite(self):
        calls=[]
        def process(*_): calls.append(1);return failure('TimeoutError: test')
        c=a.SafeCollector(process,{},clock=lambda:NOW,sleep=lambda _:None)
        self.assertIsNone(c(SPEC,'daily')[1]);self.assertEqual(len(calls),2)
    def test_rate_limit_sets_cooldown_without_hammering(self):
        calls=[];state={}
        def process(*_): calls.append(1);return failure('YFRateLimitError: test')
        c=a.SafeCollector(process,state,clock=lambda:NOW,sleep=lambda _:None)
        c(SPEC,'daily');c(SPEC,'daily')
        self.assertEqual(len(calls),1);self.assertEqual(c.events[-1]['attempt'],0)
        self.assertGreater(a.ts(state['cooldowns']['TEST|daily']),NOW)
    def test_cooldown_expires(self):
        state={'cooldowns':{'TEST|daily':(NOW-timedelta(seconds=1)).isoformat()}}
        c=a.SafeCollector(lambda *_:successful(),state,clock=lambda:NOW)
        self.assertIsNotNone(c(SPEC,'daily')[1]);self.assertNotIn('TEST|daily',state['cooldowns'])
    def test_structural_error_is_not_retried(self):
        calls=[]
        def process(*_): calls.append(1);return failure('ValueError: invalid price')
        c=a.SafeCollector(process,{},clock=lambda:NOW,sleep=lambda _:None)
        c(SPEC,'daily');self.assertEqual(len(calls),1)
    def test_session_wait_is_not_collection_failure(self):
        self.assertIsNone(a.source_failure(successful()[0]))
    def test_old_quote_never_substituted(self):
        c=a.SafeCollector(lambda *_:failure('YFRateLimitError: test'),{},clock=lambda:NOW)
        r,bars=c(SPEC,'daily')
        self.assertIsNone(bars);self.assertNotIn('price',r)
    def test_lock_recovers_but_unknown_error_does_not(self):
        self.assertEqual(a.source_failure(failure('OperationalError: database is locked')[0]),'cache_lock')
        self.assertEqual(a.source_failure(failure('RuntimeError: model')[0]),'nontransient')

class EvidenceTests(unittest.TestCase):
    def test_append_is_allowed(self): a.preserve_records([{'id':'a','v':1}],[{'id':'a','v':1},{'id':'b','v':2}])
    def test_deletion_is_rejected(self):
        with self.assertRaises(ValueError):a.preserve_records([{'id':'a'}],[])
    def test_answer_rewrite_is_rejected(self):
        with self.assertRaises(ValueError):a.preserve_records([{'id':'a','correct':False}],[{'id':'a','correct':True}])
    def test_conflicting_id_is_rejected(self):
        with self.assertRaises(ValueError):a.preserve_records([],[{'id':'a','x':0},{'id':'a','x':1}])
    def test_manifest_once(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'m.jsonl';r={'id':'recipe','recipe':RECIPE}
            self.assertTrue(a.append_once(p,r));self.assertFalse(a.append_once(p,r));self.assertEqual(len(a.lines(p)),1)
    def test_collapse_and_missing_class_are_visible(self):
        q={'single_class_collapse':True,'directions':{'down':{'actual':3,'recall':0},'up':{'actual':0}}}
        reasons=a.diagnose({'directional_research':{'actual_direction_quality':q}},[])
        self.assertIn('single_direction_collapse',reasons);self.assertIn('missed_down_moves',reasons)
        self.assertIn('no_forward_up_samples',reasons)
    def test_rejected_transaction_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'stock-forecast-ledger.jsonl';p.write_text('{"id":"old","correct":false}\n')
            before=p.read_bytes()
            def broken(root,processor):
                (root/'stock-forecast-ledger.jsonl').write_text('corrupt')
                raise ValueError('synthetic injected failure')
            with self.assertRaises(ValueError):a.run(root,pipeline=broken,clock=lambda:NOW)
            self.assertEqual(p.read_bytes(),before)
            self.assertEqual(a.read(root,a.REPORT,{})['status'],'cycle_rejected')
    def test_successful_transaction_checks_real_audit_contract(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            def engine(root,processor):
                processor(SPEC,'daily')
                for name in a.CORE_OUTPUTS:
                    if name.endswith('.jsonl'):(root/name).touch()
                a.write(root/'stock-forecast-learning-state.json',l.blank_state())
                a.write(root/'stock-forecast-learning.json',{'overall':{'samples':0,'correct':0},'learning':{'training_updates':0}})
                a.write(root/'stock-direction-forecast.json',{'records':[]})
                return {'records':[]}
            with patch('run_stock_forecasts.process',lambda *_:successful()):
                report=a.run(root,pipeline=engine,clock=lambda:NOW)
            self.assertEqual(report['status'],'research_cycle_verified')
            self.assertFalse(report['perfect_prediction_proven'])
            self.assertFalse(report['orders_enabled'])
            self.assertEqual(report['timing_utility']['status'],'not_proven')
            self.assertEqual(report['new_learning_updates'],0)
    def test_all_failed_collectors_cannot_publish_new_success(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            def engine(root,processor):
                processor(SPEC,'daily')
                for name in a.CORE_OUTPUTS:
                    if name.endswith('.jsonl'):(root/name).touch()
                a.write(root/'stock-forecast-learning-state.json',l.blank_state())
                a.write(root/'stock-forecast-learning.json',{'overall':{'samples':0,'correct':0},'learning':{'training_updates':0}})
                a.write(root/'stock-direction-forecast.json',{'records':[]})
            with patch('run_stock_forecasts.process',lambda *_:failure('YFRateLimitError: test')):
                with self.assertRaises(RuntimeError):a.run(root,pipeline=engine,clock=lambda:NOW)
            self.assertFalse((root/'stock-direction-forecast.json').exists())
    def test_unauthorized_learning_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);stage=root/'stage';stage.mkdir();s=l.blank_state()
            s.update(trained_events=['unavailable-answer'],training_updates=1)
            a.write(stage/'stock-forecast-learning-state.json',s)
            with self.assertRaises(ValueError):a.verify_stage(root,stage,NOW)

class CascadeTests(unittest.TestCase):
    def data(self):
        rng=np.random.default_rng(9029);X=rng.normal(size=(150,6));y=np.tile([0,1,2],50)
        return X,y
    def test_probabilities_and_class_order(self):
        X,y=self.data();m=MovementThenDirection().fit(X,y);p=m.predict_proba(X[:10])
        np.testing.assert_allclose(p.sum(axis=1),1)
        self.assertTrue((p>=0).all());self.assertEqual(m.classes_.tolist(),[0,1,2])
    def test_missing_direction_not_fabricated(self):
        X,y=self.data()
        with self.assertRaises(ValueError):MovementThenDirection().fit(X[y!=0],y[y!=0])
    def test_bad_features_block(self):
        X,y=self.data();m=MovementThenDirection().fit(X,y);X[0,0]=np.nan
        with self.assertRaises(ValueError):m.predict_proba(X[:1])
    def test_future_rows_do_not_change_trained_parameters(self):
        X,y=self.data();m=MovementThenDirection().fit(X[:120],y[:120]);p=m.predict_proba(X[:4])
        X[120:]+=100
        np.testing.assert_allclose(p,m.predict_proba(X[:4]))
    def test_catalogue_is_bounded_and_correction_is_tightened(self):
        self.assertIn('movement_then_direction',d.SPECIALISTS)
        self.assertEqual(len(d.VARIANTS),4)
        self.assertLessEqual(d.POLICY['three_challenger_interval_tail'],.05/8)
        self.assertEqual(a.POLICY['maximum_new_recipe_families'],1)
    def test_no_trading_or_unrestricted_source_rewrite(self):
        self.assertFalse(a.POLICY['arbitrary_source_rewrite']);self.assertFalse(a.POLICY['live_orders'])


class StagedLearningGateTests(unittest.TestCase):
    def test_corrupt_staged_weight_must_block_publication(self):
        """Synthetic-only fault: internally valid outcomes but disconnected saved weights."""
        import json
        from audit_stock_learning_evidence import synthetic
        records, outcomes, deliveries, events, state, cutoff = synthetic()
        deliveries[0]['verification_id'] = 'synthetic-public-proof'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / 'stage'
            stage.mkdir()
            for name, rows in (
                ('stock-forecast-ledger.jsonl', records),
                ('stock-forecast-outcomes.jsonl', outcomes),
                ('stock-forecast-deliveries.jsonl', deliveries),
                ('stock-forecast-learning-events.jsonl', events),
            ):
                (stage / name).write_text(''.join(
                    json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
            a.write(stage / 'stock-forecast-learning-state.json', state)
            a.write(stage / 'stock-forecast-learning.json',
                    {'overall': {'samples': 1, 'correct': 0, 'accuracy': 0.0,
                                 'brier_loss': 1.04, 'balanced_accuracy': None,
                                 'recall': {'down': 0.0, 'flat': None, 'up': None},
                                 'confusion_matrix': [[0, 1, 0], [0, 0, 0], [0, 0, 0]]},
                     'learning': {'training_updates': 1}})
            a.write(stage / 'stock-direction-forecast.json', {'records': []})
            self.assertEqual(a.verify_stage(root, stage, cutoff)['scored'], 1)
            group = events[0]['group']
            state['groups'][group]['weights'][0][0] += 0.125
            a.write(stage / 'stock-forecast-learning-state.json', state)
            with self.assertRaisesRegex(ValueError, 'staged_learning_evidence_rejected'):
                a.verify_stage(root, stage, cutoff)


    def test_direction_summary_forgery_must_block_publication(self):
        """Synthetic-only: a staged report cannot invent directional recall."""
        import json
        from copy import deepcopy
        from audit_stock_learning_evidence import synthetic
        records, outcomes, deliveries, events, state, cutoff = synthetic()
        deliveries[0]['verification_id'] = 'synthetic-public-proof'
        valid = {'samples': 1, 'correct': 0, 'accuracy': 0.0,
                 'brier_loss': 1.04, 'balanced_accuracy': None,
                 'recall': {'down': 0.0, 'flat': None, 'up': None},
                 'confusion_matrix': [[0, 1, 0], [0, 0, 0], [0, 0, 0]]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / 'stage'
            stage.mkdir()
            for name, rows in (
                ('stock-forecast-ledger.jsonl', records),
                ('stock-forecast-outcomes.jsonl', outcomes),
                ('stock-forecast-deliveries.jsonl', deliveries),
                ('stock-forecast-learning-events.jsonl', events),
            ):
                (stage / name).write_text(''.join(
                    json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
            a.write(stage / 'stock-forecast-learning-state.json', state)
            a.write(stage / 'stock-direction-forecast.json', {'records': []})
            report = {'overall': valid, 'learning': {'training_updates': 1}}
            a.write(stage / 'stock-forecast-learning.json', report)
            self.assertEqual(a.verify_stage(root, stage, cutoff)['scored'], 1)
            mutations = {
                'accuracy': 0.98,
                'brier_loss': 0.01,
                'recall': {'down': 1.0, 'flat': None, 'up': None},
                'confusion_matrix': [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
            }
            for field, forged in mutations.items():
                with self.subTest(tampered_field=field):
                    corrupted = deepcopy(report)
                    corrupted['overall'] = deepcopy(valid)
                    corrupted['overall'][field] = forged
                    a.write(stage / 'stock-forecast-learning.json', corrupted)
                    with self.assertRaisesRegex(ValueError, 'staged_score_summary_mismatch'):
                        a.verify_stage(root, stage, cutoff)

if __name__=='__main__':unittest.main()
