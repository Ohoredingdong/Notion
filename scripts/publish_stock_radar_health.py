"""Inspect latest main on every publication attempt; publish only that health report.

A timestamp from an old checkout cannot authorize a newer heartbeat. The
private worktree, inspected input hashes and ordinary fast-forward push bind
the report and its previous-health counter to one immutable source snapshot.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from publish_widget_data import git, revision_bytes


OUTPUT = "stock-radar-health.json"
MONITOR = "scripts/monitor-stock-value-radar.py"
PUBLISHER_CODE = ("scripts/publish_stock_radar_health.py", "scripts/publish_widget_data.py")
CONTROL_INPUTS = ("stock-value-radar.html", MONITOR, "scripts/market_data_utils.py", *PUBLISHER_CODE)


def sha256(body):
    return hashlib.sha256(body).hexdigest() if body is not None else None


def run_monitor(work):
    # Execute the latest worktree's policy and calendar helper, not code or a
    # precomputed report left in the initiating job's possibly old checkout.
    subprocess.run([sys.executable, MONITOR], cwd=work, check=True,
                   text=True, capture_output=True, timeout=90)


def inspect_snapshot(work, base):
    previous = revision_bytes(work, base, OUTPUT)
    run_monitor(work)
    wire = (work / OUTPUT).read_bytes()
    if wire == previous:
        raise RuntimeError("health_inspection_did_not_refresh_report; no stale report published")
    report = json.loads(wire)
    names = report.get("monitored_files")
    if report.get("version") != "canonical-radar-health-v2" or not isinstance(names, dict) or not names:
        raise RuntimeError("health_report_missing_canonical_input_manifest")
    inputs = {}
    for name in sorted(set(names.values()) | set(CONTROL_INPUTS)):
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or name == OUTPUT:
            raise RuntimeError("invalid_health_input_path")
        recorded = revision_bytes(work, base, name)
        current = (work / path).read_bytes() if (work / path).exists() else None
        if current != recorded:
            raise RuntimeError("health_input_changed_during_inspection: " + name)
        # Missing input and invalid JSON remain distinguishable. Both may
        # legitimately produce an error report that must still be published.
        inputs[name] = {"exists": recorded is not None, "sha256": sha256(recorded)}
    report["source_snapshot"] = {
        "commit": base,
        "inputs": inputs,
        "previous_health_sha256": sha256(previous),
    }
    return json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def publish(root=Path("."), attempts=6):
    root = Path(root).resolve()
    for attempt in range(attempts):
        git(root, "fetch", "origin", "main")
        with tempfile.TemporaryDirectory(prefix="radar-health-publish-") as temporary:
            work = Path(temporary) / "work"
            git(root, "worktree", "add", "--detach", str(work), "origin/main")
            try:
                base = git(work, "rev-parse", "HEAD").stdout.strip()
                for name in PUBLISHER_CODE:
                    if (root / name).read_bytes() != revision_bytes(work, base, name):
                        raise RuntimeError("health_publisher_code_changed; rerun from latest main")
                wire = inspect_snapshot(work, base)
                (work / OUTPUT).write_text(wire, encoding="utf-8")
                git(work, "add", "--", OUTPUT)
                if git(work, "diff", "--cached", "--quiet", check=False).returncode == 0:
                    raise RuntimeError("health_publication_unchanged; no fresh report confirmed")
                git(work, "config", "user.name", "github-actions[bot]")
                git(work, "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
                git(work, "commit", "-m", "ops: publish health inspected against current main inputs")
                if git(work, "push", "origin", "HEAD:main", check=False).returncode == 0:
                    commit = git(work, "rev-parse", "HEAD").stdout.strip()
                    # Alerting and final job status consume exactly the report
                    # that was successfully published, never the old checkout.
                    (root / OUTPUT).write_text(wire, encoding="utf-8")
                    report = json.loads(wire)
                    print(json.dumps({"published_commit": commit, "source_commit": base,
                                      "status": report["status"], "issues": report["issues"]}, ensure_ascii=False))
                    return commit
            finally:
                git(root, "worktree", "remove", "--force", str(work), check=False)
        if attempt + 1 < attempts:
            time.sleep(min(10, attempt + 1))
    raise RuntimeError("health_publication_race; latest main and local alert report preserved")


if __name__ == "__main__":
    publish()
