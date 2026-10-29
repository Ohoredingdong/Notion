"""Synthetic red/green for source availability timestamps. No market or broker data."""
import unittest
from audit_stock_forecast_independent import audit, ts


class OutcomeSourceTimeTests(unittest.TestCase):
    def fixture(self):
        prediction = {
            'id': 'synthetic-source-asof', 'symbol': 'TEST', 'market': 'US',
            'mode': 'intraday', 'status': 'research_prediction',
            'observed_until': '2026-10-29T13:35:00Z',
            'received_at': '2026-10-29T13:35:10Z',
            'issued_at': '2026-10-29T13:36:00Z',
            'target': {'start': '2026-10-29T14:00:00Z',
                       'end': '2026-10-29T14:30:00Z'},
            'probabilities': {'down': .2, 'flat': .6, 'up': .2},
            'direction': 'flat', 'neutral_band_pct': .3}
        publication = {
            'status': 'public_verified',
            'snapshot_generated_at': '2026-10-29T13:36:30Z',
            'verified_at': '2026-10-29T13:37:00Z',
            'prediction_ids': [prediction['id']]}
        outcome = {
            'id': prediction['id'], 'symbol': 'TEST', 'mode': 'intraday',
            'status': 'observed', 'target': prediction['target'],
            'evaluated_at': '2026-10-29T14:31:00Z',
            'target_open': 100., 'target_close': 99.,
            'return_pct': -1., 'actual': 'down', 'predicted': 'flat',
            'correct': False, 'brier_loss': 1.04,
            'source_checked_at': '2026-10-29T14:30:30Z',
            'delivery_verified_at': '2026-10-29T13:37:00Z'}
        return prediction, publication, outcome

    def evaluated(self, **changes):
        p, d, o = self.fixture()
        return audit([p], [{**o, **changes}], [d], ts('2026-10-29T15:00:00Z'))

    def test_valid_source_checked_between_target_end_and_outcome_evaluation(self):
        result = self.evaluated()
        self.assertEqual(result['status'], 'ledger_arithmetic_consistent')
        self.assertEqual(result['scored'], 1)

    def test_source_checked_later_than_claimed_evaluation_is_rejected(self):
        result = self.evaluated(source_checked_at='2026-10-29T14:40:00Z')
        self.assertEqual(result['status'], 'integrity_errors')
        self.assertTrue(any(e.get('error') == 'outcome_source_time_inconsistent'
                            for e in result['errors']))

    def test_source_checked_before_target_end_is_rejected(self):
        result = self.evaluated(source_checked_at='2026-10-29T14:29:59Z')
        self.assertEqual(result['status'], 'integrity_errors')
        self.assertTrue(any(e.get('error') == 'outcome_source_time_inconsistent'
                            for e in result['errors']))

    def test_absent_legacy_source_checked_time_not_backfilled(self):
        _, _, o = self.fixture()
        o.pop('source_checked_at')
        result = self.evaluated(**o)
        self.assertEqual(result['status'], 'ledger_arithmetic_consistent')
        self.assertEqual(result['scored'], 1)


if __name__ == '__main__':
    unittest.main()
