"""Offline evidence regressions; fixtures are synthetic, never market outputs."""
import copy
import sys
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

import stock_price_evidence as price
import stock_fundamental_extensions as financial
import update_stock_decisions as decision
import update_stock_opportunities as opportunity
import build_stock_decision_guide as guide


def metadata(symbol='AAPL', market='US', currency='USD'):
    return {'symbol': symbol, 'currency': currency, 'instrumentType': 'INDEX' if symbol.startswith('^') else 'EQUITY',
            'exchangeName': {'^KS11': 'KSC', '^KQ11': 'KOE', '^GSPC': 'SNP', '^IXIC': 'NIM'}.get(symbol, 'NMS' if market=='US' else 'KSC'),
            'exchangeTimezoneName': 'America/New_York' if market=='US' else 'Asia/Seoul'}


class Ticker:
    def __init__(self, replies, meta=None):
        self.replies=list(replies);self.meta=meta or metadata();self.calls=[]
        self._price_history=SimpleNamespace(_history_metadata=None)

    def history(self, **kwargs):
        self.calls.append(kwargs)
        value=self.replies.pop(0)
        if isinstance(value, Exception):raise value
        self._price_history._history_metadata=copy.deepcopy(self.meta)
        return pd.DataFrame({'Close':[close for day,close in value]}, index=pd.to_datetime([day for day,close in value]))


def proof(rows, symbol='AAPL', market='US', currency='USD'):
    return price.daily_change(rows,market,symbol,currency,price.response_identity(metadata(symbol,market,currency),symbol,market,currency))


class DailyChangeTests(unittest.TestCase):
    def test_technical_window_cannot_hide_missing_trading_session(self):
        cal=price.exchange_calendar('US',2026)
        dates=list(cal.sessions_in_range('2026-07-01','2026-11-05'))
        rows=[{'date':str(day.date()),'open':100,'high':102,'low':99,'close':101,'volume':1000,'split':0} for day in dates]
        self.assertEqual(decision.technical(rows,rows,'US')['status'],'ok')
        missing=rows[:-3]+rows[-2:]
        self.assertEqual(decision.technical(missing,rows,'US')['status'],'missing')

    def test_benchmark_gap_cannot_extend_twenty_session_comparison(self):
        cal=price.exchange_calendar('US',2026)
        dates=list(cal.sessions_in_range('2026-07-01','2026-11-05'))
        rows=[{'date':str(day.date()),'open':100,'high':102,'low':99,'close':101,'volume':1000,'split':0} for day in dates]
        benchmark=[row for row in rows if row['date']!=rows[-21]['date']]
        self.assertIsNone(decision.technical(rows,benchmark,'US')['relative20_pp'])

    def test_actual_previous_exchange_session_not_calendar_yesterday(self):
        # US Independence Day + weekend: Thursday to Monday is one session.
        result=proof([{'date':'2025-07-03','close':100},{'date':'2025-07-07','close':103}])
        self.assertEqual(result['status'],'verified')
        self.assertEqual(result['expected_previous_session'],'2025-07-03')
        self.assertAlmostEqual(result['change_1d_pct'],3)

    def test_two_day_gap_is_not_one_day_return(self):
        result=proof([{'date':'2026-11-03','close':100},{'date':'2026-11-05','close':110}])
        self.assertEqual(result['expected_previous_session'],'2026-11-04')
        self.assertFalse(result['consecutive_sessions'])
        self.assertIsNone(result['change_1d_pct'])

    def test_latest_session_split_does_not_create_apparent_crash(self):
        result=proof([{'date':'2026-11-04','close':100},{'date':'2026-11-05','close':50,'split':2}])
        self.assertEqual(result['reason'],'latest_session_split_requires_basis_review')
        self.assertIsNone(result['change_1d_pct'])

    def test_missing_zero_nonfinite_previous_values_are_unknown(self):
        for close in (None,0,-1,float('nan'),float('inf'),True):
            with self.subTest(close=close):
                result=proof([{'date':'2026-11-04','close':close},{'date':'2026-11-05','close':100}])
                self.assertIsNone(result['change_1d_pct'])

    def test_identity_and_currency_proof_required(self):
        rows=[{'date':'2026-11-04','close':100},{'date':'2026-11-05','close':101}]
        for evidence in ({},{'source_identity_verified':True,'provider_symbol':'OTHER','market':'US','currency':'USD'},
                         {'source_identity_verified':True,'provider_symbol':'AAPL','market':'US','currency':'CNY'}):
            self.assertIsNone(price.daily_change(rows,'US','AAPL','USD',evidence)['change_1d_pct'])

    def test_history_only_means_as_of_observed_day(self):
        result=proof([{'date':'2026-11-03','close':100},{'date':'2026-11-04','close':101}])
        self.assertEqual(result['price_session'],'2026-11-04')
        self.assertEqual(result['status'],'verified')

    def test_kr_calendar_and_currency(self):
        result=proof([{'date':'2026-11-05','close':201500},{'date':'2026-11-06','close':210000}], '005930.KS','KR','KRW')
        self.assertEqual(result['status'],'verified')
        self.assertAlmostEqual(result['change_1d_pct'],(210000/201500-1)*100)


