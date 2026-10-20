import copy,json,unittest
from pathlib import Path
import update_stock_opportunities as m

class Policy(unittest.TestCase):
 def row(self):
  return {'status':'current','market':'US','price':80.,'price_session':'2026-10-19','size_group':'mid','forecasts':{'status':'ok','analysts':8,'eps_revision30_pct':1.,'eps_growth_next_fy_pct':15.,'spread':.2},'targets':{'status':'ok','analysts':8,'median_gap_pct':30.,'spread':.4,'review_price_ceiling':86.66666667},'balance':{'net_debt_ebitda':1.},'history':{'fcf':1e8},'official_history':{'matched':['revenue','eps','fcf'],'issues':[]},'technical':{'relative20_pp':4.},'liquidity':{'avg_turnover20':2e7}}
 def test_ready_requires_all(self):self.assertEqual(m.assessment(self.row())['state'],'ready')
 def test_stale_blocks(self):
  r=self.row();r['status']='incomplete';self.assertEqual(m.assessment(r)['state'],'data')
 def test_unverified_is_not_ready(self):
  r=self.row();r['official_history']['matched']=[];self.assertEqual(m.assessment(r)['state'],'verify')
 def test_revision_risk_not_hidden(self):
  r=self.row();r['forecasts']['eps_revision30_pct']=-4;self.assertEqual(m.assessment(r)['state'],'risk')
 def test_dispersion(self):
  r=self.row();r['targets']['spread']=1;self.assertEqual(m.assessment(r)['state'],'risk')
 def test_cash(self):
  r=self.row();r['history']['fcf']=-1;self.assertEqual(m.assessment(r)['state'],'risk')
 def test_liquidity(self):
  r=self.row();r['liquidity']['avg_turnover20']=20;self.assertEqual(m.assessment(r)['state'],'risk')
 def test_missing_never_zero_success(self):
  r=self.row();r['balance']['net_debt_ebitda']=None;self.assertEqual(m.assessment(r)['state'],'data')
 def test_sample(self):
  r=self.row();r['forecasts']['analysts']=2;self.assertEqual(m.assessment(r)['state'],'data')
 def test_price_boundary(self):
  r=self.row();r['targets']['median_gap_pct']=19.9;self.assertEqual(m.assessment(r)['state'],'price')
 def test_micro(self):
  r=self.row();r['size_group']='micro';self.assertEqual(m.assessment(r)['state'],'risk')
 def test_conflict(self):
  r=self.row();r['official_history']['issues']=['eps'];self.assertEqual(m.assessment(r)['state'],'risk')
 def test_recent_split(self):
  r=self.row();r['technical']['recent_split']=True;self.assertEqual(m.assessment(r)['state'],'risk')
 def test_score_no_missing_rescale(self):self.assertEqual(m.priority_score({})['score'],0)
 def test_score_bounds(self):
  s=m.priority_score(self.row());self.assertLessEqual(s['score'],100);self.assertEqual(sum(x['maximum'] for x in s['factors']),100)
 def test_forecast_not_probability(self):self.assertFalse(m.assessment(self.row())['forecast_independently_verified'])
 def test_condition_formula(self):self.assertAlmostEqual(m.assessment(self.row())['price_condition']['move_pct'],8.333333,places=5)
 def test_size_actual(self):
  self.assertEqual(m.size_group(3e9,'US'),'mid');self.assertEqual(m.size_group(None,'US'),'unknown');self.assertEqual(m.size_group(2e12,'KR'),'mid')
 def test_failed_row_safe(self):self.assertEqual(m.assessment({'status':'failed'})['state'],'data')

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Policy))
 Path('stock-opportunity-tests.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
