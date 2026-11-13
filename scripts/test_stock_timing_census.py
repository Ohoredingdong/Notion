"""Synthetic-only exhaustive-accounting controls, independent of live prices."""
from copy import deepcopy
import json
import unittest
from audit_stock_forecast_census import census, stats
from audit_stock_forecast_independent import audit, ts
from test_stock_timing_target_instants import fixture, proof, CUT


def examine(records, outcomes, deliveries, controller=None, upstream=None, cutoff=CUT):
    upstream = audit(records,outcomes,deliveries,cutoff) if upstream is None else upstream
    return census(records,outcomes,deliveries,upstream,controller or {})

class CensusTests(unittest.TestCase):
    def test_empty_is_not_perfect(self):
        result=examine([],[],[])
        self.assertIsNone(result['observed_metrics']['accuracy'])
        self.assertEqual(result['timing_utility'],'not_proven')
        self.assertFalse(result['external_exchange_prices_verified'])

    def test_all_original_rows_have_exactly_one_disposition(self):
        r,o=fixture();second=deepcopy(r);second['id']='later';second['issued_at']='2026-10-29T13:36:10Z'
        result=examine([r,second],[o],proof([r,second]))
        self.assertEqual(result['row_accounting'],{'scored':1,'later_reissue':1})
        self.assertEqual(sum(result['row_accounting'].values()),2)
        self.assertFalse(result['errors'])

    def test_all_outcomes_recomputed_even_when_not_scored(self):
        r,o=fixture();second=deepcopy(r);second['id']='later';second['issued_at']='2026-10-29T13:36:10Z'
        oo=deepcopy(o);oo['id']='later';oo['correct']=False
        result=examine([r,second],[o,oo],proof([r,second]))
        self.assertIn('invalid_stored_outcome',result['errors'])
        self.assertEqual(result['verified_outcome_ids'],1)

    def test_pending_is_not_missing_or_success(self):
        r,o=fixture();result=examine([r],[],proof([r]),cutoff=ts('2026-10-29T14:15:00Z'))
        self.assertEqual(result['row_accounting'],{'pending_target':1})
        self.assertIsNone(result['observed_metrics']['accuracy'])

    def test_expired_target_with_older_collector_is_waiting_not_failure(self):
        r,o=fixture();c={'source_attempts':[{'symbol':'TEST','mode':'intraday','observed_until':'2026-10-29T13:30:00Z'}]}
        result=examine([r],[],proof([r]),c)
        self.assertEqual(result['missing_context_counts'],{'awaiting_later_source_observation':1})
        self.assertFalse(result['errors'])

    def test_missing_with_newer_source_remains_unresolved(self):
        r,o=fixture();c={'source_attempts':[{'symbol':'TEST','mode':'intraday','observed_until':'2026-10-29T15:30:00Z'}]}
        result=examine([r],[],proof([r]),c)
        self.assertEqual(result['missing_context_counts'],{'missing_despite_later_source_snapshot':1})
        self.assertEqual(result['observed_metrics']['samples'],0)

    def test_late_publication_cannot_score(self):
        r,o=fixture();d=proof([r]);d[0]['verified_at']='2026-10-29T14:01:00Z'
        result=examine([r],[o],d)
        self.assertEqual(result['row_accounting'],{'public_not_timely':1})
        self.assertEqual(result['verified_outcome_ids'],1)
        self.assertEqual(result['observed_metrics']['samples'],0)

    def test_overlapping_target_excluded_before_correctness(self):
        r,o=fixture();r2=deepcopy(r);r2['id']='overlap';r2['target']={'start':'2026-10-29T14:15:00Z','end':'2026-10-29T14:45:00Z'}
        o2=deepcopy(o);o2['id']='overlap';o2['target']=deepcopy(r2['target']);o2['evaluated_at']='2026-10-29T14:46:00Z'
        result=examine([r,r2],[o,o2],proof([r,r2]))
        self.assertEqual(result['row_accounting'],{'scored':1,'overlap_excluded':1})
        self.assertEqual(result['verified_outcome_ids'],2)

    def test_exact_id_replay_is_explicit_not_new_score(self):
        r,o=fixture();result=examine([r,deepcopy(r)],[o],proof([r]))
        self.assertEqual(result['row_accounting'],{'scored':1,'exact_id_replay':1})
        self.assertEqual(result['observed_metrics']['samples'],1)

    def test_ambiguous_alias_targets_never_choose_lucky_first_row(self):
        r,o=fixture();r2=deepcopy(r);r2['id']='alias';r2['target']={'start':'2026-10-29T23:00:00+09:00','end':'2026-10-29T23:30:00+09:00'}
        result=examine([r,r2],[o],proof([r,r2]))
        self.assertEqual(result['row_accounting'],{'ambiguous_first_issuance':2})
        self.assertEqual(result['observed_metrics']['samples'],0)
        self.assertIn('ambiguous_first_issuance',result['errors'])

    def test_upstream_error_never_promoted_to_consistent(self):
        r,o=fixture();d=proof([r]);up=audit([r],[o],d,CUT);up['errors']=[{'error':'synthetic'}]
        result=examine([r],[o],d,upstream=up)
        self.assertIn('upstream_integrity_not_verified',result['errors'])

    def test_wrong_upstream_cohort_is_rejected(self):
        r,o=fixture();d=proof([r]);up=audit([r],[o],d,CUT);up['rows']=[];up['scored']=0
        result=examine([r],[o],d,upstream=up)
        self.assertIn('independent_scored_cohort_mismatch',result['errors'])

    def test_outcome_unknown_forecast_is_rejected(self):
        r,o=fixture();o['id']='unknown';result=examine([r],[o],proof([r]))
        self.assertIn('outcome_without_valid_forecast',result['errors'])

    def test_original_baseline_absence_is_not_backfilled(self):
        r,o=fixture();result=examine([r],[o],proof([r]))
        self.assertEqual(result['paired_baseline']['missing_original_baseline'],1)
        self.assertEqual(result['paired_baseline']['baseline']['samples'],0)
        self.assertIsNone(result['paired_baseline']['brier_gain'])

    def test_no_evidence_mutation_or_false_human_receipt(self):
        r,o=fixture();d=proof([r]);before=json.dumps([r,o,d],sort_keys=True)
        result=examine([r],[o],d)
        self.assertEqual(json.dumps([r,o,d],sort_keys=True),before)
        self.assertIsNone(result['rows'][0]['human_received_at'])
        self.assertFalse(result['human_receipt_verified'])
        self.assertEqual(result['new_learning_updates'],0)

    def test_directional_denominators_and_probability_error(self):
        r=stats([('up','flat',[.2,.6,.2]),('down','down',[.6,.2,.2]),('flat','flat',[.2,.6,.2])])
        self.assertAlmostEqual(r['accuracy'],2/3)
        self.assertEqual(r['directions']['up']['missed'],1)
        self.assertIsNone(r['directions']['up']['precision'])
        self.assertAlmostEqual(r['directions']['flat']['precision'],.5)
        self.assertAlmostEqual(r['brier_loss'],(1.04+.24+.24)/3)

    def test_missing_windows_are_grouped_by_true_utc_instant_without_scoring(self):
        first,_ = fixture()
        second = deepcopy(first)
        second['id']='synthetic-same-window-second'
        second['symbol']='TEST2'
        second['target']={'start':'2026-10-29T23:00:00+09:00','end':'2026-10-29T23:30:00+09:00'}
        delivered=proof([first,second])
        before=json.dumps([first,second,delivered],sort_keys=True)
        latest={'source_attempts':[
            {'symbol':name,'mode':'intraday','observed_until':'2026-10-29T15:30:00Z'}
            for name in ('TEST','TEST2')]}
        result=examine([first,second],[],delivered,latest)
        self.assertEqual(result['row_accounting'],{'outcome_missing_at_snapshot':2})
        clusters=result['missing_target_windows']
        self.assertEqual(len(clusters),1)
        group=clusters[0]
        self.assertEqual(group['target_start_utc'],'2026-10-29T14:00:00+00:00')
        self.assertEqual(group['target_end_utc'],'2026-10-29T14:30:00+00:00')
        self.assertEqual(group['symbols'],['TEST','TEST2'])
        self.assertEqual(group['forecast_ids'],sorted([first['id'],second['id']]))
        self.assertEqual(group['count'],2)
        self.assertEqual(group['missing_context_counts'],{'missing_despite_later_source_snapshot':2})
        self.assertEqual(group['root_cause'],'unverified')
        self.assertFalse(group['exchange_raw_bars_verified'])
        self.assertEqual(result['observed_metrics']['samples'],0)
        self.assertEqual(json.dumps([first,second,delivered],sort_keys=True),before)

    def test_missing_window_clusters_respect_explicit_venue_and_ignore_pending(self):
        r,_=fixture();r['venue']='KRX';second=deepcopy(r)
        second['id']='synthetic-other-venue';second['symbol']='TEST2';second['venue']='NXT'
        result=examine([r,second],[],proof([r,second]))
        self.assertEqual(len(result['missing_target_windows']),2)
        self.assertEqual([x['venue'] for x in result['missing_target_windows']],['KRX','NXT'])
        self.assertEqual([x['count'] for x in result['missing_target_windows']],[1,1])
        later,_=fixture()
        pending=examine([later],[],proof([later]),cutoff=ts('2026-10-29T14:15:00Z'))
        self.assertEqual(pending['missing_target_windows'],[])
        self.assertEqual(pending['row_accounting'],{'pending_target':1})

    def test_missing_window_clusters_do_not_count_later_reissues(self):
        original,_=fixture();later=deepcopy(original)
        later['id']='synthetic-later-reissue';later['issued_at']='2026-10-29T13:36:10Z'
        result=examine([original,later],[],proof([original,later]))
        self.assertEqual(result['row_accounting'],{'outcome_missing_at_snapshot':1,'later_reissue':1})
        self.assertEqual(result['missing_target_windows'][0]['count'],1)
        self.assertEqual(result['missing_target_windows'][0]['forecast_ids'],[original['id']])

if __name__=='__main__':unittest.main()
