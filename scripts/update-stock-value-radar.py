from __future__ import annotations
"""Stock research radar: official filings + existing delayed price snapshot.

US: SEC CompanyFacts, last two *annual* reports (FY, NOT trailing 12 months).
KR: OpenDART financials, only when DART_API_KEY GitHub secret exists.
Never fill missing values with fabricated numbers.
"""
import json, os, time, urllib.request, urllib.parse, io, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PRICE_FILE = Path("stocks-dashboard-data.json")
OUT_FILE = Path("stock-value-radar-data.json")
KST = ZoneInfo("Asia/Seoul")
USA = {
    "AAPL": ("Apple", 320193), "MSFT": ("Microsoft", 789019),
    "NVDA": ("NVIDIA", 1045810), "AMZN": ("Amazon", 1018724),
    "TSLA": ("Tesla", 1318605),
}
KOREA = {
    "005930": "삼성전자", "000660": "SK하이닉스",
    "035420": "NAVER", "207940": "삼성바이오로직스",
    "005380": "현대자동차",
}
REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"
]
HEADERS = {"User-Agent": "Investment research educational dashboard (github.com/Ohoredingdong/Notion)",
           "Accept": "application/json"}

def get_json(url, params=None):
    if params: url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=22) as response:
        return json.load(response)

def number(v):
    try:
        if v is None: return None
        val = float(str(v).replace(",", "").replace(" ", ""))
        return val if abs(val) < 1e30 else None
    except (ValueError, TypeError): return None

def growth(new, old):
    if new is None or old is None or old <= 0: return None
    return round((new / old - 1) * 100, 2)

