"""Synthetic only: verify public-proof ID agrees with its frozen payload.

A canonical SHA256 match does not independently prove public availability,
human notification receipt, exchange prices, or executable trading timing.
"""
from copy import deepcopy
import unittest
from audit_stock_forecast_independent import audit, audit_digest, ts


class PublicProofPayloadFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.forecast = {
            "id": "SYNTHETIC-public-fingerprint", "symbol": "TEST", "market": "US",
            "mode": "intraday", "status": "research_prediction",
            "observed_until": "2026-10-29T13:30:00Z",
            "received_at": "2026-10-29T13:31:00Z",
            "issued_at": "2026-10-29T13:36:00Z",
            "target": {"start": "2026-10-29T14:00:00Z", "end": "2026-10-29T14:30:00Z"},
            "probabilities": {"down": .2, "flat": .6, "up": .2},
            "direction": "flat", "neutral_band_pct": .3,
        }
        self.outcome = {
            "id": self.forecast["id"], "symbol": "TEST", "mode": "intraday",
            "status": "observed", "target": self.forecast["target"],
            "evaluated_at": "2026-10-29T14:40:00Z", "target_open": 100.,
            "target_close": 99., "return_pct": -1., "actual": "down",
            "predicted": "flat", "correct": False, "brier_loss": 1.04,
        }

    def proof(self, *, late=False):
        d = {
            "status": "public_verified",
            "snapshot_generated_at": "2026-10-29T14:05:00Z" if late else "2026-10-29T13:36:30Z",
            "verified_at": "2026-10-29T14:06:00Z" if late else "2026-10-29T13:37:00Z",
            "prediction_ids": [self.forecast["id"]],
            "human_notification_received": False,
        }
        return {**d, "verification_id": audit_digest(d)}

    def check(self, docs):
        return audit([self.forecast], [self.outcome], docs, ts("2026-10-29T15:00:00Z"))

    def test_valid_canonical_proof_is_eligible(self):
        r = self.check([self.proof()])
        self.assertEqual(r["status"], "ledger_arithmetic_consistent")
        self.assertEqual(r["scored"], 1)

    def test_late_proof_remains_unscored(self):
        r = self.check([self.proof(late=True)])
        self.assertEqual(r["status"], "ledger_arithmetic_consistent")
        self.assertEqual(r["scored"], 0)

    def test_unique_wrong_id_cannot_forge_earlier_publication(self):
        late = self.proof(late=True)
        fake = {**self.proof(), "verification_id": "f" * 64}
        r = self.check([late, fake])
        self.assertEqual(r["status"], "integrity_errors")
        self.assertTrue(any(e["error"] == "public_verification_fingerprint_mismatch" for e in r["errors"]))
        self.assertEqual(r["scored"], 0, "A wrongly fingerprinted earlier proof cannot establish pre-target publication")

    def test_payload_mutation_without_id_update_is_rejected(self):
        d = self.proof()
        changed = deepcopy(d)
        changed["verified_at"] = "2026-10-29T13:38:00Z"
        r = self.check([changed])
        self.assertEqual(r["status"], "integrity_errors")
        self.assertTrue(any(e["error"] == "public_verification_fingerprint_mismatch" for e in r["errors"]))
        self.assertEqual(r["scored"], 0)

    def test_legacy_synthetic_without_fingerprint_retains_old_scoring_path(self):
        d = self.proof()
        d.pop("verification_id")
        r = self.check([d])
        self.assertEqual(r["status"], "ledger_arithmetic_consistent")
        self.assertEqual(r["scored"], 1)
        self.assertFalse(r["human_push_delivery_verified"])


if __name__ == "__main__":
    unittest.main()
