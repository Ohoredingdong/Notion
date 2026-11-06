"""Recompute the displayed accuracy audit on each latest-main publication attempt."""
from __future__ import annotations
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile
import time
import sys
from audit_stock_radar_accuracy import report

OUTPUT = 'stock-radar-accuracy-audit.json'
DISPLAY_OUTPUT = 'stock-display-number-audit.json'


def git(root, *args, check=True):
    return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=check)


def worktree_report(work, root, script, output):
    """Use the selected main revision's code as well as its data.

    A failed calculation leaves fresh failure evidence in the workflow checkout,
    never an old successful report in an always-uploaded artifact.
    """
    target = work / output
    target.unlink(missing_ok=True)
    failure = {'status': 'audit_execution_failed', 'checked_at': datetime.now(timezone.utc).isoformat(),
               'source_commit': git(work, 'rev-parse', 'HEAD').stdout.strip(),
               'errors': [{'issue': 'audit_did_not_complete', 'script': script}]}
    (root / output).write_text(json.dumps(failure, ensure_ascii=False, indent=2)+'\n')
    result = subprocess.run([sys.executable, str(work/'scripts'/script)], cwd=work,
                            text=True, capture_output=True)
    if not target.is_file():
        raise RuntimeError('audit_report_not_generated:'+script)
    wire = target.read_text()
    (root / output).write_text(wire)
    data = json.loads(wire)
    if result.returncode != 0:
        raise RuntimeError('audit_execution_failed:'+script)
    return data


def publish(root=Path('.'), attempts=6, include_display_numbers=False):
    root = Path(root).resolve()
    for attempt in range(attempts):
        git(root, 'fetch', 'origin', 'main')
        with tempfile.TemporaryDirectory(prefix='radar-accuracy-publish-') as temporary:
            work = Path(temporary) / 'work'
            git(root, 'worktree', 'add', '--detach', str(work), 'origin/main')
            try:
                if include_display_numbers:
                    pending = {'status': 'audit_pending', 'checked_at': datetime.now(timezone.utc).isoformat(),
                               'source_commit': git(work, 'rev-parse', 'HEAD').stdout.strip(),
                               'errors': [{'issue': 'latest_source_audit_not_completed'}]}
                    for name in (OUTPUT, DISPLAY_OUTPUT):
                        (root/name).write_text(json.dumps(pending, ensure_ascii=False, indent=2)+'\n')
                # Recompute after every race; rebasing a stale derived report
                # would attach the old forecast's audit to a newer forecast.
                audit = (worktree_report(work, root, 'audit_stock_radar_accuracy.py', OUTPUT)
                         if include_display_numbers else report(work))
                if not audit['data_integrity']['check_passed']:
                    raise RuntimeError('accuracy_source_integrity_failed: ' + '; '.join(audit['data_integrity']['errors']))
                wire = json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
                outputs = {OUTPUT: wire}
                if include_display_numbers:
                    display = worktree_report(work, root, 'audit_stock_display_numbers.py', DISPLAY_OUTPUT)
                    if display['errors']:
                        raise RuntimeError('display_number_integrity_failed: ' + json.dumps(display['errors'][:10], ensure_ascii=False))
                    outputs[DISPLAY_OUTPUT] = json.dumps(display, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
                for name, body in outputs.items():
                    (work / name).write_text(body)
                git(work, 'add', '--', *outputs)
                if git(work, 'diff', '--cached', '--quiet', check=False).returncode == 0:
                    for name, body in outputs.items():
                        (root / name).write_text(body)
                    print('Accuracy audit already matches current source snapshots.')
                    return None
                git(work, 'config', 'user.name', 'github-actions[bot]')
                git(work, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
                git(work, 'commit', '-m', 'audit: publish source-aligned radar accuracy report')
                if git(work, 'push', 'origin', 'HEAD:main', check=False).returncode == 0:
                    sha = git(work, 'rev-parse', 'HEAD').stdout.strip()
                    for name, body in outputs.items():
                        (root / name).write_text(body)
                    print('Published source-aligned accuracy audit:', sha)
                    return sha
            finally:
                git(root, 'worktree', 'remove', '--force', str(work), check=False)
        if attempt + 1 < attempts:
            time.sleep(min(10, attempt + 1))
    raise RuntimeError('accuracy_publication_race; latest main preserved, recollect on next run')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-display-numbers', action='store_true')
    publish(include_display_numbers=parser.parse_args().include_display_numbers)
