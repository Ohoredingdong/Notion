"""Synthetic fixtures only; no approvals or market prices are written to production."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from build_stock_entry_plan import IDS,evaluate,completed_bar,number,fresh,build,market_scenarios

NOW=dt.datetime(2026,10,28,8,tzinfo=dt.timezone.utc)
STAMP=dt.datetime(2026,10,28,7,tzinfo=dt.timezone.utc).isoformat()

def fixture():
    raw={'generated_at':STAMP,'market_sessions':{'KR':'2026-10-28'}}
    c={'symbol':'TEST_ONLY','name':'Synthetic test fixture','market':'KR','currency':'KRW','price':100,
       'source_integrity':{'fetched_at':STAMP},
       'technical':{'price_session':'2026-10-28','expected_session':'2026-10-28',
                    'date':'2026-10-28','close':100,'ma20':99,'ma60':95,'atr14':2,'support10':96,'prior_high20':102,'volume_ratio':1.1,'relative20_pp':3,'avg_turnover20':2e9},
       'estimates':{'next_year':{'eps_avg':10,'eps_30d':10,'fiscal_end':'2027-12-31'}}}
    r={'version':'strict-green-1.0','green_eligible':True,'source_generated_at':STAMP,
       'reviewed_at':STAMP,'valid_until':(NOW+dt.timedelta(hours=3)).isoformat(),
       'input_price':100,'input_price_session':'2026-10-28','input_forecast_eps':10,
       'checks':[{'id':key,'status':'pass'} for key in IDS],
       'valuation':{'reference_price':120}}
    case={'green_review':copy.deepcopy(r)}
    return c,case,r,raw

def result(change=None,revalidated=True):
    c,case,r,raw=fixture()
    if change: change(c,case,r,raw)
    return evaluate(c,case,r,raw,NOW,revalidated)

class EntryTests(unittest.TestCase):
    def test_valid_is_paper_only(self):
        r=result(); self.assertTrue(r['entry_conditions_met']); self.assertFalse(r['live_recommendation'])
    def test_no_document_rereview(self): self.assertFalse(result(revalidated=False)['entry_conditions_met'])
    def test_missing_all_checks(self):
        self.assertFalse(result(lambda c,k,r,s:r.update(checks=[]))['entry_conditions_met'])
    def test_each_required_id_fail_closed(self):
        for key in IDS:
            with self.subTest(key=key):
                def change(c,k,r,s): r['checks']=[v for v in r['checks'] if v['id']!=key]
                self.assertFalse(result(change)['entry_conditions_met'])
    def test_duplicate_id(self):
        self.assertFalse(result(lambda c,k,r,s:r['checks'][-1].update(id='inputs'))['entry_conditions_met'])
    def test_review_blocked_missing(self):
        for status in ['review','blocked','missing']:
            with self.subTest(status=status):
                self.assertFalse(result(lambda c,k,r,s:r['checks'][2].update(status=status))['entry_conditions_met'])
    def test_truthy_boolean_not_approval(self):
        for value in [1,'true','false',None]:
            with self.subTest(value=value):
                self.assertFalse(result(lambda c,k,r,s:r.update(green_eligible=value))['entry_conditions_met'])
    def test_embedded_false(self): self.assertFalse(result(lambda c,k,r,s:k['green_review'].update(green_eligible=False))['entry_conditions_met'])
    def test_wrong_version(self): self.assertFalse(result(lambda c,k,r,s:r.update(version='other'))['entry_conditions_met'])
    def test_review_expired(self): self.assertFalse(result(lambda c,k,r,s:r.update(valid_until=NOW.isoformat()))['entry_conditions_met'])
    def test_old_review(self): self.assertFalse(result(lambda c,k,r,s:r.update(reviewed_at=(NOW-dt.timedelta(days=31)).isoformat()))['entry_conditions_met'])
    def test_future_review(self): self.assertFalse(result(lambda c,k,r,s:r.update(reviewed_at=(NOW+dt.timedelta(hours=1)).isoformat()))['entry_conditions_met'])
    def test_price_changed(self): self.assertFalse(result(lambda c,k,r,s:c.update(price=101))['entry_conditions_met'])
    def test_eps_changed(self): self.assertFalse(result(lambda c,k,r,s:c['estimates']['next_year'].update(eps_avg=11))['entry_conditions_met'])
    def test_session_changed(self): self.assertFalse(result(lambda c,k,r,s:r.update(input_price_session='2026-10-27'))['entry_conditions_met'])
    def test_snapshot_changed(self): self.assertFalse(result(lambda c,k,r,s:r.update(source_generated_at='2026-10-28T06:00:00+00:00'))['entry_conditions_met'])
    def test_old_raw(self): self.assertFalse(result(lambda c,k,r,s:s.update(generated_at=(NOW-dt.timedelta(hours=19)).isoformat()))['entry_conditions_met'])
    def test_future_raw(self): self.assertFalse(result(lambda c,k,r,s:s.update(generated_at=(NOW+dt.timedelta(seconds=1)).isoformat()))['entry_conditions_met'])
    def test_generated_is_not_collection(self): self.assertFalse(result(lambda c,k,r,s:c.pop('source_integrity'))['entry_conditions_met'])
    def test_cached_price(self): self.assertFalse(result(lambda c,k,r,s:c['source_integrity'].update(fetched_at=(NOW-dt.timedelta(hours=19)).isoformat()))['entry_conditions_met'])
    def test_intraday_bar(self): self.assertFalse(result(lambda c,k,r,s:c['source_integrity'].update(fetched_at='2026-10-28T02:00:00+00:00'))['entry_conditions_met'])
    def test_next_fy_unknown(self): self.assertFalse(result(lambda c,k,r,s:c['estimates']['next_year'].pop('fiscal_end'))['entry_conditions_met'])
    def test_single_target_not_value(self): self.assertFalse(result(lambda c,k,r,s:r.update(valuation={'target_median':120}))['entry_conditions_met'])
    def test_trend_wait(self): self.assertFalse(result(lambda c,k,r,s:c['technical'].update(ma60=110))['entry_conditions_met'])
    def test_overextended(self): self.assertFalse(result(lambda c,k,r,s:c['technical'].update(ma20=90))['entry_conditions_met'])
    def test_missing_atr(self): self.assertFalse(result(lambda c,k,r,s:c['technical'].update(atr14=None))['entry_conditions_met'])
    def test_liquidity_missing(self): self.assertFalse(result(lambda c,k,r,s:c['technical'].pop('avg_turnover20'))['entry_conditions_met'])
    def test_revision_cut(self): self.assertFalse(result(lambda c,k,r,s:c['estimates']['next_year'].update(eps_30d=12))['entry_conditions_met'])
    def test_split(self): self.assertFalse(result(lambda c,k,r,s:c['technical'].update(split_events=['test']))['entry_conditions_met'])
    def test_price_nan(self): self.assertFalse(result(lambda c,k,r,s:c.update(price=float('nan')))['entry_conditions_met'])
    def test_rejected_has_no_buy_price(self):
        r=result(revalidated=False); self.assertIsNone(r['plan']['entry_ceiling'])
    def test_future_session(self): self.assertFalse(completed_bar('2026-10-29','KR',STAMP,NOW))
    def test_us_dst(self):
        self.assertFalse(completed_bar('2026-10-27','US','2026-10-27T19:59:00Z',NOW))
        self.assertTrue(completed_bar('2026-10-27','US','2026-10-27T20:31:00Z',NOW))
    def test_naive_timestamp_rejected(self): self.assertFalse(fresh('2026-10-28T07:00:00',18,NOW))
    def test_bool_is_not_number(self): self.assertIsNone(number(True))
    def test_scenarios_do_not_invent_probability(self):
        for s in market_scenarios({},NOW)['indices']: self.assertIsNone(s['probability']);self.assertFalse(s['is_prediction'])
    def test_build_records_once_without_fake_approvals(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); c,k,r,raw=fixture(); raw['companies']=[c]
            (root/'stock-opportunity-data.json').write_text(json.dumps(raw))
            a=build(root,NOW); b=build(root,NOW)
            self.assertEqual(a['live_recommendations'],0)
            self.assertEqual(len((root/'stock-entry-ledger.jsonl').read_text().splitlines()),1)
            self.assertFalse((root/'stock-research-review-records.json').exists())
            self.assertIn('derived_snapshot_mismatch',b['companies'][0]['data_blocks'])

if __name__=='__main__': unittest.main()

class OutcomeTests(unittest.TestCase):
    def fixture(self):
        from evaluate_stock_entry_outcomes import observe
        record={'id':'synthetic','recorded_at':'2026-10-28T08:00:00Z'}
        row={'symbol':'TEST_ONLY','market':'KR','price':100,'price_session':'2026-10-28','state':'timing_wait'}
        bars=[{'date':'2026-10-28','close':100,'split':0},{'date':'2026-10-29','close':105,'split':0}]
        bench=[{'date':'2026-10-28','close':200,'split':0},{'date':'2026-10-29','close':202,'split':0}]
        return observe,record,row,bars,bench
    def test_future_not_counted(self):
        f,r,c,b,m=self.fixture(); self.assertTrue(all(x['status']=='pending' for x in f(r,c,b,m,NOW)))
    def test_only_matured_session(self):
        f,r,c,b,m=self.fixture(); x=f(r,c,b,m,NOW+dt.timedelta(days=1))
        self.assertEqual(x[0]['status'],'observed');self.assertAlmostEqual(x[0]['excess_price_return_pp'],4)
        self.assertEqual(x[1]['status'],'pending');self.assertEqual(x[2]['status'],'pending')
    def test_no_credit_before_record(self):
        f,r,c,b,m=self.fixture();r['recorded_at']='2026-10-29T08:00:00Z'
        self.assertEqual(f(r,c,b,m,NOW+dt.timedelta(days=1))[0]['status'],'pending')
    def test_split_not_profit(self):
        f,r,c,b,m=self.fixture(); b[-1]['split']=2
        self.assertEqual(f(r,c,b,m,NOW+dt.timedelta(days=1))[0]['status'],'corporate_action_review')
    def test_revised_baseline_not_accepted(self):
        f,r,c,b,m=self.fixture(); b[0]['close']=90
        self.assertEqual(f(r,c,b,m,NOW+dt.timedelta(days=1)),[])
    def test_missing_benchmark_not_success(self):
        f,r,c,b,m=self.fixture()
        self.assertEqual(f(r,c,b,[],NOW+dt.timedelta(days=1))[0]['status'],'benchmark_missing')

class ActualSchemaTests(unittest.TestCase):
    def test_real_collection_field(self):
        def change(c,k,r,s): c['collected_at']=STAMP;c.pop('source_integrity')
        self.assertTrue(result(change)['entry_conditions_met'])
    def test_next_fy_inferred_is_labelled_not_confirmed(self):
        def change(c,k,r,s):
            c.pop('estimates');c['forecasts']={'next_fy':{'avg':10},'next_fy_end_inferred':'2027-12-31','eps_revision30_pct':0}
        x=result(change);self.assertEqual(x['forecast_period_basis'],'inferred_next_fy_not_exact_close_date')
    def test_old_expected_date_cannot_make_old_quote_current(self):
        def change(c,k,r,s):
            c['price_session']='2026-10-27';c['expected_session']={'date':'2026-10-27'};r['input_price_session']='2026-10-27'
        self.assertIn('price_session_mismatch',result(change)['data_blocks'])
    def test_technical_close_must_match(self):
        self.assertIn('technical_price_mismatch',result(lambda c,k,r,s:c['technical'].update(close=99))['data_blocks'])
    def test_earnings_event_wait(self):
        self.assertIn('earnings_event_near',result(lambda c,k,r,s:c.update(earnings_calendar={'Earnings Date':['2026-10-29']}))['timing_blocks'])
    def test_calendar_weekend(self):
        from stock_entry_inputs import clock
        sat=dt.datetime(2026,10,31,8,tzinfo=dt.timezone.utc)
        self.assertEqual(clock('KR',sat)['date'],'2026-10-30')
    def test_calendar_unknown_market(self):
        from stock_entry_inputs import clock
        self.assertIsNone(clock('UNKNOWN',NOW)['date'])
    def test_early_rebound_not_green(self):
        x=result(lambda c,k,r,s:c['technical'].update(ma60=110))
        self.assertEqual(x['tech']['setup'],'early_rebound_watch');self.assertFalse(x['entry_conditions_met'])
