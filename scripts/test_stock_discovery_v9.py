import unittest,json
from pathlib import Path
import discover_stock_candidates_v9 as d
import curate_stock_decisions_v9 as c

class Discovery(unittest.TestCase):
 def quote(self):return {'symbol':'ABCD','exchange':'NMS','currency':'USD','quoteType':'EQUITY','shortName':'Example Inc.','marketCap':3e9,'regularMarketPrice':50,'averageDailyVolume3Month':1e6,'epsTrailingTwelveMonths':2,'forwardPE':20,'trailingPE':25,'sector':'Technology'}
 def record(self,s='ABCD',sector='Technology'):
  q=self.quote();q['symbol']=s;q['sector']=sector;return d.normalize(q,'US')
 def test_valid(self):self.assertEqual(d.normalize(self.quote(),'US')['symbol'],'ABCD')
 def test_wrong_currency(self):
  q=self.quote();q['currency']='JPY';self.assertIsNone(d.normalize(q,'US'))
 def test_no_fund(self):
  q=self.quote();q['quoteType']='ETF';self.assertIsNone(d.normalize(q,'US'))
 def test_no_otc(self):
  q=self.quote();q['exchange']='PNK';self.assertIsNone(d.normalize(q,'US'))
 def test_korea_suffix(self):
  q=self.quote();q.update(symbol='123450.KQ',exchange='KOE',currency='KRW',marketCap=2e12);self.assertEqual(d.normalize(q,'KR')['source_symbol'],'123450.KQ')
 def test_missing_price(self):
  q=self.quote();q.pop('regularMarketPrice');self.assertIsNone(d.normalize(q,'US'))
 def test_no_nano(self):
  q=self.quote();q['marketCap']=2000;self.assertIsNone(d.normalize(q,'US'))
 def test_do_not_duplicate_fixed(self):self.assertEqual(d.pick_additions([self.record()],{'ABCD'}),[])
 def test_financials_model_exclusion(self):self.assertEqual(d.pick_additions([self.record(sector='Financial Services')],set()),[])
 def test_missing_eps_not_pass(self):
  r=self.record();r['ttm_eps']=None;self.assertEqual(d.pick_additions([r],set()),[])
 def test_liquidity(self):
  r=self.record();r['approx_turnover']=10;self.assertEqual(d.pick_additions([r],set()),[])
 def test_limit(self):self.assertEqual(len(d.pick_additions([self.record(x) for x in ['AAA','BBB','CCC']],set(),2)),2)
 def test_brief_does_not_promote_risk(self):
  rows=[{'symbol':'A','status':'current','sector':'X','period_integrity':{'status':'ok'},'assessment':{'state':'risk'},'priority':{'display_score':100}}];self.assertEqual(c.candidates(rows,{'ready','verify'}),[])
 def test_brief_does_not_promote_bad_period(self):
  rows=[{'symbol':'A','status':'current','sector':'X','period_integrity':{'status':'needs_review'},'assessment':{'state':'ready'},'priority':{'display_score':100}}];self.assertEqual(c.candidates(rows,{'ready','verify'}),[])
 def test_brief_ready_before_unverified(self):
  def row(s,state,score):return {'symbol':s,'status':'current','sector':s,'period_integrity':{'status':'ok'},'assessment':{'state':state},'priority':{'display_score':score}}
  self.assertEqual(c.candidates([row('A','verify',100),row('B','ready',70)],{'ready','verify'})[0]['symbol'],'B')

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Discovery))
 Path('stock-opportunity-discovery-tests.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