class FetchTests(unittest.TestCase):
    def test_current_reply_is_not_retried(self):
        ticker=Ticker([[('2026-11-05',100)]])
        frame,evidence=price.fetch_daily_history(ticker,'AAPL','US','2026-11-05')
        self.assertEqual(len(ticker.calls),1)
        self.assertEqual(evidence['latest_completed_session'],'2026-11-05')
        self.assertFalse(evidence['stale_retry_attempted'])

    def test_actual_stale_reply_gets_one_absolute_end_exclusive_retry(self):
        ticker=Ticker([[('2026-11-04',100)],[('2026-11-04',100),('2026-11-05',101)]])
        frame,evidence=price.fetch_daily_history(ticker,'AAPL','US','2026-11-05')
        self.assertEqual(len(ticker.calls),2)
        self.assertEqual(ticker.calls[1]['end'],'2026-11-06')
        self.assertNotIn('period',ticker.calls[1])
        self.assertFalse(ticker.calls[1]['auto_adjust'])
        self.assertFalse(ticker.calls[1]['repair'])
        self.assertEqual(evidence['selected_attempt'],2)
        self.assertEqual(frame.index[-1].date().isoformat(),'2026-11-05')

    def test_still_old_after_retry_stays_old(self):
        ticker=Ticker([[('2026-11-04',100)],[('2026-11-04',100)]])
        frame,evidence=price.fetch_daily_history(ticker,'AAPL','US','2026-11-05')
        self.assertEqual(len(ticker.calls),2)
        self.assertEqual(evidence['latest_completed_session'],'2026-11-04')
        self.assertEqual(frame.index[-1].date().isoformat(),'2026-11-04')

    def test_failed_retry_preserves_real_historical_reply_with_failure(self):
        ticker=Ticker([[('2026-11-04',100)],TimeoutError('bounded fixture')])
        frame,evidence=price.fetch_daily_history(ticker,'AAPL','US','2026-11-05')
        self.assertEqual(evidence['selected_attempt'],1)
        self.assertEqual(evidence['attempts'][1]['status'],'failed')
        self.assertEqual(evidence['latest_completed_session'],'2026-11-04')

    def test_wrong_response_identity_currency_exchange_and_type_fail_closed(self):
        for field,value in (('symbol','MSFT'),('currency','CNY'),('exchangeName','KSC'),
                            ('exchangeTimezoneName','Asia/Seoul'),('instrumentType','ETF')):
            with self.subTest(field=field):
                meta=metadata();meta[field]=value
                ticker=Ticker([[('2026-11-05',100)]],meta)
                with self.assertRaisesRegex(ValueError,'provider_history_'):
                    price.fetch_daily_history(ticker,'AAPL','US','2026-11-05')
                self.assertEqual(len(ticker.calls),1)

    def test_partial_today_is_never_relabelled_as_completed(self):
        ticker=Ticker([[('2026-11-04',100),('2026-11-05',999)]])
        frame,evidence=price.fetch_daily_history(ticker,'AAPL','US','2026-11-04')
        self.assertEqual(evidence['latest_completed_session'],'2026-11-04')


