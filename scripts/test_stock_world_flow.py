"""Offline semantic regressions for sourced global-market observations."""
from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

try:
    from scripts import build_stock_world_flow as flow
except ImportError:
    import build_stock_world_flow as flow

UTC = timezone.utc
NOW = datetime(2026, 11, 6, 9, tzinfo=UTC)


def metadata(spec):
    return {'symbol': spec.symbol, 'instrumentType': spec.instrument,
            'exchangeName': spec.exchanges[0] if spec.exchanges else None,
            'exchangeTimezoneName': spec.zones[0], 'currency': spec.quote_currency}


def identity(spec):
    if spec.id == 'us10y':
        return {'identity_verified': True, 'provider_symbol': 'BC_10YEAR',
                'response_symbol': 'BC_10YEAR', 'timezone': 'America/New_York'}
    return flow.verify_metadata(spec, metadata(spec))


def frame(spec, days=('2026-11-04', '2026-11-05'), values=(100, 101)):
    return pd.DataFrame({'Close': list(values)},
                        index=pd.to_datetime(list(days)).tz_localize(spec.zones[0]))


def treasury_xml(rows):
    entries = ''.join('<entry><content><m:properties>'
                      f'<d:NEW_DATE>{day}T00:00:00</d:NEW_DATE><d:BC_10YEAR>{value}</d:BC_10YEAR>'
                      '</m:properties></content></entry>' for day, value in rows)
    return ('<feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" '
            'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices">' + entries + '</feed>').encode()


def record(identifier, points, now=NOW):
    spec = flow.BY_ID[identifier]
    return flow.make_record(spec, points, now, identity(spec), {'fixture': 'synthetic_only'})


class Sessions(unittest.TestCase):
    def test_six_regions_have_distinct_last_completed_dates_and_real_closes(self):
        # At 09 UTC Friday Asia has closed, Europe and US have not.
        for identifier, expected, close in (
            ('kospi', '2026-11-06', '2026-11-06T06:30:00Z'),
            ('sp500', '2026-11-05', '2026-11-05T21:00:00Z'),
            ('dax', '2026-11-05', '2026-11-05T16:30:00Z'),
            ('shanghai', '2026-11-06', '2026-11-06T07:00:00Z'),
            ('nikkei225', '2026-11-06', '2026-11-06T06:30:00Z'),
            ('hang_seng', '2026-11-06', '2026-11-06T08:00:00Z'),
        ):
            with self.subTest(identifier=identifier):
                clock = flow.session_clock(flow.BY_ID[identifier], NOW)
                self.assertEqual(clock['expected_session'], expected)
                self.assertEqual(clock['closed_at'], close)
                self.assertGreater(flow.stamp(clock['next_check_after']), NOW)

    def test_korea_close_delay_does_not_accept_unfinished_bar(self):
        before = datetime(2026, 11, 6, 6, 45, tzinfo=UTC)
        row = record('kospi', [('2026-11-04', 100), ('2026-11-05', 101), ('2026-11-06', 999)], before)
        self.assertEqual(row['session'], '2026-11-05')
        self.assertEqual(row['value'], 101)
        self.assertEqual(row['freshness']['next_check_after'], '2026-11-06T07:00:00Z')

    def test_actual_holidays_china_japan_korea_hong_kong_and_germany(self):
        cases = [('shanghai', '2026-10-05'), ('nikkei225', '2026-11-03'),
                 ('kospi', '2026-10-09'), ('hang_seng', '2026-10-19'), ('dax', '2026-12-25')]
        for identifier, day in cases:
            with self.subTest(identifier=identifier):
                cal = flow.calendar(flow.BY_ID[identifier].calendar, 2026)
                self.assertFalse(cal.is_session(day))

    def test_us_dst_and_short_day_follow_calendar(self):
        summer = flow.session_clock(flow.BY_ID['sp500'], datetime(2026, 10, 30, 21, tzinfo=UTC))
        self.assertEqual(summer['closed_at'], '2026-10-30T20:00:00Z')
        winter = flow.session_clock(flow.BY_ID['sp500'], datetime(2026, 11, 6, 22, tzinfo=UTC))
        self.assertEqual(winter['closed_at'], '2026-11-06T21:00:00Z')
        short = flow.session_clock(flow.BY_ID['sp500'], datetime(2026, 11, 27, 19, tzinfo=UTC))
        self.assertEqual(short['closed_at'], '2026-11-27T18:00:00Z')

    def test_vix_close_is_1615_not_equity_1600(self):
        clock = flow.session_clock(flow.BY_ID['vix'], datetime(2026, 11, 6, 21, 40, tzinfo=UTC))
        self.assertEqual(clock['expected_session'], '2026-11-05')
        self.assertEqual(clock['next_close'], '2026-11-06T21:15:00Z')
        self.assertEqual(clock['next_check_after'], '2026-11-06T21:45:00Z')

    def test_provider_local_date_not_elapsed_utc_date(self):
        # At 00:15 UTC, the New York Nov5 daily value may still be forming.
        clock = flow.session_clock(flow.BY_ID['dxy'], datetime(2026, 11, 6, 0, 15, tzinfo=UTC))
        self.assertEqual(clock['expected_session'], '2026-11-04')
        self.assertEqual(clock['next_check_after'], '2026-11-06T05:30:00Z')
        self.assertIsNone(clock['closed_at'])

    def test_future_china_holiday_coverage_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'calendar_coverage_expired'):
            flow.session_clock(flow.BY_ID['shanghai'], datetime(2027, 1, 6, 9, tzinfo=UTC))


