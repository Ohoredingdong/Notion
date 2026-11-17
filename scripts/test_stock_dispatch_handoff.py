"""Offline delivery tests: no real credentials, network, or Actions dispatch."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
class DispatchTests(unittest.TestCase):
 def run_case(self, failures, target='stock-entry-plan.yml', token='fake-test-only'):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); log=p/'calls'; count=p/'count'
   (p/'gh').write_text('#!/bin/sh\necho "$*" >> "$LOG"\nn=$(cat "$COUNT" 2>/dev/null || echo 0)\nn=$((n+1)); echo "$n" > "$COUNT"\n[ "$n" -gt "$FAILURES" ]\n')
   (p/'sleep').write_text('#!/bin/sh\nexit 0\n')
   for name in ('gh','sleep'):(p/name).chmod(0o755)
   env={**os.environ,'PATH':d+':'+os.environ['PATH'],'GH_TOKEN':token,'GITHUB_REPOSITORY':'example/repo','LOG':str(log),'COUNT':str(count),'FAILURES':str(failures)}
   result=subprocess.run(['bash',str(ROOT/'scripts/dispatch_stock_handoff.sh'),target],env=env,capture_output=True,text=True)
   return result.returncode,log.read_text().splitlines() if log.exists() else []
 def test_success_once(self):
  code,calls=self.run_case(0);self.assertEqual(code,0);self.assertEqual(len(calls),1);self.assertIn('-f ref=main',calls[0])
 def test_transient_failure_retries(self):
  code,calls=self.run_case(2);self.assertEqual(code,0);self.assertEqual(len(calls),3)
 def test_exhausted_failures_fail_closed(self):
  code,calls=self.run_case(9);self.assertNotEqual(code,0);self.assertEqual(len(calls),3)
 def test_unapproved_target_never_dispatches(self):
  code,calls=self.run_case(0,'other.yml');self.assertNotEqual(code,0);self.assertEqual(calls,[])
 def test_missing_token_never_dispatches(self):
  code,calls=self.run_case(0,token='');self.assertNotEqual(code,0);self.assertEqual(calls,[])
 def test_no_automatic_cancellation_or_early_reading_audit(self):
  rec=(ROOT/'.github/workflows/stock-recommendations.yml').read_text()
  reading=(ROOT/'.github/workflows/stock-reading-depth.yml').read_text()
  entry=(ROOT/'.github/workflows/stock-entry-plan.yml').read_text()
  self.assertIn('cancel-in-progress: false',rec)
  self.assertNotIn('audit-stock-radar-accuracy.yml',reading)
  self.assertIn('runs-on: ubuntu-24.04',entry)
  self.assertIn('@playwright/test@1.56.0',entry)
 def test_ci_is_read_only_and_covers_helper_changes(self):
  workflow=(ROOT/'.github/workflows/test-stock-handoff-safety.yml').read_text()
  self.assertIn('contents: read',workflow)
  self.assertIn('persist-credentials: false',workflow)
  self.assertIn("'scripts/dispatch_stock_handoff.sh'",workflow)
  self.assertIn("'scripts/test_stock_dispatch_handoff.py'",workflow)
  self.assertIn('python -m unittest test_stock_dispatch_handoff test_stock_refresh_handoffs',workflow)
  for forbidden in ('actions: write','contents: write','secrets.','github.token','git push','gh api','workflow_run:'):
   self.assertNotIn(forbidden,workflow)
if __name__=='__main__':unittest.main()
