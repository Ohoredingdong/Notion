"""Publish only the completed extended snapshot, preserving concurrent main work."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

OUTPUT = 'stock-extended-direction-forecast.json'
DEPENDENCIES = (
    'stock-universe-catalog.json', 'scripts/run_stock_universe_forecasts.py',
    'scripts/stock_forecast_model.py', 'scripts/stock_forecast_sources.py',
    'scripts/audit_stock_forecast_independent.py',
    'scripts/publish_stock_universe_forecasts.py', '.github/workflows/stock-extended-coverage.yml',
)


def git(*args, cwd=None, check=True):
    return subprocess.run(['git', *args], cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('publication_timestamp_requires_timezone')
    return result


def source_lease(root, source, remote):
    if git('diff', '--quiet', source, remote, '--', *DEPENDENCIES, cwd=root, check=False).returncode:
        raise ValueError('full_universe_inputs_changed_during_collection')


def publish(root, source, branch, attempts=5):
    root = Path(root).resolve()
    if not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('source_commit_requires_exact_sha')
    if branch not in {'main', 'feat/radar-all-ai-20261106'}:
        raise ValueError('publication_branch_not_authorized')
    payload = (root/OUTPUT).read_bytes()
    document = json.loads(payload)
    if (document.get('version') != 'stock-extended-direction-v1' or
            document.get('generation_mode') != 'full_universe' or
            document.get('automatic_orders') is not False):
        raise ValueError('completed_full_universe_snapshot_required')
    coverage = document['coverage']
    if (document.get('run', {}).get('source_commit') != source or
            coverage['total'] != len(document['records']) or
            coverage['total'] != coverage['prediction']+coverage['failed']+coverage['not_attempted']):
        raise ValueError('incomplete_full_universe_snapshot')
    generated = instant(document['generated_at'])
    for attempt in range(attempts):
        git('fetch', 'origin', branch, cwd=root)
        remote = git('rev-parse', f'origin/{branch}', cwd=root).stdout.strip()
        source_lease(root, source, remote)
        old = git('show', f'{remote}:{OUTPUT}', cwd=root, check=False)
        if old.returncode == 0:
            old_document = json.loads(old.stdout)
            if old_document.get('generated_at') and instant(old_document['generated_at']) > generated:
                raise ValueError('refusing_to_replace_a_newer_forecast_snapshot')
            if old.stdout.encode() == payload:
                return {'published': False, 'commit': remote, 'coverage': coverage}
        with tempfile.TemporaryDirectory(prefix='radar-universe-publish-') as temp:
            work = Path(temp)/'checkout'
            git('worktree', 'add', '--detach', str(work), remote, cwd=root)
            try:
                (work/OUTPUT).write_bytes(payload)
                git('add', '--', OUTPUT, cwd=work)
                git('-c', 'user.name=github-actions[bot]', '-c',
                    'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                    'commit', '-m', 'research: generate AI direction analysis for the full verified universe', cwd=work)
                commit = git('rev-parse', 'HEAD', cwd=work).stdout.strip()
                pushed = git('push', 'origin', f'HEAD:refs/heads/{branch}', cwd=work, check=False)
                if pushed.returncode == 0:
                    return {'published': True, 'commit': commit, 'coverage': coverage}
                if attempt == attempts-1:
                    raise RuntimeError('publication_race_or_push_failed: '+pushed.stderr[-800:])
            finally:
                git('worktree', 'remove', '--force', str(work), cwd=root, check=False)
        time.sleep(2)
    raise RuntimeError('publication_attempts_exhausted')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    result = publish(args.root, args.source_commit, args.branch)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as target:
            target.write('published='+str(result['published']).lower()+'\n')
            target.write('commit='+result['commit']+'\n')
    print('FULL_UNIVERSE_PUBLICATION', json.dumps(result, ensure_ascii=False))
