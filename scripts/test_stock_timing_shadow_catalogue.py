"""Synthetic-only boundary tests: pre-registered direction-specialist catalogue.

Never read actual future prices, trade, rewrite forecasts, or select models.
"""
import unittest
from audit_stock_forecast_independent import validate


def frozen_record(candidates=None):
    row = {
        'id': 'synthetic-catalogue-fixture',
        'symbol': 'TEST', 'market': 'US', 'mode': 'intraday',
        'status': 'research_prediction',
        'observed_until': '2026-10-29T13:30:00Z',
        'received_at': '2026-10-29T13:31:00Z',
        'issued_at': '2026-10-29T13:36:00Z',
        'target': {'start': '2026-10-29T14:00:00Z',
                   'end': '2026-10-29T14:30:00Z'},
        'probabilities': {'down': .2, 'flat': .6, 'up': .2},
        'direction': 'flat', 'neutral_band_pct': .3,
    }
    if candidates is not None:
        row['directional_specialists'] = {
            'version': 'direction-specialists-1.0',
            'status': 'shadow_only',
            'candidates': candidates,
        }
    return row


def candidate():
    return {
        'probabilities': {'down': .5, 'flat': .2, 'up': .3},
        'direction': 'down',
    }


class ReviewedShadowCatalogueTests(unittest.TestCase):
    def test_legacy_without_shadow_candidates_is_unchanged(self):
        validate(frozen_record())

    def test_reviewed_movement_then_direction_is_valid(self):
        validate(frozen_record({'movement_then_direction': candidate()}))

    def test_reviewed_balanced_candidates_remain_valid(self):
        validate(frozen_record({'balanced_linear': candidate(),
                                'balanced_nonlinear': candidate()}))

    def test_unreviewed_cybernetically_named_candidate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unreviewed_shadow_candidate'):
            validate(frozen_record({'oracle_future_peek': candidate()}))

    def test_unreviewed_candidate_hidden_beside_valid_one_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unreviewed_shadow_candidate'):
            validate(frozen_record({'movement_then_direction': candidate(),
                                    'oracle_future_peek': candidate()}))


if __name__ == '__main__':
    unittest.main()
