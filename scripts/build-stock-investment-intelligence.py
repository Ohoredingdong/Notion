from __future__ import annotations
"""Deterministic investment research snapshots; NEVER a buy/sell recommender.

Reads the existing 10+ stock fundamentals and current quoted prices.
Outputs: stock-investment-intelligence.json, stock-investment-history.json
Run even if RSS headlines are unavailable. No artificial prices/financials.
"""
import json, os, re, math, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
NOW = datetime.now(timezone.utc)
KST = ZoneInfo("Asia/Seoul")
RADAR=Path("stock-value-radar-data.json")
QUOTES=Path("stocks-dashboard-data.json")
OUTPUT=Path("stock-investment-intelligence.json")
HISTORY=Path("stock-investment-history.json")
FRESH_DAYS=5
MAX_HISTORY=90
NEWS_LIMIT=2

def load(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError): return default
def num(n):
    try:
        n=float(n)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError): return None
def dt(s):
    try:
        if not s:return None
        x=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x.astimezone(timezone.utc)
    except ValueError:return None
def age_hours(s):
    x=dt(s);return round((NOW-x).total_seconds()/3600,1) if x else None
def pct(a,b):
    if not a or b is None:return None
    return round((b/a-1)*100,2)
def rank(r):
    """Score is for INVESTIGATION priority, NOT expected return."""
    rg=num(r.get("revenue_growth"));op=num(r.get("operating_margin"))
    fcf=num(r.get("fcf"));per=num(r.get("annual_per"))
    if rg is None or op is None:return {"score":None,"label":"자료 부족","reasons":["매출 성장 또는 수익성 정보 부족"]}
    score=0; reasons=[]
    if rg>=15:score+=2;reasons.append("연간 매출 고성장")
    elif rg>0:score+=1
    if op>=20:score+=2;reasons.append("영업이익률 20% 이상")
    elif op>5:score+=1
    if fcf is not None and fcf>0:score+=2;reasons.append("FCF 양수")
    if per is not None and 0<per<30:score+=1;reasons.append("연간 PER 30배 미만")
    risks=[]
    if rg<-5:risks.append("매출 감소")
    if op<0:risks.append("영업손실")
    if fcf is not None and fcf<0:risks.append("FCF 적자")
    if per is not None and per>65:risks.append("높은 이익 대비 주가 배수")
    reasons += risks
    return {"score":score,"label":("위험 우선 검토" if risks else "심층 검토 후보" if score>=5 else "관찰 대상"),"reasons":reasons,"risks":risks}

def validate(row,previous):
    warnings=[]; critical=[]
    sym=row["symbol"]; price=num(row.get("price"))
    fin_date=dt(row.get("filing_period")); price_hours=age_hours(row.get("price_updated_at"))
    finance_hours=age_hours(row.get("filing_period"))
    rg=num(row.get("revenue_growth"));op=num(row.get("operating_margin"))
    eps=num(row.get("eps"));pe=num(row.get("annual_per"))
    rev=num(row.get("revenue"));fcf=num(row.get("fcf"))
    if price is None or price<=0:critical.append("유효한 주가 없음")
    if price_hours is None:critical.append("주가 시각 확인 불가")
    elif price_hours>120:critical.append("주가가 5일 넘게 갱신되지 않음")
    elif price_hours>72:warnings.append("휴장일 또는 갱신 지연: 주가 72시간 이상 경과")
    if rev is None or eps is None:warnings.append("필수 재무항목 누락")
    if finance_hours is None:warnings.append("공시 대상기간 미상")
    elif finance_hours > 24*640:warnings.append("연간 재무 대상기간이 오래됨")
    if rev is not None and rev<0:critical.append("매출액 음수: 자료 오류 가능")
    if op is not None and abs(op)>250:critical.append("이익률 이상치: 회계 단위 확인")
    if rg is not None and abs(rg)>500:warnings.append("매출 성장률 극단값: 공시 확인 필요")
    if eps is not None and eps<=0 and pe is not None:critical.append("EPS 0 이하인데 PER 표시됨")
    if row.get("filing_source","").startswith("Yahoo"):warnings.append("비공식 보조 재무자료 — 공시와 교차검증 필요")
    if row.get("market")=="KR" and not row.get("dart_verified",False):warnings.append("DART 공식 검증 미완료")
    if previous and row.get("filing_period")==previous.get("filing_period"):
        for key,desc in [("revenue","매출"),("eps","EPS"),("fcf","FCF")]:
            a=num(previous.get(key));b=num(row.get(key))
            if a is not None and b is not None and abs(a)>0:
                change=abs(b/a-1)
                if change>0.4:critical.append(desc+" 값이 같은 공시기간에 40% 이상 변경")
    if previous and price is not None:
        p=num(previous.get("price"))
        past=dt(previous.get("price_updated_at"));present=dt(row.get("price_updated_at"))
        if p and past and present and present!=past and abs(price/p-1)>0.35:
            critical.append("이전 수집 대비 주가 35% 이상 변동: 액면분할·기업행사·데이터 오류 확인")
    status="error" if critical else "warning" if warnings else "ok"
    return {"status":status,"warnings":warnings,"critical":critical,
            "price_age_hours":price_hours,
            "financial_period_age_days":round(finance_hours/24) if finance_hours is not None else None}

