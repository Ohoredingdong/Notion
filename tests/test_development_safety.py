"""Regressions for test selection, real failure propagation and candidate gates."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_changed as checks
import prepare_release as release
import yaml


class SelectionTests(unittest.TestCase):
    def test_financial_build_update_and_test_changes_select_their_actual_suites(self):
        expected = {
            "scripts/build_stock_event_outlook.py": "scripts.test_stock_event_outlook",
            "scripts/build_stock_entry_plan.py": "scripts.test_stock_entry_plan",
            "scripts/update_stock_opportunities.py": "scripts.test_stock_opportunities",
        }
        for path, suite in expected.items():
            with self.subTest(path=path):
                plan = checks.plan_checks([path])
                self.assertIn("radar", plan["groups"])
                self.assertIn("radar", plan["browser_required"])
                commands = checks.commands_for(plan["groups"], plan["unit_modules"], plan["node_tests"])
                self.assertTrue(any(suite in command for _, command in commands), commands)

    def test_entry_ui_test_runs_when_it_alone_changes(self):
        plan = checks.plan_checks(["tests/stock-entry-ui.test.cjs"])
        self.assertTrue(any("tests/stock-entry-ui.test.cjs" in command for _, command in checks.commands_for(plan["groups"])))

    def test_unmapped_production_module_is_not_green_just_from_generic_tests(self):
        plan = checks.plan_checks(["scripts/build_stock_uncovered_feature.py"])
        self.assertEqual(plan["unknown_code"], ["scripts/build_stock_uncovered_feature.py"])
        for path in ("scripts/uncovered-collector.cjs", "scripts/uncovered-job.sh"):
            self.assertEqual(checks.plan_checks([path])["unknown_code"], [path])

    def test_radar_ui_selects_finance_and_browser_regressions(self):
        plan = checks.plan_checks(["assets/stock-radar-flow-v2.js"])
        self.assertEqual(plan["groups"], ["radar"])
        self.assertEqual(plan["browser_required"], ["radar"])

    def test_data_and_publisher_paths_are_not_mistaken_for_docs(self):
        self.assertIn("radar", checks.plan_checks(["stock-direction-forecast.json"])["groups"])
        self.assertIn("publishers", checks.plan_checks(["scripts/publish_widget_data.py"])["groups"])

    def test_shared_tooling_covers_existing_widget_tests(self):
        groups = checks.plan_checks(["requirements-dev.txt"])["groups"]
        self.assertEqual(groups, ["auction", "fridge", "publishers", "radar", "tooling", "toss"])

    def test_unmapped_widget_is_explicitly_unverified(self):
        self.assertEqual(checks.plan_checks(["new-widget.html"])["unknown_ui"], ["new-widget.html"])

    def test_no_production_publisher_or_collector_is_a_test_command(self):
        commands = checks.commands_for(["radar", "publishers", "fridge", "auction", "tooling", "toss"])
        for _, command in commands:
            self.assertFalse(any("scripts/publish_" in p or "scripts/run_stock" in p for p in command), command)
        self.assertTrue(any("scripts.test_widget_data_repairs" in command for _, command in commands))


class StaticTests(unittest.TestCase):
    def test_deleted_referenced_asset_fails_even_if_html_did_not_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<script src="./gone.js?v=2"></script>')
            result = checks.static_checks(root, ["gone.js"])
            self.assertEqual(result["status"], "failed")
            self.assertIn("Missing local dependency", str(result["errors"]))

    def test_broken_inline_javascript_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<script>const broken = ;</script>')
            self.assertEqual(checks.static_checks(root, ["index.html"])["status"], "failed")

    def test_json_nonfinite_is_not_accepted_as_financial_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data.json").write_text('{"price":NaN}')
            self.assertEqual(checks.static_checks(root, ["data.json"])["status"], "failed")

    def test_source_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<script src="../outside.js"></script>')
            self.assertEqual(checks.static_checks(root, ["index.html"])["status"], "failed")


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Offline test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "index.html").write_text("<h1>Verified candidate</h1>")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")
        self.report = {"schema_version": 1, "status": "passed", "unverified": [],
                       "head_sha": self.git("rev-parse", "HEAD").strip(), "source_digest": checks.source_digest(self.root),
                       "plan": {"browser_required": ["radar"]},
                       "checks": [{"name": "radar-browser", "status": "passed", "returncode": 0}]}

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

class CandidateTests(GitFixture):
    def test_success_creates_review_archive_without_git_or_secrets(self):
        report_path = self.root.parent / "report.json"
        report_path.write_text(json.dumps(self.report))
        manifest = release.prepare(self.root, report_path, self.root.parent / "candidate.tar.gz")
        self.assertEqual(manifest["kind"], "review-only-not-deployed")
        self.assertEqual(list(manifest["files"]), ["index.html"])
        with tarfile.open(self.root.parent / "candidate.tar.gz") as archive:
            data = archive.extractfile("index.html").read()
            self.assertEqual(hashlib.sha256(data).hexdigest(), manifest["files"]["index.html"])
            self.assertEqual(data, b"<h1>Verified candidate</h1>")

    def test_concurrent_source_edit_blocks_atomic_candidate_output(self):
        report_path = self.root.parent / "report.json"
        report_path.write_text(json.dumps(self.report))
        output = self.root.parent / "candidate.tar.gz"
        original = release.verify_report
        calls = 0

        def concurrent_edit(root, report):
            nonlocal calls
            calls += 1
            if calls == 2:
                (root / "index.html").write_text("<h1>Concurrent untested edit</h1>")
            return original(root, report)

        with patch.object(release, "verify_report", side_effect=concurrent_edit), self.assertRaises(ValueError):
            release.prepare(self.root, report_path, output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.parent.glob(".widget-candidate-*")), [])

    def test_failed_cancelled_incomplete_or_no_tests_block_candidate(self):
        for status in ("failed", "cancelled", "incomplete"):
            with self.subTest(status=status), self.assertRaises(ValueError):
                release.verify_report(self.root, {**self.report, "status": status})
        with self.assertRaises(ValueError):
            release.verify_report(self.root, {**self.report, "checks": []})

    def test_nonzero_exit_cannot_be_relabelled_as_pass(self):
        with self.assertRaisesRegex(ValueError, "exit code"):
            release.verify_report(self.root, {**self.report, "checks": [{"name": "radar-browser", "status": "passed", "returncode": 7}]})

    def test_missing_browser_cannot_be_relabelled_as_pass(self):
        report = {**self.report, "checks": [{"name": "syntax", "status": "passed", "returncode": 0}]}
        with self.assertRaisesRegex(ValueError, "browser check"):
            release.verify_report(self.root, report)

    def test_source_edit_after_validation_blocks_candidate(self):
        (self.root / "index.html").write_text("<h1>Untested edit</h1>")
        with self.assertRaisesRegex(ValueError, "committed and clean"):
            release.verify_report(self.root, self.report)

    def test_different_clean_commit_blocks_candidate(self):
        (self.root / "index.html").write_text("<h1>Another commit</h1>")
        self.git("add", ".")
        self.git("commit", "-m", "another")
        with self.assertRaisesRegex(ValueError, "another commit"):
            release.verify_report(self.root, self.report)

    def test_tampered_digest_blocks_candidate(self):
        with self.assertRaisesRegex(ValueError, "differs"):
            release.verify_report(self.root, {**self.report, "source_digest": "0" * 64})


class RealFailurePropagationTests(GitFixture):
    # Reuse the real temporary Git fixture, not mocked successful report files.
    def args(self, artifacts, browser=False):
        return argparse.Namespace(base="HEAD~1", head="HEAD", working_tree=False,
                                  browser=browser, profile=None, executable=None,
                                  artifacts=str(artifacts), plan_only=False)

    def change(self, name, body):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        self.git("add", ".")
        self.git("commit", "-m", "change fixture")

    def test_nonzero_command_cannot_turn_green_or_modify_source(self):
        self.change("scripts/example.py", "x = 1\n")
        before = checks.source_digest(self.root)
        output = self.root.parent / "artifacts"
        with patch.object(checks, "commands_for", return_value=[("failing-command", [sys.executable, "-c", "raise SystemExit(7)"])]):
            code = checks.run_checks(self.root, self.args(output))
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["checks"][-1]["returncode"], 7)
        self.assertEqual(checks.source_digest(self.root), before)

    def test_zero_tests_is_failure_despite_success_exit(self):
        self.change("scripts/example.py", "x = 1\n")
        output = self.root.parent / "artifacts"
        with patch.object(checks, "commands_for", return_value=[("empty-suite", [sys.executable, "-c", "print('Ran 0 tests')"])]):
            self.assertEqual(checks.run_checks(self.root, self.args(output)), 1)
        self.assertEqual(json.loads((output / "report.json").read_text())["checks"][-1]["reason"], "zero_tests")

    def test_testing_another_head_against_current_files_is_rejected(self):
        self.change("scripts/example.py", "x = 1\n")
        args = self.args(self.root.parent / "artifacts")
        args.head = "HEAD~1"
        with self.assertRaisesRegex(ValueError, "current checkout"):
            checks.run_checks(self.root, args)

    def test_unselected_working_changes_cannot_receive_a_clean_report(self):
        self.change("scripts/example.py", "x = 1\n")
        (self.root / "index.html").write_text("<h1>Unselected edit</h1>")
        with self.assertRaisesRegex(ValueError, "working changes"):
            checks.run_checks(self.root, self.args(self.root.parent / "artifacts"))

    def test_required_but_unrun_browser_is_incomplete(self):
        self.change("stock-widget.js", "const value = 1;\n")
        output = self.root.parent / "artifacts"
        with patch.object(checks, "commands_for", return_value=[]):
            self.assertEqual(checks.run_checks(self.root, self.args(output)), 1)
        self.assertEqual(json.loads((output / "report.json").read_text())["status"], "incomplete")


class WorkflowProtectionTests(unittest.TestCase):
    def test_all_existing_scheduled_financial_job_contracts_are_preserved(self):
        baseline = json.loads((ROOT / "tests/fixtures/scheduled-finance-jobs.json").read_text())
        self.assertEqual(len(baseline["sha256"]), 24)
        for filename, expected in baseline["sha256"].items():
            with self.subTest(filename=filename):
                doc = yaml.load((ROOT / filename).read_text(), Loader=yaml.BaseLoader)
                jobs = {key: value for key, value in doc["jobs"].items()
                        if not (filename.endswith("test-stock-neutral-ui.yml") and key == "verify")}
                payload = {key: doc.get(key) for key in ("permissions", "concurrency")}
                payload.update(schedule=doc["on"]["schedule"], jobs=jobs)
                actual = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                self.assertEqual(actual, expected, "Scheduled finance behavior changed; needs explicit review")

    def test_new_workflows_have_no_production_permissions_or_main_push_trigger(self):
        for filename in ("widget-development.yml", "widget-release-candidate.yml"):
            doc = yaml.load((ROOT / ".github/workflows" / filename).read_text(), Loader=yaml.BaseLoader)
            self.assertEqual(doc["permissions"], {"contents": "read"})
            self.assertNotIn("pull_request_target", doc["on"])
            self.assertNotIn("schedule", doc["on"])
            self.assertNotIn("main", doc["on"].get("push", {}).get("branches", []))
            text = json.dumps(doc)
            self.assertNotIn("deploy-pages", text)
            self.assertNotIn("git push", text)

    def test_integration_pr_paths_cover_same_sources_as_push(self):
        doc = yaml.load((ROOT / ".github/workflows/test-stock-radar-integration.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertTrue(set(doc["on"]["push"]["paths"]) <= set(doc["on"]["pull_request"]["paths"]))

    def test_legacy_ui_installer_is_design_branch_only(self):
        doc = yaml.load((ROOT / ".github/workflows/test-stock-neutral-ui.yml").read_text(), Loader=yaml.BaseLoader)
        installer = [step for step in doc["jobs"]["verify"]["steps"] if "python scripts/install_stock_radar_neutral.py" in step.get("run", "")]
        self.assertEqual(len(installer), 1)
        self.assertEqual(installer[0]["if"], "github.ref_name == 'design/neutral-production-20261030'")


if __name__ == "__main__":
    unittest.main()
