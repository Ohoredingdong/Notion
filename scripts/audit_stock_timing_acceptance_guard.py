"""Fail-closed, read-only timing-usefulness completion-claim guard.

The sample threshold is a minimum operating gate, NOT a statistical proof.
This checker cannot independently verify exchange quotes, user push receipts,
cost-after-delivery paper trades or an untouched follow-up window. Therefore
it never returns \"proven\". New independent evidence adapters and review are
required before any future successful completion claim is possible.

It never modifies forecasts, learning, strict-green approval or orders.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

LEDGER = "stock-forecast-ledger.jsonl"
AUDIT = "stock-forecast-independent-audit.json"
CONTROLLER = "stock-forecast-autopilot.json"
OUTPUT = "stock-timing-acceptance-guard.json"
CLASSES = ("down", "flat", "up")
MIN_TARGETS = 120
MIN_DAYS = 20
MIN_ACTUAL = 10
MIN_UP_DOWN_CALLS = 10
MARKET_ZONES = {"KR": ZoneInfo("Asia/Seoul"), "US": ZoneInfo("America/New_York")}


def instant(value):
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("timezone_required")
    return t


def key(row):
    target = row["target"]
    return (row["symbol"], row["market"], row["mode"], row.get("venue"),
            target["start"], target["end"])


def audit_acceptance(independent, ledger, controller):
    errors = []
    if independent.get("status") != "ledger_arithmetic_consistent":
        errors.append("upstream_audit_not_consistent")
    if type(independent.get("prediction_rows")) is not int or independent["prediction_rows"] != len(ledger):
        errors.append("upstream_prediction_count_mismatch")
    rows = independent.get("rows")
    if not isinstance(rows, list):
        errors.append("missing_upstream_scored_rows")
        rows = []
    if type(independent.get("scored")) is not int or independent["scored"] != len(rows):
        errors.append("upstream_scored_count_mismatch")

    originals = {}
    by_id = {}
    for frozen in ledger:
        try:
            if frozen["status"] != "research_prediction":
                raise ValueError("invalid_frozen_status")
            ident = frozen["id"]
            if ident in by_id:
                if by_id[ident] != frozen:
                    raise ValueError("conflicting_frozen_id")
                raise ValueError("duplicate_frozen_id")
            by_id[ident] = frozen
            if frozen["market"] not in MARKET_ZONES or frozen["mode"] not in ("daily", "intraday"):
                raise ValueError("unknown_market_mode")
            k = key(frozen)
            if k not in originals or instant(frozen["issued_at"]) < instant(originals[k]["issued_at"]):
                originals[k] = frozen
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(str(exc))

    groups = defaultdict(list)
    seen = set()
    correct_count = 0
    for row in rows:
        try:
            ident = row["id"]
            if ident in seen:
                raise ValueError("duplicate_scored_id")
            seen.add(ident)
            frozen = by_id.get(ident)
            if frozen is None:
                raise ValueError("scored_unknown_frozen_id")
            # An audit selection cannot choose later reissues of the same target.
            if originals.get(key(frozen), {}).get("id") != ident:
                raise ValueError("scored_not_first_issued_forecast")
            if (row["symbol"] != frozen["symbol"] or
                    row["predicted"] != frozen["direction"] or
                    row["target"] != frozen["target"] or
                    row["actual"] not in CLASSES or
                    type(row["correct"]) is not bool or
                    row["correct"] != (row["predicted"] == row["actual"])):
                raise ValueError("scored_row_mismatches_frozen")
            seen_public = instant(row["public_at"])
            start = instant(row["target"]["start"])
            end = instant(row["target"]["end"])
            if not (instant(frozen["issued_at"]) <= seen_public < start < end):
                raise ValueError("unusable_scored_public_or_target_time")
            correct_count += int(row["correct"])
            group = "|".join((frozen["symbol"], frozen["market"], frozen["mode"],
                              frozen.get("venue") or "venue_unverified"))
            session = start.astimezone(MARKET_ZONES[frozen["market"]]).date().isoformat()
            groups[group].append({"id": ident, "actual": row["actual"],
                                  "predicted": row["predicted"], "session": session,
                                  "start": start, "end": end})
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(str(exc))
    if type(independent.get("correct")) is not int or correct_count != independent["correct"]:
        errors.append("upstream_correct_count_mismatch")

    completed = {}
    for group, entries in sorted(groups.items()):
        ordered = sorted(entries, key=lambda e: (e["start"], e["end"]))
        for earlier, later in zip(ordered, ordered[1:]):
            if later["start"] < earlier["end"]:
                errors.append("overlap_in_independently_scored_group")
        actual = Counter(e["actual"] for e in ordered)
        calls = Counter(e["predicted"] for e in ordered)
        sessions = len({e["session"] for e in ordered})
        blockers = []
        if len(ordered) < MIN_TARGETS:
            blockers.append("insufficient_nonoverlapping_targets")
        if sessions < MIN_DAYS:
            blockers.append("insufficient_observed_sessions")
        for direction in CLASSES:
            if actual[direction] < MIN_ACTUAL:
                blockers.append("insufficient_actual_" + direction)
        for direction in ("up", "down"):
            if calls[direction] < MIN_UP_DOWN_CALLS:
                blockers.append("insufficient_" + direction + "_predictions")
        completed[group] = {
            "scored_nonoverlapping_targets": len(ordered),
            "observed_market_local_sessions": sessions,
            "actual": {c: actual[c] for c in CLASSES},
            "predicted_calls": {c: calls[c] for c in CLASSES},
            "minimal_sample_gate_met": not blockers,
            "blockers": blockers,
        }

    claim = controller.get("timing_utility") if isinstance(controller, dict) else None
    if not isinstance(claim, dict) or claim.get("status") != "not_proven":
        # This guard deliberately cannot authorize a positive claim without
        # independently connected quotes, receipts, trading costs and follow-up.
        errors.append("unverified_completion_claim")
    if isinstance(claim, dict) and claim.get("automatic_completion_notice") is True:
        errors.append("unverified_completion_notice_enabled")
    errors = sorted(set(errors))
    return {
        "version": "timing-acceptance-claim-guard-1.0",
        "status": "integrity_errors" if errors else "not_proven",
        "upstream_scored": len(rows),
        "upstream_correct_recomputed": correct_count,
        "groups": completed,
        "groups_with_minimal_sample_gate": sum(v["minimal_sample_gate_met"] for v in completed.values()),
        "contract_minima": {"nonoverlapping_targets_per_group": MIN_TARGETS,
                            "market_local_observed_sessions": MIN_DAYS,
                            "actual_per_class": MIN_ACTUAL,
                            "predicted_up_down_per_class": MIN_UP_DOWN_CALLS},
        "actual_human_receipt_verified": False,
        "actual_executable_quotes_verified": False,
        "official_venue_and_session_prices_verified": False,
        "after_cost_forward_paper_edge_verified": False,
        "untouched_followup_verified": False,
        "model_vs_baseline_forward_edge_verified_here": False,
        "strict_green_buy_approval": False,
        "automatic_completion_notice": False,
        "integrity_errors": errors,
        "scope": "Policy-minimum arithmetic and false-completion-claim check only; not live-price, human receipt or trading evidence.",
    }


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def main():
    report = audit_acceptance(
        json.loads(Path(AUDIT).read_text()), read_jsonl(LEDGER),
        json.loads(Path(CONTROLLER).read_text()))
    Path(OUTPUT).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"],
                      "upstream_scored": report["upstream_scored"],
                      "groups": len(report["groups"]),
                      "groups_with_minimal_sample_gate": report["groups_with_minimal_sample_gate"],
                      "evidence_gaps": [k for k in (
                          "actual_human_receipt_verified",
                          "actual_executable_quotes_verified",
                          "after_cost_forward_paper_edge_verified",
                          "untouched_followup_verified") if not report[k]],
                      "integrity_errors": report["integrity_errors"]}, ensure_ascii=False))
    if report["integrity_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
