"""Frozen model-vintage chronology guard: synthetic input only, no prices/orders."""
import unittest
from audit_stock_forecast_independent import validate

class FrozenModelAsOfTests(unittest.TestCase):
    def record(self):
        return {
            "id":"SYNTHETIC-model-asof-only", "symbol":"TEST", "market":"US",
            "mode":"intraday", "status":"research_prediction", "version":"legacy",
            "observed_until":"2026-10-29T13:35:00Z",
            "received_at":"2026-10-29T13:35:40Z",
            "issued_at":"2026-10-29T13:36:00Z",
            "target":{"start":"2026-10-29T14:00:00Z","end":"2026-10-29T14:30:00Z"},
            "probabilities":{"down":0.2,"flat":0.6,"up":0.2},
            "direction":"flat", "neutral_band_pct":0.3,
            "trained_through":"2026-10-29T12:00:00Z",
            "calibrated_through":"2026-10-29T13:00:00Z",
            "validation":{"test_end":"2026-10-29T13:35:00Z"}
        }
    def test_valid_model_vintage_before_snapshot_passes(self):
        validate(self.record())
    def test_legacy_without_model_dates_not_backfilled(self):
        r=self.record()
        for field in ("trained_through","calibrated_through","validation"):
            r.pop(field)
        validate(r)
    def test_training_after_observation_but_before_issuance_is_rejected(self):
        r=self.record(); r["trained_through"]="2026-10-29T13:35:20Z"
        with self.assertRaisesRegex(ValueError,"model_training_after_observed_input"):
            validate(r)
    def test_calibration_after_observation_but_before_issuance_is_rejected(self):
        r=self.record(); r["calibrated_through"]="2026-10-29T13:35:20Z"
        with self.assertRaisesRegex(ValueError,"model_calibration_after_observed_input"):
            validate(r)
    def test_holdout_end_after_observation_but_before_issuance_is_rejected(self):
        r=self.record(); r["validation"]["test_end"]="2026-10-29T13:35:20Z"
        with self.assertRaisesRegex(ValueError,"model_validation_after_observed_input"):
            validate(r)
    def test_training_after_calibration_is_rejected(self):
        r=self.record(); r["trained_through"]="2026-10-29T13:10:00Z"
        with self.assertRaisesRegex(ValueError,"model_training_after_calibration"):
            validate(r)

if __name__=="__main__":
    unittest.main()
