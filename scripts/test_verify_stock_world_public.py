"""Release regressions: stale observations and unbound derived files must fail."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_stock_world_public as subject

NOW = datetime(2026, 11, 6, 11, tzinfo=timezone.utc)


def observations():
    raw = {'companies': [{'symbol': 'TEST', 'market': 'US', 'price_session': '2026-11-05', 'price': 100.0}]}
    series = {}
    for key, market, day in [('TEST', 'US', '2026-11-05'), ('^GSPC', 'US', '2026-11-05'),
                             ('^IXIC', 'US', '2026-11-05'), ('^KS11', 'KR', '2026-11-06'),
                             ('^KQ11', 'KR', '2026-11-06')]:
        series[key] = {'market': market, 'price_session': day, 'bars': [{'date': day, 'close': 100.0}]}
    world = {'indicators': [{'id': key, 'session': '2026-11-05', 'value': 100.0,
                            'status': 'current', 'comparison_verified': True,
                            'received_at': '2026-11-06T10:00:00Z', 'observed_at': None}
                           for key in subject.BY_ID]}
    return raw, {'series': series}, world


def bound_snapshot():
    expected = {name: json.dumps({'file': name}).encode() for name in subject.AUDITED_DATA}
    audit = {'status': 'passed_with_limitations', 'errors': [], 'checked_at': '2026-11-06T10:00:00Z',
             'source_sha256': {name: hashlib.sha256(body).hexdigest() for name, body in expected.items()}}
    expected['stock-display-number-audit.json'] = json.dumps(audit).encode()
    return expected


class PublicationEvidenceTests(unittest.TestCase):
    def test_all_twenty_three_audited_sources_are_bound(self):
        _, bindings = subject.validate_audit_bindings(bound_snapshot(), NOW)
        self.assertEqual(len(bindings), 23)
        self.assertIn('stock-recommendations.json', bindings)
        self.assertIn('stock-extended-direction-forecast.json', bindings)
        self.assertTrue(all(bindings.values()))

    def test_new_derived_data_cannot_reuse_a_previous_successful_audit(self):
        for name in ('stock-entry-plan.json', 'stock-reading-depth.json', 'stock-recommendations.json',
                     'stock-extended-direction-forecast.json', 'stock-universe-catalog.json'):
            expected = bound_snapshot()
            expected[name] = b'{"changed":true}'
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'latest_source_rebuild'):
                subject.validate_audit_bindings(expected, NOW)

    def test_removing_audit_binding_does_not_reduce_release_scope(self):
        expected = bound_snapshot()
        audit = json.loads(expected['stock-display-number-audit.json'])
        del audit['source_sha256']['stock-reading-depth.json']
        expected['stock-display-number-audit.json'] = json.dumps(audit).encode()
        with self.assertRaisesRegex(ValueError, 'source_set_incomplete'):
            subject.validate_audit_bindings(expected, NOW)

    def test_future_or_failed_audit_does_not_pass(self):
        for change in ({'checked_at': '2026-11-06T12:00:00Z'}, {'errors': [{'issue': 'wrong_value'}]}, {'errors': None}):
            expected = bound_snapshot()
            audit = json.loads(expected['stock-display-number-audit.json'])
            audit.update(change)
            expected['stock-display-number-audit.json'] = json.dumps(audit).encode()
            with self.subTest(change=change), self.assertRaises(ValueError):
                subject.validate_audit_bindings(expected, NOW)

    @patch.object(subject, 'session_clock', return_value={'expected_session': '2026-11-05'})
    def test_current_prices_do_not_require_financial_completion(self, _):
        raw, charts, world = observations()
        raw['companies'][0]['status'] = 'incomplete'
        raw['companies'][0]['financial_currency'] = 'CNY'
        _, quotes, chart_count, world_count = subject.require_current_observations(raw, charts, world, NOW)
        self.assertEqual((quotes, chart_count, world_count), (1, 5, 14))

    @patch.object(subject, 'session_clock', return_value={'expected_session': '2026-11-05'})
    def test_one_stale_quote_blocks_success_instead_of_only_reporting_a_count(self, _):
        raw, charts, world = observations()
        raw['companies'][0]['price_session'] = '2026-11-04'
        with self.assertRaisesRegex(ValueError, 'quotes_not_all_current:0/1'):
            subject.require_current_observations(raw, charts, world, NOW)

    @patch.object(subject, 'session_clock', return_value={'expected_session': '2026-11-05'})
    def test_invalid_and_missing_prices_block_release(self, _):
        for price in (None, True, 0, -1, float('nan'), float('inf')):
            raw, charts, world = observations()
            raw['companies'][0]['price'] = price
            with self.subTest(price=price), self.assertRaisesRegex(ValueError, 'quotes_not_all_current'):
                subject.require_current_observations(raw, charts, world, NOW)

    @patch.object(subject, 'session_clock', return_value={'expected_session': '2026-11-05'})
    def test_missing_required_chart_or_false_endpoint_blocks_success(self, _):
        raw, charts, world = observations()
        del charts['series']['^GSPC']
        with self.assertRaisesRegex(ValueError, 'chart_identities_missing'):
            subject.require_current_observations(raw, charts, world, NOW)
        raw, charts, world = observations()
        charts['series']['TEST']['bars'][-1]['date'] = '2026-11-04'
        with self.assertRaisesRegex(ValueError, 'charts_not_all_current'):
            subject.require_current_observations(raw, charts, world, NOW)

    @patch.object(subject, 'session_clock', return_value={'expected_session': '2026-11-05'})
    def test_missing_market_and_session_are_not_equal_current_dates(self, _):
        raw, charts, world = observations()
        for key in ('market', 'price_session'):
            del raw['companies'][0][key]
        with self.assertRaisesRegex(ValueError, 'quotes_not_all_current'):
            subject.require_current_observations(raw, charts, world, NOW)
        raw, charts, world = observations()
        for key in ('market', 'price_session'):
            del charts['series']['TEST'][key]
        del charts['series']['TEST']['bars'][-1]['date']
        with self.assertRaisesRegex(ValueError, 'charts_not_all_current'):
            subject.require_current_observations(raw, charts, world, NOW)

    def test_source_movement_during_http_check_cannot_be_reported_as_latest(self):
        digest = hashlib.sha256(b'previous verified source').hexdigest()
        with patch.object(subject.subprocess, 'run'), \
                patch.object(subject.subprocess, 'check_output', return_value='new-main\n'), \
                patch.object(subject, 'revision_bytes', return_value=b'newer source'):
            with self.assertRaisesRegex(ValueError, 'main_snapshot_changed_during_public_verification'):
                subject.confirm_latest_snapshot({'stock-opportunity-data.json': digest})

    def test_unrelated_main_commit_does_not_invalidate_verified_radar_files(self):
        body = b'unchanged radar source'
        with patch.object(subject.subprocess, 'run'), \
                patch.object(subject.subprocess, 'check_output', return_value='unrelated-commit\n'), \
                patch.object(subject, 'revision_bytes', return_value=body):
            self.assertEqual(subject.confirm_latest_snapshot({'stock-opportunity-data.json': hashlib.sha256(body).hexdigest()}),
                             'unrelated-commit')

    @patch.object(subject, 'session_clock', return_value={'expected_session': '2026-11-05'})
    def test_world_current_flag_cannot_override_actual_verification_clock(self, _):
        for mutation in ({'session': '2026-11-04'}, {'received_at': '2026-11-06T12:00:00Z'},
                         {'observed_at': '2026-11-06T12:00:00Z'}, {'comparison_verified': False}):
            raw, charts, world = observations()
            world['indicators'][0].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'world_not_all_current:13/14'):
                subject.require_current_observations(raw, charts, world, NOW)

    @patch.object(subject, 'session_clock', return_value={'expected_session': '2026-11-05'})
    def test_partial_world_feed_never_reports_complete(self, _):
        raw, charts, world = observations()
        world['indicators'].pop()
        with self.assertRaisesRegex(ValueError, 'world_indicator_set_incomplete'):
            subject.require_current_observations(raw, charts, world, NOW)

    def test_failure_replaces_old_success_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'publication.json'
            path.write_text('{"status":"exact_public_world_and_number_update_verified"}')
            with patch.object(subject, 'verify', side_effect=ValueError('new_snapshot_unverified')), \
                    patch('sys.argv', ['verify', '--ui-commit', 'abc', '--output', str(path), '--attempts', '1']):
                with self.assertRaisesRegex(ValueError, 'new_snapshot_unverified'):
                    subject.main()
            result = json.loads(path.read_text())
            self.assertEqual(result['status'], 'verification_failed')
            self.assertEqual(result['error'], 'new_snapshot_unverified')


if __name__ == '__main__':
    unittest.main()
