"""v8: auditable research priorities, not execution orders or return probabilities.

Existing v7 thresholds remain unchanged. A high research score cannot override
missing verification, weak estimates, illiquidity or a stale market session.
Only newly fetched values are used; no failed field is silently carried forward.
"""
from __future__ import annotations
import json, math, time, os
from pathlib import Path
from datetime import datetime, timezone
from statistics import mean
from urllib.parse import quote
import update_stock_decisions as core

RULES={**core.RULES,'min_turnover_usd':5000000,'min_turnover_krw':1000000000}
FIELDS=['revenue','revenue_growth','operating_income','operating_margin','net_income','eps','capex','fcf']
OUT=Path('stock-opportunity-data.json')
N=core.num


def size_group(cap,market):
    cap=N(cap)
    if cap is None or cap<=0:return 'unknown'
    if market=='US':
        return 'mega' if cap>=200e9 else 'large' if cap>=10e9 else 'mid' if cap>=2e9 else 'small' if cap>=300e6 else 'micro'
    return 'mega' if cap>=100e12 else 'large' if cap>=10e12 else 'mid' if cap>=1e12 else 'small' if cap>=200e9 else 'micro'


def priority_score(row):
    """Fixed research rubric; missing fields receive zero, not inflated weights."""
    f=row.get('forecasts',{});t=row.get('targets',{});b=row.get('balance',{});h=row.get('history',{});tech=row.get('technical',{})
    g=N(t.get('median_gap_pct'));eg=N(f.get('eps_growth_next_fy_pct'));rev=N(f.get('eps_revision30_pct'));lev=N(b.get('net_debt_ebitda'));fcf=N(h.get('fcf'));rel=N(tech.get('relative20_pp'))
    items=[]
    def add(name,value,maxpoints,points,rule):items.append({'name':name,'value':value,'points':points if value is not None else 0,'maximum':maxpoints,'rule':rule,'available':value is not None})
    add('목표가 중앙값 대비 여유',g,25,25 if g is not None and g>=30 else 20 if g is not None and g>=20 else 12 if g is not None and g>=10 else 5 if g is not None and g>=0 else 0,'30% 이상 25점 / 20% 이상 20점 / 10% 이상 12점 / 0% 이상 5점. 목표가는 내재가치가 아님.')
    add('예상 EPS 성장',eg,20,20 if eg is not None and eg>=20 else 15 if eg is not None and eg>=10 else 8 if eg is not None and eg>0 else 0,'다음 FY 대 이번 FY 예상 EPS 성장 20% 이상 20점 / 10% 이상 15점 / 양수 8점.')
    add('EPS 전망 30일 변화',rev,15,15 if rev is not None and rev>=2 else 10 if rev is not None and rev>=0 else 5 if rev is not None and rev>=-3 else 0,'2% 이상 15점 / 0% 이상 10점 / -3% 이상 5점. 같은 FY 전망끼리 비교.')
    add('순차입금 부담',lev,15,15 if lev is not None and lev<=0 else 12 if lev is not None and lev<=1 else 6 if lev is not None and lev<=3 else 0,'순차입금/EBITDA 0 이하 15점 / 1 이하 12점 / 3 이하 6점. 금융업·자동차 금융연결은 미판정.')
    add('연간 잉여현금흐름',fcf,10,10 if fcf is not None and fcf>0 else 0,'동일 FY 영업현금흐름-CAPEX가 양수 10점. 현금 잔액이 아님.')
    add('시장 대비 상대성과',rel,10,10 if rel is not None and rel>=5 else 5 if rel is not None and rel>0 else 0,'20거래일 상대 가격수익률 5%p 이상 10점 / 양수 5점. 배당 제외.')
    es=N(f.get('spread'));ts=N(t.get('spread'));spread=max(es,ts) if es is not None and ts is not None else None
    add('전망 편차',spread,5,5 if es is not None and ts is not None and es<=RULES['max_eps_spread'] and ts<=RULES['max_target_spread'] else 0,'EPS (고-저)/평균 0.5 이하 및 목표가 (고-저)/중앙값 0.8 이하일 때 5점.')
    return {'score':sum(x['points'] for x in items),'maximum':100,'available':sum(x['available'] for x in items),'factors':items,'meaning':'주어진 후보 안의 조사 순서. 수익률·성공확률·절대 기업가치 점수가 아닙니다. 검증 상태와 별도입니다.'}


