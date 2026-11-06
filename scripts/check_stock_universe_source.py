"""Small live-source preflight; never manufactures a missing history or forecast."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time


def main(output):
    from stock_forecast_sources import prepare_sessions
    from stock_forecast_model import normalise_history, fit_model, make_prediction
    from run_stock_universe_forecasts import load_catalog, targets_for_catalog, YahooCollector, validate_provider
    prepare_sessions()
    catalogue, _ = load_catalog('stock-universe-catalog.json')
    targets = {t['provider_symbol']: t for t in targets_for_catalog(catalogue, 1)}
    collector = YahooCollector()
    results = []
    for market, symbol in [('KR', '005930.KS'), ('US', 'AAPL'),
                           ('KR', '000660.KS'), ('US', 'BRK-B'),
                           ('US', 'KO'), ('KR', '0001A0.KQ')]:
        row = {'market': market, 'symbol': symbol}
        try:
            frame, metadata = collector(targets[symbol])
            received = datetime.now(timezone.utc)
            validate_provider(targets[symbol], metadata)
            bars = normalise_history(frame, market, 'daily', received)
            row.update(source_status='received', received_at=received.isoformat(),
                       response_symbol=metadata.get('symbol'), response_exchange=metadata.get('exchangeName'),
                       bars=len(bars), observed_until=bars.iloc[-1]['end'].isoformat(),
                       history_sha256=hashlib.sha256(bars.to_json(date_format='iso').encode()).hexdigest())
            try:
                fitted = fit_model(bars, 'daily')
                result = make_prediction(bars, fitted, symbol, market, 'daily', received,
                                         issued_at=datetime.now(timezone.utc))
                row.update(model_status=result['status'], reason=result.get('reason'),
                           model_sha256=fitted['model_sha256'])
            except ValueError as exc:
                row.update(model_status='no_call', reason=str(exc))
        except Exception as exc:
            row.update(source_status='unavailable', reason=f'{type(exc).__name__}: {exc}'[:240])
            if 'ratelimit' in type(exc).__name__.lower() or '429' in str(exc):
                raise RuntimeError('source_rate_limited_before_full_sweep') from exc
        results.append(row)
        print('LIVE_SOURCE_PREFLIGHT', json.dumps(row, ensure_ascii=False), flush=True)
        time.sleep(.75)
    report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'results': results,
              'synthetic_prices_used': False, 'automatic_orders': False}
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    available = {r['market'] for r in results if r.get('source_status') == 'received' and r.get('bars', 0) > 500}
    if available != {'KR', 'US'}:
        raise RuntimeError('full_sweep_requires_real_KR_and_US_history_preflight')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    main(parser.parse_args().output)