def metric(facts, tags, unit="USD", min_days=300):
    """Use annual facts with 10-K sources; return newest and previous comparable FY."""
    best_items, best_tag = [], None
    for tag in tags:
        data = (facts.get(tag) or {}).get("units", {}).get(unit) or []
        items = []
        for x in data:
            if x.get("form") not in ("10-K", "10-K/A") or x.get("fp") != "FY": continue
            start, end = x.get("start"), x.get("end")
            if min_days and (not start or not end or
                    not 300 <= (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days <= 380):
                continue
            if not end or number(x.get("val")) is None: continue
            items.append(x)
        if not items: continue
        by_end = {}
        for x in items:
            end = x["end"]
            if end not in by_end or x.get("filed", "") > by_end[end].get("filed", ""):
                by_end[end] = x
        ordered = sorted(by_end.values(), key=lambda x: x["end"], reverse=True)
        if ordered and (not best_items or ordered[0]["end"] > best_items[0]["end"]):
            best_items, best_tag = ordered[:2], tag
    return best_items, best_tag

def latest_value(facts, tags, unit="USD", min_days=300):
    return metric(facts, tags, unit, min_days)[0]

def values(facts, tags, unit="USD", min_days=300):
    points, tag = metric(facts, tags, unit, min_days)
    return (number(points[0].get("val")) if len(points) > 0 else None,
            number(points[1].get("val")) if len(points) > 1 else None,
            points[0].get("end") if points else None, tag)

def stock_sec(symbol, name, cik):
    raw = get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    facts = raw.get("facts", {}).get("us-gaap", {})
    rev, rev_prev, date, rev_tag = values(facts, REVENUE_TAGS)
    op, _, _, _ = values(facts, ["OperatingIncomeLoss"])
    ni, _, _, _ = values(facts, ["NetIncomeLossAvailableToCommonStockholdersBasic", "NetIncomeLoss"])
    eps, _, _, _ = values(facts, ["EarningsPerShareDiluted", "EarningsPerShareBasic"], "USD/shares")
    ocf, _, _, _ = values(facts, ["NetCashProvidedByUsedInOperatingActivities"])
    capex, _, _, _ = values(facts, ["PaymentsToAcquirePropertyPlantAndEquipment",
                                     "PaymentsToAcquireProductiveAssets"])
    fcf = (ocf - capex) if ocf is not None and capex is not None else None
    # SEC taxonomy tags are not necessarily universal; no invented substitutions.
    return {"symbol":symbol, "name":name, "market":"US", "filing_source":"SEC CompanyFacts",
            "filing_url":f"https://www.sec.gov/edgar/browse/?CIK={cik}",
            "filing_period":date, "statement_basis":"최근 연간 10-K (TTM 아님)",
            "revenue":rev, "revenue_growth":growth(rev, rev_prev),
            "operating_income":op, "operating_margin":round(op/rev*100,2) if op is not None and rev and rev>0 else None,
            "net_income":ni, "eps":eps, "fcf":fcf,
            "fcf_margin":round(fcf/rev*100,2) if fcf is not None and rev and rev>0 else None,
            "capex":capex, "currency":"USD", "revenue_tag":rev_tag}

def dart_code_lookup(key):
    req = urllib.request.Request("https://opendart.fss.or.kr/api/corpCode.xml?"+urllib.parse.urlencode({"crtfc_key":key}),headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as response:
        b=response.read()
    z=zipfile.ZipFile(io.BytesIO(b))
    root=ET.fromstring(z.read(z.namelist()[0]))
    result={}
    for x in root.findall("list"):
        ticker=(x.findtext("stock_code") or "").strip()
        if ticker in KOREA: result[ticker]=(x.findtext("corp_code") or "").strip()
    return result

def dart_rows_by_code(key, codes, year):
    params={"crtfc_key":key,"corp_code":",".join(codes),"bsns_year":str(year),"reprt_code":"11011"}
    data=get_json("https://opendart.fss.or.kr/api/fnlttMultiAcnt.json",params)
    if data.get("status")!="000": raise RuntimeError("DART API: "+str(data.get("status"))+" "+str(data.get("message")))
    return data.get("list") or []

def dart_build(ticker, name, corp, rows, year):
    subset=[x for x in rows if str(x.get("corp_code"))==corp and x.get("fs_div")=="CFS"]
    def find(labels):
        for term in labels:
            for r in subset:
                if r.get("account_nm")==term:
                    return number(r.get("thstrm_amount")),number(r.get("frmtrm_amount"))
        return None,None
    rev,rev_pre=find(["매출액","매출","수익(매출액)","영업수익","수익"])
    op,_=find(["영업이익","영업이익(손실)","영업손익"])
    ni,_=find(["지배기업 소유주지분 순이익","지배기업의 소유주에게 귀속되는 당기순이익","당기순이익","당기순이익(손실)"])
    return {"symbol":ticker,"name":name,"market":"KR", "filing_source":"OpenDART",
            "filing_url":"https://dart.fss.or.kr/", "filing_period":str(year)+"-12-31",
            "statement_basis":f"{year}년 연간 연결 주요계정",
            "revenue":rev,"revenue_growth":growth(rev,rev_pre),
            "operating_income":op,"operating_margin":round(op/rev*100,2) if op is not None and rev and rev>0 else None,
            "net_income":ni,"eps":None,"fcf":None,"fcf_margin":None,"capex":None,
            "currency":"KRW","note":"EPS·FCF는 기본 다중회사 주요계정 응답만으로 검증 불가. 별도 주석/현금흐름 연동 필요."}

def base_record(symbol,name,market,reason):
    return {"symbol":symbol,"name":name,"market":market,"filing_source":None,
            "filing_period":None,"statement_basis":None,"revenue":None,"revenue_growth":None,
            "operating_income":None,"operating_margin":None,"net_income":None,"eps":None,
            "fcf":None,"fcf_margin":None,"capex":None,
            "currency":"KRW" if market=="KR" else "USD", "note":reason}

def main():
    snap=json.loads(PRICE_FILE.read_text(encoding="utf-8"))
    old=json.loads(OUT_FILE.read_text(encoding="utf-8")) if OUT_FILE.exists() else {}
    old_records={r["symbol"]:r for r in old.get("rows",[]) if r.get("symbol")}
    pricing={}
    for market, key in [("US","US"),("KR","KOR")]:
        for x in (snap.get("datasets",{}).get(key,{}).get("rows") or []):
            pricing[x.get("symbol")]={"price":x.get("raw_price"),"price_updated_at":x.get("market_time"),"price_change_pct":x.get("pct")}
    results=[];errors=[]
    for symbol,(name,cik) in USA.items():
        try:
            row=stock_sec(symbol,name,cik)
        except Exception as e:
            errors.append(f"SEC {symbol}: {str(e)[:140]}")
            row=old_records.get(symbol) or base_record(symbol,name,"US","SEC 연결 실패")
        row=dict(row);row.update(pricing.get(symbol) or {"price":None,"price_updated_at":None,"price_change_pct":None})
        eps=number(row.get("eps"));price=number(row.get("price"))
        row["annual_per"]=round(price/eps,2) if price is not None and eps and eps>0 else None
        results.append(row)
        time.sleep(.19)
    key=os.environ.get("DART_API_KEY","").strip()
    korean={}
    if key:
        try:
            codes=dart_code_lookup(key)
            if not codes: raise RuntimeError("상장기업 고유번호 조회 결과 없음")
            rows=dart_rows_by_code(key,list(codes.values()),2025)
            korean={s:dart_build(s,name,codes[s],rows,2025) for s,name in KOREA.items() if s in codes}
        except Exception as e: errors.append("OpenDART: "+str(e)[:160])
    for symbol,name in KOREA.items():
        row=korean.get(symbol) or old_records.get(symbol) or base_record(symbol,name,"KR",
          "DART_API_KEY 미연결: 주가는 자동 갱신, 재무 분석은 데이터 미연결")
        row=dict(row);row.update(pricing.get(symbol) or {"price":None,"price_updated_at":None,"price_change_pct":None})
        row["annual_per"]=None
        results.append(row)
    out={"generated_at":datetime.now(KST).isoformat(),
         "price_source":snap.get("source_label","Yahoo Finance · delayed/indicative"),
         "price_generated_at":snap.get("generated_at"),"financial_sources":["SEC CompanyFacts","OpenDART(키 연결 시)"],
         "coverage_note":"US: last reported ANNUAL 10-K, NOT TTM. KR: financial metrics only when API connected.",
         "dart_connected":bool(key and korean),"errors":errors,"rows":results}
    OUT_FILE.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("updated",len(results),"rows","issues:",len(errors))
if __name__=="__main__": main()
