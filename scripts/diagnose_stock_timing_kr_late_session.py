"""Bounded, read-only diagnostic of frozen KR intraday matured-outcome gaps.

No outcome insertion, model change, price export or exchange-authentication claim.
A current Yahoo 5m snapshot is not proof of the original historical provider feed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

TARGETS = ("^KS11", "^KQ11", "005930.KS", "000660.KS", "035420.KS", "403870.KQ")
PINNED_CUTOFF = "2026-11-03T13:25:16+00:00"
TARGET_UTC_STARTS = ("2026-10-30T05:45:00+00:00", "2026-11-02T06:00:00+00:00")
POSITIVE_CONTROL = "2026-11-02T03:00:00+00:00"


def instant(value):
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("missing_timezone")
    return t.astimezone(timezone.utc)


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def first_issue_nonoverlapping(ledger):
    first = {}
    for row in ledger:
        key = (row["symbol"], row["market"], row["mode"], row["target"]["start"], row["target"]["end"])
        if key not in first or instant(row["issued_at"]) < instant(first[key]["issued_at"]):
            first[key] = row
    last = {}
    selected = []
    overlap = 0
    for row in sorted(first.values(), key=lambda r: (
        r["symbol"], r["market"], r["mode"], instant(r["target"]["start"]), instant(r["issued_at"]))):
        group = (row["symbol"], row["market"], row["mode"])
        begin, end = instant(row["target"]["start"]), instant(row["target"]["end"])
        if group in last and begin < last[group]:
            overlap += 1
            continue
        last[group] = end
        selected.append(row)
    return selected, len(ledger) - len(first), overlap


def missing_matured(ledger, outcomes, deliveries, cutoff):
    selected, duplicates, overlaps = first_issue_nonoverlapping(ledger)
    saved_outcomes = {row["id"] for row in outcomes if row.get("status") == "observed"}
    by_id = {r["id"]: r for r in ledger}
    public = {}
    for proof in deliveries:
        if proof.get("status") != "public_verified":
            continue
        snapshot, verified = instant(proof["snapshot_generated_at"]), instant(proof["verified_at"])
        if verified < snapshot or verified > cutoff:
            continue
        for pid in proof.get("prediction_ids", []):
            prediction = by_id.get(pid)
            if prediction is None or instant(prediction["issued_at"]) > snapshot:
                continue
            if pid not in public or verified < public[pid]:
                public[pid] = verified
    missing, pending, untimely, scored = [], 0, 0, 0
    for r in selected:
        begin, end = instant(r["target"]["start"]), instant(r["target"]["end"])
        if end > cutoff:
            pending += 1
            continue
        seen = public.get(r["id"])
        if seen is None or not instant(r["issued_at"]) <= seen < begin:
            untimely += 1
            continue
        if r["id"] not in saved_outcomes:
            missing.append(r)
        else:
            scored += 1
    return {"missing": missing, "pending": pending, "untimely": untimely,
            "scored": scored, "duplicates": duplicates, "overlaps": overlaps,
            "independent": len(selected)}


def expected_five_minute_starts(target):
    start, end = instant(target["start"]), instant(target["end"])
    if end - start != timedelta(minutes=30):
        raise ValueError("not_a_30_minute_target")
    return [start + timedelta(minutes=5*i) for i in range(6)]


def gap_classification(target, raw_starts, normalized_starts):
    expected = expected_five_minute_starts(target)
    raw, clean = set(raw_starts), set(normalized_starts)
    missing_raw = [x.isoformat() for x in expected if x not in raw]
    missing_regular = [x.isoformat() for x in expected if x not in clean]
    if missing_raw:
        status = "source_snapshot_missing_five_minute_timestamp"
    elif missing_regular:
        status = "regular_session_or_ohlc_filter_excluded_timestamp"
    else:
        status = "complete_in_new_snapshot_but_outcome_still_unstored"
    return {"status": status, "expected_bars": 6,
            "raw_present": 6-len(missing_raw), "regular_present": 6-len(missing_regular),
            "missing_raw_utc": missing_raw, "missing_regular_utc": missing_regular}


def report(ledger, outcomes, deliveries, cutoff, probe):
    evidence = missing_matured(ledger, outcomes, deliveries, cutoff)
    cohort = Counter(r["target"]["start"] for r in evidence["missing"])
    scoped = [r for r in evidence["missing"]
              if r["market"] == "KR" and r["mode"] == "intraday"
              and r["symbol"] in TARGETS
              and r["target"]["start"] in TARGET_UTC_STARTS]
    if len(scoped) != 12 or len(evidence["missing"]) != 12 or evidence["scored"] != 72:
        raise ValueError("frozen_cohort_no_longer_matches_preregistered_snapshot")
    if set(cohort) != set(TARGET_UTC_STARTS) or any(cohort[k] != 6 for k in TARGET_UTC_STARTS):
        raise ValueError("frozen_cohort_counts_mismatch")

    controls = Counter((r["symbol"] for r in ledger if r.get("mode") == "intraday"
                        and r.get("market") == "KR" and r.get("target", {}).get("start") == POSITIVE_CONTROL))
    positives = sum(1 for r in ledger
                    if r.get("mode") == "intraday" and r.get("market") == "KR"
                    and r.get("target", {}).get("start") == POSITIVE_CONTROL
                    and any(o["id"] == r["id"] for o in outcomes))
    if positives != 6:
        raise ValueError("prior_scored_control_missing")

    checked = sorted(scoped, key=lambda r: (r["target"]["start"], r["symbol"]))
    results = []
    if probe:
        from stock_forecast_sources import history
        from stock_forecast_model import normalise_history
        for symbol in TARGETS:  # one bounded source request per symbol
            rows = [r for r in checked if r["symbol"] == symbol]
            observed_now = datetime.now(timezone.utc)
            try:
                raw = history(symbol, "intraday")
                cleaned = normalise_history(raw, "KR", "intraday", observed_now)
                raw_times = [instant(t.to_pydatetime()) for t in raw.index]
                clean_times = [instant(t.to_pydatetime()) for t in cleaned["start"]]
                for r in rows:
                    result = gap_classification(r["target"], raw_times, clean_times)
                    results.append({"symbol": symbol, "target": r["target"],
                                    "observed_now": observed_now.isoformat(), **result})
            except Exception as exc:
                # Do not log provider exception strings (may contain URLs or credentials).
                for r in rows:
                    results.append({"symbol": symbol, "target": r["target"],
                                    "observed_now": observed_now.isoformat(),
                                    "status": "source_unavailable",
                                    "exception_type": type(exc).__name__,
                                    "missing_raw_utc": None, "missing_regular_utc": None})
    return {
        "status": "read_only_research_diagnostic",
        "cutoff": cutoff.isoformat(),
        "evidence": {k: v for k, v in evidence.items() if k != "missing"},
        "matured_missing_count": len(evidence["missing"]),
        "missing_cohorts": dict(sorted(cohort.items())),
        "existing_20261030_cohort_is_prior_work": True,
        "new_20261102_cohort_positive_scored_control_count": positives,
        "probe": "single_provider_5m_now_not_original_vintage" if probe else "not_requested",
        "source_diagnostics": results,
        "source_is_official_exchange": False,
        "independent_executable_quotes": False,
        "human_receipt": False,
        "new_outcomes_written": 0,
        "model_or_acceptance_changed": False,
        "timing_utility": "not_proven",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default=PINNED_CUTOFF)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--output", default="stock-timing-kr-late-session-source-research.json")
    args = ap.parse_args()
    result = report(
        read_jsonl("stock-forecast-ledger.jsonl"),
        read_jsonl("stock-forecast-outcomes.jsonl"),
        read_jsonl("stock-forecast-deliveries.jsonl"),
        instant(args.cutoff), args.probe)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "matured_missing": result["matured_missing_count"],
                      "cohorts": result["missing_cohorts"],
                      "source_statuses": dict(Counter(x["status"] for x in result["source_diagnostics"])),
                      "scope": result["probe"], "new_outcomes_written": 0}))


if __name__ == "__main__":
    main()
