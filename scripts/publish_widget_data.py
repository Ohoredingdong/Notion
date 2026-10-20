#!/usr/bin/env python3
"""Publish an explicit JSON snapshot on current main without losing parallel updates.

Collection happens in the Actions checkout. Publication uses a fresh worktree
and a normal fast-forward push, so unrelated widget jobs cannot be overwritten.
"""
import argparse
import json
import random
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def git(root, *args, check=True):
    return subprocess.run(["git", *args], cwd=root, text=True,
                          capture_output=True, check=check)


def revision_bytes(root, revision, name):
    result = subprocess.run(["git", "show", f"{revision}:{name}"], cwd=root,
                            capture_output=True)
    return result.stdout if result.returncode == 0 else None


def snapshot_time(body):
    if body is None:
        return None
    data = json.loads(body)
    if not isinstance(data, dict):
        return None
    for key in ("generated_at", "generatedAt", "updated_at", "updatedAt",
                "checked_at", "checkedAt"):
        value = data.get(key)
        if value:
            try:
                stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if stamp.tzinfo is not None:
                    return stamp.astimezone(timezone.utc)
            except ValueError:
                pass
    value = (data.get("verification") or {}).get("checkedAt")
    if value:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is not None:
            return stamp.astimezone(timezone.utc)
    return None


def publish(root, names, message, attempts=12):
    root = Path(root).resolve()
    payload, baseline = {}, {}
    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".json":
            raise ValueError(f"Expected an explicit relative JSON output: {name}")
        target = root / path
        if target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError(f"Output must be inside the checkout: {name}")
        body = target.read_bytes()
        json.loads(body)  # Refuse to publish incomplete/non-JSON output.
        old = revision_bytes(root, "HEAD", name)
        if body != old:
            payload[name], baseline[name] = body, old
    if not payload:
        print("No generated data changes to publish.")
        return None

    for attempt in range(attempts):
        git(root, "fetch", "origin", "main")
        worktree = Path(tempfile.mkdtemp(prefix="widget-data-publish-"))
        worktree.rmdir()
        git(root, "worktree", "add", "--detach", str(worktree), "origin/main")
        try:
            for name, body in payload.items():
                remote = revision_bytes(worktree, "HEAD", name)
                if remote in (baseline[name], body):
                    continue
                ours, theirs = snapshot_time(body), snapshot_time(remote)
                if ours is None or theirs is None:
                    raise RuntimeError(f"Concurrent change to {name} has no comparable timestamp; preserving main. Rerun collection.")
                if theirs >= ours:
                    print(f"A newer snapshot of {name} is already published; preserving the complete current bundle.")
                    return None
            for name, body in payload.items():
                target = worktree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
            git(worktree, "config", "user.name", "github-actions[bot]")
            git(worktree, "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
            git(worktree, "add", "--", *payload)
            if git(worktree, "diff", "--cached", "--quiet", check=False).returncode == 0:
                print("Snapshot already published.")
                return None
            git(worktree, "commit", "-m", message)
            result = git(worktree, "push", "origin", "HEAD:main", check=False)
            if result.returncode == 0:
                sha = git(worktree, "rev-parse", "HEAD").stdout.strip()
                print(f"Published {len(payload)} data files: {sha}")
                return sha
            print(f"Publication raced another update ({attempt + 1}/{attempts}); retrying on current main.")
            # Do not include remote URLs or credentials from stderr in logs.
        finally:
            git(root, "worktree", "remove", "--force", str(worktree), check=False)
        if attempt + 1 < attempts:
            # A source change can start all twelve widget jobs together. Spread
            # their retries so the last finisher can publish after the burst.
            time.sleep(min(15, 2 * (attempt + 1)) + random.uniform(0, 3))
    raise RuntimeError("Publication could not fast-forward after retries; existing main is preserved.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    publish(Path.cwd(), args.files, args.message)


if __name__ == "__main__":
    main()
