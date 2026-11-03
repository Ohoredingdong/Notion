"""Fixed-clock prospective published-signal display selection, synthetic only.

No exchange histories, historical outcome labels, orders, or permission changes.
The test must fail until a distinct, read-only presentation selector exists.
"""
import copy
from datetime import datetime, timezone
import json
import unittest

from stock_forecast_presentation import prior_public_forecasts

AS_OF = "2026-11-02T22:30:31+00:00"
ISSUED = "2026-11-02T13:54:46+00:00"
START = "2026-11-03T00:00:00+00:00"
END = "2026-11-03T06:30:00+00:00"
VERIFIED = "2026-11-02T13:56:10+00:00"


def issued_record(symbol="^KS11", market="KR", ident="frozen-first",
                  start=START, end=END, issued=ISSUED):
    return {
        "id": ident, "symbol": symbol, "market": market, "mode": "daily",
        "status": "research_prediction", "direction": "up",
        "probabilities": {"down": 0.27, "flat": 0.31, "up": 0.42},
        "issued_at": issued, "received_at": "2026-11-02T13:54:29+00:00",
        "observed_until": "2026-11-02T06:30:00+00:00",
        "target": {"start": start, "end": end},
        "neutral_band_pct": 0.30,
        "recommendation": False, "strict_green_override": False,
    }


def public_proof(ids=("frozen-first",), when=VERIFIED, snapshot=None):
    return {
        "status": "public_verified", "verified_at": when,
        "snapshot_generated_at": snapshot or ISSUED,
        "prediction_ids": list(ids), "human_notification_received": False,
    }


class PriorPublicPresentationTests(unittest.TestCase):
    def setUp(self):
        self.ledger = [issued_record()]
        self.proofs = [public_proof()]
        self.current = [{"symbol": "^KS11", "market": "KR", "mode": "daily",
                         "status": "no_call", "probabilities": None,
                         "direction": None, "reason": "insufficient_session_time"}]

    def call(self, **kw):
        return prior_public_forecasts(kw.get("ledger", self.ledger),
                                      kw.get("proofs", self.proofs),
                                      kw.get("current", self.current),
                                      kw.get("now", AS_OF))

    def test_previous_frozen_still_pending_despite_newer_no_call(self):
        before = json.dumps([self.ledger, self.proofs, self.current], sort_keys=True)
        shown = self.call()
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0]["id"], "frozen-first")
        self.assertEqual(shown[0]["direction"], "up")
        self.assertEqual(shown[0]["probabilities"], self.ledger[0]["probabilities"])
        self.assertEqual(shown[0]["target"], self.ledger[0]["target"])
        self.assertEqual(shown[0]["display_origin"], "earlier_public_frozen_record")
        self.assertFalse(shown[0]["user_receipt_verified"])
        self.assertFalse(shown[0]["recommendation"])
        self.assertEqual(json.dumps([self.ledger,self.proofs,self.current],sort_keys=True),before)
        self.assertEqual(self.current[0]["status"], "no_call")

    def test_missing_or_post_start_proof_rejected(self):
        self.assertEqual(self.call(proofs=[]), [])
        self.assertEqual(self.call(proofs=[public_proof(when="2026-11-03T00:01:00+00:00")]), [])
        self.assertEqual(self.call(proofs=[public_proof(when=START)]), [])
        self.assertEqual(self.call(proofs=[public_proof(snapshot="2026-11-02T14:00:00+00:00",
                                                        when="2026-11-02T13:56:10+00:00")]), [])
        self.assertEqual(self.call(proofs=[public_proof(ids=["another-id"])]), [])

    def test_ended_or_invalid_timestamps_rejected(self):
        self.assertEqual(self.call(now="2026-11-03T06:31:00+00:00"), [])
        bad = issued_record()
        bad["received_at"] = "2026-11-02T14:20:00+00:00"
        self.assertEqual(self.call(ledger=[bad]), [])
        bad = issued_record()
        bad["target"] = {"start": START}
        self.assertEqual(self.call(ledger=[bad]), [])

    def test_duplicates_and_cross_market_kept_separate(self):
        duplicate = issued_record(ident="later-copy", issued="2026-11-02T13:55:40+00:00")
        original_public = public_proof(ids=("frozen-first","later-copy"),when="2026-11-02T13:57:00+00:00",
                                       snapshot="2026-11-02T13:56:00+00:00")
        other_market = issued_record(market="US", ident="other-market")
        matches = self.call(ledger=[duplicate, other_market, issued_record()],
                            proofs=[original_public,public_proof(ids=("other-market",))])
        self.assertEqual([x["id"] for x in matches], ["frozen-first", "other-market"])
        self.assertEqual({x["market"] for x in matches}, {"KR","US"})

    def test_unpublished_current_signal_not_a_previous_proof(self):
        self.assertEqual(self.call(current=[self.ledger[0]]), [])
        fake = copy.deepcopy(self.ledger[0])
        fake["direction"] = "down"
        fake["probabilities"] = {"down": 0.42, "flat": 0.31, "up": 0.27}
        self.assertEqual(self.call(ledger=[fake],proofs=[public_proof()])[0]["direction"], "down")


if __name__ == "__main__":
    unittest.main(verbosity=2)
