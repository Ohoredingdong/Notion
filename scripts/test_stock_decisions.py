import unittest,json,sys
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import patch
import update_stock_decisions as m

class MathSafety(unittest.TestCase):
 def test_missing_zero_distinction(self):
  self.assertIsNone(m.num(None));self.assertIsNone(m.num(True));self.assertEqual(m.num(0),0)
 def test_nan(self):self.assertIsNone(m.num(float('nan')))
 def test_negative_eps_growth_not_divided(self):self.assertIsNone(m.change(2,-1))
 def test_percentage(self):self.assertAlmostEqual(m.change(110,100),10)
 def test_clean_json(self):self.assertEqual(json.dumps(m.clean({'x':float('inf')}),allow_nan=False),'{"x": null}')
 def test_targets_not_fair_value(self):
  t=m.target_data({'low':80,'median':120,'mean':120,'high':160},{'numberOfAnalystOpinions':10},100)
  self.assertAlmostEqual(t['review_price_ceiling'],100);self.assertIn('적정가치',t['note'])
 def test_targets_inverted(self):self.assertEqual(m.target_data({'low':200,'median':100,'high':150},{},100)['status'],'missing')
 def test_missing_estimates(self):self.assertEqual(m.forecast_data({}, {}, {},100)['status'],'missing')
 def test_forecast_real_revision(self):
  f=m.forecast_data({'0y':{'avg':10},'+1y':{'avg':12,'low':11,'high':13,'numberOfAnalysts':8}}, {'+1y':{'current':12,'30daysAgo':10}}, {'currency':'USD','financialCurrency':'USD'},100)
  self.assertAlmostEqual(f['eps_revision30_pct'],20);self.assertAlmostEqual(f['next_fy_pe'],100/12)
 def test_no_revisions_is_unknown(self):
  f=m.forecast_data({'+1y':{'avg':12,'low':11,'high':13}},{},{},100)
  self.assertIsNone(f['eps_revision30_pct'])

class DecisionSafety(unittest.TestCase):
 def tech(self):return {'status':'ok','close':100,'ma20':98,'ma60':90,'prior_high20':99,'volume_ratio':2,'relative20_pp':2,'reward_risk':3,'support_loss_pct':5,'support10':95,'recent_split':False}
 def test_short_can_change(self):self.assertEqual(m.short_decision(self.tech(),True)['state'],'conditional')
 def test_short_data_block(self):self.assertEqual(m.short_decision(self.tech(),False)['state'],'data_wait')
 def test_partial_volume_not_good(self):
  t=self.tech();t['volume_ratio']=None;self.assertNotEqual(m.short_decision(t,True)['state'],'conditional')
 def test_earnings_gap_blocks(self):self.assertNotEqual(m.short_decision(self.tech(),True,2)['state'],'conditional')
 def test_split_blocks(self):
  t=self.tech();t['recent_split']=True;self.assertEqual(m.short_decision(t,True)['state'],'data_wait')
 def test_long_no_forecast(self):self.assertEqual(m.long_decision({}, {}, {}, {}, True)['state'],'data_wait')
 def test_long_can_change(self):
  f={'status':'ok','analysts':10,'eps_revision30_pct':2,'eps_growth_next_fy_pct':15,'spread':0.2}
  t={'status':'ok','analysts':10,'median_gap_pct':25,'spread':0.3,'review_price_ceiling':100}
  b={'net_debt_ebitda':1};a={'matched':['revenue','eps','fcf']}
  self.assertEqual(m.long_decision(f,t,b,a,True)['state'],'conditional')
  t['median_gap_pct']=10;self.assertEqual(m.long_decision(f,t,b,a,True)['state'],'price_wait')
  f['eps_revision30_pct']=-5;self.assertEqual(m.long_decision(f,t,b,a,True)['state'],'risk_review')
 def test_period_audit_invalidated(self):
  now=datetime.now(timezone.utc);base={'symbol':'A','filing_period':'2025-12-31','eps':3}
  report={'generated_at':now.isoformat(),'companies':[{'symbol':'A','fields':[{'field':'eps','widget_value':3,'widget_period':'2024-12-31','status':'match'}]}]}
  self.assertEqual(m.historical_audit(base,report,now)['matched'],[])
 def test_changed_input_invalidated(self):
  now=datetime.now(timezone.utc);base={'symbol':'A','filing_period':'2025-12-31','eps':3}
  report={'generated_at':now.isoformat(),'companies':[{'symbol':'A','fields':[{'field':'eps','widget_value':2,'widget_period':'2025-12-31','status':'match'}]}]}
  self.assertEqual(m.historical_audit(base,report,now)['matched'],[])
 def test_old_audit_invalidated(self):
  now=datetime.now(timezone.utc);base={'symbol':'A','filing_period':'2025-12-31','eps':3}
  report={'generated_at':(now-timedelta(days=3)).isoformat(),'companies':[{'symbol':'A','fields':[{'field':'eps','widget_value':3,'widget_period':'2025-12-31','status':'match'}]}]}
  self.assertEqual(m.historical_audit(base,report,now)['matched'],[])

