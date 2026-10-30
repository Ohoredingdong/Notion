"""Synthetic/static controls for post-forecast independent audit handoff.

These tests verify the reviewed YAML contract. Only an actual Actions run can
establish that GitHub delivered the workflow_run event and read the latest data.
They do not validate forecasts, quotes, or trading profitability.
"""
from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/stock-forecast-independent-audit.yml"


class PostForecastAuditHandoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        cls.triggers = cls.source.split("\npermissions:", 1)[0]

    def test_completed_forecast_main_is_an_audit_trigger(self):
        self.assertRegex(
            self.triggers,
            r"(?m)^  workflow_run:\n"
            r"    workflows: \['Stock Prospective Forecasts'\]\n"
            r"    types: \[completed\]\n"
            r"    branches: \[main\]\n",
        )

    def test_failure_and_foreign_repo_cannot_trigger_audit_job(self):
        job = re.search(r"(?ms)^  independent-audit:\n(.*?)(?=^  [a-z_-]+:\n|\Z)", self.source)
        self.assertIsNotNone(job)
        condition = re.search(r"(?m)^    if: (.+)$", job.group(1))
        self.assertIsNotNone(condition)
        expression = condition.group(1)
        self.assertIn("github.event_name != 'workflow_run'", expression)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", expression)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", expression)
        self.assertIn("github.event.workflow_run.head_repository.full_name == github.repository", expression)
        self.assertIn("&&", expression)
        self.assertIn("||", expression)

    def test_existing_schedule_and_manual_entry_preserved(self):
        self.assertIn("  workflow_dispatch:", self.triggers)
        self.assertIn("  schedule:\n    - cron: '33 * * * *'", self.triggers)

    def test_pr_premerge_replay_uses_branch_but_production_reads_main(self):
        self.assertIn("  pull_request:", self.triggers)
        self.assertIn("github.event_name == 'pull_request' && github.event.pull_request.head.sha || 'main'", self.source)
        self.assertIn("python scripts/test_stock_timing_audit_handoff.py -v", self.source)

    def test_workflow_remains_read_only_and_checks_acceptance(self):
        self.assertIn("permissions:\n  contents: read", self.source)
        self.assertIn("python scripts/audit_stock_forecast_independent.py", self.source)
        self.assertIn("python scripts/audit_stock_learning_evidence.py", self.source)
        self.assertIn("python scripts/audit_stock_forecast_attempt_coverage.py", self.source)
        self.assertIn("python scripts/audit_stock_timing_acceptance_guard.py", self.source)
        self.assertIn("cancel-in-progress: false", self.source)


if __name__ == "__main__":
    unittest.main()