class ValuesAndIdentity(unittest.TestCase):
    def test_percent_sign_and_previous_value_exact_arithmetic(self):
        for current, direction in ((103, 'up'), (97, 'down'), (100, 'flat')):
            row = record('kospi', [('2026-11-05', 100), ('2026-11-06', current)])
            self.assertEqual(row['change_pct'], current - 100)
            self.assertEqual(row['direction'], direction)
            self.assertEqual(row['unit'], 'index_points')
            self.assertIsNone(row['currency'])
            self.assertIsNone(row['change_bp'])

    def test_missing_previous_session_does_not_become_multi_day_one_day_return(self):
        row = record('kospi', [('2026-11-04', 100), ('2026-11-06', 105)])
        self.assertEqual(row['value'], 105)
        self.assertIsNone(row['previous_value'])
        self.assertIsNone(row['change_pct'])
        self.assertFalse(row['comparison_verified'])
        self.assertEqual(row['direction'], 'unknown')
        self.assertEqual(row['reason'], 'previous_session_missing')

    def test_old_real_value_is_stale_not_retimestamped_current(self):
        row = record('kospi', [('2026-11-04', 100), ('2026-11-05', 101)])
        self.assertEqual(row['status'], 'stale')
        self.assertEqual(row['observed_at'], '2026-11-05T06:30:00Z')
        self.assertEqual(row['received_at'], '2026-11-06T09:00:00Z')
        self.assertEqual(row['expected_session'], '2026-11-06')

    def test_provider_date_values_have_no_invented_observed_timestamp(self):
        for identifier, unit in (('usdkrw', 'KRW_per_USD'), ('wti', 'USD_per_barrel'), ('gold', 'USD_per_troy_ounce')):
            row = record(identifier, [('2026-11-04', 100), ('2026-11-05', 101)])
            self.assertEqual(row['unit'], unit)
            self.assertIsNone(row['observed_at'])
            self.assertEqual(row['observed_at_precision'], 'source_date')
            self.assertEqual(row['quote_basis'], 'provider_daily_close')

    def test_symbol_type_exchange_timezone_currency_mismatch_rejected(self):
        spec = flow.BY_ID['wti']
        for key, value in (('symbol', 'BZ=F'), ('instrumentType', 'EQUITY'),
                           ('exchangeName', 'CMX'), ('exchangeTimezoneName', 'Asia/Tokyo'), ('currency', 'CNY')):
            with self.subTest(key=key):
                data = metadata(spec)
                data[key] = value
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    flow.verify_metadata(spec, data)

    def test_actual_vix_cxi_metadata_is_specific_to_vix_and_keeps_other_checks(self):
        # Actions 42192615887 returned this exact quote identity on 2026-11-06.
        actual = {'symbol': '^VIX', 'instrumentType': 'INDEX', 'exchangeName': 'CXI',
                  'exchangeTimezoneName': 'America/Chicago', 'currency': 'USD'}
        self.assertTrue(flow.verify_metadata(flow.BY_ID['vix'], actual)['identity_verified'])
        for key, value in (('symbol', '^VXO'), ('instrumentType', 'FUTURE'),
                           ('exchangeTimezoneName', 'Asia/Seoul'), ('currency', 'KRW')):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'mismatch'):
                flow.verify_metadata(flow.BY_ID['vix'], {**actual, key: value})
        sp500 = metadata(flow.BY_ID['sp500'])
        with self.assertRaisesRegex(ValueError, 'exchange_mismatch'):
            flow.verify_metadata(flow.BY_ID['sp500'], {**sp500, 'exchangeName': 'CXI'})

    def test_source_date_duplicates_and_naive_time_rejected(self):
        spec = flow.BY_ID['kospi']
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            flow.frame_points(frame(spec, ('2026-11-05', '2026-11-05')), spec.zones[0])
        with self.assertRaisesRegex(ValueError, 'timezone'):
            flow.frame_points(pd.DataFrame({'Close': [1]}, index=pd.to_datetime(['2026-11-05'])), spec.zones[0])

    def test_nonfinite_and_nonpositive_source_closes_not_replaced(self):
        spec = flow.BY_ID['kospi']
        points, provenance = flow.frame_points(frame(spec, ('2026-11-03', '2026-11-04', '2026-11-05'), (100, float('nan'), 0)), spec.zones[0])
        self.assertEqual(points, [('2026-11-03', 100.0)])
        self.assertEqual(provenance['invalid_close_rows'], 2)
        self.assertEqual(provenance['source_rows'], 3)


