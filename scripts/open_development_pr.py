#!/usr/bin/env python3
"""Open or reuse a draft PR only for the exact pushed, fully checked clean HEAD.

This helper does not push, merge, deploy, log in, modify protection rules, or
route blocked GitHub API requests through another service. API uncertainty is
reported as blocked; it is never treated as proof that no PR exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

try:
    from scripts import prepare_release as release
except ImportError:
    import prepare_release as release


SCHEMA_VERSION = 1
DEFAULT_REPOSITORY = "Ohoredingdong/Notion"
PR_FIELDS = "url,headRefOid,isCrossRepository,headRefName,baseRefName"


class OperationStopped(Exception):
    def __init__(self, status: str, stage: str, reason: str, message: str):
        super().__init__(message)
        self.status, self.stage, self.reason = status, stage, reason


def stop(status: str, stage: str, reason: str, message: str):
    raise OperationStopped(status, stage, reason, message)


def run_command(root: Path, arguments: list[str]) -> subprocess.CompletedProcess:
    """Structured arguments, no interactive login and no shell interpolation."""
    environment = dict(os.environ, GH_PROMPT_DISABLED="1")
    try:
        return subprocess.run(arguments, cwd=root, text=True, capture_output=True,
                              stdin=subprocess.DEVNULL, env=environment, timeout=60)
    except FileNotFoundError:
        stop("blocked", "tooling", "tool_unavailable", "A required Git or GitHub CLI executable is unavailable.")
    except subprocess.TimeoutExpired:
        stop("blocked", "network", "request_timeout", "The remote operation timed out; its state is unconfirmed.")
    except UnicodeError:
        stop("blocked", "github-response", "unexpected_github_encoding", "The remote response could not be decoded safely.")


def repository_slug(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        stop("rejected", "arguments", "invalid_repository", "Use an explicit GitHub OWNER/REPOSITORY slug.")
    return value


def validate_ref(root: Path, value: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("-"):
        stop("rejected", "repository", "invalid_branch", "A valid named Git branch is required.")
    try:
        release.git(root, "check-ref-format", "refs/heads/" + value)
    except release.ReleaseRejected:
        stop("rejected", "repository", "invalid_branch", "A valid named Git branch is required.")
    return value


def check_origin(root: Path, expected: str) -> None:
    remote = release.git(root, "remote", "get-url", "origin").decode().strip()
    if remote.startswith("git@github.com:"):
        actual = remote[len("git@github.com:"):]
    else:
        try:
            parsed = urlsplit(remote)
        except ValueError:
            stop("rejected", "repository", "repository_mismatch", "origin is not a valid GitHub repository URL.")
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            stop("rejected", "repository", "repository_mismatch", "origin is not the requested GitHub repository.")
        actual = parsed.path.strip("/")
    actual = actual.removesuffix(".git")
    if actual.casefold() != expected.casefold():
        stop("rejected", "repository", "repository_mismatch", "origin is not the requested GitHub repository.")


def check_pushed_head(root: Path, branch: str, sha: str) -> None:
    reference = "refs/heads/" + branch
    response = run_command(root, ["git", "ls-remote", "--heads", "origin", reference])
    if response.returncode != 0:
        stop("blocked", "remote", "remote_access_blocked", "The pushed branch could not be verified with the existing Git connection.")
    rows = [row.split() for row in response.stdout.splitlines() if row.strip()]
    if not rows:
        stop("rejected", "remote", "branch_not_pushed", "Push the tested branch before requesting a draft PR.")
    if len(rows) != 1 or len(rows[0]) != 2 or rows[0][1] != reference:
        stop("blocked", "remote", "unexpected_remote_output", "The remote branch response could not be verified.")
    if rows[0][0] != sha:
        stop("rejected", "remote", "remote_head_mismatch", "The pushed branch differs from the tested HEAD.")


def checked_state(root: Path, sha: str, report: dict, output: Path) -> None:
    release.require_clean(root, sha)
    snapshot = release.tracked_snapshot(root)
    required = release.current_check_ids(root, output.parent / "pr-plan")
    release.validate_receipt(report, sha, snapshot, required)


def existing_url(value: object, repository: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
            r"https://github\.com/" + re.escape(repository) + r"/pull/[1-9][0-9]*/?", value, re.I):
        stop("blocked", "github-response", "unexpected_github_output", "The GitHub PR URL could not be verified.")
    return value


def metadata(value: object, repository: str, sha: str, branch: str, base: str) -> str:
    if not isinstance(value, dict):
        stop("blocked", "github-response", "unexpected_github_output", "The GitHub PR metadata could not be verified.")
    url = existing_url(value.get("url"), repository)
    if value.get("headRefOid") != sha:
        stop("blocked", "github-response", "pull_request_head_mismatch", "The pull request does not contain the exact tested HEAD.")
    if value.get("isCrossRepository") is not False or value.get("headRefName") != branch or value.get("baseRefName") != base:
        stop("blocked", "github-response", "pull_request_source_mismatch", "The PR source repository, branch or base differs from the tested pushed branch.")
    return url


def api_failure(response: subprocess.CompletedProcess, stage: str) -> None:
    text = (response.stderr or "").casefold()
    reason = "github_api_unavailable"
    if "forbidden" in text or "403" in text:
        reason = "github_api_forbidden"
    elif any(part in text for part in ("authenticate", "authentication", "gh auth login", "401", "not logged")):
        reason = "github_authentication_unavailable"
    elif "certificate" in text or "tls" in text:
        reason = "github_tls_verification_failed"
    # Do not copy credentials, request headers or arbitrary CLI diagnostics into reports.
    stop("blocked", stage, reason,
         "GitHub could not confirm the PR operation. No authentication, proxy or deployment settings were changed.")


def parse_response(response: subprocess.CompletedProcess, stage: str):
    if response.returncode != 0:
        api_failure(response, stage)
    try:
        return json.loads(response.stdout)
    except (TypeError, ValueError):
        stop("blocked", stage, "unexpected_github_output", "The GitHub response was not valid PR metadata.")


def open_pull_request(root: Path, report_path: Path, title: str, body_file: Path,
                      base: str, repository: str, output: Path) -> dict:
    result = {"schema_version": SCHEMA_VERSION, "operation": "draft-pull-request",
              "status": "rejected", "creation_attempted": False,
              "creation_may_have_succeeded": False}
    stage = "arguments"
    try:
        root = release.checkout_root(root)
        output = release.external_path(root, output)
        report_path = release.external_path(root, report_path)
        if output == report_path or output == body_file.resolve():
            stop("rejected", stage, "output_conflicts_with_input", "The result output must not overwrite the check receipt or PR body.")
        repository = repository_slug(repository)
        base = validate_ref(root, base)
        if not isinstance(title, str) or not title.strip() or len(title) > 256 or any(c in title for c in "\r\n\x00"):
            stop("rejected", stage, "invalid_title", "Use a nonempty, single-line PR title of at most 256 characters.")
        if any(part.is_symlink() for part in (body_file.absolute(), *body_file.absolute().parents)) or not body_file.is_file():
            stop("rejected", stage, "invalid_body_file", "The PR body must be a readable regular file.")
        body_file = body_file.resolve()
        body_bytes = body_file.read_bytes()
        if not body_bytes.strip():
            stop("rejected", stage, "empty_body", "Prepare a concrete PR description before creating a draft.")
        sha = release.exact_sha(release.git(root, "rev-parse", "HEAD").decode().strip())
        result["head_sha"] = sha
        stage = "checks"
        try:
            report_bytes = report_path.read_bytes()
            report = json.loads(report_bytes)
        except (OSError, ValueError):
            stop("rejected", stage, "invalid_check_receipt", "The completed --all check receipt is missing or malformed.")
        checked_state(root, sha, report, output)
        branch_response = subprocess.run(["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
                                         text=True, capture_output=True)
        if branch_response.returncode != 0:
            stop("rejected", "repository", "detached_head", "Use the named development branch, not detached HEAD.")
        branch = validate_ref(root, branch_response.stdout.strip())
        if branch in {"main", "master", base}:
            stop("rejected", "repository", "protected_source_branch", "A development branch separate from main and the PR base is required.")
        result.update({"head_sha": sha, "branch": branch, "base": base, "repository": repository,
                       "check_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                       "body_file_sha256": hashlib.sha256(body_bytes).hexdigest()})
        check_origin(root, repository)
        check_pushed_head(root, branch, sha)
        stage = "list"
        host_repository = "github.com/" + repository
        response = run_command(root, ["gh", "pr", "list", "--repo", host_repository, "--head", branch,
                                      "--base", base, "--state", "open", "--json", PR_FIELDS])
        listed = parse_response(response, stage)
        if not isinstance(listed, list) or len(listed) > 1:
            stop("blocked", stage, "ambiguous_existing_pull_request", "The existing PR response is ambiguous; no new PR was created.")
        checked_state(root, sha, report, output)
        check_pushed_head(root, branch, sha)
        if listed:
            url = metadata(listed[0], repository, sha, branch, base)
            result.update({"status": "existing", "url": url, "exit_code": 0,
                           "message": "The existing PR already contains the exact tested HEAD; it was not edited."})
            return result
        if body_file.read_bytes() != body_bytes:
            stop("rejected", "body", "body_changed", "The prepared PR description changed before creation.")
        stage = "create"
        result["creation_attempted"] = True
        result["creation_may_have_succeeded"] = True
        response = run_command(root, ["gh", "pr", "create", "--draft", "--repo", host_repository,
                                      "--head", branch, "--base", base, "--title", title,
                                      "--body-file", str(body_file)])
        if response.returncode != 0:
            api_failure(response, stage)
        url = existing_url(response.stdout.strip(), repository)
        result["candidate_url"] = url
        stage = "verify-created"
        response = run_command(root, ["gh", "pr", "view", url, "--repo", host_repository,
                                      "--json", PR_FIELDS])
        verified = metadata(parse_response(response, stage), repository, sha, branch, base)
        if verified != url:
            stop("blocked", stage, "pull_request_url_mismatch", "The created PR URL differs from its verified metadata.")
        checked_state(root, sha, report, output)
        check_pushed_head(root, branch, sha)
        if body_file.read_bytes() != body_bytes:
            stop("blocked", stage, "body_changed", "The description file changed during the PR operation; review the candidate PR before retrying.")
        result.update({"status": "created", "url": url, "exit_code": 0,
                       "message": "A draft PR was created and its exact tested HEAD was verified. Nothing was merged or deployed."})
        return result
    except OperationStopped as error:
        status = "blocked" if result["creation_attempted"] else error.status
        result.update({"status": status, "stage": error.stage, "reason": error.reason,
                       "message": str(error), "exit_code": 2 if status == "blocked" else 1})
    except release.ReleaseRejected as error:
        result.update({"status": "blocked" if result["creation_attempted"] else "rejected",
                       "stage": stage, "reason": "source_or_check_guard_rejected", "message": str(error),
                       "exit_code": 2 if result["creation_attempted"] else 1})
    except OSError:
        result.update({"status": "blocked", "stage": stage, "reason": "operation_unavailable",
                       "message": "A required file or command could not be used; the operation is unconfirmed.", "exit_code": 2})
    return result


def write_result(root: Path, path: Path, result: dict) -> None:
    path = release.external_path(release.checkout_root(root), path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="notion-pr-result-",
                                     dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--base", default="main")
    parser.add_argument("--repo", default=DEFAULT_REPOSITORY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = open_pull_request(args.root, args.report, args.title, args.body_file,
                               args.base, args.repo, args.output)
    try:
        if args.output.resolve() not in (args.report.resolve(), args.body_file.resolve()):
            write_result(args.root, args.output, result)
    except (release.ReleaseRejected, OSError):
        result = {**result, "status": "blocked", "stage": "result", "reason": "result_output_unavailable",
                  "message": "The operation result could not be written safely; no success is claimed.", "exit_code": 2}
        if "url" in result:
            result["candidate_url"] = result.pop("url")
    print(json.dumps(result, ensure_ascii=False))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
