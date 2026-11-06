"""Regression checks for latest-code audits and truthful failure artifacts."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.publish_stock_radar_audit import worktree_report


class WorktreeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.work = self.base/'selected-main'
        self.root = self.base/'old-checkout'
        (self.work/'scripts').mkdir(parents=True)
        (self.root/'scripts').mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(self.work)], check=True)
        subprocess.run(['git', '-c', 'user.name=Audit Test', '-c', 'user.email=audit-test@example.test',
                        'commit', '-q', '--allow-empty', '-m', 'selected source'], cwd=self.work, check=True)
        self.output = 'report.json'
        (self.root/self.output).write_text('{"status":"old_success"}')
        (self.work/self.output).write_text('{"status":"tracked_old_success"}')

    def tearDown(self):
        self.temp.cleanup()

    def test_runs_selected_worktree_code_and_replaces_old_artifact(self):
        (self.root/'scripts'/'audit.py').write_text("raise RuntimeError('old source must not execute')\n")
        (self.work/'scripts'/'audit.py').write_text("from pathlib import Path\nPath('report.json').write_text('{\"status\":\"selected_source\"}')\n")
        result = worktree_report(self.work, self.root, 'audit.py', self.output)
        self.assertEqual(result['status'], 'selected_source')
        self.assertEqual(json.loads((self.root/self.output).read_text()), result)

    def test_failed_audit_preserves_new_failure_evidence_without_old_success(self):
        (self.work/'scripts'/'audit.py').write_text("from pathlib import Path\nPath('report.json').write_text('{\"status\":\"failed\",\"errors\":[\"new failure\"]}')\nraise SystemExit(1)\n")
        with self.assertRaisesRegex(RuntimeError, 'audit_execution_failed'):
            worktree_report(self.work, self.root, 'audit.py', self.output)
        result = json.loads((self.root/self.output).read_text())
        self.assertEqual(result['errors'], ['new failure'])
        self.assertEqual(result['status'], 'failed')

    def test_crash_before_output_cannot_reuse_tracked_success(self):
        (self.work/'scripts'/'audit.py').write_text("raise RuntimeError('source unavailable')\n")
        with self.assertRaisesRegex(RuntimeError, 'audit_report_not_generated'):
            worktree_report(self.work, self.root, 'audit.py', self.output)
        result = json.loads((self.root/self.output).read_text())
        self.assertEqual(result['status'], 'audit_execution_failed')
        self.assertEqual(result['errors'][0]['issue'], 'audit_did_not_complete')
        self.assertTrue(result['source_commit'])


if __name__ == '__main__':
    unittest.main()
