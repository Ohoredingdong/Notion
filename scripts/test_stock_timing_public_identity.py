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


class PublicNoCallProducerProofTests(unittest.TestCase):
    """Synthetic local public-byte verification; no network or archived evidence."""

    def verify_snapshot(self, records):
        import contextlib
        import io
        import json
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import verify_stock_forecast_public as verifier

        scripts = (
            'assets/stock-forecast.js',
            'assets/stock-forecast-learning.js',
            'assets/stock-forecast-directions.js',
            'assets/stock-forecast-autopilot.js',
        )
        with tempfile.TemporaryDirectory() as temporary:
            previous = os.getcwd()
            try:
                os.chdir(temporary)
                payloads = {
                    'stock-direction-forecast.json': {
                        'generated_at': '2026-11-05T20:36:14+00:00',
                        'records': records,
                    },
                    'stock-forecast-learning.json': {'status': 'research_only'},
                    'stock-forecast-autopilot.json': {'status': 'research_cycle_verified'},
                }
                for filename, payload in payloads.items():
                    Path(filename).write_text(json.dumps(payload), encoding='utf-8')
                for filename in scripts:
                    target = Path(filename)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text('// SYNTHETIC verifier fixture\n', encoding='utf-8')
                Path('stock-value-radar.html').write_text(
                    '<html><head>' + ''.join(
                        '<script src="' + s + '"></script>' for s in scripts
                    ) + '</head></html>', encoding='utf-8')
                with patch.object(verifier, 'get_public',
                                  side_effect=lambda name: Path(name).read_bytes()):
                    with contextlib.redirect_stdout(io.StringIO()):
                        verifier.main(paper_only=False)
                ledger = Path('stock-forecast-deliveries.jsonl')
                return [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
            finally:
                os.chdir(previous)

    def test_no_call_only_snapshot_must_not_create_empty_public_proof(self):
        # RED on old producer: its unconditional append adds prediction_ids=[].
        rows = self.verify_snapshot([
            {'status': 'no_call', 'symbol': 'SYNTHETIC', 'reason': 'session_closed'},
        ])
        self.assertEqual(rows, [], 'No-call byte verification is not an issued forecast')

    def test_one_real_frozen_call_with_no_calls_still_gets_proof(self):
        import verify_stock_forecast_public as verifier
        rows = self.verify_snapshot([
            {'status': 'no_call', 'symbol': 'SYNTHETIC-NO-CALL'},
            {'status': 'research_prediction', 'id': 'SYNTHETIC-CALL'},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['prediction_ids'], ['SYNTHETIC-CALL'])
        self.assertIs(rows[0]['human_notification_received'], False)
        payload = {key: value for key, value in rows[0].items()
                   if key != 'verification_id'}
        self.assertEqual(rows[0]['verification_id'], verifier.digest(payload))


if __name__ == "__main__":
    unittest.main()