def scenarios(row):
    """Transparent SENSITIVITY TEST only; not a fair-value model."""
    eps=num(row.get("eps"));pe=num(row.get("annual_per"));price=num(row.get("price"))
    if not eps or eps<=0 or not pe or pe<=0 or not price:return None
    # Explicit sensitivity assumptions anchored to CURRENT reported revenue growth;
    # not an EPS forecast and NOT a fair-value estimate.
    rev_growth=num(row.get("revenue_growth"))
    g0=max(-0.20,min(0.25,rev_growth/100*0.60)) if rev_growth is not None else 0.0
    base_pe_factor=0.70 if pe>=70 else 0.85 if pe>=40 else 0.95 if pe>=25 else 1.0
    assumptions=[("bear",max(-0.60,g0-0.25),base_pe_factor*0.75),
                 ("base",g0,base_pe_factor),
                 ("bull",min(0.70,g0+0.25),min(1.2,base_pe_factor*1.15))]
    result={}
    for name,g,m in assumptions:
        val=round(eps*(1+g)*pe*m,2)
        result[name]={"eps_change_pct":round(g*100,1),"pe_multiple_factor":m,
                      "implied_price":val,"vs_price_pct":round((val/price-1)*100,2)}
    return result

def thesis(row):
    growth=num(row.get("revenue_growth"));margin=num(row.get("operating_margin"))
    fcf=num(row.get("fcf"));per=num(row.get("annual_per"))
    bulls=[];bears=[];tests=[]
    if growth is not None:
        if growth>10:bulls.append(f"연간 매출 성장 {growth:+.1f}%: 고객 수요가 이어질 가능성")
        if growth<0:bears.append(f"연간 매출 {growth:.1f}%: 수요 위축 여부")
        tests.append("매출 성장률과 다음 분기 회사 가이던스")
    if margin is not None:
        if margin>=20:bulls.append(f"영업이익률 {margin:.1f}%: 경쟁 우위 지속 가능성")
        if margin<10:bears.append(f"영업이익률 {margin:.1f}%: 원가·경쟁 위험")
        tests.append("경쟁사의 영업이익률과 과거 3년 추세")
    if fcf is not None:
        if fcf>0:bulls.append("잉여현금흐름이 양수: 현금 창출 지속성 확인")
        else:bears.append("잉여현금흐름이 음수: 설비투자·운전자본 점검")
        tests.append("CAPEX 대비 영업현금흐름")
    if per is not None and per>40:bears.append(f"연간 PER {per:.1f}배: 미래 성장 기대가 높은 가격")
    if per is not None and 0<per<20:bulls.append(f"연간 PER {per:.1f}배: 저평가인지 업황 악화인지 조사")
    tests.append("추정 EPS와 공시 주당이익, 차입금 만기")
    return {"bull":bulls or ["향후 수주·이익 회복의 객관적 근거 필요"],
            "bear":bears or ["실적 전망 하향·부채·정책 충격 점검"],
            "tests":tests}

def news_headlines(rows):
    """Optional headline discovery, explicitly UNVERIFIED. No LLM, no claimed causal sentiment."""
    if os.getenv("RADAR_NEWS_ENABLED","1")=="0":return {}
    old=load(OUTPUT,{}).get("headlines",{})
    out={}
    # Restrict external calls; failed source keeps only recent previous material.
    topics=[("market","한국 미국 증시 금리 경제"),
            ("semis","삼성전자 SK하이닉스 NVIDIA 반도체 HBM")]
    for key,topic in topics:
        try:
            query=urllib.parse.urlencode({"q":topic+" when:3d","hl":"ko","gl":"KR","ceid":"KR:ko"})
            url="https://news.google.com/rss/search?"+query
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (educational personal dashboard)"})
            with urllib.request.urlopen(req,timeout=12) as resp:
                root=ET.fromstring(resp.read(450000))
            items=[]
            for x in root.findall("./channel/item")[:NEWS_LIMIT]:
                title=(x.findtext("title") or "").strip()
                link=(x.findtext("link") or "").strip()
                published=x.findtext("pubDate")
                if title and link and link.startswith("http"):
                    items.append({"title":title[:180],"url":link,"published":published,
                                  "status":"unverified_headline_only"})
            out[key]=items
        except Exception:
            out[key]=old.get(key,[])[:NEWS_LIMIT]
    return out

