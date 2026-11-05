"""Official-source financial coverage for the Korea/US issuer catalogue.

- SEC EDGAR XBRL companyfacts and KRX-listed companies' OpenDART reports only.
- Incremental, bounded; never invents EPS, revenue, price or probability.
- Preserves already verified records on a failed provider request.
- This is *reported* history, not an analyst EPS forecast or investment signal.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from xml.etree import ElementTree as ET
import zipfile

UTC = timezone.utc
VERSION = "official-financial-coverage-v1"
OUTPUT = Path("stock-financial-coverage.json")
QUARANTINE_OUTPUT = Path("data-quarantine/stock-financial-coverage.json")
CATALOG_POLICY = "kr-six-character-alphanumeric-v2"
IDENTITY_POLICY = "official-issuer-identity-v2"
PROJECT_AGENT = "GeoyeonInvestmentRadar/1.0 (+https://github.com/Ohoredingdong/Notion)"
SEC_CIK = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
DART_MAP = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_MULTI = "https://opendart.fss.or.kr/api/fnlttMultiAcnt.json"
DART_COMPANY = "https://opendart.fss.or.kr/api/company.json"
MAX_US_BATCH, MAX_KR_BATCH = 120, 3000
MAX_IDENTITY_LOOKUPS = 80
FINANCIAL_STATUSES = {"available", "partial", "stale"}
KR_SYMBOL = re.compile(r"[0-9A-Z]{6}")
FORMS = {"10-Q", "10-K", "20-F", "40-F"}
TAGS = {
    "revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet",
                "Revenue", "RevenueFromContractsWithCustomers"),
    "operating_income": ("OperatingIncomeLoss", "ProfitLossFromOperatingActivities"),
    "net_income": ("NetIncomeLoss", "ProfitLoss",
                   "NetIncomeLossAvailableToCommonStockholdersBasic",
                   "ProfitLossAttributableToOwnersOfParent"),
    "cash_from_operations": ("NetCashProvidedByUsedInOperatingActivities",
                             "CashFlowsFromUsedInOperatingActivities"),
    "capital_expenditure": ("PaymentsToAcquirePropertyPlantAndEquipment",
                            "PurchaseOfPropertyPlantAndEquipment",
                            "PaymentsToAcquireProductiveAssets"),
    "reported_eps": ("EarningsPerShareDiluted", "DilutedEarningsLossPerShare",
                     "EarningsPerShareBasic", "BasicEarningsLossPerShare"),
}
INSTANT_TAGS = {
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "equity": ("StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "Equity"),
    "cash_and_equivalents": ("CashAndCashEquivalentsAtCarryingValue", "CashAndCashEquivalents"),
}


def iso():
    return datetime.now(UTC).isoformat()


def json_file(path: Path, default):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"),
                              allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def safe_reason(error):
    # Do not persist API keys or signed query strings in a public status file.
    text = re.sub(r"(?i)(crtfc_key|api_key|token)=([^&\s]+)", r"\1=[redacted]", str(error))
    return text[:180]


def sec_contact_configured(agent):
    match = re.search(r"[A-Za-z0-9_.+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", agent or "")
    if not match or match.group(1).lower() in {"example.com", "example.org", "example.net"}:
        return False
    return len(re.sub(re.escape(match.group(0)), "", agent).strip(" ()<>/")) >= 3


def company_name_key(name):
    value = unicodedata.normalize("NFKC", str(name or "")).upper()
    for marker in ("주식회사", "유한회사", "(주)", "(유)", "(株)"):
        value = value.replace(marker, "")
    return re.sub(r"[\s·_.,()\-]", "", value)


def observed_date(value=None):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return datetime.now(UTC).date()


def reported_period_candidates(as_of):
    """Only request ended reporting periods, in actual chronological order."""
    periods = []
    for year in (as_of.year, as_of.year - 1):
        for code, month, day in (("11013", 3, 31), ("11012", 6, 30),
                                  ("11014", 9, 30), ("11011", 12, 31)):
            end = date(year, month, day)
            if end <= as_of:
                periods.append((end, year, code))
    return [(year, code) for _, year, code in sorted(periods, reverse=True)]


def read_url(url, *, agent, max_bytes=16_000_000, attempts=2):
    if not agent or len(agent.strip()) < 15:
        raise ValueError("source_user_agent_not_configured")
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if (host == "sec.gov" or host.endswith(".sec.gov")) and not sec_contact_configured(agent):
        raise ValueError("SEC_contact_user_agent_not_configured")
    error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": agent, "Accept": "application/json, application/zip, */*",
                "Accept-Encoding": "identity",
            })
            with urllib.request.urlopen(req, timeout=25) as r:
                payload = r.read(max_bytes + 1)
                if len(payload) > max_bytes:
                    raise ValueError("provider_response_exceeds_size_limit")
                return payload
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            error = exc
            if attempt + 1 < attempts and getattr(exc, "code", 0) in (403, 408, 429, 500, 502, 503, 504):
                time.sleep(1 + attempt)
                continue
            break
    raise RuntimeError(f"source_fetch_failed: {type(error).__name__}: {getattr(error, 'code', str(error))}")


def official_cik_map(raw):
    obj = json.loads(raw)
    fields = obj.get("fields") or []
    data = obj.get("data") or []
    try:
        symbol_i, cik_i = fields.index("ticker"), fields.index("cik")
    except ValueError as exc:
        raise ValueError("SEC_ticker_mapping_schema_invalid") from exc
    output = {}
    for row in data:
        if len(row) <= max(symbol_i, cik_i):
            continue
        symbol = str(row[symbol_i]).upper().strip()
        try:
            cik = int(row[cik_i])
        except (TypeError, ValueError):
            continue
        if symbol and cik > 0:
            output[symbol] = cik
    if not output:
        raise ValueError("empty_SEC_CIK_mapping")
    return output


def dart_corp_identities(raw):
    if not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ValueError("DART_corpCode_response_not_ZIP")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = [x for x in zf.namelist() if x.lower().endswith(".xml")]
        if not names:
            raise ValueError("DART_zip_missing_XML")
        document = ET.fromstring(zf.read(names[0]))
    found = {}
    for item in document.findall(".//list"):
        stock, corp = (item.findtext("stock_code") or "").strip(), (item.findtext("corp_code") or "").strip()
        stock = stock.upper()
        if KR_SYMBOL.fullmatch(stock) and re.fullmatch(r"[0-9]{8}", corp):
            row = {"stock_code": stock, "corp_code": corp,
                   "corp_name": (item.findtext("corp_name") or "").strip(),
                   "modify_date": (item.findtext("modify_date") or "").strip()}
            candidates = found.setdefault(stock, [])
            if not any(x["corp_code"] == corp for x in candidates):
                candidates.append(row)
    if not found:
        raise ValueError("empty_DART_corp_mapping")
    return found


def dart_corp_map(raw):
    # Compatibility helper: never silently choose between historical issuers
    # which happen to share a stock code.
    return {stock: rows[0]["corp_code"] for stock, rows in dart_corp_identities(raw).items()
            if len(rows) == 1}


def resolve_dart_identity(item, candidates, *, getter, key, agent, budget, checked_at):
    symbol, name = item["symbol"], company_name_key(item["name"])
    matching = [x for x in candidates if name and company_name_key(x["corp_name"]) == name]
    source = DART_MAP
    if len(matching) == 1:
        identity = matching[0]
    else:
        verified = []
        for candidate in candidates[:3]:
            if budget[0] <= 0:
                break
            budget[0] -= 1
            request = DART_COMPANY + "?" + urllib.parse.urlencode(
                {"crtfc_key": key, "corp_code": candidate["corp_code"]})
            response = json.loads(getter(request, agent=agent))
            if response.get("status") != "000":
                raise ValueError("DART_company_identity_" + str(response.get("status")))
            expected_market = {"KOSPI": "Y", "KOSDAQ": "K", "KONEX": "N"}.get(item.get("exchange"))
            if (response.get("stock_code") == symbol and
                    (not expected_market or response.get("corp_cls") == expected_market) and
                    name in {company_name_key(response.get("corp_name")),
                             company_name_key(response.get("stock_name"))}):
                verified.append({**candidate, "corp_name": response.get("corp_name") or
                                 candidate["corp_name"], "stock_name": response.get("stock_name")})
        if len(verified) != 1:
            return None
        identity, source = verified[0], DART_COMPANY
    return {**identity, "catalog_name": item["name"], "catalog_symbol": symbol,
            "official_symbol": symbol, "verified_at": checked_at,
            "source_url": source, "method": "official_symbol_corporation_and_name"}


def _xbrl_fact(facts, category, start=None, end=None):
    namespaces = ("us-gaap", "ifrs-full")
    target_unit = "USD/shares" if category == "reported_eps" else "USD"
    selections = []
    for namespace in namespaces:
        sec = facts.get(namespace) or {}
        for tag in TAGS[category]:
            concept = sec.get(tag) or {}
            for unit in concept.get("units", {}).get(target_unit, []):
                if unit.get("form") not in FORMS:
                    continue
                filing_date, period_end, period_start = unit.get("filed"), unit.get("end"), unit.get("start")
                if not (isinstance(filing_date, str) and isinstance(period_end, str)):
                    continue
                try:
                    filing = date.fromisoformat(filing_date)
                    end_day = date.fromisoformat(period_end)
                    beginning = date.fromisoformat(period_start) if period_start else None
                    value = float(unit["val"])
                except (ValueError, TypeError, KeyError):
                    continue
                if filing > date.today() or not beginning or not (60 <= (end_day - beginning).days <= 390):
                    continue
                if start is not None and period_start != start:
                    continue
                if end is not None and period_end != end:
                    continue
                selections.append((period_end, filing_date, value, period_start, tag, namespace,
                                   unit.get("accn"), unit.get("form")))
    return max(selections, key=lambda x: (x[0], x[1])) if selections else None


def _xbrl_instant(facts, category, period_end):
    found = []
    for namespace in ("us-gaap", "ifrs-full"):
        for tag in INSTANT_TAGS[category]:
            for row in (facts.get(namespace, {}).get(tag, {})
                        .get("units", {}).get("USD", [])):
                if row.get("form") not in FORMS or row.get("end") != period_end:
                    continue
                try:
                    filed = date.fromisoformat(str(row["filed"]))
                    val = float(row["val"])
                except (ValueError, KeyError, TypeError):
                    continue
                if filed <= date.today() and row.get("start") is None:
                    found.append((filed.isoformat(),val))
    return max(found, key=lambda x: x[0])[1] if found else None


def parse_sec_companyfacts(raw, *, symbol, cik, checked_at):
    obj = json.loads(raw)
    try:
        returned_cik = int(obj["cik"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("SEC_companyfacts_missing_issuer_identity") from None
    if returned_cik != int(cik):
        raise ValueError("SEC_companyfacts_issuer_identity_mismatch")
    facts = obj.get("facts") or {}
    core = [x for k in ("revenue", "net_income", "operating_income")
            if (x := _xbrl_fact(facts, k))]
    if not core:
        return {"symbol": symbol, "country": "US", "status": "no_comparable_facts",
                "checked_at": checked_at, "source": "SEC EDGAR XBRL",
                "source_url": SEC_FACTS.format(cik=cik),
                "reason": "No dated US-GAAP/IFRS companyfacts reporting matching categories"}
    # Choose one reporting interval. Never combine quarterly income with annual income.
    chosen = max(core, key=lambda x: (x[0], x[1]))
    begin, end = chosen[3], chosen[0]
    fields = {}
    for name in TAGS:
        fact = _xbrl_fact(facts, name, start=begin, end=end)
        fields[name] = fact[2] if fact else None
    for name in INSTANT_TAGS:
        fields[name] = _xbrl_instant(facts, name, end)
    ops, capex = fields["cash_from_operations"], fields["capital_expenditure"]
    fields["free_cash_flow"] = ops - capex if ops is not None and capex is not None else None
    present = sum(fields.get(k) is not None for k in ("revenue", "net_income", "operating_income"))
    filed = chosen[1]
    stale = (date.today() - date.fromisoformat(end)).days > 560
    return {"symbol": symbol, "country": "US", "status": ("stale" if stale else
            "available" if present>=2 else "partial"),
            "cik": returned_cik, "official_name": obj.get("entityName"),
            "identity_policy": IDENTITY_POLICY, "identity_verified": True,
            "identity": {"official_symbol": symbol, "cik": returned_cik,
                         "source_url": SEC_CIK, "verified_at": checked_at,
                         "method": "official_ticker_cik_and_companyfacts_cik"},
            "checked_at": checked_at, "source": "SEC EDGAR XBRL",
            "source_url": SEC_FACTS.format(cik=cik),
            "filing_date": filed, "period_start": begin, "period_end": end,
            "period_type": "quarter_or_year_as_reported", "currency": "USD",
            "annualized": False, "estimated": False,
            "full_financial_statements": False,
            "statement_scope": "selected_reported_accounts",
            "metrics": fields,
            "missing_metrics": [key for key, value in fields.items() if value is None],
            "limitations": ["XBRL reported facts; not forward-looking analyst EPS",
                            "FCF only if matching report interval operating cash & capex"]}


def _amount(value):
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    raw = str(value or "").strip().replace(",", "")
    if not raw or raw in ("-", "—", "N/A"):
        return None
    try:
        parsed = float(raw)
        return parsed if math.isfinite(parsed) else None
    except ValueError:
        return None


def parse_dart_multi(raw, *, corp_map, checked_at, report_year, report_code, identities=None):
    data = json.loads(raw)
    if data.get("status") == "013":
        return {}  # A not-yet-published report is not a provider failure.
    if data.get("status") != "000":
        raise ValueError("DART_response_"+str(data.get("status"))+"_"+str(data.get("message"))[:65])
    by_stock = {}
    mapping = {corp: sym for sym,corp in corp_map.items()}
    for entry in data.get("list") or []:
        stock = str(entry.get("stock_code") or "").strip().upper()
        expected_stock = mapping.get(entry.get("corp_code"))
        if expected_stock and stock != expected_stock:
            raise ValueError("DART_response_stock_corporation_mismatch")
        if stock not in corp_map:
            continue
        if entry.get("corp_code") and entry["corp_code"] != corp_map[stock]:
            raise ValueError("DART_response_corporation_mismatch")
        if str(entry.get("bsns_year", report_year)) != str(report_year) or str(
                entry.get("reprt_code", report_code)) != str(report_code):
            raise ValueError("DART_response_reporting_period_mismatch")
        by_stock.setdefault(stock, []).append(entry)
    out = {}
    latest_period_label={"11013": "Q1", "11012": "H1", "11014": "Q3", "11011": "FY"}[report_code]
    for stock, entries in by_stock.items():
        as_of = observed_date(checked_at)
        receipts = [str(r.get("rcept_no") or "") for r in entries
                    if re.fullmatch(r"[0-9]{14}", str(r.get("rcept_no") or "")) and
                    str(r["rcept_no"])[:8] <= as_of.strftime("%Y%m%d")]
        if not receipts:
            continue
        receipt = max(receipts)
        entries = [r for r in entries if str(r.get("rcept_no")) == receipt]
        # One actual filing, one consolidation basis and one currency per issuer.
        consolidated = [r for r in entries if r.get("fs_div") == "CFS"]
        rows = consolidated or [r for r in entries if r.get("fs_div") == "OFS"]
        currencies = {str(r.get("currency") or "").strip().upper() for r in rows}
        if len(currencies) != 1 or not next(iter(currencies), ""):
            raise ValueError("DART_report_currency_missing_or_inconsistent")
        currency = next(iter(currencies))
        vals = {}
        labels = {"revenue": ("매출액","영업수익","수익(매출액)"),
                  "operating_income": ("영업이익","영업이익(손실)"),
                  "net_income": ("당기순이익","당기순이익(손실)"),
                  "assets": ("자산총계",),
                  "liabilities": ("부채총계",),
                  "equity": ("자본총계",)}
        selected = {}
        for key,names in labels.items():
            for name in names:
                candidates=[r for r in rows if str(r.get("account_nm") or "").replace(" ","")==name.replace(" ","")
                            and r.get("sj_div") in (("BS",) if key in INSTANT_TAGS else ("IS", "CIS"))]
                candidate=next((x for x in candidates if _amount(x.get("thstrm_amount")) is not None or
                                _amount(x.get("thstrm_add_amount")) is not None),None)
                if candidate:
                    selected[key]=candidate
                    break
        ends = {}
        for key, row in selected.items():
            dates = []
            for year, month, day in re.findall(r"([0-9]{4})[.\-/]([0-9]{1,2})[.\-/]([0-9]{1,2})",
                                                str(row.get("thstrm_dt") or "")):
                try:
                    parsed = date(int(year), int(month), int(day))
                    if parsed <= as_of:
                        dates.append(parsed)
                except ValueError:
                    pass
            if dates:
                ends[key] = max(dates).isoformat()
        if not ends:
            continue
        end = max(ends.values())
        cumulative = report_code != "11011" and any(
            _amount(row.get("thstrm_add_amount")) is not None for key, row in selected.items()
            if key not in INSTANT_TAGS)
        metric_sources = {}
        for key, row in selected.items():
            if ends.get(key) != end:
                continue
            field = "thstrm_add_amount" if cumulative and key not in INSTANT_TAGS else "thstrm_amount"
            amount = _amount(row.get(field))
            if amount is not None:
                vals[key] = amount
                metric_sources[key] = {"field": field, "reported_period": row.get("thstrm_dt"),
                                       "rcept_no": receipt, "period_end": end}
        if not vals:
            continue
        identity = (identities or {}).get(stock)
        fields={"revenue":vals.get("revenue"),"operating_income":vals.get("operating_income"),
                "net_income":vals.get("net_income"),"assets":vals.get("assets"),
                "liabilities":vals.get("liabilities"),"equity":vals.get("equity"),
                "cash_and_equivalents":None,"cash_from_operations":None,
                "capital_expenditure":None,"free_cash_flow":None,"reported_eps":None}
        out[stock]={"symbol":stock,"country":"KR","status":"stale" if
                    (as_of-date.fromisoformat(end)).days>560 else "available" if len(vals)>=2 else "partial",
            "corp_code":corp_map[stock],"official_name":identity.get("corp_name") if identity else None,
            "identity_policy":IDENTITY_POLICY,"identity_verified":bool(identity),
            "identity":identity,"rcept_no":receipt,
            "checked_at":checked_at,"source":"DART periodic reports",
            "source_url":"https://dart.fss.or.kr/dsaf001/main.do?rcpNo="+receipt,
            "report_year":report_year,"report_code":report_code,
            "period_end_label":str(report_year)+"-"+latest_period_label,
            "period_end":end,"period_start":None,
            "income_amount_basis":"year_to_date_as_reported" if cumulative else "current_period_as_reported",
            "consolidation":"CFS" if consolidated else "OFS",
            "currency":currency,"annualized":False,"estimated":False,
            "full_financial_statements":False,"statement_scope":"selected_reported_accounts",
            "metrics":fields,"metric_sources":metric_sources,
            "missing_metrics":[key for key,value in fields.items() if value is None],
            "limitations":["Selected reported accounts, not a complete financial statement; do not annualize",
                           "Cashflow, FCF and forecast EPS not obtained in multi-account endpoint"]}
    return out


def choose(items, cursor, country, count):
    selected = [x for x in items if x.get("country") == country and x.get("symbol")]
    if not selected or count <= 0:
        return [], 0 if not selected else (cursor % len(selected))
    position = cursor % len(selected)
    count = min(len(selected), count)
    return (selected[position:position+count] +
            selected[:max(0,position+count-len(selected))]), (position+count) % len(selected)


def period_order(record):
    if record.get("period_end"):
        return str(record["period_end"])
    match = re.fullmatch(r"([0-9]{4})-(Q1|H1|Q3|FY)", str(record.get("period_end_label") or ""))
    return (match[1] + {"Q1":"-03-31","H1":"-06-30","Q3":"-09-30","FY":"-12-31"}[match[2]]
            if match else "")


def verified_financial_record(record, key=None, item=None):
    if (record.get("status") not in FINANCIAL_STATUSES or record.get("identity_verified") is not True or
            record.get("identity_policy") != IDENTITY_POLICY or not isinstance(record.get("metrics"), dict)):
        return False
    symbol, country = record.get("symbol"), record.get("country")
    identity = record.get("identity") or {}
    if key is not None and key != f"{country}:{symbol}":
        return False
    if identity.get("official_symbol") != symbol:
        return False
    if country == "KR":
        if not (KR_SYMBOL.fullmatch(str(symbol or "")) and
                re.fullmatch(r"[0-9]{8}", str(record.get("corp_code") or "")) and
                identity.get("corp_code") == record["corp_code"]):
            return False
    elif country == "US":
        if not isinstance(record.get("cik"), int) or record["cik"] <= 0 or identity.get("cik") != record["cik"]:
            return False
    else:
        return False
    if item and (item.get("country") != country or item.get("symbol") != symbol or
                 company_name_key(record.get("catalog_name")) != company_name_key(item.get("name"))):
        return False
    if item and any(item.get(field) is not None and item[field] != record.get(field)
                    for field in ("corp_code","cik")):
        return False
    return all(value is None or (isinstance(value, (int, float)) and math.isfinite(value))
               for value in record["metrics"].values())


def isolate_unverified_records(root, prior, items, checked_at):
    """Keep the original bytes' meaning in an archive, never relabel bad issuers."""
    allowed = {x["country"]+":"+x["symbol"]:x for x in items}
    archive = json_file(root/QUARANTINE_OUTPUT, {"version":"official-financial-identity-quarantine-v1",
        "not_for_display_or_analysis":True,"records":[]})
    fingerprints = {x["sha256"] for x in archive["records"]}
    kept, changed = {}, False
    for key, record in (prior.get("records") or {}).items():
        if not isinstance(record, dict):
            reason = "malformed_record"
        elif key not in allowed:
            reason = "identifier_absent_from_corrected_official_catalogue"
        elif any(allowed[key].get(field) is not None and allowed[key][field] != record.get(field)
                 for field in ("corp_code","cik")):
            reason = "official_issuer_mapping_changed"
        elif record.get("metrics") is not None or record.get("status") in FINANCIAL_STATUSES:
            reason = None if verified_financial_record(record, key, allowed[key]) else "issuer_identity_not_verified"
        else:
            reason = None if key == f"{record.get('country')}:{record.get('symbol')}" else "identifier_key_mismatch"
        if not reason:
            kept[key] = record
            continue
        digest = hashlib.sha256(json.dumps([key,record], ensure_ascii=False, sort_keys=True,
                                          separators=(",",":")).encode()).hexdigest()
        if digest not in fingerprints:
            archive["records"].append({"sha256":digest,"previous_key":key,"reason":reason,
                "quarantined_at":checked_at,"source_generated_at":prior.get("generated_at"),"record":record})
            fingerprints.add(digest)
            changed = True
    if changed:
        archive["updated_at"] = checked_at
        write_json(root/QUARANTINE_OUTPUT, archive)
    return kept, len(archive["records"])


