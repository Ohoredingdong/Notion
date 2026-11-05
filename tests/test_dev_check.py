"""Behavioral regressions for change routing and isolated execution (offline)."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dev_check", ROOT / "scripts/dev_check.py")
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


def fixture_config():
    return {"version": 1, "documentation": ["*.md", "docs/**"],
            "checks": {"browser": {"argv": ["{python}", "tests/test_browser.py"]},
                       "policy": {"argv": ["{python}", "tests/test_policy.py"]}},
            "routes": [{"patterns": ["stock-value-radar.html", "assets/radar.js", "stock-*.json"], "checks": ["browser"]},
                       {"patterns": [".github/workflows/**"], "checks": ["policy"]}]}


class ChangeRoutingTests(unittest.TestCase):
    def test_zero_terminated_rename_preserves_both_paths(self):
        result = dev.parse_name_status(b"R097\0assets/old\tfile.js\0assets/new file.js\0D\0gone.py\0")
        self.assertEqual(result, [{"status": "R097", "path": "assets/new file.js", "old_path": "assets/old\tfile.js"},
                                  {"status": "D", "path": "gone.py"}])

    def test_incomplete_rename_is_an_error(self):
        with self.assertRaises(ValueError):
            dev.parse_name_status(b"R100\0old.js\0")

    def test_unsafe_paths_are_rejected(self):
        for path in ["../secret", "/tmp/secret", ".git/config", "assets/../../config"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                dev.safe_path(path)

    def test_root_star_does_not_match_nested_data(self):
        self.assertTrue(dev.path_matches("stock-ledger.json", "stock-*.json"))
        self.assertFalse(dev.path_matches("data/stock-ledger.json", "stock-*.json"))
        self.assertFalse(dev.path_matches("stock-dir/file.json", "stock-*.json"))

    def test_double_star_supports_zero_or_many_directories(self):
        for path in [".github/workflows/a.yml", ".github/workflows/nested/a.yml"]:
            self.assertTrue(dev.path_matches(path, ".github/workflows/**"))
        self.assertTrue(dev.path_matches("docs/readme.md", "docs/**/*.md"))

    def test_rename_selects_old_and_new_functional_routes(self):
        changes = [{"status": "R100", "old_path": "assets/radar.js", "path": ".github/workflows/move.yml"}]
        result = dev.plan_checks(changes, fixture_config())
        self.assertEqual(set(result["functional_coverage"][changes[0]["path"]]), {"browser", "policy"})

    def test_deleted_radar_runs_functional_checks_without_reading_deleted_file(self):
        result = dev.plan_checks([{"status": "D", "path": "stock-value-radar.html"}], fixture_config())
        self.assertEqual([x["id"] for x in result["selected"]], ["browser"])
        self.assertEqual(result["uncovered"], [])

    def test_deleted_unrouted_data_requires_coverage(self):
        result = dev.plan_checks([{"status": "D", "path": "important.json"}], fixture_config())
        self.assertEqual(len(result["uncovered"]), 1)

    def test_unknown_code_never_passes_on_syntax_only(self):
        for path in ["new-widget.html", "assets/new.js", "scripts/new.py", "assets/new.css", "scripts/new.sh"]:
            with self.subTest(path=path):
                result = dev.plan_checks([{"status": "M", "path": path}], fixture_config())
                self.assertEqual([x["path"] for x in result["uncovered"]], [path])

    def test_unknown_operational_json_requires_functional_coverage(self):
        for path in ["misc-data.json", "unvalidated-ledger.jsonl", "data/current.json"]:
            with self.subTest(path=path):
                result = dev.plan_checks([{"status": "M", "path": path}], fixture_config())
                self.assertEqual([x["path"] for x in result["uncovered"]], [path])
                self.assertEqual(result["selected"][0]["id"], "static:" + path)

    def test_documentation_json_is_parsed_but_exempt_from_functional_coverage(self):
        result = dev.plan_checks([{"status": "M", "path": "docs/audit-evidence.json"}], fixture_config())
        self.assertEqual(result["uncovered"], [])
        self.assertEqual(result["functional_coverage"]["docs/audit-evidence.json"], [])
        self.assertEqual(result["selected"][0]["id"], "static:docs/audit-evidence.json")
        self.assertEqual(len(result["not_applicable"]), 1)

    def test_executable_source_in_docs_is_still_uncovered(self):
        result = dev.plan_checks([{"status": "M", "path": "docs/unsafe.py"}], fixture_config())
        self.assertEqual(len(result["uncovered"]), 1)

    def test_nonfunctional_route_does_not_hide_missing_coverage(self):
        config = fixture_config()
        config["checks"]["browser"]["functional"] = False
        result = dev.plan_checks([{"status": "M", "path": "assets/radar.js"}], config)
        self.assertEqual(len(result["uncovered"]), 1)

    def test_docs_are_explicitly_not_applicable(self):
        result = dev.plan_checks([{"status": "M", "path": "README.md"}], fixture_config())
        self.assertEqual(result["uncovered"], [])
        self.assertEqual(result["selected"], [])
        self.assertEqual(len(result["not_applicable"]), 1)

    def test_scheduled_bot_json_changes_select_radar_browser(self):
        result = dev.plan_checks([{"status": "M", "path": "stock-direction-forecasts.json"}], fixture_config())
        self.assertEqual(result["functional_coverage"]["stock-direction-forecasts.json"], ["browser"])
        self.assertEqual(len(result["selected"]), 2)

    def test_repository_routes_never_execute_data_writers(self):
        config = dev.load_config(ROOT)
        for check in config["checks"].values():
            self.assertNotIn("git", check["argv"])
            self.assertNotIn("gh", check["argv"])
        for path in ["assets/stock-radar-flow-v2.js", "stock-value-radar.html", "stock-opportunity-data.json",
                     "scripts/dev_check.py", "scripts/publish_widget_data.py", ".github/workflows/update-commodities.yml"]:
            result = dev.plan_checks([{"status": "M", "path": path}], config)
            self.assertEqual(result["uncovered"], [], path)

    def test_browser_feed_routes_match_actual_canonical_inputs(self):
        source = ast.parse((ROOT / "scripts/test_stock_radar_canonical_browser.py").read_text())
        feeds = next(ast.literal_eval(statement.value) for statement in source.body
                     if isinstance(statement, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "DATA_FILES"
                                                                for target in statement.targets))
        config = dev.load_config(ROOT)
        for path in feeds:
            result = dev.plan_checks([{"status": "M", "path": path}], config)
            self.assertIn("radar-browser", result["functional_coverage"][path], path)
            self.assertEqual(result["uncovered"], [], path)
        for path in ["stock-new-ledger.json", "stock-unconsumed.jsonl", "stock-synthetic-test-results.json",
                     "market-events-data.json", "stock-event-calendar-seed.json"]:
            result = dev.plan_checks([{"status": "M", "path": path}], config)
            self.assertNotIn("radar-browser", result["functional_coverage"][path])
            self.assertEqual(len(result["uncovered"]), 1, path)

    def test_accuracy_audit_is_read_only_and_only_routed_to_consumed_inputs(self):
        config = dev.load_config(ROOT)
        check = config["checks"]["radar-data-audit"]
        self.assertEqual(check["argv"], ["{python}", "scripts/audit_stock_radar_accuracy.py", "--check"])
        for path in ["stock-forecast-outcomes.jsonl", "stock-forecast-learning.json"]:
            result = dev.plan_checks([{"status": "M", "path": path}], config)
            self.assertIn("radar-data-audit", result["functional_coverage"][path])
        result = dev.plan_checks([{"status": "M", "path": "stock-forecast-ledger.jsonl"}], config)
        self.assertNotIn("radar-data-audit", result["functional_coverage"]["stock-forecast-ledger.jsonl"])

    def test_production_writer_in_route_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github").mkdir()
            config = fixture_config()
            config["checks"]["browser"]["argv"] = ["{python}", "scripts/publish_widget_data.py"]
            (root / dev.CONFIG).write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "production writer"):
                dev.load_config(root)


class StaticValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_python_syntax_check_never_creates_bytecode(self):
        self.write("good.py", "answer = 42\n")
        dev.static_check(self.root, "good.py")
        self.assertFalse((self.root / "__pycache__").exists())
        self.write("bad.py", "def broken(:\n")
        with self.assertRaises(SyntaxError):
            dev.static_check(self.root, "bad.py")

    def test_jsonl_reports_exact_invalid_line(self):
        self.write("data.jsonl", '{"a": 1}\n\n{"broken":\n')
        with self.assertRaisesRegex(ValueError, "data.jsonl:3:"):
            dev.static_check(self.root, "data.jsonl")

    def test_nonfinite_json_is_rejected(self):
        self.write("data.json", '{"value": NaN}')
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            dev.static_check(self.root, "data.json")

    def test_html_missing_stylesheet_is_a_failure(self):
        self.write("index.html", '<link rel="stylesheet" href="./assets/missing.css?v=1">')
        with self.assertRaisesRegex(ValueError, "missing local link"):
            dev.static_check(self.root, "index.html")

    def test_html_inline_script_is_actually_parsed(self):
        self.write("index.html", '<script>function broken( {</script>')
        with self.assertRaisesRegex(ValueError, "inline script 1"):
            dev.static_check(self.root, "index.html")

    def test_html_module_script_and_data_blocks(self):
        self.write("module.js", 'export const value = 1;\n')
        self.write("index.html", '<script type="module" src="./module.js?v=1"></script>'
                   '<script type="application/ld+json">{"value":1}</script>')
        dev.static_check(self.root, "index.html")

    def test_html_external_assets_are_not_downloaded(self):
        self.write("index.html", '<script src="https://example.invalid/missing.js"></script>')
        dev.static_check(self.root, "index.html")


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "artifacts"

    def run_command(self, source, **options):
        return dev.command_check({"id": "sample", "argv": ["{python}", "-c", source], **options},
                                 self.root, self.artifacts, None)

    def test_nonzero_exit_and_output_are_preserved(self):
        result = self.run_command("import sys; print('meaningful failure'); sys.exit(7)")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 7)
        self.assertIn("meaningful failure", Path(result["log"]).read_text())

    def test_timeout_is_failure_not_pass_or_skip(self):
        result = self.run_command("import time; time.sleep(1)", timeout=0.03)
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["status"], "failed")

    def test_empty_unittest_suite_is_not_success(self):
        result = dev.command_check({"id": "empty", "argv": ["{python}", "-m", "unittest", "discover", "-s", "."]},
                                   self.root, self.artifacts, None)
        # Python versions differ: newer unittest returns 5 for zero tests.
        self.assertIn(result["exit_code"], [0, 5])
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["empty_suite"])

    def test_missing_executable_is_reported_as_failure(self):
        result = dev.command_check({"id": "missing", "argv": ["/definitely/not/a/tool"]},
                                   self.root, self.artifacts, None)
        self.assertEqual(result["status"], "failed")

    def test_isolated_node_test_can_use_installed_checkout_dependencies(self):
        dependencies = self.root / "installed"
        module = dependencies / "node_modules/example-dependency/index.js"
        module.parent.mkdir(parents=True)
        module.write_text("module.exports = 42;\n")
        isolated = self.root / "snapshot"
        isolated.mkdir()
        result = dev.command_check({"id": "dependency-resolution", "argv": ["node", "-e",
                                   "require('node:assert/strict').equal(require('example-dependency'), 42)"]},
                                   isolated, self.artifacts, None, dependencies)
        self.assertEqual(result["status"], "passed", result["output_tail"])
        self.assertFalse((isolated / "node_modules").exists())

    def test_uncovered_source_blocks_green_even_if_syntax_passes(self):
        (self.root / "new.py").write_text("answer = 42")
        plan = dev.plan_checks([{"status": "M", "path": "new.py"}], fixture_config())
        dev.execute_plan(plan, self.root, self.artifacts, None)
        self.assertEqual(plan["counts"]["passed"], 1)
        self.assertEqual(plan["counts"]["uncovered"], 1)
        self.assertEqual(plan["status"], "failed")

    def test_unrun_checks_remain_visible_after_infrastructure_failure(self):
        plan = dev.plan_checks([{"status": "M", "path": "assets/radar.js"}], fixture_config())
        plan["infrastructure_error"] = "snapshot could not be prepared"
        dev.finish_report(plan)
        self.assertEqual(plan["status"], "failed")
        self.assertEqual(plan["counts"]["unrun"], 2)
        self.assertEqual(plan["counts"]["passed"], 0)


class GitSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        self.call("init", "-q")
        self.call("config", "user.email", "test@example.invalid")
        self.call("config", "user.name", "Validation tests")
        (self.root / "data.json").write_text('{"original": true}\n')
        self.call("add", "data.json")
        self.call("commit", "-qm", "initial")

    def call(self, *args):
        return dev.git(self.root, *args)

    def test_working_tree_discovery_includes_staged_unstaged_and_new_paths(self):
        (self.root / "data.json").write_text('{"changed": true}\n')
        (self.root / "staged.js").write_text("const staged = true;")
        self.call("add", "staged.js")
        (self.root / "new file.py").write_text("fresh = True\n")
        found = dev.discover_changes(self.root, "HEAD", working_tree=True)
        self.assertEqual({x["path"] for x in found}, {"data.json", "staged.js", "new file.py"})

    def test_explicit_scope_excludes_unrelated_user_files(self):
        (self.root / "user-work.py").write_text("preserved = True\n")
        found = dev.discover_changes(self.root, "HEAD", files=["data.json"])
        self.assertEqual([x["path"] for x in found], ["data.json"])
        self.assertTrue((self.root / "user-work.py").exists())

    def test_commit_diff_handles_renames_and_deleted_files(self):
        self.call("mv", "data.json", "new name.json")
        self.call("commit", "-qm", "rename")
        found = dev.discover_changes(self.root, "HEAD~1")
        self.assertEqual(found[0]["old_path"], "data.json")
        self.assertEqual(found[0]["path"], "new name.json")
        (self.root / "new name.json").unlink()
        self.assertEqual(dev.discover_changes(self.root, "HEAD", working_tree=True)[0]["status"], "D")

    def test_execution_cannot_modify_source_data_through_cwd(self):
        before = (self.root / "data.json").read_bytes()
        target = Path(self.temp.name) / "isolated"
        target.mkdir()
        dev.snapshot(self.root, target, "HEAD", False, None)
        result = dev.command_check({"id": "writer-test", "argv": ["{python}", "-c",
                                   "from pathlib import Path; Path('data.json').write_text('changed by test')"]},
                                   target, Path(self.temp.name) / "logs", None)
        self.assertEqual(result["status"], "passed")
        self.assertEqual((self.root / "data.json").read_bytes(), before)
        self.assertNotEqual((target / "data.json").read_bytes(), before)
        self.assertFalse((target / ".git").exists())

    def test_focused_working_snapshot_excludes_unrelated_untracked_files(self):
        (self.root / "private.txt").write_text("unrelated private user content")
        (self.root / "editable-source.py").write_text("unrelated_user_work = True\n")
        (self.root / "selected.py").write_text("selected_check = True\n")
        (self.root / "data.json").write_text('{"tracked_working_change": true}\n')
        target = Path(self.temp.name) / "focused"
        target.mkdir()
        dev.snapshot(self.root, target, "HEAD", True, ["selected.py"])
        self.assertFalse((target / "private.txt").exists())
        self.assertFalse((target / "editable-source.py").exists())
        self.assertEqual((target / "selected.py").read_text(), "selected_check = True\n")
        self.assertEqual(json.loads((target / "data.json").read_text()), {"tracked_working_change": True})
        self.assertEqual((self.root / "private.txt").read_text(), "unrelated private user content")

    def test_committed_snapshot_ignores_uncommitted_source_edits(self):
        (self.root / "data.json").write_text("broken work in progress")
        target = Path(self.temp.name) / "isolated"
        target.mkdir()
        dev.snapshot(self.root, target, "HEAD", False, None)
        self.assertEqual(json.loads((target / "data.json").read_text()), {"original": True})

    def test_cli_ignores_uncommitted_routes_and_keeps_committed_failure(self):
        (self.root / ".github").mkdir()
        config = {"version": 1, "documentation": [], "checks": {
            "behavior": {"argv": ["{python}", "-m", "unittest", "discover", "-s", "tests", "-v"]}},
            "routes": [{"patterns": ["program.py"], "checks": ["behavior"]}]}
        (self.root / dev.CONFIG).write_text(json.dumps(config))
        (self.root / "tests").mkdir()
        (self.root / "program.py").write_text("def double(value):\n    return value * 2\n")
        (self.root / "tests/test_program.py").write_text(
            "import unittest\nfrom program import double\n"
            "class BehaviorTests(unittest.TestCase):\n"
            "    def test_double(self):\n        self.assertEqual(double(21), 42)\n")
        self.call("add", ".github", "program.py", "tests")
        self.call("commit", "-qm", "covered program")
        (self.root / "program.py").write_text("def double(value):\n    return value * 3\n")
        self.call("add", "program.py")
        self.call("commit", "-qm", "regression")
        committed_configuration = (self.root / dev.CONFIG).read_bytes()
        # A local route which would report a false success must not be used for
        # a report attesting the immutable HEAD commit.
        config["checks"]["behavior"]["argv"] = ["{python}", "-c", "pass"]
        (self.root / dev.CONFIG).write_text(json.dumps(config))
        before_status = self.call("status", "--porcelain")
        report = Path(self.temp.name) / "evidence/report.json"
        result = subprocess.run([sys.executable, str(ROOT / "scripts/dev_check.py"), "--base", "HEAD~1",
                                 "--check", "--output", str(report)], cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        saved = json.loads(report.read_text())
        self.assertEqual(saved["scope"], "commit_diff")
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["configuration_sha256"], hashlib.sha256(committed_configuration).hexdigest())
        self.assertEqual(saved["configuration_source"], "commit:" + saved["head"] + ":" + dev.CONFIG)
        behavior = next(x for x in saved["selected"] if x["id"] == "behavior")
        self.assertEqual(behavior["exit_code"], 1)
        self.assertIn("63 != 42", behavior["output_tail"])
        self.assertEqual(self.call("status", "--porcelain"), before_status)

    def test_commit_scope_never_falls_back_when_configuration_missing_in_head(self):
        (self.root / ".github").mkdir()
        (self.root / dev.CONFIG).write_text(json.dumps(fixture_config()))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/dev_check.py"), "--base", "HEAD"],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stderr)["status"], "error")
        self.assertIn(dev.CONFIG, json.loads(result.stderr)["error"])
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
