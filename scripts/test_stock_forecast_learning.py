"""Synthetic fixtures only. Never persisted as production predictions/approvals."""
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import numpy as np
import pandas as pd
import stock_forecast_learning as L

NOW=pd.Timestamp('2026-10-30T12:00:00Z')

def fixture(start='2026-10-29T01:00:00Z',actual='up',p=None,rid=None):
    s=pd.Timestamp(start);end=s+pd.Timedelta(minutes=30)
    p=p or {'down':.2,'flat':.3,'up':.5}
    r={'id':rid or str(s),'symbol':'TEST_ONLY','market':'KR','mode':'intraday',
       'policy_revision':'synthetic-v1','status':'research_prediction',
       'probabilities':p,'direction':L.CLASSES[int(np.argmax([p[k] for k in L.CLASSES]))],
       'observed_until':(s-pd.Timedelta(minutes=30)).isoformat(),
       'received_at':(s-pd.Timedelta(minutes=20)).isoformat(),
       'issued_at':(s-pd.Timedelta(minutes=10)).isoformat(),
       'target':{'start':s.isoformat(),'end':end.isoformat()},'neutral_band_pct':.2,
       'feature_values':{k:.001 for k in L.FEATURES},'model_sha256':'test-only'}
    price={'up':101,'flat':100,'down':99}[actual]
    o={'id':r['id'],'status':'observed','actual':actual,'target_open':100,'target_close':price,
       'target':r['target'],'evaluated_at':(end+pd.Timedelta(minutes=15)).isoformat()}
    d={'status':'public_verified','verified_at':(s-pd.Timedelta(minutes=5)).isoformat(),
       'prediction_ids':[r['id']]}
    return r,o,d