def merge_record(previous, latest):
    if not previous:
        return latest
    issuer_key="corp_code" if previous.get("country")=="KR" else "cik"
    if ((latest.get("identity_verified") is True or latest.get("issuer_mapping_verified") is True) and
            latest.get(issuer_key) is not None and previous.get(issuer_key)!=latest[issuer_key]):
        return latest  # A reused ticker is not the same issuer's reporting history.
    # A temporary outage must not erase a previous real financial statement.
    if verified_financial_record(previous) and latest.get("status") not in FINANCIAL_STATUSES:
        old={**previous}
        old["last_refresh_error"]={"at":latest.get("checked_at"),"reason":latest.get("reason",latest.get("status"))}
        return old
    if verified_financial_record(previous) and verified_financial_record(latest):
        # A delayed provider/cache response may not roll reporting periods backward.
        if period_order(latest) < period_order(previous):
            return previous
    return latest


def build(root=Path("."), *, us_batch=60, kr_batch=240, getter=None,
          agent=None, dart_agent=None, dart_key=None, throttle=0.30, as_of=None):
    root=Path(root)
    catalog=json_file(root/"stock-universe-catalog.json",{})
    items=catalog.get("items") or []
    if not items or catalog.get("counts",{}).get("total")!=len(items):
        raise RuntimeError("verified_issuer_catalog_missing_or_incomplete")
    if catalog.get("identifier_policy") != CATALOG_POLICY:
        raise RuntimeError("catalogue_requires_alphanumeric_identifier_rebuild")
    if catalog.get("status") != "complete":
        raise RuntimeError("catalogue_source_refresh_incomplete_preserve_previous_financial_snapshot")
    if any(x.get("country") == "KR" and (not KR_SYMBOL.fullmatch(str(x.get("symbol", ""))) or
            x.get("source_symbol") != x.get("symbol")) for x in items):
        raise RuntimeError("catalogue_official_identifier_provenance_missing")
    if not 0 <= us_batch <= MAX_US_BATCH or not 0 <= kr_batch <= MAX_KR_BATCH:
        raise ValueError("batch_size_exceeds_safe_cap")
    prior=json_file(root/OUTPUT,{})
    now=iso()
    today=as_of or observed_date(now)
    known, quarantine_count = isolate_unverified_records(root, prior, items, now)
    previous_cursor=prior.get("cursor") or {}
    us, next_us=choose(items,int(previous_cursor.get("US",0)),"US",us_batch)
    kr, next_kr=choose(items,int(previous_cursor.get("KR",0)),"KR",kr_batch)
    getter=getter or read_url
    user_agent=agent if agent is not None else os.getenv("SEC_USER_AGENT", "")
    kr_agent=dart_agent if dart_agent is not None else (os.getenv("DART_USER_AGENT", "").strip() or PROJECT_AGENT)
    sec_contact_ok=sec_contact_configured(user_agent)
    key=dart_key if dart_key is not None else os.getenv("DART_API_KEY", "")
    stats={country:{"attempted":0,"available":0,"blocked":0,"provider_errors":0,
                    "identity_errors":0,"no_report":0} for country in ("US","KR")}
    issues=[]

    def save_result(item, result):
        nonlocal quarantine_count
        country, symbol = item["country"], item["symbol"]
        result["catalog_name"] = item["name"]
        result["name"] = item["name"]
        key=country+":"+symbol
        issuer_key="corp_code" if country=="KR" else "cik"
        old=known.get(key)
        if (old and verified_financial_record(old) and
                (result.get("identity_verified") is True or result.get("issuer_mapping_verified") is True) and
                result.get(issuer_key) is not None and old.get(issuer_key)!=result[issuer_key]):
            _,quarantine_count=isolate_unverified_records(root,
                {"records":{key:old},"generated_at":prior.get("generated_at")},
                [{**item,issuer_key:result[issuer_key]}],now)
            known.pop(key,None)
        counter = stats[country]
        counter["attempted"] += 1
        if result.get("status") in FINANCIAL_STATUSES:
            if not verified_financial_record(result, country+":"+symbol, item):
                raise ValueError("refusing_unverified_financial_record:"+country+":"+symbol)
            counter["available"] += 1
        else:
            counter["blocked"] += 1
            if result.get("status") in ("source_unavailable","source_not_configured"):
                counter["provider_errors"] += 1
            elif result.get("status") == "identity_mismatch":
                counter["identity_errors"] += 1
            else:
                counter["no_report"] += 1
        identity = country+":"+symbol
        known[identity] = merge_record(known.get(identity), result)

    if us:
        if not sec_contact_ok:
            issues.append("SEC_USER_AGENT must identify a real organization and a contact email; US requests skipped.")
            cik_map={}
        else:
            try:
                cik_map=official_cik_map(getter(SEC_CIK,agent=user_agent))
            except Exception as exc:
                cik_map={}
                issues.append("SEC_mapping: "+safe_reason(exc))
        provider_failure_streak=0
        for item in us:
            symbol=item["symbol"]
            cik=cik_map.get(symbol)
            if provider_failure_streak>=3:
                result={"symbol":symbol,"country":"US","status":"source_unavailable",
                        "checked_at":now,
                        "reason":"SEC request circuit breaker: repeated source/access errors"}
            elif cik is None:
                result={"symbol":symbol,"country":"US",
                        "status":"source_not_configured" if not sec_contact_ok else
                                 "source_unavailable" if not cik_map else "identifier_unmatched",
                        "checked_at":now,"reason":"Real SEC contact user agent not configured" if not sec_contact_ok else
                            "SEC CIK map unavailable" if not cik_map else "No verified SEC CIK"}
            else:
                try:
                    content=getter(SEC_FACTS.format(cik=cik),agent=user_agent)
                    result=parse_sec_companyfacts(content,symbol=symbol,cik=cik,checked_at=now)
                    provider_failure_streak=0
                except Exception as exc:
                    provider_failure_streak+=1
                    result={"symbol":symbol,"country":"US","status":"source_unavailable",
                             "checked_at":now,"reason":safe_reason(exc)}
                if throttle and provider_failure_streak<3:
                    time.sleep(throttle)
            if cik is not None:
                result["cik"]=int(cik)
                result["issuer_mapping_verified"]=True
            save_result(item, result)
        if provider_failure_streak>=3:
            issues.append("SEC repeated provider errors; remaining batch requests paused to avoid hammering the service.")
    if kr:
        if not key:
            issues.append("KR DART_API_KEY is not configured; no official Korean financial data generated.")
            for item in kr:
                result={"symbol":item["symbol"],"country":"KR","status":"source_not_configured",
                        "checked_at":now,"reason":"DART_API_KEY is required"}
                save_result(item, result)
        else:
            mapping_error=None
            try:
                official=dart_corp_identities(getter(DART_MAP+"?"+urllib.parse.urlencode({"crtfc_key":key}),
                                                     agent=kr_agent,max_bytes=30_000_000))
            except Exception as exc:
                official={}
                mapping_error=safe_reason(exc)
                issues.append("DART_corp_map: "+mapping_error)
            identities, identity_errors = {}, {}
            budget=[MAX_IDENTITY_LOOKUPS]
            for item in kr:
                symbol=item["symbol"]
                if not official.get(symbol):
                    continue
                try:
                    identity=resolve_dart_identity(item,official[symbol],getter=getter,key=key,
                                                  agent=kr_agent,budget=budget,checked_at=now)
                    if identity:
                        identities[symbol]=identity
                    else:
                        identity_errors[symbol]="Official corporation/name does not match the catalogue; financials withheld"
                except Exception as exc:
                    identity_errors[symbol]=safe_reason(exc)
                    issues.append("DART_identity "+symbol+": "+safe_reason(exc))
            resolved={symbol:identity["corp_code"] for symbol,identity in identities.items()}
            outcomes={}
            report_errors=set()
            if resolved:
                # Try latest reported period, then previous reports only for unfilled symbols.
                reports=reported_period_candidates(today)
                unresolved=dict(resolved)
                for report_year, code in reports:
                    if not unresolved:
                        break
                    companies=list(unresolved.items())
                    for k in range(0,len(companies),80):
                        portion=dict(companies[k:k+80])
                        url=DART_MULTI+"?"+urllib.parse.urlencode({
                            "crtfc_key":key,"corp_code":",".join(portion.values()),
                            "bsns_year":str(report_year),"reprt_code":code})
                        try:
                            payload=getter(url,agent=kr_agent)
                            found=parse_dart_multi(payload,corp_map=portion,checked_at=now,
                                                   report_year=report_year,report_code=code,
                                                   identities=identities)
                            outcomes.update(found)
                            for sym in found:
                                unresolved.pop(sym,None)
                        except Exception as exc:
                            issues.append(f"DART_{report_year}_{code}: {safe_reason(exc)}")
                            report_errors.update(portion)
                        if throttle:
                            time.sleep(throttle)
            for item in kr:
                sym=item["symbol"]
                result=outcomes.get(sym)
                if result is None:
                    status=("source_unavailable" if mapping_error or sym in report_errors else
                            "identity_mismatch" if sym in identity_errors else
                            "identifier_unmatched" if sym not in identities else "no_report")
                    reason=(mapping_error or identity_errors.get(sym) or
                            ("DART report request failed; latest published period could not be checked" if sym in report_errors else
                             "No verified DART issuer mapping" if sym not in identities else
                             "No comparable published DART periodic accounts"))
                    result={"symbol":sym,"country":"KR","status":status,"checked_at":now,"reason":reason}
                elif sym in report_errors:
                    result["latest_period_check_incomplete"]=True
                    result["last_refresh_error"]={"at":now,"reason":"A newer reporting-period request failed"}
                    stats["KR"]["provider_errors"]+=1
                if sym in identities:
                    result["corp_code"]=identities[sym]["corp_code"]
                    result["issuer_mapping_verified"]=True
                save_result(item, result)
    allowed={(x["country"]+":"+x["symbol"]) for x in items}
    count={country:sum(k.startswith(country+":") and verified_financial_record(rec, k)
                      for k,rec in known.items() if k in allowed)
           for country in ("KR","US")}
    published={k:v for k,v in known.items() if k in allowed}
    for counter in stats.values():
        counter["refresh_status"]=("not_requested" if not counter["attempted"] else
            "blocked" if not counter["available"] and (counter["provider_errors"] or counter["identity_errors"]) else
            "partial" if counter["blocked"] or counter["provider_errors"] else "success")
    requested=[x for x in stats.values() if x["attempted"]]
    refreshed=sum(x["available"] for x in requested)
    refresh_status=("not_requested" if not requested else
                    "blocked" if not refreshed and any(x["refresh_status"]=="blocked" for x in requested) else
                    "partial" if any(x["refresh_status"]!="success" for x in requested) else "success")
    source_failed=any(x["provider_errors"] or x["identity_errors"] for x in requested)
    observed=[row["checked_at"] for row in published.values() if verified_financial_record(row) and row.get("checked_at")]
    result={"version":VERSION,"identity_policy":IDENTITY_POLICY,"generated_at":now,
        "catalog_generated_at":catalog.get("generated_at"),
        "status":"partial_verified_financial_coverage",
        "scope_note":"공식 종목·법인 연결을 검증한 SEC/DART 주요계정입니다. 전체 재무제표·미래 EPS·현재 시세·AI 확률이 아닙니다.",
        "full_financial_statements":False,"refresh_status":refresh_status,"current_run_failed":source_failed,
        "last_successful_observation_at":max(observed) if observed else None,
        "provider_readiness":{"US":"configured" if sec_contact_ok else "real_contact_required",
                              "KR":"configured" if key else "dart_api_key_required"},
        "universe":catalog.get("counts"),"processed":len(published),
        "financial_available":count,"run":stats,"issues":issues[:60],
        "quarantined_records":quarantine_count,"quarantine_file":str(QUARANTINE_OUTPUT),
        "cursor":{"US":next_us,"KR":next_kr},"records":published}
    write_json(root/OUTPUT,result)
    print("FINANCIAL_COVERAGE",result["universe"],"real_statements",count,"this_run",stats,
          "issues",len(issues))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--us-batch",type=int,default=60)
    parser.add_argument("--kr-batch",type=int,default=240)
    args=parser.parse_args()
    result=build(us_batch=args.us_batch,kr_batch=args.kr_batch)
    if result["current_run_failed"]:
        raise SystemExit("Current financial refresh was blocked or incomplete; prior verified accounts were retained. See run/issues, not accumulated coverage counts.")


if __name__=="__main__":
    main()
