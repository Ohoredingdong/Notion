"""Regression checks for observed market-widget failures; no network required."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def module(filename):
    spec = importlib.util.spec_from_file_location(filename.replace('-', '_'), HERE / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


premium = module('update-bitcoin-korea-premium.py')
supply = module('update-supply-chain.py')
sentiment = module('update_fear_greed.py')


class MarketRepairTests(unittest.TestCase):
    def test_gscpi_uses_observation_month_and_one_vintage(self):
        data = 'Date,Sep-26,Oct-26\n31-Jul-2026,0.79,0.93\n31-Aug-2026,1.06,1.20\n30-Sep-2026,#N/A,1.28\n'
        parsed = supply.parse_gscpi(data)
        self.assertEqual(parsed['reference_month'], '2026-09')
        self.assertEqual(parsed['source_vintage'], '2026-10')
        self.assertEqual(parsed['previous'], 1.2)
        self.assertEqual([x['value'] for x in parsed['history']], [.93, 1.2, 1.28])

    def test_ism_parses_table_not_unrelated_prose_numbers(self):
        html = '<h1>September 2026 ISM® Manufacturing PMI® Report</h1><p>Suppliers in 18 industries.</p><table><tr><td>Supplier Deliveries</td><td>59.0</td><td>59.3</td><td>-0.3</td></tr><tr><td>Prices</td><td>77.9</td><td>71.1</td><td>+6.8</td></tr></table>'
        data = supply.parse_ism(html, 'https://example.test/report')
        self.assertEqual(data['supplier_deliveries']['change'], -.3)
        self.assertEqual(data['ism_prices']['value'], 77.9)
        self.assertEqual(data['ism_prices']['reference_month'], '2026-09')

    def test_wci_accepts_current_publisher_wording_and_full_month(self):
        data = supply.parse_wci('<p>15 October 2026: Drewry’s World Container Index (WCI) rose 3% to $4,485 per 40ft container.</p>')
        self.assertEqual((data['value'], data['change_pct'], data['reference_date']), (4485, 3, '2026-10-15'))

    def test_wci_stable_release_does_not_take_previous_article_date(self):
        data = supply.parse_wci('<p>16 Oct 2026: unrelated article.</p><p>10 Sep 2026: Drewry’s World Container Index (WCI) remained stable at $4,476 per 40ft container.</p>')
        self.assertEqual((data['value'], data['change_pct'], data['reference_date']), (4476, 0, '2026-09-10'))

    def test_failed_premium_fetch_keeps_values_and_observation_time(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'premium.json'
            original = {'updated_at': '2026-10-19T02:00:00+00:00', 'premium_pct': 1.2,
                        'rows': [{'symbol': 'BTC', 'local_krw': 1000, 'global_usd': 1}]}
            target.write_text(json.dumps(original))
            with patch.object(premium, 'OUT', target), patch.object(premium, 'collect', side_effect=RuntimeError('HTTP 429')):
                premium.main()
            saved = json.loads(target.read_text())
            self.assertEqual(saved['updated_at'], original['updated_at'])
            self.assertEqual(saved['rows'], original['rows'])
            self.assertEqual(saved['premium_pct'], 1.2)
            self.assertTrue(saved['stale'])

    def test_korea_aligns_different_trading_calendars_by_date(self):
        start = 1704067200000
        kospi = [(start + n * 86400000, 100 + n) for n in range(50)]
        kosdaq = [(time, 200 + index) for index, (time, _) in enumerate(kospi) if index != 30]
        fx = [(time, 1000 - index) for index, (time, _) in enumerate(kospi)]
        with patch.object(sentiment, 'chart', side_effect=[kospi, kosdaq, fx]):
            data = sentiment.korea()
        self.assertNotIn(start + 30 * 86400000, [row['timestamp'] for row in data['history']])
        self.assertIsNone(data['headline']['previous_1_year'])
        self.assertIsNone(data['one_year_average'])
        self.assertEqual(data['history'][-1]['value'], data['headline']['score'])

    def test_failed_sentiment_fetch_keeps_original_score(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'sentiment.json'
            old = {'updated_at': '2026-08-20T09:30:00+09:00', 'headline': {'score': 52}}
            target.write_text(json.dumps(old))
            with patch.object(sentiment, 'ROOT', Path(directory)):
                sentiment.safe_update(target.name, lambda: (_ for _ in ()).throw(RuntimeError('429')))
            saved = json.loads(target.read_text())
            self.assertEqual(saved['updated_at'], old['updated_at'])
            self.assertEqual(saved['headline'], old['headline'])
            self.assertEqual(saved['status'], 'stale')


if __name__ == '__main__':
    unittest.main()
