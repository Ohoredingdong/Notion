"""Offline regressions for source-preserved annual comparison inputs."""
import copy
import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

import stock_revenue_evidence as evidence
import update_stock_opportunities as opportunities
import update_stock_decisions as decisions

spec = importlib.util.spec_from_file_location('reference_radar_collector',
                                             Path(__file__).with_name('update-stock-value-radar.py'))
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def yahoo_pair(**changes):
    args = dict(symbol='AAPL', source_name='Yahoo Finance',
                source_url='https://finance.yahoo.com/quote/AAPL/financials/',
                provider_symbol='AAPL', currency='USD', account='TotalRevenue',
                current={'value': 478834000000, 'period': '2026-09-30', 'account': 'TotalRevenue'},
                prior={'value': 416161000000, 'period': '2025-09-30', 'account': 'TotalRevenue'},
                metadata={'provider_symbol': 'AAPL', 'financial_currency': 'USD',
                          'quote_currency': 'USD', 'quote_type': 'EQUITY', 'frequency': 'yearly'},
                observed_at='2026-11-06T10:00:00+00:00')
    args.update(changes)
    return evidence.revenue_comparison(**args)


class ContractTests(unittest.TestCase):
    def test_two_decimal_growth_preserves_exact_denominator(self):
        result = yahoo_pair()
        self.assertEqual(result['revenue_previous'], 416161000000)
        self.assertEqual(result['revenue_growth'], 15.06)
        self.assertNotEqual(result['revenue_previous'], 478834000000/1.1506)
        self.assertEqual(result['revenue_growth_evidence']['status'], 'verified')
        self.assertEqual(evidence.comparison_issues(result['revenue_growth_evidence'],
                         symbol='AAPL', currency='USD', current=478834000000,
                         period='2026-09-30', previous=416161000000, published_growth=15.06), [])

    def test_existing_serializer_does_not_destroy_recheck(self):
        result = decisions.clean(yahoo_pair())
        self.assertEqual(evidence.comparison_issues(result['revenue_growth_evidence']), [])

    def test_no_relative_tolerance_can_hide_changed_current_amount(self):
        e = yahoo_pair()['revenue_growth_evidence']
        self.assertIn('current_amount_mismatch', evidence.comparison_issues(e, current=478834000001))
        self.assertIn('previous_amount_mismatch', evidence.comparison_issues(e, previous=416161000001))

    def test_missing_zero_nonfinite_and_negative_prior_are_withheld(self):
        for value in (None, 0, -100, True, float('nan'), float('inf')):
            with self.subTest(value=value):
                result = yahoo_pair(prior={'value': value, 'period': '2025-09-30', 'account': 'TotalRevenue'})
                self.assertIsNone(result['revenue_growth'])
                self.assertIsNone(result['revenue_previous'])
                self.assertEqual(result['revenue_growth_evidence']['status'], 'withheld')

    def test_other_account_is_not_a_comparable_revenue_denominator(self):
        result = yahoo_pair(prior={'value': 416161000000, 'period': '2025-09-30', 'account': 'OperatingRevenue'})
        self.assertIn('account_mismatch', result['revenue_growth_evidence']['issues'])
        self.assertIsNone(result['revenue_growth'])

    def test_missing_currency_is_not_assumed_to_be_quote_currency(self):
        result = yahoo_pair(currency=None)
        self.assertIsNone(result['revenue_growth'])
        self.assertIn('source_currency_unverified', result['revenue_growth_evidence']['issues'])

    def test_wrong_metadata_identity_is_withheld(self):
        for key, value in (('provider_symbol', 'MSFT'), ('financial_currency', 'CNY'),
                           ('quote_type', 'ETF'), ('frequency', 'quarterly')):
            args = copy.deepcopy(yahoo_pair()['revenue_growth_evidence']['source_rows']['metadata'])
            args[key] = value
            self.assertIsNone(yahoo_pair(metadata=args)['revenue_growth'])

    def test_valid_provider_payload_cannot_be_attached_to_another_symbol(self):
        self.assertIsNone(yahoo_pair(symbol='MSFT')['revenue_growth'])

    def test_future_observation_and_wrong_symbol_url_fail_closed(self):
        self.assertIsNone(yahoo_pair(observed_at='2099-11-06T10:00:00+00:00')['revenue_growth'])
        self.assertIsNone(yahoo_pair(source_url='https://finance.yahoo.com/quote/MSFT/financials/')['revenue_growth'])

    def test_quarter_or_skipped_year_is_not_annual_growth(self):
        for period in ('2026-06-30', '2024-09-30', '2027-09-30', None):
            result = yahoo_pair(prior={'value': 416161000000, 'period': period, 'account': 'TotalRevenue'})
            self.assertIsNone(result['revenue_growth'])
            self.assertIn('annual_periods_not_consecutive', result['revenue_growth_evidence']['issues'])

    def test_tampered_saved_source_rows_are_rejected(self):
        e = yahoo_pair()['revenue_growth_evidence']
        e['source_rows']['prior']['value'] += 1
        self.assertIn('source_rows_digest_mismatch', evidence.comparison_issues(e))

    def test_unrelated_symbol_currency_period_and_display_percentage_are_rejected(self):
        e = yahoo_pair()['revenue_growth_evidence']
        for args, issue in (({'symbol':'MSFT'}, 'symbol_mismatch'),
                            ({'currency':'KRW'}, 'currency_mismatch'),
                            ({'period':'2025-09-30'}, 'current_period_mismatch'),
                            ({'published_growth':15.07}, 'displayed_growth_mismatch')):
            self.assertIn(issue, evidence.comparison_issues(e, **args))


