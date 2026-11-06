"""Observe deployed UI and the exact latest-main market/numerical source bytes."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.build_stock_world_flow import BY_ID, session_clock, validate_document
from scripts.market_data_utils import market_session_clock
from scripts.publish_widget_data import OPPORTUNITY_BINDINGS
from scripts.stock_technical_evidence import validate_technical_evidence
from scripts.validate_stock_financial_coverage import validate as validate_financial

BASE = 'https://ohoredingdong.github.io/Notion/'
UI = ('stock-value-radar.html', 'assets/stock-world-flow.js',
      'assets/stock-radar-clean-bridge.js', 'assets/stock-radar-flow-v2.js',
      'assets/stock-catalog-ui.js')
AUDITED_DATA = ('stock-opportunity-data.json', 'stock-opportunity-summary.json',
               'stock-radar-chart-data.json', 'stock-universe-catalog.json',
               'stock-financial-coverage.json', 'stock-extended-direction-forecast.json',
               'stock-direction-forecast.json', *OPPORTUNITY_BINDINGS,
               'fear-greed-data.json', 'stock-korea-fear-greed.json', 'stock-world-flow.json')
DATA = tuple(dict.fromkeys((*AUDITED_DATA, 'stock-display-number-audit.json')))


def revision_bytes(revision, name):
    return subprocess.check_output(['git', 'show', revision+':'+name], cwd=ROOT)


def public_digest(name):
    request = urllib.request.Request(BASE+name+'?verify='+str(time.time_ns()),
                                     headers={'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=40) as response:
        digest = hashlib.sha256()
        for block in iter(lambda: response.read(1024 * 1024), b''):
            digest.update(block)
        return digest.hexdigest()


def instant(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def validate_audit_bindings(expected, now):
    """Every audited input must still match, including all derived records and AI."""
    audit = json.loads(expected['stock-display-number-audit.json'])
    if audit.get('errors') != [] or audit.get('status') != 'passed_with_limitations':
        raise ValueError('published_display_number_audit_failed')
    checked = instant(audit.get('checked_at'))
    if checked is None or checked > now:
        raise ValueError('published_display_number_audit_invalid_time')
    recorded = audit.get('source_sha256') or {}
    if set(recorded) != set(AUDITED_DATA):
        raise ValueError('published_number_audit_source_set_incomplete')
    bindings = {name: recorded[name] == hashlib.sha256(expected[name]).hexdigest()
                for name in AUDITED_DATA}
    if not all(bindings.values()):
        raise ValueError('published_number_audit_needs_latest_source_rebuild:' +
                         ','.join(name for name, matches in bindings.items() if not matches))
    return audit, bindings


def require_current_observations(raw, charts, world, now):
    """A successful publication proof must enforce its reported freshness counts."""
    sessions = {market: market_session_clock(market, now)['expected_session'] for market in ('KR', 'US')}
    rows = raw.get('companies') or []
    valid_price = lambda value: type(value) in (int, float) and math.isfinite(value) and value > 0
    current_quotes = sum(r.get('market') in sessions and r.get('price_session') == sessions[r['market']]
                         and valid_price(r.get('price')) for r in rows)
    if not rows or current_quotes != len(rows):
        raise ValueError(f'published_quotes_not_all_current:{current_quotes}/{len(rows)}')
    series = charts.get('series') or {}
    required = {row['symbol'] for row in rows} | {'^KS11', '^KQ11', '^GSPC', '^IXIC'}
    if not required <= set(series):
        raise ValueError('published_chart_identities_missing:' + ','.join(sorted(required-set(series))))
    def current_chart(row):
        bars = row.get('bars') or []
        return (bool(bars) and row.get('market') in sessions
                and row.get('price_session') == sessions[row['market']] == bars[-1].get('date')
                and valid_price(bars[-1].get('close')))
    current_charts = sum(current_chart(row) for row in series.values())
    if current_charts != len(series):
        raise ValueError(f'published_charts_not_all_current:{current_charts}/{len(series)}')
    indicators = world.get('indicators') or []
    if len(indicators) != len(BY_ID) or {row.get('id') for row in indicators} != set(BY_ID):
        raise ValueError('published_world_indicator_set_incomplete')
    current_world = 0
    for row in indicators:
        key = row['id']
        expected_session = session_clock(BY_ID[key], now, (row.get('source') or {}).get('timezone'))['expected_session']
        session = row.get('session') or ''
        current = session >= expected_session if key == 'us10y' else session == expected_session
        received = instant(row.get('received_at'))
        observed = instant(row.get('observed_at')) if row.get('observed_at') is not None else None
        current = (current and row.get('comparison_verified') is True
                   and row.get('status') != 'unavailable' and valid_price(row.get('value'))
                   and received is not None and received <= now
                   and (row.get('observed_at') is None or (observed is not None and observed <= now)))
        current_world += bool(current)
    if current_world != len(BY_ID):
        raise ValueError(f'published_world_not_all_current:{current_world}/{len(BY_ID)}')
    return sessions, current_quotes, current_charts, current_world


def confirm_latest_snapshot(expected_digests):
    """An unrelated commit is harmless; any relevant source/UI movement retries."""
    subprocess.run(['git', 'fetch', 'origin', 'main'], cwd=ROOT, check=True, capture_output=True)
    latest = subprocess.check_output(['git', 'rev-parse', 'origin/main'], cwd=ROOT, text=True).strip()
    for name, digest in expected_digests.items():
        if hashlib.sha256(revision_bytes(latest, name)).hexdigest() != digest:
            raise ValueError('main_snapshot_changed_during_public_verification:'+name)
    return latest


def verify(ui_commit):
    subprocess.run(['git', 'fetch', 'origin', 'main'], cwd=ROOT, check=True, capture_output=True)
    latest = subprocess.check_output(['git', 'rev-parse', 'origin/main'], cwd=ROOT, text=True).strip()
    expected = {name: revision_bytes(ui_commit if name in UI else latest, name) for name in UI+DATA}
    now = datetime.now(timezone.utc)
    # Fail quickly on a changing source snapshot before downloading large AI feeds.
    audit, bindings = validate_audit_bindings(expected, now)
    world = json.loads(expected['stock-world-flow.json'])
    contract = validate_document(world)
    raw = json.loads(expected['stock-opportunity-data.json'])
    charts = json.loads(expected['stock-radar-chart-data.json'])
    financial = json.loads(expected['stock-financial-coverage.json'])
    catalogue = json.loads(expected['stock-universe-catalog.json'])
    finance_counts = validate_financial(catalogue, financial)
    sessions, current_quotes, current_charts, current_world = require_current_observations(raw, charts, world, now)
    technical_evidence = {'verified': 0, 'verified_withheld': 0}
    for row in raw.get('companies', []):
        result = validate_technical_evidence(row, now=now)
        if result['status'] not in technical_evidence or result['errors']:
            raise ValueError('published_technical_source_evidence_invalid:' + str(row.get('symbol')) + ':' +
                             json.dumps(result['errors'][:3], ensure_ascii=False))
        technical_evidence[result['status']] += 1
    digests = {name: hashlib.sha256(body).hexdigest() for name, body in expected.items()}
    def compare_public(name):
        if public_digest(name) != digests[name]:
            raise ValueError('public_bytes_not_yet_aligned:'+name)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(compare_public, expected))
    latest = confirm_latest_snapshot(digests)
    # Recheck after the HTTP requests so a market close during verification cannot
    # turn an expired observation into a successful current-session proof.
    now = datetime.now(timezone.utc)
    sessions, current_quotes, current_charts, current_world = require_current_observations(raw, charts, world, now)
    return {'status': 'exact_public_world_and_number_update_verified',
            'verified_at': now.isoformat(), 'base_url': BASE,
            'ui_commit': ui_commit, 'data_commit': latest,
            'world_flow': contract, 'current_world_observations': current_world,
            'world_generated_at': world['generated_at'],
            'expected_completed_sessions': sessions,
            'detailed_research_rows': len(raw.get('companies', [])), 'current_quotes': current_quotes,
            'chart_series': len(charts.get('series', {})), 'current_charts': current_charts,
            'official_financial_available': finance_counts,
            'numerical_audit_errors': len(audit['errors']), 'numerical_audit_checks': audit['check_count'],
            'numerical_audit_source_binding': bindings,
            'numerical_audit_warnings': len(audit.get('warnings') or []),
            'technical_source_evidence': technical_evidence,
            'public_files_sha256': digests,
            'scope': 'Exact public file bytes, source contracts and arithmetic; no certification of forecasts or provider accuracy.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ui-commit', required=True)
    parser.add_argument('--output', type=Path, default=Path('radar-world-flow-evidence/publication.json'))
    parser.add_argument('--attempts', type=int, default=30)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'status': 'verification_pending',
                          'started_at': datetime.now(timezone.utc).isoformat(),
                          'ui_commit': args.ui_commit})+'\n')
    for index in range(args.attempts):
        try:
            result = verify(args.ui_commit)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps(result, ensure_ascii=False))
            return 0
        except Exception as exc:
            args.output.write_text(json.dumps({'status': 'verification_failed' if index+1 == args.attempts else 'verification_pending',
                                  'checked_at': datetime.now(timezone.utc).isoformat(), 'ui_commit': args.ui_commit,
                                  'attempt': index+1, 'error': str(exc)[:1000]}, ensure_ascii=False, indent=2)+'\n')
            print('PUBLIC_UPDATE_PENDING', type(exc).__name__, str(exc)[:180], flush=True)
            if index+1 == args.attempts:
                raise
            time.sleep(10)


if __name__ == '__main__':
    sys.exit(main())
