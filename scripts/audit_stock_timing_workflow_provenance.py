"""Read-only fail-closed evidence binding for post-forecast workflow_run audits.

A GitHub Actions workflow_run payload identifies the invoking upstream run and
its source commit. The checked-out latest main may instead contain a later
research snapshot. Match both identities before presenting the downstream audit
as evidence for that upstream run. This is NOT proof of market prices, useful
signals, executable trades or human receipt. No writes or network calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def aware(value):
    if not isinstance(value, str):
        raise ValueError("timestamp_string_required")
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        raise ValueError("timezone_required")
    return moment.astimezone(timezone.utc)


def examine(controller, forecast, learning, expected_run_id, expected_head_sha):
    """Return separate provenance status; never amend, score, or train evidence."""
    errors = []
    if not isinstance(expected_run_id, str) or not re.fullmatch(r"[1-9][0-9]*", expected_run_id):
        errors.append("invalid_expected_run_id")
    if not isinstance(expected_head_sha, str) or not re.fullmatch(r"[a-fA-F0-9]{40}", expected_head_sha):
        errors.append("invalid_expected_head_sha")
    if not all(isinstance(obj, dict) for obj in (controller, forecast, learning)):
        return {"status": "upstream_run_mismatch",
                "errors": ["invalid_archive_structure"]}

    if (controller.get("version") != "bounded-autopilot-1.0"
            or controller.get("status") != "research_cycle_verified"):
        errors.append("controller_unverified_cycle")
    if controller.get("run_id") != expected_run_id:
        errors.append("controller_run_id_mismatch")
    if controller.get("source_commit") != expected_head_sha:
        errors.append("controller_source_commit_mismatch")
    if forecast.get("source_run_id") != expected_run_id:
        errors.append("forecast_run_id_mismatch")

    times = []
    try:
        times = [aware(obj.get("generated_at")) for obj in
                 (controller, forecast, learning)]
    except (ValueError, TypeError, OverflowError):
        errors.append("missing_or_invalid_generation_time")
    if len(times) == 3:
        controller_time, forecast_time, learning_time = times
        if forecast_time != learning_time or forecast_time > controller_time:
            errors.append("snapshot_generation_order_mismatch")

    errors = sorted(set(errors))
    return {"status": "upstream_run_mismatch" if errors else "upstream_run_evidence_matched",
            "errors": errors,
            "scope": ("Only binds workflow-run metadata to self-reported archived "
                      "source-run metadata; no exchange, notification or timing-edge proof.")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-head-sha", required=True)
    args = parser.parse_args()
    controller = json.loads(Path("stock-forecast-autopilot.json").read_text(encoding="utf-8"))
    forecast = json.loads(Path("stock-direction-forecast.json").read_text(encoding="utf-8"))
    learning = json.loads(Path("stock-forecast-learning.json").read_text(encoding="utf-8"))
    report = examine(controller, forecast, learning,
                     args.expected_run_id, args.expected_head_sha)
    print(json.dumps(report, ensure_ascii=False))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