def assessment(row):
    f=row.get('forecasts',{});t=row.get('targets',{});b=row.get('balance',{});h=row.get('history',{});proof=row.get('official_history',{});tech=row.get('technical',{})
    fresh=row.get('status')=='current';count=N(f.get('analysts'));tc=N(t.get('analysts'));g=N(t.get('median_gap_pct'));rev=N(f.get('eps_revision30_pct'));growth=N(f.get('eps_growth_next_fy_pct'));lev=N(b.get('net_debt_ebitda'));fcf=N(h.get('fcf'))
    missing=[];risks=[];checks=[]
    def ck(key,label,ok,actual):checks.append({'key':key,'label':label,'ok':bool(ok),'actual':actual})
    ck('price','완료 거래일·통화 일치',fresh,row.get('price_session'))
    ck('sample','EPS/목표가 분석가 각 5명 이상',count is not None and tc is not None and min(count,tc)>=RULES['min_analysts'],{'eps':count,'target':tc})
    ck('room','목표가 중앙값까지 20% 이상 여유',g is not None and g>=20,g)
    ck('revision','EPS 전망 하향 3% 이내',rev is not None and rev>=-3,rev)
    ck('growth','다음 회계연도 EPS 성장 양수',growth is not None and growth>0,growth)
    es=N(f.get('spread'));ts=N(t.get('spread'));ck('dispersion','EPS·목표가 전망 편차 범위 이내',es is not None and ts is not None and es<=0.5 and ts<=0.8,{'eps':es,'target':ts})
    ck('debt','순차입금/EBITDA 3배 이내',lev is not None and lev<=3,lev)
    ck('cash','연간 FCF 양수',fcf is not None and fcf>0,fcf)
    matched=set(proof.get('matched',[]));ck('audit','과거 매출·EPS·FCF 공식 대조',{'revenue','eps','fcf'}.issubset(matched) and not proof.get('issues'),sorted(matched))
    turnover=N(row.get('liquidity',{}).get('avg_turnover20'));floor=RULES['min_turnover_krw'] if row.get('market')=='KR' else RULES['min_turnover_usd'];liquid=turnover is not None and turnover>=floor
    ck('liquidity','20일 평균 거래대금 기준 충족',liquid,turnover)
    if not fresh:missing.append('최신 완료 거래일의 시세·통화 확인')
    if f.get('status')!='ok':missing.append('다음 회계연도 EPS 상·하단')
    if t.get('status')!='ok':missing.append('목표가 중앙값·상하단')
    if count is None or tc is None or min(count,tc)<5:missing.append('최소 5명 이상의 전망 표본')
    if rev is None:missing.append('같은 회계연도 EPS 30일 변화')
    if lev is None:missing.append('적합한 부채·현금 분석')
    if fcf is None:missing.append('같은 회계연도의 FCF')
    if turnover is None:missing.append('거래대금')
    if rev is not None and rev<-3:risks.append('EPS 전망이 30일 동안 3% 넘게 하향')
    if growth is not None and growth<=0:risks.append('다음 회계연도 예상 EPS 성장 비양수')
    if lev is not None and lev>3:risks.append('순차입금/EBITDA 3배 초과')
    if fcf is not None and fcf<=0:risks.append('연간 FCF 비양수: 투자·현금회수 점검')
    if es is not None and es>0.5:risks.append('EPS 전망 상·하단 편차 큼')
    if ts is not None and ts>0.8:risks.append('목표가 전망 상·하단 편차 큼')
    if not liquid and turnover is not None:risks.append('거래대금 부족')
    if row.get('size_group')=='micro':risks.append('자체 규모 기준의 초소형 기업')
    if proof.get('issues'):risks.append('공식 재무 숫자 불일치')
    if tech.get('recent_split'):risks.append('최근 주식분할·병합: 주가와 주당 수치 기준 대조')
    if not fresh:state,label='data','자료 갱신 필요'
    elif risks:state,label='risk','위험 요인 먼저 확인'
    elif missing:state,label='data','판단 자료 보강'
    elif g is not None and g<20:state,label='price','가격을 기다릴 후보'
    elif not checks[8]['ok']:state,label='verify','실적·가격 후보 · 공식 대조 전'
    elif all(c['ok'] for c in checks):state,label='ready','명시 조건 충족 · 매수 후보'
    else:state,label='data','조건 추가 확인'
    ceiling=N(t.get('review_price_ceiling'));price=N(row.get('price'));move=core.change(ceiling,price)
    if state=='ready':next_action='조건은 충족됐습니다. 원문 실적·최신 호가·투자금의 용도를 확인한 뒤 분할 진입 여부를 결정하세요.'
    elif state=='verify':next_action='공시에서 매출·주당이익·현금흐름 3개를 먼저 대조하세요. 맞으면 같은 가격·전망 조건으로 다시 평가합니다.'
    elif state=='price':next_action='아래 조건가격을 관심 표시해 두세요. 주가가 내려와도 EPS와 목표가가 함께 하향되면 기준가격도 다시 계산합니다.'
    elif state=='risk':next_action='싸 보이는 이유가 이익 악화인지 확인하세요. 아래 실제 위험이 해소되기 전에는 비중 확대 후보로 표시하지 않습니다.'
    else:next_action='아래 누락된 항목부터 채우세요. 데이터 부재를 매도 신호 또는 낮은 기업가치로 해석하지 않습니다.'
    return {'state':state,'label':label,'checks':checks,'risks':risks,'missing':missing,'next_action':next_action,'price_condition':{'ceiling':ceiling,'current':price,'move_pct':move,'formula':'중앙 목표가 ÷ 1.20','meaning':'목표가가 유지된다는 가정의 검토 문턱값. 적정주가·보장수익이 아님.'},'invalidation':['같은 FY EPS 전망이 30일 대비 3% 넘게 하향되는지','목표가 중앙값·EPS 상하단이 바뀌어 가격 여유 조건이 사라지는지','현금흐름·부채 또는 공식 대조에 새로운 문제 발생 여부'],'is_trade_order':False,'forecast_independently_verified':False}


