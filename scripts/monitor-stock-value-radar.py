"""Monitor the feeds actually consumed by the canonical radar, not its retired 10-stock page."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from market_data_utils import finite, market_session_clock, utc_stamp

UTC = timezone.utc
FILES = {
    'opportunity': 'stock-opportunity-data.json',
    'cases': 'stock-investment-cases-summary.json',
    'entry': 'stock-entry-plan-summary.json',
    'charts': 'stock-radar-chart-data.json',
    'forecast': 'stock-direction-forecast.json',
    'learning': 'stock-forecast-learning.json',
    'accuracy': 'stock-radar-accuracy-audit.json',
    'market': 'stock-market-context.json',
    'news': 'news-link-data.json',
    'calendar': 'market-events-data.json',
    'events': 'stock-event-outlook.json',
}
EXTENDED = {
    'catalog': 'stock-universe-catalog.json',
    'financial': 'stock-financial-coverage.json',
    'extended_forecast': 'stock-extended-direction-forecast.json',
}
INDEX_MARKETS = {'^KS11': 'KR', '^KQ11': 'KR', '^GSPC': 'US', '^IXIC': 'US'}
MACRO_MARKETS = {'kospi': 'KR', 'kosdaq': 'KR', 'sp500': 'US', 'nasdaq': 'US'}


def read(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (ValueError, OSError):
        return {}


def full_universe_state(feed, catalog, now, clock_fn=market_session_clock):
    """Validate the daily exception against actual identities and this run's rows.

    This is a read-only health contract, independent of the training dependency
    stack. A fresh wrapper alone cannot make old issuance evidence current.
    """
    policy = 'kr-six-character-alphanumeric-v2'
    if (feed.get('generation_mode') != 'full_universe' or
            feed.get('version') != 'stock-extended-direction-v1' or
            feed.get('source_identity_policy') != policy or
            catalog.get('identifier_policy') != policy or catalog.get('status') != 'complete' or
            feed.get('automatic_orders') is not False):
        raise ValueError('full_universe_policy_mismatch')
    items, records = catalog.get('items'), feed.get('records')
    if not isinstance(items, list) or not items or not isinstance(records, list):
        raise ValueError('full_universe_records_missing')
    expected, aliases = {}, Counter()
    for item in items:
        country, symbol, exchange = item['country'], item['symbol'], item['exchange']
        key = country + ':' + symbol
        if (country not in ('KR', 'US') or key in expected or not item.get('name') or not exchange or
                not isinstance(symbol, str) or symbol != symbol.strip().upper()):
            raise ValueError('full_universe_catalog_identity_invalid')
        if country == 'KR':
            if not re.fullmatch(r'[0-9A-Z]{6}', symbol) or item.get('source_symbol') != symbol:
                raise ValueError('full_universe_korean_identity_invalid')
            suffix = {'KOSPI': '.KS', 'KOSDAQ': '.KQ'}.get(exchange)
            provider = symbol + suffix if suffix else None
        else:
            provider = symbol.replace('.', '-') if re.fullmatch(r'[A-Z]{1,5}(?:[.-][A-Z])?', symbol) else None
        expected[key] = (item, provider)
        if provider:
            aliases[provider] += 1
    countries = Counter(item['country'] for item in items)
    if (catalog.get('counts', {}).get('total') != len(items) or
            any(catalog['counts'].get(country) != countries[country] for country in ('KR', 'US')) or
            len(records) != len(items)):
        raise ValueError('full_universe_catalog_record_count_mismatch')

    def stamp(value):
        parsed = utc_stamp(value)
        if parsed is None:
            raise ValueError('full_universe_timestamp_missing')
        return parsed

    def digest(value, length=64):
        return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value)

    run, coverage = feed.get('run') or {}, feed.get('coverage') or {}
    started, completed, generated = (stamp(value) for value in
                                    (run.get('started_at'), run.get('completed_at'), feed.get('generated_at')))
    if not started <= completed == generated <= now:
        raise ValueError('full_universe_run_timestamp_mismatch')
    if (not feed.get('run_id') or feed['run_id'] != run.get('id') or
            not digest(feed.get('source_commit'), 40) or feed['source_commit'] != run.get('source_commit') or
            not digest(feed.get('manifest_sha256')) or feed['manifest_sha256'] != run.get('manifest_sha256') or
            not digest(feed.get('source_catalog_sha256')) or feed['source_catalog_sha256'] != run.get('catalog_sha256') or
            not isinstance(feed.get('implementation_sha256'), dict) or not feed['implementation_sha256'] or
            feed['implementation_sha256'] != run.get('implementation_sha256') or
            any(not digest(value) for value in feed['implementation_sha256'].values())):
        raise ValueError('full_universe_run_provenance_mismatch')
    shards, shard_count = run.get('shards'), run.get('shard_count')
    if type(shard_count) is not int or not 1 <= shard_count <= 128 or not isinstance(shards, list) or len(shards) != shard_count:
        raise ValueError('full_universe_shards_missing')
    shard_by_index = {}
    for shard in shards:
        index = shard.get('index')
        if type(index) is not int or not 0 <= index < shard_count or index in shard_by_index or not digest(shard.get('sha256')):
            raise ValueError('full_universe_shard_identity_invalid')
        a, b = stamp(shard.get('started_at')), stamp(shard.get('completed_at'))
        if not started <= a <= b <= completed:
            raise ValueError('full_universe_shard_time_invalid')
        shard_by_index[index] = (shard, a, b)
    if min(value[1] for value in shard_by_index.values()) != started:
        raise ValueError('full_universe_run_start_not_bound_to_shards')
    assigned = {key: i % shard_count for i, key in enumerate(sorted(expected))}
    counts = Counter(total=len(records))
    errors, seen, shard_rows = Counter(), set(), Counter()
    active, expired, session_targets = Counter(), Counter(), {}
    for row in records:
        key = row.get('key')
        if key not in expected or key in seen:
            raise ValueError('full_universe_record_identity_missing_or_duplicate')
        seen.add(key)
        item, provider = expected[key]
        provider = provider if provider and aliases[provider] == 1 else None
        identity = {'market': item['country'], 'name': item['name'], 'catalog_name': item['name'],
                    'catalog_symbol': item['symbol'], 'catalog_exchange': item['exchange'],
                    'provider_symbol': provider, 'symbol': provider or item['symbol']}
        if (any(row.get(field) != value for field, value in identity.items()) or
                row.get('identity_verified') is not True or row.get('source_identity_policy') != policy or
                row.get('mode') != 'daily' or row.get('recommendation') is not False or row.get('live_validated') is not False):
            raise ValueError('full_universe_record_identity_mismatch')
        shard, shard_start, shard_end = shard_by_index[assigned[key]]
        issued = stamp(row.get('issued_at'))
        if not shard_start <= issued <= shard_end:
            raise ValueError('full_universe_issuance_outside_current_run')
        shard_rows[assigned[key]] += 1
        collection, attempts = row.get('collection_status'), row.get('source_fetch_attempts')
        skipped = collection in ('circuit_skipped', 'deadline_skipped')
        if (collection not in ('fetched', 'cache_current', 'source_error', 'unsupported', 'circuit_skipped', 'deadline_skipped') or
                type(attempts) is not int or attempts < 0 or type(row.get('source_collection_attempted')) is not bool or
                row['source_collection_attempted'] != (attempts > 0) or
                ((skipped or collection in ('unsupported', 'cache_current')) and attempts) or
                ((collection == 'unsupported') != (provider is None)) or
                (collection == 'fetched' and not attempts) or type(row.get('price_available')) is not bool):
            raise ValueError('full_universe_source_attempt_count_invalid')
        counts['source_fetch_attempts'] += attempts
        counts['source_collection_attempted'] += row['source_collection_attempted']
        counts['price_available'] += row['price_available']
        counts['cache_current'] += collection == 'cache_current'
        counts['unsupported'] += collection == 'unsupported'
        if row['price_available']:
            price = row.get('price_provenance') or {}
            received = stamp(row.get('received_at'))
            if (collection not in ('fetched', 'cache_current') or row.get('source_identity_verified') is not True or
                    not provider or row.get('source_response_symbol') != provider or price.get('provider_symbol') != provider or
                    not digest(price.get('history_sha256')) or not digest(price.get('source_sha256')) or
                    not stamp(price.get('fetched_at')) <= received <= issued):
                raise ValueError('full_universe_price_provenance_invalid')
        if row.get('status') == 'no_call':
            if (any(row.get(field) is not None for field in ('probabilities', 'target', 'direction')) or
                    not row.get('reason') or not row.get('error_kind')):
                raise ValueError('full_universe_no_call_contains_prediction_or_lacks_reason')
            counts['not_attempted' if skipped else 'failed'] += 1
            errors[row['error_kind']] += 1
            continue
        if row.get('status') != 'research_prediction' or not row['price_available'] or skipped:
            raise ValueError('full_universe_prediction_without_price')
        if row.get('error_kind') is not None or row.get('reason') is not None:
            raise ValueError('full_universe_prediction_contains_failure_reason')
        probabilities = row.get('probabilities') or {}
        values = [finite(probabilities.get(name)) for name in ('down', 'flat', 'up')]
        target = row.get('target') or {}
        start, end, observed = stamp(target.get('start')), stamp(target.get('end')), stamp(row.get('observed_until'))
        direction = row.get('direction')
        if (set(probabilities) != {'down', 'flat', 'up'} or any(v is None or not 0 <= v <= 1 for v in values) or
                abs(sum(v or 0 for v in values)-1) > 1e-6 or direction not in probabilities or
                abs(probabilities[direction]-max(values)) > 1e-12 or not observed <= received <= issued < start < end):
            raise ValueError('full_universe_prediction_probability_or_time_invalid')
        session_key = (item['country'], observed)
        if session_key not in session_targets:
            session_targets[session_key] = clock_fn(item['country'], observed+timedelta(seconds=1), delay_minutes=0)
        session = session_targets[session_key]
        if (observed != stamp(session['closed_at']) or start != stamp(session['next_open']) or
                end != stamp(session['next_close']) or row.get('origin_session') != session['expected_session'] or
                price.get('last_session') != row.get('origin_session')):
            raise ValueError('full_universe_prediction_not_next_complete_exchange_session')
        counts['prediction'] += 1
        (active if end > now else expired)[item['country']] += 1
    counts['attempted'] = counts['prediction'] + counts['failed']
    counts['no_call'] = counts['failed'] + counts['not_attempted']
    keys = ('total', 'prediction', 'failed', 'not_attempted', 'attempted', 'no_call',
            'source_collection_attempted', 'source_fetch_attempts', 'price_available', 'cache_current', 'unsupported')
    if (seen != set(expected) or any(type(coverage.get(key)) is not int or coverage[key] != counts[key] for key in keys) or
            coverage.get('error_kinds') != dict(errors) or coverage.get('manifest_complete') is not True or
            coverage.get('coverage_complete') is not (counts['not_attempted'] == 0) or
            any(type(shard[0].get('records')) is not int or shard[0]['records'] != shard_rows[index]
                for index, shard in shard_by_index.items())):
        raise ValueError('full_universe_coverage_does_not_match_actual_records')
    run_counts = {'attempted': counts['attempted'], 'research_prediction': counts['prediction'],
                  'no_call': counts['failed'], 'failed': counts['failed'], 'not_attempted': counts['not_attempted'],
                  'source_collection_attempted': counts['source_collection_attempted'],
                  'source_fetch_attempts': counts['source_fetch_attempts'], 'retained_predictions': 0,
                  'retained_unexpired_after_no_call': 0}
    if any(type(run.get(key)) is not int or run[key] != value for key, value in run_counts.items()):
        raise ValueError('full_universe_run_counts_mismatch')
    due = started.replace(hour=6, minute=55, second=0, microsecond=0)
    if due <= started:
        due += timedelta(days=1)
    while due.weekday() >= 5:
        due += timedelta(days=1)
    return {'contract_verified': True, 'started_at': started.isoformat(), 'completed_at': completed.isoformat(),
            'next_due': due.isoformat(), 'deadline': (due+timedelta(hours=3)).isoformat(),
            'counts': {key: counts[key] for key in keys},
            'active_by_market': {market: active[market] for market in ('KR', 'US')},
            'expired_by_market': {market: expired[market] for market in ('KR', 'US')}}


def inspect(root=Path('.'), now=None, clock_fn=market_session_clock):
    root = Path(root)
    now = utc_stamp(now or datetime.now(UTC))
    if now is None:
        raise ValueError('timezone_required')
    old = read(root / 'stock-radar-health.json')
    page = (root / 'stock-value-radar.html').read_text() if (root / 'stock-value-radar.html').exists() else ''
    names = {**FILES, **(EXTENDED if 'stock-catalog-ui.js' in page else {})}
    feeds = {key: read(root / name) for key, name in names.items()}
    issues, warnings, ages, clocks, grace_clocks, sessions = [], [], {}, {}, {}, {}

    for market in ('KR', 'US'):
        try:
            clocks[market] = clock_fn(market, now, delay_minutes=30)
            # Allow the scheduled collector to finish after a new close. A fresh
            # outer generated_at must never reset this source-session deadline.
            grace_clocks[market] = clock_fn(market, now, delay_minutes=120)
        except Exception as exc:
            issues.append(f'{market} 완료 세션 달력 확인 실패: {type(exc).__name__}')
    active = any(value.get('market_open') for value in clocks.values())
    daily = None
    extended = feeds.get('extended_forecast') or {}
    if extended.get('generation_mode') == 'full_universe':
        try:
            daily = full_universe_state(extended, feeds.get('catalog') or {}, now, clock_fn)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            issues.append(f'extended_forecast: 전체 명부 일간 계약 확인 실패 ({exc})')

    for key, payload in feeds.items():
        if not payload:
            issues.append(f'{key}: 필수 자료가 없거나 JSON이 유효하지 않습니다.')
            continue
        generated = utc_stamp(payload.get('generated_at'))
        # The accuracy report is tied to source versions, not an invented
        # independent timestamp that could make old forecasts appear fresh.
        if key == 'accuracy':
            generated = utc_stamp((payload.get('source') or {}).get('forecasts_generated_at'))
        hours = (now - generated).total_seconds() / 3600 if generated else None
        ages[key] = {'file': names[key], 'generated_at': generated.isoformat() if generated else None,
                     'age_hours': round(hours, 2) if hours is not None else None}
        if hours is None or hours < -0.05:
            issues.append(f'{key}: 갱신 시각이 없거나 미래입니다.')
        limit = {'news': 6, 'calendar': 18, 'events': 18, 'catalog': 168, 'financial': 48}.get(key)
        if key == 'extended_forecast' and daily:
            ages[key].update(freshness_policy='weekday_0655_utc_plus_3h',
                             freshness_basis='run.started_at', next_due=daily['next_due'], deadline=daily['deadline'])
            if now > utc_stamp(daily['deadline']):
                issues.append(f"extended_forecast: 전체 AI 일간 갱신 지연 (다음 발행 {daily['next_due']}, 완료 기한 {daily['deadline']})")
        elif active and key in ('forecast', 'extended_forecast'):
            limit = 2
        if limit is not None:
            ages[key]['max_hours'] = limit
            if hours is not None and hours > limit:
                issues.append(f'{key}: {hours:.1f}시간 동안 갱신되지 않았습니다. (허용 {limit}시간)')

    for key in ('news', 'calendar'):
        if feeds.get(key, {}).get('stale') is True:
            issues.append(f'{key}: 제공처 수집 실패 또는 부분 실패 자료입니다. 새 생성시각만으로 정상 처리하지 않습니다.')
    event_data, calendar_data = feeds.get('events', {}), feeds.get('calendar', {})
    if event_data.get('calendar_fresh') is not True:
        issues.append('events: 현재 경제 일정 원자료의 신선도가 확인되지 않았습니다.')
    if event_data.get('source_calendar_generated_at') != calendar_data.get('generated_at'):
        issues.append('events: 경제 일정 원자료와 해석 스냅샷의 시점이 다릅니다.')

    def check_session(group, symbol, market, date, price, collected=None):
        record = {'symbol': str(symbol), 'market': market, 'session': date}
        sessions.setdefault(group, []).append(record)
        if finite(price) is None or finite(price) <= 0:
            record['problem'] = 'missing_or_invalid_price'
            return
        if market not in clocks:
            record['problem'] = 'calendar_unavailable'
            return
        try:
            datetime.strptime(str(date), '%Y-%m-%d')
        except (TypeError, ValueError):
            record['problem'] = 'missing_session'
            return
        expected = clocks[market]['expected_session']
        required = grace_clocks[market]['expected_session']
        record['expected_session'] = expected
        if date > expected:
            record['problem'] = 'unfinished_or_future_session'
        elif date < required:
            record['problem'] = 'stale_source_session'
        elif date < expected:
            record['pending_after_close'] = True
        if date == expected:
            fetched = utc_stamp(collected)
            available = utc_stamp(clocks[market]['available_at'])
            if fetched is None or fetched < available or fetched > now + timedelta(minutes=3):
                record['problem'] = 'close_not_confirmed_at_collection'

    raw = feeds.get('opportunity', {})
    rows = raw.get('companies') or []
    if not isinstance(rows, list):
        rows = []
    if any(not isinstance(row, dict) for row in rows):
        issues.append('opportunity: 종목 레코드 형식이 손상되었습니다.')
        rows = [row for row in rows if isinstance(row, dict)]
    symbols = [str(row.get('symbol')) for row in rows if isinstance(row, dict)]
    if not rows or len(symbols) != len(set(symbols)):
        issues.append('opportunity: 추적 종목이 없거나 중복된 종목 코드가 있습니다.')
    for row in rows:
        tech = row.get('technical') or {}
        integrity = row.get('source_integrity') or {}
        collected = row.get('collected_at') or integrity.get('fetched_at') or (integrity.get('price') or {}).get('fetched_at')
        check_session('opportunity', row.get('symbol'), row.get('market'),
                      row.get('price_session') or tech.get('date'), row.get('price'), collected)

    chart = feeds.get('charts', {})
    series = chart.get('series') or {}
    required_series = {str(row.get('symbol')): row.get('market') for row in rows}
    required_series.update(INDEX_MARKETS)
    for symbol, market in required_series.items():
        value = series.get(symbol) or {}
        bars = value.get('bars') or []
        last = bars[-1] if bars else {}
        check_session('charts', symbol, market, last.get('date'), last.get('close'), value.get('collected_at'))
        if value.get('price_session') != last.get('date') or value.get('status') not in ('ok', 'stale'):
            issues.append(f'charts: {symbol} 저장된 차트와 상태/기준일이 일치하지 않습니다.')
    if chart and chart.get('source_generated_at') != raw.get('generated_at'):
        issues.append('charts: 가격차트가 현재 종목 분석 스냅샷과 연결되어 있지 않습니다.')

    market_data = feeds.get('market', {})
    for key, market in MACRO_MARKETS.items():
        value = (market_data.get('indicators') or {}).get(key) or {}
        check_session('market', key, market, value.get('date'), value.get('value'), value.get('collected_at'))
        if value.get('price_basis') != 'completed_regular_session_close':
            issues.append(f'market: {key} 완료 정규장 기준인지 확인할 수 없습니다.')
    if market_data.get('errors'):
        warnings.append(f"market: 거시지표 수집 오류 {len(market_data['errors'])}건; 누락값을 최신값으로 취급하지 않습니다.")
    for group, values in sessions.items():
        bad = [value for value in values if value.get('problem')]
        pending = [value for value in values if value.get('pending_after_close')]
        if bad:
            kinds = sorted({value['problem'] for value in bad})
            issues.append(f'{group}: {len(bad)}/{len(values)}개 가격의 완료 세션·원자료 확인 실패 ({", ".join(kinds)})')
        if pending:
            warnings.append(f'{group}: 새 장 마감 후 수집 유예 중 {len(pending)}개. 새 종가 갱신 완료로 표시하지 않습니다.')

    forecast, learning = feeds.get('forecast', {}), feeds.get('learning', {})
    records = forecast.get('records') or []
    calls = [row for row in records if row.get('status') == 'research_prediction']
    invalid, expired = [], []
    for row in calls:
        start = utc_stamp((row.get('target') or {}).get('start'))
        end = utc_stamp((row.get('target') or {}).get('end'))
        issued = utc_stamp(row.get('issued_at'))
        probabilities = row.get('probabilities') or {}
        values = [finite(probabilities.get(name)) for name in ('down', 'flat', 'up')]
        if (not start or not end or not issued or not issued < start < end
                or any(value is None or not 0 <= value <= 1 for value in values)
                or abs(sum(value or 0 for value in values) - 1) > .025):
            invalid.append(str(row.get('symbol')))
        elif end < now - timedelta(hours=2):
            expired.append(str(row.get('symbol')))
    if invalid:
        issues.append(f'forecast: 유효하지 않은 발행시각·미래 타깃·확률 {len(invalid)}건')
    if expired:
        issues.append(f'forecast: 종료된 예측이 새 예측으로 교체되지 않은 기록 {len(expired)}건')
    if not records:
        issues.append('forecast: 예측/보류 기록이 없습니다.')
    if forecast.get('generated_at') != learning.get('generated_at'):
        issues.append('learning: 예측과 학습 평가의 스냅샷 시점이 다릅니다.')
    audit = feeds.get('accuracy', {})
    source = audit.get('source') or {}
    for key, actual in [('forecasts_generated_at', forecast.get('generated_at')),
                        ('learning_generated_at', learning.get('generated_at')),
                        ('opportunity_generated_at', raw.get('generated_at')),
                        ('chart_generated_at', chart.get('generated_at')),
                        ('market_generated_at', market_data.get('generated_at'))]:
        if not actual or source.get(key) != actual:
            issues.append(f'accuracy: 현재 자료와 감사 시점 불일치 ({key})')
    if audit and not (audit.get('data_integrity') or {}).get('check_passed'):
        issues.append('accuracy: 데이터 정합성 감사가 통과하지 않았습니다.')
    for name in ('cases', 'entry'):
        if feeds.get(name, {}).get('source_generated_at') != raw.get('generated_at'):
            raw_at = utc_stamp(raw.get('generated_at'))
            if raw_at and timedelta(0) <= now - raw_at <= timedelta(minutes=90):
                warnings.append(f'{name}: 새 종목 스냅샷 이후 후속 분석 생성 대기; 아직 현재 자료와 일치하지 않습니다.')
            else:
                issues.append(f'{name}: 현재 종목 자료를 바탕으로 생성된 분석이 아닙니다.')

    extra = {}
    if 'catalog' in names:
        catalog, finance, extended = (feeds.get(name, {}) for name in ('catalog', 'financial', 'extended_forecast'))
        extra['catalog_count'] = len(catalog.get('items') or [])
        extra['financial_available'] = finance.get('financial_available') or {}
        extra['financial_current_run'] = finance.get('run') or {}
        extra['financial_refresh_status'] = finance.get('refresh_status')
        extra['financial_current_run_failed'] = finance.get('current_run_failed')
        extra['financial_provider_readiness'] = finance.get('provider_readiness') or {}
        extra['financial_last_successful_observation_at'] = finance.get('last_successful_observation_at')
        extended_rows = extended.get('records') if isinstance(extended.get('records'), list) else []
        extra['extended_forecast_symbols'] = len({str(row.get('symbol')) for row in extended_rows if isinstance(row, dict) and row.get('status') == 'research_prediction'})
        if daily:
            extra['extended_forecast_daily'] = daily
            if daily['counts']['not_attempted']:
                issues.append(f"extended_forecast: 전체 명부 중 미처리 {daily['counts']['not_attempted']}개; 일간 생성 시각으로 수집 누락을 정상 처리하지 않습니다.")
            if daily['counts']['failed']:
                warnings.append(f"extended_forecast: 처리 후 예측 보류/실패 {daily['counts']['failed']}개. 실제 생성 수는 {daily['counts']['prediction']}개입니다.")
            for market, timing in clocks.items():
                if timing.get('market_open') and not daily['active_by_market'].get(market):
                    expired_count = daily['expired_by_market'].get(market, 0)
                    issues.append(f'extended_forecast {market}: 시장이 열려 있지만 유효한 일간 예측이 없습니다. (종료된 예측 {expired_count}개)')
        if catalog.get('identifier_policy') != 'kr-six-character-alphanumeric-v2':
            issues.append('catalog: 최신 종목 식별 정책으로 수집되지 않은 명부입니다.')
        if catalog.get('status') != 'complete':
            issues.append('catalog: 전체 명부 수집이 완료되지 않았습니다.')
        if finance.get('identity_policy') != 'official-issuer-identity-v2':
            issues.append('financial: 발행회사 식별 검증 정책이 적용되지 않았습니다.')
        if finance.get('catalog_generated_at') != catalog.get('generated_at'):
            issues.append('financial: 현재 명부 이후 재무 대조가 완료되지 않았습니다.')
        for region, run in (finance.get('run') or {}).items():
            if isinstance(run, dict) and (run.get('blocked') or run.get('refresh_status') in ('partial', 'blocked')):
                warnings.append(f'financial {region}: 이번 수집에 차단/부분 성공이 있습니다. 누적 보유량은 최신 수집 성공 건수가 아닙니다.')
        warnings.append('전체 명부 수와 재무 확인 수·유효한 AI 예측 수는 서로 다른 범위입니다.')

    issues, warnings = list(dict.fromkeys(issues)), list(dict.fromkeys(warnings))
    warnings.append('제공처 지연 자료와 연구 예측입니다. 감시 통과는 거래소 실시간 검증·예측력·수익성의 증거가 아닙니다.')
    failures = int(old.get('consecutive_failures') or 0) + 1 if issues else 0
    return {
        'version': 'canonical-radar-health-v2', 'checked_at': now.isoformat(),
        'status': 'error' if issues else 'warning' if warnings else 'ok',
        'consecutive_failures': failures, 'notification_required': bool(issues and failures >= 2),
        'data_ages': ages, 'session_clocks': clocks, 'session_checks': sessions,
        'coverage': {'tracked': len(rows), 'required_chart_series': len(required_series),
                     'chart_series_present': len(series), 'forecast_symbols': len({row.get('symbol') for row in calls}),
                     'forecast_records': len(records), 'research_predictions': len(calls),
                     'no_calls': sum(row.get('status') == 'no_call' for row in records), **extra},
        'monitored_files': names, 'issues': issues, 'warnings': warnings,
        'notice': '현재 화면이 사용하는 종목·예측·차트·뉴스·시장·감사 파일을 검사합니다. 장중 미완료 일봉과 오래된 원자료는 새 갱신시각으로 정상화하지 않습니다.',
        'repair_url': 'https://github.com/Ohoredingdong/Notion/actions/workflows/update-stock-opportunities.yml',
        'verification_url': 'https://github.com/Ohoredingdong/Notion/actions/workflows/monitor-stock-value-radar.yml',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = inspect()
    if not args.check:
        Path('stock-radar-health.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'coverage', 'issues', 'warnings')}, ensure_ascii=False))
    if args.check and result['issues']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

