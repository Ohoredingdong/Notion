"""Preserve the two source observations behind a displayed annual revenue change.

This verifies a source contract and arithmetic.  A provider response is never
promoted to an independently verified filing, and no missing denominator is
reconstructed from a rounded percentage.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

VERSION = 'annual-revenue-comparison-v1'


def finite(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def day(value):
    try:
        result = date.fromisoformat(value)
        return result if result.isoformat() == value else None
    except (TypeError, ValueError):
        return None


def source_rows_digest(source_rows):
    wire = json.dumps(source_rows, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(wire.encode('utf-8')).hexdigest()


def comparison_issues(evidence, *, symbol=None, currency=None, current=None,
                      period=None, previous=None, published_growth=None, now=None):
    """Recheck the saved observations without trusting a saved 'verified' flag."""
    e = evidence if isinstance(evidence, dict) else {}
    issues = []
    if e.get('version') != VERSION:
        return ['version_missing_or_unknown']
    src = e.get('source') or {}
    rows = e.get('source_rows') or {}
    if not isinstance(src, dict) or not isinstance(rows, dict):
        return ['invalid_source_rows']
    cur, old = rows.get('current') or {}, rows.get('prior') or {}
    meta = rows.get('metadata') or {}
    if not all(isinstance(v, dict) for v in (cur, old, meta)):
        return ['invalid_source_rows']
    name = src.get('name')
    if name not in ('SEC CompanyFacts', 'OpenDART', 'Yahoo Finance'):
        issues.append('unknown_source')
    url = urlsplit(str(src.get('url') or ''))
    hosts = {'SEC CompanyFacts': ('data.sec.gov',),
             'OpenDART': ('opendart.fss.or.kr',),
             'Yahoo Finance': ('finance.yahoo.com',)}
    if url.scheme != 'https' or url.hostname not in hosts.get(name, ()) or url.username or url.password:
        issues.append('invalid_source_url')
    if src.get('identity_verified') is not True or not src.get('provider_symbol'):
        issues.append('source_identity_unverified')
    if not e.get('symbol') or (symbol is not None and e.get('symbol') != symbol):
        issues.append('symbol_mismatch')
    ccy = src.get('currency')
    if not isinstance(ccy, str) or not re.fullmatch('[A-Z]{3}', ccy):
        issues.append('source_currency_unverified')
    if currency is not None and ccy != currency:
        issues.append('currency_mismatch')
    if src.get('period_kind') != 'annual':
        issues.append('nonannual_source')
    account = src.get('account')
    if not account or cur.get('account') != account or old.get('account') != account:
        issues.append('account_mismatch')
    new, prev = finite(cur.get('value')), finite(old.get('value'))
    if new is None or new < 0:
        issues.append('invalid_current_revenue')
    if prev is None or prev <= 0:
        issues.append('invalid_previous_revenue')
    end, prior_end = day(cur.get('period')), day(old.get('period'))
    if end is None or prior_end is None or not 300 <= (end-prior_end).days <= 380:
        issues.append('annual_periods_not_consecutive')
    for label, point in (('current', cur), ('prior', old)):
        if point.get('start') is not None:
            start, finish = day(point.get('start')), day(point.get('period'))
            if start is None or finish is None or not 300 <= (finish-start).days <= 380:
                issues.append(label+'_duration_not_annual')
    if cur.get('start') and prior_end and day(cur['start']) and day(cur['start']) <= prior_end:
        issues.append('annual_periods_overlap')
    try:
        observed = datetime.fromisoformat(str(src.get('observed_at')).replace('Z', '+00:00'))
        if (observed.tzinfo is None or observed > (now or datetime.now(timezone.utc)) or
                (end and end > observed.date())):
            issues.append('invalid_observation_time')
    except (TypeError, ValueError):
        issues.append('invalid_observation_time')
    if name == 'Yahoo Finance':
        if (meta.get('provider_symbol') != src.get('provider_symbol') or
                str(src.get('provider_symbol')).removesuffix('.KS').removesuffix('.KQ') != e.get('symbol') or
                url.path != '/quote/'+str(src.get('provider_symbol'))+'/financials/' or
                meta.get('financial_currency') != ccy or meta.get('frequency') != 'yearly' or
                meta.get('quote_type') != 'EQUITY'):
            issues.append('yahoo_statement_identity_mismatch')
    elif name == 'OpenDART':
        if (meta.get('stock_code') != e.get('symbol') or
                meta.get('corp_code') != src.get('provider_symbol') or
                meta.get('reprt_code') != '11011' or meta.get('fs_div') != 'CFS' or
                meta.get('sj_div') not in ('IS', 'CIS') or url.path != '/api/fnlttMultiAcnt.json' or
                meta.get('currency') != ccy or
                not re.fullmatch(r'\d{14}', str(meta.get('rcept_no') or '')) or
                (end and str(meta.get('bsns_year')) != str(end.year))):
            issues.append('dart_statement_identity_mismatch')
    elif name == 'SEC CompanyFacts':
        cik = str(src.get('provider_symbol') or '')
        if (str(meta.get('cik')) != src.get('provider_symbol') or
                not cik.isdigit() or url.path != '/api/xbrl/companyfacts/CIK'+cik.zfill(10)+'.json' or
                meta.get('unit') != ccy or meta.get('taxonomy') != 'us-gaap' or
                not meta.get('accession') or cur.get('accession') != meta.get('accession') or
                old.get('accession') != meta.get('accession') or
                cur.get('form') not in ('10-K', '10-K/A') or
                old.get('form') not in ('10-K', '10-K/A')):
            issues.append('sec_statement_identity_mismatch')
    try:
        if e.get('source_rows_sha256') != source_rows_digest(rows):
            issues.append('source_rows_digest_mismatch')
    except (TypeError, ValueError):
        issues.append('invalid_source_rows')
    if current is not None and finite(current) != new:
        issues.append('current_amount_mismatch')
    if previous is not None and finite(previous) != prev:
        issues.append('previous_amount_mismatch')
    if period is not None and cur.get('period') != period:
        issues.append('current_period_mismatch')
    expected = (new/prev-1)*100 if new is not None and prev is not None and prev > 0 else None
    if e.get('published_decimal_places') != 2:
        issues.append('unknown_published_precision')
    exact = finite(e.get('calculated_growth_pct'))
    # Values may pass through the existing eight-decimal JSON serializer.
    if expected is None or exact is None or abs(exact-expected) > 5.1e-9:
        issues.append('calculated_growth_mismatch')
    saved = finite(e.get('published_growth_pct'))
    if expected is None or saved != round(expected, 2):
        issues.append('published_growth_mismatch')
    if published_growth is not None and finite(published_growth) != saved:
        issues.append('displayed_growth_mismatch')
    return sorted(set(issues))


def revenue_comparison(*, symbol, source_name, source_url, provider_symbol,
                       currency, account, current, prior, metadata,
                       identity_verified=True, observed_at=None):
    def json_safe(value):
        if isinstance(value, dict):
            return {key: json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [json_safe(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    rows = json_safe({'current': copy.deepcopy(current), 'prior': copy.deepcopy(prior),
                      'metadata': copy.deepcopy(metadata)})
    new, old = finite(current.get('value')), finite(prior.get('value'))
    exact = (new/old-1)*100 if new is not None and old is not None and old > 0 else None
    evidence = {
        'version': VERSION, 'symbol': symbol,
        'source': {'name': source_name, 'url': source_url,
                   'provider_symbol': provider_symbol, 'currency': currency,
                   'account': account, 'period_kind': 'annual',
                   'identity_verified': identity_verified,
                   'observed_at': observed_at or datetime.now(timezone.utc).isoformat()},
        'source_rows': rows, 'source_rows_sha256': source_rows_digest(rows),
        'source_rows_scope': 'selected_annual_revenue_observations_and_identity',
        'calculated_growth_pct': exact,
        'published_growth_pct': round(exact, 2) if exact is not None else None,
        'published_decimal_places': 2,
        'verification_scope': 'source_contract_and_arithmetic; independent_filing_comparison_is_separate',
    }
    issues = comparison_issues(evidence)
    evidence.update(status='verified' if not issues else 'withheld', issues=issues)
    return {'revenue_previous': old if not issues else None,
            'revenue_previous_period': prior.get('period') if not issues else None,
            'revenue_growth': evidence['published_growth_pct'] if not issues else None,
            'revenue_growth_decimal_places': 2,
            'revenue_growth_evidence': evidence}
