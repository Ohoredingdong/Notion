"""Synthetic fixtures test chronology only; never production performance evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import stock_forecast_model as base
import stock_forecast_recent_daily as recent
from test_stock_forecasts import fixture


class RecentDailyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bars = fixture(n=930)
        cls.data, cls.x, cls.band = base.samples(cls.bars, 'daily')
        cls.origin = cls.data.origin.iloc[-30]
        cls.model, cls.meta = recent.fit_asof(cls.data, cls.origin)

    def test_recipe_is_one_shadow_only(self):
        self.assertEqual(recent.RECIPE['name'], 'recent_daily_logistic_v1')
        self.assertTrue(recent.RECIPE['shadow_only'])
        self.assertFalse(recent.RECIPE['automatic_promotion'])
        self.assertFalse(recent.RECIPE['orders_enabled'])

    def test_same_original_features_and_C(self):
        self.assertEqual(recent.RECIPE['features'], base.FEATURES)
        self.assertEqual(recent.RECIPE['C'], base.POLICY['logistic_C'])

    def test_train_calibration_purge(self):
        train, cal = recent.split_asof(self.data, self.origin)
        self.assertLess(train.target_end.max(), cal.origin.min())
        self.assertLess(cal.target_end.max(), self.origin)
        self.assertFalse(set(train.session) & set(cal.session))
        self.assertLessEqual(train.session.nunique(), 756)
        self.assertLessEqual(cal.session.nunique(), 60)
        self.assertGreaterEqual(len(train), 500)
        self.assertGreaterEqual(len(cal), 40)

    def test_future_label_changes_leave_model_hash_identical(self):
        changed = self.data.copy(deep=True)
        future = changed.target_end >= self.origin
        changed.loc[future, 'y'] = (changed.loc[future, 'y']+1) % 3
        changed.loc[future, base.FEATURES] *= 2
        _, metadata = recent.fit_asof(changed, self.origin)
        self.assertEqual(self.meta['model_sha256'], metadata['model_sha256'])

    def test_label_ending_exactly_at_origin_excluded(self):
        origin = self.data.target_end.iloc[-30]
        train, cal = recent.split_asof(self.data, origin)
        self.assertTrue((train.target_end < origin).all())
        self.assertTrue((cal.target_end < origin).all())

    def test_probability_normalized(self):
        p = recent.predict(self.model, self.meta, self.x.iloc[[-1]])
        np.testing.assert_allclose(p.sum(axis=1), 1, rtol=0, atol=1e-12)
        self.assertTrue(np.isfinite(p).all())
        self.assertTrue((p >= 0).all() and (p <= 1).all())

    def test_inputs_not_mutated(self):
        before = self.data.copy(deep=True)
        recent.split_asof(self.data, self.origin)
        pd.testing.assert_frame_equal(before, self.data)

    def test_minimum_history_not_relaxed(self):
        with self.assertRaisesRegex(ValueError, 'history_short'):
            recent.fit_asof(self.data.iloc[:400], self.origin)

    def test_one_class_not_silently_trained(self):
        d = self.data.copy(); d['y'] = 1
        with self.assertRaisesRegex(ValueError, 'class_samples_short'):
            recent.fit_asof(d, self.origin)

    def test_duplicate_origin_rejected(self):
        d = pd.concat([self.data, self.data.iloc[[-1]]])
        with self.assertRaisesRegex(ValueError, 'origin_order'):
            recent.split_asof(d, self.origin)

    def test_unsorted_rows_rejected(self):
        with self.assertRaisesRegex(ValueError, 'origin_order'):
            recent.split_asof(self.data.iloc[::-1], self.origin)

    def test_future_feature_timestamps_rejected(self):
        d = self.data.copy(); d.loc[0, 'origin'] = d.loc[0, 'target_end']
        with self.assertRaises(ValueError):
            recent.split_asof(d, self.origin)

    def test_naive_timestamps_rejected(self):
        d = self.data.copy(); d['origin'] = d.origin.dt.tz_localize(None)
        with self.assertRaisesRegex(ValueError, 'timezone_required'):
            recent.split_asof(d, self.origin)

    def test_nan_features_rejected(self):
        d = self.data.copy(); d.loc[0, 'r1'] = np.nan
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            recent.split_asof(d, self.origin)

    def test_negative_band_rejected(self):
        d = self.data.copy(); d.loc[0, 'band'] = -.1
        with self.assertRaisesRegex(ValueError, 'band'):
            recent.split_asof(d, self.origin)

    def test_invalid_class_rejected(self):
        d = self.data.copy(); d.loc[0, 'y'] = 4
        with self.assertRaisesRegex(ValueError, 'class_invalid'):
            recent.split_asof(d, self.origin)

    def test_intraday_not_mixed_with_daily(self):
        bars = self.bars.copy(); bars.attrs['mode'] = 'intraday'
        with self.assertRaisesRegex(ValueError, 'daily_only'):
            recent.diagnose(bars)

    def test_fresh_refit_uses_more_recent_training_than_old(self):
        old = base.fit_model(self.bars, 'daily')
        _, meta = recent.fit_asof(self.data, self.bars.end.iloc[-1])
        self.assertGreater(base.stamp(meta['trained_through']), base.stamp(old['trained_through']))
        self.assertLess(base.stamp(meta['calibrated_through']), self.bars.end.iloc[-1])

    def test_replay_has_exactly_fixed_126_targets_and_six_folds(self):
        report, meta, choices, band = recent.diagnose(self.bars)
        self.assertEqual(len(report['diagnostic_rows']), 126)
        self.assertEqual(len(report['folds']), 6)
        for fold in report['folds']:
            self.assertLess(base.stamp(fold['calibrated_through']), base.stamp(fold['origin']))
        self.assertEqual(band, float(self.band.iloc[-1])*100)
        self.assertIn('movement_then_direction', report['diagnostic'])
        self.assertIn('frozen_training_frequency', report['diagnostic'])
        self.assertFalse(report['untouched_confirmation'])
        self.assertFalse(report['history_is_point_in_time_vintage'])
        self.assertTrue(all(r['diagnostic_only_not_issued_forecast'] for r in report['diagnostic_rows']))
        self.assertTrue(all('issued_at' not in r for r in report['diagnostic_rows']))
        self.assertEqual(set(choices), {'recent_daily_logistic_v1', 'incumbent', 'movement_then_direction'})

    def test_source_failure_is_reported_not_imputed(self):
        with patch('run_stock_forecasts.collect', side_effect=ValueError('missing')):
            with self.assertRaisesRegex(ValueError, 'missing'):
                recent.process(('TEST', 'Test', 'US'))

    def test_forward_after_target_start_is_no_call(self):
        dummy = ({}, deepcopy(self.meta), {recent.RECIPE['name']: np.array([.2,.3,.5]), 'incumbent': np.array([.3,.4,.3])}, .3)
        now = datetime.now(timezone.utc)
        with patch('run_stock_forecasts.collect', return_value=(self.bars, now)), patch.object(recent, 'diagnose', return_value=dummy), patch.object(base, 'future_target', return_value=(None, 'target_already_started_or_delivery_window_too_short')):
            result = recent.process(('TEST', 'Test', 'US'))['fresh_shadow']
        self.assertEqual(result['status'], 'no_call')
        self.assertIsNone(result['probabilities'])
        self.assertIsNone(result['target'])
        self.assertFalse(result['recommendation'])
        self.assertFalse(result['strict_green_override'])
        self.assertFalse(result['public_before_target_verified'])
        self.assertEqual(result['forward_scored'], 0)

    def test_failed_groups_remain_explicit(self):
        result = recent.aggregate([{'symbol': 'TEST', 'status': 'group_failed'}])
        self.assertEqual(result['targets'], 0)
        self.assertEqual(result['failed_groups'], ['TEST'])
        self.assertEqual(result['status'], 'no_real_comparison')


if __name__ == '__main__':
    unittest.main()
