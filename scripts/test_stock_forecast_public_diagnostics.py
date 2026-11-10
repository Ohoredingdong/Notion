"""Synthetic RED/GREEN diagnostics for immutable public evidence checks only.

All HTTP byte responses are injected. No live quote, forecast, or delivery proof.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_stock_forecast_public as verifier


DATA = ("stock-direction-forecast.json", "stock-forecast-learning.json",
        "stock-forecast-autopilot.json")
SCRIPTS = ("assets/stock-forecast.js", "assets/stock-forecast-learning.js",
           "assets/stock-forecast-directions.js", "assets/stock-forecast-autopilot.js")


class PublicFailureDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.previous_cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.previous_cwd)
        self.remote = {}
        for i, name in enumerate(DATA):
            value = {"generated_at": "2026-11-10T00:00:00Z",
                     "records": []} if i == 0 else {"version": i}
            contents = json.dumps(value, sort_keys=True).encode("utf-8")
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_bytes(contents)
            self.remote[name] = contents
        for name in SCRIPTS:
            contents = ("// synthetic " + name).encode("utf-8")
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(contents)
            self.remote[name] = contents
        self.remote["stock-value-radar.html"] = (" ".join(SCRIPTS)).encode("utf-8")

    def check_failure(self, getter):
        with patch.object(verifier, "get_public", side_effect=getter), \
             patch.object(verifier.time, "sleep"):
            with self.assertRaises(RuntimeError) as caught:
                verifier.main(paper_only=False)
        self.assertFalse((self.root / "stock-forecast-deliveries.jsonl").exists(),
                         "Failed public verification must not manufacture delivery")
        return str(caught.exception)

    def test_json_mismatch_names_the_public_data_asset_without_weakening_gate(self):
        remote = dict(self.remote)
        remote["stock-forecast-autopilot.json"] = b'{"version":9999}'
        message = self.check_failure(remote.__getitem__)
        self.assertIn("public_snapshot_not_equal:stock-forecast-autopilot.json", message)

    def test_js_mismatch_names_the_public_code_asset(self):
        remote = dict(self.remote)
        remote["assets/stock-forecast-learning.js"] = b"// stale public JavaScript"
        message = self.check_failure(remote.__getitem__)
        self.assertIn("public_code_not_equal:assets/stock-forecast-learning.js", message)

    def test_missing_html_integration_is_distinguishable(self):
        remote = dict(self.remote)
        remote["stock-value-radar.html"] = b"<html>no forecast integration</html>"
        message = self.check_failure(remote.__getitem__)
        self.assertIn("main_radar_not_integrated", message)

    def test_untrusted_exception_text_is_not_reflected_or_marked_as_success(self):
        def forbidden(_):
            raise RuntimeError("PRIVATE_TOKEN=do-not-log;https://site/?auth=private")
        message = self.check_failure(forbidden)
        self.assertIn("public_deployment_unverified: RuntimeError", message)
        self.assertNotIn("PRIVATE_TOKEN", message)
        self.assertNotIn("auth=private", message)


if __name__ == "__main__":
    unittest.main()