def annual_history(ticker,errors):
    try:
        income=ticker.get_income_stmt(freq='yearly');cash=ticker.get_cashflow(freq='yearly')
        if income is None or income.empty:return {}
        dates=sorted(income.columns,reverse=True);end=dates[0];prior=dates[1] if len(dates)>1 else None
        def val(frame,keys,day):
            if frame is None or frame.empty or day not in frame.columns:return None
            for key in keys:
                if key in frame.index:return N(frame.loc[key,day])
            return None
        rev=val(income,['TotalRevenue','Total Revenue'],end);prev=val(income,['TotalRevenue','Total Revenue'],prior);op=val(income,['OperatingIncome','Operating Income'],end)
        eps=val(income,['DilutedEPS','Diluted EPS'],end);net=val(income,['NetIncomeCommonStockholders','NetIncome','Net Income'],end)
        cfo=val(cash,['OperatingCashFlow','Operating Cash Flow'],end);rawcap=val(cash,['CapitalExpenditure','Capital Expenditure'],end);cap=abs(rawcap) if rawcap is not None else None
        return {'filing_period':str(end)[:10],'revenue':rev,'revenue_growth':core.change(rev,prev),'operating_income':op,'operating_margin':op/rev*100 if rev and op is not None else None,'net_income':net,'eps':eps,'cfo':cfo,'capex':cap,'fcf':cfo-cap if cfo is not None and cap is not None else None,'basis':'Yahoo 연간 재무; EPS는 희석, FCF=CFO-CAPEX. 공식 원문 대조와 별개.'}
    except Exception as e:errors.append({'field':'annual','error':type(e).__name__+': '+str(e)[:120]});return {}


