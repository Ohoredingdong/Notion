"""Read-only fail-closed evidence binding for post-forecast workflow_run audits.

A GitHub Actions workflow_run payload identifies the invoking run and its event
commit. A queued producer intentionally checks out the latest branch head.
Bind the archived event to that run and check the separately reported checkout;
do not confuse either with a later, unrelated research snapshot. This is NOT
proof of market prices, useful signals, executable trades or human receipt.
No writes or network calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from stock_forecast_identity import RESOLVED, valid_commit


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
    if not valid_commit(expected_head_sha):
        errors.append("invalid_expected_head_sha")
    if not all(isinstance(obj, dict) for obj in (controller, forecast, learning)):
        return {"status": "upstream_run_mismatch",
                "errors": ["invalid_archive_structure"]}

    if (controller.get("version") != "bounded-autopilot-1.0"
            or controller.get("status") != "research_cycle_verified"):
        errors.append("controller_unverified_cycle")
    if controller.get("run_id") != expected_run_id:
        errors.append("controller_run_id_mismatch")
    explicit_identity = any(key in controller for key in
                            ("event_commit", "source_identity_status"))
    if explicit_identity:
        # A queued producer deliberately checks out the latest branch, so its
        # actual code HEAD may differ from the initiating workflow event SHA.
        for label, archive in (("controller", controller), ("forecast", forecast)):
            if not valid_commit(archive.get("event_commit")):
                errors.append(f"invalid_{label}_event_commit")
            elif archive["event_commit"] != expected_head_sha:
                errors.append(f"{label}_event_commit_mismatch")
            if not valid_commit(archive.get("source_commit")):
                errors.append(f"invalid_{label}_source_commit")
            if archive.get("source_identity_status") != RESOLVED:
                errors.append(f"{label}_source_identity_unverified")
        if forecast.get("source_commit") != controller.get("source_commit"):
            errors.append("forecast_source_commit_mismatch")
    elif controller.get("source_commit") != expected_head_sha:
        # Historical reports did not distinguish the event from the checkout.
        # Preserve their original event-binding rule; never rewrite archives.
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
            "identity_mode": ("event_and_checkout" if explicit_identity
                              else "legacy_source_commit_event_fallback"),
            "event_commit": controller.get("event_commit") if explicit_identity
                            else controller.get("source_commit"),
            "source_commit": controller.get("source_commit"),
            "scope": ("Only binds workflow-run metadata to self-reported archived "
                      "event/checkout metadata; the code SHA format and resolved label "
                      "are not an authenticated attestation, exchange, notification "
                      "or timing-edge proof.")}


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
