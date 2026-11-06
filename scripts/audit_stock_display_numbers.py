"""Recalculate published display numbers without changing source records.

This verifies arithmetic, identity/count contracts and explicit source periods.
It does not certify a vendor's estimates, predict returns, or rewrite ledgers.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.market_data_utils import market_session_clock, exchange_calendar
from scripts.publish_widget_data import OPPORTUNITY_BINDINGS, verify_source_bindings
from scripts.validate_stock_financial_coverage import validate as validate_financial


def number(value):
    return value if type(value) in (float, int) and math.isfinite(value) else None


def ratio(a, b, scale=1):
    return a / b * scale if number(a) is not None and number(b) is not None and b != 0 else None


def growth(a, b):
    return (a-b) / abs(b) * 100 if number(a) is not None and number(b) is not None and b != 0 else None


def instant(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


class Audit:
    def __init__(self):
        self.checks = Counter()
        self.errors = []
        self.warnings = []
        self.quantization_checks = []

    def check(self, group, ok, message, **context):
        self.checks[group] += 1
        if not ok:
            self.errors.append({'group': group, 'issue': message, **context})

    def compare(self, group, actual, expected, field, identity=None, tolerance=1e-5):
        if actual is None:
            return
        if expected is None:
            self.warnings.append({'group': group, 'issue': 'insufficient_inputs_for_recalculation',
                                  'field': field, 'identity': identity})
            return
        self.check(group, number(actual) is not None and math.isclose(actual, expected, rel_tol=1e-7, abs_tol=tolerance),
                   'arithmetic_mismatch', field=field, identity=identity, published=actual, recalculated=expected)

    def warn(self, group, message, **context):
        self.warnings.append({'group': group, 'issue': message, **context})


def reward_risk_interval(close, support, resistance):
    """Propagate the source serializer's documented round(x, 8), not a loose tolerance.

    update_stock_decisions.clean rounds all output floats to eight decimal places
    and run_stock_research_v9 applies that clean function to the published record.
    Each serialized price therefore represents a closed +/- 0.5e-8 interval.
    The same close is used in both numerator and denominator at every corner.
    """
    if any(number(value) is None for value in (close, support, resistance)):
        return {'status': 'unverifiable', 'reason': 'reward_risk_missing_price_inputs'}
    with localcontext() as context:
        context.prec = 50
        half = Decimal('0.000000005')
        c, s, r = (Decimal(str(value)) for value in (close, support, resistance))
        intervals = [(value-half, value+half) for value in (c, s, r)]
        denominator = (intervals[0][0]-intervals[1][1], intervals[0][1]-intervals[1][0])
        if denominator[0] <= 0 <= denominator[1]:
            return {'status': 'unverifiable', 'reason': 'reward_risk_denominator_interval_crosses_zero',
                    'denominator_interval': [str(value) for value in denominator]}
        if denominator[1] <= 0:
            return {'status': 'unverifiable', 'reason': 'reward_risk_nonpositive_risk'}
        values = [(resistance_value-close_value)/(close_value-support_value)
                  for close_value, support_value, resistance_value in product(*intervals)]
        # Outward Decimal rounding covers only the 50-digit division operation.
        lower, upper = min(values).next_minus(), max(values).next_plus()
        return {'status': 'bounded', 'source_decimal_places': 8,
                'input_half_quantum': str(half), 'lower': str(lower), 'upper': str(upper),
                'denominator_interval': [str(value) for value in denominator]}


def check_reward_risk(a, published, close, support, resistance, identity=None):
    interval = reward_risk_interval(close, support, resistance)
    if interval['status'] != 'bounded':
        if published is None:
            a.warn('technical', interval['reason'], field='reward_risk', identity=identity)
            return True
        a.check('technical', False, interval['reason'], field='reward_risk', identity=identity,
                published=published, quantization=interval, required_action='withhold_unverifiable_ratio')
        return False
    if published is None:
        return True
    valid = number(published) is not None and published >= 0
    if valid:
        with localcontext() as context:
            context.prec = 50
            value, half = Decimal(str(published)), Decimal('0.000000005')
            # The ratio itself passes through the same round8 serializer.
            valid = value+half >= Decimal(interval['lower']) and value-half <= Decimal(interval['upper'])
    evidence = {'identity': identity, 'field': 'reward_risk', 'published': published, **interval, 'verified': valid}
    a.quantization_checks.append(evidence)
    a.check('technical', valid, 'reward_risk_quantization_interval_mismatch', field='reward_risk',
            identity=identity, published=published, quantization=interval)
    return valid


def check_daily_change(a, proof, *, identity, market, provider, currency, session, close, now, bars=None):
    """A verified label requires complete evidence; optional comparisons cannot skip it."""
    if proof.get('status') != 'verified':
        return False
    values_ok = (number(close) is not None and close > 0
                 and number(proof.get('close')) is not None and proof['close'] > 0
                 and number(proof.get('previous_close')) is not None and proof['previous_close'] > 0
                 and number(proof.get('change_1d_pct')) is not None)
    a.check('daily_change', values_ok, 'verified_daily_change_missing_numeric_evidence', identity=identity)
    contract = (proof.get('version') == 'completed-session-change-v1'
                and proof.get('source_identity_verified') is True and proof.get('consecutive_sessions') is True
                and proof.get('basis') == 'provider_close_auto_adjust_false'
                and bool(provider) and proof.get('provider_symbol') == provider
                and bool(currency) and proof.get('currency') == currency
                and market in ('KR', 'US') and proof.get('market') == market
                and isinstance(session, str) and proof.get('price_session') == session)
    a.check('daily_change', contract, 'daily_change_source_contract_invalid', identity=identity)
    adjacent = False
    if market in ('KR', 'US') and isinstance(session, str):
        try:
            previous_session = str(exchange_calendar(market, now.year).previous_session(session))[:10]
            adjacent = (proof.get('previous_session') == proof.get('expected_previous_session') == previous_session)
        except (ValueError, KeyError, TypeError):
            pass
    a.check('daily_change', adjacent, 'previous_session_not_calendar_adjacent', identity=identity)
    if not values_ok:
        return False
    quote_match = math.isclose(proof['close'], close, rel_tol=1e-8, abs_tol=1e-6)
    computed = (proof['close'] / proof['previous_close'] - 1) * 100
    percentage_match = math.isclose(proof['change_1d_pct'], computed, rel_tol=1e-8, abs_tol=1e-5)
    a.check('daily_change', quote_match, 'quote_matches_daily_change', identity=identity)
    a.check('daily_change', percentage_match, 'arithmetic_mismatch', identity=identity,
            field='change_1d_pct', published=proof['change_1d_pct'], recalculated=computed)
    bars_match = True
    if bars is not None:
        by_date = {row.get('date'): row.get('close') for row in bars}
        for field, date_field in (('close', 'price_session'), ('previous_close', 'previous_session')):
            value = by_date.get(proof.get(date_field))
            ok = number(value) is not None and math.isclose(proof[field], value, rel_tol=1e-8, abs_tol=1e-6)
            a.check('daily_change', ok, 'daily_change_disagrees_with_chart_bar', identity=identity, field=field)
            bars_match &= ok
    return values_ok and contract and adjacent and quote_match and percentage_match and bars_match


def forecast_counts(records):
    statuses = Counter(row.get('status') for row in records)
    skipped = sum(row.get('collection_status') in ('circuit_skipped', 'deadline_skipped') for row in records)
    prediction = statuses['research_prediction']
    return {'total': len(records), 'prediction': prediction, 'no_call': statuses['no_call'],
            'not_attempted': skipped, 'attempted': len(records)-skipped,
            'failed': len(records)-prediction-skipped}


def missing_chart_identities(companies, series):
    return sorted(({row['symbol'] for row in companies} | {'^KS11', '^KQ11', '^GSPC', '^IXIC'}) - set(series))


def world_current_counts(document, now):
    """Recheck current calendar expectations independently of a fresh report wrapper."""
    from scripts.build_stock_world_flow import BY_ID, session_clock
    counts = Counter()
    for row in document['indicators']:
        if row.get('status') == 'unavailable':
            counts['unavailable'] += 1
            continue
        expected = session_clock(BY_ID[row['id']], now, (row.get('source') or {}).get('timezone'))['expected_session']
        # Treasury may have actually published today's date before the service's
        # conservative 18:00 ET recheck time. The source date remains explicit.
        session = row.get('session') or ''
        fresh = session >= expected if row['id'] == 'us10y' else session == expected
        receipt = instant(row.get('received_at'))
        observed = instant(row.get('observed_at')) if row.get('observed_at') is not None else None
        fresh = fresh and receipt is not None and receipt <= now and (observed is None or observed <= now)
        counts['current' if fresh and row.get('comparison_verified') is True else 'stale_or_unverified'] += 1
    return dict(counts)


def check_sentiment_observations(a, us, kr, now, expected_kr):
    for key in ('kospi', 'kosdaq'):
        value = (kr.get(key) or {}).get('index')
        a.check('sentiment', number(value) is not None and 0 <= value <= 100,
                'sentiment_out_of_range', field='KR.'+key+'.index', value=value)
    value = (us.get('headline') or {}).get('score')
    a.check('sentiment', number(value) is not None and 0 <= value <= 100,
            'sentiment_out_of_range', field='US.headline.score', value=value)
    observed = instant(us.get('source_timestamp') or (us.get('headline') or {}).get('timestamp'))
    a.check('sentiment', observed is not None and observed <= now, 'sentiment_invalid_or_future_observation', field='US.source_timestamp')
    try:
        day = datetime.strptime(str(kr.get('date')), '%Y-%m-%d').date()
        valid = day.isoformat() == kr.get('date') and day <= now.astimezone(ZoneInfo('Asia/Seoul')).date() and day.isoformat() <= expected_kr
    except (TypeError, ValueError):
        valid = False
    a.check('sentiment', valid, 'sentiment_invalid_or_uncompleted_source_date', field='KR.date')


def audit(root=ROOT, now=None, require_current=False):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('audit_clock_requires_timezone')
    a = Audit()
    hashes = {}

    def read(name):
        body = (root/name).read_bytes()
        hashes[name] = hashlib.sha256(body).hexdigest()
        doc = json.loads(body)
        def finite_walk(value, path):
            if isinstance(value, float):
                a.check('finite_numbers', math.isfinite(value), 'non_finite_value', field=path)
            elif isinstance(value, dict):
                for k, child in value.items():
                    finite_walk(child, path+'.'+k)
            elif isinstance(value, list):
                for i, child in enumerate(value):
                    finite_walk(child, path+'['+str(i)+']')
        finite_walk(doc, name)
        return doc

    raw = read('stock-opportunity-data.json')
    summary = read('stock-opportunity-summary.json')
    chart = read('stock-radar-chart-data.json')
    catalog = read('stock-universe-catalog.json')
    financial = read('stock-financial-coverage.json')
    extended = read('stock-extended-direction-forecast.json')
    core = read('stock-direction-forecast.json')
    companies = raw.get('companies', [])
    by_symbol = {r['symbol']: r for r in companies}
    a.check('counts', len(by_symbol) == len(companies), 'duplicate_research_identity')
    a.check('counts', raw.get('counts', {}).get('tracked') == len(companies), 'research_count_mismatch')
    a.check('counts', raw.get('counts') == summary.get('counts'), 'summary_count_mismatch')
    a.check('counts', raw.get('generated_at') == summary.get('generated_at'), 'summary_source_mismatch')

    expected = {}
    for market in ('KR', 'US'):
        expected[market] = market_session_clock(market, now)['expected_session']
    quote_counts = Counter()
    currency_unknown = []
    for row in companies:
        symbol = row['symbol']
        market = row.get('market')
        p = number(row.get('price'))
        session = row.get('price_session')
        current = p is not None and p > 0 and session == expected.get(market)
        quote_counts['current' if current else 'stale_or_unavailable'] += 1
        a.check('quotes', p is None or p > 0, 'nonpositive_quote', identity=symbol)
        if not current:
            a.warn('freshness', 'quote_not_latest_completed_session', identity=symbol,
                   session=session, expected_session=expected.get(market))
        dc = row.get('daily_change') or {}
        if dc.get('status') == 'verified':
            valid_dc = check_daily_change(a, dc, identity=symbol, market=market,
                         provider=row.get('source_symbol') or symbol, currency=row.get('currency'),
                         session=session, close=p, now=now)
            quote_counts['verified_daily_change' if valid_dc else 'invalid_daily_change'] += 1
        else:
            quote_counts['daily_change_withheld'] += 1

        f, t, h, b = (row.get(k) or {} for k in ('forecasts', 'targets', 'history', 'balance'))
        f0, f1 = f.get('current_fy') or {}, f.get('next_fy') or {}
        a.compare('valuation', t.get('median_gap_pct'), growth(t.get('median'), p), 'targets.median_gap_pct', symbol)
        a.compare('valuation', t.get('low_gap_pct'), growth(t.get('low'), p), 'targets.low_gap_pct', symbol)
        a.compare('valuation', t.get('review_price_ceiling'), ratio(t.get('median'), 1.2), 'targets.review_price_ceiling', symbol)
        a.compare('valuation', f.get('next_fy_pe'), ratio(p, f1.get('avg')), 'forecasts.next_fy_pe', symbol)
        if f.get('next_fy_pe') is not None:
            a.check('valuation', f.get('currency') == row.get('currency') and bool(f.get('currency')),
                    'forecast_pe_currency_mismatch', identity=symbol)
        a.compare('valuation', f.get('eps_growth_next_fy_pct'), growth(f1.get('avg'), f0.get('avg')), 'forecasts.eps_growth_next_fy_pct', symbol)
        trend = f.get('eps_trend_next_fy') or {}
        a.compare('valuation', f.get('eps_revision30_pct'), growth(trend.get('current'), trend.get('30daysAgo')), 'forecasts.eps_revision30_pct', symbol)
        if all(number(h.get(k)) is not None for k in ('cfo', 'capex')):
            a.compare('financial_arithmetic', h.get('fcf'), h['cfo']-abs(h['capex']), 'history.fcf', symbol, tolerance=.02)
        a.compare('financial_arithmetic', h.get('operating_margin'), ratio(h.get('operating_income'), h.get('revenue'), 100), 'history.operating_margin', symbol, tolerance=.011)
        for field in ('revenue', 'operating_income', 'net_income', 'eps', 'cfo', 'capex', 'fcf', 'accounts_receivable', 'inventory', 'equity', 'total_assets'):
            a.compare('financial_arithmetic', h.get(field+'_growth'), growth(h.get(field), h.get(field+'_previous')), 'history.'+field+'_growth', symbol, tolerance=.011)
        if all(number(b.get(k)) is not None for k in ('cash', 'debt', 'ebitda')) and b['ebitda'] > 0:
            a.compare('financial_arithmetic', b.get('net_debt_ebitda'), (b['debt']-b['cash'])/b['ebitda'], 'balance.net_debt_ebitda', symbol)
        if any(number(h.get(k)) is not None for k in ('fcf', 'revenue', 'net_income')) and not h.get('currency'):
            currency_unknown.append(symbol)
        values = (row.get('priority') or {}).get('factors', [])
        if values:
            a.compare('scores', (row.get('priority') or {}).get('score'), sum(x.get('points', 0) for x in values), 'priority.score', symbol)

    chart_counts = Counter()
    missing_charts = missing_chart_identities(companies, chart.get('series') or {})
    a.check('chart', not missing_charts, 'required_chart_identities_missing', identities=missing_charts)
    for symbol, series in (chart.get('series') or {}).items():
        bars = series.get('bars') or []
        if not bars:
            chart_counts['unavailable'] += 1
            continue
        dates = [r.get('date') for r in bars]
        a.check('chart', dates == sorted(set(dates)), 'unordered_or_duplicate_dates', identity=symbol)
        a.check('chart', all(number(r.get('close')) is not None and r['close'] > 0 for r in bars), 'invalid_close', identity=symbol)
        a.check('chart', series.get('price_session') == dates[-1], 'endpoint_session_mismatch', identity=symbol)
        check_daily_change(a, series.get('daily_change') or {}, identity='chart:'+symbol,
                           market=series.get('market'), provider=series.get('provider') or series.get('provider_symbol'),
                           currency=series.get('currency'), session=dates[-1], close=bars[-1].get('close'), now=now, bars=bars)
        current = dates[-1] == expected.get(series.get('market'))
        chart_counts['current' if current else 'stale'] += 1
        source = by_symbol.get(symbol)
        if source and source.get('price_session') == dates[-1]:
            a.compare('chart', bars[-1]['close'], source.get('price'), 'chart_and_quote_close', symbol, tolerance=.0001)
            tech = source.get('technical') or {}
            if tech.get('status') == 'ok' and len(bars) >= 61:
                closes = [r['close'] for r in bars]
                a.compare('technical', tech.get('ma20'), sum(closes[-20:])/20, 'ma20', symbol, tolerance=.0001)
                a.compare('technical', tech.get('ma60'), sum(closes[-60:])/60, 'ma60', symbol, tolerance=.0001)
                a.compare('technical', tech.get('return20_pct'), growth(closes[-1], closes[-21]), 'return20_pct', symbol)
                volumes = [r.get('volume') for r in bars[-21:-1]]
                if all(number(v) is not None for v in volumes):
                    average_volume = sum(volumes)/20
                    a.compare('technical', tech.get('avg_volume20'), average_volume, 'avg_volume20', symbol, tolerance=.01)
                    a.compare('technical', tech.get('volume_ratio'), ratio(tech.get('volume'), average_volume), 'volume_ratio', symbol)
                support = number(tech.get('support10'))
                resistance = number(tech.get('resistance_1y'))
                close = number(tech.get('close'))
                if close is not None and support is not None and close > support:
                    a.compare('technical', tech.get('support_loss_pct'), (close-support)/close*100, 'support_loss_pct', symbol)
                check_reward_risk(a, tech.get('reward_risk'), close, support, resistance, symbol)

    try:
        available = validate_financial(catalog, financial)
        a.check('official_financial_coverage', True, 'official_identity_and_count_contract')
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        available = financial.get('financial_available')
        a.check('official_financial_coverage', False, str(exc))
    for key, row in financial.get('records', {}).items():
        if row.get('status') != 'available':
            continue
        m = row.get('metrics') or {}
        if all(number(m.get(k)) is not None for k in ('assets', 'liabilities', 'equity')):
            a.compare('official_financial_arithmetic', m['assets'], m['liabilities']+m['equity'], 'assets=liabilities+equity', key, tolerance=1)
        if all(number(m.get(k)) is not None for k in ('cash_from_operations', 'capital_expenditure')):
            a.compare('official_financial_arithmetic', m.get('free_cash_flow'), m['cash_from_operations']-abs(m['capital_expenditure']), 'free_cash_flow', key, tolerance=1)

    identities = {(x['country'], x['symbol']) for x in catalog['items']}
    record_identities = {(x.get('market'), x.get('catalog_symbol')) for x in extended['records']}
    a.check('forecast_coverage', identities == record_identities and len(record_identities) == len(extended['records']), 'catalog_forecast_identity_set_mismatch')
    statuses = Counter(r.get('status') for r in extended['records'])
    coverage = extended.get('coverage') or {}
    expected_coverage = forecast_counts(extended['records'])
    a.check('forecast_coverage', set(statuses) <= {'research_prediction', 'no_call'}, 'unknown_forecast_status')
    a.check('forecast_coverage', all(row.get('collection_status') in
            {'circuit_skipped', 'deadline_skipped', 'fetched', 'cache_current', 'source_error', 'unsupported'}
            for row in extended['records']), 'unknown_collection_status')
    a.check('forecast_coverage', all(row.get('status') == 'no_call' for row in extended['records']
              if row.get('collection_status') in ('circuit_skipped', 'deadline_skipped')), 'skipped_collection_has_prediction')
    for key, value in expected_coverage.items():
        a.check('forecast_coverage', coverage.get(key) == value, 'coverage_counter_mismatch', field=key, published=coverage.get(key), recalculated=value)
    for key, value in (('attempted', expected_coverage['attempted']), ('research_prediction', expected_coverage['prediction']),
                       ('no_call', expected_coverage['failed']), ('not_attempted', expected_coverage['not_attempted'])):
        a.check('forecast_coverage', (extended.get('run') or {}).get(key) == value, 'run_counter_mismatch',
                field=key, published=(extended.get('run') or {}).get(key), recalculated=value)
    for feed_name, document in (('core', core), ('universe', extended)):
        for row in document.get('records', []):
            key = row.get('key', row.get('symbol'))
            if row.get('status') != 'research_prediction':
                if row.get('status') == 'no_call':
                    a.check('forecast_probabilities', row.get('probabilities') is None, 'withheld_record_has_probability', identity=key)
                continue
            p = row.get('probabilities') or {}
            valid = set(p) == {'up', 'flat', 'down'} and all(number(v) is not None and 0 <= v <= 1 for v in p.values())
            a.check('forecast_probabilities', valid and abs(sum(p.values())-1) < 1e-6, 'invalid_probability_distribution', identity=key)
            if valid:
                a.check('forecast_probabilities', p.get(row.get('direction'), -1) >= max(p.values())-1e-12, 'direction_not_probability_argmax', identity=key)
            v = row.get('validation') or {}
            cm = v.get('confusion_matrix')
            if isinstance(cm, list) and len(cm) == 3 and all(isinstance(x, list) and len(x) == 3 for x in cm):
                total = sum(sum(x) for x in cm)
                a.compare('forecast_validation', v.get('test_samples'), total, 'test_samples', key, tolerance=0)
                a.compare('forecast_validation', v.get('accuracy'), ratio(sum(cm[i][i] for i in range(3)), total), 'holdout_accuracy', key)
            if feed_name == 'universe':
                total = sum(row.get(k, 0) for k in ('training_samples', 'calibration_samples')) + (v.get('test_samples') or 0)
                a.check('forecast_validation', total >= 500, 'usable_samples_below_policy', identity=key, samples=total)
            times = [instant(row.get(k)) for k in ('observed_until', 'received_at', 'issued_at')]
            target = row.get('target') or {}
            times += [instant(target.get(k)) for k in ('start', 'end')]
            a.check('forecast_timing', all(times) and times[0] <= times[1] <= times[2] < times[3] < times[4], 'non_prospective_forecast', identity=key)

    bindings = {}
    derived_counts = {}
    for name in OPPORTUNITY_BINDINGS:
        if not (root/name).exists():
            continue
        body = (root/name).read_bytes()
        bindings[name] = body
        hashes[name] = hashlib.sha256(body).hexdigest()
        doc = json.loads(body)
        if isinstance(doc.get('companies'), list):
            rows = doc['companies']
            derived_counts[name] = len(rows)
            for row in rows:
                base = by_symbol.get(row.get('symbol'))
                if not base:
                    continue
                for field in ('input_price', 'price'):
                    if field in row:
                        a.compare('derived_binding', row[field], base.get('price'), name+'.'+field, row.get('symbol'))
    try:
        verify_source_bindings(root, bindings)
        a.check('derived_binding', True, 'source_snapshots_aligned')
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        a.check('derived_binding', False, str(exc))

    sentiment = read('fear-greed-data.json')
    korea = read('stock-korea-fear-greed.json')
    def check_sentiment(node, path):
        if isinstance(node, dict):
            for k, value in node.items():
                if k in ('score', 'value') and number(value) is not None:
                    a.check('sentiment', 0 <= value <= 100, 'sentiment_out_of_range', field=path+'.'+k, value=value)
                elif isinstance(value, (dict, list)):
                    check_sentiment(value, path+'.'+k)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                check_sentiment(value, path+'['+str(i)+']')
    check_sentiment(sentiment, 'US')
    check_sentiment(korea, 'KR')
    check_sentiment_observations(a, sentiment, korea, now, expected['KR'])

    world = None
    if (root/'stock-world-flow.json').exists():
        from scripts.build_stock_world_flow import validate_document
        try:
            world_document = read('stock-world-flow.json')
            world = validate_document(world_document)
            a.check('world_flow', world['contract_verified'] is True, 'world_flow_contract')
            generated = instant(world_document.get('generated_at'))
            a.check('world_flow', generated is not None and generated <= now, 'world_flow_future_generation')
            world['at_audit_time'] = world_current_counts(world_document, now)
            if world['at_audit_time'].get('current', 0) != world['total']:
                a.warn('world_flow', 'not_all_observations_current_at_audit_time', counts=world['at_audit_time'])
        except (ValueError, KeyError, TypeError, AssertionError) as exc:
            a.check('world_flow', False, str(exc))
    else:
        a.warn('world_flow', 'feed_not_collected')
    if require_current:
        a.check('release_freshness', quote_counts['current'] == len(companies), 'quotes_not_all_current', counts=dict(quote_counts))
        a.check('release_freshness', not missing_charts and chart_counts['stale'] == 0 and chart_counts['unavailable'] == 0, 'charts_not_all_current', counts=dict(chart_counts))
        a.check('release_freshness', world is not None and world.get('at_audit_time', {}).get('current', 0) == world.get('total'),
                'world_flow_missing_or_not_current', counts=world)
    if currency_unknown:
        a.warn('financial_units', 'financial_currency_unverified_display_must_withhold_currency_label', symbols=currency_unknown)
    return {
        'version': 'stock-display-number-audit-v1', 'checked_at': now.isoformat(),
        'status': 'passed_with_limitations' if not a.errors else 'failed',
        'checks': dict(a.checks), 'check_count': sum(a.checks.values()),
        'errors': a.errors, 'warnings': a.warnings,
        'quantization_checks': a.quantization_checks,
        'coverage': {'catalogue': catalog['counts'], 'detailed_research': len(companies),
                     'quotes': dict(quote_counts), 'charts': dict(chart_counts),
                     'expected_completed_sessions': expected, 'ai': dict(statuses),
                     'official_financial_available': available, 'world_flow': world,
                     'derived_records': derived_counts},
        'source_sha256': hashes,
        'limitations': ['Arithmetic and source contracts are checked; vendor facts and forecasts are not guaranteed.',
                       'Analyst estimates/targets remain estimates; model probabilities are research outputs, not observed success rates.',
                       'Official financial coverage is selected reported accounts with explicit periods, not all companies or full statements.',
                       'Historical evaluation and immutable observation ledgers are not rewritten.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=Path('stock-display-number-audit.json'))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--require-current', action='store_true')
    args = parser.parse_args()
    result = audit(args.root, require_current=args.require_current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'check_count', 'coverage')}, ensure_ascii=False))
    print('ERRORS', len(result['errors']), 'WARNINGS', len(result['warnings']))
    if args.check and result['errors']:
        for error in result['errors'][:25]:
            print(json.dumps(error, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
