import unittest
import scripts.build_stock_recommendations as m
class RecommendationTests(unittest.TestCase):
 def base(self):
  row={'symbol':'X','name':'X','market':'US','sector':'기술','currency':'USD','price':100,'price_session':'2026-10-20','status':'current','period_integrity':{'status':'ok'},'model_integrity':{'status':'ok'},'assessment':{'checks':[{'key':'liquidity','ok':True}]},'balance':{'net_debt_ebitda':0.5},'forecasts':{'eps_growth_next_fy_pct':20,'eps_revision30_pct':1,'analysts':10,'spread':.2,'next_fy_pe':15},'targets':{'median_gap_pct':25},'history':{'quality_flags':[]}}
  case={'official':{},'official_comparison':[],'peer_context':None}
  depth={'series':[{'period':'2025-12-31','revenue':100,'operating_income':20,'net_income':15,'cfo':20,'fcf':12,'roe_average':18,'cfo_to_profit':1.3,'revenue_growth':10},{'period':'2024-12-31','revenue':90,'operating_income':18,'net_income':14,'cfo':18,'fcf':10},{'period':'2023-12-31','revenue':80,'operating_income':16,'net_income':12,'cfo':16,'fcf':9}]}
  return row,case,depth
 def test_recommend(self):
  r,c,d=self.base();x=m.evaluate(r,c,d,{'status':'ok','scanned_at':'2099-01-01T00:00:00+00:00','events':[]});self.assertIn(x['grade'],('우선 추천','추천'))
 def test_negative_fcf_blocks(self):
  r,c,d=self.base();d['series'][0]['fcf']=-1;x=m.evaluate(r,c,d,{'status':'ok','scanned_at':'2099-01-01T00:00:00+00:00','events':[]});self.assertEqual(x['grade'],'제외')
 def test_low_analyst_count_blocks(self):
  r,c,d=self.base();r['forecasts']['analysts']=2;x=m.evaluate(r,c,d,{'status':'ok','scanned_at':'2099-01-01T00:00:00+00:00','events':[]});self.assertEqual(x['grade'],'제외')
 def test_bad_pe_blocks(self):
  r,c,d=self.base();r['forecasts']['next_fy_pe']=2;x=m.evaluate(r,c,d,{'status':'ok','scanned_at':'2099-01-01T00:00:00+00:00','events':[]});self.assertEqual(x['grade'],'제외')
 def test_quality_flag_downgrades(self):
  r,c,d=self.base();r['history']['quality_flags']=['재고 급증'];x=m.evaluate(r,c,d,{'status':'ok','scanned_at':'2099-01-01T00:00:00+00:00','events':[]});self.assertNotEqual(x['grade'],'우선 추천')
 def test_target_gap_cannot_dominate(self):
  r,c,d=self.base();r['targets']['median_gap_pct']=500;r['forecasts']['next_fy_pe']=55;x=m.evaluate(r,c,d,{'status':'ok','scanned_at':'2099-01-01T00:00:00+00:00','events':[]});self.assertLess(x['scores']['valuation'],20)
 def test_korea_requires_dart(self):
  r,c,d=self.base();r['market']='KR';r['currency']='KRW';x=m.evaluate(r,c,d);self.assertEqual(x['grade'],'제외')
 def test_event_warning_downgrades(self):
  r,c,d=self.base();x=m.evaluate(r,c,d,{'status':'ok','scanned_at':'2099-01-01T00:00:00+00:00','events':[{'severity':'medium','category':'labor_dispute','title':'총파업 연기·노사갈등 지속'}]});self.assertEqual(x['grade'],'관심')
 def test_missing_event_scan_blocks(self):
  r,c,d=self.base();x=m.evaluate(r,c,d,{});self.assertEqual(x['grade'],'제외')
if __name__=='__main__': unittest.main()
