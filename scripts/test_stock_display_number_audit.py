"""Offline adversarial checks for actual display-audit acceptance boundaries."""
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from audit_stock_display_numbers import (Audit, check_daily_change, forecast_counts,
    missing_chart_identities, world_current_counts, check_sentiment_observations,
    reward_risk_interval, check_reward_risk, check_revenue_source_evidence,
    check_official_balance_equation)
from stock_revenue_evidence import revenue_comparison

NOW = datetime(2026, 11, 6, 9, tzinfo=timezone.utc)
PROOF = {'version': 'completed-session-change-v1', 'status': 'verified', 'market': 'US',
         'provider_symbol': 'TEST', 'currency': 'USD', 'source_identity_verified': True,
         'price_session': '2026-11-05', 'close': 110.0, 'previous_session': '2026-11-04',
         'previous_close': 100.0, 'expected_previous_session': '2026-11-04',
         'consecutive_sessions': True, 'change_1d_pct': 10.0, 'basis': 'provider_close_auto_adjust_false'}


class DisplayAuditTests(unittest.TestCase):
    def source_precision_row(self):
        path = Path(__file__).resolve().parents[1] / 'data-evidence/stock-financial-precision-review-20261106.json'
        source = json.loads(path.read_text())['records']['KR:011280']['source_precision']
        return {'symbol': '011280', 'country': 'KR', 'corp_code': '00153524',
                'rcept_no': '20260814003299', 'report_year': 2026, 'report_code': '11012',
                'period_end': '2026-06-30', 'consolidation': 'CFS', 'currency': 'KRW',
                'status': 'available',
                'metrics': {'assets': 698863343000, 'liabilities': 381374004000, 'equity': 317489340000},
                'account_validation': {'balance_sheet': {
                    'status': 'verified_with_declared_precision', 'source_precision': source,
                    'reported_difference': '-1000', 'difference_interval': ['-2500', '500'],
                    'declared_decimals': {'assets': '-3', 'liabilities': '-3', 'equity': '-3'},
                    'reported_values_unchanged': True}}}

    def test_official_source_precision_records_the_residual_and_interval_without_changing_amounts(self):
        row = self.source_precision_row()
        original = copy.deepcopy(row)
        a = Audit()
        self.assertTrue(check_official_balance_equation(a, row, 'KR:011280'))
        self.assertEqual(row, original)
        self.assertEqual(a.errors, [])
        self.assertEqual(a.checks, {'official_financial_precision': 1, 'official_financial_arithmetic': 1})
        evidence = a.official_financial_precision_checks[0]
        self.assertEqual(evidence['status'], 'verified')
        self.assertEqual(evidence['published_amounts'], row['metrics'])
        self.assertEqual(evidence['reported_difference'], '-1000')
        self.assertEqual(evidence['difference_interval'], ['-2500', '500'])
        self.assertEqual(evidence['declared_decimals'], {'assets': '-3', 'liabilities': '-3', 'equity': '-3'})
        self.assertEqual(evidence['source_rcept_no'], '20260814003299')
        self.assertEqual(evidence['source_package_sha256'], row['account_validation']['balance_sheet']['source_precision']['source']['package_sha256'])

    def test_official_precision_claim_cannot_survive_a_changed_issuer_period_currency_or_amount(self):
        for field, value in (('symbol', '038110'), ('corp_code', '00139153'),
                             ('rcept_no', '20260814003298'), ('period_end', '2026-03-31'),
                             ('consolidation', 'OFS'), ('currency', 'USD'), ('assets', 698863344000)):
            row = self.source_precision_row()
            (row['metrics'] if field == 'assets' else row)[field] = value
            a = Audit()
            self.assertFalse(check_official_balance_equation(a, row, 'KR:011280'), field)
            self.assertEqual(a.errors[0]['issue'], 'official_balance_precision_evidence_invalid')
            self.assertEqual(a.official_financial_precision_checks[0]['status'], 'invalid')
            self.assertEqual(a.checks.get('official_financial_arithmetic', 0), 0)

    def test_official_precision_malformed_or_modified_proof_is_an_explicit_audit_failure(self):
        changes = (
            lambda v: v.pop('source_precision'),
            lambda v: v.update(source_precision=['invalid']),
            lambda v: v['source_precision'].update(source=['invalid']),
            lambda v: v['source_precision']['context']['period'].update(instant='2026-03-31'),
            lambda v: v['source_precision']['facts']['assets'].update(decimals='0'),
            lambda v: v.update(difference_interval=['-2501', '501']),
            lambda v: v.update(reported_values_unchanged=False),
        )
        for change in changes:
            row = self.source_precision_row()
            change(row['account_validation']['balance_sheet'])
            a = Audit()
            self.assertFalse(check_official_balance_equation(a, row, 'KR:011280'))
            self.assertEqual(a.errors[0]['group'], 'official_financial_precision')

    def test_official_balance_equation_has_no_percentage_tolerance_for_large_issuers(self):
        for difference, expected in ((0, True), (1, True), (-1, True), (2, False), (5000, False)):
            row = {'metrics': {'assets': 10**18 + difference, 'liabilities': 6 * 10**17, 'equity': 4 * 10**17}}
            a = Audit()
            self.assertEqual(check_official_balance_equation(a, row), expected, difference)
            self.assertEqual(a.official_financial_precision_checks, [])
            if not expected:
                self.assertEqual(a.errors[0]['absolute_tolerance'], '1')
                self.assertEqual(a.errors[0]['relative_tolerance'], 0)
        row = self.source_precision_row()
        del row['account_validation']
        self.assertFalse(check_official_balance_equation(Audit(), row, 'KR:011280'))

    def test_quarantined_balance_values_stay_null_without_a_precision_exception(self):
        row = {'metrics': dict.fromkeys(('assets', 'liabilities', 'equity')),
               'account_validation': {'balance_sheet': {'status': 'withheld_source_mismatch'}}}
        original = copy.deepcopy(row)
        a = Audit()
        self.assertIsNone(check_official_balance_equation(a, row, 'KR:038110'))
        self.assertEqual(row, original)
        self.assertEqual(a.errors, [])
        self.assertEqual(a.checks, {})
        self.assertEqual(a.official_financial_precision_checks, [])

    def annual_revenue_row(self):
        evidence = revenue_comparison(symbol='TEST', source_name='Yahoo Finance',
                    source_url='https://finance.yahoo.com/quote/TEST/financials/', provider_symbol='TEST',
                    currency='USD', account='TotalRevenue',
                    current={'value': 115060000.0, 'period': '2025-12-31', 'account': 'TotalRevenue'},
                    prior={'value': 100000000.0, 'period': '2024-12-31', 'account': 'TotalRevenue'},
                    metadata={'provider_symbol': 'TEST', 'financial_currency': 'USD',
                              'frequency': 'yearly', 'quote_type': 'EQUITY'},
                    observed_at='2026-11-06T08:00:00Z')
        return {'symbol': 'TEST', 'history': {'revenue': 115060000.0,
                'filing_period': '2025-12-31', 'currency': 'USD', **evidence}}

    def test_revenue_display_binds_to_same_saved_annual_source_values(self):
        a = Audit()
        check_revenue_source_evidence(a, self.annual_revenue_row(), NOW)
        self.assertEqual(a.errors, [])
        self.assertEqual(a.revenue_evidence_checks[0]['status'], 'verified')

    def test_revenue_evidence_cannot_validate_other_display_period_currency_or_amount(self):
        for field, value in (('currency', 'KRW'), ('filing_period', '2026-12-31'),
                             ('revenue', 115060001.0), ('revenue_previous', 100000001.0),
                             ('revenue_growth', 15.07), ('revenue_previous_period', '2023-12-31'),
                             ('revenue_growth_decimal_places', 8)):
            row = self.annual_revenue_row()
            row['history'][field] = value
            a = Audit()
            check_revenue_source_evidence(a, row, NOW)
            self.assertTrue(a.errors, field)

    def test_revenue_valid_label_does_not_replace_missing_published_inputs(self):
        for field in ('revenue_previous', 'revenue', 'revenue_growth', 'currency', 'filing_period'):
            row = self.annual_revenue_row()
            del row['history'][field]
            a = Audit()
            check_revenue_source_evidence(a, row, NOW)
            self.assertTrue(a.errors, field)

    def test_modified_or_future_revenue_source_evidence_fails(self):
        row = self.annual_revenue_row()
        row['history']['revenue_growth_evidence']['source_rows']['prior']['value'] += 1
        a = Audit()
        check_revenue_source_evidence(a, row, NOW)
        self.assertTrue(a.errors)
        row = self.annual_revenue_row()
        row['history']['revenue_growth_evidence']['source']['observed_at'] = '2026-11-06T10:00:00Z'
        a = Audit()
        check_revenue_source_evidence(a, row, NOW)
        self.assertTrue(a.errors)

    def test_actual_knx_ratio_is_inside_the_documented_round8_price_intervals(self):
        close, support, resistance = 59.47000122, 59.45000076, 82.86000061
        interval = reward_risk_interval(close, support, resistance)
        self.assertAlmostEqual(float(interval['lower']), 1169.47248639657, places=8)
        self.assertAlmostEqual(float(interval['upper']), 1169.47365684272, places=8)
        a = Audit()
        self.assertTrue(check_reward_risk(a, 1169.47320237, close, support, resistance, 'KNX'))
        self.assertEqual(a.errors, [])
        self.assertEqual(a.quantization_checks[0]['source_decimal_places'], 8)

    def test_incorrect_ratio_is_not_rescued_by_a_small_denominator_or_display_rounding(self):
        for value in (1169.47, 1169.4737, 1200, '1169.47320237'):
            a = Audit()
            self.assertFalse(check_reward_risk(a, value, 59.47000122, 59.45000076, 82.86000061, 'KNX'))
            self.assertTrue(a.errors)
        a = Audit()
        self.assertTrue(check_reward_risk(a, 2.0, 100.0, 90.0, 120.0, 'CONTROL'))
        self.assertFalse(check_reward_risk(Audit(), 2.0001, 100.0, 90.0, 120.0, 'CONTROL'))

    def test_denominator_interval_touching_zero_requires_withholding_the_ratio(self):
        for close, support in ((1.0, 1.0), (1.00000001, 1.0)):
            interval = reward_risk_interval(close, support, 2.0)
            self.assertEqual(interval['reason'], 'reward_risk_denominator_interval_crosses_zero')
            a = Audit()
            self.assertFalse(check_reward_risk(a, 1e8, close, support, 2.0))
            self.assertEqual(a.errors[0]['required_action'], 'withhold_unverifiable_ratio')
            a = Audit()
            self.assertTrue(check_reward_risk(a, None, close, support, 2.0))
            self.assertEqual(a.errors, [])
            self.assertEqual(a.warnings[0]['issue'], 'reward_risk_denominator_interval_crosses_zero')

    def daily(self, proof, bars=None):
        audit = Audit()
        result = check_daily_change(audit, proof, identity='TEST', market='US', provider='TEST',
                 currency='USD', session='2026-11-05', close=110.0, now=NOW, bars=bars)
        return result, audit.errors

    def test_verified_requires_explicit_finite_numeric_fields(self):
        self.assertEqual(self.daily(PROOF), (True, []))
        for field in ('close', 'previous_close', 'change_1d_pct'):
            for value in (None, True, '110', float('nan')):
                proof = {**PROOF, field: value}
                result, errors = self.daily(proof)
                self.assertFalse(result, (field, value))
                self.assertTrue(any(x['issue'] == 'verified_daily_change_missing_numeric_evidence' for x in errors))
        proof = {**PROOF, 'current_close': 110.0}
        del proof['close']
        self.assertFalse(self.daily(proof)[0])

    def test_zero_negative_and_inconsistent_daily_prices_are_rejected(self):
        for changes in ({'previous_close': 0}, {'close': -110}, {'close': 111},
                        {'change_1d_pct': 20}, {'previous_session': '2026-11-03'}, {'currency': 'CNY'}):
            self.assertFalse(self.daily({**PROOF, **changes})[0], changes)

    def test_chart_proof_must_match_both_original_bars(self):
        bars = [{'date': '2026-11-04', 'close': 100.0}, {'date': '2026-11-05', 'close': 110.0}]
        self.assertEqual(self.daily(PROOF, bars), (True, []))
        bars[0]['close'] = 105.0
        result, errors = self.daily(PROOF, bars)
        self.assertFalse(result)
        self.assertTrue(any(x['issue'] == 'daily_change_disagrees_with_chart_bar' for x in errors))
        self.assertFalse(self.daily(PROOF, bars[1:])[0])

    def test_complete_manifest_still_counts_skipped_processing(self):
        records = [{'status': 'research_prediction', 'collection_status': 'cache_current'},
                   {'status': 'no_call', 'collection_status': 'source_error'},
                   {'status': 'no_call', 'collection_status': 'deadline_skipped'},
                   {'status': 'no_call', 'collection_status': 'circuit_skipped'}]
        self.assertEqual(forecast_counts(records), {'total': 4, 'prediction': 1, 'no_call': 3,
                         'attempted': 2, 'failed': 1, 'not_attempted': 2})

    def test_empty_or_partial_chart_map_cannot_claim_complete_coverage(self):
        companies = [{'symbol': 'TEST'}, {'symbol': '005930'}]
        full = {key: {} for key in ('TEST', '005930', '^KS11', '^KQ11', '^GSPC', '^IXIC')}
        self.assertEqual(missing_chart_identities(companies, full), [])
        del full['TEST']
        self.assertEqual(missing_chart_identities(companies, full), ['TEST'])
        self.assertEqual(len(missing_chart_identities(companies, {})), 6)

    def test_world_fresh_wrapper_does_not_refresh_an_old_market_session(self):
        row = {'id': 'kospi', 'status': 'current', 'session': '2026-11-05', 'comparison_verified': True,
               'source': {'timezone': 'Asia/Seoul'}, 'received_at': '2026-11-06T08:59:00Z',
               'observed_at': '2026-11-05T06:30:00Z'}
        with patch('scripts.build_stock_world_flow.session_clock', return_value={'expected_session': '2026-11-06'}):
            self.assertEqual(world_current_counts({'indicators': [row]}, NOW), {'stale_or_unverified': 1})
            row['session'] = '2026-11-06'
            self.assertEqual(world_current_counts({'indicators': [row]}, NOW), {'current': 1})

    def test_treasury_actual_early_date_is_allowed_without_inventing_time(self):
        row = {'id': 'us10y', 'status': 'current', 'session': '2026-11-06', 'comparison_verified': True,
               'source': {'timezone': 'America/New_York'}, 'received_at': '2026-11-06T08:59:00Z', 'observed_at': None}
        with patch('scripts.build_stock_world_flow.session_clock', return_value={'expected_session': '2026-11-05'}):
            self.assertEqual(world_current_counts({'indicators': [row]}, NOW), {'current': 1})

    def test_korean_index_and_original_observation_clocks_are_checked(self):
        us = {'headline': {'score': 19.8}, 'source_timestamp': '2026-11-06T01:00:00Z'}
        kr = {'date': '2026-11-05', 'kospi': {'index': 31.7}, 'kosdaq': {'index': 12.5}}
        audit = Audit(); check_sentiment_observations(audit, us, kr, NOW, '2026-11-06')
        self.assertEqual(audit.errors, [])  # Historical values retain their source date.
        us['source_timestamp'] = '2026-11-06T09:01:00Z'
        kr['date'] = '2026-11-07'; kr['kospi']['index'] = 101
        audit = Audit(); check_sentiment_observations(audit, us, kr, NOW, '2026-11-06')
        self.assertEqual(len(audit.errors), 3)
        kr['date'] = '2026-11-06'; kr['kospi']['index'] = 31.7
        audit = Audit(); check_sentiment_observations(audit, {**us, 'source_timestamp': '2026-11-06T01:00:00Z'}, kr, NOW, '2026-11-05')
        self.assertTrue(any(x['issue'] == 'sentiment_invalid_or_uncompleted_source_date' for x in audit.errors))


if __name__ == '__main__':
    unittest.main()
