"""Synthetic unit fixtures only. Never used to publish real forecasts."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest
import numpy as np
import pandas as pd
import stock_forecast_directions as d
import stock_forecast_learning as l
import stock_forecast_model as b

NOW = datetime(2026,10,29,8,tzinfo=timezone.utc)

def fixture(i=0, actual='down', candidate=None, old=None):
    start = pd.Timestamp('2026-09-01T00:30:00Z')+pd.Timedelta(days=i//3, minutes=40*(i%3))
    end = start+pd.Timedelta(minutes=30)
    old = old or {'down':.25,'flat':.5,'up':.25}
    candidate = candidate or {'down':.65,'flat':.2,'up':.15}
    r = {'id':str(i),'symbol':'SYNTHETIC','market':'KR','mode':'intraday',
         'policy_revision':'test-only','status':'research_prediction','target':{'start':start.isoformat(),'end':end.isoformat()},
         'issued_at':(start-pd.Timedelta(minutes=5)).isoformat(),
         'received_at':(start-pd.Timedelta(minutes=6)).isoformat(),
         'observed_until':(start-pd.Timedelta(minutes=7)).isoformat(),
         'neutral_band_pct':.2,'probabilities':old,'direction':b.CLASSES[int(l.probability(old).argmax())],
         'feature_values':{k:0.01 for k in b.FEATURES},'model_sha256':'test-model',
         'online_learning':{'version':l.VERSION,'incumbent_probabilities':old,'challenger_probabilities':candidate},
         'directional_specialists':{'version':d.VERSION,'candidates':{k:{'probabilities':candidate} for k in d.SPECIALISTS}}}
    close = 101 if actual=='up' else 99 if actual=='down' else 100
    o = {'id':r['id'],'status':'observed','actual':actual,'target':r['target'],
         'target_open':100.,'target_close':close,'evaluated_at':(end+pd.Timedelta(minutes=1)).isoformat()}
    return r,o

def prices(n=700):
    rng=np.random.default_rng(77)
    sessions=pd.bdate_range('2021-01-04',periods=n)
    changes=rng.normal(0,.012,n)
    opens=100*np.exp(np.cumsum(rng.normal(0,.005,n)))
    closes=opens*np.exp(changes)
    return pd.DataFrame({'open':opens,'close':closes,'high':np.maximum(opens,closes)*1.003,
                         'low':np.minimum(opens,closes)*.997,
                         'start':pd.to_datetime(sessions,utc=True),
                         'end':pd.to_datetime(sessions,utc=True)+pd.Timedelta(hours=6),
                         'session':sessions.strftime('%Y-%m-%d')})

class DirectionMetricsTests(unittest.TestCase):
    def test_flat_collapse_is_not_direction_skill(self):
        m=d.metrics([0,0,0,1,1,1], np.tile([.2,.6,.2],(6,1)))
        self.assertEqual(m['accuracy'],.5)
        self.assertEqual(m['directions']['down']['missed'],3)
        self.assertEqual(m['directions']['down']['recall'],0)
        self.assertIsNone(m['directions']['up']['recall'])
        self.assertIsNone(m['directions']['down']['precision'])
        self.assertTrue(m['single_class_collapse'])
    def test_no_observations_not_100_percent(self):
        m=d.metrics([],np.empty((0,3)))
        self.assertIsNone(m['accuracy']);self.assertIsNone(m['balanced_accuracy'])
    def test_false_direction_calls_are_counted(self):
        m=d.metrics([0,1,2],np.tile([.8,.1,.1],(3,1)))
        self.assertEqual(m['directions']['down']['false_calls'],2)
        self.assertAlmostEqual(m['directions']['down']['precision'],1/3)
        self.assertAlmostEqual(m['balanced_accuracy'],1/3)
    def test_bad_probabilities_rejected(self):
        for p in ([[.1,.1,.1]], [[-.2,.7,.5]], [[np.nan,0,1]],[[0,0,2]]):
            with self.subTest(p=p),self.assertRaises(ValueError):d.metrics([0],p)
    def test_missing_direction_never_passes_gate(self):
        m=d.metrics([0]*20+[1]*20,np.tile([.6,.3,.1],(40,1)))
        self.assertIn('insufficient_actual_up',d.direction_guard(m,m))
    def test_only_down_improvement_is_not_enough(self):
        y=np.tile([0,1,2],30);base=np.tile([.2,.6,.2],(90,1))
        cand=base.copy();cand[y==0]=[.8,.1,.1]
        reasons=d.direction_guard(d.metrics(y,base),d.metrics(y,cand))
        self.assertIn('recall_not_improved_up',reasons)
    def test_correct_both_directions_can_pass_policy(self):
        y=np.tile([0,1,2],30);old=np.tile([.2,.6,.2],(90,1))
        new=np.eye(3)[y]*.7+.1
        self.assertEqual(d.direction_guard(d.metrics(y,old),d.metrics(y,new)),[])
    def test_true_label_cannot_change_candidate(self):
        r,o=fixture();orig=deepcopy(r)
        o['actual']='up'
        self.assertEqual(r,orig)

class DirectionStateTests(unittest.TestCase):
    def test_legacy_records_are_not_backfilled(self):
        r,o=fixture();r.pop('directional_specialists')
        state=l.blank_state();self.assertEqual(d.select_variants(state,[(r,o)],NOW),[])
        self.assertNotIn('balanced_linear',d.variants(r))
    def test_six_cases_cannot_promote(self):
        pairs=[fixture(i) for i in range(6)]
        state=l.blank_state();self.assertEqual(d.select_variants(state,pairs,NOW),[])
    def test_future_answer_cannot_promote(self):
        pairs=[fixture(i,actual=b.CLASSES[i%3],candidate={k:.8 if j==i%3 else .1 for j,k in enumerate(b.CLASSES)}) for i in range(120)]
        for r,o in pairs:o['evaluated_at']=(pd.Timestamp(NOW)+pd.Timedelta(days=10)).isoformat()
        self.assertEqual(d.select_variants(l.blank_state(),pairs,NOW),[])
    def test_no_forced_up_or_down_output(self):
        r,o=fixture(old={'down':.32,'flat':.36,'up':.32})
        state=l.blank_state();new=d.apply_variant(r,state)
        self.assertEqual(new['direction'],'flat')
        self.assertTrue(new['directional_signal']['uncertain'])
        self.assertTrue(new['directional_signal']['all_original_predictions_still_scored'])
    def test_no_call_is_never_rewritten_as_flat(self):
        r={'status':'no_call'}
        self.assertIs(d.apply_variant(r,l.blank_state()),r)
    def test_shadow_keeps_incumbent_and_preserves_record(self):
        r,o=fixture();before=deepcopy(r);new=d.apply_variant(r,l.blank_state())
        self.assertEqual(new['probabilities'],r['probabilities']);self.assertEqual(r,before)
        self.assertFalse(new['directional_selection']['orders_enabled'])
    def test_unavailable_active_candidate_falls_back(self):
        r,o=fixture();r.pop('directional_specialists');state=l.blank_state()
        l.ensure(state,r)['directional_active']='balanced_linear'
        new=d.apply_variant(r,state)
        self.assertEqual(new['directional_selection']['active'],'incumbent')
        self.assertEqual(new['directional_selection']['fallback_reason'],'active_specialist_unavailable')
    def test_active_candidate_does_not_inherit_old_score(self):
        r,o=fixture();state=l.blank_state();l.ensure(state,r)['directional_active']='balanced_linear'
        r['validation']={'accuracy':1.0,'test_samples':1000}
        new=d.apply_variant(r,state)
        self.assertEqual(new['validation']['test_samples'],0)
        self.assertEqual(new['incumbent_historical_validation']['accuracy'],1.)
    def test_strong_forward_fixture_promotes_without_green(self):
        pairs=[fixture(i,actual=b.CLASSES[i%3],candidate={k:.8 if j==i%3 else .1 for j,k in enumerate(b.CLASSES)}) for i in range(120)]
        state=l.blank_state();events=d.select_variants(state,pairs,NOW)
        self.assertEqual(len(events),1);self.assertEqual(events[0]['kind'],'directional_research_promotion')
        self.assertFalse(events[0]['strict_green_override']);self.assertFalse(events[0]['orders_enabled'])
        self.assertEqual(d.select_variants(state,pairs,NOW),[])
    def test_all_flat_candidate_never_promotes(self):
        pairs=[fixture(i,actual=b.CLASSES[i%3],candidate={'down':.05,'flat':.9,'up':.05}) for i in range(120)]
        events=d.select_variants(l.blank_state(),pairs,NOW)
        self.assertEqual(events[0]['kind'],'directional_checkpoint_no_change')
    def test_new_audit_does_not_change_old_results(self):
        r,o=fixture();before=deepcopy((r,o));delivery={'status':'public_verified','prediction_ids':[r['id']],
           'verified_at':(pd.Timestamp(r['issued_at'])+pd.Timedelta(seconds=5)).isoformat()}
        report=d.report([r],[o],[delivery],[],l.blank_state(),NOW)
        self.assertEqual((r,o),before);self.assertEqual(report['actual_direction_quality']['directions']['down']['missed'],1)

class FeatureTests(unittest.TestCase):
    def test_appending_future_cannot_modify_past(self):
        bars=prices();old=d.expanded_features(bars.iloc[:550].copy(),'daily')
        full=d.expanded_features(bars,'daily').iloc[:550]
        np.testing.assert_allclose(old.to_numpy(),full.to_numpy(),equal_nan=True)
    def test_future_mutation_cannot_modify_past(self):
        bars=prices();old=d.expanded_features(bars,'daily');changed=bars.copy()
        changed.loc[550:,['open','high','low','close']]*=1.2
        new=d.expanded_features(changed,'daily')
        np.testing.assert_allclose(old.iloc[:550],new.iloc[:550],equal_nan=True)
    def test_session_high_resets(self):
        bars=prices(50);x=d.expanded_features(bars,'daily')
        np.testing.assert_allclose(x.session_drawdown,bars.close/bars.high-1)
    def test_model_has_disjoint_periods_and_coherent_probabilities(self):
        bars=prices();fitted=b.fit_model(bars,'daily');suite=d.fit(bars,'daily',fitted)
        self.assertLess(suite['train_end'],suite['calibration_end']);self.assertLess(suite['calibration_end'],suite['test_start'])
        self.assertEqual(set(suite['candidates']),set(d.SPECIALISTS))
        for c in suite['candidates'].values():
            self.assertAlmostEqual(sum(c['probabilities'].values()),1)
            self.assertFalse(c['historical_test_used_for_promotion'])
            self.assertFalse(c['recommendation'])
    def test_test_tail_does_not_change_fitted_weights(self):
        bars=prices();one=d.fit(bars,'daily',b.fit_model(bars,'daily'))
        changed=bars.copy();changed.loc[600:,'close']*=1.001
        changed.loc[600:,'high']=np.maximum(changed.loc[600:,'high'],changed.loc[600:,'close']*1.001)
        two=d.fit(changed,'daily',b.fit_model(changed,'daily'))
        for k in d.SPECIALISTS:self.assertEqual(one['candidates'][k]['model_sha256'],two['candidates'][k]['model_sha256'])

if __name__=='__main__':unittest.main()
