#!/usr/bin/env python3
"""Select and run read-only development checks for this static widget repository.

No collectors, installers, publishers, merges or deployment commands are run.
--all means all configured checks, not every historical browser script. See the
report's coverage notes and DEVELOPMENT.md for external/device checks.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


SCHEMA_VERSION = 1
ROOT = Path(__file__).resolve().parent.parent
RADAR_JS_TESTS = [
    'scripts/test_stock_forecast_ui.cjs', 'scripts/test_stock_forecast_wiring.cjs',
    'scripts/test_stock_event_ui.cjs', 'scripts/test_stock_evidence_review.cjs',
    'scripts/stock_autopilot_recovery.cjs',
]
CORE_FILES = {
    'AGENTS.md', '.gitignore', 'package.json', 'package-lock.json', 'requirements-dev.in',
    'requirements-dev.txt', 'scripts/dev_check.py', 'scripts/setup_dev.sh',
    'scripts/validate_repository.py', 'scripts/validate_development_policy.py',
    'scripts/prepare_release.py', 'scripts/open_development_pr.py',
    'scripts/install_actionlint.sh',
}
CORE_TESTS = ('test_dev_', 'test_development_', 'test_release_')


def git(root: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          text=True, capture_output=True).stdout


def tracked_paths(root: Path) -> list[str]:
    return sorted(p for p in git(root, 'ls-files', '-z').split('\0') if p)


def untracked_paths(root: Path) -> list[str]:
    return sorted(p for p in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0') if p)


def snapshot(root: Path, include_untracked=False) -> dict[str, str | None]:
    result = {}
    names = tracked_paths(root)
    if include_untracked:
        names = sorted(set(names + untracked_paths(root)))
    for name in names:
        path = root / name
        if path.is_symlink():
            result[name] = 'symlink:' + os.readlink(path)
        elif path.is_file():
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            result[name] = None
    return result


def changed_paths(root: Path, base: str | None) -> tuple[str, list[str]]:
    base = base or 'origin/main'
    # --no-renames intentionally includes both old and new paths. Deleted
    # files must still select the feature they used to belong to.
    revision = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').strip()
    merge = git(root, 'merge-base', revision, 'HEAD').strip()
    changes = git(root, 'diff', '--no-renames', '--name-only', '-z', merge, '--').split('\0')
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')
    return merge, sorted(set(filter(None, changes + untracked)))


def classify(name: str) -> str:
    path = Path(name)
    if name in CORE_FILES or name.startswith(('.github/', '.agents/', 'config/')):
        return 'infra'
    if path.name.startswith(CORE_TESTS):
        return 'infra'
    if name.startswith('services/toss-live/') or name.startswith('toss-live'):
        return 'toss'
    if name.startswith('use-me-first') or name.startswith('tests/fridge'):
        return 'fridge'
    if name.startswith(('auction-study', 'tests/auction', 'scripts/test_auction')):
        return 'auction'
    if name.startswith(('stock-', 'assets/stock-', 'scripts/stock_', 'scripts/test_stock_',
                        'scripts/update_stock_', 'scripts/build_stock_', 'scripts/publish_stock_',
                        'scripts/audit_stock_', 'scripts/install_stock_', 'scripts/refresh_stock_',
                        'scripts/curate_stock_', 'scripts/discover_stock_', 'tests/stock-')):
        return 'data' if path.suffix in ('.json', '.jsonl') else 'radar'
    if path.suffix in ('.json', '.jsonl'):
        return 'data'
    if name.startswith(('scripts/update-', 'scripts/update_', 'scripts/run_',
                        'scripts/market_', 'scripts/test_market_', 'scripts/test_widget_',
                        'scripts/publish_widget_data')):
        return 'market'
    if name.startswith(('docs/', 'designs/')) or path.suffix.lower() in (
            '.md', '.png', '.jpg', '.svg', '.webp', '.avif', '.txt'):
        return 'docs'
    return 'unmapped'


def unit_modules(root: Path, families: set[str]) -> list[str]:
    result = []
    for path in sorted((root / 'scripts').glob('test_*.py')):
        tree = ast.parse(path.read_bytes(), filename=str(path))
        # Do not import top-level historical browser scripts during discovery.
        # Existing unit files declare unittest.TestCase directly.
        has_case = any(isinstance(node, ast.ClassDef) and any(
            isinstance(base, ast.Attribute) and base.attr == 'TestCase'
            or isinstance(base, ast.Name) and base.id == 'TestCase'
            for base in node.bases) for node in ast.walk(tree))
        if not has_case:
            continue
        family = classify(path.relative_to(root).as_posix())
        if 'all' in families or family in families or family == 'infra':
            result.append('scripts.' + path.stem)
    return result


def build_plan(root: Path, *, all_checks=False, suite=None, base=None, files=None,
               output=None, browser_executable=None) -> dict:
    """Side-effect-free, stdlib-only plan; also used by the release guard."""
    root = Path(root).resolve()
    head = git(root, 'rev-parse', 'HEAD').strip()
    if base and re.fullmatch(r'0{40}', base):
        all_checks = True
    merge = None
    if files is not None:
        changed = sorted(set(files))
    elif all_checks or suite:
        changed = []
    else:
        merge, changed = changed_paths(root, base)
    selected = {classify(p) for p in changed}
    if suite:
        selected.add(suite)
    full = all_checks or 'infra' in selected or 'unmapped' in selected
    families = {'all'} if full else selected
    output = Path(output or (Path(tempfile.gettempdir()) / 'notion-check')).resolve()
    paths = sorted(set(tracked_paths(root) + untracked_paths(root) + [p for p in changed if (root / p).is_file()]))
    # Global JSON parse is inexpensive and catches broken data unrelated to
    # source spelling. It never replaces provider freshness/official audits.
    code_paths = paths if full or suite else changed
    checks = [{'id': 'repository-policy', 'command': [sys.executable, str(root / 'scripts/dev_check.py'),
                                                     '--internal', 'policy']}]
    if full:
        checks.append({'id': 'workflow-lint', 'command': [shutil.which('actionlint') or 'actionlint',
                                                        '-oneline', '-shellcheck=', '-pyflakes=']})
    modules = unit_modules(root, families) if full or selected.intersection({'radar', 'market'}) else []
    if modules:
        checks.append({'id': 'python-unit', 'command': [sys.executable, '-m', 'unittest', *modules, '-v'],
                       'require_count': 'python'})
    if full or 'toss' in selected:
        checks.append({'id': 'service-unit', 'command': [sys.executable, '-m', 'unittest', 'discover',
                       '-s', str(root / 'services/toss-live'), '-p', 'test_*.py', '-v'], 'require_count': 'python'})
    node_files = []
    for path in sorted((root / 'tests').glob('*.test.cjs')):
        family = classify(path.relative_to(root).as_posix())
        if full or family in selected:
            node_files.append(str(path))
    if node_files:
        checks.append({'id': 'node-unit', 'command': ['node', '--test', *node_files], 'require_count': 'node'})
    radar = full or 'radar' in selected
    if radar:
        checks.append({'id': 'radar-js-unit', 'command': ['node', '--test', *[str(root / n) for n in RADAR_JS_TESTS]],
                       'require_count': 'node'})
        command = [sys.executable, str(root / 'scripts/test_stock_radar_canonical_browser.py'),
                   '--root', str(root), '--output', str(output / 'radar-browser')]
        browser_executable = browser_executable or os.environ.get('NOTION_BROWSER_EXECUTABLE')
        if browser_executable:
            command += ['--browser-executable', str(browser_executable)]
        checks.append({'id': 'radar-browser', 'command': command, 'require_browser_report': True,
                       'browser_report': str(output / 'radar-browser/results.json'), 'minimum_cases': 7})
        for ident, program, engine in [
            ('radar-flow-browser', 'scripts/test_stock_radar_flow_browser.py', sys.executable),
            ('radar-entry-browser', 'tests/stock-entry-browser.cjs', 'node'),
            ('radar-advanced-browser', 'scripts/test_stock_decision_browser.py', sys.executable),
        ]:
            target = output / ident
            extra_command = [engine, str(root / program), '--root', str(root), '--output', str(target)]
            if browser_executable:
                extra_command += ['--browser-executable', str(browser_executable)]
            checks.append({'id': ident, 'command': extra_command, 'require_browser_report': True,
                           'browser_report': str(target / 'results.json'),
                           'minimum_cases': 2 if ident == 'radar-entry-browser' else 1})
    checks += [
        {'id': 'syntax', 'command': [sys.executable, str(root / 'scripts/validate_repository.py'), '--root', str(root),
          '--kind', 'syntax', '--files-json', str(output / 'syntax-files.json')]},
        {'id': 'data-integrity', 'command': [sys.executable, str(root / 'scripts/validate_repository.py'), '--root', str(root),
          '--kind', 'data', '--files-json', str(output / 'data-files.json')]},
    ]
    return {'schema_version': SCHEMA_VERSION, 'head_sha': head,
            'mode': 'all' if full else 'suite:' + suite if suite else 'related',
            'base_sha': merge, 'changed_files': changed, 'suites': sorted(families),
            'checks': checks, 'expected_check_ids': [c['id'] for c in checks],
            'syntax_files': code_paths, 'data_files': paths,
            'needs_browser': radar, 'needs_dependencies': bool(modules or node_files or full or 'toss' in selected),
            'coverage_gaps': [p for p in changed if classify(p) == 'unmapped'],
            'coverage_notes': [
                '--all covers all configured checks, not every historical browser script.',
                'Canonical radar desktop/mobile/local iframe checks do not prove actual Notion/Safari or live provider accuracy.',
                'Data-only checks preserve existing collector and workflow_run audit responsibilities.',
                'Unit fixtures and deliberate failures are test controls, not newly collected financial observations.',
            ]}


def now():
    return datetime.now(timezone.utc).isoformat()


def outside(root: Path, directory: Path):
    if directory.resolve() == root.resolve() or directory.resolve().is_relative_to(root.resolve()):
        raise ValueError('Logs, reports and screenshots must be outside the checkout.')


def execute(root: Path, plan: dict, output: Path) -> dict:
    outside(root, output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'syntax-files.json').write_text(json.dumps(plan['syntax_files']))
    (output / 'data-files.json').write_text(json.dumps(plan['data_files']))
    before = snapshot(root)
    input_before = snapshot(root, include_untracked=True)
    git_status = git(root, 'status', '--porcelain=v1', '--untracked-files=all')
    report = {**plan, 'started_at': now(), 'checks': [], 'snapshot': before,
              'working_tree_clean': not git_status, 'input_snapshot': input_before, 'status': 'failed'}
    def save_progress():
        done = {c['id'] for c in report['checks']}
        report['not_run_check_ids'] = [i for i in plan['expected_check_ids'] if i not in done]
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    save_progress()
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(root) + os.pathsep + str(root / 'scripts') + os.pathsep + environment.get('PYTHONPATH', '')
    environment['PYTHONPYCACHEPREFIX'] = str(output / 'pycache')
    environment.update({'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NO_COLOR': '1'})
    for check in plan['checks']:
        started = now()
        log_path = output / (check['id'] + '.log')
        status, code, detail, count = 'failed', 1, '', None
        try:
            if check.get('require_browser_report'):
                old_report = Path(check.get('browser_report', output / 'radar-browser/results.json'))
                if old_report.exists():
                    old_report.rename(old_report.with_name('results.previous.' + str(time.time_ns()) + '.json'))
            with log_path.open('w') as log:
                result = subprocess.run(check['command'], cwd=root, env=environment,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=900)
            code = result.returncode
            text = log_path.read_text(errors='replace')
            count = None
            summary = text
            if check.get('require_count') == 'python':
                matches = list(re.finditer(r'^Ran (\d+) tests?\b', text, re.M))
                match = matches[-1] if matches else None
                count = int(match[1]) if match else 0
                summary = text[match.end():] if match else text
            elif check.get('require_count') == 'node':
                matches = list(re.finditer(r'^(?:#|ℹ) tests (\d+)\b', text, re.M))
                match = matches[-1] if matches else None
                count = int(match[1]) if match else 0
                summary = text[match.end():] if match else text
            if count == 0:
                code, detail = 1, 'No executed tests were reported; zero-test success is rejected.'
            skipped = re.search(r'\bskipped=(\d+)', summary) if check.get('require_count') == 'python' else re.search(r'(?:#|ℹ) skipped (\d+)\b', summary)
            if check.get('require_count') and skipped and int(skipped[1]):
                code, detail = 1, 'A required unit suite skipped tests; report it as incomplete.'
            if check.get('require_browser_report') and code == 0:
                browser_file = Path(check.get('browser_report', output / 'radar-browser/results.json'))
                browser_data = json.loads(browser_file.read_text()) if browser_file.is_file() else {}
                samples = next((browser_data[k] for k in ['cases', 'profiles', 'checks']
                                if isinstance(browser_data.get(k), list) and browser_data[k]), [])
                if browser_data.get('passed') is not True or len(samples) < check.get('minimum_cases', 1):
                    code, detail = 1, 'Missing or unsuccessful actual browser report.'
                else:
                    count = len(samples)
            status = 'passed' if code == 0 else 'failed'
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            detail = str(error)
            with log_path.open('a') as log:
                log.write('\n' + detail + '\n')
        report['checks'].append({'id': check['id'], 'status': status, 'returncode': code,
                                 'started_at': started, 'ended_at': now(), 'log': str(log_path), 'detail': detail,
                                 'executed_tests': count})
        save_progress()
        print(check['id'] + ': ' + status, flush=True)
        if status == 'failed':
            print(log_path.read_text(errors='replace')[-7000:], file=sys.stderr, flush=True)
    after = snapshot(root)
    input_after = snapshot(root, include_untracked=True)
    current_status = git(root, 'status', '--porcelain=v1', '--untracked-files=all')
    report.update({'ended_at': now(), 'snapshot_unchanged': before == after,
                   'input_snapshot_unchanged': input_before == input_after,
                   'head_unchanged': git(root, 'rev-parse', 'HEAD').strip() == plan['head_sha'],
                   'git_status_unchanged': git_status == current_status, 'working_tree_clean': not current_status})
    if (all(c['status'] == 'passed' for c in report['checks']) and before == after
            and input_before == input_after and report['head_unchanged']
            and git_status == current_status and not plan['coverage_gaps']):
        report['status'] = 'passed'
    if plan['coverage_gaps']:
        report['failure_reason'] = 'Unmapped production changes need an explicit related test plan.'
    save_progress()
    print('Report: ' + str(output / 'report.json'), flush=True)
    return report


def internal_policy(root: Path) -> int:
    from validate_development_policy import validate
    errors = validate(root)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    # This existing guard protects the canonical UI against automated legacy installers.
    subprocess.run([sys.executable, str(root / 'scripts/test_stock_radar_publish_protection.py')],
                   check=True, cwd=root)
    print('Existing production automation and read-only CI policy preserved.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--base')
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--all', action='store_true')
    scope.add_argument('--suite', choices=['radar', 'market', 'fridge', 'auction', 'toss'])
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--output', type=Path, default=Path(tempfile.gettempdir()) / 'notion-check')
    parser.add_argument('--browser-executable')
    parser.add_argument('--internal', choices=['policy'], help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.internal:
            return internal_policy(root)
        plan = build_plan(root, all_checks=args.all, suite=args.suite, base=args.base,
                          output=args.output, browser_executable=args.browser_executable)
        if args.plan:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        return 0 if execute(root, plan, args.output.resolve())['status'] == 'passed' else 1
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
