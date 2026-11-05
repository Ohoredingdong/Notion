"""Read-only workflow policy checks; never invoke a collector, Git push or deployment.

The immutable audit inventory protects existing schedules, permissions, concurrency
and publisher commands while review-time checks and explicit chain guards change.
This is a repository check, not evidence that GitHub branch/Pages policy is active.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
import yaml


class StrictLoader(yaml.BaseLoader):
    pass


def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
CHAIN_GUARDS = {
    'verify-stock-official.yml': 'verify', 'update-stock-decisions.yml': 'refresh',
    'update-stock-opportunities.yml': 'refresh', 'stock-investment-cases.yml': 'cases',
    'stock-reading-depth.yml': 'reading', 'test-stock-decisions-ui.yml': 'browser',
}
CI = 'change-validation.yml'
RELEASE = 'reviewed-pages-release.yml'


def read_workflow(path):
    value = yaml.load(path.read_text(encoding='utf-8'), Loader=StrictLoader)
    if not isinstance(value, dict) or not isinstance(value.get('jobs'), dict):
        raise ValueError('workflow must contain jobs')
    if not isinstance(value.get('on'), dict):
        raise ValueError('workflow events must be an explicit mapping')
    return value


def runs(workflow):
    for job_id, job in workflow['jobs'].items():
        for step in job.get('steps', []):
            if isinstance(step, dict) and isinstance(step.get('run'), str):
                yield job_id, step, step['run']


def check(root):
    root = Path(root)
    errors, checks = [], []
    def require(condition, label):
        checks.append({'name': label, 'passed': bool(condition)})
        if not condition: errors.append(label)
    inventory_path = root / 'docs/development-workflow-inventory.json'
    try:
        inventory = json.loads(inventory_path.read_text())
        baseline = {Path(item['file']).name:item for item in inventory['workflows']}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'passed':False,'checks':[],'errors':[f'inventory unavailable: {error}']}
    workflows = {}
    for path in sorted((root / '.github/workflows').glob('*.y*ml')):
        try:
            workflows[path.name] = read_workflow(path)
            require(True, f'{path.name}: valid YAML without duplicate keys')
        except (OSError, ValueError, yaml.YAMLError) as error:
            require(False, f'{path.name}: invalid workflow: {error}')
    for filename, before in baseline.items():
        require(filename in workflows, f'{filename}: existing automation retained')
        if filename not in workflows: continue
        after = workflows[filename]
        if before.get('permissions', {}).get('contents') != 'write': continue
        require(after.get('permissions') == before.get('permissions'), f'{filename}: publisher permissions unchanged')
        require(after.get('concurrency') == before.get('concurrency'), f'{filename}: publisher concurrency unchanged')
        for event in ('schedule', 'workflow_run', 'workflow_dispatch'):
            require(after['on'].get(event) == before.get('events', {}).get(event), f'{filename}: {event} trigger retained')
        for old_job in before['jobs']:
            job = after['jobs'].get(old_job['id'])
            require(job is not None, f'{filename}/{old_job["id"]}: existing job retained')
            if job is None: continue
            # Compare the actual publication step, not a coincidental command in a comment.
            for command in old_job.get('publication_commands', []):
                step = next((s for s in job.get('steps', []) if s.get('name') == command['step']), None)
                require(step is not None and command['command'] in [line.strip() for line in str(step.get('run', '')).splitlines()]
                        and step.get('if') == command.get('if'),
                        f'{filename}/{old_job["id"]}: publication retained: {command["step"]}: {command["command"]}')
    for filename, job_id in CHAIN_GUARDS.items():
        expr = workflows.get(filename, {}).get('jobs', {}).get(job_id, {}).get('if', '')
        require("github.event_name != 'workflow_run'" in expr
                and "github.event.workflow_run.conclusion == 'success'" in expr
                and 'github.event.workflow_run.head_repository.full_name == github.repository' in expr,
                f'{filename}: failed or foreign predecessor cannot start chained work; independent recovery allowed')
    ci = workflows.get(CI, {})
    require(bool(ci), 'change validation workflow exists')
    if ci:
        require('pull_request' in ci['on'] and not (ci['on']['pull_request'] or {}).get('paths'),
                'PR validation always reports a check (no path-filter pending checks)')
        require('pull_request_target' not in ci['on'], 'PR code is never executed with pull_request_target privileges')
        require(ci.get('permissions') == {'contents':'read'}, 'change validation is read-only')
        require(ci.get('concurrency',{}).get('cancel-in-progress') == "${{ github.event_name != 'workflow_run' }}" and 'data-main' in ci.get('concurrency',{}).get('group',''), 'data observation is coalesced without starving an active check')
        all_runs = '\n'.join(command for _,_,command in runs(ci))
        require('dev_check.py' in all_runs and '--run' in all_runs, 'change validation executes the selected checks')
        require(not re.search(r'\bgit\s+(?:push|reset)\b|pages/builds|deploy-pages', all_runs), 'validation cannot publish or reset main')
        require(not any(job.get('continue-on-error') == 'true' or step.get('continue-on-error') == 'true'
                        for job in ci['jobs'].values() for step in job.get('steps', [])), 'validation failures are not converted to success')
    release = workflows.get(RELEASE, {})
    require(bool(release), 'manual release workflow exists')
    if release:
        require(set(release['on']) == {'workflow_dispatch'}, 'release has no automatic event trigger')
        source = (root / '.github/workflows' / RELEASE).read_text()
        require('release_gate.py' in source and 'authorize' in source and 'dry_run' in source,
                'release requires authorization gate and defaults to dry run')
        require(release.get('permissions') == {'contents':'read'}, 'release default token is read-only')
    try:
        policy = json.loads((root/'.github/release-policy.json').read_text())
        require(policy.get('enabled') is False, 'deployment activation remains disabled pending explicit owner review')
    except (OSError, ValueError):
        require(False, 'release activation policy is readable')
    return {'passed':not errors,'checks':checks,'errors':errors,
            'scope':'Repository policy only. GitHub settings, remote CI and production deployment are not verified.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=check(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'checks':len(result['checks']),'errors':result['errors']},ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__': sys.exit(main())
