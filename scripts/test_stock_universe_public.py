"""Synthetic publication fixtures; no market data or network requests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import publish_stock_universe_forecasts as publisher
import verify_stock_universe_public as public


class PublicVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = {'items': [{'country': 'US', 'symbol': 'TEST', 'name': 'Synthetic test only', 'exchange': 'NASDAQ'}]}
        self.record = {'market': 'US', 'catalog_symbol': 'TEST', 'catalog_name': 'Synthetic test only',
                       'catalog_exchange': 'NASDAQ', 'identity_verified': True,
                       'status': 'research_prediction', 'probabilities': {'up': .4, 'flat': .35, 'down': .25},
                       'observed_until': '2026-11-05T21:00:00Z', 'received_at': '2026-11-06T07:00:00Z',
                       'issued_at': '2026-11-06T07:01:00Z',
                       'target': {'start': '2026-11-06T14:30:00Z', 'end': '2026-11-06T21:00:00Z'}}
        self.document = {'generation_mode': 'full_universe', 'automatic_orders': False,
                         'generated_at': '2026-11-06T07:02:00Z',
                         'coverage': {'total': 1, 'prediction': 1}, 'records': [self.record],
                         'run': {'id': 'synthetic-only', 'catalog_sha256': hashlib.sha256(json.dumps(self.catalog).encode()).hexdigest()}}
        for name in public.FILES:
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic UI fixture')
        (self.root/public.FILES[1]).write_text(json.dumps(self.catalog))
        (self.root/'stock-value-radar.html').write_text(' '.join(public.FILES[3:]))
        self.save()

    def save(self):
        (self.root/public.FILES[0]).write_text(json.dumps(self.document))

    def check(self, at='2026-11-06T08:00:00+00:00', get=None):
        return public.verify(self.root, get or (lambda n: (self.root/n).read_bytes()),
                             clock=lambda: datetime.fromisoformat(at))

    def test_exact_public_bytes_and_clock_count_a_prospective_check(self):
        report = self.check()
        self.assertEqual(report['public_before_target_verified'], 1)
        self.assertFalse(report['human_notification_received'])

    def test_late_observation_stays_late(self):
        report = self.check('2026-11-06T15:00:00+00:00')
        self.assertEqual(report['public_before_target_verified'], 0)
        self.assertEqual(report['late_publication_observed'], 1)

    def test_stale_public_response_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'public_bytes_mismatch'):
            self.check(get=lambda n: b'older snapshot')

    def test_wrong_company_with_equal_count_is_rejected(self):
        self.record['catalog_symbol'] = 'OTHER'; self.save()
        with self.assertRaisesRegex(ValueError, 'identity_set_mismatch'):
            self.check()

    def test_invalid_probability_and_future_issue_are_rejected(self):
        self.record['probabilities']['up'] = True; self.save()
        with self.assertRaisesRegex(ValueError, 'probabilities_invalid'):
            self.check()
        self.record['probabilities']['up'] = .4
        self.record['issued_at'] = '2026-11-06T16:00:00Z'; self.save()
        with self.assertRaisesRegex(ValueError, 'not_prospective'):
            self.check()

    def test_catalogue_bytes_bind_the_result(self):
        self.document['run']['catalog_sha256'] = '0'*64; self.save()
        with self.assertRaisesRegex(ValueError, 'catalogue_provenance_mismatch'):
            self.check()


class PublicationLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'work'; self.root.mkdir()
        publisher.git('init', '-q', '-b', 'main', cwd=self.root)
        publisher.git('config', 'user.name', 'Synthetic Test', cwd=self.root)
        publisher.git('config', 'user.email', 'test@invalid.local', cwd=self.root)
        for name in publisher.DEPENDENCIES:
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('baseline')
        (self.root/publisher.OUTPUT).write_text(json.dumps({'generated_at': '2026-11-05T00:00:00Z'}))
        self.commit('baseline')
        self.source = publisher.git('rev-parse', 'HEAD', cwd=self.root).stdout.strip()
        self.remote = Path(self.temp.name)/'remote.git'
        publisher.git('clone', '--bare', str(self.root), str(self.remote))
        publisher.git('remote', 'add', 'origin', str(self.remote), cwd=self.root)
        self.payload = {'version': 'stock-extended-direction-v1', 'generation_mode': 'full_universe',
                        'automatic_orders': False, 'generated_at': '2026-11-06T07:00:00Z',
                        'run': {'source_commit': self.source}, 'records': [{'fixture': 'synthetic only'}],
                        'coverage': {'total': 1, 'prediction': 1, 'failed': 0, 'not_attempted': 0}}

    def commit(self, message):
        publisher.git('add', '.', cwd=self.root)
        publisher.git('commit', '-qm', message, cwd=self.root)

    def save(self):
        (self.root/publisher.OUTPUT).write_text(json.dumps(self.payload))

    def test_unrelated_concurrent_updates_survive_publication(self):
        (self.root/'unrelated.txt').write_text('keep concurrent work')
        self.commit('unrelated update'); publisher.git('push', '-q', 'origin', 'main', cwd=self.root)
        self.save()
        result = publisher.publish(self.root, self.source, 'main')
        self.assertTrue(result['published'])
        publisher.git('fetch', '-q', 'origin', 'main', cwd=self.root)
        self.assertEqual(publisher.git('show', 'origin/main:unrelated.txt', cwd=self.root).stdout, 'keep concurrent work')

    def test_changed_model_input_blocks_publication(self):
        (self.root/'scripts/stock_forecast_model.py').write_text('changed model')
        self.commit('changed input'); publisher.git('push', '-q', 'origin', 'main', cwd=self.root)
        self.save()
        with self.assertRaisesRegex(ValueError, 'inputs_changed'):
            publisher.publish(self.root, self.source, 'main')

    def test_wrong_source_commit_blocks_publication(self):
        self.payload['run']['source_commit'] = '0'*40; self.save()
        with self.assertRaisesRegex(ValueError, 'incomplete_full_universe_snapshot'):
            publisher.publish(self.root, self.source, 'main')


if __name__ == '__main__':
    unittest.main()