class Treasury(unittest.TestCase):
    def test_percent_is_not_tnx_tenths_and_delta_is_basis_points(self):
        xml = treasury_xml([('2026-11-04', '4.81'), ('2026-11-05', '4.84')])
        points = flow.parse_treasury(xml)
        row = record('us10y', points)
        self.assertEqual(row['value'], 4.84)
        self.assertAlmostEqual(row['change_value'], .03)
        self.assertAlmostEqual(row['change_bp'], 3)
        self.assertIsNone(row['change_pct'])
        self.assertEqual(row['unit'], 'percent')
        self.assertIsNone(row['observed_at'])
        self.assertEqual(row['source']['response_symbol'], 'BC_10YEAR')

    def test_treasury_zero_yield_is_valid_and_nan_is_not_zero(self):
        points = flow.parse_treasury(treasury_xml([('2026-11-04', '0'), ('2026-11-05', '0.01'), ('2026-11-06', 'NaN')]))
        row = record('us10y', points)
        self.assertEqual(row['previous_value'], 0)
        self.assertEqual(row['change_bp'], 1)
        self.assertIsNone(row['change_pct'])

    def test_treasury_veterans_day_holiday_not_stock_calendar(self):
        clock = flow.treasury_clock(datetime(2026, 11, 12, 10, tzinfo=UTC))
        self.assertEqual(clock['expected_session'], '2026-11-10')
        self.assertEqual(clock['next_expected_session'], '2026-11-12')
        self.assertTrue(flow.calendar('XNYS', 2026).is_session('2026-11-11'))
        row = record('us10y', [('2026-11-09', 4.8), ('2026-11-10', 4.81)], datetime(2026, 11, 12, 10, tzinfo=UTC))
        self.assertEqual(row['status'], 'current')

    def test_treasury_good_friday_2026_is_early_close_not_full_holiday(self):
        self.assertTrue(flow.valid_treasury_day(datetime(2026, 4, 3).date()))
        self.assertFalse(flow.calendar('XNYS', 2026).is_session('2026-04-03'))

    def test_new_official_publication_before_policy_deadline_advances_next_check(self):
        row = record('us10y', [('2026-11-05', 4.8), ('2026-11-06', 4.81)], datetime(2026, 11, 6, 22, tzinfo=UTC))
        self.assertEqual(row['session'], '2026-11-06')
        self.assertEqual(row['freshness']['next_check_after'], '2026-11-09T23:00:00Z')

    def test_duplicate_xml_and_missing_field_fail_instead_of_zero_change(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            flow.parse_treasury(treasury_xml([('2026-11-05', 4.8), ('2026-11-05', 4.9)]))
        with self.assertRaisesRegex(ValueError, 'field_missing'):
            flow.parse_treasury(treasury_xml([]))


class SummaryAndCollection(unittest.TestCase):
    @staticmethod
    def complete_document():
        def fetch(spec, timeout):
            clock = flow.session_clock(spec, NOW)
            current = clock['expected_session']
            prior = str(flow.calendar(spec.calendar, 2026).previous_session(current))[:10]
            return frame(spec, (prior, current), (100, 101)), metadata(spec)
        collector = flow.Collector(now_fn=lambda: NOW, sleep_fn=lambda _: None, yahoo_fn=fetch,
                                   xml_fn=lambda url, timeout: treasury_xml([('2026-11-04', 4.81), ('2026-11-05', 4.84)]))
        with patch('builtins.print'):
            return collector.run()

    def test_complete_document_contract_and_exact_six_region_count(self):
        doc = self.complete_document()
        self.assertEqual(flow.validate_document(doc)['current'], 14)
        self.assertEqual(doc['run']['total'], 14)
        self.assertEqual(doc['summary']['regions_available'], 6)
        self.assertEqual(doc['summary']['regions_up'], 6)
        self.assertEqual(doc['status'], 'complete')

    def test_validator_rejects_tampered_unit_percent_bp_summary_and_receipt(self):
        original = self.complete_document()
        mutations = (
            lambda doc: doc['indicators'][0].update(unit='percent'),
            lambda doc: doc['indicators'][0].update(change_pct=10),
            lambda doc: doc['indicators'][10].update(change_bp=30),
            lambda doc: doc['summary'].update(regions_up=7),
            lambda doc: doc['indicators'][0].update(received_at='2026-11-06T09:10:00Z'),
            lambda doc: doc['indicators'][0]['source'].update(response_symbol='^KQ11'),
            lambda doc: doc['indicators'][0]['freshness'].update(next_check_after='2026-11-20T07:00:00Z'),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                doc = copy.deepcopy(original)
                mutate(doc)
                with self.assertRaises(ValueError):
                    flow.validate_document(doc)

    def test_validator_rejects_retimestamped_old_data_as_current(self):
        doc = self.complete_document()
        later = '2026-11-09T09:00:00Z'
        doc['generated_at'] = later
        doc['run']['completed_at'] = later
        with self.assertRaisesRegex(ValueError, 'semantic_mismatch|freshness_mismatch'):
            flow.validate_document(doc)

    def test_crossed_collection_deadline_rechecks_status_preserving_receipt(self):
        clock = [datetime(2026, 11, 6, 6, 59, tzinfo=UTC)]
        def fetch(spec, timeout):
            session_clock = flow.session_clock(spec, clock[0])
            current = session_clock['expected_session']
            prior = str(flow.calendar(spec.calendar, 2026).previous_session(current))[:10]
            if spec.id == 'gold':
                clock[0] = datetime(2026, 11, 6, 7, 1, tzinfo=UTC)
            return frame(spec, (prior, current)), metadata(spec)
        collector = flow.Collector(now_fn=lambda: clock[0], sleep_fn=lambda _: None, yahoo_fn=fetch,
                                   xml_fn=lambda url, timeout: treasury_xml([('2026-11-04', 4.81), ('2026-11-05', 4.84)]))
        with patch('builtins.print'):
            doc = collector.run()
        korea = doc['indicators'][0]
        self.assertEqual(korea['status'], 'stale')
        self.assertEqual(korea['session'], '2026-11-05')
        self.assertEqual(korea['received_at'], '2026-11-06T06:59:00Z')
        self.assertEqual(korea['expected_session'], '2026-11-06')

    def test_summary_counts_current_regions_without_weights_or_causal_claims(self):
        rows = [record('kospi', [('2026-11-05', 100), ('2026-11-06', 101)]),
                record('kosdaq', [('2026-11-05', 100), ('2026-11-06', 99)]),
                record('sp500', [('2026-11-04', 100), ('2026-11-05', 101)]),
                record('nasdaq', [('2026-11-04', 100), ('2026-11-05', 102)]),
                record('dax', [('2026-11-03', 100), ('2026-11-04', 99)])]
        regions, summary = flow.summarise(rows)
        self.assertEqual(regions[0]['direction'], 'mixed')
        self.assertEqual(regions[1]['direction'], 'up')
        self.assertEqual(summary['regions_available'], 2)
        self.assertEqual(summary['regions_mixed'], 1)
        self.assertEqual(summary['regions_up'], 1)
        self.assertNotIn('dax', summary['basis_ids'])
        self.assertNotIn('score', summary)

    def test_related_news_preserves_date_link_and_context_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'news.json'
            path.write_text(json.dumps({'generated_at': flow.iso(NOW), 'items': [
                {'title': '원문 기사 제목', 'source': '출처', 'source_tier': 'A', 'url': 'https://example.org/a', 'published_at': flow.iso(NOW - timedelta(hours=1))},
                {'title': '오래된 기사', 'source': '출처', 'source_tier': 'A', 'url': 'https://example.org/b', 'published_at': flow.iso(NOW - timedelta(days=8))},
                {'title': '미래 기사', 'source': '출처', 'source_tier': 'A', 'url': 'https://example.org/c', 'published_at': flow.iso(NOW + timedelta(days=1))}]}))
            items, context = flow.read_news(path, NOW)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]['context_only'])
        self.assertEqual(items[0]['url'], 'https://example.org/a')
        self.assertIn('원인으로 검증한 것이 아닙니다', context['note'])

    def test_rate_limit_circuit_is_bounded_and_treasury_remains_available(self):
        calls = []
        def unavailable(spec, timeout):
            calls.append(spec.id)
            raise RuntimeError('HTTP 429 Too Many Requests')
        collector = flow.Collector(now_fn=lambda: NOW, sleep_fn=lambda _: None,
                                   yahoo_fn=unavailable,
                                   xml_fn=lambda url, timeout: treasury_xml([('2026-11-04', 4.8), ('2026-11-05', 4.9)]))
        with patch('builtins.print'):
            doc = collector.run()
        self.assertEqual(len(calls), 2)
        self.assertEqual(doc['run']['attempted'], 2)  # one Yahoo indicator + Treasury
        rows = {r['id']: r for r in doc['indicators']}
        self.assertEqual(rows['us10y']['status'], 'current')
        self.assertEqual(rows['kospi']['reason'], 'yahoo_rate_limited')
        self.assertFalse(rows['kosdaq']['source_collection_attempted'])
        self.assertEqual(doc['run']['current'] + doc['run']['stale'] + doc['run']['unavailable'], 14)

    def test_receipt_time_is_after_network_completion(self):
        clock = [NOW]
        spec = flow.BY_ID['sp500']
        def fetch(item, timeout):
            clock[0] += timedelta(seconds=7)
            return frame(item), metadata(item)
        collector = flow.Collector(now_fn=lambda: clock[0], sleep_fn=lambda _: None, yahoo_fn=fetch)
        row = collector.collect_yahoo(spec)
        self.assertEqual(row['received_at'], flow.iso(NOW + timedelta(seconds=7)))
        self.assertTrue(row['source']['identity_verified'])

    def test_deadline_skips_network_and_does_not_report_attempt(self):
        elapsed = [0]
        calls = []
        collector = flow.Collector(max_seconds=5, monotonic_fn=lambda: elapsed[0],
                                   now_fn=lambda: NOW, yahoo_fn=lambda *args: calls.append(args))
        elapsed[0] = 6
        row = collector.collect_yahoo(flow.BY_ID['kospi'])
        self.assertEqual(row['reason'], 'collection_deadline_exhausted')
        self.assertFalse(row['source_collection_attempted'])
        self.assertFalse(calls)


if __name__ == '__main__':
    unittest.main()
