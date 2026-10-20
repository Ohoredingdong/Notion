"""Practical recommendation layer: rank investable candidates, not perfection.
A recommendation is a research opinion, never a return probability or trade order.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, math, hashlib

VERSION='recommendation-v1.0'
def n(x):
    if x is None or isinstance(x,bool): return None
    try:
        v=float(x); return v if math.isfinite(v) else None
    except (ValueError,TypeError): return None
def clamp(x,a,b): return max(a,min(b,x))
def change(a,b):
    a,b=n(a),n(b)
    return (a/b-1)*100 if a is not None and b is not None and b>0 else None
def read(name): return json.loads(Path(name).read_text())
def official_ok(row,case):
    if row.get('market')!='KR': return None
    annual=(case.get('official') or {}).get('annual') or {}
    matches={x.get('field') for x in (case.get('official_comparison') or []) if x.get('status')=='matched'}
    return annual.get('status')=='ok' and {'revenue','operating_income'}.issubset(matches) and bool(matches & {'cfo','fcf'})
def evaluate(row,case,depth):
    series=(depth.get('series') or [])[:3]
    latest=series[0] if series else {}
    h=row.get('history') or {}; f=row.get('forecasts') or {}; t=row.get('targets') or {}; b=row.get('balance') or {}
    blockers=[]; warnings=[]
    liq=next((x.get('ok') for x in (row.get('assessment') or {}).get('checks',[]) if x.get('key')=='liquidity'),None)
    if row.get('status')!='current': blockers.append('최근 완료 거래일 시세가 아니에요.')
    if (row.get('period_integrity') or {}).get('status')!='ok': blockers.append('회계기간이 서로 맞지 않아요.')
    if (row.get('model_integrity') or {}).get('status')!='ok': blockers.append('현재 평가모형이 이 업종에 맞지 않아요.')
    if liq is not True: blockers.append('평균 거래대금이 기준 미달이거나 확인되지 않았어요.')
    if len(series)<3: blockers.append('비교 가능한 최근 3년 실적이 부족해요.')
    op=n(latest.get('operating_income')); cfo=n(latest.get('cfo')); fcf=n(latest.get('fcf')); rev=n(latest.get('revenue'))
    if op is None or op<=0: blockers.append('최근 연간 영업이익이 흑자가 아니에요.')
    if cfo is None or cfo<=0: blockers.append('최근 연간 영업현금흐름(CFO)이 양수가 아니에요.')
    if fcf is None or fcf<=0: blockers.append('최근 연간 FCF(잉여현금흐름)가 양수가 아니에요.')
    leverage=n(b.get('net_debt_ebitda'))
    if leverage is None or leverage>3: blockers.append('순차입금/EBITDA가 3배 초과이거나 확인되지 않았어요.')
    eps_growth=n(f.get('eps_growth_next_fy_pct')); revision=n(f.get('eps_revision30_pct')); analysts=n(f.get('analysts')); spread=n(f.get('spread')); fpe=n(f.get('next_fy_pe'))
    if eps_growth is None or eps_growth<=0: blockers.append('다음 회계연도 예상 EPS가 성장하지 않아요.')
    if revision is None or revision<-3: blockers.append('같은 회계연도 예상 EPS가 최근 한 달 3% 넘게 하향됐어요.')
    if analysts is None or analysts<5: blockers.append('이익 전망을 낸 분석가가 5명 미만이에요.')
    if spread is None or spread>.60: blockers.append('예상 EPS 상·하단 편차가 너무 커요.')
    if fpe is None or not 5<=fpe<=60: blockers.append('예상 PER이 비정상 범위이거나 기준을 확인하기 어려워요.')
    official=official_ok(row,case)
    if row.get('market')=='KR' and official is not True: blockers.append('DART에서 매출·영업이익·현금흐름 핵심 대조가 충분하지 않아요.')

    for x in (h.get('quality_flags') or []): warnings.append(x)
    # 35: business/financial quality
    margin=op/rev*100 if rev and op is not None else None
    roe=n(latest.get('roe_average')); conversion=n(latest.get('cfo_to_profit'))
    quality=clamp((margin or 0)/25*10,0,10)+clamp((roe or 0)/20*8,0,8)
    quality += 8 if conversion is not None and conversion>=1 else 6 if conversion is not None and conversion>=.8 else 3 if conversion is not None and conversion>=.6 else 0
    quality += 5 if leverage is not None and leverage<0 else 4 if leverage is not None and leverage<=1 else 2 if leverage is not None and leverage<=2 else 0
    revenue_growth=n(latest.get('revenue_growth')); op_growth=change(op,series[1].get('operating_income')) if len(series)>1 else None
    quality += 4 if revenue_growth is not None and revenue_growth>5 and op_growth is not None and op_growth>0 else 2 if revenue_growth is not None and revenue_growth>0 else 0
    quality=round(quality,1)

    # 25: growth
    growth=clamp((eps_growth or 0)/30*15,0,15)
    growth += 5 if revision is not None and revision>=0 else 3 if revision is not None and revision>=-1 else 0
    growth += clamp((revenue_growth or 0)/20*5,0,5)
    growth=round(growth,1)

    # 25: valuation. Analyst target gap is only 4 points of 25.
    valuation=0; peg=fpe/eps_growth if fpe and eps_growth and eps_growth>0 else None
    valuation += 10 if peg is not None and peg<=.8 else 8 if peg is not None and peg<=1.2 else 5 if peg is not None and peg<=1.8 else 2 if peg is not None and peg<=2.5 else 0
    peer=(case.get('peer_context') or {}).get('median')
    if n(peer) is not None and fpe:
        premium=(fpe/peer-1)*100
        valuation += 8 if premium<=-15 else 6 if premium<=5 else 3 if premium<=25 else 0
    else:
        valuation += 6 if fpe and fpe<=15 else 5 if fpe and fpe<=20 else 3 if fpe and fpe<=30 else 1 if fpe else 0
    target_gap=n(t.get('median_gap_pct'))
    valuation += 4 if target_gap is not None and target_gap>=30 else 2 if target_gap is not None and target_gap>=15 else 0
    valuation += 3 if leverage is not None and leverage<0 else 1
    valuation=round(valuation,1)

    # 15: observed risk. Missing risks are not turned into positives.
    risk=15-min(9,3*len(warnings))
    if len(series)>1:
        names={'net_income':'순이익','cfo':'영업현금흐름','fcf':'FCF'}
        for key,cut in [('net_income',-15),('cfo',-15),('fcf',-20)]:
            ch=change(series[0].get(key),series[1].get(key))
            if ch is not None and ch<cut:
                risk-=3; warnings.append(f"{names[key]}이 전년보다 {abs(ch):.1f}% 줄었어요.")
    risk=max(0,round(risk,1))
    score=round(quality+growth+valuation+risk,1)

    if blockers: grade='제외'; action='지금은 매수 후보에서 빼요.'
    elif warnings:
        grade='관심'; action='수치는 매력적이지만 경고 원인을 확인한 뒤 결정해요.'
    elif score>=85:
        grade='우선 추천'; action='현재 자료 기준으로 가장 먼저 매수를 검토할 후보예요.'
    elif score>=75:
        grade='추천'; action='매수 후보로 볼 만해요. 가격과 최신 공시를 마지막으로 확인해요.'
    elif score>=65:
        grade='관심'; action='좋은 점은 있지만 우선순위는 한 단계 낮아요.'
    else:
        grade='보류'; action='현재 가격과 실적 조합은 추천하기 부족해요.'
    why=[
      f"영업이익률 {margin:.1f}%·ROE {roe:.1f}%" if margin is not None and roe is not None else '수익성 일부 미확인',
      f"다음 FY 예상 EPS 성장 {eps_growth:+.1f}%·한 달 조정 {revision:+.1f}%" if eps_growth is not None and revision is not None else '이익 전망 일부 미확인',
      f"예상 PER {fpe:.1f}배·EPS성장 대비 PER {peg:.2f}" if fpe is not None and peg is not None else '가격 지표 일부 미확인',
      f"순차입금/EBITDA {leverage:.2f}배" if leverage is not None else '부채부담 미확인'
    ]
    return {'symbol':row['symbol'],'name':row.get('name'),'market':row.get('market'),'sector':row.get('sector'),'currency':row.get('currency'),'price':row.get('price'),'price_session':row.get('price_session'),'grade':grade,'action':action,'score':score,'scores':{'quality':quality,'growth':growth,'valuation':valuation,'risk':risk},'why':why,'blockers':blockers,'warnings':warnings,'metrics':{'operating_margin_pct':margin,'roe_pct':roe,'cfo_to_profit':conversion,'revenue_growth_pct':revenue_growth,'eps_growth_next_fy_pct':eps_growth,'eps_revision30_pct':revision,'forward_pe':fpe,'peer_forward_pe':peer,'peg_like':peg,'target_gap_pct':target_gap,'net_debt_ebitda':leverage,'analysts':analysts,'eps_spread':spread,'official_core_checked':official},'not_probability':True,'not_personal_allocation_advice':True}

def main():
    raw_bytes=Path('stock-opportunity-data.json').read_bytes(); raw=json.loads(raw_bytes)
    cases=read('stock-investment-cases.json'); depth=read('stock-reading-depth.json')
    if cases.get('source_generated_at')!=raw.get('generated_at') or depth.get('source_generated_at')!=raw.get('generated_at'): raise SystemExit('source snapshot mismatch')
    c={x['symbol']:x for x in cases['companies']}; d={x['symbol']:x for x in depth['companies']}
    results=[evaluate(r,c.get(r['symbol'],{}),d.get(r['symbol'],{})) for r in raw['companies']]
    order={'우선 추천':0,'추천':1,'관심':2,'보류':3,'제외':4}
    results.sort(key=lambda x:(order[x['grade']],-x['score'],x['symbol']))
    top=[x for x in results if x['grade'] in ('우선 추천','추천')][:5]
    counts={g:sum(x['grade']==g for x in results) for g in order}
    out={'version':VERSION,'generated_at':datetime.now(timezone.utc).isoformat(),'source_generated_at':raw['generated_at'],'source_sha256':hashlib.sha256(raw_bytes).hexdigest(),'counts':counts,'top_recommendations':top,'companies':results,'method':{'hard_gates':['최신 완료시세·기간·업종모형·유동성','비교 가능한 3년 실적','영업이익·CFO·FCF 양수','순차입금/EBITDA 3배 이하','예상 EPS 성장·30일 수정·분석가 수·편차','예상 PER 5~60배 sanity check','한국기업은 DART 핵심 실적 대조'],'weights':{'사업·재무 질':35,'성장':25,'가격':25,'관측 위험':15},'target_price_weight':'애널리스트 목표가 차이는 100점 중 최대 4점만 반영','labels':{'우선 추천':'85점 이상·탈락조건/경고 없음','추천':'75점 이상·탈락조건/경고 없음','관심':'경고가 있거나 65~74.9점','제외':'탈락조건 존재'},'note':'점수는 기대수익률·상승확률이 아닙니다. 같은 입력으로 후보 우선순위를 일관되게 비교하기 위한 규칙입니다.'}}
    Path('stock-recommendations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    Path('stock-recommendations-summary.json').write_text(json.dumps({k:out[k] for k in ('version','generated_at','source_generated_at','counts','top_recommendations','method')},ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(counts);print([(x['symbol'],x['name'],x['grade'],x['score']) for x in top])
if __name__=='__main__':main()
