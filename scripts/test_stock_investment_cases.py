import unittest,copy,json
from datetime import datetime,timezone
from pathlib import Path
from build_stock_investment_cases import evaluate,extract,compare,num
NOW=datetime(2026,10,20,tzinfo=timezone.utc)
class Cases(unittest.TestCase):
 def row(self):
  return {'symbol':'EX','market':'US','status':'current','period_integrity':{'status':'ok'},'model_integrity':{'status':'ok'},'price':100,'price_session':'2026-10-19','sector':'Software','history':{'filing_period':'2025-12-31','revenue':1000,'operating_income':200,'fcf':150,'cfo':170,'eps':4,'operating_margin':20},'balance':{'net_debt_ebitda':1},'forecasts':{'status':'ok','analysts':8,'eps_growth_next_fy_pct':20,'eps_revision30_pct':1,'spread':.2,'next_fy':{'avg':5}},'targets':{'status':'ok','analysts':8,'median_gap_pct':30,'spread':.3},'assessment':{'checks':[{'key':'liquidity','ok':True}]},'official_history':{'matched':['revenue','eps','fcf'],'checked_at':'2026-10-20T00:00:00+00:00'}}
 def test_positive(self):self.assertEqual(evaluate(self.row(),{}, {},NOW)['state'],'attractive')
 def test_price(self):
  r=self.row();r['targets']['median_gap_pct']=12;self.assertEqual(evaluate(r,{}, {},NOW)['state'],'price_wait')
 def test_unknown_not_buy(self):
  r=self.row();r['balance']['net_debt_ebitda']=None;self.assertEqual(evaluate(r,{}, {},NOW)['state'],'insufficient')
 def test_no_official_conditional(self):
  r=self.row();r['official_history']={};self.assertEqual(evaluate(r,{}, {},NOW)['state'],'conditional')
 def test_stale_price(self):
  r=self.row();r['status']='failed';self.assertEqual(evaluate(r,{}, {},NOW)['state'],'insufficient')
 def test_bad_period(self):
  r=self.row();r['period_integrity']={'status':'needs_review'};self.assertEqual(evaluate(r,{}, {},NOW)['state'],'insufficient')
 def test_unsupported_sector(self):
  r=self.row();r['model_integrity']={'status':'needs_sector_model'};self.assertEqual(evaluate(r,{}, {},NOW)['state'],'insufficient')
 def test_actual_cash_loss(self):
  r=self.row();r['history']['fcf']=-2;self.assertEqual(evaluate(r,{}, {},NOW)['state'],'avoid')
 def test_forecast_decline(self):
  r=self.row();r['forecasts']['eps_revision30_pct']=-5;self.assertEqual(evaluate(r,{}, {},NOW)['state'],'avoid')
 def test_future_no_guarantee(self):self.assertTrue(evaluate(self.row(),{}, {},NOW)['no_guarantee'])
 def test_boolean_missing(self):self.assertIsNone(num(True))
 def test_proof_stale_not_verified(self):
  r=self.row();r['official_history']['checked_at']='2026-10-01';self.assertEqual(evaluate(r,{}, {},NOW)['state'],'conditional')
 def payload(self,interim=False):
  return {'status':'000','list':[{'corp_code':'00000001','bsns_year':'2025','reprt_code':'11012' if interim else '11011','currency':'KRW','sj_div':'IS','account_id':'ifrs-full_Revenue','account_nm':'매출액','thstrm_amount':'100','thstrm_add_amount':'300','frmtrm_amount':'80','frmtrm_add_amount':'200','rcept_no':'20260301000001'}]}
 def test_cumulative(self):self.assertEqual(extract(self.payload(True),'00000001',2025,'11012','CFS')['facts']['revenue'],300)
 def test_annual(self):self.assertEqual(extract(self.payload(),'00000001',2025,'11011','CFS')['facts']['revenue'],100)
 def test_identity(self):
  with self.assertRaises(ValueError):extract(self.payload(),'wrong',2025,'11011','CFS')
 def test_currency(self):
  p=self.payload();p['list'][0]['currency']='USD'
  with self.assertRaises(ValueError):extract(p,'00000001',2025,'11011','CFS')
 def test_ambiguous_tag(self):
  p=self.payload();q=copy.deepcopy(p['list'][0]);q['thstrm_amount']='9';p['list'].append(q)
  self.assertNotIn('revenue',extract(p,'00000001',2025,'11011','CFS')['facts'])
 def test_missing_intangible_not_zero(self):self.assertNotIn('fcf',extract(self.payload(),'00000001',2025,'11011','CFS')['facts'])
 def test_eps_mismatch(self):
  a={'status':'ok','year':2025,'facts':{'eps':100},'source_url':'https://example.org','basis':'CFS'};r={'history':{'filing_period':'2025-12-31','eps':1000}}
  self.assertEqual(compare(r,a)[0]['status'],'difference')
 def test_latest_interim_decline(self):
  r=self.row();a={'interim':{'status':'ok','year':2026,'facts':{'revenue_growth':-20,'operating_income':50},'previous':{'operating_income':100},'source_url':'https://example.org'}}
  self.assertEqual(evaluate(r,a,{},NOW)['state'],'avoid')
 def test_sample_min(self):
  r=self.row();r['forecasts']['analysts']=1;self.assertEqual(evaluate(r,{}, {},NOW)['state'],'insufficient')
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
 Path('stock-investment-cases-tests.json').write_text(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'failures':len(r.failures),'errors':len(r.errors)},indent=2))
 raise SystemExit(0 if r.wasSuccessful() else 1)
