"""Read-only best-effort GitHub schedule observation, not a market-data feed."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import urllib.request

REPO = "Ohoredingdong/Notion"
NAME = "Stock Prospective Forecasts"
WORKFLOW = ".github/workflows/stock-forecasts.yml"
CRONS = ("7,17,27,37,47,57 0-7,13-22 * * 1-5", "47 23 * * 0-4")
UTC = timezone.utc


def utc(s):
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("timezone_required")
    return d.astimezone(UTC)


def field(spec, low, high):
    values = set()
    for item in spec.split(","):
        if "-" in item:
            a, b = map(int, item.split("-"))
            if a > b:
                raise ValueError("reversed_cron_range")
            values.update(range(a, b + 1))
        else:
            values.add(int(item))
    if not values or min(values) < low or max(values) > high:
        raise ValueError("invalid_cron_field")
    return values


def due(dt, cron):
    parts = cron.split()
    if len(parts) != 5 or parts[2:4] != ["*", "*"]:
        raise ValueError("unsupported_cron_syntax")
    return (dt.minute in field(parts[0], 0, 59)
            and dt.hour in field(parts[1], 0, 23)
            and (dt.weekday() + 1) % 7 in field(parts[4], 0, 6))


def expected(start, as_of, grace=30):
    if start.tzinfo is None or as_of.tzinfo is None or as_of < start:
        raise ValueError("invalid_window")
    if not 0 <= grace <= 360:
        raise ValueError("invalid_grace")
    cutoff = as_of - timedelta(minutes=grace)
    cursor = start.replace(second=0, microsecond=0)
    if cursor < start:
        cursor += timedelta(minutes=1)
    found = []
    while cursor <= cutoff:
        if any(due(cursor, cron) for cron in CRONS):
            found.append(cursor.isoformat())
        cursor += timedelta(minutes=1)
    return found


def check_workflow(source):
    crons = tuple(re.findall(r"^\s*-\s*cron:\s*'([^']+)'\s*$", source, re.M))
    if crons != CRONS:
        raise ValueError("workflow_cron_changed_fail_closed")


def audit(runs, start, as_of, *, complete, grace=30):
    due_slots = expected(start, as_of, grace)
    all_visible = [
        (utc(r["created_at"]), r) for r in runs
        if r.get("name") == NAME and r.get("event") == "schedule"
        and utc(r["created_at"]) <= as_of
    ]
    # GitHub timestamps have second precision; equal instants must not cause
    # Python to compare run dictionaries while sorting.
    all_visible.sort(key=lambda pair: pair[0])
    begun = [(t, r) for t, r in all_visible if start <= t <= as_of]
    if not complete:
        status = "history_incomplete"
    elif not due_slots:
        status = "no_due_slots"
    elif len(begun) < len(due_slots):
        status = "unobserved_schedule_coverage"
    else:
        status = "created_run_count_only"
    return {
        "status": status,
        "scope": "github_best_effort_scheduled_start_metadata_only",
        "as_of": as_of.isoformat(), "window_start": start.isoformat(),
        "grace_minutes": grace,
        "due_slots": due_slots, "due_slots_count": len(due_slots),
        "observed_schedule_created_count": len(begun),
        "unattributed_count_gap": max(0, len(due_slots) - len(begun)) if complete else None,
        "latest_created_at": all_visible[-1][0].isoformat() if all_visible else None,
        "conclusions_in_window": dict(Counter(
            str(r.get("conclusion") or r.get("status") or "unknown")
            for _, r in begun)),
        "history_complete": bool(complete),
        "limitations": [
            "GitHub run created_at does not establish original scheduled cron slot",
            "Unobserved scheduled launches may be delayed or dropped; cause unresolved",
            "Missing job is not an issued forecast, a no_call, or an exchange outcome",
            "Successful launch is not timely data receipt, human push or executable quote",
        ],
        "notification_enabled": False, "live_orders_enabled": False,
        "timing_utility_proven": False,
    }


def github_runs(start, max_pages=5):
    rows = []
    for page in range(1, max_pages + 1):
        url = ("https://api.github.com/repos/" + REPO
               + "/actions/runs?event=schedule&per_page=100&page=" + str(page))
        headers = {"Accept": "application/vnd.github+json",
                   "User-Agent": "read-only-stock-schedule-research"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                    timeout=18) as response:
            data = json.load(response)
        batch = data.get("workflow_runs")
        if not isinstance(batch, list):
            raise ValueError("invalid_api_workflow_runs")
        rows.extend(batch)
        if len(batch) < 100 or min(utc(r["created_at"]) for r in batch) <= start:
            return rows, True
    return rows, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--grace", type=int, default=30)
    parser.add_argument("--offline-json")
    parser.add_argument("--output")
    args = parser.parse_args()
    check_workflow(Path(WORKFLOW).read_text())
    start, as_of = utc(args.window_start), utc(args.as_of)
    if args.offline_json:
        record = json.loads(Path(args.offline_json).read_text())
        rows = record.get("workflow_runs", []) if isinstance(record, dict) else record
        complete = isinstance(record, dict) and record.get("history_complete") is True
    else:
        rows, complete = github_runs(start)
    report = audit(rows, start, as_of, complete=complete, grace=args.grace)
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(output)
    print(output)
    return 2 if report["status"] == "history_incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
