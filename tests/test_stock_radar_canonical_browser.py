"""Fast safety checks for the browser runner; no browser, server, or network."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/test_stock_radar_canonical_browser.py"
SPEC = importlib.util.spec_from_file_location("radar_canonical_browser", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class CanonicalBrowserRunnerTests(unittest.TestCase):
    def test_membership_uses_saved_venue_and_explicit_current_dow(self):
        data = {"companies": [
            {"symbol": "kr", "source_symbol": "kr.KQ", "market": "KR"},
            {"symbol": "tech", "exchange": "NMS"},
            {"symbol": "industrial", "exchange": "NYQ"},
            {"symbol": "unclassified", "market": "US"},
        ]}
        groups = {"members": {"kr.KQ": {"venue": "KOSDAQ"}},
                  "dow": {"status": "current", "symbols": ["industrial"]}}
        self.assertEqual(runner.market_symbols(data, groups, "KOSDAQ"), {"kr"})
        self.assertEqual(runner.market_symbols(data, groups, "NASDAQ"), {"tech"})
        self.assertEqual(runner.market_symbols(data, groups, "DOW"), {"industrial"})
        groups["dow"]["status"] = "stale"
        self.assertEqual(runner.market_symbols(data, groups, "DOW"), set())

    def test_external_base_url_cannot_accidentally_target_production(self):
        for url in ("https://ohoredingdong.github.io/Notion/", "http://example.org/", "file:///tmp/"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "local HTTP"):
                with runner.serve(Path("."), url):
                    self.fail("external server was accepted")

    def test_artifacts_cannot_be_written_inside_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = [str(RUNNER_PATH), "--root", str(root), "--output", str(root / "screenshots")]
            with patch.object(sys, "argv", args), self.assertRaisesRegex(SystemExit, "outside the checkout"):
                runner.main()
            self.assertFalse((root / "screenshots").exists())

    def test_missing_browser_dependency_writes_failed_report_and_keeps_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, output = Path(temporary) / "checkout", Path(temporary) / "artifacts"
            root.mkdir()
            for name in (*runner.DATA_FILES, *runner.UI_FILES):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"companies": [{"symbol": "005930"}],
                                            "generated_at": "2026-11-05T00:00:00+00:00"}))
            before = runner.fingerprints(root)
            args = [str(RUNNER_PATH), "--root", str(root), "--output", str(output)]
            with patch.object(sys, "argv", args), patch.dict(sys.modules, {"playwright.sync_api": None}), redirect_stdout(io.StringIO()):
                result = runner.main()
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(result, 1)
            self.assertFalse(report["passed"])
            self.assertEqual(report["checks_failed"], 1)
            self.assertEqual(report["checks"][0]["name"], "browser runner infrastructure")
            self.assertEqual(runner.fingerprints(root), before)

    def test_failed_assertion_is_recorded_and_never_reported_as_pass(self):
        checks = object.__new__(runner.Checks)
        checks.report = {"checks": []}
        with redirect_stdout(io.StringIO()):
            checks.case("broken behavior", lambda: checks.check("wrong source data", False, "real mismatch"))
        self.assertTrue(checks.report["checks"])
        self.assertTrue(all(not item["pass"] for item in checks.report["checks"]))
        self.assertIn("real mismatch", checks.report["checks"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
