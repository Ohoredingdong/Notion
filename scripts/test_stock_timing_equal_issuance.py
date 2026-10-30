"""Synthetic negative controls: same-instant first-issuance conflicts must fail closed.

No real predictions/outcomes are constructed or modified by these tests.
"""
import unittest
from audit_stock_forecast_independent import audit, ts


class EqualFirstIssuanceTests(unittest.TestCase):
    def setUp(self):
        self.first = {
            "id": "synthetic-first-flat", "symbol": "TEST", "market": "US", "mode": "intraday",
            "status": "research_prediction",
            "observed_until": "2026-10-29T13:30:00Z",
            "received_at": "2026-10-29T13:35:00Z",
            "issued_at": "2026-10-29T13:36:00Z",
            "target": {"start": "2026-10-29T14:00:00Z", "end": "2026-10-29T14:30:00Z"},
            "probabilities": {"down": .2, "flat": .6, "up": .2}, "direction": "flat",
            "neutral_band_pct": .3,
        }
        self.alternate = {
            **self.first, "id": "synthetic-second-down",
            "probabilities": {"down": .6, "flat": .2, "up": .2},
            "direction": "down",
        }
        common = {
            "symbol": "TEST", "mode": "intraday", "status": "observed",
            "target": self.first["target"], "evaluated_at": "2026-10-29T14:31:00Z",
            "target_open": 100.0, "target_close": 99.0,
            "return_pct": -1.0, "actual": "down",
        }
        self.outcomes = [
            {**common, "id": self.first["id"], "predicted": "flat", "correct": False,
             "brier_loss": 1.04},
            {**common, "id": self.alternate["id"], "predicted": "down", "correct": True,
             "brier_loss": .24},
        ]
        self.publication = {
            "status": "public_verified",
            "snapshot_generated_at": "2026-10-29T13:37:00Z",
            "verified_at": "2026-10-29T13:38:00Z",
            "prediction_ids": [self.first["id"], self.alternate["id"]],
        }
        self.cutoff = ts("2026-10-29T15:00:00Z")

    def evaluate(self, rows, delivery=None):
        return audit(rows, self.outcomes,
                     [self.publication if delivery is None else delivery],
                     self.cutoff)

    def test_distinct_ids_same_instant_fail_closed_in_original_order(self):
        result = self.evaluate([self.first, self.alternate])
        self.assertEqual(result["status"], "integrity_errors")
        self.assertIn("ambiguous_first_issuance_tie",
                      [e["error"] for e in result["errors"]])

    def test_distinct_ids_same_instant_fail_closed_when_reversed(self):
        result = self.evaluate([self.alternate, self.first])
        self.assertEqual(result["status"], "integrity_errors")
        self.assertIn("ambiguous_first_issuance_tie",
                      [e["error"] for e in result["errors"]])

    def test_equal_instant_with_timezone_offset_is_still_ambiguous(self):
        alternate = {**self.alternate, "issued_at": "2026-10-29T09:36:00-04:00"}
        result = self.evaluate([alternate, self.first])
        self.assertEqual(result["status"], "integrity_errors")
        self.assertIn("ambiguous_first_issuance_tie",
                      [e["error"] for e in result["errors"]])

    def test_later_distinct_issuance_keeps_proven_first(self):
        later = {**self.alternate, "issued_at": "2026-10-29T13:39:00Z"}
        publication = {**self.publication, "snapshot_generated_at": "2026-10-29T13:40:00Z",
                       "verified_at": "2026-10-29T13:41:00Z"}
        for rows in ([self.first, later], [later, self.first]):
            result = self.evaluate(rows, publication)
            self.assertEqual(result["status"], "ledger_arithmetic_consistent")
            self.assertEqual(result["scored"], 1)
            self.assertEqual(result["correct"], 0)
            self.assertEqual(result["rows"][0]["id"], self.first["id"])

    def test_exact_same_idempotent_record_remains_valid(self):
        publication = {**self.publication, "prediction_ids": [self.first["id"]]}
        result = audit([self.first, self.first], self.outcomes[:1],
                       [publication], self.cutoff)
        self.assertEqual(result["status"], "ledger_arithmetic_consistent")
        self.assertEqual(result["scored"], 1)


if __name__ == "__main__":
    unittest.main()
