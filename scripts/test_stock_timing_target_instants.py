"""Synthetic-only UTC target-identity regressions; never rewrite source rows."""
from copy import deepcopy
import json
import unittest
from audit_stock_forecast_independent import audit, ts

CUT = ts('2026-10-29T16:00:00Z')

def fixture():
    r = {'id':'synthetic-utc-first','symbol':'TEST','market':'US','mode':'intraday',
         'status':'research_prediction','observed_until':'2026-10-29T13:30:00Z',
         'received_at':'2026-10-29T13:31:00Z','issued_at':'2026-10-29T13:36:00Z',
         'target':{'start':'2026-10-29T14:00:00Z','end':'2026-10-29T14:30:00Z'},
         'probabilities':{'down':.2,'flat':.6,'up':.2},'direction':'flat','neutral_band_pct':.3}
    o = {'id':r['id'],'symbol':'TEST','mode':'intraday','status':'observed',
         'target':deepcopy(r['target']),'evaluated_at':'2026-10-29T14:31:00Z',
         'target_open':100.,'target_close':100.,'return_pct':0.,'actual':'flat',
         'predicted':'flat','correct':True,'brier_loss':.24}
    return r,o

def proof(rows):
    return [{'status':'public_verified','snapshot_generated_at':'2026-10-29T13:36:30Z',
             'verified_at':'2026-10-29T13:37:00Z','prediction_ids':[r['id'] for r in rows]}]

class TargetInstantTests(unittest.TestCase):
    def pair(self, start, end, later=False):
        a,oa=fixture();b=deepcopy(a);b['id']='synthetic-offset-second'
        b['target']={'start':start,'end':end}
        if later:b['issued_at']='2026-10-29T13:36:10Z'
        ob=deepcopy(oa);ob['id']=b['id'];ob['target']=deepcopy(b['target'])
        return [a,b],[oa,ob]

    def test_z_plus_zero_competing_first_issuance_rejected(self):
        r,o=self.pair('2026-10-29T14:00:00+00:00','2026-10-29T14:30:00+00:00')
        result=audit(r,o,proof(r),CUT)
        self.assertEqual(result['scored'],0)
        self.assertIn('ambiguous_first_issuance_tie',[e['error'] for e in result['errors']])

    def test_nonzero_offset_same_event_rejected(self):
        r,o=self.pair('2026-10-29T23:00:00+09:00','2026-10-29T23:30:00+09:00')
        result=audit(r,o,proof(r),CUT)
        self.assertEqual(result['scored'],0)
        self.assertEqual(result['unique_events'],1)

    def test_equivalent_first_issuance_is_order_invariant(self):
        r,o=self.pair('2026-10-29T10:00:00-04:00','2026-10-29T10:30:00-04:00')
        for rr in (r,list(reversed(r))):
            result=audit(rr,o,proof(r),CUT)
            self.assertEqual(result['scored'],0)
            self.assertEqual(result['status'],'integrity_errors')

    def test_later_alias_is_reissue_not_new_or_overlap(self):
        r,o=self.pair('2026-10-29T14:00:00+00:00','2026-10-29T14:30:00+00:00',later=True)
        result=audit(r,o,proof(r),CUT)
        self.assertEqual(result['unique_events'],1)
        self.assertEqual(result['counts'].get('duplicate_issuances'),1)
        self.assertEqual(result['counts'].get('overlap_excluded',0),0)
        self.assertEqual([x['id'] for x in result['rows']],[r[0]['id']])

    def test_different_absolute_targets_remain_distinct(self):
        r,o=self.pair('2026-10-29T14:30:00Z','2026-10-29T15:00:00Z',later=True)
        o[1]['evaluated_at']='2026-10-29T15:01:00Z'
        result=audit(r,o,proof(r),CUT)
        self.assertEqual(result['unique_events'],2)
        self.assertEqual(result['scored'],2)
        self.assertFalse(result['errors'])

    def test_normalization_never_rewrites_frozen_evidence(self):
        r,o=self.pair('2026-10-29T23:00:00+09:00','2026-10-29T23:30:00+09:00')
        d=proof(r);before=json.dumps([r,o,d],sort_keys=True)
        audit(r,o,d,CUT)
        self.assertEqual(json.dumps([r,o,d],sort_keys=True),before)

    def test_same_id_exact_replay_is_not_competing_issue(self):
        r,o=fixture();result=audit([r,deepcopy(r)],[o],proof([r]),CUT)
        self.assertFalse(result['errors']);self.assertEqual(result['scored'],1)

    def test_timezone_naive_target_stays_rejected(self):
        r,o=fixture();r['target']['start']='2026-10-29T14:00:00'
        result=audit([r],[o],proof([r]),CUT)
        self.assertEqual(result['scored'],0);self.assertEqual(result['status'],'integrity_errors')

if __name__=='__main__':unittest.main()
