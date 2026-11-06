"""Offline adversarial checks for actual display-audit acceptance boundaries."""
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from audit_stock_display_numbers import (Audit, check_daily_change, forecast_counts,
    missing_chart_identities, world_current_counts, check_sentiment_observations)

NOW = datetime(2026, 11, 6, 9, tzinfo=timezone.utc)
PROOF = {'version': 'completed-session-change-v1', 'status': 'verified', 'market': 'US',
         'provider_symbol': 'TEST', 'currency': 'USD', 'source_identity_verified': True,
         'price_session': '2026-11-05', 'close': 110.0, 'previous_session': '2026-11-04',
         'previous_close': 100.0, 'expected_previous_session': '2026-11-04',
         'consecutive_sessions': True, 'change_1d_pct': 10.0, 'basis': 'provider_close_auto_adjust_false'}


class DisplayAuditTests(unittest.TestCase):
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