def many(n=120,start='2026-01-01',good=True):
    pairs=[]
    for i in range(n):
        day=pd.Timestamp(start,tz='UTC')+pd.Timedelta(days=i//6,hours=1,minutes=(i%6)*40)
        y=L.CLASSES[i%3];r,o,d=fixture(day,actual=y)
        a={'down':.34,'flat':.33,'up':.33}
        b={k:.1 for k in L.CLASSES};b[y]=.8
        if not good:a,b=b,a
        r['online_learning']={'version':L.VERSION,'incumbent_probabilities':a,'challenger_probabilities':b}
        pairs.append((r,o))
    return pairs

class EvaluationTests(unittest.TestCase):
    def test_valid_contract(self): self.assertTrue(L.contract(fixture()[0]))
    def test_no_call_is_not_flat(self):
        r,o,d=fixture();r['status']='no_call';self.assertFalse(L.contract(r))
    def test_future_information_rejected(self):
        r,o,d=fixture();r['received_at']=r['target']['start'];self.assertFalse(L.contract(r))
    def test_direction_must_match_argmax(self):
        r,o,d=fixture();r['direction']='down';self.assertFalse(L.contract(r))
    def test_invalid_probabilities(self):
        for p in [{'up':1},{'up':True,'down':0,'flat':0},{'up':.7,'down':.7,'flat':0}, {'up':float('nan'),'down':0,'flat':0}]:
            with self.assertRaises((TypeError,ValueError)):L.probability(p)
    def test_pending_not_success(self):
        r,o,d=fixture();p,c=L.joined([r],[o],[d],pd.Timestamp(r['target']['start']));self.assertEqual(p,[]);self.assertEqual(c['pending_targets'],1)
    def test_missing_outcome_not_success(self):
        r,o,d=fixture();p,c=L.joined([r],[],[d],NOW);self.assertEqual(c['outcome_missing'],1)
    def test_absent_delivery_not_success(self):
        r,o,d=fixture();p,c=L.joined([r],[o],[],NOW);self.assertEqual(c['not_publicly_timely'],1)
    def test_late_delivery_not_success(self):
        r,o,d=fixture();d['verified_at']=r['target']['start'];p,c=L.joined([r],[o],[d],NOW);self.assertFalse(p)
    def test_outcome_cannot_be_known_before_end(self):
        r,o,d=fixture();o['evaluated_at']=r['issued_at'];p,c=L.joined([r],[o],[d],NOW);self.assertEqual(c['invalid_outcome_time'],1)
    def test_outcome_cannot_be_from_future(self):
        r,o,d=fixture();o['evaluated_at']=(NOW+pd.Timedelta(days=1)).isoformat();self.assertFalse(L.joined([r],[o],[d],NOW)[0])
    def test_mismatched_actual_rejected(self):
        r,o,d=fixture();o['actual']='down';p,c=L.joined([r],[o],[d],NOW);self.assertEqual(c['invalid_outcome_value'],1)
    def test_first_wrong_call_not_replaced_with_later_correct_call(self):
        r,o,d=fixture(p={'down':.8,'flat':.1,'up':.1},rid='first')
        r2,o2,d2=fixture(rid='second');r2['issued_at']=(pd.Timestamp(r['issued_at'])+pd.Timedelta(minutes=1)).isoformat()
        pairs,counts=L.joined([r2,r],[o2,o],[d2,d],NOW)
        self.assertEqual(L.statistics(pairs)['accuracy'],0);self.assertEqual(counts['duplicate_issuances'],1)
    def test_nonoverlap_selection_ignores_truth(self):
        records=[fixture('2026-10-29T01:00:00Z')[0],fixture('2026-10-29T01:15:00Z')[0],fixture('2026-10-29T01:30:00Z')[0]]
        chosen,stats=L.canonical(records);self.assertEqual(len(chosen),2);self.assertEqual(stats['overlap_excluded'],1)
    def test_one_correct_is_not_near_certain_skill(self):
        r,o,d=fixture();s=L.statistics([(r,o)]);self.assertEqual(s['accuracy'],1);self.assertLess(s['wilson_95_interval'][0],.3)
    def test_high_confidence_coverage_not_hidden(self):
        r,o,d=fixture();s=L.statistics([(r,o)]);self.assertEqual(s['high_confidence']['coverage'],0);self.assertIsNone(s['high_confidence']['accuracy'])
    def test_legacy_baseline_is_not_invented(self):
        r,o,d=fixture();report=L.report([r],[o],[d],[],L.blank_state(),[],NOW);self.assertEqual(report['baseline_paired']['samples'],0)
    def test_abstentions_count_in_attempt_rate(self):
        a=[{'version':L.VERSION,'status':'no_call','reason':'missing'},{'version':L.VERSION,'status':'research_prediction'}]
        s=L.report([],[],[],a,L.blank_state(),[],NOW);self.assertEqual(s['coverage']['call_rate'],.5);self.assertEqual(s['overall']['samples'],0)
    def test_same_event_ignores_model_change(self):
        r,o,d=fixture();b=deepcopy(r);b['model_sha256']='new';self.assertEqual(L.key(r),L.key(b))

class LearningTests(unittest.TestCase):
    def test_learning_changes_future_challenger_not_old_prediction(self):
        r,o,d=fixture();old=deepcopy(r);s=L.blank_state();events=L.learn(s,[(r,o)],NOW)
        self.assertEqual(len(events),1);self.assertEqual(r,old);self.assertEqual(s['training_updates'],1)
        self.assertNotEqual(L.ensure(s,r)['weights'],np.zeros((3,13)).tolist())
    def test_duplicate_feedback_learned_once(self):
        r,o,d=fixture();s=L.blank_state();L.learn(s,[(r,o)],NOW);self.assertEqual(L.learn(s,[(r,o)],NOW),[])
    def test_future_label_cannot_update(self):
        r,o,d=fixture();o['evaluated_at']=(NOW+pd.Timedelta(days=1)).isoformat();s=L.blank_state();L.learn(s,[(r,o)],NOW);self.assertEqual(s['training_updates'],0)
    def test_missing_features_do_not_train(self):
        r,o,d=fixture();r.pop('feature_values');s=L.blank_state();self.assertEqual(L.learn(s,[(r,o)],NOW),[])
    def test_overlap_not_double_learned(self):
        r,o,d=fixture();r2,o2,d2=fixture('2026-10-29T01:15:00Z');s=L.blank_state();self.assertEqual(len(L.learn(s,[(r,o),(r2,o2)],NOW)),1)
    def test_zero_adjustment_matches_incumbent(self):
        p=np.array([.2,.3,.5]);q=L.adaptive(p,np.ones(13),np.zeros((3,13)));np.testing.assert_allclose(p,q)
    def test_insufficient_forward_samples_cannot_promote(self):
        s=L.blank_state();self.assertEqual(L.select_variant(s,many(20),NOW),[])
    def test_enough_good_paired_data_can_promote_research_only(self):
        s=L.blank_state();events=L.select_variant(s,many(),NOW);self.assertEqual(events[0]['kind'],'research_promotion');self.assertFalse(events[0]['orders_enabled'])
    def test_bad_candidate_not_promoted(self):
        s=L.blank_state();events=L.select_variant(s,many(good=False),NOW);self.assertEqual(events[0]['new'],'incumbent')
    def test_degradation_rolls_back(self):
        s=L.blank_state();pairs=many();L.select_variant(s,pairs,NOW)
        bad=many(42,start='2026-04-01',good=False);events=L.select_variant(s,bad,NOW)
        self.assertEqual(events[0]['kind'],'rollback')
    def test_same_checkpoint_not_repeated(self):
        s=L.blank_state();p=many();L.select_variant(s,p,NOW);self.assertEqual(L.select_variant(s,p,NOW),[])
    def test_augment_keeps_order_and_strict_gate_disabled(self):
        r,o,d=fixture(start='2026-10-30T13:00:00Z');r['recommendation']=False;r['strict_green_override']=False
        v=L.augment(r,L.blank_state(),NOW);self.assertFalse(v['recommendation']);self.assertFalse(v['strict_green_override']);self.assertEqual(v['online_learning']['active_variant'],'incumbent')
    def test_augment_after_target_is_no_call(self):
        r,o,d=fixture();v=L.augment(r,L.blank_state(),NOW);self.assertEqual(v['status'],'no_call')
    def test_unknown_future_state_label_is_rejected(self):
        r,o,d=fixture(start='2026-10-30T13:00:00Z');s=L.blank_state();s['last_outcome_available_at']='2026-10-31T00:00:00Z'
        with self.assertRaises(ValueError):L.augment(r,s,NOW)
    def test_corrupt_model_state_not_silently_reset(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);s=L.blank_state();g=L.ensure(s,fixture()[0]);g['weights']=[[1]]
            (p/L.STATE_FILE).write_text(json.dumps(s))
            with self.assertRaises(ValueError):L.load_state(p)
    def test_append_only_preserves_first_record(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.jsonl';L.append_unique(p,[{'id':'x','value':1}]);L.append_unique(p,[{'id':'x','value':2}]);self.assertEqual(L.lines(p)[0]['value'],1)

if __name__=='__main__': unittest.main()
