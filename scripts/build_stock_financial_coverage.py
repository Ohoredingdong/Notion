"""Official-source financial coverage for the Korea/US issuer catalogue.

- SEC EDGAR XBRL companyfacts and KRX-listed companies' OpenDART reports only.
- Incremental, bounded; never invents EPS, revenue, price or probability.
- Preserves already verified records on a failed provider request.
- This is *reported* history, not an analyst EPS forecast or investment signal.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET
import zipfile

UTC = timezone.utc
VERSION = "official-financial-coverage-v1"
OUTPUT = Path("stock-financial-coverage.json")
SEC_CIK = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
DART_MAP = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_MULTI = "https://opendart.fss.or.kr/api/fnlttMultiAcnt.json"
MAX_US_BATCH, MAX_KR_BATCH = 120, 400
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


def iso():
    return datetime.now(UTC).isoformat()


def json_file(path: Path, default):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_url(url, *, agent, max_bytes=16_000_000, attempts=2):
    if not agent or len(agent.strip()) < 15:
        raise ValueError("source_contact_user_agent_not_configured")
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


def dart_corp_map(raw):
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
        if re.fullmatch(r"\d{6}", stock) and re.fullmatch(r"\d{8}", corp):
            found[stock] = corp
    if not found:
        raise ValueError("empty_DART_corp_mapping")
    return found


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


def parse_sec_companyfacts(raw, *, symbol, cik, checked_at):
    obj = json.loads(raw)
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
    ops, capex = fields["cash_from_operations"], fields["capital_expenditure"]
    fields["free_cash_flow"] = ops - capex if ops is not None and capex is not None else None
    present = sum(fields.get(k) is not None for k in ("revenue", "net_income", "operating_income"))
    filed = chosen[1]
    stale = (date.today() - date.fromisoformat(end)).days > 560
    return {"symbol": symbol, "country": "US", "status": ("stale" if stale else
            "available" if present>=2 else "partial"),
            "checked_at": checked_at, "source": "SEC EDGAR XBRL",
            "source_url": SEC_FACTS.format(cik=cik),
            "filing_date": filed, "period_start": begin, "period_end": end,
            "period_type": "quarter_or_year_as_reported", "currency": "USD",
            "annualized": False, "estimated": False,
            "metrics": fields,
            "limitations": ["XBRL reported facts; not forward-looking analyst EPS",
                            "FCF only if matching report interval operating cash & capex"]}


def _amount(value):
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value or "").strip().replace(",", "")
    if not raw or raw in ("-", "—", "N/A"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_dart_multi(raw, *, corp_map, checked_at, report_year, report_code):
    data = json.loads(raw)
    if data.get("status") != "000":
        raise ValueError("DART_response_"+str(data.get("status"))+"_"+str(data.get("message"))[:65])
    by_stock = {}
    mapping = {corp: sym for sym,corp in corp_map.items()}
    for entry in data.get("list") or []:
        stock = mapping.get(entry.get("corp_code"))
        if not stock:
            continue
        by_stock.setdefault(stock, []).append(entry)
    out = {}
    latest_period_label={"11013": "Q1", "11012": "H1", "11014": "Q3", "11011": "FY"}[report_code]
    for stock, entries in by_stock.items():
        # Prefer consolidated statements; if not available take the separate set,
        # but never mix consolidated and separate for the same issuer.
        consolidated = [r for r in entries if r.get("fs_div") == "CFS"]
        rows = consolidated or [r for r in entries if r.get("fs_div") == "OFS"]
        vals = {}
        labels = {"revenue": ("매출액","영업수익","수익(매출액)"),
                  "operating_income": ("영업이익","영업이익(손실)"),
                  "net_income": ("당기순이익","당기순이익(손실)")}
        for key,names in labels.items():
            for name in names:
                candidates=[r for r in rows if str(r.get("account_nm") or "").replace(" ","")==name.replace(" ","")]
                value=next((_amount(x.get("thstrm_amount")) for x in candidates
                            if _amount(x.get("thstrm_amount")) is not None),None)
                if value is not None:
                    vals[key]=value
                    break
        if not vals:
            continue
        out[stock]={"symbol":stock,"country":"KR","status":"available" if len(vals)>=2 else "partial",
            "checked_at":checked_at,"source":"DART periodic reports",
            "source_url":"https://opendart.fss.or.kr/",
            "report_year":report_year,"report_code":report_code,
            "period_end_label":str(report_year)+"-"+latest_period_label,
            "consolidation":"CFS" if consolidated else "OFS",
            "currency":"KRW","annualized":False,"estimated":False,
            "metrics":{"revenue":vals.get("revenue"),"operating_income":vals.get("operating_income"),
                       "net_income":vals.get("net_income"),"cash_from_operations":None,
                       "capital_expenditure":None,"free_cash_flow":None,"reported_eps":None},
            "limitations":["DART thstrm_amount reported period; do not annualize",
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


def merge_record(previous, latest):
    if not previous:
        return latest
    # A temporary outage must not erase a previous real financial statement.
    if previous.get("status") in ("available","partial","stale") and latest.get("status") not in (
        "available","partial","stale"):
        old={**previous}
        old["last_refresh_error"]={"at":latest.get("checked_at"),"reason":latest.get("reason",latest.get("status"))}
        return old
    if previous.get("status") in ("available","partial") and latest.get("status") in ("available","partial"):
        # A delayed provider/cache response may not roll reporting periods backward.
        prior=previous.get("period_end") or previous.get("period_end_label") or ""
        newest=latest.get("period_end") or latest.get("period_end_label") or ""
        if str(newest) < str(prior):
            return previous
    return latest


def build(root=Path("."), *, us_batch=60, kr_batch=240, getter=None,
          agent=None, dart_key=None, throttle=0.30):
    root=Path(root)
    catalog=json_file(root/"stock-universe-catalog.json",{})
    items=catalog.get("items") or []
    if not items or catalog.get("counts",{}).get("total")!=len(items):
        raise RuntimeError("verified_issuer_catalog_missing_or_incomplete")
    if not 0 <= us_batch <= MAX_US_BATCH or not 0 <= kr_batch <= MAX_KR_BATCH:
        raise ValueError("batch_size_exceeds_safe_cap")
    prior=json_file(root/OUTPUT,{})
    known = {str(k):v for k,v in (prior.get("records") or {}).items() if isinstance(v,dict)}
    previous_cursor=prior.get("cursor") or {}
    us, next_us=choose(items,int(previous_cursor.get("US",0)),"US",us_batch)
    kr, next_kr=choose(items,int(previous_cursor.get("KR",0)),"KR",kr_batch)
    getter=getter or read_url
    user_agent=agent or os.getenv("SEC_USER_AGENT") or "Ohoredingdong/Notion stock-research via https://github.com/Ohoredingdong/Notion/issues"
    key=dart_key if dart_key is not None else os.getenv("DART_API_KEY", "")
    now=iso()
    stats={"US":{"attempted":0,"available":0,"blocked":0},
           "KR":{"attempted":0,"available":0,"blocked":0}}
    issues=[]
    if us:
        try:
            cik_map=official_cik_map(getter(SEC_CIK,agent=user_agent))
        except Exception as exc:
            cik_map={}
            issues.append("SEC_mapping: "+str(exc)[:180])
        provider_failure_streak=0
        for item in us:
            symbol=item["symbol"]
            stats["US"]["attempted"]+=1
            cik=cik_map.get(symbol)
            if provider_failure_streak>=3:
                result={"symbol":symbol,"country":"US","status":"source_unavailable",
                        "checked_at":now,
                        "reason":"SEC request circuit breaker: repeated source/access errors"}
            elif cik is None:
                result={"symbol":symbol,"country":"US",
                        "status":"source_unavailable" if not cik_map else "identifier_unmatched",
                        "checked_at":now,"reason":"SEC CIK map unavailable" if not cik_map else "No verified SEC CIK"}
            else:
                try:
                    content=getter(SEC_FACTS.format(cik=cik),agent=user_agent)
                    result=parse_sec_companyfacts(content,symbol=symbol,cik=cik,checked_at=now)
                    provider_failure_streak=0
                    if result["status"] in ("available","partial","stale"):
                        stats["US"]["available"]+=1
                except Exception as exc:
                    provider_failure_streak+=1
                    result={"symbol":symbol,"country":"US","status":"source_unavailable",
                            "checked_at":now,"reason":str(exc)[:180]}
                if throttle and provider_failure_streak<3:
                    time.sleep(throttle)
            if result["status"] not in ("available","partial","stale"):
                stats["US"]["blocked"]+=1
            identity="US:"+symbol
            known[identity]=merge_record(known.get(identity),result)
        if provider_failure_streak>=3:
            issues.append("SEC repeated provider errors; remaining batch requests paused to avoid hammering the service.")
    if kr:
        if not key:
            issues.append("KR DART_API_KEY is not configured; no official Korean financial data generated.")
            for item in kr:
                identity="KR:"+item["symbol"]
                result={"symbol":item["symbol"],"country":"KR","status":"source_not_configured",
                        "checked_at":now,"reason":"DART_API_KEY is required"}
                known[identity]=merge_record(known.get(identity),result)
                stats["KR"]["attempted"]+=1;stats["KR"]["blocked"]+=1
        else:
            try:
                official=dart_corp_map(getter(DART_MAP+"?"+urllib.parse.urlencode({"crtfc_key":key}),
                                               agent=user_agent,max_bytes=30_000_000))
            except Exception as exc:
                official={}
                issues.append("DART_corp_map: "+str(exc)[:180])
            grouped={item["symbol"]:official.get(item["symbol"]) for item in kr}
            resolved={symbol:corp for symbol,corp in grouped.items() if corp}
            outcomes={}
            if resolved:
                # Try latest reported period, then previous reports only for unfilled symbols.
                current_year=datetime.now(UTC).year
                reports=[(current_year,"11014"),(current_year,"11012"),
                         (current_year,"11013"),(current_year-1,"11011")]
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
                            payload=getter(url,agent=user_agent)
                            found=parse_dart_multi(payload,corp_map=portion,checked_at=now,
                                                   report_year=report_year,report_code=code)
                            outcomes.update(found)
                            for sym in found:
                                unresolved.pop(sym,None)
                        except Exception as exc:
                            issues.append(f"DART_{report_year}_{code}: {str(exc)[:150]}")
                        if throttle:
                            time.sleep(throttle)
            for item in kr:
                sym=item["symbol"]
                result=outcomes.get(sym) or {"symbol":sym,"country":"KR",
                    "status":"source_unavailable" if not official else
                             "identifier_unmatched" if not grouped.get(sym) else "no_report",
                    "checked_at":now,"reason":"No comparable published DART periodic accounts"}
                if result["status"] in ("available","partial","stale"):
                    stats["KR"]["available"]+=1
                else:
                    stats["KR"]["blocked"]+=1
                stats["KR"]["attempted"]+=1
                identity="KR:"+sym
                known[identity]=merge_record(known.get(identity),result)
    allowed={(x["country"]+":"+x["symbol"]) for x in items}
    count={country:sum(k.startswith(country+":") and rec.get("status") in
            ("available","partial","stale") for k,rec in known.items() if k in allowed)
           for country in ("KR","US")}
    published={k:v for k,v in known.items() if k in allowed}
    result={"version":VERSION,"generated_at":now,"catalog_generated_at":catalog.get("generated_at"),
        "status":"partial_verified_financial_coverage",
        "scope_note":"SEC XBRL / DART 실제 공시; 분석 완료 종목만 수치 표시. 미수집은 검증 대기. EPS 예상치·현재 시세·AI 확률 아님.",
        "universe":catalog.get("counts"),"processed":len(published),
        "financial_available":count,"run":stats,"issues":issues[:60],
        "cursor":{"US":next_us,"KR":next_kr},"records":published}
    target=root/OUTPUT
    tmp=target.with_suffix(target.suffix+".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"),
                              allow_nan=False)+"\n",encoding="utf-8")
    tmp.replace(target)
    print("FINANCIAL_COVERAGE",result["universe"],"real_statements",count,"this_run",stats,
          "issues",len(issues))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--us-batch",type=int,default=60)
    parser.add_argument("--kr-batch",type=int,default=240)
    args=parser.parse_args()
    build(us_batch=args.us_batch,kr_batch=args.kr_batch)


if __name__=="__main__":
    main()
