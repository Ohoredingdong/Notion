"""Live preflight through the exact production collection/model path."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import time


def main(output):
    from stock_forecast_sources import prepare_sessions
    from run_stock_universe_forecasts import (
        load_catalog, targets_for_catalog, YahooCollector, RequestBudget,
        process_target, model_module, now_utc,
    )
    prepare_sessions()
    catalogue, _ = load_catalog('stock-universe-catalog.json')
    targets = {t['provider_symbol']: t for t in targets_for_catalog(catalogue, 1)}
    collector, model = YahooCollector(), model_module()
    budget = RequestBudget(max_seconds=240, request_delay=.75, retries=1, backoff=15,
                           clock=now_utc, monotonic=time.monotonic, sleeper=time.sleep)
    results = []
    with tempfile.TemporaryDirectory(prefix='radar-live-source-preflight-') as cache:
        # 000020 previously failed because one invalid historical bar rejected
        # its whole history. Exercise the same per-bar filtering as every shard.
        for symbol in ('005930.KS', 'AAPL', '000660.KS', 'BRK-B', 'KO', '0001A0.KQ', '000020.KS'):
            result = process_target(targets[symbol], model=model, collector=collector,
                                    cache_dir=cache, budget=budget, clock=now_utc)
            provenance = result.get('price_provenance') or {}
            row = {'market': targets[symbol]['market'], 'symbol': symbol,
                   'source_status': 'received' if result['price_available'] else 'unavailable',
                   'model_status': result['status'], 'reason': result.get('reason'),
                   'error_kind': result.get('error_kind'), 'bars': provenance.get('bars', 0),
                   'received_at': result.get('received_at'), 'issued_at': result['issued_at'],
                   'observed_until': result.get('observed_until'), 'target': result.get('target'),
                   'response_symbol': provenance.get('source_response_symbol'),
                   'response_exchange': provenance.get('source_response_exchange'),
                   'history_sha256': provenance.get('history_sha256'),
                   'model_sha256': result.get('model_sha256'),
                   'row_quality': provenance.get('row_quality')}
            results.append(row)
            print('LIVE_SOURCE_PREFLIGHT', json.dumps(row, ensure_ascii=False), flush=True)
            if budget.circuit_reason or budget.rate_limit_events:
                raise RuntimeError('source_rate_limited_or_unavailable_before_full_sweep')
    report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'results': results,
              'production_collection_path': True, 'synthetic_prices_used': False,
              'automatic_orders': False}
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    available = {r['market'] for r in results if r['source_status'] == 'received' and r['bars'] > 500}
    if available != {'KR', 'US'}:
        raise RuntimeError('full_sweep_requires_real_KR_and_US_history_preflight')
    if next(r for r in results if r['symbol'] == '000020.KS')['source_status'] != 'received':
        raise RuntimeError('per_bar_filtering_regression_not_verified_against_live_source')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
