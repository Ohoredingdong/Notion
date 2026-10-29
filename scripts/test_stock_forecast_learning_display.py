"""Do not relabel incumbent holdout scores as learned-model performance."""
import unittest
from copy import deepcopy
from run_stock_forecasts import label_validation
class DisplayTests(unittest.TestCase):
    def test_incumbent_keeps_actual_history(self):
        r={'validation':{'accuracy':.5},'online_learning':{'active_variant':'incumbent'}}
        self.assertIs(label_validation(r),r)
    def test_adaptive_does_not_inherit_holdout_claim(self):
        r={'validation':{'accuracy':.9,'above_baseline_in_this_holdout':True},'online_learning':{'active_variant':'adaptive'}}
        old=deepcopy(r);s=label_validation(r)
        self.assertEqual(r,old);self.assertIsNone(s['validation']['accuracy'])
        self.assertFalse(s['validation']['above_baseline_in_this_holdout'])
        self.assertEqual(s['incumbent_historical_validation']['accuracy'],.9)
    def test_repeated_display_preserves_original_incumbent_record(self):
        r={'validation':{'accuracy':.4},'online_learning':{'active_variant':'adaptive'}}
        a=label_validation(r);b=label_validation(a)
        self.assertEqual(a,b)
