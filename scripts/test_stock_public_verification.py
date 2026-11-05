"""Synthetic, offline bounded public verification regression controls.

The mocked digest follows the real canonical hash format, but the model module is
stubbed to isolate HTTP retry / immutable public-proof behavior. No exchange data.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

MODEL_STUB = types.ModuleType("stock_forecast_model")
def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()
MODEL_STUB.digest = canonical_digest
SPEC = importlib.util.spec_from_file_location(
    "public_verifier_under_test", Path(__file__).with_name("verify_stock_forecast_public.py"))
with patch.dict(sys.modules, {"stock_forecast_model": MODEL_STUB}):
    VERIFY = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(VERIFY)

NAMES = ["stock-direction-forecast.json", "stock-forecast-learning.json", "stock-forecast-autopilot.json"]
SCRIPTS = ["assets/stock-forecast.js", "assets/stock-forecast-learning.js",
           "assets/stock-forecast-directions.js", "assets/stock-forecast-autopilot.js"]

class PublicVerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        old = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, old)
        self.payload = {}
        self.payload[NAMES[0]] = json.dumps({"generated_at": "2026-11-02T22:30:30+00:00",
                                            "records": [{"id": "synthetic-only", "status": "research_prediction"}]}).encode()
        self.payload[NAMES[1]] = b'{"status":"synthetic-only"}'
        self.payload[NAMES[2]] = b'{"status":"research_cycle_verified","timing_utility":{"status":"not_proven"}}'
        for name in SCRIPTS:
            self.payload[name] = ("// synthetic frozen JS: " + name).encode()
        self.payload["stock-value-radar.html"] = ("<html>" + "|".join(SCRIPTS) + "</html>").encode()
        for name, body in self.payload.items():
            dest = Path(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
        self.polls = 0

    def fake_public(self, *, stale_json_until=0, wrong_script=False, absent_html_asset=False):
        def fetch(request, timeout=15):
            name = urlsplit(request.full_url).path.split("/Notion/", 1)[1]
            if name == NAMES[0]:
                self.polls += 1
            if name == NAMES[0] and self.polls <= stale_json_until:
                return io.BytesIO(b'{"generated_at":"previous deployment","records":[]}')
            if name == SCRIPTS[1] and wrong_script:
                return io.BytesIO(b"// public mismatch in synthetic test")
            if name == "stock-value-radar.html" and absent_html_asset:
                return io.BytesIO(("<html>" + "|".join(SCRIPTS[:-1]) + "</html>").encode())
            return io.BytesIO(self.payload[name])
        return fetch

    def run_verifier(self, fetch, **kwargs):
        with patch.object(VERIFY.urllib.request, "urlopen", side_effect=fetch), \
             patch.object(VERIFY.time, "sleep", return_value=None):
            return VERIFY.main(**kwargs)

    def proof_rows(self):
        p = Path("stock-forecast-deliveries.jsonl")
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def test_delayed_matching_public_snapshot_after_twenty_three_rounds(self):
        self.run_verifier(self.fake_public(stale_json_until=23))
        self.assertEqual(self.polls, 24)
        proof = self.proof_rows()
        self.assertEqual(len(proof), 1)
        self.assertEqual(proof[0]["prediction_ids"], ["synthetic-only"])
        self.assertIs(proof[0]["human_notification_received"], False)
        self.assertEqual(proof[0]["verification_id"],
                         canonical_digest({k:v for k,v in proof[0].items() if k!="verification_id"}))

    def test_permanently_stale_fails_closed_without_proof(self):
        with self.assertRaisesRegex(RuntimeError, "public_deployment_unverified"):
            self.run_verifier(self.fake_public(stale_json_until=500))
        self.assertEqual(self.proof_rows(), [])

    def test_public_javascript_mismatch_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "public_deployment_unverified.*public_code_not_equal"):
            self.run_verifier(self.fake_public(wrong_script=True))
        self.assertEqual(self.proof_rows(), [])

    def test_missing_html_integration_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "public_deployment_unverified.*main_radar_not_integrated"):
            self.run_verifier(self.fake_public(absent_html_asset=True))
        self.assertEqual(self.proof_rows(), [])

    def test_probe_only_never_creates_delivery_record(self):
        self.run_verifier(self.fake_public(), probe_only=True)
        self.assertEqual(self.polls, 1)
        self.assertEqual(self.proof_rows(), [])

if __name__ == "__main__":
    unittest.main()
