import unittest
from stock_reading_depth import ratios,parse_dart,growth,num
class Reading(unittest.TestCase):
 def test_average_not_closing_equity(self):
  r=ratios([{'period':'2025-12-31','owner_income':10,'owner_equity':50},{'period':'2024-12-31','owner_income':8,'owner_equity':100}]);self.assertAlmostEqual(r[0]['roe_average'],1000/75)
 def test_zero_income(self):
  r=ratios([{'period':'2025-12-31','owner_income':0,'owner_equity':50},{'period':'2024-12-31','owner_equity':50}]);self.assertEqual(r[0]['roe_average'],0)
 def test_equity_negative(self):
  r=ratios([{'period':'2025-12-31','owner_income':10,'owner_equity':-50},{'period':'2024-12-31','owner_equity':50}]);self.assertIsNone(r[0]['roe_average'])
 def test_missing_not_total_scope(self):
  r=ratios([{'period':'2025-12-31','net_income':10,'owner_equity':50},{'period':'2024-12-31','owner_equity':50}]);self.assertIsNone(r[0]['roe_average'])
 def test_equity_shrunk(self):
  r=ratios([{'period':'2025-12-31','owner_income':5,'owner_equity':25},{'period':'2024-12-31','owner_income':5,'owner_equity':50}]);self.assertIn('이익은 늘지',r[0]['roe_driver'])
 def test_missing_not_zero(self):self.assertIsNone(num(None));self.assertIsNone(num(True));self.assertIsNone(growth(1,-5))
 def test_wrong_issuer(self):
  with self.assertRaises(ValueError):parse_dart({'status':'000','list':[{'corp_code':'wrong'}]},'123',2025,'CFS')
 def fixture(self):
  return {'status':'000','list':[{'corp_code':'123','bsns_year':'2025','reprt_code':'11011','currency':'KRW','rcept_no':'20260301000000','sj_div':'IS','account_id':'ifrs-full_Revenue','account_nm':'매출액','thstrm_amount':'300','frmtrm_amount':'200','bfefrmtrm_amount':'100'}]}
 def test_three_columns(self):self.assertEqual([r['revenue'] for r in parse_dart(self.fixture(),'123',2025,'CFS')],[300,200,100])
 def test_missing_capex_no_fake_fcf(self):self.assertIsNone(parse_dart(self.fixture(),'123',2025,'CFS')[0]['fcf'])
 def test_currency(self):
  d=self.fixture();d['list'][0]['currency']='USD'
  with self.assertRaises(ValueError):parse_dart(d,'123',2025,'CFS')
if __name__=='__main__':unittest.main()
