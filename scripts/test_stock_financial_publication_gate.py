"""Regression: failed current collection must not publish a fresh catalogue."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from scripts.check_stock_financial_publication import require_publishable_refresh

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/stock-financial-coverage.yml"


class FinancialPublicationGateTests(unittest.TestCase):
    def test_fail_closed_despite_retained_historical_coverage(self):
        document = {"current_run_failed": True, "refresh_status": "partial",
                    "financial_available": {"KR": 2648, "US": 0},
                    "run": {"US": {"attempted": 60, "provider_errors": 60}}}
        with self.assertRaisesRegex(ValueError, "current_financial_refresh_unverified"):
            require_publishable_refresh(document)
        for missing_or_invalid in ({}, {"current_run_failed": None},
                                   {"current_run_failed": 0}, {"current_run_failed": "false"}):
            with self.subTest(missing_or_invalid=missing_or_invalid):
                with self.assertRaises(ValueError):
                    require_publishable_refresh(missing_or_invalid)

    def test_only_explicit_verified_boolean_false_passes_this_gate(self):
        source = {"current_run_failed": False, "refresh_status": "success",
                  "financial_available": {"KR": 7, "US": 3}}
        self.assertIs(require_publishable_refresh(source), source)

    def test_cli_blocks_failed_refresh_and_allows_verified_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stock-financial-coverage.json"
            for failed, expected in ((True, 1), (False, 0)):
                path.write_text(json.dumps({"current_run_failed": failed, "refresh_status":
                                            "partial" if failed else "success"}), encoding="utf-8")
                run = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/check_stock_financial_publication.py")],
                    cwd=folder, capture_output=True, text=True, check=False)
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)

    def test_workflow_gate_is_after_identity_validation_but_before_any_push(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        valid = text.index("name: Validate aligned catalogue and every displayable issuer identity")
        gate = text.index("name: Reject failed current refresh before any publication")
        publication = text.index("name: Publish a coherent snapshot only if its source was not superseded")
        pages = text.index("name: Request existing Pages build for a published main snapshot")
        self.assertLess(valid, gate)
        self.assertLess(gate, publication)
        self.assertLess(publication, pages)
        self.assertIn("run: python scripts/check_stock_financial_publication.py", text)
        self.assertIn("if: always()", text)
        self.assertIn("official-stock-financial-evidence", text)


if __name__ == "__main__":
    unittest.main()