class FinancialBasisTests(unittest.TestCase):
    def estimates(self):return {'0y':{'avg':10},'+1y':{'avg':12,'low':11,'high':13}}

    def test_same_currency_next_fy_pe_is_saved_price_divided_by_plus1y(self):
        f=decision.forecast_data(self.estimates(),{}, {'currency':'USD','financialCurrency':'USD'},120)
        self.assertEqual(f['next_fy_pe'],10)
        self.assertTrue(f['comparison_currency_verified'])

    def test_unknown_or_mismatched_currency_is_not_foreign_currency_pe(self):
        for info in ({},{'financialCurrency':'USD'},{'currency':'USD','financialCurrency':'CNY'}):
            f=decision.forecast_data(self.estimates(),{},info,120)
            self.assertIsNone(f['next_fy_pe'])
            self.assertEqual(f['status'],'currency_mismatch')

    def test_provider_forward_pe_never_overrides_same_fy_calculation(self):
        row={'symbol':'A','forecasts':{'next_fy_pe':10,'next_fy_pe_basis':'fixture'},'history':{'roe':50}}
        financial.add_profile(row,{'forwardPE':99,'returnOnEquity':0,'financialCurrency':'USD','currency':'USD'})
        self.assertEqual(row['valuation']['forward_pe'],10)
        self.assertEqual(row['valuation']['provider_forward_pe'],99)
        self.assertEqual(row['valuation']['return_on_equity_pct'],0)
        self.assertEqual(row['valuation']['annual_end_equity_roe_pct'],50)
        values=guide.valuation_reading(row,{})['items']
        self.assertEqual(next(x for x in values if x['term']=='예상 PER')['value'],10)

    def test_no_unknown_provider_period_fallback_in_guide(self):
        result=guide.valuation_reading({'valuation':{'forward_pe':99},'history':{'roe':50}}, {})
        self.assertIsNone(next(x for x in result['items'] if x['term']=='예상 PER')['value'])

    def test_same_fy_different_net_income_scope_cannot_import_growth(self):
        base={'filing_period':'2025-12-31','currency':'KRW','net_income':100,'fcf':10,'capex':5}
        source={'filing_period':'2025-12-31','currency':'KRW','net_income':95,
                'net_income_previous':90,'net_income_growth':(95/90-1)*100,'equity':200,'roe':47.5}
        result=financial.merge_supplemental_history(base,source)
        self.assertEqual(result['net_income'],100)
        self.assertNotIn('net_income_growth',result)
        self.assertNotIn('net_income_previous',result)
        self.assertNotIn('roe',result)
        self.assertNotIn('cfo',result)
        self.assertTrue(result['supplemental_excluded_fields'])
        self.assertEqual(base['net_income'],100)

    def test_matching_current_and_comparison_basis_can_import_growth(self):
        base={'filing_period':'2025-12-31','currency':'USD','net_income':100}
        source={**base,'net_income_previous':80,'net_income_growth':25,'equity':200,'roe':50}
        result=financial.merge_supplemental_history(base,source)
        self.assertEqual(result['net_income_growth'],25)
        self.assertEqual(result['net_income_previous'],80)
        self.assertEqual(result['roe'],50)

    def test_existing_growth_disagreement_does_not_import_another_denominator(self):
        base={'filing_period':'2025-12-31','currency':'USD','revenue':100,'revenue_growth':10}
        source={**base,'revenue_previous':80,'revenue_growth':25}
        result=financial.merge_supplemental_history(base,source)
        self.assertEqual(result['revenue_growth'],10)
        self.assertNotIn('revenue_previous',result)

    def test_different_period_or_currency_cannot_join(self):
        base={'filing_period':'2025-12-31','currency':'USD','net_income':100}
        for source in ({'filing_period':'2024-12-31','currency':'USD','cfo':200},
                       {'filing_period':'2025-12-31','currency':'CNY','cfo':200}):
            self.assertNotIn('cfo',financial.merge_supplemental_history(base,source))


class RawCollectorContractTests(unittest.TestCase):
    class CompanyTicker(Ticker):
        ticker='AAPL'
        calendar={}
        def history(self, **kwargs):
            frame=super().history(**kwargs)
            frame['Open']=frame['Close'];frame['High']=frame['Close']+1
            frame['Low']=frame['Close']-1;frame['Volume']=1000;frame['Stock Splits']=0
            return frame
        def get_info(self):return {'symbol':'AAPL','quoteType':'EQUITY','currency':'USD','financialCurrency':'USD'}
        def get_earnings_estimate(self):return pd.DataFrame()
        def get_eps_trend(self):return pd.DataFrame()
        def get_analyst_price_targets(self):return {}
        def get_income_stmt(self,**kwargs):return pd.DataFrame()

    def collect(self,ticker):
        spec=['AAPL','Apple','US','test','AAPL','fixture','https://example.invalid']
        with patch.dict(sys.modules,{'yfinance':SimpleNamespace(Ticker=lambda symbol:ticker)}), patch.object(opportunity.time,'sleep'):
            return opportunity.collect(spec,{}, {},[],datetime(2026,11,6,8,tzinfo=timezone.utc))

    def test_raw_price_and_daily_proof_use_actual_successful_retry(self):
        result=self.collect(self.CompanyTicker([[('2026-11-04',100)],[('2026-11-04',100),('2026-11-05',101)]]))
        self.assertEqual(result['price'],101)
        self.assertEqual(result['price_session'],'2026-11-05')
        self.assertEqual(result['price_source']['selected_attempt'],2)
        self.assertEqual(result['daily_change']['status'],'verified')
        self.assertEqual(result['daily_change']['close'],result['price'])
        self.assertEqual(result['history']['currency'],'USD')
        self.assertEqual(result['balance']['currency'],'USD')

    def test_raw_current_price_does_not_make_missing_previous_session_daily(self):
        result=self.collect(self.CompanyTicker([[('2026-11-03',100),('2026-11-05',110)]]))
        self.assertEqual(result['status'],'current')
        self.assertEqual(result['daily_change']['status'],'unavailable')
        self.assertIsNone(result['daily_change']['change_1d_pct'])

    def test_wrong_response_issuer_cannot_become_a_company_price(self):
        meta=metadata();meta['symbol']='MSFT'
        result=self.collect(self.CompanyTicker([[('2026-11-05',101)]],meta))
        self.assertIsNone(result['price'])
        self.assertEqual(result['status'],'incomplete')
        self.assertIn('price_source_identity_unverified',result['price_integrity']['issues'])


if __name__=='__main__':unittest.main()
