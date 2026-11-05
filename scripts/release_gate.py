#!/usr/bin/env python3
"""Fail-closed, opt-in Pages release checks. Never changes GitHub or Git settings.

This complements, but does not replace, the currently active Pages deployment.
Its disabled policy and legacy-Pages refusal require a separately approved
migration before an operator can use the manual production job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


class ReleaseDenied(ValueError):
    """Evidence or authorization is insufficient to publish."""


def require(condition, message):
    if not condition:
        raise ReleaseDenied(message)


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None,
            "Candidate and observed commit IDs must be full lowercase 40-character Git SHAs")
    return value


def safe_path(value):
    require(isinstance(value, str) and value and "\\" not in value and "\0" not in value,
            "Invalid artifact path")
    parts = value.split("/")
    require(not PurePosixPath(value).is_absolute() and all(p not in {"", ".", ".."} for p in parts),
            f"Unsafe artifact path: {value!r}")
    require(all(not p.startswith(".") for p in parts) or value == ".nojekyll",
            f"Hidden artifact path is not public: {value!r}")
    return value


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    require(result.returncode == 0, result.stderr.decode(errors="replace").strip() or "Git command failed")
    return result.stdout


def digest(content):
    return hashlib.sha256(content).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_policy(path):
    policy = read_json(path)
    require(policy.get("version") == 1 and isinstance(policy.get("enabled"), bool), "Invalid release policy")
    require(policy.get("default_branch") == "main", "This gate supports only the existing main branch")
    require(policy.get("required_pages_build_type") == "workflow", "Pages must use the workflow build type")
    for key in ("public_root_files", "asset_extensions"):
        require(isinstance(policy.get(key), list) and policy[key] and all(isinstance(p, str) for p in policy[key]),
                f"Missing explicit public allowlist: {key}")
    for name in policy["public_root_files"]:
        require("/" not in safe_path(name), "Root allowlist cannot include directories")
    require(all(re.fullmatch(r"\.[a-z0-9]+", extension) for extension in policy["asset_extensions"]),
            "Asset extensions must be literal lowercase suffixes")
    return policy


def check_candidate(candidate, main_sha, checkout_sha=None):
    candidate = sha(candidate)
    require(candidate == sha(main_sha), "Main advanced or candidate is not main HEAD; validate the latest commit again")
    if checkout_sha is not None:
        require(candidate == sha(checkout_sha), "Checked-out commit does not match the requested candidate")
    return candidate


def is_public(path, policy):
    safe_path(path)
    if "/" not in path:
        return path in policy["public_root_files"]
    return path.startswith("assets/") and PurePosixPath(path).suffix.lower() in policy["asset_extensions"]


def tree(root, candidate):
    entries = {}
    for record in git(root, "ls-tree", "-r", "-z", "--full-tree", sha(candidate)).split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8", errors="strict")
        # Hidden/private source paths need not be published, but traversal is
        # rejected even if a malicious tree entry would otherwise be excluded.
        require(not PurePosixPath(path).is_absolute() and ".." not in path.split("/") and "\\" not in path,
                "Unsafe Git tree path")
        entries[path] = (mode, kind, oid)
    return entries


def public_blobs(root, candidate, policy):
    blobs = {}
    for path, (mode, kind, oid) in tree(root, candidate).items():
        # Ordinary repository metadata is excluded without asking safe_path to
        # regard it as a public path.
        if any(part.startswith(".") for part in path.split("/")) and path != ".nojekyll":
            continue
        if not is_public(path, policy):
            continue
        require(kind == "blob" and mode in {"100644", "100755"}, f"Public symlinks/submodules are forbidden: {path}")
        blobs[path] = git(root, "cat-file", "blob", oid)
    require(blobs and any(name.endswith(".html") for name in blobs), "Public artifact has no HTML pages")
    return blobs


def validate_evidence(root, candidate, validation, browser, radar):
    require(validation.get("head") == candidate and validation.get("base") ==
            git(root, "rev-parse", candidate + "^").decode().strip(), "Change checks did not validate candidate against its parent")
    require(validation.get("scope") == "commit_diff" and validation.get("status") == "passed",
            "Change checks must be an executed, successful commit diff")
    checks = validation.get("selected", [])
    require(checks and all(check.get("status") == "passed" for check in checks) and not validation.get("uncovered"),
            "Change checks are empty, incomplete, failed or uncovered")
    mandatory = {"radar-browser", "radar-publish-protection", "radar-evidence-review", "radar-forecast-wiring", "event-ui"}
    require(radar.get("head") == candidate and radar.get("status") == "passed" and
            radar.get("scope") == "explicit_files" and not radar.get("uncovered"),
            "Mandatory radar checks did not validate the exact candidate")
    radar_checks = radar.get("selected", [])
    require(mandatory <= {check.get("id") for check in radar_checks} and
            all(check.get("status") == "passed" for check in radar_checks),
            "Mandatory radar checks are missing or failed")
    require(browser.get("suite") == "canonical-investment-radar" and browser.get("passed") is True,
            "Canonical investment radar browser checks did not pass")
    checks = browser.get("checks", [])
    require(checks and all(check.get("pass") is True for check in checks) and browser.get("checks_failed") == 0,
            "Browser checks are empty or contain failures")
    before, after = browser.get("source_sha256_before"), browser.get("source_sha256_after")
    require(isinstance(before, dict) and before and before == after,
            "Browser evidence does not prove source/data preservation")
    require({"stock-value-radar.html", "stock-radar-dashboard.html", "stock-opportunity-data.json"} <= before.keys(),
            "Browser evidence is missing canonical radar sources")
    for path, fingerprint in before.items():
        safe_path(path)
        require(digest(git(root, "show", candidate + ":" + path)) == fingerprint,
                f"Browser evidence belongs to different content: {path}")


def package(root, candidate, policy, site, manifest, validation_report, browser_report, radar_report):
    sha(candidate)
    require(git(root, "rev-parse", "HEAD").decode().strip() == candidate, "Packaging must run at the tested candidate")
    require(not git(root, "status", "--porcelain", "--untracked-files=no"), "Tracked checkout changed during validation")
    validate_evidence(root, candidate, read_json(validation_report), read_json(browser_report), read_json(radar_report))
    root, site, manifest = Path(root).resolve(), Path(site).resolve(), Path(manifest).resolve()
    require(not site.is_relative_to(root) and not manifest.is_relative_to(root), "Build outputs must be outside the checkout")
    require(not manifest.is_relative_to(site), "Provenance must remain outside the public site")
    require(not site.exists() or site.is_dir() and not any(site.iterdir()), "Refusing to overwrite a nonempty site output")
    blobs = public_blobs(root, candidate, policy)
    site.mkdir(parents=True, exist_ok=True)
    records = []
    for path, content in sorted(blobs.items()):
        target = site / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        records.append({"path": path, "sha256": digest(content), "size": len(content)})
    evidence = {"version": 1, "candidate_sha": candidate, "tested_sha": candidate,
                "validation_report_sha256": digest(Path(validation_report).read_bytes()),
                "browser_report_sha256": digest(Path(browser_report).read_bytes()),
                "radar_report_sha256": digest(Path(radar_report).read_bytes()), "files": records}
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


def verify_artifact(root, candidate, policy, site, manifest, validation_report, browser_report, radar_report):
    evidence = read_json(manifest)
    require(evidence.get("version") == 1 and evidence.get("candidate_sha") == candidate and
            evidence.get("tested_sha") == candidate, "Artifact candidate/tested SHA mismatch")
    for key, path in (("validation_report_sha256", validation_report), ("browser_report_sha256", browser_report),
                      ("radar_report_sha256", radar_report)):
        require(evidence.get(key) == digest(Path(path).read_bytes()), "Validation evidence was modified after packaging")
    validate_evidence(root, candidate, read_json(validation_report), read_json(browser_report), read_json(radar_report))
    expected = public_blobs(root, candidate, policy)
    records = evidence.get("files", [])
    require(isinstance(records, list), "Invalid artifact manifest")
    indexed = {safe_path(record["path"]): record for record in records}
    require(len(indexed) == len(records) and set(indexed) == set(expected), "Artifact manifest does not match public candidate tree")
    site = Path(site).resolve()
    actual = set()
    for path in site.rglob("*"):
        require(not path.is_symlink(), "Artifact contains a symlink")
        if path.is_file():
            actual.add(safe_path(path.relative_to(site).as_posix()))
    require(actual == set(expected), "Artifact has extra or missing files")
    for path, content in expected.items():
        require((site / path).read_bytes() == content and indexed[path] ==
                {"path": path, "sha256": digest(content), "size": len(content)},
                f"Artifact differs from tested candidate: {path}")
    return evidence


def authorize(policy, candidate, main_sha, confirmation, dry_run, pages_config, evidence):
    check_candidate(candidate, main_sha)
    require(policy.get("enabled") is True, "Manual production releases are disabled by policy; approval is required before enabling")
    require(dry_run is False, "Dry run: deployment is not authorized")
    require(confirmation == "DEPLOY " + candidate, "Explicit confirmation must exactly equal DEPLOY <candidate SHA>")
    require(pages_config.get("build_type") == "workflow",
            "Existing Pages is not workflow-based; a separately approved Pages settings migration is required")
    require(evidence.get("candidate_sha") == candidate and evidence.get("tested_sha") == candidate,
            "Only the exact tested and packaged commit may deploy")
    return {"authorized": True, "candidate_sha": candidate}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Support the machine-friendly historical flag spelling without relying on
    # argparse treating an option-looking token as a subcommand.
    if argv and argv[0] == "--check":
        argv[0] = "check"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--policy", type=Path, help="Default: <root>/.github/release-policy.json")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--candidate", required=True)
    check.add_argument("--main-sha", required=True)
    check.add_argument("--checkout-sha")
    for name in ("package", "verify", "authorize"):
        command = sub.add_parser(name)
        command.add_argument("--candidate", required=True)
        command.add_argument("--site", type=Path, required=True)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--validation-report", type=Path, required=True)
        command.add_argument("--browser-report", type=Path, required=True)
        command.add_argument("--radar-report", type=Path, required=True)
        if name == "authorize":
            command.add_argument("--main-sha", required=True)
            command.add_argument("--pages-config", type=Path, required=True)
            command.add_argument("--confirm", required=True)
            command.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.policy or args.root / ".github/release-policy.json")
        if args.command == "check":
            result = {"candidate_sha": check_candidate(args.candidate, args.main_sha, args.checkout_sha)}
        elif args.command == "package":
            result = package(args.root, args.candidate, policy, args.site, args.manifest,
                             args.validation_report, args.browser_report, args.radar_report)
            result = {"candidate_sha": result["candidate_sha"], "public_files": len(result["files"])}
        else:
            result = verify_artifact(args.root, args.candidate, policy, args.site, args.manifest,
                                     args.validation_report, args.browser_report, args.radar_report)
            if args.command == "authorize":
                result = authorize(policy, args.candidate, args.main_sha, args.confirm, args.dry_run,
                                   read_json(args.pages_config), result)
            else:
                result = {"verified": True, "candidate_sha": args.candidate}
        print(json.dumps(result))
        return 0
    except (ReleaseDenied, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"denied": True, "reason": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
