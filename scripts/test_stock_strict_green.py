"""Synthetic rule tests. Passing these does NOT validate investment returns."""
import copy,json,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
import stock_strict_green as g
NOW=datetime(2026,10,20,10,0,tzinfo=timezone.utc)
class Gate(unittest.TestCase):
 def setUp(self):
  self.raw={'generated_at':NOW.isoformat()}
  self.row={'symbol':'TEST','market':'US','currency':'USD','status':'current','price':100.,'price_session':'2026-10-19','expected_session':{'date':'2026-10-19'},'period_integrity':{'status':'ok'},'model_integrity':{'status':'ok'},'size_group':'mid','technical':{},'sources':{'official':'https://www.sec.gov/Archives/edgar/data/1/test.htm','balance':'https://example.com/bs','estimates':'https://example.com/eps','history':'https://example.com/price'},'liquidity':{'avg_turnover20':1e7},'history':{'filing_period':'2025-12-31','revenue':1210.,'operating_income':150.,'eps':8.,'cfo':150.,'capex':20.,'fcf':130.},'forecasts':{'status':'ok','analysts':8,'spread':.2,'eps_revision30_pct':1.,'eps_growth_next_fy_pct':20.,'next_fy':{'avg':10.}}}
  self.case={'symbol':'TEST','state':'attractive','label':'old positive','verdict':'screen only','confidence':'old screen','input_price':100.,'input_price_session':'2026-10-19','input_forecast_eps':10.,'official':{'annual':{'status':'ok','year':2025,'basis':'CFS','currency':'USD','source_url':self.row['sources']['official'],'checked_at':NOW.isoformat(),'receipt':'TEST-ANNUAL','facts':{k:v for k,v in self.row['history'].items() if k!='filing_period'}}}}
  self.series=[]
  for i,(year,rev,ni,ocf) in enumerate([(2025,1210,120,150),(2024,1100,110,145),(2023,1000,100,140)]):self.series.append({'period':f'{year}-12-31','currency':'USD','basis':'CFS','source_type':'official','source_url':self.row['sources']['official'],'net_income':ni,'cfo':ocf,'capex':20.,'fcf':ocf-20,'revenue':rev,'operating_income':150-i*10,'receivables':121-i*11,'inventory':60-i*5})
  self.depth={'generated_at':NOW.isoformat(),'source_generated_at':self.raw['generated_at'],'companies':[{'symbol':'TEST','series':self.series}]}
  self.macro={'generated_at':NOW.isoformat(),'indicators':{'fed_policy':{'date':'2026-09-17'}}}
  rr={**self.row,'strict_source_receipts':{'annual':'TEST-ANNUAL','interim':None}}
  self.records={'TEST':{'fundamental_fingerprint':g.fingerprint(rr),'sections':{}}}
  for area,topics in g.TOPICS.items():
   r={'reviewer':'synthetic test fixture only','reviewed_at':NOW.isoformat(),'decision':'resolved','findings':{t:'Synthetic reviewed finding with required details, used only in unit tests.' for t in topics},'sources':[{'url':self.row['sources']['official'],'locator':'TEST paragraph','publisher':'synthetic SEC','published_at':'2026-03-01','document_sha256':'a'*64,'evidence_excerpt':'Synthetic source excerpt for structural tests. Not real company data.'}]}
   if area=='forecast':r['sources'].append({**r['sources'][0],'url':'https://example.com/independent','publisher':'synthetic second publisher'})
   if area=='debt':r['amounts']={'currency':'USD','as_of':'2026-09-30','unrestricted_cash':200.,'stressed_operating_inflow_12m':100.,'all_committed_cash_uses_12m':100.}
   if area=='valuation':r['models']={'currency':'USD','share_basis':'diluted_common','normalised_eps_pe':{'conservative':{'eps':8.,'pe':20.},'base':{'eps':10.,'pe':22.},'stress':{'eps':7.,'pe':16.}},'fcfe_dcf':{'cashflow_definition':'after_debt_cashflows_to_common_equity','diluted_shares':10.,'conservative':{'annual_fcfe':[150.]*5,'cost_of_equity':.10,'terminal_growth':.02},'base':{'annual_fcfe':[170.]*5,'cost_of_equity':.09,'terminal_growth':.02},'stress':{'annual_fcfe':[130.]*5,'cost_of_equity':.12,'terminal_growth':.01}}}
   self.records['TEST']['sections'][area]=r
 def run_gate(self):return g.evaluate(self.row,self.case,self.raw,self.depth,self.macro,self.records,NOW)
 def ck(self,key):return next(c for c in self.run_gate()['checks'] if c['id']==key)
 def no_green(self):self.assertFalse(self.run_gate()['green_eligible'])
 def test_all_named_checks_can_pass(self):
  r=self.run_gate();self.assertEqual([c['id'] for c in r['checks']],g.IDS);self.assertTrue(r['green_eligible']);self.assertFalse(r['return_guarantee'])
 def test_missing_diligence_never_passes(self):self.records={};self.no_green()
 def test_links_alone_do_not_pass(self):self.records['TEST']['sections']['business'].pop('findings');self.no_green()
 def test_stale_quote(self):self.raw['generated_at']=(NOW-timedelta(hours=19)).isoformat();self.no_green()
 def test_future_quote(self):self.raw['generated_at']=(NOW+timedelta(hours=1)).isoformat();self.no_green()
 def test_wrong_price(self):self.case['input_price']=99.;self.no_green()
 def test_wrong_forecast(self):self.case['input_forecast_eps']=9.;self.no_green()
 def test_wrong_session(self):self.row['expected_session']['date']='2026-10-20';self.no_green()
 def test_wrong_period(self):self.row['period_integrity']['status']='needs_review';self.no_green()
 def test_unsupported_model(self):self.row['model_integrity']['status']='needs_sector_model';self.no_green()
 def test_expired_annual(self):self.row['history']['filing_period']='2023-12-31';self.no_green()
 def test_wrong_official_currency(self):self.case['official']['annual']['currency']='KRW';self.no_green()
 def test_wrong_official_year(self):self.case['official']['annual']['year']=2024;self.no_green()
 def test_only_revenue_verified(self):self.case['official']['annual']['facts']={'revenue':1210};self.no_green()
 def test_material_eps_difference(self):self.case['official']['annual']['facts']['eps']=7.;self.no_green()
 def test_fcf_identity(self):self.case['official']['annual']['facts']['fcf']=120.;self.no_green()
 def test_actual_rounded_difference_allowed(self):self.case['official']['annual']['facts']['revenue']+=.00001;self.assertEqual(self.ck('official')['status'],'pass')
 def test_boolean_not_number(self):self.case['official']['annual']['facts']['fcf']=True;self.no_green()
 def test_nan_not_number(self):self.case['official']['annual']['facts']['eps']=float('nan');self.no_green()
 def test_nonofficial_annual(self):self.case['official']['annual']['source_url']='https://example.com/annual';self.no_green()
 def test_source_check_old(self):self.case['official']['annual']['checked_at']=(NOW-timedelta(days=2)).isoformat();self.no_green()
 def test_two_years_not_three(self):self.series.pop();self.no_green()
 def test_depth_source_mismatch(self):self.depth['source_generated_at']='2026-10-19T00:00:00Z';self.no_green()
 def test_depth_stale(self):self.depth['generated_at']=(NOW-timedelta(hours=20)).isoformat();self.no_green()
 def test_mixed_cfs_ofs(self):self.series[1]['basis']='OFS';self.no_green()
 def test_nonannual_series(self):self.series[1]['period']='2025-06-30';self.no_green()
 def test_mixed_currency(self):self.series[2]['currency']='KRW';self.no_green()
 def test_missing_cash_not_zero(self):self.series[0]['cfo']=None;self.no_green()
 def test_earnings_cash_gap_flags_without_review(self):
  self.series[0]['cfo']=10.;del self.records['TEST']['sections']['cash_quality'];self.assertEqual(self.ck('cash_quality')['status'],'review');self.no_green()
 def test_old_earnings_decline_not_hidden(self):
  self.series[0]['net_income']=50.;del self.records['TEST']['sections']['cash_quality'];self.assertEqual(self.ck('cash_quality')['status'],'review')
 def test_inventory_faster_than_sales(self):
  self.series[0]['inventory']=200.;del self.records['TEST']['sections']['working_capital'];self.assertEqual(self.ck('working_capital')['status'],'review');self.no_green()
 def test_missing_receivables_not_healthy(self):
  self.series[0]['receivables']=None;del self.records['TEST']['sections']['working_capital'];self.assertEqual(self.ck('working_capital')['status'],'missing')
 def test_zero_inventory_not_missing(self):
  for s in self.series:s['inventory']=0.
  del self.records['TEST']['sections']['working_capital'];self.assertEqual(self.ck('working_capital')['status'],'pass')
 def test_debt_service_coverage(self):self.records['TEST']['sections']['debt']['amounts']['all_committed_cash_uses_12m']=500.;self.assertEqual(self.ck('debt')['status'],'review');self.no_green()
 def test_debt_currency(self):self.records['TEST']['sections']['debt']['amounts']['currency']='KRW';self.no_green()
 def test_covenants_unknown(self):self.records['TEST']['sections']['debt']['findings'].pop('covenants');self.no_green()
 def test_review_outdated(self):self.records['TEST']['sections']['business']['reviewed_at']=(NOW-timedelta(days=31)).isoformat();self.no_green()
 def test_governance_one_day_expiry(self):self.records['TEST']['sections']['governance']['reviewed_at']=(NOW-timedelta(days=2)).isoformat();self.no_green()
 def test_new_filing_invalidates_review(self):self.case['official']['annual']['receipt']='NEW';self.no_green()
 def test_no_reviewer(self):self.records['TEST']['sections']['business']['reviewer']='';self.no_green()
 def test_location_required(self):self.records['TEST']['sections']['business']['sources'][0]['locator']='';self.no_green()
 def test_key_in_url_rejected(self):self.records['TEST']['sections']['business']['sources'][0]['url']='https://dart.fss.or.kr/a?crtfc_key=private';self.no_green()
 def test_auth_does_not_approve_stock(self):self.case['auth']={'status':'authenticated'};self.records={};self.no_green()
 def test_future_published_source(self):self.records['TEST']['sections']['business']['sources'][0]['published_at']='2027-01-01';self.no_green()
 def test_unresolved_review(self):self.records['TEST']['sections']['governance']['decision']='unresolved';self.no_green()
 def test_target_alone_not_valuation(self):self.records['TEST']['sections']['valuation']['models']={'target_median':10000};self.no_green()
 def test_valuation_safety_margin(self):self.row['price']=200;self.case['input_price']=200;self.assertEqual(self.ck('valuation')['status'],'review');self.no_green()
 def test_bad_terminal_growth(self):self.records['TEST']['sections']['valuation']['models']['fcfe_dcf']['base']['terminal_growth']=.2;self.no_green()
 def test_ev_not_equity(self):self.records['TEST']['sections']['valuation']['models']['fcfe_dcf']['cashflow_definition']='EBITDA';self.no_green()
 def test_no_diluted_shares(self):self.records['TEST']['sections']['valuation']['models']['fcfe_dcf']['diluted_shares']=None;self.no_green()
 def test_zero_shares(self):self.records['TEST']['sections']['valuation']['models']['fcfe_dcf']['diluted_shares']=0;self.no_green()
 def test_bad_scenario_order(self):self.records['TEST']['sections']['valuation']['models']['normalised_eps_pe']['stress']['eps']=50;self.no_green()
 def test_stress_loss_bound(self):
  r=self.run_gate();self.assertFalse(r['valuation']['is_loss_bound']);self.assertFalse(r['return_guarantee'])
 def test_consensus_single_publisher(self):self.records['TEST']['sections']['forecast']['sources'].pop();self.no_green()
 def test_five_analysts_required(self):self.row['forecasts']['analysts']=4;self.no_green()
 def test_downward_estimate(self):self.row['forecasts']['eps_revision30_pct']=-5;self.no_green()
 def test_illiquid(self):self.row['liquidity']['avg_turnover20']=100;self.no_green()
 def test_recent_split(self):self.row['technical']['recent_split']=True;self.no_green()
 def test_macros_missing(self):self.macro={};self.no_green()
 def test_no_score_override(self):self.row['priority']={'score':100};self.records={};self.no_green()
 def test_all_but_one_cannot_be_green(self):self.records['TEST']['sections'].pop('governance');self.assertEqual(self.run_gate()['passed'],11);self.no_green()
 def test_synthetic_pass_is_not_strategy_evidence(self):self.assertEqual(self.run_gate()['strategy_performance'],'not_validated')
 def test_duplicate_issuer_rejected(self):
  self.raw['companies']=[self.row,self.row]
  with self.assertRaises(ValueError):g.apply_bundle(self.raw,{'source_generated_at':self.raw['generated_at'],'companies':[self.case]},self.depth,self.macro,self.records,NOW)
 def test_unmatched_snapshot_rejected(self):
  self.raw['companies']=[self.row]
  with self.assertRaises(ValueError):g.apply_bundle(self.raw,{'source_generated_at':'wrong','companies':[self.case]},self.depth,self.macro,self.records,NOW)
 def test_repeated_review_retains_screen_not_green(self):
  self.raw['companies']=[self.row];c={'source_generated_at':self.raw['generated_at'],'companies':[self.case]}
  c,_=g.apply_bundle(self.raw,c,self.depth,self.macro,{},NOW);self.assertNotEqual(c['companies'][0]['state'],'attractive')
  c,_=g.apply_bundle(self.raw,c,self.depth,self.macro,self.records,NOW);self.assertTrue(c['companies'][0]['green_review']['green_eligible']);self.assertEqual(c['companies'][0]['screening_opinion']['state'],'attractive')
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Gate))
 Path('stock-green-tests.json').write_text(json.dumps({'synthetic_policy_tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'passed':r.wasSuccessful(),'investment_performance_test':False},indent=2)+'\n')
 raise SystemExit(not r.wasSuccessful())
