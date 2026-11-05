"""Synthetic-only verification-id conflict regression. No broker/exchange data or forecast edits."""
from copy import deepcopy
import unittest

from audit_stock_forecast_independent import audit, audit_digest, ts


class PublicVerificationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.r = {
            "id": "SYNTHETIC-public-identity", "symbol": "TEST", "market": "US",
            "mode": "intraday", "status": "research_prediction",
            "observed_until": "2026-10-29T13:30:00Z",
            "received_at": "2026-10-29T13:31:00Z",
            "issued_at": "2026-10-29T13:36:00Z",
            "target": {"start": "2026-10-29T14:00:00Z",
                       "end": "2026-10-29T14:30:00Z"},
            "probabilities": {"down": .2, "flat": .6, "up": .2},
            "direction": "flat", "neutral_band_pct": .3,
        }
        self.o = {
            "id": self.r["id"], "symbol": "TEST", "mode": "intraday",
            "status": "observed", "issued_at": self.r["issued_at"],
            "target": self.r["target"], "evaluated_at": "2026-10-29T14:40:00Z",
            "target_open": 100., "target_close": 99., "return_pct": -1.,
            "actual": "down", "predicted": "flat", "correct": False,
            "brier_loss": 1.04,
        }
        self.genuine = {
            "status": "public_verified",
            "snapshot_generated_at": "2026-10-29T14:05:00Z",
            "verified_at": "2026-10-29T14:06:00Z",
            "prediction_ids": [self.r["id"]],
            "human_notification_received": False,
        }
        # Publisher-style canonical identifier on the original synthetic proof.
        self.genuine["verification_id"] = audit_digest(self.genuine)
        self.forged = {
            **self.genuine,
            "snapshot_generated_at": "2026-10-29T13:36:30Z",
            "verified_at": "2026-10-29T13:37:00Z",
        }

    def result(self, deliveries):
        return audit([self.r], [self.o], deliveries, ts("2026-10-29T15:00:00Z"))

    def test_late_genuine_publication_is_not_timely(self):
        result = self.result([self.genuine])
        self.assertEqual(result["status"], "ledger_arithmetic_consistent")
        self.assertEqual(result["scored"], 0)

    def test_conflicting_same_verification_id_must_fail_closed(self):
        result = self.result([self.genuine, self.forged])
        self.assertEqual(result["status"], "integrity_errors")
        self.assertTrue(any(x["error"] == "conflicting_public_verification_id"
                            for x in result["errors"]))

    def test_reverse_order_of_conflicting_id_also_fails_closed(self):
        result = self.result([self.forged, self.genuine])
        self.assertEqual(result["status"], "integrity_errors")
        self.assertTrue(any(x["error"] == "conflicting_public_verification_id"
                            for x in result["errors"]))

    def test_identical_record_replay_does_not_invent_a_conflict(self):
        result = self.result([self.genuine, deepcopy(self.genuine)])
        self.assertEqual(result["status"], "ledger_arithmetic_consistent")
        self.assertEqual(result["scored"], 0)


    def test_repeated_only_public_proof_cannot_masquerade_as_new_forecast(self):
        # Fixed synthetic chronology; target begins at 14:00Z.
        first = {
            **self.genuine,
            "snapshot_generated_at": "2026-10-29T13:36:30Z",
            "verified_at": "2026-10-29T13:37:00Z",
        }
        first["verification_id"] = audit_digest(
            {k: v for k, v in first.items() if k != "verification_id"})
        repeated = {
            **first,
            "snapshot_generated_at": "2026-10-29T13:49:00Z",
            "verified_at": "2026-10-29T13:50:00Z",
        }
        repeated["verification_id"] = audit_digest(
            {k: v for k, v in repeated.items() if k != "verification_id"})
        report = self.result([first, repeated])
        self.assertEqual(report["status"], "ledger_arithmetic_consistent")
        self.assertEqual(report["scored"], 1)
        self.assertEqual(
            report["freshness_evidence"]["last_public_verified_at"],
            "2026-10-29T13:50:00+00:00")
        self.assertEqual(
            report["freshness_evidence"]["last_first_issued_timely_public_verified_at"],
            "2026-10-29T13:37:00+00:00")
        self.assertAlmostEqual(
            report["freshness_evidence"]["first_issued_timely_public_age_minutes"],
            83.0)

    def test_first_public_proof_after_start_is_not_new_actionable_public(self):
        # Existing genuine proof is at 14:06Z, after target start 14:00Z.
        report = self.result([self.genuine])
        self.assertEqual(report["status"], "ledger_arithmetic_consistent")
        self.assertEqual(report["scored"], 0)
        self.assertEqual(
            report["freshness_evidence"]["last_public_verified_at"],
            "2026-10-29T14:06:00+00:00")
        self.assertIsNone(
            report["freshness_evidence"]["last_first_issued_timely_public_verified_at"])
        self.assertIsNone(
            report["freshness_evidence"]["first_issued_timely_public_age_minutes"])


if __name__ == "__main__":
    unittest.main()
