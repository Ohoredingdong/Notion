"""Recognize only an observed, completely skipped news research job.

Artifact absence is never a reason to skip evidence checks. Unknown, partial,
or executed jobs still require the existing strict provenance audit. This
read-only classifier uses the initiating run's exact attempt, not wall time.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


GATE = "Skip news-triggered runs outside regular research hours"
GATED_STEPS = (
    "Run actions/checkout@v4",
    "Run actions/setup-python@v5",
    "Install model and session readers",
    "Test future targets, transaction rejection and bounded recovery",
    "Execute bounded autonomous research transaction",
    "Test actual forecast and autonomous status screens",
    "Publish forecast and learning state atomically",
    "Request public build",
    "Verify public autonomous cycle and code",
    "Verify paper plans in the same public build",
    "Preserve forecast and paper publication evidence with the matching audit",
    "Run actions/upload-artifact@v4",
)
EXPECTED_STEPS = ("Set up job", GATE, *GATED_STEPS, "Complete job")


def classify(event_name, event, jobs_payload, repository):
    required = {"audit_required": True, "reason": "execution_or_unrecognized_upstream"}
    if event_name != "workflow_run":
        return {"audit_required": True, "reason": "direct_audit_trigger"}
    if not isinstance(event, dict) or not isinstance(jobs_payload, dict):
        return required
    upstream = event.get("workflow_run")
    if not isinstance(upstream, dict):
        return required
    if (upstream.get("event") != "workflow_run"
            or upstream.get("status") != "completed"
            or upstream.get("conclusion") != "success"
            or upstream.get("path") != ".github/workflows/stock-forecasts.yml"
            or upstream.get("head_branch") != "main"
            or not repository
            or (upstream.get("head_repository") or {}).get("full_name") != repository):
        return required
    jobs = jobs_payload.get("jobs")
    if jobs_payload.get("total_count") != 1 or not isinstance(jobs, list) or len(jobs) != 1:
        return required
    job = jobs[0]
    if not isinstance(job, dict):
        return required
    if (job.get("name") != "research" or job.get("status") != "completed"
            or job.get("conclusion") != "success"
            or not upstream.get("id") or job.get("run_id") != upstream["id"]
            or not upstream.get("head_sha") or job.get("head_sha") != upstream["head_sha"]
            or not upstream.get("run_attempt") or job.get("run_attempt") != upstream["run_attempt"]):
        return required
    steps = job.get("steps")
    if not isinstance(steps, list) or not all(isinstance(step, dict) for step in steps):
        return required
    if tuple(step.get("name") for step in steps) != EXPECTED_STEPS:
        return required
    for step in steps:
        expected = "skipped" if step["name"] in GATED_STEPS else "success"
        if step.get("status") != "completed" or step.get("conclusion") != expected:
            return required
    return {"audit_required": False, "reason": "observed_news_gate_only_noop",
            "upstream_run_id": upstream["id"], "upstream_run_attempt": upstream["run_attempt"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True)
    args = parser.parse_args()
    report = classify(os.environ["GITHUB_EVENT_NAME"], json.loads(args.event.read_text()),
                      json.loads(args.jobs.read_text()), os.environ["GITHUB_REPOSITORY"])
    print(json.dumps(report))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as target:
        target.write("audit_required=" + str(report["audit_required"]).lower() + "\n")
    if not report["audit_required"]:
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as target:
            target.write("## No research cycle to audit\n\n"
                         "The initiating news-triggered run completed only its market-hours gate. "
                         "Checkout, research, publication, public verification and artifact upload "
                         "were all observed as skipped in that exact run attempt. "
                         "No forecast evidence was audited or approved by this no-op.\n")


if __name__ == "__main__":
    main()
