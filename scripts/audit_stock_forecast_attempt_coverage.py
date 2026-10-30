"""Independent read-only audit of scheduled forecast *attempts*, not trade signals.

Forecast correctness is separately audited in audit_stock_forecast_independent.py.
A repeated attempt referencing the same frozen prediction is not a new forecast.
Session-deferral reasons are not evidence of a data failure or lost trade.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

ATTEMPTS = "stock-forecast-attempts.jsonl"
LEDGER = "stock-forecast-ledger.jsonl"
REPORT = "stock-forecast-learning.json"
OUTPUT = "stock-forecast-attempt-coverage-audit.json"


def checked_instant(value):
    """Parse archived attempt clocks, rejecting naive/non-ISO timestamps."""
    if not isinstance(value, str):
        raise ValueError("checked_at_is_not_a_string")
    value = value.replace("Z", "+00:00")
    checked = datetime.fromisoformat(value)
    if checked.tzinfo is None:
        raise ValueError("timezone_required")
    return checked.astimezone(timezone.utc)


def audit_attempt_coverage(attempts, predictions, report):
    errors = []
    try:
        summary_time = checked_instant(report.get("generated_at"))
    except (ValueError, TypeError):
        errors.append("invalid_coverage_summary_generated_at")
        summary_time = None
    frozen_by_id = {}
    for row in predictions:
        if row.get("status") != "research_prediction":
            errors.append("invalid_forecast_reference_ledger_status")
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or not ident:
            errors.append("missing_forecast_reference_id")
            continue
        if ident in frozen_by_id and frozen_by_id[ident] != row:
            errors.append("conflicting_forecast_reference")
        frozen_by_id[ident] = row

    ids = set()
    valid_runs = set()
    calls = 0
    no_calls = 0
    reasons = Counter()
    categories = Counter()
    referenced = set()
    known_deferrals = {
        "insufficient_regular_session_time": "session_deferred",
        "target_already_started_or_delivery_window_too_short": "missed_delivery_window",
    }
    for row in attempts:
        ident = row.get("id")
        if not isinstance(ident, str) or not ident or ident in ids:
            errors.append("duplicate_attempt_id" if ident in ids else "invalid_attempt_id")
        else:
            ids.add(ident)
        run = row.get("run_id")
        if not isinstance(run, str) or not run:
            errors.append("missing_attempt_run_id")
        else:
            valid_runs.add(run)
        # This is a scheduler check, not forecast issuance, public delivery or
        # a user receipt. A later run can legitimately reference an old call.
        try:
            checked = checked_instant(row.get("checked_at"))
        except (ValueError, TypeError):
            errors.append("invalid_attempt_checked_at")
            checked = None
        if checked is not None:
            if summary_time is not None and checked > summary_time:
                errors.append("attempt_after_coverage_report")
            # One GitHub run_id can be rerun and archive a second legitimate
            # batch with a new checked_at; do not assume run_id is one clock.
        if row.get("mode") not in ("daily", "intraday") or not isinstance(row.get("symbol"), str):
            errors.append("invalid_attempt_group")
        status = row.get("status")
        if status == "research_prediction":
            calls += 1
            if row.get("reason") is not None:
                errors.append("issued_attempt_has_no_call_reason")
            pred_id = row.get("prediction_id")
            forecast = frozen_by_id.get(pred_id)
            if forecast is None:
                errors.append("attempt_unknown_prediction_id")
            else:
                referenced.add(pred_id)
                if forecast.get("symbol") != row.get("symbol") or forecast.get("mode") != row.get("mode"):
                    errors.append("attempt_prediction_symbol_mode_mismatch")
        elif status == "no_call":
            no_calls += 1
            if row.get("prediction_id") is not None:
                errors.append("no_call_has_prediction_id")
            reason = row.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append("no_call_missing_reason")
                continue
            reasons[reason] += 1
            category = known_deferrals.get(reason)
            if category is None:
                if "database is locked" in reason.lower():
                    category = "source_lock"
                elif "ratelimit" in reason.lower() or "rate limited" in reason.lower():
                    category = "source_rate_limit"
                else:
                    category = "other_unclassified_reason"
            categories[category] += 1
        else:
            errors.append("unexpected_attempt_status")

    total = len(attempts)
    rate = calls / total if total else None
    coverage = report.get("coverage") if isinstance(report, dict) else None
    expected = {"attempts": total, "prediction_attempts": calls, "no_calls": no_calls,
                "call_rate": rate, "no_call_reasons": dict(reasons)}
    if not isinstance(coverage, dict):
        errors.append("missing_reported_coverage")
    else:
        for field in ("attempts", "prediction_attempts", "no_calls"):
            if type(coverage.get(field)) is not int or coverage[field] != expected[field]:
                errors.append("reported_coverage_mismatch")
        stated_rate = coverage.get("call_rate")
        if (rate is None and stated_rate is not None or
            rate is not None and (isinstance(stated_rate, bool) or
            not isinstance(stated_rate, (int, float)) or not math.isfinite(stated_rate) or
            abs(stated_rate - rate) > 1e-12)):
            errors.append("reported_coverage_mismatch")
        if coverage.get("no_call_reasons") != expected["no_call_reasons"]:
            errors.append("reported_coverage_mismatch")
        if coverage.get("definition") != "scheduler-attempt coverage, not whole-market coverage":
            errors.append("reported_coverage_definition_mismatch")
    recorded = report.get("recorded_predictions") if isinstance(report, dict) else None
    if type(recorded) is not int or recorded != len(frozen_by_id):
        errors.append("reported_frozen_forecast_count_mismatch")

    facts = {"attempts": total, "prediction_attempts": calls, "no_calls": no_calls,
             "raw_attempt_call_rate": rate, "distinct_frozen_forecasts_referenced": len(referenced),
             "unique_run_ids": len(valid_runs), "session_deferred": categories["session_deferred"],
             "missed_delivery_window": categories["missed_delivery_window"],
             "source_lock": categories["source_lock"],
             "source_rate_limit": categories["source_rate_limit"],
             "other_unclassified_reasons": categories["other_unclassified_reason"]}
    return {
        "version": "forecast-attempt-coverage-audit-1.0",
        "status": "attempt_coverage_integrity_errors" if errors else "attempt_coverage_consistent",
        "facts": facts, "errors": sorted(set(errors)),
        "human_notification_receipt_verified": False,
        "eligible_market_opportunity_coverage_verified": False,
        "executable_quotes_verified": False,
        "scope": "Rechecks archived scheduler attempts and a generated coverage summary. "
                 "It does not prove full market coverage, user delivery or market execution.",
    }


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def main():
    result = audit_attempt_coverage(
        read_jsonl(ATTEMPTS), read_jsonl(LEDGER),
        json.loads(Path(REPORT).read_text()))
    Path(OUTPUT).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
