import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_real_estate_pulse as collector
import run_real_estate_pulse_update as runner
import requests

class RefreshTests(unittest.TestCase):
    def test_disconnect_retried(self):
        response = Mock()
        with patch.object(collector.requests, 'request', side_effect=[requests.ConnectionError('disconnect'), response]) as call, patch.object(collector.time, 'sleep'):
            self.assertIs(collector.get('https://www.reb.or.kr/test'), response)
            self.assertEqual(call.call_count, 2)

    def test_exhaustion_bounded_and_identifies_source(self):
        with patch.object(collector.requests, 'request', side_effect=requests.Timeout('timeout')) as call, patch.object(collector.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'reb.or.kr/test.*3 attempt'):
                collector.get('https://www.reb.or.kr/test')
            self.assertEqual(call.call_count, 3)

    def test_forbidden_not_retried(self):
        response = Mock(status_code=403)
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        with patch.object(collector.requests, 'request', return_value=response) as call:
            with self.assertRaises(RuntimeError): collector.get('https://www.reb.or.kr/test')
            self.assertEqual(call.call_count, 1)

    def test_official_homepage_fallback(self):
        html = '<a data-id="123">주간 아파트 가격동향 (20261109 기준)</a>'
        with patch.object(collector, 'get', side_effect=[RuntimeError('disconnect'), Mock(text=html)]):
            stamp, url = collector.latest_release()
            self.assertEqual(stamp, '20261109')
            self.assertTrue(url.startswith('https://www.reb.or.kr/'))

    def test_failure_preserves_last_good_bytes(self):
        original = (Path(__file__).resolve().parents[1] / 'real-estate-pulse-data.json').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output, health = Path(directory)/'data.json', Path(directory)/'health.json'
            output.write_bytes(original)
            with patch.object(runner, 'OUT', output), patch.object(runner, 'HEALTH', health), patch.object(runner.updater, 'collect', side_effect=RuntimeError('unavailable')):
                self.assertFalse(runner.refresh())
            self.assertEqual(output.read_bytes(), original)
            self.assertNotEqual(json.loads(health.read_text())['status'], 'ok')

    def test_invalid_data_preserved(self):
        original = (Path(__file__).resolve().parents[1] / 'real-estate-pulse-data.json').read_bytes()
        invalid = json.loads(original); invalid['regions'][0]['sale'] = None
        with tempfile.TemporaryDirectory() as directory:
            output, health = Path(directory)/'data.json', Path(directory)/'health.json'
            output.write_bytes(original)
            with patch.object(runner, 'OUT', output), patch.object(runner, 'HEALTH', health), patch.object(runner.updater, 'collect', return_value=invalid):
                self.assertFalse(runner.refresh())
            self.assertEqual(output.read_bytes(), original)

if __name__ == '__main__': unittest.main()
