"""Routing, real failure propagation and data validation negative controls."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts import dev_check as dev
from scripts.validate_repository import data_errors
from scripts.validate_development_policy import validate


ROOT = Path(__file__).resolve().parent.parent


class SelectionTests(unittest.TestCase):
    def plan(self, *names):
        return dev.build_plan(ROOT, files=list(names))

    def test_data_update_keeps_light_validation_without_installing_browser(self):
        p = self.plan('stock-opportunity-data.json', 'stock-forecast-ledger.jsonl')
        self.assertEqual(p['expected_check_ids'], ['repository-policy', 'syntax', 'data-integrity'])
        self.assertFalse(p['needs_dependencies'])
        self.assertFalse(p['needs_browser'])

    def test_docs_still_validate_existing_automation_and_real_json(self):
        self.assertIn('repository-policy', self.plan('docs/change.md')['expected_check_ids'])
        self.assertFalse(self.plan('docs/change.md')['needs_browser'])

    def test_canonical_html_and_shared_js_cannot_skip_radar_checks(self):
        for name in ['stock-value-radar.html', 'assets/stock-radar-flow-v2.js', 'stock-radar-dashboard.html']:
            p = self.plan(name)
            self.assertIn('python-unit', p['expected_check_ids'])
            self.assertIn('radar-js-unit', p['expected_check_ids'])
            self.assertIn('radar-browser', p['expected_check_ids'])

    def test_rename_and_deletion_include_both_feature_families(self):
        p = self.plan('use-me-first-kitchen.js', 'assets/stock-radar-clean-bridge.js')
        self.assertEqual(set(p['suites']), {'fridge', 'radar'})
        node = next(c for c in p['checks'] if c['id'] == 'node-unit')
        self.assertTrue(any('fridge-ui.test.cjs' in word for word in node['command']))
        self.assertIn('radar-browser', self.plan('scripts/update_stock_decisions.py')['expected_check_ids'])

    def test_unmapped_production_changes_are_reported_instead_of_silent_success(self):
        p = self.plan('new-widget.html')
        self.assertEqual(p['coverage_gaps'], ['new-widget.html'])
        self.assertTrue(p['needs_browser'])

    def test_infrastructure_changes_select_every_configured_check(self):
        p = self.plan('.github/workflows/development-checks.yml')
        self.assertEqual(p['suites'], ['all'])
        self.assertEqual(p['mode'], 'all')
        self.assertIn('service-unit', p['expected_check_ids'])
        self.assertEqual(p['expected_check_ids'], [
            'repository-policy', 'workflow-lint', 'python-unit', 'service-unit',
            'node-unit', 'radar-js-unit', 'radar-browser', 'radar-flow-browser',
            'radar-entry-browser', 'radar-advanced-browser', 'syntax', 'data-integrity',
        ])

    def test_unit_discovery_never_imports_top_level_browser_programs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'scripts').mkdir()
            marker = root / 'unsafe-import-marker'
            (root / 'scripts/test_bad_browser.py').write_text(f'open({str(marker)!r}, "w").write("unsafe")\n')
            (root / 'scripts/test_good.py').write_text('import unittest\nclass Tests(unittest.TestCase):\n def test_real(self): pass\n')
            self.assertEqual(dev.unit_modules(root, {'all'}), ['scripts.test_good'])
            self.assertFalse(marker.exists())


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='notion-check-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        (self.root / 'existing.txt').write_text('original\n')
        subprocess.run(['git', 'init', '--quiet', str(self.root)], check=True)
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--quiet', '-m', 'fixture')
        self.output = self.root.parent / 'results'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def run_check(self, body, **extra):
        check = {'id': 'negative-control', 'command': [sys.executable, '-c', body], **extra}
        plan = {'checks': [check], 'syntax_files': [], 'data_files': [], 'coverage_gaps': [],
                'head_sha': self.git('rev-parse', 'HEAD').strip(), 'mode': 'all',
                'schema_version': 1, 'expected_check_ids': ['negative-control']}
        return dev.execute(self.root, plan, self.output)

    def test_nonzero_exit_is_never_reported_as_passed(self):
        report = self.run_check('raise SystemExit(7)')
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['checks'][0]['returncode'], 7)

    def test_zero_test_success_is_rejected(self):
        r = self.run_check('print("Ran 0 tests in 0.0s\\nOK")', require_count='python')
        self.assertEqual(r['status'], 'failed')
        self.assertIn('zero-test', r['checks'][0]['detail'])

    def test_skipped_required_cases_are_incomplete(self):
        r = self.run_check('print("Ran 3 tests in 0.0s\\nOK (skipped=1)")', require_count='python')
        self.assertEqual(r['status'], 'failed')

    def test_nested_negative_controls_do_not_replace_real_final_unit_summary(self):
        r = self.run_check('print("Ran 0 tests in 0.0s\\nOK (skipped=1)\\nRan 4 tests in 0.1s\\nOK")', require_count='python')
        self.assertEqual(r['status'], 'passed')

    def test_mutating_an_untracked_development_source_is_also_detected(self):
        (self.root / 'new-source.js').write_text('original')
        r = self.run_check('from pathlib import Path; Path("new-source.js").write_text("changed")')
        self.assertEqual(r['status'], 'failed')
        self.assertFalse(r['input_snapshot_unchanged'])

    def test_stale_browser_result_cannot_satisfy_new_run(self):
        old = self.output / 'radar-browser/results.json'
        old.parent.mkdir(parents=True)
        old.write_text('{"passed": true}')
        r = self.run_check('pass', require_browser_report=True)
        self.assertEqual(r['status'], 'failed')
        self.assertTrue(list(old.parent.glob('results.previous.*.json')))

    def test_a_passing_command_that_rewrites_source_still_fails(self):
        r = self.run_check('from pathlib import Path; Path("existing.txt").write_text("changed")')
        self.assertEqual(r['status'], 'failed')
        self.assertFalse(r['snapshot_unchanged'])

    def test_output_inside_checkout_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            dev.outside(self.root, self.root / 'test-results')


class DataAndAutomationTests(unittest.TestCase):
    def test_malformed_json_and_nonfinite_values_fail_without_repair(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = '[{"word":"existing"}'
            (root / 'words.json').write_text(original)
            (root / 'price.json').write_text('{"price":NaN}')
            self.assertEqual(len(data_errors(root, ['words.json', 'price.json'])), 2)
            self.assertEqual((root / 'words.json').read_text(), original)

    def policy_copy(self):
        temp = tempfile.TemporaryDirectory(prefix='notion-policy-test-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        paths = ['config/automation-contract.json']
        paths += list(json.loads((ROOT / paths[0]).read_text())['workflows'])
        paths += ['.github/workflows/development-checks.yml', '.github/workflows/prepare-release-candidate.yml']
        for name in paths:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        return root

    def test_current_production_schedule_and_writers_remain_intact(self):
        self.assertEqual(validate(self.policy_copy()), [])

    def test_changing_a_financial_writer_or_schedule_is_detected(self):
        root = self.policy_copy()
        path = root / '.github/workflows/update-commodities.yml'
        path.write_text(path.read_text().replace('cron:', 'disabled-cron:', 1))
        self.assertTrue(any('Production on' in e for e in validate(root)))

    def test_readonly_verify_fix_does_not_relax_chart_cache_writer(self):
        root = self.policy_copy()
        path = root / '.github/workflows/test-stock-neutral-ui.yml'
        path.write_text(path.read_text().replace('  verify:', '  verify:\n    # review-only test', 1))
        self.assertEqual(validate(root), [])
        path.write_text(path.read_text().replace('  display-cache:', '  changed-display-cache:', 1))
        self.assertTrue(any('writer job changed' in e for e in validate(root)))

    def test_ci_cannot_gain_write_permission_or_ignore_failures(self):
        for addition in ['\n    permissions: write-all\n', '\n    continue-on-error: ${{ always() }}\n']:
            with self.subTest(setting=addition):
                root = self.policy_copy()
                path = root / '.github/workflows/development-checks.yml'
                path.write_text(path.read_text() + addition)
                self.assertTrue(validate(root))


if __name__ == '__main__':
    unittest.main()
