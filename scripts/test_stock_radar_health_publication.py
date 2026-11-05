"""Real local-git races and deterministic health-policy regression controls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import publish_stock_radar_health as publisher
from test_stock_data_pipeline import NOW, SCRIPTS, clock, health, health_fixture, write


class HealthPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote, self.local, self.writer = (self.root / name for name in ("remote.git", "local", "writer"))
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(self.remote), str(self.local)], check=True, capture_output=True)
        self.git(self.local, "checkout", "-b", "main")
        self.configure(self.local)
        health_fixture(self.local)
        (self.local / "stock-value-radar.html").write_text("<html></html>\n")
        (self.local / "scripts").mkdir()
        for name in publisher.CONTROL_INPUTS:
            if name.startswith("scripts/"):
                shutil.copyfile(SCRIPTS.parent / name, self.local / name)
        self.old = health.inspect(self.local, NOW, clock)
        self.old["checked_at"] = "2026-11-05T09:50:00+00:00"
        write(self.local, publisher.OUTPUT, self.old)
        self.commit_push(self.local, "initial source")
        subprocess.run(["git", "clone", "--branch", "main", str(self.remote), str(self.writer)], check=True, capture_output=True)
        self.configure(self.writer)
        self.initial = (self.local / publisher.OUTPUT).read_bytes()
        self.inspections = []

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def git(root, *args, check=True):
        return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=check)

    def configure(self, root):
        self.git(root, "config", "user.name", "Health regression fixture")
        self.git(root, "config", "user.email", "fixture@example.invalid")

    def commit_push(self, root, message):
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", message)
        self.git(root, "push", "origin", "HEAD:main")
        return self.git(root, "rev-parse", "HEAD").stdout.strip()

    def inspect(self, work):
        result = health.inspect(work, NOW, clock)
        self.inspections.append(result)
        write(work, publisher.OUTPUT, result)

    def remote_report(self):
        wire = self.git(self.remote, "show", "main:" + publisher.OUTPUT).stdout
        return json.loads(wire), wire.encode()

    def publish(self, **kwargs):
        with patch.object(publisher, "run_monitor", side_effect=self.inspect), patch.object(publisher.time, "sleep"), patch("builtins.print"):
            return publisher.publish(self.local, **kwargs)

    def test_old_checkout_error_is_recomputed_against_current_main(self):
        audit = json.loads((self.local / "stock-radar-accuracy-audit.json").read_text())
        audit["source"]["market_generated_at"] = "old"
        write(self.local, "stock-radar-accuracy-audit.json", audit)
        write(self.local, publisher.OUTPUT, health.inspect(self.local, NOW, clock))
        self.assertTrue(json.loads((self.local / publisher.OUTPUT).read_text())["issues"])
        base = self.git(self.writer, "rev-parse", "HEAD").stdout.strip()
        commit = self.publish()
        report, remote_wire = self.remote_report()
        self.assertFalse(report["issues"])
        self.assertEqual(report["source_snapshot"]["commit"], base)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), remote_wire)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout.strip(), commit)

    def test_actual_current_error_is_published_without_weakening_policy(self):
        audit = json.loads((self.writer / "stock-radar-accuracy-audit.json").read_text())
        audit["data_integrity"]["check_passed"] = False
        write(self.writer, "stock-radar-accuracy-audit.json", audit)
        self.old["consecutive_failures"] = 1
        write(self.writer, publisher.OUTPUT, self.old)
        self.commit_push(self.writer, "current broken audit")
        self.publish()
        report, wire = self.remote_report()
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["consecutive_failures"], 2)
        self.assertTrue(report["notification_required"])
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), wire)

    def test_push_race_rechecks_same_timestamp_changed_audit_bytes(self):
        audit = json.loads((self.writer / "stock-radar-accuracy-audit.json").read_text())
        audit["data_integrity"]["check_passed"] = False
        write(self.writer, "stock-radar-accuracy-audit.json", audit)
        self.commit_push(self.writer, "temporary audit error")
        original_git = publisher.git
        raced = []
        def racing_git(root, *args, **kwargs):
            if args[:1] == ("push",) and not raced:
                audit["data_integrity"]["check_passed"] = True
                write(self.writer, "stock-radar-accuracy-audit.json", audit)
                raced.append(self.commit_push(self.writer, "correct audit without timestamp change"))
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=racing_git):
            self.publish(attempts=2)
        report, _ = self.remote_report()
        self.assertEqual(len(self.inspections), 2)
        self.assertTrue(self.inspections[0]["issues"])
        self.assertFalse(report["issues"])
        self.assertEqual(report["source_snapshot"]["commit"], raced[0])
        audit_bytes = (self.writer / "stock-radar-accuracy-audit.json").read_bytes()
        self.assertEqual(report["source_snapshot"]["inputs"]["stock-radar-accuracy-audit.json"]["sha256"], hashlib.sha256(audit_bytes).hexdigest())

    def test_retry_uses_latest_previous_health_counter_once(self):
        (self.writer / "news-link-data.json").unlink()
        self.commit_push(self.writer, "missing required news")
        original_git = publisher.git
        previous = []
        def racing_git(root, *args, **kwargs):
            if args[:1] == ("push",) and not previous:
                updated = {**self.old, "consecutive_failures": 6}
                write(self.writer, publisher.OUTPUT, updated)
                previous.append((self.writer / publisher.OUTPUT).read_bytes())
                self.commit_push(self.writer, "another completed health observation")
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=racing_git):
            self.publish(attempts=2)
        report, _ = self.remote_report()
        self.assertEqual(report["consecutive_failures"], 7)
        self.assertEqual(report["source_snapshot"]["previous_health_sha256"], hashlib.sha256(previous[0]).hexdigest())

    def test_missing_and_invalid_inputs_are_recorded_without_hiding_errors(self):
        (self.writer / "news-link-data.json").unlink()
        (self.writer / "market-events-data.json").write_bytes(b"{invalid-json")
        (self.writer / "stock-value-radar.html").write_text('<script src="assets/stock-catalog-ui.js"></script>')
        self.commit_push(self.writer, "missing and invalid required feeds")
        self.publish()
        report, _ = self.remote_report()
        inputs = report["source_snapshot"]["inputs"]
        self.assertEqual(inputs["news-link-data.json"], {"exists": False, "sha256": None})
        self.assertEqual(inputs["market-events-data.json"], {"exists": True, "sha256": hashlib.sha256(b"{invalid-json").hexdigest()})
        self.assertTrue(set(health.FILES.values()) | set(health.EXTENDED.values()) | set(publisher.CONTROL_INPUTS) <= set(inputs))
        self.assertEqual(report["status"], "error")

    def test_latest_monitor_code_executes_in_worktree_not_old_checkout(self):
        (self.local / publisher.MONITOR).write_text("raise RuntimeError('old checkout code must not run')\n")
        # Execute the real monitor in the fetched worktree. A missing local
        # calendar package is itself reported as a health error, not hidden.
        with patch("builtins.print"):
            publisher.publish(self.local)
        report, wire = self.remote_report()
        self.assertEqual(report["version"], "canonical-radar-health-v2")
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), wire)
        self.assertIn("old checkout code", (self.local / publisher.MONITOR).read_text())

    def test_changed_input_during_inspection_is_rejected(self):
        before = self.git(self.remote, "rev-parse", "main").stdout
        def mutating_inspection(work):
            self.inspect(work)
            (work / "stock-radar-accuracy-audit.json").write_text("{}")
        with patch.object(publisher, "run_monitor", side_effect=mutating_inspection):
            with self.assertRaisesRegex(RuntimeError, "health_input_changed_during_inspection"):
                publisher.publish(self.local)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, before)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_no_fresh_monitor_output_never_copies_prior_report_as_success(self):
        with patch.object(publisher, "run_monitor"):
            with self.assertRaisesRegex(RuntimeError, "health_inspection_did_not_refresh_report"):
                publisher.publish(self.local)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_unchanged_staging_is_not_reported_as_success(self):
        original_git = publisher.git
        def no_diff(root, *args, **kwargs):
            if args == ("diff", "--cached", "--quiet"):
                return SimpleNamespace(returncode=0)
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=no_diff):
            with self.assertRaisesRegex(RuntimeError, "health_publication_unchanged"):
                self.publish()
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_push_failure_and_retry_exhaustion_leave_local_alert_report_untouched(self):
        before = self.git(self.remote, "rev-parse", "main").stdout
        original_git = publisher.git
        def denied_push(root, *args, **kwargs):
            if args[:1] == ("push",):
                return SimpleNamespace(returncode=1)
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=denied_push):
            with self.assertRaisesRegex(RuntimeError, "health_publication_race"):
                self.publish(attempts=2)
        self.assertEqual(len(self.inspections), 2)
        self.assertEqual(self.git(self.remote, "rev-parse", "main").stdout, before)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_monitor_exception_never_reuses_prior_report(self):
        with patch.object(publisher, "run_monitor", side_effect=RuntimeError("inspection failed")):
            with self.assertRaisesRegex(RuntimeError, "inspection failed"):
                publisher.publish(self.local)
        self.assertEqual((self.local / publisher.OUTPUT).read_bytes(), self.initial)

    def test_workflow_uses_published_report_and_refreshes_after_accuracy_converges(self):
        source = (SCRIPTS.parent / ".github/workflows/monitor-stock-value-radar.yml").read_text()
        self.assertIn("'Audit Stock Radar Accuracy'", source)
        self.assertIn("python scripts/publish_stock_radar_health.py", source)
        self.assertIn("test_stock_radar_health_publication.py", source)
        self.assertNotIn("python scripts/publish_widget_data.py", source)
        self.assertNotIn("run: python scripts/monitor-stock-value-radar.py", source)

    def test_pull_request_runs_read_only_regressions_without_publication_or_alerts(self):
        source = (SCRIPTS.parent / ".github/workflows/monitor-stock-value-radar.yml").read_text()
        self.assertIn("  pull_request:\n", source)
        self.assertIn("format('monitor-stock-radar-pr-{0}', github.event.pull_request.number)", source)
        regression = re.search(r"(?ms)^  publication-regression:\n(.*?)(?=^  monitor:)", source).group(1)
        self.assertIn("if: github.event_name == 'pull_request'", regression)
        self.assertIn("permissions:\n      contents: read", regression)
        self.assertIn("test_stock_radar_health_publication.py", regression)
        self.assertNotIn("python scripts/publish_stock_radar_health.py", regression)
        self.assertNotIn("gh issue", regression)
        monitor = source.split("\n  monitor:\n", 1)[1]
        self.assertIn("if: github.event_name != 'pull_request' &&", monitor)


if __name__ == "__main__":
    unittest.main()
