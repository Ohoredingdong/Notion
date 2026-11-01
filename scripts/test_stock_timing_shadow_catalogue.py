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


def with_uncertainty_signal(record, *, uncertain, selection=True):
    """Synthetic applied forecast metadata, never a production recommendation."""
    row = dict(record)
    if selection:
        row['directional_selection'] = {
            'version': 'direction-specialists-1.0',
            'active': 'incumbent',
            'orders_enabled': False,
            'strict_green_override': False,
        }
    row['directional_signal'] = {
        'uncertain': uncertain,
        'uncertainty_is_not_flat': True,
        'all_original_predictions_still_scored': True,
        'thresholds_are_policy_not_success_probabilities': True,
    }
    return row


class FrozenUncertaintyMetadataTests(unittest.TestCase):
    def test_correct_low_confidence_flag_remains_valid(self):
        record = frozen_record()
        record['probabilities'] = {'down': .42, 'flat': .34, 'up': .24}
        record['direction'] = 'down'
        validate(with_uncertainty_signal(record, uncertain=True))

    def test_false_certain_flag_is_rejected(self):
        record = frozen_record()
        record['probabilities'] = {'down': .42, 'flat': .34, 'up': .24}
        record['direction'] = 'down'
        with self.assertRaisesRegex(ValueError, 'directional_uncertainty_mismatch'):
            validate(with_uncertainty_signal(record, uncertain=False))

    def test_false_uncertain_flag_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'directional_uncertainty_mismatch'):
            validate(with_uncertainty_signal(frozen_record(), uncertain=True))

    def test_nonboolean_uncertainty_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid_directional_signal'):
            validate(with_uncertainty_signal(frozen_record(), uncertain='no'))

    def test_selected_direction_without_signal_is_rejected(self):
        record = with_uncertainty_signal(frozen_record(), uncertain=False)
        del record['directional_signal']
        with self.assertRaisesRegex(ValueError, 'directional_signal_missing'):
            validate(record)

    def test_safety_flags_cannot_be_dropped(self):
        record = with_uncertainty_signal(frozen_record(), uncertain=False)
        record['directional_signal']['all_original_predictions_still_scored'] = False
        with self.assertRaisesRegex(ValueError, 'invalid_directional_signal'):
            validate(record)


if __name__ == '__main__':
    unittest.main()
