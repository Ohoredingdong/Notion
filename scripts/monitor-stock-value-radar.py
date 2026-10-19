from __future__ import annotations
"""External-ish health watchdog: executes independently of data builders.
Never reports OK just because an old cached JSON still exists.
"""
import json, math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
NOW=datetime.now(timezone.utc); KST=ZoneInfo("Asia/Seoul")
PATHS={"prices":Path("stocks-dashboard-data.json"),"fundamentals":Path("stock-value-radar-data.json"),
       "analysis":Path("stock-investment-intelligence.json")}
OUT=Path("stock-radar-health.json")
def load(p):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError,OSError):return {}
def hours(s):
    try:
        t=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return round((NOW-t.astimezone(timezone.utc)).total_seconds()/3600,1)
    except (ValueError,TypeError,AttributeError):return None
def main():
    old=load(OUT);data={k:load(p) for k,p in PATHS.items()}
    issues=[]; warnings=[]
    timestamp={}
    limits={"prices":3.5,"fundamentals":36,"analysis":36}
    for name,payload in data.items():
        age=hours(payload.get("generated_at"))
        timestamp[name]={"generated_at":payload.get("generated_at"),"age_hours":age,"max_hours":limits[name]}
        if age is None:issues.append(name+" 데이터의 갱신 시각이 없습니다.")
        elif age < -1:issues.append(name+" 갱신 시각이 미래입니다.")
        elif age>limits[name]:issues.append(name+f" {age}시간 동안 갱신되지 않았습니다. (허용 {limits[name]}시간)")
    prices=data["prices"];fund=data["fundamentals"];intel=data["analysis"]
    if prices.get("stale"):warnings.append("기존 가격 수집기가 일부 시장을 갱신하지 못함")
    if prices.get("last_errors"):warnings += [str(e)[:160] for e in prices["last_errors"][:3]]
    rows=fund.get("rows") or [];analysis=intel.get("companies") or []
    n_fin=sum(1 for r in rows if r.get("revenue") is not None)
    if len(rows)<5:issues.append("추적 종목 수가 5개 미만: 구성 데이터 손상 가능성")
    if rows and n_fin/len(rows)<.8:issues.append("재무데이터 수집률 80% 미만")
    if not analysis:issues.append("분석된 종목이 전혀 없습니다.")
    if analysis and len(analysis)<len(rows)*.8:issues.append("분석 결과 종목 누락")
    critical=[{"symbol":r["symbol"],"reasons":r.get("quality",{}).get("critical",[])}
              for r in analysis if r.get("quality",{}).get("status")=="error"]
    if critical:issues.append("개별 기업 데이터 이상치: "+", ".join(x["symbol"] for x in critical[:8]))
    for row in analysis:
        sym=row.get("symbol"); price=row.get("price")
        if price is not None and (not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0):
            issues.append(f"{sym} 주가가 유효하지 않음")
    # Detect exact same warning repeated and permanent fallback without needless alarm.
    if not fund.get("dart_connected"):warnings.append("한국 공식 OpenDART 인증키 미설정; Yahoo 비공식 재무자료 사용")
    if any("Yahoo" in str(x.get("filing_source")) for x in rows):
        warnings.append("미국/한국 일부 재무데이터가 비공식 Yahoo Finance 제공 자료임")
    previous=old.get("consecutive_failures",0)
    failures=previous+1 if issues else 0
    level="error" if issues else "warning" if warnings else "ok"
    out={"checked_at":datetime.now(KST).isoformat(),"status":level,"consecutive_failures":failures,
         "notification_required":bool(issues and failures>=2),
         "data_ages":timestamp,"coverage":{"tracked":len(rows),"fundamentals_filled":n_fin,
                                      "analysis_count":len(analysis),"critical_count":len(critical)},
         "issues":issues,"warnings":warnings,"critical_rows":critical,
         "notice":"정상 표시도 투자데이터의 실시간 정확성을 보장하지 않습니다. 출처·공시 대조가 필요합니다.",
         "repair_url":"https://github.com/Ohoredingdong/Notion/actions/workflows/update-stock-value-radar.yml",
         "verification_url":"https://github.com/Ohoredingdong/Notion/actions/workflows/monitor-stock-value-radar.yml"}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":level,"consecutive_failures":failures,
                      "notification_required":out["notification_required"],
                      "issues":issues,"warnings":warnings[:2]},ensure_ascii=False))
if __name__=="__main__":main()