def collect(spec,base,audit,benchmark,now):
    import yfinance as yf
    symbol,name,market,sector,source_symbol,cohort,ir=spec
    ticker=yf.Ticker(source_symbol);errors=[]
    def call(label,fn,default):
        try:v=fn();time.sleep(.12);return v
        except Exception as e:errors.append({'field':label,'error':type(e).__name__+': '+str(e)[:120]});return default
    session=core.latest_session(market,now)
    bars=core.bars_from(call('bars',lambda:ticker.history(period='1y',auto_adjust=False,actions=True,raise_errors=True),None),session)
    info=call('quote',ticker.get_info,{}) or {};price=bars[-1]['close'] if bars else None;expected='KRW' if market=='KR' else 'USD'
    fresh=bool(bars and bars[-1]['date']==session['date'] and info.get('currency')==info.get('financialCurrency')==expected)
    estimates=core.frame_rows(call('EPS',ticker.get_earnings_estimate,None));trend=core.frame_rows(call('EPS trend',ticker.get_eps_trend,None));targets=call('targets',ticker.get_analyst_price_targets,{}) or {}
    forecasts=core.forecast_data(estimates,trend,info,price);target=core.target_data(targets,info,price)
    calendar=core.clean(call('calendar',lambda:ticker.calendar,{}) or {});h=annual_history(ticker,errors)
    # For the audited original universe, preserve the exact per-account reference basis.
    hist={k:base.get(k) for k in FIELDS+['filing_period']} if base else h
    hist['basis']=base.get('statement_basis','연간 제공처 재무') if base else h.get('basis')
    c,de,e=[N(info.get(k)) for k in ('totalCash','totalDebt','ebitda')]
    balance={'cash':c,'debt':de,'ebitda':e,'net_debt_ebitda':(de-c)/e if c is not None and de is not None and e is not None and e>0 else None,'asof':datetime.fromtimestamp(info['mostRecentQuarter'],timezone.utc).date().isoformat() if N(info.get('mostRecentQuarter')) else None,'basis':'제공처 연결 집계; 만기·리스·EBITDA 기간은 별도 검증'}
    if symbol=='005380':balance['net_debt_ebitda']=None;balance['basis']='자동차 금융자회사 연결 영향으로 일반기업 비율 판정 제외'
    proof=core.historical_audit({**hist,'symbol':symbol},audit,now)
    tech=core.technical(bars,benchmark);turnover=mean(r['close']*r['volume'] for r in bars[-20:]) if len(bars)>=20 else None
    earnings=calendar.get('Earnings Date') or [];days=None
    if earnings:
        try:days=(datetime.fromisoformat(str(earnings[0])[:10]).date()-now.date()).days
        except ValueError:pass
    cap=N(info.get('marketCap'));root='https://finance.yahoo.com/quote/'+source_symbol
    official=proof.get('source_url') or ir or ('https://dart.fss.or.kr/dsab001/main.do?autoSearch=true&textCrpNm='+quote(name) if market=='KR' else 'https://www.sec.gov/edgar/search/')
    row={'symbol':symbol,'name':name,'market':market,'sector':sector,'cohort':cohort,'source_symbol':source_symbol,'currency':expected,'status':'current' if fresh else 'incomplete','collected_at':datetime.now(timezone.utc).isoformat(),'price':price,'price_session':bars[-1]['date'] if bars else None,'expected_session':session,'market_cap':cap,'size_group':size_group(cap,market),'technical':tech,'forecasts':forecasts,'targets':target,'balance':balance,'history':hist,'official_history':proof,'liquidity':{'avg_turnover20':turnover,'currency':expected,'period':'last 20 completed sessions'},'earnings_calendar':calendar,'short':core.short_decision(tech,fresh,days),'sources':{'history':root+'/history/','estimates':root+'/analysis/','cashflow':root+'/cash-flow/','balance':root+'/balance-sheet/','official':official},'errors':errors,'flow_status':'외국인·기관 수급 미연결; 거래량과 구분','forecast_basis':'단일 제공처 애널리스트 추정; 독립 대조 전·개별 리포트 날짜 미제공'}
    row['priority']=priority_score(row);row['assessment']=assessment(row)
    return row


