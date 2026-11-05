"""Regression controls for an actual all-skipped news upstream, not market proof."""
from copy import deepcopy
from pathlib import Path
import unittest

from audit_stock_timing_trigger import EXPECTED_STEPS, GATED_STEPS, classify


REPO = "Ohoredingdong/Notion"


def fixture():
    # Identities and step structure from the observed no-op run 42030390598.
    upstream = {"id": 42030390598, "run_attempt": 1,
                "head_sha": "6673a5592583543d6b569dd31ff09ab7b0f24c9d",
                "event": "workflow_run", "status": "completed", "conclusion": "success",
                "path": ".github/workflows/stock-forecasts.yml", "head_branch": "main",
                "head_repository": {"full_name": REPO}}
    job = {"name": "research", "status": "completed", "conclusion": "success",
           "run_id": upstream["id"], "run_attempt": upstream["run_attempt"],
           "head_sha": upstream["head_sha"],
           "steps": [{"name": name, "status": "completed",
                      "conclusion": "skipped" if name in GATED_STEPS else "success"}
                     for name in EXPECTED_STEPS]}
    return {"workflow_run": upstream}, {"total_count": 1, "jobs": [job]}


class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.event, self.jobs = fixture()

    def required(self, event_name="workflow_run"):
        return classify(event_name, self.event, self.jobs, REPO)["audit_required"]

    def test_observed_gate_only_noop_skips_evidence_claims(self):
        self.assertFalse(self.required())

    def test_direct_schedule_push_manual_and_pr_always_audit(self):
        for event_name in ("schedule", "push", "workflow_dispatch", "pull_request"):
            with self.subTest(event_name=event_name):
                self.assertTrue(self.required(event_name))

    def test_news_is_the_only_allowed_upstream_event(self):
        for event in ("push", "schedule", "workflow_dispatch", None):
            self.event["workflow_run"]["event"] = event
            self.assertTrue(self.required())

    def test_any_executed_or_failed_gated_step_requires_audit_even_without_artifact(self):
        for index in range(2, len(EXPECTED_STEPS) - 1):
            for conclusion in ("success", "failure", "cancelled", None):
                with self.subTest(step=EXPECTED_STEPS[index], conclusion=conclusion):
                    event, jobs = fixture()
                    jobs["jobs"][0]["steps"][index]["conclusion"] = conclusion
                    self.assertTrue(classify("workflow_run", event, jobs, REPO)["audit_required"])

    def test_real_execution_with_missing_or_failed_upload_is_not_skipped(self):
        steps = self.jobs["jobs"][0]["steps"]
        for step in steps:
            step["conclusion"] = "success"
        steps[-2]["conclusion"] = "failure"
        self.assertTrue(self.required())
        steps.pop(-2)
        self.assertTrue(self.required())

    def test_unproven_gate_or_incomplete_job_requires_audit(self):
        self.jobs["jobs"][0]["steps"][1]["conclusion"] = "skipped"
        self.assertTrue(self.required())
        self.event, self.jobs = fixture()
        self.jobs["jobs"][0]["status"] = "in_progress"
        self.assertTrue(self.required())

    def test_missing_duplicate_reordered_or_unknown_step_requires_audit(self):
        for mutation in ("missing", "duplicate", "reordered", "unknown"):
            event, jobs = fixture()
            steps = jobs["jobs"][0]["steps"]
            if mutation == "missing":
                steps.pop(2)
            elif mutation == "duplicate":
                steps.insert(2, deepcopy(steps[2]))
            elif mutation == "reordered":
                steps[2], steps[3] = steps[3], steps[2]
            else:
                steps.insert(-1, {"name": "Unknown work", "status": "completed", "conclusion": "skipped"})
            self.assertTrue(classify("workflow_run", event, jobs, REPO)["audit_required"])

    def test_other_run_commit_or_attempt_cannot_authorize_skip(self):
        for field, value in (("run_id", 9), ("head_sha", "f" * 40), ("run_attempt", 2)):
            event, jobs = fixture()
            jobs["jobs"][0][field] = value
            self.assertTrue(classify("workflow_run", event, jobs, REPO)["audit_required"])

    def test_foreign_or_failed_upstream_is_not_a_known_noop(self):
        for field, value in (("head_branch", "other"), ("path", "other.yml"),
                             ("conclusion", "failure"), ("head_repository", {"full_name": "other/repo"})):
            event, jobs = fixture()
            event["workflow_run"][field] = value
            self.assertTrue(classify("workflow_run", event, jobs, REPO)["audit_required"])

    def test_missing_truncated_or_multiple_jobs_requires_audit(self):
        for payload in ({}, {"total_count": 0, "jobs": []},
                        {"total_count": 2, "jobs": self.jobs["jobs"]},
                        {"total_count": 2, "jobs": self.jobs["jobs"] * 2}):
            self.assertTrue(classify("workflow_run", self.event, payload, REPO)["audit_required"])

    def test_classifier_does_not_mutate_evidence(self):
        before = deepcopy((self.event, self.jobs))
        self.required()
        self.assertEqual(before, (self.event, self.jobs))

    def test_workflow_uses_exact_attempt_and_preserves_strict_provenance(self):
        source = (Path(__file__).resolve().parents[1] / ".github/workflows/stock-forecast-independent-audit.yml").read_text()
        self.assertIn('/attempts/${UPSTREAM_ATTEMPT}/jobs?per_page=100', source)
        self.assertIn("github.event.workflow_run.run_attempt", source)
        self.assertIn("actions: read", source)
        self.assertIn("python scripts/audit_stock_timing_workflow_provenance.py", source)
        self.assertIn("if: always() && steps.upstream.outputs.audit_required == 'true'", source)
        self.assertIn("python scripts/test_stock_timing_trigger.py -v", source)


if __name__ == "__main__":
    unittest.main()
