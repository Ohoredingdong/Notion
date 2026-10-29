"""Merge only forecast-owned outputs on current main, without force-pushing.
The append-only ledger retains the first actual issue time for each prediction.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time

FILES = ['stock-direction-forecast.json', 'stock-forecast-ledger.jsonl',
         'stock-forecast-outcomes.jsonl', 'stock-forecast-deliveries.jsonl']
TAG = '<script src="./assets/stock-forecast.js?v=direction-forecast-1.0" defer></script>'


def git(root, *args, check=True):
    return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=check)


def merged_lines(old, new):
    result, seen = [], set()
    for line in (old+'\n'+new).splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        key = record.get('id') or record.get('verification_id')
        if not key:
            raise ValueError('ledger_record_missing_id')
        if key not in seen:
            seen.add(key)
            result.append(json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(',', ':')))
    return '\n'.join(result)+'\n' if result else ''


def publish(root=Path('.')):
    root = root.resolve()
    payload = {p: (root/p).read_text() for p in FILES}
    data = json.loads(payload[FILES[0]])
    for _ in range(8):
        git(root, 'fetch', 'origin', 'main')
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)/'work'
            git(root, 'worktree', 'add', '--detach', str(work), 'origin/main')
            try:
                remote = work/FILES[0]
                if remote.exists() and json.loads(remote.read_text())['generated_at'] > data['generated_at']:
                    raise RuntimeError('newer_forecast_already_published')
                for name, body in payload.items():
                    dest = work/name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if name.endswith('.jsonl'):
                        body = merged_lines(dest.read_text() if dest.exists() else '', body)
                    dest.write_text(body)
                for name in ['stock-value-radar.html', 'assets/stock-radar-v8.html']:
                    path = work/name
                    if not path.exists():
                        raise RuntimeError('existing_radar_template_missing')
                    html = path.read_text()
                    if 'assets/stock-forecast.js' not in html:
                        if '</head>' not in html:
                            raise RuntimeError('template_head_missing')
                        path.write_text(html.replace('</head>', TAG+'\n</head>', 1))
                git(work, 'config', 'user.name', 'github-actions[bot]')
                git(work, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
                git(work, 'add', '--', *FILES, 'stock-value-radar.html', 'assets/stock-radar-v8.html')
                if git(work, 'diff', '--cached', '--quiet', check=False).returncode == 0:
                    return
                git(work, 'commit', '-m', 'forecast: record prospective direction estimates and immutable outcomes')
                result = git(work, 'push', 'origin', 'HEAD:main', check=False)
                if result.returncode == 0:
                    print('Forecast publication committed', git(work, 'rev-parse', 'HEAD').stdout.strip())
                    return
            finally:
                git(root, 'worktree', 'remove', '--force', str(work), check=False)
        time.sleep(2)
    raise RuntimeError('publication_raced_other_updates; no existing source overwritten')


if __name__ == '__main__':
    publish()
