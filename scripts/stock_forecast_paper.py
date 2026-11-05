"""Prospective, orderless quote/cost experiment and frozen shadow diagnostics.

No historical plans, quotes, receipts, costs or probabilities are fabricated.
Schema/chronology checks are NOT provider authentication or execution evidence.
This module never promotes a model or certifies timing usefulness.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

VERSION = "forecast-paper-evidence-1.0"
POLICY_FILE = "stock-forecast-paper-policy.json"
PLAN_FILE = "stock-forecast-paper-plans.jsonl"
PUBLICATION_FILE = "stock-forecast-paper-publication-verifications.jsonl"
PUBLICATION_VERSION = "forecast-paper-publication-1.0"
PUBLIC_BASE = "https://ohoredingdong.github.io/Notion/"
REPORT_FILE = "stock-forecast-paper-audit.json"
SHADOW_FILE = "stock-forecast-shadow-comparison.json"
EVIDENCE_FILE = "stock-forecast-execution-evidence.jsonl"
COST_FILE = "stock-forecast-paper-cost-schedules.json"
PAPER_OUTPUTS = (POLICY_FILE, PLAN_FILE, PUBLICATION_FILE, REPORT_FILE, SHADOW_FILE)
READ_ONLY_INPUTS = (EVIDENCE_FILE, COST_FILE)
CLASSES = ("down", "flat", "up")
CANDIDATES = ("adaptive", "balanced_linear", "balanced_nonlinear", "movement_then_direction")
ZONES = {"KR": ZoneInfo("Asia/Seoul"), "US": ZoneInfo("America/New_York")}
VENUES = {"KR": {"XKRX"}, "US": {"XNYS", "XNAS"}}
RULES = {
    "strategy": "up_long_else_cash",
    "benchmarks": ["always_cash", "always_long", "frozen_baseline_long_else_cash"],
    "maximum_shares": 1,
    "minimum_registration_lead_seconds": 60,
    "entry_window_seconds": 60,
    "exit_window_seconds_before_target_end": 60,
    "maximum_quote_latency_seconds": 5,
    "maximum_spread_bps": 50,
    "entry_selection": "first_received_quote_in_fixed_window",
    "exit_selection": "first_received_quote_in_fixed_preclose_window",
    "bad_first_entry_quote": "cancel_without_replacement",
    "bad_or_missing_exit_quote": "unresolved_not_assumed_fill",
    "cost_schedule_must_be_frozen_before_target": True,
    "slippage_is_explicit_assumption": True,
    "orders_enabled": False,
    "strict_green_override": False,
}


def instant(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone_required")
    return result.astimezone(timezone.utc)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite_number_required")
    return float(value)


def evidence_error(error):
    # Never copy an invalid receipt field, raw provider payload or URL into a
    # public report through a parser's exception text.
    message = str(error)
    return message if re.fullmatch(r"[a-z][a-z0-9_]{1,100}", message) else "invalid_evidence_schema"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else deepcopy(default)


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def distribution(value):
    if not isinstance(value, dict) or set(value) != set(CLASSES):
        raise ValueError("invalid_frozen_probability_vector")
    values = [number(value[key]) for key in CLASSES]
    if min(values) < 0 or max(values) > 1 or abs(math.fsum(values) - 1) > 1e-7:
        raise ValueError("invalid_frozen_probability_vector")
    return values


def direction(value):
    values = distribution(value)
    return CLASSES[max(range(3), key=lambda index: values[index])]


def probabilities(record, variant):
    if variant == "active":
        return record["probabilities"]
    if variant == "frozen_baseline":
        return record.get("frozen_baseline_probabilities")
    learning = record.get("online_learning") or {}
    if variant == "incumbent":
        return learning.get("incumbent_probabilities", record["probabilities"])
    if variant == "adaptive":
        return learning.get("challenger_probabilities")
    return ((record.get("directional_specialists") or {}).get("candidates") or {}).get(variant, {}).get("probabilities")


def metrics(pairs):
    """Independent stdlib arithmetic; does not call the model metric functions."""
    matrix = [[0, 0, 0] for _ in CLASSES]
    brier, logs = [], []
    for actual, value in pairs:
        truth = CLASSES.index(actual)
        p = distribution(value)
        predicted = max(range(3), key=lambda index: p[index])
        matrix[truth][predicted] += 1
        brier.append(math.fsum((p[index] - int(index == truth)) ** 2 for index in range(3)))
        logs.append(-math.log(max(p[truth], 1e-9)))
    size = len(pairs)
    directions = {}
    for index, name in enumerate(CLASSES):
        actual = sum(matrix[index])
        calls = sum(row[index] for row in matrix)
        correct = matrix[index][index]
        directions[name] = {"actual": actual, "calls": calls, "correct": correct,
                            "missed": actual - correct, "false_calls": calls - correct,
                            "recall": correct / actual if actual else None,
                            "precision": correct / calls if calls else None}
    correct = sum(matrix[index][index] for index in range(3))
    return {"samples": size, "correct": correct, "accuracy": correct / size if size else None,
            "confusion_matrix": matrix, "directions": directions,
            "brier_loss": math.fsum(brier) / size if size else None,
            "log_loss": math.fsum(logs) / size if size else None}


def compare_frozen(records, independent, cutoff):
    by_id = {row["id"]: row for row in records}
    comparisons = {}
    for variant in ("active", "frozen_baseline") + CANDIDATES:
        cohort = [row for row in independent["rows"] if probabilities(by_id[row["id"]], variant) is not None]
        reference = metrics([(row["actual"], probabilities(by_id[row["id"]], "incumbent")) for row in cohort])
        candidate = metrics([(row["actual"], probabilities(by_id[row["id"]], variant)) for row in cohort])
        groups = defaultdict(list)
        for row in cohort:
            frozen = by_id[row["id"]]
            groups["|".join((frozen["symbol"], frozen["market"], frozen["mode"]))].append(frozen)
        group_counts = {}
        for key, values in sorted(groups.items()):
            days = {instant(row["target"]["start"]).astimezone(ZONES[row["market"]]).date().isoformat() for row in values}
            group_counts[key] = {"samples": len(values), "market_local_days": len(days),
                                 "minimum_count_and_days_met": len(values) >= 120 and len(days) >= 20}
        comparisons[variant] = {
            "candidate": candidate, "incumbent_on_identical_cohort": reference,
            "missing_frozen_vector": independent["scored"] - len(cohort),
            "cohort_sha256": digest([row["id"] for row in cohort]),
            "brier_improvement_vs_incumbent": reference["brier_loss"] - candidate["brier_loss"] if cohort else None,
            "log_loss_improvement_vs_incumbent": reference["log_loss"] - candidate["log_loss"] if cohort else None,
            "per_group": group_counts,
            "groups_with_minimum_count_and_days": sum(group["minimum_count_and_days_met"] for group in group_counts.values()),
        }
    return {"version": VERSION, "generated_at": cutoff.isoformat(),
            "status": "descriptive_frozen_forecasts_only", "independently_scored": independent["scored"],
            "comparisons": comparisons, "model_trials": 0, "refits": 0, "promotions": 0,
            "retroactive_probabilities_created": 0, "untouched_confirmation": False,
            "timing_utility": "not_proven", "orders_enabled": False,
            "scope": "Paired descriptive diagnostics on recorded probabilities; no candidate selection or trading proof."}


def policy_for(existing, cutoff):
    if existing:
        payload = {key: value for key, value in existing.items() if key != "id"}
        if (existing.get("version") != VERSION or existing.get("rules") != RULES
                or digest(payload) != existing.get("id") or instant(existing["registered_at"]) > cutoff):
            raise ValueError("immutable_paper_policy_mismatch")
        return existing
    payload = {"version": VERSION, "registered_at": cutoff.isoformat(), "rules": deepcopy(RULES),
               "source_commit": os.environ.get("GITHUB_SHA"), "purpose": "orderless_research_only"}
    return {**payload, "id": digest(payload)}


def cost_schedule(value, market, registered_at, start, end):
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("market") != market:
        raise ValueError("cost_schedule_market_mismatch")
    if value.get("basis") not in ("published_schedule", "explicit_assumption"):
        raise ValueError("cost_basis_missing")
    source = urlparse(str(value.get("source_url", "")))
    if source.scheme != "https" or not source.hostname or source.username or source.password or source.query:
        raise ValueError("cost_source_reference_required")
    if not (instant(value["recorded_at"]) <= registered_at and
            instant(value["effective_from"]) <= start < end <= instant(value["effective_until"])):
        raise ValueError("cost_schedule_not_preregistered_or_effective")
    for key in ("buy_fee_bps", "sell_fee_bps", "sell_tax_bps", "assumed_slippage_bps_per_side"):
        if not 0 <= number(value[key]) <= 1000:
            raise ValueError("cost_rate_out_of_range")
    return deepcopy(value)


def register_plans(records, deliveries, policy, existing, schedules, cutoff):
    from audit_stock_forecast_independent import event_key, validate
    by_forecast = {}
    by_id = {record["id"]: record for record in records}
    for plan in existing:
        payload = {key: value for key, value in plan.items() if key != "id"}
        frozen = by_id.get(plan.get("forecast_id"))
        if (digest(payload) != plan.get("id") or plan.get("policy_id") != policy["id"] or
                frozen is None or digest(frozen) != plan.get("forecast_sha256") or
                plan["forecast_id"] in by_forecast):
            raise ValueError("immutable_paper_plan_mismatch")
        if not instant(policy["registered_at"]) <= instant(plan["registered_at"]) < instant(plan["target"]["start"]):
            raise ValueError("retrospective_paper_plan")
        if (any(plan.get(key) != frozen.get(key) for key in ("symbol", "market", "mode", "target", "direction"))
                or plan.get("strategy") != ("long" if frozen["direction"] == "up" else "cash")
                or plan.get("currency") != ("KRW" if frozen["market"] == "KR" else "USD")
                or plan.get("orders_enabled") is not False or plan.get("strict_green_override") is not False):
            raise ValueError("paper_plan_disagrees_with_frozen_forecast")
        baseline = frozen.get("frozen_baseline_probabilities")
        expected_baseline = ("long" if direction(baseline) == "up" else "cash") if baseline is not None else None
        if plan.get("baseline_strategy") != expected_baseline:
            raise ValueError("paper_baseline_not_frozen")
        by_forecast[plan["forecast_id"]] = plan
    public = {}
    for proof in deliveries:
        if proof.get("status") == "public_verified" and instant(proof["verified_at"]) <= cutoff:
            for identifier in proof.get("prediction_ids", []):
                public[identifier] = min(public.get(identifier, instant(proof["verified_at"])), instant(proof["verified_at"]))
    first = {}
    for frozen in sorted(records, key=lambda row: (instant(row["issued_at"]), row["id"])):
        validate(frozen)
        first.setdefault(event_key(frozen), frozen)
    additions, skipped = [], Counter()
    occupied = defaultdict(list)
    for plan in existing:
        occupied[(plan["symbol"], plan["market"], plan["mode"])].append((instant(plan["target"]["start"]), instant(plan["target"]["end"])))
    for frozen in sorted(first.values(), key=lambda row: (instant(row["target"]["start"]), row["id"])):
        if frozen["id"] in by_forecast:
            continue
        start, end = instant(frozen["target"]["start"]), instant(frozen["target"]["end"])
        if start <= cutoff + timedelta(seconds=RULES["minimum_registration_lead_seconds"]):
            skipped["target_started_or_registration_window_too_short"] += 1
            continue
        if frozen["symbol"].startswith("^"):
            skipped["index_is_not_executable_share"] += 1
            continue
        if not instant(frozen["issued_at"]) <= public.get(frozen["id"], end) <= cutoff < start:
            skipped["first_forecast_not_public_before_registration"] += 1
            continue
        group = (frozen["symbol"], frozen["market"], frozen["mode"])
        if any(start < previous_end and previous_start < end for previous_start, previous_end in occupied[group]):
            skipped["overlapping_paper_target"] += 1
            continue
        baseline = frozen.get("frozen_baseline_probabilities")
        payload = {"version": VERSION, "policy_id": policy["id"], "registered_at": cutoff.isoformat(),
                   "forecast_id": frozen["id"], "forecast_sha256": digest(frozen),
                   "symbol": frozen["symbol"], "market": frozen["market"], "mode": frozen["mode"],
                   "currency": "KRW" if frozen["market"] == "KR" else "USD",
                   "target": deepcopy(frozen["target"]), "first_public_at": public[frozen["id"]].isoformat(),
                   "direction": frozen["direction"], "strategy": "long" if frozen["direction"] == "up" else "cash",
                   "baseline_strategy": ("long" if direction(baseline) == "up" else "cash") if baseline is not None else None,
                   "cost_schedule": cost_schedule(schedules.get(frozen["market"]), frozen["market"], cutoff, start, end),
                   "orders_enabled": False, "strict_green_override": False}
        additions.append({**payload, "id": digest(payload)})
        occupied[group].append((start, end))
    return additions, dict(skipped)


def validate_quote(quote, plan, earliest, latest, receipt_at):
    if any(quote.get(key) != plan[key] for key in ("symbol", "market", "currency")):
        raise ValueError("quote_identity_mismatch")
    if quote.get("venue") not in VENUES[plan["market"]] or quote.get("session") != "regular":
        raise ValueError("quote_venue_or_session_mismatch")
    if quote.get("kind") != "observed_bid_ask" or quote.get("source_kind") not in ("official_exchange", "licensed_broker"):
        raise ValueError("executable_quote_source_missing")
    if (not isinstance(quote.get("source_event_id"), str) or not quote["source_event_id"] or
            not isinstance(quote.get("raw_sha256"), str) or
            not re.fullmatch(r"[0-9a-f]{64}", quote["raw_sha256"])):
        raise ValueError("quote_raw_provenance_missing")
    observed, received = instant(quote["observed_at"]), instant(quote["received_at"])
    if not receipt_at <= earliest <= observed <= received <= latest:
        raise ValueError("quote_not_available_in_action_window")
    if (received - observed).total_seconds() > RULES["maximum_quote_latency_seconds"]:
        raise ValueError("stale_quote")
    bid, ask = number(quote["bid"]), number(quote["ask"])
    if not 0 < bid <= ask:
        raise ValueError("invalid_bid_ask")
    if number(quote["bid_size"]) < 1 or number(quote["ask_size"]) < 1:
        raise ValueError("insufficient_quote_size")
    if (ask - bid) / ((ask + bid) / 2) * 10000 > RULES["maximum_spread_bps"]:
        raise ValueError("spread_above_preregistered_limit")


def verified_plan_publication(plan, policy, publications, cutoff):
    """Return only an intact, actually timestamped, before-target public check.

    A website check never stands in for a person's receipt. Late checks stay in
    the append-only ledger, but cannot make a historical plan prospective.
    """
    valid = []
    for proof in publications:
        if proof.get("plan_id") != plan["id"]:
            continue
        payload = {key: value for key, value in proof.items() if key != "verification_id"}
        verified = instant(proof["verified_at"])
        before = instant(plan["registered_at"]) <= verified < instant(plan["target"]["start"])
        hashes = proof.get("public_files_sha256", {})
        if (proof.get("version") != PUBLICATION_VERSION or proof.get("status") != "public_plan_verified"
                or proof.get("verification_id") != digest(payload)
                or proof.get("base_url") != PUBLIC_BASE
                or proof.get("human_notification_received") is not False
                or proof.get("policy_id") != policy["id"]
                or proof.get("policy_sha256") != digest(policy)
                or proof.get("forecast_id") != plan["forecast_id"]
                or proof.get("plan_sha256") != digest(plan)
                or proof.get("public_before_target_verified") is not before
                or verified < instant(plan["registered_at"])
                or verified > cutoff
                or set(hashes) != {POLICY_FILE, PLAN_FILE}
                or any(not re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in hashes.values())):
            raise ValueError("invalid_paper_publication_proof")
        if before:
            valid.append(proof)
    return min(valid, key=lambda row: instant(row["verified_at"])) if valid else None


def evaluate_plan(plan, bundles, cutoff, public_proof=None):
    result = {"plan_id": plan["id"], "forecast_id": plan["forecast_id"], "symbol": plan["symbol"],
              "target": plan["target"], "status": "pending", "blockers": [],
              "plan_public_before_target_verified": public_proof is not None,
              "plan_public_verified_at": public_proof["verified_at"] if public_proof else None,
              "actual_fill_verified": False, "external_evidence_authenticated": False}
    start, end = instant(plan["target"]["start"]), instant(plan["target"]["end"])
    if not bundles:
        result.update(status="awaiting_execution_evidence" if cutoff < end else "missing_execution_evidence",
                      blockers=["human_receipt_missing", "observed_quotes_missing"])
        if public_proof is None:
            result["blockers"].append("plan_publication_proof_missing")
        if plan.get("cost_schedule") is None:
            result["blockers"].append("preregistered_cost_schedule_missing")
        return result
    if len(bundles) != 1:
        result.update(status="invalid_evidence", blockers=["duplicate_execution_evidence"])
        return result
    evidence = bundles[0]
    try:
        if evidence.get("forecast_id") != plan["forecast_id"] or evidence.get("plan_id") != plan["id"]:
            raise ValueError("execution_evidence_identity_mismatch")
        recorded = instant(evidence["recorded_at"])
        if recorded > cutoff:
            raise ValueError("future_execution_evidence")
        proof = evidence.get("plan_publication") or public_proof or {}
        if (proof.get("plan_id") != plan["id"] or proof.get("plan_sha256") != digest(plan) or
                not instant(plan["registered_at"]) <= instant(proof["verified_at"]) < start or
                instant(proof["verified_at"]) > recorded):
            raise ValueError("plan_publication_proof_missing_or_late")
        receipt = evidence.get("human_receipt") or {}
        if receipt.get("kind") != "human_receipt" or receipt.get("forecast_id") != plan["forecast_id"] or not receipt.get("receipt_id"):
            raise ValueError("human_receipt_missing")
        received = instant(receipt["received_at"])
        if not max(instant(plan["first_public_at"]), instant(proof["verified_at"])) <= received < start or received > recorded:
            raise ValueError("human_receipt_after_target_start_or_before_publication")
        if evidence.get("corporate_action_clear") is not True:
            raise ValueError("corporate_action_review_missing")
        schedule = plan.get("cost_schedule")
        if schedule is None:
            raise ValueError("preregistered_cost_schedule_missing")
        cost_schedule(schedule, plan["market"], instant(plan["registered_at"]), start, end)
        quotes = evidence.get("quotes")
        if not isinstance(quotes, list):
            raise ValueError("observed_quotes_missing")
        if any(instant(q["received_at"]) > recorded for q in quotes):
            raise ValueError("quote_not_recorded_before_evidence")
        def first_in_window(earliest, latest):
            available = sorted((q for q in quotes if earliest <= instant(q["received_at"]) <= latest),
                               key=lambda q: (instant(q["received_at"]), str(q.get("source_event_id", ""))))
            if not available:
                raise ValueError("quote_window_missing")
            return available[0]
        if cutoff < start:
            result["status"] = "awaiting_target"
            return result
        entry_end = start + timedelta(seconds=RULES["entry_window_seconds"])
        try:
            entry = first_in_window(start, min(entry_end, cutoff))
            validate_quote(entry, plan, start, entry_end, received)
        except (KeyError, TypeError, ValueError) as error:
            result.update(status="entry_cancelled" if cutoff >= entry_end else "entry_pending",
                          blockers=[evidence_error(error)])
            return result
        exit_start = end - timedelta(seconds=RULES["exit_window_seconds_before_target_end"])
        if cutoff < exit_start:
            result["status"] = "awaiting_exit_quote"
            return result
        try:
            exit_quote = first_in_window(exit_start, min(end, cutoff))
            validate_quote(exit_quote, plan, exit_start, end, received)
            if entry["venue"] != exit_quote["venue"]:
                raise ValueError("entry_exit_venue_mismatch")
        except (KeyError, TypeError, ValueError) as error:
            result.update(status="exit_unresolved", blockers=[evidence_error(error)])
            return result
        slip = schedule["assumed_slippage_bps_per_side"] / 10000
        entry_price = entry["ask"] * (1 + slip)
        exit_price = exit_quote["bid"] * (1 - slip)
        capital = entry_price * (1 + schedule["buy_fee_bps"] / 10000)
        proceeds = exit_price * (1 - (schedule["sell_fee_bps"] + schedule["sell_tax_bps"]) / 10000)
        long_return = (proceeds / capital - 1) * 100
        strategy = long_return if plan["strategy"] == "long" else 0.0
        baseline = (long_return if plan["baseline_strategy"] == "long" else 0.0) if plan["baseline_strategy"] is not None else None
        result.update(status="quote_based_paper_diagnostic", quote_pair_sha256=digest([entry, exit_quote]),
                      strategy_return_pct=strategy, always_cash_return_pct=0.0,
                      always_long_return_pct=long_return, frozen_baseline_return_pct=baseline,
                      excess_over_always_long_pp=strategy - long_return,
                      excess_over_frozen_baseline_pp=strategy - baseline if baseline is not None else None,
                      initial_capital_per_maximum_share=capital, cost_basis=schedule["basis"],
                      slippage_is_assumed=True, actual_execution_return=False,
                      blockers=["external_provider_and_receipt_authentication_unverified",
                                "actual_fill_and_slippage_unverified", "untouched_followup_not_verified"])
    except (KeyError, TypeError, ValueError) as error:
        result.update(status="invalid_or_missing_evidence", blockers=[evidence_error(error)])
    return result


def run(root=Path("."), cutoff=None):
    from audit_stock_forecast_independent import audit
    root = Path(root)
    cutoff = instant(cutoff or datetime.now(timezone.utc))
    records = read_lines(root / "stock-forecast-ledger.jsonl")
    outcomes = read_lines(root / "stock-forecast-outcomes.jsonl")
    deliveries = read_lines(root / "stock-forecast-deliveries.jsonl")
    independent = audit(records, outcomes, deliveries, cutoff)
    if independent["errors"]:
        raise ValueError("independent_audit_rejected_paper_inputs")
    policy = policy_for(read_json(root / POLICY_FILE, None), cutoff)
    existing = read_lines(root / PLAN_FILE)
    schedules = read_json(root / COST_FILE, {})
    additions, skipped = register_plans(records, deliveries, policy, existing, schedules, cutoff)
    plans = existing + additions
    publications = read_lines(root / PUBLICATION_FILE)
    evidence = read_lines(root / EVIDENCE_FILE)
    by_plan = defaultdict(list)
    for row in evidence:
        by_plan[row.get("plan_id")].append(row)
    plan_ids = {plan["id"] for plan in plans}
    unknown = sum(row.get("plan_id") not in plan_ids for row in evidence)
    if any(row.get("plan_id") not in plan_ids for row in publications):
        raise ValueError("paper_publication_for_unknown_plan")
    public_by_plan = {plan["id"]: verified_plan_publication(plan, policy, publications, cutoff) for plan in plans}
    results = [evaluate_plan(plan, by_plan.get(plan["id"], []), cutoff, public_by_plan[plan["id"]]) for plan in plans]
    source_names = ("stock-forecast-ledger.jsonl", "stock-forecast-outcomes.jsonl", "stock-forecast-deliveries.jsonl")
    inputs = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_names}
    evidence_inputs = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                       if (root / name).exists() else None for name in READ_ONLY_INPUTS}
    report = {"version": VERSION, "generated_at": cutoff.isoformat(), "policy_id": policy["id"],
              "source_sha256": inputs, "status": "not_proven", "timing_utility": "not_proven",
              "optional_evidence_sha256": evidence_inputs,
              "paper_publication": {"ledger": PUBLICATION_FILE, "records": len(publications),
                  "ledger_sha256": hashlib.sha256((root / PUBLICATION_FILE).read_bytes() if (root / PUBLICATION_FILE).exists() else b"").hexdigest(),
                  "plans_public_before_target": sum(proof is not None for proof in public_by_plan.values()),
                  "late_checks": sum(row.get("public_before_target_verified") is False for row in publications),
                  "human_receipts_created": 0},
              "registered_plans": len(plans), "new_plans": len(additions),
              "registration_exclusions": skipped, "status_counts": dict(Counter(row["status"] for row in results)),
              "blocker_counts": dict(Counter(reason for row in results for reason in row["blockers"])),
              "unknown_evidence_records": unknown, "results": results,
              "external_quote_adapter_connected": False, "human_receipt_adapter_connected": False,
              "after_cost_forward_edge_verified": False, "untouched_followup_verified": False,
              "automatic_completion_notice": False, "orders_enabled": False, "strict_green_override": False,
              "scope": "Orderless paper arithmetic with supplied quote/receipt evidence; no external authentication or real fills."}
    shadow = compare_frozen(records, independent, cutoff)
    shadow["source_sha256"] = inputs
    # All calculations and immutable checks precede writes. The bounded controller
    # executes this on its private stage before its own all-or-rollback publication.
    if not (root / POLICY_FILE).exists():
        write_json(root / POLICY_FILE, policy)
    if additions or not (root / PLAN_FILE).exists():
        with (root / PLAN_FILE).open("a") as target:
            for row in additions:
                target.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    if not (root / PUBLICATION_FILE).exists():
        (root / PUBLICATION_FILE).write_text("")
    write_json(root / REPORT_FILE, report)
    write_json(root / SHADOW_FILE, shadow)
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({key: result[key] for key in ("status", "registered_plans", "new_plans", "status_counts", "blocker_counts")}, ensure_ascii=False))
