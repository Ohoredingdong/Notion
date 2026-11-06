"""Accept the actual full-universe AI snapshot in desktop/mobile UI.

Uses exact saved source bytes and the actual clock. --require-full is the
aggregate/publication gate; omitting it also supports a source preview before
any full-universe result exists. No forecasts, quotes or times are fabricated.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time

import test_stock_universe_browser as universe


def source_contract(source, require_full):
    verify = universe.verify
    feed, catalog = source['extended'], source['catalog_by_key']
    full = feed.get('generation_mode') == 'full_universe' or bool(feed.get('coverage'))
    verify('full-universe output exists when required', full or not require_full,
           {'mode': feed.get('generation_mode'), 'records': len(feed.get('records', []))})
    verify('official identities are unique', len(catalog) == len(source['catalog']['items']))
    if not full:
        return {'full': False, 'total': len(catalog)}
    now = datetime.now(timezone.utc).timestamp()
    rows = feed.get('records', [])
    indexed = source['forecast_rows']['extended']
    verify('every official identity has one exactly bound output', len(rows) == len(catalog)
           and set(indexed) == set(catalog) and source['forecast_rejections']['extended'] == 0,
           {'official': len(catalog), 'rows': len(rows), 'bound': len(indexed),
            'rejected': source['forecast_rejections']['extended']})
    verify('full output binds the current catalogue generation',
           feed.get('source_catalog_generated_at') == source['catalog']['generated_at'])
    run, coverage = feed.get('run') or {}, feed.get('coverage') or {}
    started, completed, generated = [universe.timestamp(v) for v in
                                     (run.get('started_at'), run.get('completed_at'), feed.get('generated_at'))]
    verify('reported execution and aggregate clocks are real and ordered',
           all(math.isfinite(v) for v in (started, completed, generated))
           and started <= completed == generated <= now,
           {'started': run.get('started_at'), 'completed': run.get('completed_at'), 'now': now})
    prediction = failed = pending = price_available = 0
    errors = Counter()
    for key, bucket in indexed.items():
        row = bucket[0]
        issued = universe.timestamp(row.get('issued_at'))
        if not math.isfinite(issued) or issued > completed:
            raise AssertionError(f'{key}: result issue timestamp is invalid')
        if type(row.get('price_available')) is not bool:
            raise AssertionError(f'{key}: price availability is not explicit')
        if row['price_available']:
            if not universe.verified_price(row) or universe.timestamp(row.get('received_at')) > issued:
                raise AssertionError(f'{key}: verified source price provenance missing')
            price_available += 1
        if row.get('status') == 'research_prediction':
            if (not universe.eligible_forecast(row, now, active=False)
                    or not started <= universe.timestamp(row.get('issued_at')) <= completed
                    or universe.timestamp(row['target']['end']) <= completed):
                raise AssertionError(f'{key}: prospective prediction contract invalid')
            prediction += 1
        elif row.get('status') == 'no_call':
            if any(row.get(field) is not None for field in ('probabilities', 'target', 'direction')):
                raise AssertionError(f'{key}: no-call contains a manufactured prediction')
            if not row.get('error_kind') or not row.get('reason'):
                raise AssertionError(f'{key}: unavailable reason missing')
            errors[row['error_kind']] += 1
            if row.get('collection_status') in ('circuit_skipped', 'deadline_skipped'):
                pending += 1
            else:
                failed += 1
        else:
            raise AssertionError(f'{key}: unexpected status {row.get("status")}')
    expected = dict(total=len(catalog), attempted=prediction + failed, prediction=prediction,
                    failed=failed, not_attempted=pending, no_call=failed + pending,
                    price_available=price_available)
    verify('coverage is independently recounted from all current records',
           all(type(coverage.get(k)) is int and coverage[k] == v for k, v in expected.items()),
           {'expected': expected, 'reported': coverage})
    verify('processing completion is separate from prediction availability',
           coverage.get('manifest_complete') is True and coverage.get('coverage_complete') is (pending == 0))
    verify('run counters count new issuance and do not relabel skipped work',
           run.get('research_prediction') == prediction and run.get('no_call') == failed
           and run.get('attempted') == prediction + failed and run.get('not_attempted') == pending
           and run.get('retained_predictions', 0) == 0)
    return dict(expected, full=True, errors=dict(errors), generated_at=feed['generated_at'],
                run_id=run.get('id'), source_commit=run.get('source_commit'), manifest_sha256=feed.get('manifest_sha256'))


def sample_keys(source, now):
    """Select real non-raw successes and real non-raw unavailable rows per market."""
    samples = []
    for country in ('KR', 'US'):
        candidates = sorted(key for key in source['catalog_by_key']
                            if key.startswith(country + ':') and key not in source['raw_by_key'])
        for status in ('active', 'unavailable'):
            matches = [key for key in candidates if bool(universe.active_forecast(key, source, now)) == (status == 'active')]
            if matches:
                samples.append((status, matches[0]))
            else:
                universe.REPORT['limitations'].append(f'{country}: actual non-raw {status} sample does not exist in this snapshot')
    for key in ('US:BRK.B', 'KR:0001A0'):
        if key in source['catalog_by_key'] and key not in source['raw_by_key'] and key not in [k for _, k in samples]:
            samples.append(('identity', key))
    return samples


def run_view(browser, width, height, root, source, counts):
    ctx = universe.context(browser, width, height, root)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(universe.BASE, wait_until='domcontentloaded')
    universe.ready(page)
    label = f'{width}x{height}'
    universe.screen(page, 'stocks')
    panel = page.locator('.fx-ai-coverage')
    universe.verify(label + ': actual coverage panel exists', panel.count() == 1)
    universe.verify(label + ': official denominator comes from current source',
                    int(panel.locator('[data-fx-coverage="total"]').inner_text().replace(',', '')) == counts['total'])
    if counts['full']:
        universe.verify(label + ': full snapshot passes UI independent binding', panel.get_attribute('data-coverage-valid') == 'true')
        for field, oracle in (('prediction', 'prediction'), ('failed', 'failed'), ('not-attempted', 'not_attempted')):
            shown = panel.locator(f'[data-fx-coverage="{field}"]').inner_text()
            universe.verify(label + ': actual ' + field + ' count', int(shown.replace(',', '')) == counts[oracle], shown)
        observed_now = page.evaluate('Date.now() / 1000')
        active = sum(universe.active_forecast(key, source, observed_now) is not None
                     for key in source['union'])
        shown = panel.locator('[data-fx-coverage="active"]').inner_text()
        universe.verify(label + ': expired and unavailable records are excluded from valid count',
                        int(shown.replace(',', '')) == active, {'shown': shown, 'actual': active})
        panel.locator('summary').click()
        reasons = panel.locator('.fx-ai-coverage-reasons').inner_text()
        universe.verify(label + ': unavailability reasons are understandable and disclosed',
                        (counts['failed'] + counts['not_attempted'] == 0 or '개' in reasons)
                        and not any(kind in reasons for kind in counts['errors']), reasons)
        panel.locator('summary').click()
    else:
        universe.verify(label + ': pre-run snapshot cannot manufacture whole-universe generation counts',
                        panel.get_attribute('data-coverage-valid') == 'false'
                        and panel.locator('[data-fx-coverage="prediction"]').inner_text() == '확인 전')
    universe.verify(label + ': AI page remains within viewport width',
                    page.evaluate('document.documentElement.scrollWidth <= innerWidth + 4'))
    universe.screenshot(page, label + '-ai-coverage')
    more = page.locator('[data-fx-more]')
    if more.count():
        initial = len(universe.visible_ids(page))
        more.click()  # A footer overlap must fail hit testing, never force-click.
        universe.verify(label + ': more results remain normally clickable', len(universe.visible_ids(page)) > initial)
    samples = sample_keys(source, page.evaluate('Date.now() / 1000'))
    timings = []
    for kind, key in samples:
        universe.verify(label + ': tested company genuinely lies outside raw104', key not in source['raw_by_key'], key)
        started = time.perf_counter()
        universe.select_search(page, key, source, label + '/AI/' + kind)
        timings.append({'key': key, 'seconds': round(time.perf_counter() - started, 3)})
        universe.catalog_profile(page, key, source, label + '/AI/' + kind)
    if samples:
        key = samples[0][1]
        universe.select_search(page, key, source, label + '/selection')
        universe.screen(page, 'home')
        universe.catalog_profile(page, key, source, label + '/home')
        universe.screenshot(page, label + '-nonraw-home')
        universe.screen(page, 'stocks')
        universe.select_search(page, key, source, label + '/restored')
        profile = page.locator('.fx-catalog-preview')
        profile.locator('[data-nr-detail]').first.click()
        universe.catalog_profile(page, key, source, label + '/detail')
        page.reload(wait_until='domcontentloaded')
        universe.ready(page)
        universe.catalog_profile(page, key, source, label + '/reload')
    universe.verify(label + ': no uncaught browser errors', not errors, errors)
    universe.REPORT.setdefault('selection_timings', {})[label] = timings
    ctx.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=universe.BASE)
    parser.add_argument('--data-root', type=Path, default=Path(os.environ.get('RADAR_DATA_DIR', '.')))
    parser.add_argument('--out', type=Path, default=Path('radar-forecast-coverage-evidence'))
    parser.add_argument('--require-full', action='store_true')
    parser.add_argument('--oracle-only', action='store_true', help='Validate source only; does not claim a browser pass')
    args = parser.parse_args()
    universe.OUT, universe.BASE = args.out, args.base
    universe.OUT.mkdir(parents=True, exist_ok=True)
    universe.REPORT = {'checks': [], 'screenshots': [], 'limitations': [], 'browser_executed': False}
    try:
        source = universe.load_oracle(args.data_root)
        counts = source_contract(source, args.require_full)
        universe.REPORT['source'] = {'sha256': source['hashes'], 'coverage': counts,
                                      'raw': len(source['raw_by_key']), 'union': len(source['union']),
                                      'observed_at': datetime.now(timezone.utc).isoformat()}
        if not args.oracle_only:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as play:
                browser = play.chromium.launch(headless=True)
                try:
                    for width, height in ((1440, 900), (1366, 768), (390, 844)):
                        run_view(browser, width, height, args.data_root, source, counts)
                    universe.REPORT['browser_executed'] = True
                except Exception as error:
                    universe.capture_browser_failure(browser, error)
                    raise
                finally:
                    browser.close()
    except Exception as error:
        universe.REPORT['error'] = str(error)
        raise
    finally:
        (universe.OUT / 'report.json').write_text(json.dumps(universe.REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
    print('FULL_UNIVERSE_AI_ACCEPTANCE', len(universe.REPORT['checks']), 'checks',
          'browser' if universe.REPORT['browser_executed'] else 'source-only')


if __name__ == '__main__':
    main()