def main():
    import yfinance as yf
    now=datetime.now(timezone.utc);specs=core.read('stock-opportunity-universe.json',{})['companies'];base=core.read('stock-value-radar-data.json',{});audit=core.read('stock-official-audit.json',{});bases={r['symbol']:r for r in base.get('rows',[])}
    benchmarks={}
    for market,sym in [('US','SPY'),('KR','^KS11')]:
        try:benchmarks[market]=core.bars_from(yf.Ticker(sym).history(period='1y',auto_adjust=False,actions=True,raise_errors=True),core.latest_session(market,now))
        except Exception:benchmarks[market]=[]
    rows=[]
    for spec in specs:
        try:row=collect(spec,bases.get(spec[0],{}),audit,benchmarks[spec[2]],now)
        except Exception as e:row={'symbol':spec[0],'name':spec[1],'market':spec[2],'sector':spec[3],'cohort':spec[5],'status':'failed','errors':[{'field':'collector','error':type(e).__name__+': '+str(e)[:140]}]};row['priority']=priority_score(row);row['assessment']=assessment(row)
        rows.append(row);print(spec[0],row.get('size_group'),row['assessment']['state'],row['priority']['score'],flush=True)
    counts={'tracked':len(rows),'current':sum(r['status']=='current' for r in rows),'expanded':sum(r.get('cohort')=='확장' for r in rows),'mid_small':sum(r.get('size_group') in ('mid','small') for r in rows)}
    for k in ('ready','verify','price','risk','data'):counts[k]=sum(r['assessment']['state']==k for r in rows)
    out={'version':'opportunity-v8.0','generated_at':datetime.now(timezone.utc).isoformat(),'max_age_hours':18,'counts':counts,'companies':rows,'rules':RULES,'scope':'고정 후보 24개 연구. 전체 시장 자동 검색이 아니며 특정 종목의 추천 선정도 아님.','size_policy':'자체 기준: US mega≥$200B, large≥$10B, mid≥$2B, small≥$300M. KR mega≥100조, large≥10조, mid≥1조, small≥0.2조. 거래소 지수 분류와 다릅니다.','data_notice':'Yahoo 단일 제공처. 확정 재무 검증과 컨센서스·목표가 검증은 다릅니다. 공개 재배포·상용 이용 권한 별도 확인.','score_notice':'매력 순위는 실제 입력값에 고정 가중치를 적용한 조사 순서이며 성공확률이나 내재가치가 아닙니다.','pending_setup':{'DART_API_KEY':'configured' if os.getenv('DART_API_KEY') else 'pending','investor_flow':'not_connected'},'training_widget_unchanged':True}
    OUT.write_text(json.dumps(core.clean(out),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    Path('stock-opportunity-summary.json').write_text(json.dumps({'generated_at':out['generated_at'],'counts':counts,'states':[{'symbol':r['symbol'],'size':r.get('size_group'),'state':r['assessment']['state'],'score':r['priority']['score']} for r in rows]},ensure_ascii=False,indent=2)+'\n')
    if counts['current']==0:raise SystemExit('모든 완료 시세 수집 실패')

if __name__=='__main__':main()
