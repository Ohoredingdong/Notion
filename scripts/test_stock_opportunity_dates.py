import unittest,json
from datetime import datetime,timezone
from pathlib import Path
from validate_stock_opportunity_dates import validate_row
class DateTests(unittest.TestCase):
 def row(self):return {'forecasts':{'current_fy_end_provider':'2026-12-31'},'balance':{'asof':'2026-06-30'},'assessment':{'state':'ready','missing':[],'checks':[]},'priority':{'score':85}}
 def runrow(self,row):return validate_row(row,datetime(2026,10,20,tzinfo=timezone.utc))
 def test_current(self):self.assertEqual(self.runrow(self.row())['assessment']['state'],'ready')
 def test_stale_balance(self):
  r=self.row();r['balance']['asof']='2018-09-30';self.assertEqual(self.runrow(r)['assessment']['state'],'data')
 def test_old_forecast(self):
  r=self.row();r['forecasts']['current_fy_end_provider']='2018-12-31';self.assertFalse(self.runrow(r)['assessment']['price_condition_usable'])
 def test_recently_ended_fy(self):
  r=self.row();r['forecasts']['current_fy_end_provider']='2026-09-27';self.assertEqual(self.runrow(r)['period_integrity']['status'],'ok')
 def test_null_not_recent(self):
  r=self.row();r['balance']['asof']=None;self.assertEqual(self.runrow(r)['period_integrity']['status'],'needs_review')
 def test_future_balance(self):
  r=self.row();r['balance']['asof']='2027-06-30';self.assertEqual(self.runrow(r)['assessment']['state'],'data')
 def test_score_hidden_not_renormalized(self):
  r=self.row();r['forecasts']['current_fy_end_provider']='bad';r=self.runrow(r);self.assertIsNone(r['priority']['display_score']);self.assertEqual(r['priority']['score'],85)
 def test_failed_row(self):self.assertEqual(self.runrow({'status':'failed'})['assessment']['state'],'data')
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DateTests))
 Path('stock-opportunity-date-tests.json').write_text(json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'passed':r.wasSuccessful()},indent=2)+'\n')
 raise SystemExit(0 if r.wasSuccessful() else 1)