def main():
    raw=load(RADAR,{})
    quotes=load(QUOTES,{})
    if not raw.get("rows"):raise RuntimeError("근본 데이터가 없어 분석을 생성하지 않습니다.")
    history=load(HISTORY,{"entries":[]})
    entries=history.get("entries",[]) if isinstance(history.get("entries",[]),list) else []
    prior=load(OUTPUT,{})
    prev={r.get("symbol"):r for r in prior.get("companies",[]) if isinstance(r,dict)}
    quote_lookup={}
    for k in ("US","KOR"):
        for q in quotes.get("datasets",{}).get(k,{}).get("rows",[]):
            quote_lookup[q.get("symbol")]=q
    companies=[]
    for r in raw["rows"]:
        x=dict(r);symbol=x.get("symbol")
        if not symbol:continue
        q=quote_lookup.get(symbol,{})
        if q:
            x["price"]=q.get("raw_price")
            x["price_updated_at"]=q.get("market_time")
            x["price_change_pct"]=q.get("pct")
        # Recompute PER with aligned price & EPS, avoid stale stored PER.
        ep=num(x.get("eps"));p=num(x.get("price"))
        x["annual_per"]=round(p/ep,2) if p and ep and ep>0 else None
        quality=validate(x,prev.get(symbol))
        x["quality"]=quality
        x["review_rank"]=rank(x)
        x["dual_thesis"]=thesis(x)
        x["sensitivity"]=scenarios(x)
        companies.append(x)
    critical=[r["symbol"] for r in companies if r["quality"]["status"]=="error"]
    warnings=[r["symbol"] for r in companies if r["quality"]["status"]=="warning"]
    rss=news_headlines(companies)
    asof=raw.get("generated_at")
    radar_age=age_hours(asof)
    quote_age=age_hours(quotes.get("generated_at"))
    failure=(radar_age is None or radar_age>36 or not companies or len(critical)>len(companies)*.3)
    state="error" if failure else "warning" if critical or warnings or (quote_age is None or quote_age>4) else "ok"
    report={"generated_at":datetime.now(KST).isoformat(),"state":state,
            "radar_age_hours":radar_age,"quote_refresh_age_hours":quote_age,
            "counts":{"total":len(companies),"critical":len(critical),"warning":len(warnings),
                      "with_financials":sum(1 for r in companies if r.get("revenue") is not None)},
            "critical_symbols":critical,"warning_symbols":warnings,
            "source_note":"Google News RSS headlines are unverified; no automatic AI sentiment inference.",
            "discovery_scope":"정해진 관심종목만 자동 분석 (전체 상장기업 완전 검색 아님)",
            "assumptions_note":"Scenario prices are WHAT-IF sensitivities, not computed fair values or forecasts.",
            "headlines":rss,"companies":companies}
    # Log one market snapshot per quote-market day. Score is *retrospective observational*, not a claim of skill.
    # Use ACTUAL quoted market session date, not pipeline calendar day.
    # Weekends and exchange holidays must not create a fake trading observation.
    by_date={}
    for e in entries:
        if not isinstance(e,dict) or not e.get("symbol"):continue
        session=dt(e.get("price_asof"))
        if not session:continue
        key=(session.date().isoformat(),e["symbol"])
        e["date"]=key[0]
        by_date.setdefault(key,e)
    for r in companies:
        ts=dt(r.get("price_updated_at"))
        if not ts or num(r.get("price")) is None:continue
        session_date=ts.date().isoformat()
        key=(session_date,r["symbol"])
        # Keep first quote captured on each MARKET day to avoid weekend duplicates.
        if key not in by_date:
            by_date[key]={"date":session_date,"symbol":r["symbol"],"price":r.get("price"),
                          "price_asof":r.get("price_updated_at"),
                          "review_score":r["review_rank"]["score"],"quality":r["quality"]["status"]}
    entries=sorted(by_date.values(),key=lambda x:(x.get("date",""),x.get("symbol","")))
    by_symbol={}
    for r in entries:by_symbol.setdefault(r["symbol"],[]).append(r)
    for r in entries:
        series=by_symbol[r["symbol"]]
        j=next((i for i,x in enumerate(series) if x["date"]==r["date"]),None)
        if j is None:continue
        for n in (5,20):
            later=series[j+n] if j+n<len(series) else None
            if later and r.get("price") and later.get("price"):
                r[f"forward_{n}_observation_return_pct"]=pct(num(r.get("price")),num(later.get("price")))
            else:r[f"forward_{n}_observation_return_pct"]=None
    entries=entries[-MAX_HISTORY*max(1,len(companies)):]
    HISTORY.write_text(json.dumps({"updated_at":report["generated_at"],
          "method":"One first-observed quote for each exchange market timestamp date; 5/20 subsequent observed trading sessions, subject to missing schedule dates.",
          "entries":entries},ensure_ascii=False,indent=2),encoding="utf-8")
    report["validation"]={"last_error":raw.get("errors",[])[:15],
             "source":"SEC/OpenDART when available, Yahoo unofficial fallback",
             "source_reliability":"unverified" if any("Yahoo" in str(x.get("filing_source","")) for x in companies) else "filing"}
    report["history_summary"]={"recorded_days":len({e.get("date") for e in entries}),
        "evaluated_5_observations":sum(1 for e in entries if e.get("forward_5_observation_return_pct") is not None)}
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("investment intelligence",state,report["counts"], "history days",report["history_summary"]["recorded_days"])
    if state=="error":raise SystemExit(2)
if __name__=="__main__":main()
