"""Independent consistency and evidence gate for the Stock Radar research dashboard.

Checks immutable source counts and publishes an audit; it does NOT train models,
issue buy recommendations, infer executions, or alter saved forecasts.
Run: python scripts/audit_stock_radar_accuracy.py
     python scripts/audit_stock_radar_accuracy.py --check
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "stock-radar-accuracy-audit.json"


def read(name: str, root=ROOT):
    path = Path(root) / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def lines(name: str, root=ROOT):
    with (Path(root) / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def date_utc(value):
    try:
        if not value:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def fail_if(condition, message, errors):
    if condition:
        errors.append(message)


def report(root=ROOT, now=None):
    learning = read("stock-forecast-learning.json", root)
    forecasts = read("stock-direction-forecast.json", root)
    market = read("stock-market-context.json", root)
    chart = read("stock-radar-chart-data.json", root)
    opportunity = read("stock-opportunity-summary.json", root)
    cases = read("stock-investment-cases-summary.json", root)
    entry = read("stock-entry-plan-summary.json", root)
    observed = lines("stock-forecast-outcomes.jsonl", root)

    errors = []
    warnings = []
    fail_if(not learning.get("generated_at") or learning.get("generated_at") != forecasts.get("generated_at"),
            "Forecast and learning snapshots have different source timestamps", errors)
    overall = learning["overall"]
    policy = learning["policy"]
    n = int(overall["samples"])
    correct = int(overall["correct"])
    acc = number(overall.get("accuracy"))
    cm = overall["confusion_matrix"]
    classes = ("down", "flat", "up")
    totals = [sum(row) for row in cm]
    recalls = {k: cm[i][i] / totals[i] if totals[i] else None for i, k in enumerate(classes)}

    fail_if(not isinstance(cm, list) or len(cm) != 3 or any(len(r) != 3 for r in cm), "Confusion matrix should be 3x3", errors)
    fail_if(sum(totals) != n, "Confusion matrix total differs from scored sample size", errors)
    fail_if(sum(cm[i][i] for i in range(3)) != correct, "Confusion matrix diagonal differs from correct count", errors)
    fail_if(not (0 <= correct <= n), "Scored correct count outside valid range", errors)
    fail_if(acc is None or abs(acc - correct / n) > 1e-7, "Published overall accuracy does not equal correct/samples", errors)
    for k, v in recalls.items():
        published = number(overall.get("recall", {}).get(k))
        fail_if((v is None) != (published is None) or (v is not None and abs(v-published) > 1e-7),
                "Incorrect recall value for " + k, errors)
    balanced = sum(v for v in recalls.values() if v is not None) / 3
    fail_if(abs(balanced - overall["balanced_accuracy"]) > 1e-7,
            "Published balanced accuracy inconsistent with confusion matrix", errors)

    unique_ids = {row.get("id") for row in observed}
    fail_if(len(unique_ids) != len(observed), "Duplicate outcome IDs in raw observed ledger", errors)
    fail_if(any(row.get("status") != "observed" for row in observed),
            "Outcome file includes unobserved rows", errors)
    raw_correct = sum(row.get("correct") is True for row in observed)
    raw_public = sum(row.get("public_before_target_verified") is True for row in observed)

    paired = learning["baseline_paired"]
    paired_m = paired["model"]
    paired_b = paired["baseline"]
    paired_n = paired["samples"]
    fail_if(paired_n != paired_m["samples"] or paired_n != paired_b["samples"],
            "Paired model and baseline use different sample counts", errors)
    fail_if(paired_m["accuracy"] != paired_m["correct"] / paired_n, "Paired model accuracy mismatch", errors)
    fail_if(paired_b["accuracy"] != paired_b["correct"] / paired_n, "Paired baseline accuracy mismatch", errors)
    brier_gain = paired_b["brier_loss"]-paired_m["brier_loss"]
    log_loss_gain = paired_b["log_loss"]-paired_m["log_loss"]
    brier_threshold = float(policy["minimum_brier_gain"])
    loss_threshold = float(policy["minimum_logloss_gain"])
    min_samples = int(policy["minimum_paired_targets"])
    min_days = int(policy["minimum_sessions"])
    days = int(overall.get("calendar_days", 0))
    minimum_coverage_met = n >= min_samples and days >= min_days
    performance_promotion_met = minimum_coverage_met and paired_n >= min_samples and brier_gain >= brier_threshold and log_loss_gain >= loss_threshold
    live_proven = learning.get("live_profitability_proven") is True

    if not minimum_coverage_met:
        warnings.append("Insufficient independent observations and/or sessions for promotion")
    if brier_gain < brier_threshold:
        warnings.append("Paired Brier gain below configured policy threshold")
    if not live_proven:
        warnings.append("No independently proven live trading profitability")
    if recalls["up"] is not None and recalls["up"] < 0.10:
        warnings.append("Upward-direction recall under 10%; not a trading signal")

    forecast_issues = []
    statuses = {}
    now = now or datetime.now(timezone.utc)
    for pred in forecasts.get("records", []):
        st = pred.get("status", "missing")
        statuses[st] = statuses.get(st, 0)+1
        if st != "research_prediction":
            continue
        prob = pred.get("probabilities") or {}
        values = [number(prob.get(k)) for k in classes]
        issued = date_utc(pred.get("issued_at"))
        target = date_utc((pred.get("target") or {}).get("end"))
        if (not all(v is not None and 0 <= v <= 1 for v in values)
                or abs(sum(v or 0 for v in values) - 1) > .025
                or pred.get("direction") not in classes
                or issued is None or target is None or target <= issued
                or issued > now):
            forecast_issues.append({"symbol": pred.get("symbol"), "mode": pred.get("mode"), "status": "invalid research record"})
    fail_if(bool(forecast_issues), "Published research forecast contains invalid probabilities or dates", errors)

    chart_series_issues = []
    chart_ok = 0
    for symbol, series in (chart.get("series") or {}).items():
        bars = series.get("bars") or []
        prev = None
        if series.get("status") == "ok":
            chart_ok += 1
        if not bars:
            chart_series_issues.append({"symbol": symbol, "issue": "missing bars"})
            continue
        for row in bars:
            if not isinstance(row, dict) or not isinstance(row.get("date"), str):
                chart_series_issues.append({"symbol": symbol, "issue": "invalid daily bar"})
                break
            value = number(row.get("close"))
            if value is None or value <= 0:
                chart_series_issues.append({"symbol": symbol, "issue": "nonpositive or missing close"})
                break
            if prev is not None and row["date"] <= prev:
                chart_series_issues.append({"symbol": symbol, "issue": "duplicate or unordered date"})
                break
            volume = number(row.get("volume"))
            if volume is not None and volume < 0:
                chart_series_issues.append({"symbol": symbol, "issue": "negative volume"})
                break
            prev = row["date"]
        if series.get("price_session") != bars[-1].get("date"):
            chart_series_issues.append({"symbol": symbol, "issue": "price session and daily bar endpoint differ"})
    fail_if(bool(chart_series_issues), "Invalid stored daily price series", errors)

    chart_differences = []
    for key, title, symbol in [
        ("kospi", "KOSPI", "^KS11"), ("kosdaq", "KOSDAQ", "^KQ11"),
        ("nasdaq", "NASDAQ", "^IXIC"), ("sp500", "S&P 500", "^GSPC")
    ]:
        history = chart.get("series", {}).get(symbol) or {}
        hbars = history.get("bars") or []
        history_date = (hbars[-1].get("date") if hbars else None)
        m = (market.get("indicators") or {}).get(key) or {}
        market_date = m.get("date")
        if market_date != history_date:
            chart_differences.append({
                "market": title, "index_snapshot": market_date, "chart_history_through": history_date,
                "policy": "display dates separately; do not claim history chart is current",
            })
    if chart_differences:
        warnings.append("Market index snapshots have dates different from sparkline histories")

    strict_count = (cases.get("counts") or {}).get("attractive")
    approved_papers = (entry.get("counts") or {}).get("paper_candidate")
    live_count = entry.get("live_recommendations")
    fail_if(strict_count is None or approved_papers is None, "Missing strict diligence or paper-candidate counts", errors)

    result = {
        "version": "radar-accuracy-audit-v1",
        "source": {
            "learning_generated_at": learning.get("generated_at"),
            "forecasts_generated_at": forecasts.get("generated_at"),
            "opportunity_generated_at": opportunity.get("generated_at"),
            "market_generated_at": market.get("generated_at"),
            "chart_generated_at": chart.get("generated_at"),
            "chart_source_generated_at": chart.get("source_generated_at"),
            "cases_generated_at": cases.get("generated_at"),
            "entry_generated_at": entry.get("generated_at"),
        },
        "evaluation": {
            "status": learning.get("status"),
            "samples": n, "correct": correct, "accuracy": acc,
            "independent_calendar_days": days,
            "confidence_interval_95_wilson": overall.get("wilson_95_interval"),
            "balanced_accuracy": overall.get("balanced_accuracy"),
            "recall": recalls,
            "actual_class_counts": dict(zip(classes, totals)),
            "confusion_matrix": cm,
            "calibration_error": overall.get("calibration_error"),
            "brier_loss": overall.get("brier_loss"),
            "log_loss": overall.get("log_loss"),
        },
        "raw_ledger": {
            "observed_events": len(observed),
            "public_before_target_verified": raw_public,
            "observed_correct": raw_correct,
            "raw_observed_accuracy_not_independent": raw_correct/len(observed) if observed else None,
            "note": "Raw ledger includes overlaps not present in the independent scored evaluation.",
        },
        "paired_baseline": {
            "samples": paired_n,
            "model_correct": paired_m["correct"],
            "baseline_correct": paired_b["correct"],
            "model_accuracy": paired_m["accuracy"],
            "baseline_accuracy": paired_b["accuracy"],
            "difference_percentage_points": 100*(paired_m["accuracy"]-paired_b["accuracy"]),
            "brier_improvement": brier_gain,
            "minimum_brier_improvement": brier_threshold,
            "log_loss_improvement": log_loss_gain,
            "minimum_log_loss_improvement": loss_threshold,
            "paired_baseline_comparison_is_not_proof": True,
        },
        "promotion_gates": {
            "required_scored_samples": min_samples,
            "required_calendar_days": min_days,
            "observed_sample_requirement_met": n >= min_samples,
            "observed_days_requirement_met": days >= min_days,
            "paired_brier_improvement_met": brier_gain >= brier_threshold,
            "paired_log_loss_improvement_met": log_loss_gain >= loss_threshold,
            "promotion_evidence_sufficient": performance_promotion_met,
            "live_profitability_proven": live_proven,
            "investment_use_approved": False,
        },
        "investment": {
            "opportunity_tracked": (opportunity.get("counts") or {}).get("tracked"),
            "strict_diligence_approved": strict_count,
            "paper_candidates": approved_papers,
            "live_recommendations": live_count,
            "automatic_orders": False,
        },
        "forecast_records": {
            "status_counts": statuses,
            "invalid_research_records": forecast_issues,
            "no_real_time_connection": forecasts.get("real_time_connected") is not True,
        },
        "chart_integrity": {
            "series_checked": len(chart.get("series") or {}),
            "provider_status_ok": chart_ok,
            "invalid_series": chart_series_issues,
            "date_order_and_price_values_valid": not chart_series_issues,
            "note": "Consistent provider daily bars do not independently verify the exchange feed or current quote.",
        },
        "index_date_mismatch": chart_differences,
        "data_integrity": {
            "check_passed": not errors,
            "errors": errors,
            "warnings": warnings,
            "note": "Passing data consistency checks never establishes predictive accuracy or investment suitability.",
        },
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate without editing the report")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = report(args.root)
    if not result["data_integrity"]["check_passed"]:
        raise SystemExit("Accuracy audit failed: " + "; ".join(result["data_integrity"]["errors"]))
    wire = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if not args.check:
        dest = args.root / DEST.name
        if not dest.exists() or dest.read_text(encoding="utf-8") != wire:
            dest.write_text(wire, encoding="utf-8")
            print("Updated", dest.name)
        else:
            print("Audit report unchanged")
    summary = {
        "data_consistency": "passed",
        "scored": result["evaluation"]["samples"],
        "accuracy": result["evaluation"]["accuracy"],
        "up_recall": result["evaluation"]["recall"]["up"],
        "performance_approved": result["promotion_gates"]["promotion_evidence_sufficient"],
        "live_trading_proven": result["promotion_gates"]["live_profitability_proven"],
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

