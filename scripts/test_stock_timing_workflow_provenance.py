"""Synthetic fail-closed controls for GitHub-triggered audit evidence provenance.

No generated fixture is market data or proof of prediction edge. The positive
test only validates alignment of one GitHub event and archived research output.
"""
from copy import deepcopy
from pathlib import Path
import unittest

try:
    from audit_stock_timing_workflow_provenance import examine
except ImportError:
    examine = None


WORKFLOW = (Path(__file__).resolve().parents[1]
            / ".github/workflows/stock-forecast-independent-audit.yml")
RUN = "41157151233"
SHA = "f9db984b97b070ceca198ac023667740aebc3497"


def fixture():
    return (
        {"status": "research_cycle_verified",
         "version": "bounded-autopilot-1.0",
         "run_id": RUN, "source_commit": SHA,
         "generated_at": "2026-10-31T01:50:36.749289+00:00"},
        {"source_run_id": RUN,
         "generated_at": "2026-10-31T01:50:36.602632+00:00"},
        {"generated_at": "2026-10-31T01:50:36.602632+00:00"},
    )


class UpstreamRunEvidenceBinding(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(examine, "the provenance checker does not yet exist")
        self.controller, self.forecast, self.learning = fixture()

    def check(self, run=RUN, sha=SHA):
        return examine(self.controller, self.forecast, self.learning, run, sha)

    def test_matched_event_and_main_snapshot(self):
        result = self.check()
        self.assertEqual(result["status"], "upstream_run_evidence_matched")
        self.assertEqual(result["errors"], [])

    def test_rejects_newer_main_snapshot_for_older_trigger(self):
        self.controller["run_id"] = "41157151234"
        self.forecast["source_run_id"] = "41157151234"
        self.assertIn("controller_run_id_mismatch", self.check()["errors"])

    def test_rejects_upstream_commit_mismatch(self):
        self.controller["source_commit"] = "0" * 40
        self.assertIn("controller_source_commit_mismatch", self.check()["errors"])

    def test_rejects_forecast_generated_from_other_run(self):
        self.forecast["source_run_id"] = "41157151234"
        self.assertIn("forecast_run_id_mismatch", self.check()["errors"])

    def test_rejects_missing_or_reordered_snapshot_times(self):
        self.learning.pop("generated_at")
        self.assertIn("missing_or_invalid_generation_time", self.check()["errors"])
        self.learning["generated_at"] = "2026-10-31T01:55:00+00:00"
        self.assertIn("snapshot_generation_order_mismatch", self.check()["errors"])

    def test_rejects_invalid_event_identity(self):
        self.assertIn("invalid_expected_run_id", self.check(run="").get("errors", []))
        self.assertIn("invalid_expected_head_sha", self.check(sha="bad").get("errors", []))


class WorkflowIsolation(unittest.TestCase):
    def test_event_only_read_only_provenance_step(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/audit_stock_timing_workflow_provenance.py", s)
        self.assertIn("github.event.workflow_run.id", s)
        self.assertIn("github.event.workflow_run.head_sha", s)
        self.assertIn("if: github.event_name == 'workflow_run'", s)
        self.assertIn("permissions:\n  contents: read", s)
        self.assertIn("python scripts/audit_stock_forecast_independent.py", s)
        self.assertIn("python scripts/audit_stock_timing_acceptance_guard.py", s)
        self.assertIn("  workflow_dispatch:", s)
        self.assertIn("  schedule:\n    - cron: '33 * * * *'", s)


if __name__ == "__main__":
    unittest.main()
