#!/usr/bin/env python3
"""Read-only PR change classifier and data preservation guard.

Runs only as a PR quality check. Does not edit existing repository files or data.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


DATA_SUFFIXES = (".json", ".jsonl", ".db", ".sqlite", ".sqlite3", ".csv", ".parquet")
MEDIA_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".mov", ".pdf")
RADAR_ASSETS = (
    "assets/stock-radar", "assets/stock-forecast",
    "assets/stock-investment", "assets/stock-decision", "assets/stock-green",
)
KNOWN_RADAR_HTML = (
    "stock-value-radar.html", "stock-radar-dashboard.html",
    "stock-value-radar-advanced.html", "stock-forecast.html",
)
UNSAFE_WORKFLOW_ACTIONS = ("git push", "gh api --method POST", "secrets.", "contents: write")


def classify(path: str) -> dict:
    p = Path(path)
    is_data = path.startswith("backups/") or (
        p.suffix.lower() in DATA_SUFFIXES
        and not (path.startswith("tests/fixtures/") or path.startswith("docs/"))
    )
    is_media = p.suffix.lower() in MEDIA_SUFFIXES
    is_ui = (p.suffix.lower() in (".html", ".css", ".js") and
             not path.startswith("scripts/"))
    radar = path in KNOWN_RADAR_HTML or path.startswith(RADAR_ASSETS) or (
        path.startswith(("scripts/", "tests/"))
        and any(token in p.name for token in ("stock", "market_context", "codex_pr", "widget_browser"))
    )
    browser = is_ui or path.startswith((".agents/", "AGENTS.md", "scripts/pr_widget_browser.py"))
    # Newly authored guard/workflow exercises the initial integration demo.
    browser = browser or path in (
        ".github/workflows/codex-pr-safety.yml",
        "scripts/codex_pr_preflight.py",
    )
    return {"data": bool(is_data), "media": bool(is_media),
            "ui": bool(is_ui), "radar": bool(radar), "browser": bool(browser)}


def diff_paths(base_ref: str) -> list[dict]:
    base = subprocess.run(
        ["git", "merge-base", base_ref, "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if not base:
        raise RuntimeError("merge base not found; cannot trust PR diff")
    output = subprocess.run(
        ["git", "diff", "--no-renames", "--name-status", "-z", base, "HEAD"],
        check=True, capture_output=True,
    ).stdout.decode("utf-8")
    items = output.split("\x00")
    results = []
    for idx in range(0, len(items) - 1, 2):
        status, path = items[idx:idx+2]
        if status and path:
            results.append({"status": status, "path": path, **classify(path)})
    return results


def validate(items: list[dict], workflow: Path | None = None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    if not items:
        errors.append("Empty PR diff: no code or documentation changes to verify.")
    for item in items:
        status, path = item["status"], item["path"]
        if status in ("D", "R", "C") or status.startswith(("D", "R")):
            errors.append(f"{path}: deletion/rename prohibited without separate user-approved migration")
        if item["data"]:
            errors.append(f"{path}: production data/backup alteration is not permitted in a code PR")
        if path.startswith(".github/workflows/") and path != ".github/workflows/codex-pr-safety.yml":
            warnings.append(f"{path}: existing production workflow change needs a separate schedule/data review")
        if item["media"] and status == "M":
            warnings.append(f"{path}: check original image/media and visual provenance")
    if workflow is not None:
        if not workflow.is_file():
            errors.append(f"PR read-only workflow not found: {workflow}")
        else:
            s = workflow.read_text(encoding="utf-8")
            if "pull_request:" not in s or "\n  push:" in s or "\n  schedule:" in s or "\n  workflow_run:" in s:
                errors.append("PR workflow must run on pull_request only")
            if "contents: read" not in s:
                errors.append("PR workflow must declare contents: read")
            for unsafe in UNSAFE_WORKFLOW_ACTIONS:
                if unsafe in s:
                    errors.append(f"PR workflow may not use publication privileges: {unsafe}")
    return errors, warnings


def self_test() -> None:
    assert classify("stock-value-radar.html")["radar"]
    assert classify("assets/stock-radar-flow-v2.js")["browser"]
    assert classify(".agents/skills/widget-safe-pr/SKILL.md")["browser"]
    assert classify("stock-opportunity-data.json")["data"]
    assert classify("backups/saved-state.json")["data"]
    assert not classify("docs/codex-development-workflow.md")["data"]
    assert not classify("scripts/test_stock_detail_v6.py")["data"]
    examples = [{"status": "M", "path": "stock-opportunity-data.json",
                 **classify("stock-opportunity-data.json")},
                {"status": "D", "path": "assets/user-photo.png",
                 **classify("assets/user-photo.png")}]
    errors, _ = validate(examples)
    assert len(errors) == 2, errors
    assert not validate([{"status": "A", "path": "AGENTS.md", **classify("AGENTS.md")}])[0]
    print("PASS: read-only PR classifier, data preservation and deletion safeguards")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="merge-base reference, e.g. PR base SHA")
    parser.add_argument("--out", default="codex-pr-artifacts/changed-files.json")
    parser.add_argument("--workflow", default=".github/workflows/codex-pr-safety.yml")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.base:
        parser.error("--base is required unless --self-test is set")
    changes = diff_paths(args.base)
    errors, warnings = validate(changes, Path(args.workflow))
    output = {
        "reference": args.base, "changes": changes, "errors": errors,
        "warnings": warnings,
        "stock_checks": any(x["radar"] for x in changes),
        "browser_checks": any(x["browser"] for x in changes),
        "widget_pages": [x["path"] for x in changes
                         if x["path"].endswith(".html") and x["status"] != "D"],
    }
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as file:
            file.write("stock=" + str(output["stock_checks"]).lower() + "\n")
            file.write("browser=" + str(output["browser_checks"]).lower() + "\n")
    print("Changed:", ", ".join(x["status"] + " " + x["path"] for x in changes))
    for message in warnings:
        print("WARNING:", message)
    for message in errors:
        print("ERROR:", message, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