class FakeTicker:
    ticker = 'AAPL'
    calendar = {}
    def __init__(self, *, currency='USD', source_symbol='AAPL', prior='2025-09-30'):
        self.currency, self.source_symbol = currency, source_symbol
        self.inc = pd.DataFrame({'2026-09-30': {'TotalRevenue': 478834000000.0},
                                 prior: {'TotalRevenue': 416161000000.0}})
        self.inc.columns = pd.to_datetime(self.inc.columns)
    def get_info(self):
        return {'symbol':self.source_symbol, 'quoteType':'EQUITY',
                'financialCurrency': self.currency, 'currency':'USD'}
    def get_income_stmt(self, **kwargs): return self.inc
    def get_cashflow(self, **kwargs): return pd.DataFrame()
    def get_earnings_estimate(self): return pd.DataFrame()
    def get_eps_trend(self): return pd.DataFrame()
    def get_analyst_price_targets(self): return {}


class YahooCollectorTests(unittest.TestCase):
    def collect(self, ticker):
        with patch.dict(sys.modules, {'yfinance':SimpleNamespace(Ticker=lambda symbol:ticker)}):
            return reference.stock_yahoo('AAPL', 'Apple')

    def test_actual_annual_dataframe_pair_is_kept(self):
        result = self.collect(FakeTicker())
        self.assertEqual(result['revenue_previous'], 416161000000)
        self.assertEqual(result['revenue_previous_period'], '2025-09-30')
        self.assertEqual(result['revenue_growth'], 15.06)
        self.assertEqual(evidence.comparison_issues(result['revenue_growth_evidence']), [])

    def test_financial_currency_comes_from_metadata(self):
        result = self.collect(FakeTicker(currency='CNY'))
        self.assertEqual(result['currency'], 'CNY')
        self.assertEqual(result['revenue_growth_evidence']['source']['currency'], 'CNY')

    def test_wrong_company_response_cannot_generate_evidence(self):
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.collect(FakeTicker(source_symbol='MSFT'))

    def test_nonconsecutive_annual_columns_remain_withheld(self):
        self.assertIsNone(self.collect(FakeTicker(prior='2024-09-30'))['revenue_growth'])


class SecCollectorTests(unittest.TestCase):
    def payload(self):
        def observation(value, start, end, accession):
            return {'val':value,'start':start,'end':end,'accn':accession,
                    'fp':'FY','form':'10-K','filed':'2026-08-01'}
        return {'cik':789019,'facts':{'us-gaap':{'Revenues':{'units':{'USD':[
            observation(331839000000,'2025-07-01','2026-06-30','same-annual-filing'),
            observation(281724000000,'2024-07-01','2025-06-30','same-annual-filing'),
            dict(observation(999999999999,'2024-07-01','2025-06-30','another-filing'), filed='2026-09-01'),
        ]}}}}}

    def collect(self, data):
        with patch.object(reference, 'get_json', return_value=data):
            return reference.stock_sec('MSFT','Microsoft',789019)

    def test_same_filing_prior_wins_over_later_unrelated_restatement(self):
        result = self.collect(self.payload())
        self.assertEqual(result['revenue_previous'], 281724000000)
        self.assertEqual(result['revenue_growth'], 17.79)
        self.assertEqual(evidence.comparison_issues(result['revenue_growth_evidence']), [])

    def test_missing_same_filing_comparison_is_not_backfilled(self):
        data = self.payload()
        data['facts']['us-gaap']['Revenues']['units']['USD'].pop(1)
        result = self.collect(data)
        self.assertIsNone(result['revenue_previous'])
        self.assertIsNone(result['revenue_growth'])

    def test_wrong_cik_fails_before_any_values_are_returned(self):
        data = self.payload(); data['cik'] = 320193
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            self.collect(data)


