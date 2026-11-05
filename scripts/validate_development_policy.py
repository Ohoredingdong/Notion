"""Read-only protection of the existing production automation and new CI boundary.

The pinned contract intentionally protects raw production workflow source. It is
not a branch-protection setting and does not disable or dispatch any workflow.
Deliberate changes to financial automation require a reviewed contract update.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


def sha(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


def section(body: str, key: str, indent: int = 0) -> str:
    lines = body.splitlines()
    start = next((i for i, line in enumerate(lines) if line == ' ' * indent + key + ':'), None)
    if start is None:
        return ''
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() and not lines[i].lstrip().startswith('#')
                and len(lines[i]) - len(lines[i].lstrip()) <= indent), len(lines))
    return '\n'.join(lines[start:end]) + '\n'


def validate(root: Path) -> list[str]:
    failures = []
    contract = json.loads((root / 'config/automation-contract.json').read_text())
    exceptions = contract.get('reviewed_read_only_changes', {})
    for name, baseline in contract['workflows'].items():
        path = root / name
        if not path.is_file() or path.is_symlink():
            failures.append('Missing or redirected production workflow: ' + name)
            continue
        text = path.read_text()
        for key, field in [('on', 'trigger_block'), ('permissions', 'permissions_block'),
                           ('concurrency', 'concurrency_block')]:
            if section(text, key) != baseline[field]:
                failures.append(f'Production {key} changed without contract review: {name}')
        if name not in exceptions:
            if sha(text) != baseline['sha256']:
                failures.append('Production workflow body changed without contract review: ' + name)
        else:
            for job, expected in exceptions[name]['preserved_jobs'].items():
                if sha(section(text, job, 2)) != expected:
                    failures.append(f'Production writer job changed: {name}:{job}')
    for name in ['development-checks.yml', 'prepare-release-candidate.yml']:
        path = root / '.github/workflows' / name
        if not path.is_file():
            failures.append('Missing development workflow: ' + name)
            continue
        text = path.read_text()
        permissions = section(text, 'permissions')
        permission_lines = '\n'.join(line for line in permissions.splitlines()
                                     if line.strip() and not line.lstrip().startswith('#'))
        if permission_lines != 'permissions:\n  contents: read':
            failures.append('Development workflow must have contents:read only: ' + name)
        if re.search(r'^[ \t]+[\w-]+:\s*write\b', text, re.M) or re.search(r'^[ \t]+permissions:', text, re.M):
            failures.append('Development workflow must not acquire write permissions: ' + name)
        for forbidden in ['pull_request_target:', 'actions/deploy-pages@', 'continue-on-error:']:
            if forbidden in text:
                failures.append(f'Unsafe developer CI setting {forbidden}: {name}')
        if text.count('persist-credentials: false') < text.count('uses: actions/checkout@'):
            failures.append('Every development checkout must discard credentials: ' + name)
    return failures
