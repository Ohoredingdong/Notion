"""Validate an explicit, source-bound XBRL balance precision attestation.

No relative tolerance or fallback precision is accepted. The source facts must
match this issuer, filing, consolidated context, period, unit, and every amount.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import re

PRECISION_VERSION = "official-xbrl-balance-precision-v1"
BALANCE_CONCEPTS = {"assets": "Assets", "liabilities": "Liabilities", "equity": "Equity"}
CONSOLIDATION_AXIS = "ifrs-full:ConsolidatedAndSeparateFinancialStatementsAxis"
CONSOLIDATED_MEMBER = "ifrs-full:ConsolidatedMember"
DART_SCHEME = "http://dart.fss.or.kr/ifrs/CIK"
XBRL_ENDPOINT = "https://opendart.fss.or.kr/api/fnlttXbrl.xml"


def decimal_amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def precision_facts_check(record, evidence):
    """Return recomputed evidence only if the complete binding is valid."""
    if not isinstance(evidence, dict) or evidence.get("version") != PRECISION_VERSION:
        return None
    if record.get("country") != "KR" or record.get("currency") != "KRW" or record.get("consolidation") != "CFS":
        return None
    issuer = evidence.get("issuer") or {}
    if issuer != {"symbol": record.get("symbol"), "corp_code": record.get("corp_code")}:
        return None
    if not re.fullmatch(r"\d{8}", str(issuer.get("corp_code", ""))):
        return None
    source = evidence.get("source") or {}
    if (source.get("endpoint") != XBRL_ENDPOINT or source.get("rcept_no") != record.get("rcept_no")
            or str(source.get("reprt_code")) != str(record.get("report_code"))
            or str(source.get("bsns_year")) != str(record.get("report_year"))):
        return None
    if not re.fullmatch(r"\d{14}", str(source.get("rcept_no", ""))):
        return None
    for key in ("package_sha256", "instance_sha256", "artifact_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(source.get(key, ""))):
            return None
    if source.get("instance_member") != f"entity{record.get('corp_code')}_{record.get('period_end')}.xbrl":
        return None
    received, verified = timestamp(source.get("received_at")), timestamp(evidence.get("verified_at"))
    if received is None or verified is None or received > verified or verified > datetime.now(timezone.utc):
        return None
    context = evidence.get("context") or {}
    if (context.get("identifiers") != [{"scheme": DART_SCHEME, "value": record.get("corp_code")}]
            or context.get("period") != {"instant": record.get("period_end")}
            or context.get("dimensions") != [{"kind": "explicitMember", "dimension": CONSOLIDATION_AXIS,
                                               "value": CONSOLIDATED_MEMBER}]):
        return None
    context_ref, unit_ref = evidence.get("context_ref"), evidence.get("unit_ref")
    if not isinstance(context_ref, str) or not context_ref or unit_ref != "KRW":
        return None
    if evidence.get("unit") != {"measures": ["iso4217:KRW"], "has_divide": False}:
        return None
    facts = evidence.get("facts") or {}
    metrics = record.get("metrics") or {}
    if set(facts) != set(BALANCE_CONCEPTS):
        return None
    with localcontext() as ctx:
        ctx.prec = 80
        intervals, amounts, decimals = {}, {}, {}
        for key, concept in BALANCE_CONCEPTS.items():
            fact = facts[key]
            if not isinstance(fact, dict):
                return None
            if (fact.get("context_ref") != context_ref or fact.get("unit_ref") != unit_ref
                    or fact.get("nil") not in (None, "false", "0")
                    or not re.fullmatch(r"\{https://xbrl\.ifrs\.org/taxonomy/\d{4}-\d{2}-\d{2}/ifrs-full\}" + concept,
                                        str(fact.get("concept", "")))):
                return None
            amount, published = decimal_amount(fact.get("value")), decimal_amount(metrics.get(key))
            declared = fact.get("decimals")
            if amount is None or published is None or amount != published:
                return None
            if declared == "INF":
                half = Decimal(0)
            elif isinstance(declared, str) and re.fullmatch(r"[+-]?\d{1,3}", declared) and -18 <= int(declared) <= 18:
                quantum = Decimal(10) ** -int(declared)
                if amount % quantum != 0:
                    return None
                half = quantum / 2
            else:
                return None
            intervals[key] = (amount - half, amount + half)
            amounts[key], decimals[key] = amount, declared
        crosschecks = evidence.get("api_crosschecks")
        if not isinstance(crosschecks, list) or len(crosschecks) != 2 or {row.get("endpoint") for row in crosschecks} != {"fnlttMultiAcnt.json", "fnlttSinglAcntAll.json"}:
            return None
        for api in crosschecks:
            rows = api.get("rows") or []
            if (not re.fullmatch(r"[0-9a-f]{64}", str(api.get("sha256", "")))
                    or timestamp(api.get("received_at")) is None or len(rows) != 3
                    or {row.get("field") for row in rows} != set(BALANCE_CONCEPTS)):
                return None
            for row in rows:
                if (row.get("corp_code") != record.get("corp_code") or row.get("rcept_no") != record.get("rcept_no")
                        or row.get("currency") != "KRW" or row.get("sj_div") != "BS"
                        or (api["endpoint"] == "fnlttMultiAcnt.json" and row.get("fs_div") != "CFS")
                        or decimal_amount(str(row.get("thstrm_amount", "")).replace(",", "")) != amounts[row["field"]]):
                    return None
        difference = amounts["assets"] - amounts["liabilities"] - amounts["equity"]
        lower = intervals["assets"][0] - intervals["liabilities"][1] - intervals["equity"][1]
        upper = intervals["assets"][1] - intervals["liabilities"][0] - intervals["equity"][0]
        if difference != 0 and not lower < 0 < upper:
            return None
        return {"verified": True, "version": PRECISION_VERSION, "reported_difference": str(difference),
                "difference_interval": [str(lower), str(upper)], "declared_decimals": decimals,
                "source_rcept_no": source["rcept_no"], "source_package_sha256": source["package_sha256"],
                "note": "Exact reported values retained; the reported balance difference is inside the source-declared precision intervals."}


def verified_balance_precision(record):
    """Public contract for the collector, validator and independent auditor."""
    validation = (record.get("account_validation") or {}).get("balance_sheet") or {}
    if validation.get("status") != "verified_with_declared_precision":
        return None
    try:
        checked = precision_facts_check(record, validation.get("source_precision"))
        if checked is None:
            return None
        if (decimal_amount(validation.get("reported_difference")) != decimal_amount(checked["reported_difference"])
                or validation.get("difference_interval") != checked["difference_interval"]
                or validation.get("declared_decimals") != checked["declared_decimals"]
                or validation.get("reported_values_unchanged") is not True):
            return None
        return checked
    except (TypeError, ValueError, KeyError, InvalidOperation):
        return None
