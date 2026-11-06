"""Observe exact public bytes and the actual first-check clock; no human receipt."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
import urllib.request

BASE = 'https://ohoredingdong.github.io/Notion/'
FILES = ('stock-extended-direction-forecast.json', 'stock-universe-catalog.json',
         'stock-value-radar.html', 'assets/stock-radar-clean-bridge.js',
         'assets/stock-radar-flow-v2.js', 'assets/stock-catalog-ui.js')


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('public_timestamp_requires_timezone')
    return result


def get_public(name):
    request = urllib.request.Request(BASE+name+'?verify='+str(time.time_ns()),
                                     headers={'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read()


def verify(root=Path('.'), get=get_public, clock=None, commit=None):
    root = Path(root)
    clock = clock or (lambda: datetime.now(timezone.utc))
    expected = {}
    for name in FILES:
        expected[name] = (subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=root)
                          if commit else (root/name).read_bytes())
    doc = json.loads(expected[FILES[0]])
    catalog = json.loads(expected[FILES[1]])
    if (doc.get('generation_mode') != 'full_universe' or doc.get('automatic_orders') is not False
            or len(doc['records']) != len(catalog['items'])
            or doc['coverage']['total'] != len(catalog['items'])):
        raise ValueError('public_full_universe_contract_invalid')
    identities = {(r['country'], r['symbol']): r for r in catalog['items']}
    records = {(r.get('market'), r.get('catalog_symbol')): r for r in doc['records']}
    if len(records) != len(doc['records']) or records.keys() != identities.keys():
        raise ValueError('public_identity_set_mismatch')
    if doc.get('run', {}).get('catalog_sha256') != hashlib.sha256(expected[FILES[1]]).hexdigest():
        raise ValueError('public_catalogue_provenance_mismatch')
    for key, r in records.items():
        item = identities[key]
        if (r.get('identity_verified') is not True or r.get('catalog_name') != item['name']
                or r.get('catalog_exchange') != item['exchange']):
            raise ValueError('public_issuer_identity_mismatch')
        if r.get('status') == 'no_call':
            if r.get('probabilities') is not None or r.get('target') is not None or not r.get('reason'):
                raise ValueError('public_no_call_contains_prediction_or_lacks_reason')
            continue
        p = r.get('probabilities')
        if (r.get('status') != 'research_prediction' or not isinstance(p, dict)
                or set(p) != {'up', 'flat', 'down'}
                or any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in p.values())
                or abs(sum(p.values())-1) > 1e-6):
            raise ValueError('public_probabilities_invalid')
        if not (instant(r['observed_until']) <= instant(r['received_at']) <= instant(r['issued_at'])
                < instant(r['target']['start']) < instant(r['target']['end'])):
            raise ValueError('public_forecast_not_prospective')
    html = expected['stock-value-radar.html'].decode()
    if any(name not in html for name in FILES[3:]):
        raise ValueError('full_universe_ui_not_wired')
    for name in FILES:
        if get(name) != expected[name]:
            raise ValueError('public_bytes_mismatch:'+name)
    observed = clock()
    if observed.tzinfo is None or observed < instant(doc['generated_at']):
        raise ValueError('public_verification_clock_invalid')
    calls = [r for r in doc['records'] if r.get('status') == 'research_prediction']
    if len(calls) != doc['coverage']['prediction']:
        raise ValueError('public_prediction_count_mismatch')
    before = sum(instant(r['issued_at']) <= observed < instant(r['target']['start']) for r in calls)
    late = sum(instant(r['target']['start']) <= observed for r in calls)
    if before+late != len(calls):
        raise ValueError('forecast_issued_after_public_check')
    report = {'status': 'exact_public_universe_verified', 'verified_at': observed.isoformat(),
              'source_commit': commit, 'base_url': BASE, 'generation_run': doc.get('run', {}).get('id'),
              'snapshot_generated_at': doc['generated_at'], 'coverage': doc['coverage'],
              'public_prediction_count': len(calls), 'public_before_target_verified': before,
              'late_publication_observed': late, 'human_notification_received': False,
              'automatic_orders': False,
              'public_files_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in expected.items()}}
    report['verification_id'] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--attempts', type=int, default=1)
    parser.add_argument('--interval', type=float, default=10)
    parser.add_argument('--commit')
    args = parser.parse_args()
    for index in range(args.attempts):
        try:
            report = verify(commit=args.commit)
            path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            print('EXACT_PUBLIC_FULL_UNIVERSE', json.dumps(report, ensure_ascii=False)); break
        except Exception as exc:
            print('PUBLIC_CHECK_PENDING', type(exc).__name__, str(exc)[:180], flush=True)
            if index == args.attempts-1:
                raise
            time.sleep(min(max(args.interval, 0), 30))