class DartCollectorTests(unittest.TestCase):
    def row(self):
        return {'corp_code':'00126380','stock_code':'005930','bsns_year':'2025',
                'reprt_code':'11011','fs_div':'CFS','sj_div':'IS','currency':'KRW',
                'rcept_no':'20260310002820','account_nm':'매출액',
                'thstrm_dt':'2025.01.01 ~ 2025.12.31','frmtrm_dt':'2024.01.01 ~ 2024.12.31',
                'thstrm_amount':'333,605,938,000,000','frmtrm_amount':'300,870,903,000,000'}

    def collect(self, rows):
        return reference.dart_build('005930','삼성전자','00126380',rows,2025)

    def test_actual_same_response_comparative_amount_and_receipt_are_kept(self):
        result = self.collect([self.row()])
        self.assertEqual(result['revenue_previous'],300870903000000)
        self.assertEqual(result['revenue_growth'],10.88)
        self.assertEqual(result['revenue_previous_period'],'2024-12-31')
        self.assertEqual(result['filing_url'],'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260310002820')
        self.assertEqual(evidence.comparison_issues(result['revenue_growth_evidence']), [])

    def test_other_company_report_year_or_statement_basis_is_never_joined(self):
        for field, value in (('corp_code','other'),('stock_code','000660'),
                             ('bsns_year','2024'),('reprt_code','11014'),('fs_div','OFS'),('sj_div','BS')):
            row = self.row(); row[field] = value
            result = self.collect([row])
            self.assertIsNone(result['revenue_growth'])
            self.assertIsNone(result['revenue'])

    def test_missing_or_conflicting_period_and_currency_are_withheld(self):
        for field, value in (('thstrm_dt',None),('frmtrm_dt','2023.01.01 ~ 2023.12.31'),
                             ('currency',None),('rcept_no','unknown')):
            row = self.row(); row[field] = value
            self.assertIsNone(self.collect([row])['revenue_growth'])

    def test_conflicting_duplicate_accounts_are_not_first_row_wins(self):
        row = self.row(); different = dict(row, frmtrm_amount='1')
        result = self.collect([row,different])
        self.assertIsNone(result['revenue_growth'])
        self.assertIsNone(result['revenue'])


class PropagationTests(unittest.TestCase):
    def collect(self, base):
        ticker = FakeTicker()
        with patch.dict(sys.modules, {'yfinance':SimpleNamespace(Ticker=lambda symbol:ticker)}), \
             patch.object(opportunities.core,'fetch_daily_history',return_value=(None,{})), \
             patch.object(opportunities.core,'latest_session',return_value={'date':'2026-11-05'}), \
             patch.object(opportunities.time,'sleep'):
            return opportunities.collect(('AAPL','Apple','US','Tech','AAPL','기존',None),
                                         base, {}, [], datetime(2026,11,6,tzinfo=timezone.utc))

    def test_original_evidence_is_forwarded_without_overwriting_it(self):
        base = {'symbol':'AAPL','filing_period':'2026-09-30','currency':'USD','revenue':478834000000,
                **yahoo_pair()}
        before = copy.deepcopy(base)
        result = self.collect(base)
        self.assertEqual(result['history']['revenue_growth_evidence'], base['revenue_growth_evidence'])
        self.assertEqual(result['history']['revenue_previous'],416161000000)
        self.assertEqual(base, before)

    def test_legacy_base_without_observations_does_not_acquire_fabricated_evidence(self):
        result = self.collect({'symbol':'AAPL','filing_period':'2026-09-30','currency':'USD',
                               'revenue':478834000000,'revenue_growth':15.06})
        self.assertNotIn('revenue_previous',result['history'])
        self.assertNotIn('revenue_growth_evidence',result['history'])


if __name__ == '__main__':
    unittest.main()
