#!/usr/bin/env python3
"""Observed global market references, with explicit units and completed dates.

This feed describes six selected markets, not a weighted world index. Yahoo
daily bars are unofficial quotes. Treasury BC_10YEAR is an official percent
series. Provider dates never become invented observation timestamps.

Primary methodology references are emitted in each record. Network collection
is serial and bounded; a Yahoo rate-limit circuit never blocks Treasury.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time as day_time, timedelta, timezone
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

UTC = timezone.utc
VERSION = 'stock-world-flow-v1'
CALENDAR_VERSION = '4.13.1'
TREASURY_BASE = ('https://home.treasury.gov/resource-center/data-chart-center/'
                 'interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=')
TREASURY_METHOD = 'https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics'
SIFMA_CALENDAR = 'https://www.sifma.org/resources/general/holiday-schedule'
ICE_METHOD = 'https://www.ice.com/publicdocs/data/ICE_FX_Indexes_Methodology.pdf'
VIX_METHOD = 'https://cdn.cboe.com/resources/vix/VIX_Methodology.pdf'
CALENDAR_SOURCE = 'https://github.com/gerrymanoim/exchange_calendars/tree/v4.13.1'


@dataclass(frozen=True)
class Indicator:
    id: str
    label: str
    region: str
    category: str
    symbol: str
    calendar: str
    zones: tuple[str, ...]
    exchanges: tuple[str, ...]
    instrument: str
    quote_currency: str | None
    unit: str = 'index_points'
    currency: str | None = None
    quote_basis: str = 'exchange_regular_close'
    note: str = ''


INDICATORS = (
    Indicator('kospi', '코스피', 'KR', 'index', '^KS11', 'XKRX', ('Asia/Seoul',), ('KSC',), 'INDEX', 'KRW'),
    Indicator('kosdaq', '코스닥', 'KR', 'index', '^KQ11', 'XKRX', ('Asia/Seoul',), ('KOE',), 'INDEX', 'KRW'),
    Indicator('sp500', 'S&P 500', 'US', 'index', '^GSPC', 'XNYS', ('America/New_York',), ('SNP',), 'INDEX', 'USD'),
    Indicator('nasdaq', '나스닥 종합', 'US', 'index', '^IXIC', 'XNYS', ('America/New_York',), ('NIM', 'NAS'), 'INDEX', 'USD'),
    Indicator('dax', '독일 DAX', 'EU', 'index', '^GDAXI', 'XETR', ('Europe/Berlin',), ('GER',), 'INDEX', 'EUR', note='독일 주식시장 참고 지수이며 유럽 전체 지수가 아닙니다.'),
    Indicator('shanghai', '상하이 종합', 'CN', 'index', '000001.SS', 'XSHG', ('Asia/Shanghai',), ('SHH',), 'INDEX', 'CNY'),
    Indicator('nikkei225', '닛케이 225', 'JP', 'index', '^N225', 'XTKS', ('Asia/Tokyo',), ('OSA',), 'INDEX', 'JPY'),
    Indicator('hang_seng', '항셍', 'HK', 'index', '^HSI', 'XHKG', ('Asia/Hong_Kong',), ('HKG',), 'INDEX', 'HKD'),
    Indicator('usdkrw', '달러/원', 'GLOBAL', 'fx', 'KRW=X', '24/5', ('Europe/London', 'UTC', 'Etc/UTC'), ('CCY',), 'CURRENCY', 'KRW', 'KRW_per_USD', 'KRW', 'provider_daily_close', 'Yahoo의 일별 환율이며 서울 외환시장 공식 종가가 아닙니다.'),
    Indicator('dxy', '달러지수', 'GLOBAL', 'index', 'DX-Y.NYB', 'IEPA', ('America/New_York',), ('NYB',), 'INDEX', 'USD', quote_basis='provider_daily_close', note='ICE 달러지수의 Yahoo 일별 자료; 선물 계약 가격이 아닙니다.'),
    Indicator('us10y', '미 국채 10년', 'US', 'yield', 'BC_10YEAR', 'SIFMA_US_2026', ('America/New_York',), (), 'PAR_YIELD', None, 'percent', None, 'treasury_par_yield', '재무부 10년 par yield. 원문 단위는 %, 변화는 bp(1bp=0.01%p)입니다.'),
    Indicator('wti', 'WTI 선물', 'GLOBAL', 'commodity', 'CL=F', 'us_futures', ('America/New_York',), ('NYM',), 'FUTURE', 'USD', 'USD_per_barrel', 'USD', 'provider_daily_close', 'Yahoo 연속선물 일별 가격; 현물 가격이나 거래소 공식 정산가가 아니며 만기 교체 영향을 포함할 수 있습니다.'),
    Indicator('gold', '금 선물', 'GLOBAL', 'commodity', 'GC=F', 'us_futures', ('America/New_York',), ('CMX',), 'FUTURE', 'USD', 'USD_per_troy_ounce', 'USD', 'provider_daily_close', 'Yahoo 연속선물 일별 가격; 현물 가격이나 거래소 공식 정산가가 아니며 만기 교체 영향을 포함할 수 있습니다.'),
    Indicator('vix', 'VIX', 'US', 'volatility', '^VIX', 'XCBF', ('America/Chicago', 'America/New_York'), ('WCBF', 'CBO', 'CXI'), 'INDEX', 'USD', note='SPX 옵션으로 계산한 30일 기대 변동성 지수입니다. 주가 방향이나 수익 확률이 아닙니다.'),
)
BY_ID = {item.id: item for item in INDICATORS}
REGIONS = (
    ('KR', '한국', ('kospi', 'kosdaq'), '코스피·코스닥의 각 완료 정규장'),
    ('US', '미국', ('sp500', 'nasdaq'), 'S&P 500·나스닥 종합의 각 완료 정규장'),
    ('EU', '유럽 · 독일 참고', ('dax',), '독일 DAX만 포함; 유럽 전체 시장 수익률이 아님'),
    ('CN', '중국 · 상하이 참고', ('shanghai',), '상하이 종합만 포함'),
    ('JP', '일본', ('nikkei225',), '닛케이 225 참고'),
    ('HK', '홍콩', ('hang_seng',), '항셍 참고'),
)

# SIFMA's published 2026 US full closures. Good Friday 2026 is an early close,
# not a full closure. Source above; unsupported years fail closed, not weekday
# guesses. Publication recheck at 18:00 ET is OUR policy, not a Treasury SLA.
TREASURY_HOLIDAYS_2026 = frozenset((
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-05-25', '2026-06-19',
    '2026-07-03', '2026-09-07', '2026-10-12', '2026-11-11', '2026-11-26', '2026-12-25',
))


def stamp(value: Any) -> datetime:
    if hasattr(value, 'to_pydatetime'):
        value = value.to_pydatetime()
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, TypeError) as exc:
        raise ValueError('invalid_timestamp') from exc
    if result.tzinfo is None:
        raise ValueError('timestamp_timezone_required')
    return result.astimezone(UTC)


def iso(value: datetime) -> str:
    return stamp(value).isoformat().replace('+00:00', 'Z')


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (ValueError, TypeError, OverflowError):
        return None


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False, default=str).encode()).hexdigest()


def source_url(spec: Indicator, year: int) -> str:
    return TREASURY_BASE + str(year) if spec.id == 'us10y' else 'https://finance.yahoo.com/quote/' + urllib.parse.quote(spec.symbol, safe='') + '/history/'


@lru_cache(maxsize=32)
def calendar(name: str, year: int):
    import exchange_calendars as xc
    if xc.__version__ != CALENDAR_VERSION:
        raise ValueError('unverified_calendar_version:' + xc.__version__)
    # XSHG 4.13.1 has authoritative precomputed holidays only through 2026.
    # Never infer its 2027 holidays or silently fall back to weekdays.
    end_year = min(year + 1, 2026) if name == 'XSHG' else year + 1
    if end_year < year:
        raise ValueError('calendar_coverage_expired:XSHG')
    return xc.get_calendar(name, start=f'{year-1}-01-01', end=f'{end_year}-12-31')


def valid_treasury_day(day: date) -> bool:
    if day.year != 2026:
        raise ValueError('treasury_publication_calendar_coverage_expired')
    return day.weekday() < 5 and day.isoformat() not in TREASURY_HOLIDAYS_2026


def treasury_adjacent(day: date, step: int) -> date:
    for _ in range(14):
        day += timedelta(days=step)
        if valid_treasury_day(day):
            return day
    raise ValueError('treasury_calendar_gap')


def treasury_clock(now: datetime) -> dict:
    local = stamp(now).astimezone(ZoneInfo('America/New_York'))
    day = local.date()
    if not valid_treasury_day(day) or local.time() < day_time(18):
        day = treasury_adjacent(day, -1)
    following = treasury_adjacent(day, 1)
    due = datetime.combine(following, day_time(18), ZoneInfo('America/New_York'))
    return {
        'basis': 'official_source_date_publication_recheck_policy',
        'calendar': 'SIFMA_US_2026', 'calendar_source': SIFMA_CALENDAR,
        'calendar_valid_through': '2026-12-31', 'timezone': 'America/New_York',
        'expected_session': day.isoformat(), 'next_expected_session': following.isoformat(),
        'next_check_after': iso(due), 'delay_minutes': None,
        'closed_at': None, 'next_close': None,
        'note': '공식 원문은 날짜만 제공합니다. 약 15:30 ET 호가를 바탕으로 한 자료이며 18:00 ET 재확인은 서비스 정책입니다. 공식 발표 보장 시각이 아닙니다.',
    }


def session_clock(spec: Indicator, now: datetime, source_zone: str | None = None) -> dict:
    now = stamp(now)
    if spec.id == 'us10y':
        return treasury_clock(now)
    cal = calendar(spec.calendar, now.year)
    zone = source_zone or spec.zones[0]
    local = now.astimezone(ZoneInfo(zone))
    label = cal.date_to_session(local.date().isoformat(), direction='previous')
    if spec.quote_basis == 'exchange_regular_close':
        def availability(day):
            return stamp(cal.session_close(day)) + timedelta(minutes=30)
        if availability(label) > now:
            label = cal.previous_session(label)
        following = cal.next_session(label)
        return {
            'basis': 'completed_exchange_session', 'calendar': spec.calendar,
            'calendar_version': CALENDAR_VERSION, 'calendar_source': CALENDAR_SOURCE,
            'calendar_valid_through': str(cal.last_session)[:10], 'timezone': str(cal.tz),
            'expected_session': str(label)[:10], 'closed_at': iso(cal.session_close(label)),
            'delay_minutes': 30, 'next_expected_session': str(following)[:10],
            'next_close': iso(cal.session_close(following)), 'next_check_after': iso(availability(following)),
            'note': '거래소 일정의 정규장 마감 후 30분을 수집 유예로 적용합니다. 임시 휴장은 원문 일정 재확인이 필요합니다.',
        }
    # Provider day bars in FX/futures/index products are not official settlement
    # prices. Wait until their entire LOCAL date has elapsed plus 30 min. Generic
    # calendars only delimit trading dates; no fictitious exchange close is used.
    def availability(day):
        end = date.fromisoformat(str(day)[:10]) + timedelta(days=1)
        return datetime.combine(end, day_time(), ZoneInfo(zone)).astimezone(UTC) + timedelta(minutes=30)
    if availability(label) > now:
        label = cal.previous_session(label)
    following = cal.next_session(label)
    return {
        'basis': 'elapsed_provider_local_date', 'calendar': spec.calendar,
        'calendar_version': CALENDAR_VERSION, 'calendar_source': CALENDAR_SOURCE,
        'calendar_valid_through': str(cal.last_session)[:10], 'timezone': zone,
        'expected_session': str(label)[:10], 'closed_at': None, 'next_close': None,
        'delay_minutes': 30, 'next_expected_session': str(following)[:10],
        'next_check_after': iso(availability(following)),
        'note': '공급자 현지 날짜 전체가 지난 일별 자료입니다. 일반 거래일 일정으로 재확인하며 공식 현물 종가·정산가·상품별 발표 시각을 뜻하지 않습니다.',
    }


def verify_metadata(spec: Indicator, metadata: dict) -> dict:
    if not isinstance(metadata, dict):
        raise ValueError('source_identity_missing')
    symbol = metadata.get('symbol')
    instrument = metadata.get('instrumentType') or metadata.get('quoteType')
    exchange = metadata.get('exchangeName')
    zone = metadata.get('exchangeTimezoneName')
    currency = metadata.get('currency')
    if symbol != spec.symbol:
        raise ValueError('source_symbol_mismatch:' + str(symbol))
    if instrument != spec.instrument:
        raise ValueError('source_instrument_mismatch:' + str(instrument))
    if exchange not in spec.exchanges:
        raise ValueError('source_exchange_mismatch:' + str(exchange))
    if zone not in spec.zones:
        raise ValueError('source_timezone_mismatch:' + str(zone))
    if currency != spec.quote_currency:
        raise ValueError('source_currency_mismatch:' + str(currency))
    return {'provider_symbol': spec.symbol, 'response_symbol': symbol,
            'instrument_type': instrument, 'exchange': exchange, 'timezone': zone,
            'quote_currency': currency, 'identity_verified': True}


def frame_points(frame, zone: str) -> tuple[list[tuple[str, float]], dict]:
    if frame is None or frame.empty or 'Close' not in frame:
        raise ValueError('source_history_missing')
    if frame.index.tz is None:
        raise ValueError('source_bar_timezone_missing')
    seen = set()
    points = []
    invalid = 0
    raw = []
    for timestamp, row in frame.iterrows():
        stamp_value = stamp(timestamp)
        day = stamp_value.astimezone(ZoneInfo(zone)).date().isoformat()
        if day in seen:
            raise ValueError('duplicate_source_date:' + day)
        seen.add(day)
        close = number(row['Close'])
        raw.append([iso(stamp_value), close])
        if close is None or close <= 0:
            invalid += 1
            continue
        points.append((day, close))
    return sorted(points), {'source_rows': len(raw), 'invalid_close_rows': invalid,
                            'parsed_rows_sha256': digest(raw)}


def blank_record(spec: Indicator, now: datetime, reason: str, attempted=False) -> dict:
    return {
        'id': spec.id, 'label': spec.label, 'region': spec.region,
        'category': spec.category, 'status': 'unavailable', 'reason': reason,
        'value': None, 'previous_value': None, 'change_value': None,
        'change_pct': None, 'change_bp': None, 'direction': 'unknown',
        'unit': spec.unit, 'currency': spec.currency, 'quote_basis': spec.quote_basis,
        'basis_note': spec.note, 'session': None, 'previous_session': None,
        'observed_at': None, 'previous_observed_at': None,
        'observed_at_precision': 'exchange_close' if spec.quote_basis == 'exchange_regular_close' else 'source_date',
        'received_at': None, 'expected_session': None,
        'comparison_verified': False, 'comparison_basis': None,
        'source_collection_attempted': attempted,
        'source': {'provider': 'US Treasury' if spec.id == 'us10y' else 'Yahoo Finance',
                   'url': source_url(spec, now.year), 'provider_symbol': spec.symbol,
                   'response_symbol': None, 'identity_verified': False,
                   'quote_currency': spec.quote_currency,
                   'methodology_url': TREASURY_METHOD if spec.id == 'us10y' else (VIX_METHOD if spec.id == 'vix' else ICE_METHOD if spec.id == 'dxy' else None)},
        'freshness': {'status': 'unavailable', 'reason': reason,
                      'next_expected_session': None, 'next_check_after': None},
    }


def make_record(spec: Indicator, points: list[tuple[str, float]], received_at: datetime,
                identity: dict, provenance: dict, *, now: datetime | None = None) -> dict:
    received_at = stamp(received_at)
    now = stamp(now or received_at)
    if received_at > now + timedelta(seconds=1):
        raise ValueError('receipt_after_evaluation')
    if identity.get('identity_verified') is not True or identity.get('provider_symbol') != spec.symbol or identity.get('response_symbol') != spec.symbol:
        raise ValueError('source_identity_unverified')
    clock = session_clock(spec, now, identity.get('timezone'))
    record = blank_record(spec, now, 'no_completed_source_date', True)
    record['received_at'] = iso(received_at)
    record['source'].update(identity)
    record['source']['provenance'] = provenance
    record['freshness'].update(clock)
    record['expected_session'] = clock['expected_session']
    series = {}
    seen = set()
    for day, value in points:
        parsed_day = date.fromisoformat(day)
        if day in seen:
            raise ValueError('duplicate_source_date:' + day)
        seen.add(day)
        value = number(value)
        if value is None or value < 0 or (spec.category != 'yield' and value == 0):
            raise ValueError('invalid_source_value')
        if spec.id == 'us10y':
            # Date-only official observations can arrive before our 18:00
            # recheck deadline. Accept only already-published local dates.
            valid = parsed_day <= now.astimezone(ZoneInfo('America/New_York')).date()
            valid = valid and valid_treasury_day(parsed_day)
        else:
            cal = calendar(spec.calendar, now.year)
            valid = day <= clock['expected_session'] and cal.is_session(day)
        if valid:
            series[day] = value
    if not series:
        return record
    current = max(series)
    if spec.id == 'us10y':
        prior = treasury_adjacent(date.fromisoformat(current), -1).isoformat()
        # An actual newer publication is evidence of completion; advance its
        # recheck, never keep yesterday's expected-date deadline in the past.
        if current > clock['expected_session']:
            following = treasury_adjacent(date.fromisoformat(current), 1)
            clock['next_expected_session'] = following.isoformat()
            clock['next_check_after'] = iso(datetime.combine(following, day_time(18), ZoneInfo('America/New_York')))
    else:
        cal = calendar(spec.calendar, now.year)
        prior = str(cal.previous_session(current))[:10]
    value, previous = series[current], series.get(prior)
    current_enough = current >= clock['expected_session']
    reason = None if current_enough else 'expected_session_not_received'
    if previous is None:
        reason = 'previous_session_missing' if current_enough else reason + ';previous_session_missing'
    status = 'current' if current_enough else 'stale'
    difference = value - previous if previous is not None else None
    percentage = (difference / previous) * 100 if previous is not None and previous > 0 and spec.category != 'yield' else None
    direction = 'unknown' if difference is None else 'up' if difference > 0 else 'down' if difference < 0 else 'flat'
    record.update({
        'status': status, 'reason': reason, 'value': value, 'previous_value': previous,
        'change_value': difference, 'change_pct': percentage,
        'change_bp': difference * 100 if difference is not None and spec.category == 'yield' else None,
        'direction': direction, 'session': current, 'previous_session': prior if previous is not None else None,
        'comparison_verified': previous is not None,
        'comparison_basis': 'previous_published_business_day' if spec.id == 'us10y' else 'previous_exchange_session' if spec.quote_basis == 'exchange_regular_close' else 'previous_provider_trading_date',
    })
    if spec.quote_basis == 'exchange_regular_close':
        record['observed_at'] = iso(cal.session_close(current))
        record['previous_observed_at'] = iso(cal.session_close(prior)) if previous is not None else None
    record['freshness'].update(clock)
    record['freshness'].update({'status': status, 'reason': reason})
    return record


def parse_treasury(xml: bytes) -> list[tuple[str, float]]:
    namespaces = {'a': 'http://www.w3.org/2005/Atom',
                  'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices'}
    root = ET.fromstring(xml)
    values = {}
    for entry in root.findall('a:entry', namespaces):
        d = entry.find('.//d:NEW_DATE', namespaces)
        v = entry.find('.//d:BC_10YEAR', namespaces)
        if d is None or v is None or not d.text:
            continue
        day = d.text[:10]
        date.fromisoformat(day)
        if day in values:
            raise ValueError('duplicate_treasury_date:' + day)
        value = number(v.text)
        if value is None:
            continue
        if value < 0:
            raise ValueError('invalid_treasury_percent')
        # BC_10YEAR is already percent. No /10, /100, price proxy, or yield
        # conversion from ^TNX is applied.
        values[day] = value
    if not values:
        raise ValueError('treasury_10year_field_missing')
    return sorted(values.items())


def read_news(path: Path | None, now: datetime) -> tuple[list[dict], dict]:
    context = {'status': 'unavailable', 'input_generated_at': None,
               'note': '관련 기사 제목입니다. 지수 변화의 원인으로 검증한 것이 아닙니다.'}
    if path is None or not path.exists():
        return [], context
    try:
        doc = json.loads(path.read_text())
        generated = stamp(doc['generated_at'])
        if generated > now + timedelta(minutes=5):
            raise ValueError('future_news_input')
    except (ValueError, KeyError, TypeError, OSError):
        return [], context
    context['input_generated_at'] = iso(generated)
    context['input_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    items = []
    seen = set()
    for item in doc.get('items', []):
        if not isinstance(item, dict) or item.get('source_tier') not in {'A', 'B', 'OFFICIAL'}:
            continue
        url = item.get('url')
        if not isinstance(url, str) or urllib.parse.urlsplit(url).scheme != 'https' or not urllib.parse.urlsplit(url).netloc:
            continue
        try:
            published = stamp(item['published_at'])
        except (ValueError, KeyError, TypeError):
            continue
        if not now - timedelta(hours=72) <= published <= now + timedelta(minutes=5) or url in seen:
            continue
        if not isinstance(item.get('title'), str) or not isinstance(item.get('source'), str):
            continue
        seen.add(url)
        items.append({'title': item['title'], 'source': item['source'], 'url': url,
                      'published_at': iso(published), 'region': item.get('region'),
                      'context_only': True})
    items.sort(key=lambda item: item['published_at'], reverse=True)
    context['status'] = 'stale' if doc.get('stale') or now - generated > timedelta(hours=24) else 'available' if items else 'unavailable'
    return items[:6], context


def summarise(records: list[dict]) -> tuple[list[dict], dict]:
    lookup = {row['id']: row for row in records}
    regions = []
    for region, label, indicator_ids, note in REGIONS:
        valid = [lookup[i] for i in indicator_ids if i in lookup and lookup[i]['status'] == 'current'
                 and lookup[i]['comparison_verified'] and lookup[i]['source']['identity_verified']]
        directions = {row['direction'] for row in valid}
        direction = 'unknown' if not directions else next(iter(directions)) if len(directions) == 1 else 'mixed'
        regions.append({'id': region, 'label': label, 'scope_note': note,
                        'indicator_ids': list(indicator_ids), 'basis_ids': [r['id'] for r in valid],
                        'direction': direction,
                        'status': 'current' if len(valid) == len(indicator_ids) else 'partial' if valid else 'unavailable'})
    counts = Counter(row['direction'] for row in regions if row['status'] == 'current')
    available = sum(counts.values())
    pieces = [f'상승 {counts["up"]}곳', f'하락 {counts["down"]}곳']
    if counts['mixed']:
        pieces.append(f'혼조 {counts["mixed"]}곳')
    if counts['flat']:
        pieces.append(f'보합 {counts["flat"]}곳')
    headline = f'확인된 {available}개 지역 참고지수 · ' + ' · '.join(pieces) if available else '완료 세션의 지역별 방향을 확인 중입니다.'
    return regions, {'headline': headline, 'regions_up': counts['up'], 'regions_down': counts['down'],
                     'regions_flat': counts['flat'], 'regions_mixed': counts['mixed'],
                     'regions_available': available, 'regions_total': len(REGIONS),
                     'basis_ids': [i for row in regions if row['status'] == 'current' for i in row['basis_ids']],
                     'comparison_note': '지역별 직전 거래일 대비입니다. 서로 다른 현지 마감 시각이며 세계 전체를 가중한 수익률이 아닙니다.'}


def validate_document(document: dict) -> dict:
    """Reconstruct each visible number/clock from the quoted comparison pair.

    This contract gate detects edited output, unit drift and mislabeled clocks;
    it is not an independent second quote provider. Frontend also recalculates
    changes and expires next_check_after using the viewer's current time.
    """
    if document.get('version') != VERSION:
        raise ValueError('world_flow_version_mismatch')
    completed = stamp(document.get('generated_at'))
    run = document.get('run') or {}
    if stamp(run.get('completed_at')) != completed or stamp(run.get('started_at')) > completed:
        raise ValueError('world_flow_run_clock_invalid')
    records = document.get('indicators') or []
    if len(records) != len(INDICATORS) or [r.get('id') for r in records] != [s.id for s in INDICATORS]:
        raise ValueError('world_flow_indicator_manifest_mismatch')
    for row, spec in zip(records, INDICATORS):
        if row.get('unit') != spec.unit or row.get('currency') != spec.currency or row.get('category') != spec.category or row.get('quote_basis') != spec.quote_basis:
            raise ValueError('world_flow_unit_or_basis_mismatch:' + spec.id)
        source = row.get('source') or {}
        if source.get('url') != source_url(spec, completed.year) or source.get('provider_symbol') != spec.symbol:
            raise ValueError('world_flow_source_mismatch:' + spec.id)
        if row.get('status') == 'unavailable':
            if any(row.get(k) is not None for k in ('value', 'previous_value', 'change_value', 'change_pct', 'change_bp')) or row.get('comparison_verified') is not False or row.get('direction') != 'unknown':
                raise ValueError('world_flow_unavailable_number_present:' + spec.id)
            continue
        if row.get('status') not in {'current', 'stale'}:
            raise ValueError('world_flow_unknown_status:' + spec.id)
        if source.get('identity_verified') is not True or source.get('response_symbol') != spec.symbol:
            raise ValueError('world_flow_identity_unverified:' + spec.id)
        if spec.id != 'us10y':
            verify_metadata(spec, {'symbol': source.get('response_symbol'),
                                  'instrumentType': source.get('instrument_type'),
                                  'exchangeName': source.get('exchange'),
                                  'exchangeTimezoneName': source.get('timezone'),
                                  'currency': source.get('quote_currency')})
        elif source.get('field') != 'BC_10YEAR' or source.get('source_unit') != 'percent':
            raise ValueError('world_flow_treasury_field_invalid')
        received = stamp(row.get('received_at'))
        if not stamp(run['started_at']) <= received <= completed:
            raise ValueError('world_flow_receipt_outside_run:' + spec.id)
        points = [(row.get('session'), row.get('value'))]
        if row.get('previous_value') is not None:
            points.insert(0, (row.get('previous_session'), row.get('previous_value')))
        expected = make_record(spec, points, received, source, source.get('provenance') or {}, now=completed)
        for key in ('value', 'previous_value', 'change_value', 'change_pct', 'change_bp'):
            a, b = row.get(key), expected[key]
            if (a is None) != (b is None) or (a is not None and (number(a) is None or not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10))):
                raise ValueError('world_flow_arithmetic_mismatch:' + spec.id + ':' + key)
        for key in ('status', 'direction', 'comparison_verified', 'comparison_basis',
                    'observed_at', 'previous_observed_at', 'observed_at_precision', 'session', 'previous_session', 'expected_session'):
            if row.get(key) != expected[key]:
                raise ValueError('world_flow_semantic_mismatch:' + spec.id + ':' + key)
        for key in ('basis', 'calendar', 'expected_session', 'next_expected_session', 'next_check_after', 'closed_at', 'next_close'):
            if (row.get('freshness') or {}).get(key) != expected['freshness'].get(key):
                raise ValueError('world_flow_freshness_mismatch:' + spec.id + ':' + key)
        if row.get('observed_at') is not None and stamp(row['observed_at']) > received:
            raise ValueError('world_flow_observation_after_receipt:' + spec.id)
    regions, summary = summarise(records)
    if document.get('regions') != regions or document.get('summary') != summary:
        raise ValueError('world_flow_summary_mismatch')
    counts = Counter(row['status'] for row in records)
    expected_counts = {'total': len(records), 'current': counts['current'], 'stale': counts['stale'],
                       'unavailable': counts['unavailable'],
                       'attempted': sum(bool(row['source_collection_attempted']) for row in records),
                       'comparison_verified': sum(bool(row['comparison_verified']) for row in records)}
    if any(run.get(k) != v for k, v in expected_counts.items()):
        raise ValueError('world_flow_count_mismatch')
    status = 'complete' if counts['current'] == len(records) and all(r['comparison_verified'] for r in records) else 'partial' if any(r['value'] is not None for r in records) else 'unavailable'
    if document.get('status') != status:
        raise ValueError('world_flow_status_mismatch')
    return {'contract_verified': True, 'status': status, **expected_counts}


class Collector:
    def __init__(self, *, timeout=20, request_delay=.75, max_seconds=240,
                 now_fn=None, monotonic_fn=None, sleep_fn=None, yahoo_fn=None, xml_fn=None):
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        self.monotonic = monotonic_fn or time.monotonic
        self.sleep = sleep_fn or time.sleep
        self.timeout = timeout
        self.request_delay = request_delay
        self.deadline = self.monotonic() + max_seconds
        self.yahoo_fn = yahoo_fn or self.fetch_yahoo
        self.xml_fn = xml_fn or self.fetch_xml
        self.stats = Counter()
        self.yahoo_circuit_open = False

    def remaining(self):
        return max(0, self.deadline - self.monotonic())

    @staticmethod
    def fetch_yahoo(spec: Indicator, timeout: float):
        import yfinance as yf
        if yf.__version__ != '0.2.66':
            raise ValueError('unverified_yfinance_version:' + yf.__version__)
        ticker = yf.Ticker(spec.symbol)
        frame = ticker.history(period='3mo', interval='1d', auto_adjust=False,
                               actions=False, prepost=False, repair=False,
                               timeout=timeout, raise_errors=True)
        # 0.2.66 history() fills this metadata from the SAME chart response.
        # Public get_history_metadata() may request a second 5d/1h history.
        metadata = getattr(getattr(ticker, '_price_history', None), '_history_metadata', None)
        return frame, metadata

    @staticmethod
    def fetch_xml(url: str, timeout: float):
        req = urllib.request.Request(url, headers={'User-Agent': 'InvestmentRadar/1.0', 'Accept': 'application/xml'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read(4_000_000)

    def call(self, fn, *args):
        if self.remaining() <= self.request_delay + 1:
            raise TimeoutError('collection_deadline_exhausted')
        if self.request_delay:
            self.sleep(min(self.request_delay, self.remaining()))
        return fn(*args, min(self.timeout, max(1, self.remaining())))

    def collect_yahoo(self, spec: Indicator) -> dict:
        now = stamp(self.now_fn())
        if self.yahoo_circuit_open:
            return blank_record(spec, now, 'yahoo_rate_limit_circuit_open')
        if self.remaining() <= self.request_delay + 1:
            return blank_record(spec, now, 'collection_deadline_exhausted')
        metadata = None
        received = None
        for attempt in range(2):
            try:
                self.stats['yahoo_calls'] += 1
                frame, metadata = self.call(self.yahoo_fn, spec)
                received = stamp(self.now_fn())  # only AFTER network completion
                identity = verify_metadata(spec, metadata)
                points, provenance = frame_points(frame, identity['timezone'])
                provenance['metadata_sha256'] = digest(metadata)
                return make_record(spec, points, received, identity, provenance)
            except Exception as exc:
                message = str(exc)
                limited = '429' in message or 'ratelimit' in type(exc).__name__.lower() or 'rate limit' in message.lower() or 'too many requests' in message.lower()
                if limited:
                    self.stats['yahoo_rate_limits'] += 1
                    if attempt == 0 and self.remaining() > 4:
                        self.sleep(2)
                        continue
                    self.yahoo_circuit_open = True
                result = blank_record(spec, stamp(self.now_fn()),
                                      'yahoo_rate_limited' if limited else type(exc).__name__ + ':' + message[:180], True)
                result['received_at'] = iso(received) if received else None
                if isinstance(metadata, dict):
                    result['source']['response_symbol'] = metadata.get('symbol')
                    result['source']['observed_metadata'] = {key: metadata.get(key) for key in ('symbol', 'instrumentType', 'exchangeName', 'exchangeTimezoneName', 'currency')}
                return result
        raise AssertionError('unreachable')

    def collect_treasury(self) -> dict:
        spec = BY_ID['us10y']
        now = stamp(self.now_fn())
        if self.remaining() <= self.request_delay + 1:
            return blank_record(spec, now, 'collection_deadline_exhausted')
        try:
            self.stats['treasury_calls'] += 1
            url = source_url(spec, now.year)
            xml = self.call(self.xml_fn, url)
            received = stamp(self.now_fn())
            points = parse_treasury(xml)
            identity = {'provider_symbol': 'BC_10YEAR', 'response_symbol': 'BC_10YEAR',
                        'identity_verified': True, 'timezone': 'America/New_York',
                        'quote_currency': None, 'field': 'BC_10YEAR', 'source_unit': 'percent'}
            return make_record(spec, points, received, identity,
                               {'raw_response_sha256': hashlib.sha256(xml).hexdigest(), 'source_rows': len(points)})
        except Exception as exc:
            return blank_record(spec, stamp(self.now_fn()), type(exc).__name__ + ':' + str(exc)[:180], True)

    def run(self, news_path: Path | None = None) -> dict:
        started = stamp(self.now_fn())
        # An unrelated blocked Yahoo endpoint must not suppress official yields.
        lookup = {'us10y': self.collect_treasury()}
        for spec in INDICATORS:
            if spec.id == 'us10y':
                continue
            lookup[spec.id] = self.collect_yahoo(spec)
            row = lookup[spec.id]
            print(f'{spec.id}: {row["status"]} session={row["session"]} reason={row["reason"]}', flush=True)
        completed = stamp(self.now_fn())
        records = [lookup[spec.id] for spec in INDICATORS]
        # Collection can cross a session deadline. Re-evaluate freshness at
        # completed_at while preserving each real network receipt and quote.
        for index, (row, spec) in enumerate(zip(records, INDICATORS)):
            if row['value'] is None:
                continue
            points = [(row['session'], row['value'])]
            if row['previous_value'] is not None:
                points.insert(0, (row['previous_session'], row['previous_value']))
            records[index] = make_record(spec, points, stamp(row['received_at']),
                                         row['source'], row['source']['provenance'], now=completed)
        regions, summary = summarise(records)
        news, context = read_news(news_path, completed)
        counts = Counter(row['status'] for row in records)
        document = {
            'version': VERSION, 'generated_at': iso(completed),
            'status': 'complete' if counts['current'] == len(records) and all(r['comparison_verified'] for r in records) else 'partial' if any(r['value'] is not None for r in records) else 'unavailable',
            'scope_note': '한국·미국·독일·상하이·일본·홍콩의 참고 지수와 환율·금리·선물·변동성 자료입니다. 전 세계 모든 시장 또는 같은 시각의 수익률이 아닙니다.',
            'run': {'started_at': iso(started), 'completed_at': iso(completed),
                    'total': len(records), 'current': counts['current'], 'stale': counts['stale'],
                    'unavailable': counts['unavailable'],
                    'attempted': sum(bool(r['source_collection_attempted']) for r in records),
                    'comparison_verified': sum(bool(r['comparison_verified']) for r in records),
                    'collector_calls': dict(self.stats), 'yahoo_rate_limit_circuit_open': self.yahoo_circuit_open,
                    'call_count_note': '수집기 호출 수이며 yfinance 내부 HTTP 요청 수는 아닙니다.'},
            'indicators': records, 'regions': regions, 'summary': summary,
            'related_news': news, 'news_context': context,
        }
        validate_document(document)
        return document


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('stock-world-flow.json'))
    parser.add_argument('--news', type=Path, default=Path('news-link-data.json'))
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--request-delay', type=float, default=.75)
    parser.add_argument('--max-seconds', type=float, default=240)
    parser.add_argument('--validate', type=Path, help='Validate an existing feed without network calls.')
    args = parser.parse_args(argv)
    if args.validate:
        print(json.dumps(validate_document(json.loads(args.validate.read_text())), ensure_ascii=False))
        return 0
    if not 1 <= args.timeout <= 60 or not 0 <= args.request_delay <= 10 or not 5 <= args.max_seconds <= 600:
        parser.error('bounded timeout/delay/deadline required')
    document = Collector(timeout=args.timeout, request_delay=args.request_delay,
                         max_seconds=args.max_seconds).run(args.news)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_name(args.output.name + '.tmp')
    tmp.write_text(json.dumps(document, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    tmp.replace(args.output)
    print(json.dumps({'output': str(args.output), 'status': document['status'], 'run': document['run']}, ensure_ascii=False))
    # Partial failures are retained explicitly in the feed. The caller may set a
    # stricter release gate; absence of every real value is a collector failure.
    return 1 if document['status'] == 'unavailable' else 0


if __name__ == '__main__':
    sys.exit(main())
