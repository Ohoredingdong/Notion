"""Preregistered synthetic-only frozen ledger/outcome row-status integrity tests.
No exchange prices, model experiments, or production evidence mutations.
"""
import unittest
from audit_stock_forecast_independent import audit, ts


class FrozenEvidenceRowStatusTests(unittest.TestCase):
    def setUp(self):
        self.r = {
            "id": "SYNTHETIC-row-status", "symbol": "TEST", "market": "US",
            "mode": "intraday", "status": "research_prediction",
            "observed_until": "2026-10-29T13:30:00Z",
            "received_at": "2026-10-29T13:31:00Z",
            "issued_at": "2026-10-29T13:36:00Z",
            "target": {"start": "2026-10-29T14:00:00Z", "end": "2026-10-29T14:30:00Z"},
            "probabilities": {"down": .2, "flat": .6, "up": .2},
            "direction": "flat", "neutral_band_pct": .3,
        }
        self.o = {
            "id": self.r["id"], "symbol": "TEST", "mode": "intraday",
            "status": "observed", "issued_at": self.r["issued_at"],
            "target": self.r["target"], "evaluated_at": "2026-10-29T14:40:00Z",
            "target_open": 100.0, "target_close": 99.0,
            "return_pct": -1.0, "actual": "down",
            "predicted": "flat", "correct": False, "brier_loss": 1.04,
        }
        self.d = {
            "status": "public_verified",
            "snapshot_generated_at": "2026-10-29T13:36:30Z",
            "verified_at": "2026-10-29T13:37:00Z",
            "prediction_ids": [self.r["id"]],
        }

    def test_controls_remain_consistent(self):
        observed = audit([self.r], [self.o], [self.d], ts("2026-10-29T15:00:00Z"))
        self.assertEqual(observed["status"], "ledger_arithmetic_consistent")
        self.assertEqual((observed["scored"], observed["correct"]), (1, 0))
        pending = audit([self.r], [], [], ts("2026-10-29T13:50:00Z"))
        self.assertEqual(pending["status"], "ledger_arithmetic_consistent")
        self.assertEqual(pending["counts"]["pending_targets"], 1)

    def test_frozen_prediction_must_not_be_silently_relabelled_as_no_call(self):
        forged = {**self.r, "status": "no_call"}
        result = audit([forged], [], [], ts("2026-10-29T13:50:00Z"))
        self.assertEqual(result["status"], "integrity_errors")
        self.assertTrue(any(e["error"] == "unexpected_forecast_ledger_status"
                            for e in result["errors"]))

    def test_missing_frozen_prediction_status_is_not_silent(self):
        forged = {k: v for k, v in self.r.items() if k != "status"}
        result = audit([forged], [], [], ts("2026-10-29T13:50:00Z"))
        self.assertEqual(result["status"], "integrity_errors")
        self.assertTrue(any(e["error"] == "unexpected_forecast_ledger_status"
                            for e in result["errors"]))

    def test_observed_result_must_not_be_silently_suppressed(self):
        forged = {**self.o, "status": "suppressed"}
        result = audit([self.r], [forged], [self.d], ts("2026-10-29T15:00:00Z"))
        self.assertEqual(result["status"], "integrity_errors")
        self.assertTrue(any(e["error"] == "unexpected_observed_outcome_status"
                            for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