class MarketClock(unittest.TestCase):
 def test_kr_partial_day(self):
  self.assertEqual(m.latest_session('KR',datetime(2026,10,20,2,tzinfo=timezone.utc))['date'],'2026-10-19')
 def test_us_closed(self):
  self.assertEqual(m.latest_session('US',datetime(2026,10,20,2,tzinfo=timezone.utc))['date'],'2026-10-19')
 def test_us_holiday(self):
  self.assertEqual(m.latest_session('US',datetime(2025,7,4,23,tzinfo=timezone.utc))['date'],'2025-07-03')
 def test_exclude_partial_and_bad_bars(self):
  import pandas as pd
  df=pd.DataFrame({'Open':[10,10,10],'High':[12,9,12],'Low':[9,9,9],'Close':[11,11,11],'Volume':[50,50,50]},index=pd.to_datetime(['2026-10-16','2026-10-19','2026-10-20']))
  bars=m.bars_from(df,{'date':'2026-10-19'})
  self.assertEqual(len(bars),1);self.assertEqual(bars[0]['date'],'2026-10-16')

class CollectorCalendarIntegration(unittest.TestCase):
 def ticker(self,market='US',last=None,error=None):
  import pandas as pd
  currency='KRW' if market=='KR' else 'USD'
  symbol='005930.KS' if market=='KR' else 'AAPL'
  end=last or ('2026-11-06' if market=='KR' else '2026-11-05')
  dates=m.exchange_calendar(market,2026).sessions_in_range('2025-11-06',end).as_unit('us')
  frame=pd.DataFrame({'Open':100.,'High':102.,'Low':99.,'Close':101.,'Volume':1000.,'Stock Splits':0.},index=dates)
  metadata={'symbol':symbol,'currency':currency,'instrumentType':'EQUITY',
            'exchangeName':'KSC' if market=='KR' else 'NMS',
            'exchangeTimezoneName':'Asia/Seoul' if market=='KR' else 'America/New_York'}
  ticker=SimpleNamespace(_price_history=SimpleNamespace(_history_metadata=metadata))
  def history(**kwargs):
   if error is not None:raise error
   return frame.copy()
  ticker.history=history
  ticker.get_info=lambda:{'currency':currency,'financialCurrency':currency}
  ticker.get_earnings_estimate=lambda:None
  ticker.get_eps_trend=lambda:None
  ticker.get_analyst_price_targets=lambda:{}
  ticker.calendar={}
  ticker.get_eps_revisions=lambda:None
  ticker.get_news=lambda **kwargs:[]
  return ticker
 def collect(self,ticker,market='US'):
  with patch.dict(sys.modules,{'yfinance':SimpleNamespace(Ticker=lambda symbol:ticker)}),patch.object(m.time,'sleep'):
   return m.collect_symbol('005930' if market=='KR' else 'AAPL','fixture',market,'fixture',{}, {},[],datetime(2026,11,6,11,tzinfo=timezone.utc))
 def test_real_bounded_calendars_accept_provider_history_and_verify_daily_change(self):
  # This full path exposed exchange-calendars 4.11.3 / Pandas 3 date-unit errors.
  # Synthetic prices are fixtures only; dates use the actual installed calendar.
  for market in ('US','KR'):
   with self.subTest(market=market):
    row=self.collect(self.ticker(market),market)
    self.assertEqual(row['status'],'current')
    self.assertEqual(row['price_session'],row['expected_session']['date'])
    self.assertTrue(row['price_source']['source_identity_verified'])
    self.assertEqual(row['daily_change']['status'],'verified')
    self.assertEqual(row['technical']['status'],'ok')
    self.assertEqual(row['errors'],[])
 def test_old_actual_history_cannot_become_current_on_retry(self):
  row=self.collect(self.ticker(last='2026-11-04'))
  self.assertEqual(row['status'],'incomplete')
  self.assertEqual(row['price_session'],'2026-11-04')
  self.assertEqual(row['price_source']['collection_attempts'],2)
  self.assertEqual(row['short']['state'],'data_wait')
 def test_broken_exception_message_preserves_original_failure_and_missing_price(self):
  class BrokenMessageError(Exception):
   def __str__(self):raise AssertionError('fixture formatting failed')
  row=self.collect(self.ticker(error=BrokenMessageError()))
  self.assertEqual(row['status'],'incomplete')
  self.assertIsNone(row['price'])
  self.assertFalse(row['price_source'].get('source_identity_verified',False))
  self.assertEqual(row['short']['state'],'data_wait')
  self.assertEqual(row['errors'][0],{'field':'ohlcv','error':'BrokenMessageError: message_unavailable (AssertionError)'})
 def test_rendered_error_is_bounded_without_losing_type(self):
  self.assertEqual(m.error_text(ValueError('x'*500),8),'ValueError: xxxxxxxx')

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 from pathlib import Path
 Path('stock-decision-tests.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2)+'\n')
 raise SystemExit(not result.wasSuccessful())

