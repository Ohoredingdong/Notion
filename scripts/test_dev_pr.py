"""Draft-PR guard tests with disposable Git metadata and mocked GitHub replies.

Synthetic check receipts test gating only. These do not certify application,
financial data, GitHub authentication, PR creation, merging or deployment.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts import open_development_pr as pr
    from scripts import prepare_release as release
except ImportError:
    import open_development_pr as pr
    import prepare_release as release


IDS = sorted(release.MINIMUM_CHECK_IDS)
URL = "https://github.com/Ohoredingdong/Notion/pull/123"


class DevelopmentPRTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="notion-pr-guard-test-")
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.body = self.base / "pr-body.md"
        self.body_text = "Fix the reported navigation problem.\n\n- Literal `$()` and `backticks` stay text.\n"
        self.body.write_text(self.body_text)
        self.report = self.base / "check-report.json"
        self.output = self.base / "pr-result.json"
        self.branch = "chore/development-fixture"
        self.write("index.html", "<h1>Existing widget</h1>")
        self.write("scripts/dev_check.py", "IDS = " + repr(IDS) + "\n"
                   "def build_plan(root, *, all_checks=False, output=None, **kwargs):\n"
                   "    assert all_checks\n"
                   "    return {'checks':[{'id':x} for x in IDS], 'expected_check_ids':IDS}\n")
        self.git("init", "--quiet")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "user.name", "PR Guard Fixture")
        self.git("config", "user.email", "pr-guard@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/Ohoredingdong/Notion.git")
        self.commit()
        self.git("switch", "--quiet", "-c", self.branch)
        self.save_report(self.valid_report())
        self.calls = []
        self.on_list = None
        self.on_create = None
        self.remote_reply = None
        self.list_reply = self.response("[]")
        self.create_reply = self.response(URL + "\n")
        self.view_reply = self.response(json.dumps(self.pr_metadata()))

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              text=True, capture_output=True).stdout.strip()

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)

    def commit(self):
        self.git("add", "--all")
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Guard fixture")
        self.sha = self.git("rev-parse", "HEAD")

    def valid_report(self):
        stamp = datetime.now(timezone.utc).isoformat()
        return {"schema_version": 1, "head_sha": self.sha, "mode": "all", "status": "passed",
                "working_tree_clean": True, "expected_check_ids": list(IDS),
                "checks": [{"id": name, "status": "passed", "returncode": 0,
                            "started_at": stamp, "ended_at": stamp} for name in IDS],
                "snapshot": release.tracked_snapshot(self.root)}

    def save_report(self, value):
        self.report.write_text(json.dumps(value))

    def response(self, stdout="", returncode=0, stderr=""):
        return subprocess.CompletedProcess([], returncode, stdout, stderr)

    def pr_metadata(self, **changes):
        value = {"url": URL, "headRefOid": self.sha, "isCrossRepository": False,
                 "headRefName": self.branch, "baseRefName": "main"}
        value.update(changes)
        return value

    def remote(self, root, arguments):
        self.calls.append(arguments)
        if arguments[:3] == ["git", "ls-remote", "--heads"]:
            return self.remote_reply or self.response(self.sha + "\trefs/heads/" + self.branch + "\n")
        if arguments[:3] == ["gh", "pr", "list"]:
            if self.on_list:
                self.on_list()
            return self.list_reply
        if arguments[:3] == ["gh", "pr", "create"]:
            if self.on_create:
                self.on_create()
            return self.create_reply
        if arguments[:3] == ["gh", "pr", "view"]:
            return self.view_reply
        raise AssertionError("Unexpected remote operation in the PR fixture: " + repr(arguments))

    def open(self, **kwargs):
        values = {"root": self.root, "report_path": self.report, "title": "Fix widget navigation",
                  "body_file": self.body, "base": "main", "repository": "Ohoredingdong/Notion",
                  "output": self.output}
        values.update(kwargs)
        with patch.object(pr, "run_command", side_effect=self.remote):
            return pr.open_pull_request(**values)

    def github_operations(self):
        return [arguments[2] for arguments in self.calls if arguments[0] == "gh"]

    def test_creates_only_a_draft_and_verifies_its_exact_pushed_head(self):
        result = self.open(title="Literal $(printf unsafe) `title`")
        self.assertEqual(result["status"], "created")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["url"], URL)
        self.assertEqual(result["head_sha"], self.sha)
        self.assertEqual(self.github_operations(), ["list", "create", "view"])
        command = next(args for args in self.calls if args[:3] == ["gh", "pr", "create"])
        self.assertIn("--draft", command)
        self.assertEqual(command[command.index("--title") + 1], "Literal $(printf unsafe) `title`")
        self.assertEqual(command[command.index("--body-file") + 1], str(self.body))
        self.assertEqual(self.body.read_text(), self.body_text)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(result["check_report_sha256"], hashlib.sha256(self.report.read_bytes()).hexdigest())

    def test_existing_same_head_pr_is_reused_without_edits_or_duplicate_creation(self):
        self.list_reply = self.response(json.dumps([self.pr_metadata()]))
        result = self.open()
        self.assertEqual(result["status"], "existing")
        self.assertEqual(result["url"], URL)
        self.assertFalse(result["creation_attempted"])
        self.assertEqual(self.github_operations(), ["list"])

    def test_failed_skipped_zero_and_incomplete_checks_never_reach_remote_tools(self):
        for change in [lambda r: r.__setitem__("status", "failed"),
                       lambda r: r["checks"][0].__setitem__("status", "skipped"),
                       lambda r: r.__setitem__("checks", []),
                       lambda r: r["checks"].pop(),
                       lambda r: r.__setitem__("mode", "related"),
                       lambda r: r.__setitem__("working_tree_clean", False)]:
            with self.subTest(change=repr(change)):
                report = self.valid_report()
                change(report)
                self.save_report(report)
                self.calls.clear()
                result = self.open()
                self.assertEqual(result["status"], "rejected")
                self.assertNotEqual(result["exit_code"], 0)
                self.assertFalse(self.calls)

    def test_stale_head_receipt_is_rejected_before_any_github_operation(self):
        report = self.valid_report()
        report["head_sha"] = "0" * 40
        self.save_report(report)
        self.assertEqual(self.open()["status"], "rejected")
        self.assertFalse(self.calls)

    def test_dirty_worktree_is_rejected_before_any_remote_operation(self):
        self.write("index.html", "Untested changes")
        self.assertEqual(self.open()["status"], "rejected")
        self.assertFalse(self.calls)

    def test_main_and_detached_heads_cannot_create_a_development_pr(self):
        self.git("switch", "--quiet", "main")
        result = self.open()
        self.assertEqual(result["reason"], "protected_source_branch")
        self.assertFalse(self.calls)
        self.git("checkout", "--quiet", "--detach", self.sha)
        result = self.open()
        self.assertEqual(result["reason"], "detached_head")
        self.assertFalse(self.calls)

    def test_wrong_origin_repository_is_rejected_before_remote_operations(self):
        self.git("remote", "set-url", "origin", "https://github.com/Someone/Other.git")
        result = self.open()
        self.assertEqual(result["reason"], "repository_mismatch")
        self.assertFalse(self.calls)

    def test_missing_or_different_pushed_head_never_calls_github(self):
        for response, reason in [(self.response(""), "branch_not_pushed"),
                                 (self.response("0" * 40 + "\trefs/heads/" + self.branch + "\n"), "remote_head_mismatch")]:
            with self.subTest(reason=reason):
                self.remote_reply = response
                result = self.open()
                self.assertEqual(result["reason"], reason)
                self.assertEqual(self.github_operations(), [])

    def test_remote_read_failure_or_malformed_response_is_blocked_not_assumed_absent(self):
        for response in [self.response("", 1, "Forbidden"), self.response("unexpected response")]:
            with self.subTest(response=response):
                self.remote_reply = response
                result = self.open()
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(self.github_operations(), [])

    def test_api_forbidden_is_blocked_and_never_treated_as_no_existing_pr(self):
        self.list_reply = self.response("", 1, "Get https://api.github.com/repos/Ohoredingdong/Notion: Forbidden")
        result = self.open()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "github_api_forbidden")
        self.assertEqual(result["exit_code"], 2)
        self.assertFalse(result["creation_attempted"])
        self.assertEqual(self.github_operations(), ["list"])

    def test_unavailable_authentication_never_starts_login_or_creates_a_pr(self):
        self.list_reply = self.response("", 1, "To get started, please run gh auth login")
        result = self.open()
        self.assertEqual(result["reason"], "github_authentication_unavailable")
        self.assertEqual(self.github_operations(), ["list"])

    def test_malformed_ambiguous_or_wrong_head_existing_results_cannot_create_duplicates(self):
        rows = ["not JSON", "{}", "null", json.dumps([{"url": URL, "headRefOid": self.sha}] * 2),
                json.dumps([{"url": URL, "headRefOid": "0" * 40}]),
                json.dumps([{"url": "https://example.invalid/pull/1", "headRefOid": self.sha}])]
        for body in rows:
            with self.subTest(body=body):
                self.calls.clear()
                self.list_reply = self.response(body)
                result = self.open()
                self.assertEqual(result["status"], "blocked")
                self.assertFalse(result["creation_attempted"])
                self.assertEqual(self.github_operations(), ["list"])

    def test_create_error_or_ambiguous_output_does_not_claim_success(self):
        for response in [self.response("", 1, "Forbidden"), self.response("not a PR URL"),
                         self.response(URL + "\nunexpected second line"),
                         self.response("https://github.com/Other/Repository/pull/123")]:
            with self.subTest(response=response):
                self.calls.clear()
                self.create_reply = response
                result = self.open()
                self.assertEqual(result["status"], "blocked")
                self.assertTrue(result["creation_attempted"])
                self.assertTrue(result["creation_may_have_succeeded"])
                self.assertNotIn("url", result)
                self.assertEqual(self.github_operations(), ["list", "create"])

    def test_created_pr_requires_readonly_exact_head_verification(self):
        for response in [self.response("", 1, "Forbidden"), self.response("invalid JSON"),
                         self.response(json.dumps({"url": URL, "headRefOid": "0" * 40}))]:
            with self.subTest(response=response):
                self.calls.clear()
                self.view_reply = response
                result = self.open()
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["candidate_url"], URL)
                self.assertNotIn("url", result)
                self.assertTrue(result["creation_may_have_succeeded"])

    def test_branch_change_during_existing_pr_query_prevents_creation(self):
        self.on_list = lambda: self.write("index.html", "Changed during GitHub query")
        result = self.open()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.github_operations(), ["list"])

    def test_pushed_head_change_during_existing_pr_query_prevents_creation(self):
        def moved_remote():
            self.remote_reply = self.response("0" * 40 + "\trefs/heads/" + self.branch + "\n")
        self.on_list = moved_remote
        result = self.open()
        self.assertEqual(result["reason"], "remote_head_mismatch")
        self.assertEqual(self.github_operations(), ["list"])

    def test_source_change_after_creation_is_reported_as_uncertain_not_success(self):
        self.on_create = lambda: self.write("index.html", "Changed while creating PR")
        result = self.open()
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["creation_may_have_succeeded"])
        self.assertEqual(result["candidate_url"], URL)
        self.assertNotIn("url", result)

    def test_different_fork_branch_or_base_cannot_reuse_an_existing_pr(self):
        cases = [{"isCrossRepository": True}, {"headRefName": "another-branch"},
                 {"baseRefName": "another-base"}, {"isCrossRepository": None}]
        for change in cases:
            with self.subTest(change=change):
                self.calls.clear()
                self.list_reply = self.response(json.dumps([self.pr_metadata(**change)]))
                result = self.open()
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reason"], "pull_request_source_mismatch")
                self.assertEqual(self.github_operations(), ["list"])

    def test_created_pr_verification_checks_its_repository_branch_and_base(self):
        self.view_reply = self.response(json.dumps(self.pr_metadata(isCrossRepository=True)))
        result = self.open()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "pull_request_source_mismatch")
        self.assertTrue(result["creation_may_have_succeeded"])
        self.assertNotIn("url", result)

    def test_remote_change_after_creation_is_blocked_and_preserves_the_candidate_url(self):
        def moved_remote():
            self.remote_reply = self.response("0" * 40 + "\trefs/heads/" + self.branch + "\n")
        self.on_create = moved_remote
        result = self.open()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["exit_code"], 2)
        self.assertTrue(result["creation_may_have_succeeded"])
        self.assertEqual(result["candidate_url"], URL)
        self.assertNotIn("url", result)

    def test_body_change_before_creation_is_rejected(self):
        self.on_list = lambda: self.body.write_text("Different description")
        result = self.open()
        self.assertEqual(result["reason"], "body_changed")
        self.assertEqual(self.github_operations(), ["list"])

    def test_invalid_arguments_or_body_never_reach_remote_tools(self):
        empty = self.base / "empty.md"
        empty.write_text("")
        for values in [{"title": ""}, {"title": "bad\ntitle"}, {"repository": "--bad/repo"},
                       {"base": "../invalid"}, {"body_file": empty},
                       {"output": self.report}, {"output": self.body},
                       {"report_path": self.root / "inside.json"}]:
            with self.subTest(values=values):
                self.calls.clear()
                self.assertEqual(self.open(**values)["status"], "rejected")
                self.assertFalse(self.calls)

    def test_cli_writes_a_current_blocked_result_instead_of_leaving_old_success(self):
        self.output.write_text('{"status":"created","url":"stale result"}')
        self.list_reply = self.response("", 1, "Forbidden")
        with patch.object(pr, "run_command", side_effect=self.remote), patch("sys.stdout", new_callable=io.StringIO):
            code = pr.main(["--root", str(self.root), "--report", str(self.report),
                            "--title", "Fix navigation", "--body-file", str(self.body),
                            "--output", str(self.output)])
        result = json.loads(self.output.read_bytes())
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "github_api_forbidden")
        self.assertNotIn("url", result)

    def test_cli_cannot_overwrite_the_passed_check_report(self):
        before = self.report.read_bytes()
        with patch.object(pr, "run_command", side_effect=self.remote), patch("sys.stdout", new_callable=io.StringIO):
            code = pr.main(["--root", str(self.root), "--report", str(self.report),
                            "--title", "Fix navigation", "--body-file", str(self.body),
                            "--output", str(self.report)])
        self.assertNotEqual(code, 0)
        self.assertEqual(self.report.read_bytes(), before)
        self.assertFalse(self.calls)

    def test_missing_cli_and_timeout_are_blocked_without_login_fallback(self):
        for failure in [FileNotFoundError(), subprocess.TimeoutExpired(["gh"], 60)]:
            with self.subTest(failure=failure), patch.object(pr.subprocess, "run", side_effect=failure):
                with self.assertRaises(pr.OperationStopped) as stopped:
                    pr.run_command(self.root, ["gh", "pr", "list"])
                self.assertEqual(stopped.exception.status, "blocked")


if __name__ == "__main__":
    unittest.main()
