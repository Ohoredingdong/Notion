"""Observe deployed UI and the exact latest-main market/numerical source bytes."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.build_stock_world_flow import validate_document
from scripts.market_data_utils import market_session_clock
from scripts.validate_stock_financial_coverage import validate as validate_financial

BASE = 'https://ohoredingdong.github.io/Notion/'
UI = ('stock-value-radar.html', 'assets/stock-world-flow.js',
      'assets/stock-radar-clean-bridge.js', 'assets/stock-radar-flow-v2.js',
      'assets/stock-catalog-ui.js')
DATA = ('stock-world-flow.json', 'stock-opportunity-data.json',
        'stock-radar-chart-data.json', 'stock-financial-coverage.json',
        'fear-greed-data.json', 'stock-korea-fear-greed.json',
        'stock-display-number-audit.json')


def revision_bytes(revision, name):
    return subprocess.check_output(['git', 'show', revision+':'+name], cwd=ROOT)


def public(name):
    request = urllib.request.Request(BASE+name+'?verify='+str(time.time_ns()),
                                     headers={'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read()


def verify(ui_commit):
    subprocess.run(['git', 'fetch', 'origin', 'main'], cwd=ROOT, check=True, capture_output=True)
    latest = subprocess.check_output(['git', 'rev-parse', 'origin/main'], cwd=ROOT, text=True).strip()
    expected = {name: revision_bytes(ui_commit if name in UI else latest, name) for name in UI+DATA}
    for name, body in expected.items():
        if public(name) != body:
            raise ValueError('public_bytes_not_yet_aligned:'+name)
    world = json.loads(expected['stock-world-flow.json'])
    contract = validate_document(world)
    raw = json.loads(expected['stock-opportunity-data.json'])
    charts = json.loads(expected['stock-radar-chart-data.json'])
    financial = json.loads(expected['stock-financial-coverage.json'])
    catalogue = json.loads(revision_bytes(latest, 'stock-universe-catalog.json'))
    finance_counts = validate_financial(catalogue, financial)
    audit = json.loads(expected['stock-display-number-audit.json'])
    if audit.get('errors') or audit.get('status') != 'passed_with_limitations':
        raise ValueError('published_display_number_audit_failed')
    bindings = {name: (audit.get('source_sha256') or {}).get(name) == hashlib.sha256(expected[name]).hexdigest()
                for name in DATA if name != 'stock-display-number-audit.json'}
    if not all(bindings.values()):
        raise ValueError('published_number_audit_needs_latest_source_rebuild')
    now = datetime.now(timezone.utc)
    sessions = {market: market_session_clock(market, now)['expected_session'] for market in ('KR', 'US')}
    current_quotes = sum(r.get('price_session') == sessions.get(r.get('market')) and isinstance(r.get('price'), (int, float))
                         for r in raw.get('companies', []))
    current_charts = sum(r.get('price_session') == sessions.get(r.get('market')) for r in charts.get('series', {}).values())
    return {'status': 'exact_public_world_and_number_update_verified',
            'verified_at': now.isoformat(), 'base_url': BASE,
            'ui_commit': ui_commit, 'data_commit': latest,
            'world_flow': contract, 'world_generated_at': world['generated_at'],
            'expected_completed_sessions': sessions,
            'detailed_research_rows': len(raw.get('companies', [])), 'current_quotes': current_quotes,
            'chart_series': len(charts.get('series', {})), 'current_charts': current_charts,
            'official_financial_available': finance_counts,
            'numerical_audit_errors': len(audit['errors']), 'numerical_audit_checks': audit['check_count'],
            'numerical_audit_source_binding': bindings,
            'public_files_sha256': {name: hashlib.sha256(body).hexdigest() for name, body in expected.items()},
            'scope': 'Exact public file bytes, source contracts and arithmetic; no certification of forecasts or provider accuracy.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ui-commit', required=True)
    parser.add_argument('--output', type=Path, default=Path('radar-world-flow-evidence/publication.json'))
    parser.add_argument('--attempts', type=int, default=30)
    args = parser.parse_args()
    for index in range(args.attempts):
        try:
            result = verify(args.ui_commit)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps(result, ensure_ascii=False))
            return 0
        except Exception as exc:
            print('PUBLIC_UPDATE_PENDING', type(exc).__name__, str(exc)[:180], flush=True)
            if index+1 == args.attempts:
                raise
            time.sleep(10)


if __name__ == '__main__':
    sys.exit(main())
