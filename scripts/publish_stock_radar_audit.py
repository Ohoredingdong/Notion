"""Recompute the displayed accuracy audit on each latest-main publication attempt."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import tempfile
import time
from audit_stock_radar_accuracy import report

OUTPUT = 'stock-radar-accuracy-audit.json'


def git(root, *args, check=True):
    return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=check)


def publish(root=Path('.'), attempts=6):
    root = Path(root).resolve()
    for attempt in range(attempts):
        git(root, 'fetch', 'origin', 'main')
        with tempfile.TemporaryDirectory(prefix='radar-accuracy-publish-') as temporary:
            work = Path(temporary) / 'work'
            git(root, 'worktree', 'add', '--detach', str(work), 'origin/main')
            try:
                # Recompute after every race; rebasing a stale derived report
                # would attach the old forecast's audit to a newer forecast.
                audit = report(work)
                if not audit['data_integrity']['check_passed']:
                    raise RuntimeError('accuracy_source_integrity_failed: ' + '; '.join(audit['data_integrity']['errors']))
                wire = json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
                (work / OUTPUT).write_text(wire)
                git(work, 'add', '--', OUTPUT)
                if git(work, 'diff', '--cached', '--quiet', check=False).returncode == 0:
                    (root / OUTPUT).write_text(wire)
                    print('Accuracy audit already matches current source snapshots.')
                    return None
                git(work, 'config', 'user.name', 'github-actions[bot]')
                git(work, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
                git(work, 'commit', '-m', 'audit: publish source-aligned radar accuracy report')
                if git(work, 'push', 'origin', 'HEAD:main', check=False).returncode == 0:
                    sha = git(work, 'rev-parse', 'HEAD').stdout.strip()
                    (root / OUTPUT).write_text(wire)
                    print('Published source-aligned accuracy audit:', sha)
                    return sha
            finally:
                git(root, 'worktree', 'remove', '--force', str(work), check=False)
        if attempt + 1 < attempts:
            time.sleep(min(10, attempt + 1))
    raise RuntimeError('accuracy_publication_race; latest main preserved, recollect on next run')


if __name__ == '__main__':
    publish()
