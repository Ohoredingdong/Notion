"""Investment decision data v7. Read-only, no orders and no probability claims.

One provider snapshot per company. A forecast is NOT an audited result; a target
range is NOT intrinsic value or a confidence interval. Quotes use the last
completed regular session, including a 30 minute reporting buffer. Missing data
never becomes zero or a successful check. Existing financial files are untouched.
"""
from __future__ import annotations
import json, math, os, time, hashlib, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

VERSION='decision-v7.1'
OUT=Path('stock-decision-data.json')
UTC=timezone.utc
UNIVERSE=[('AAPL','Apple','US','소비자 기술'),('MSFT','Microsoft','US','클라우드·SW'),('NVDA','NVIDIA','US','AI 반도체'),('AMZN','Amazon','US','커머스·클라우드'),('TSLA','Tesla','US','자동차·에너지'),('005930','삼성전자','KR','반도체·전자'),('000660','SK하이닉스','KR','메모리 반도체'),('035420','NAVER','KR','플랫폼'),('207940','삼성바이오로직스','KR','바이오 위탁생산'),('005380','현대자동차','KR','자동차')]
RULES={'volume_ratio':1.5,'min_analysts':5,'target_upside_pct':20.0,'revision_floor_pct':-3.0,'max_target_spread':0.8,'max_eps_spread':0.5,'max_net_debt_ebitda':3.0,'min_reward_risk':2.0,'max_support_loss_pct':8.0}

def num(x):
    if isinstance(x,bool):return None
    try:
        n=float(x)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError):return None

def change(new,old):
    a,b=num(new),num(old)
    return (a/b-1)*100 if a is not None and b is not None and b>0 else None

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,(datetime,)):return x.isoformat()
    if hasattr(x,'item'):return clean(x.item())
    if isinstance(x,float):return round(x,8) if math.isfinite(x) else None
    if hasattr(x,'isoformat'):return x.isoformat()
    return x

def read(p,default):
    try:return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def frame_rows(df):
    if df is None or getattr(df,'empty',True):return {}
    return {str(i):{str(k):num(v) for k,v in row.items()} for i,row in df.iterrows()}

def latest_session(market,now):
    import pandas as pd
    import exchange_calendars as xc
    cal=xc.get_calendar('XKRX' if market=='KR' else 'XNYS')
    schedule=cal.schedule.loc[(now-timedelta(days=40)).date().isoformat():(now+timedelta(days=5)).date().isoformat()]
    eligible=schedule[schedule['close']+pd.Timedelta(minutes=30)<=pd.Timestamp(now)]
    if eligible.empty:raise ValueError('거래소 완료 세션을 결정할 수 없음')
    idx=eligible.index[-1]
    return {'date':str(idx.date()),'closed_at':eligible.iloc[-1]['close'].isoformat(),'calendar':cal.name,'buffer_minutes':30,'schedule_note':'exchange_calendars 커뮤니티 달력; 임시휴장 변경은 거래소 원문 확인'}

def bars_from(df,session):
    rows=[]
    if df is None or df.empty:return rows
    for stamp,r in df.iterrows():
        date=stamp.date().isoformat()
        if date>session['date']:continue
        values={k.lower():num(r.get(k)) for k in ('Open','High','Low','Close','Volume')}
        if any(values[k] is None for k in values) or values['close']<=0 or values['volume']<0:continue
        if values['high']<max(values['open'],values['close']) or values['low']>min(values['open'],values['close']):continue
        rows.append({'date':date,**values,'split':num(r.get('Stock Splits')) or 0})
    return sorted(rows,key=lambda r:r['date'])

def technical(bars,benchmark):
    if len(bars)<61:return {'status':'missing','reason':'완료 일봉 61개 이상 필요'}
    b=bars[-1];c=b['close'];prev=bars[-21:-1]
    true_ranges=[max(r['high']-r['low'],abs(r['high']-bars[i-1]['close']),abs(r['low']-bars[i-1]['close'])) for i,r in enumerate(bars) if i>0]
    avgvol=mean(r['volume'] for r in prev)
    stock_by={r['date']:r['close'] for r in bars};bench_by={r['date']:r['close'] for r in benchmark}
    common=sorted(set(stock_by)&set(bench_by))
    relative=None
    if len(common)>=21 and common[-1]==b['date']:
        end,start=common[-1],common[-21]
        relative=change(stock_by[end],stock_by[start])-change(bench_by[end],bench_by[start])
    support=min(r['low'] for r in bars[-11:-1]);resistance=max(r['high'] for r in bars[-253:-1])
    risk=c-support;reward=resistance-c
    return {'status':'ok','date':b['date'],'close':c,'volume':b['volume'],'avg_volume20':avgvol,
            'volume_ratio':b['volume']/avgvol if avgvol>0 else None,'ma20':mean(r['close'] for r in bars[-20:]),
            'ma60':mean(r['close'] for r in bars[-60:]),'atr14':mean(true_ranges[-14:]),
            'prior_high20':max(r['high'] for r in prev),'return20_pct':change(c,bars[-21]['close']),
            'relative20_pp':relative,'support10':support,'resistance_1y':resistance,
            'support_loss_pct':risk/c*100 if risk>0 else None,
            'reward_risk':reward/risk if risk>0 and reward>0 else None,
            'recent_split':any(r['split']!=0 for r in bars[-30:]),
            'note':'기술적 지표만 계산. 지지·저항은 매도 체결가격 보장/확률/적정가치가 아님. 상대성과는 배당 미포함 가격수익률.'}

def forecast_data(estimates,trends,info,price):
    current=estimates.get('0y',{});following=estimates.get('+1y',{});tr=trends.get('+1y',{})
    avg=num(following.get('avg'));lo=num(following.get('low'));hi=num(following.get('high'))
    valid=avg is not None and lo is not None and hi is not None and 0<lo<=avg<=hi
    first_end=info.get('nextFiscalYearEnd');period=None;nextperiod=None
    if num(first_end):
        d=datetime.fromtimestamp(float(first_end),UTC).date();period=d.isoformat()
        try:nextperiod=d.replace(year=d.year+1).isoformat()
        except ValueError:nextperiod=d.replace(year=d.year+1,day=28).isoformat()
    count=num(following.get('numberOfAnalysts'))
    # Positive comparison denominator only; never report turnaround as percentage growth.
    revision=change(tr.get('current'),tr.get('30daysAgo'))
    return {'status':'ok' if valid else 'missing','current_fy':current,'next_fy':following,
            'current_fy_end_provider':period,'next_fy_end_inferred':nextperiod,
            'period_note':'0y/+1y는 제공처의 이번/다음 회계연도. +1y 결산일은 0y 표기에서 1년을 더한 표시로 52주 회계의 실제 날짜와 다를 수 있음.',
            'eps_revision30_pct':revision,'eps_trend_next_fy':tr,
            'eps_growth_next_fy_pct':change(avg,current.get('avg')),'next_fy_pe':price/avg if valid and price and avg>0 else None,
            'analysts':count,'spread':(hi-lo)/avg if valid else None,
            'currency':info.get('financialCurrency'),'basis':'제공처 애널리스트 추정; GAAP/조정 EPS 구분 미제공. 과거 공시 EPS와 직접 성장률 비교하지 않음.',
            'source_report_dates_available':False}

def target_data(targets,info,price):
    vals={k:num(targets.get(k)) for k in ('low','median','mean','high')}
    n=num(info.get('numberOfAnalystOpinions'));l,m,h=vals['low'],vals['median'],vals['high']
    valid=all(v is not None and v>0 for v in (l,m,h)) and l<=m<=h
    return {'status':'ok' if valid else 'missing',**vals,'analysts':n,
            'median_gap_pct':change(m,price) if valid else None,'low_gap_pct':change(l,price) if valid else None,
            'spread':(h-l)/m if valid else None,
            'review_price_ceiling':m/(1+RULES['target_upside_pct']/100) if valid else None,
            'note':'애널리스트 목표가 분포. 적정가치/손실 최저선/신뢰구간이 아님. 검토가격은 목표가 중앙값까지 20% 여유를 요구한다는 명시적 정책 가정.',
            'report_dates_available':False}

def historical_audit(row,audit,now):
    item=next((x for x in audit.get('companies',[]) if x.get('symbol')==row.get('symbol')),None)
    if not item:return {'matched':[],'status':'missing','reason':'공식 대조 기록 없음'}
    try:age=(now-datetime.fromisoformat(audit['generated_at'].replace('Z','+00:00'))).total_seconds()/3600
    except (ValueError,KeyError):age=math.inf
    matches=[];wrong=[]
    for f in item.get('fields',[]):
        key=f.get('field');old=num(f.get('widget_value'));new=num(row.get(key))
        same=old is not None and new is not None and abs(old-new)<=max(1e-8,abs(new)*1e-10)
        if f.get('status')=='match' and same and f.get('widget_period')==row.get('filing_period') and age<=36:matches.append(key)
        if f.get('status') in ('mismatch','basis_mismatch','unit_mismatch'):wrong.append(key)
    src=item.get('source') or {}
    return {'status':'current' if age<=36 else 'stale','matched':matches,'issues':wrong,'checked_at':audit.get('generated_at'),
            'source_url':src.get('url') or src.get('source_url'),'period':row.get('filing_period'),
            'note':'과거 실적의 원문 대조만 해당. 미래 EPS와 목표가는 별도 검증 전.'}

def short_decision(t,fresh,earnings_days=None):
    reasons=[];conditions=[]
    if not fresh or t.get('status')!='ok':return {'state':'data_wait','label':'판단 보류 · 완료 시세 부족','reasons':['거래소 완료 세션과 수집 일봉이 일치해야 함'],'change_conditions':['다음 수집에서 완료 일봉·거래량을 확보'],'horizon':'5~20거래일'}
    if t.get('recent_split'):return {'state':'data_wait','label':'판단 보류 · 기업행사 확인','reasons':['최근 액면분할/병합이 있어 가격 기준 대조 필요'],'change_conditions':['수정주가와 거래량 기준 대조'],'horizon':'5~20거래일'}
    c=t['close'];trend=c>t['ma20']>t['ma60'];vol=t.get('volume_ratio');relative=t.get('relative20_pp');rr=t.get('reward_risk')
    breakout=c>=t['prior_high20'];volume_ok=vol is not None and vol>=RULES['volume_ratio'];relative_ok=relative is not None and relative>0
    risk_ok=rr is not None and rr>=RULES['min_reward_risk'] and 0<(t.get('support_loss_pct') or 0)<=RULES['max_support_loss_pct']
    if c<t['ma20']:reasons.append('종가가 20일 평균 아래: 가격 추세 약세')
    if not volume_ok:reasons.append('거래량이 직전 20일 평균의 1.5배에 미달하거나 미확인')
    if not relative_ok:reasons.append('최근 20거래일 시장 대비 강세 미확인')
    if not risk_ok:reasons.append('과거 지지·저항 기준 손익비 2배/지지 이탈폭 8% 이내 조건 미충족')
    imminent=earnings_days is not None and 0<=earnings_days<=3
    if imminent:reasons.append('3일 이내 실적발표 예상: 갭 변동 위험')
    ready=trend and breakout and volume_ok and relative_ok and risk_ok and not imminent
    state='conditional' if ready else 'avoid_entry' if c<t['ma60'] and not relative_ok else 'watch'
    label={'conditional':'조건부 기술적 진입 검토','avoid_entry':'신규 진입 보류 · 추세 약세','watch':'관망 · 추세/수급 조건 대기'}[state]
    if ready:reasons.append('돌파·거래량·상대강도·가격구조 조건이 동시에 충족됨; 뉴스 원문 대조 후 판단')
    conditions=[f"종가가 직전 20일 고점 {t['prior_high20']:,.2f} 이상인지",'거래량 20일 평균 대비 1.5배 이상 + 시장대비 상대강도 양수',f"10일 저점 {t['support10']:,.2f} 이탈 시 기술적 가설 재검토"]
    return {'state':state,'label':label,'reasons':reasons,'change_conditions':conditions,'horizon':'5~20거래일','event_causality_verified':False,'rule_note':'명시적 기술적 선별 규칙. 뉴스 효과·성공확률·체결 가능성을 검증한 전략이 아님.'}

def long_decision(f,t,b,proof,fresh):
    reasons=[];conditions=[];blocked=[]
    if not fresh:blocked.append('완료 시세 기준 불일치')
    if f.get('status')!='ok':blocked.append('다음 회계연도 EPS 범위 없음')
    if t.get('status')!='ok':blocked.append('목표가 범위 없음')
    if (f.get('analysts') or 0)<RULES['min_analysts'] or (t.get('analysts') or 0)<RULES['min_analysts']:blocked.append('분석가 표본 5명 미만 또는 확인 불가')
    if not {'revenue','eps','fcf'}.issubset(set(proof.get('matched',[]))):blocked.append('과거 매출·EPS·FCF 공식 대조 미완료')
    if b.get('net_debt_ebitda') is None:blocked.append('부채·현금·EBITDA 비교 자료 부족')
    if f.get('eps_revision30_pct') is None:blocked.append('동일 회계연도 EPS 30일 변화 없음')
    gap=t.get('median_gap_pct');revision=f.get('eps_revision30_pct');growth=f.get('eps_growth_next_fy_pct');leverage=b.get('net_debt_ebitda')
    reasons.extend(blocked)
    spread=max(f.get('spread') or 0,t.get('spread') or 0)
    weak=(revision is not None and revision<RULES['revision_floor_pct']) or (growth is not None and growth<0) or (leverage is not None and leverage>RULES['max_net_debt_ebitda'])
    uncertain=(f.get('spread') or 0)>RULES['max_eps_spread'] or (t.get('spread') or 0)>RULES['max_target_spread']
    if blocked:state,label='data_wait','매수 판단 보류 · 핵심 근거 부족'
    elif weak:state,label='risk_review','비중 확대 보류 · 전망/부채 점검'
    elif gap is None or gap<RULES['target_upside_pct']:state,label='price_wait','가격 대기 · 목표가 대비 여유 부족'
    elif uncertain:state,label='uncertain','보수적 검토 · 전망 편차 큼'
    else:state,label='conditional','조건부 매수 검토 · 단일 제공처 추정'
    if revision is not None:reasons.append(f'다음 회계연도 예상 EPS의 30일 변화 {revision:+.2f}%')
    if gap is not None:reasons.append(f'목표가 중앙값과 완료 종가 차이 {gap:+.1f}% (기대수익률 아님)')
    if leverage is not None:reasons.append(f'순차입금/EBITDA {leverage:.2f}배 (제공처 집계; 만기구조는 별도)')
    if uncertain:reasons.append('EPS 또는 목표가 상·하단 차이가 정책 허용폭보다 큼')
    if t.get('review_price_ceiling'):conditions.append(f"목표가가 유지된다는 전제에서 {t['review_price_ceiling']:,.2f} 이하인지 재검토 (중앙 목표가까지 20% 여유 가정)")
    conditions+=['EPS 전망이 30일 대비 3% 넘게 하향되면 가설 재검토','다음 공식 실적·CAPEX·현금흐름 전망과 컨센서스를 독립 대조']
    return {'state':state,'label':label,'reasons':reasons,'change_conditions':conditions,'horizon':'사업 관점 3년 이상; 숫자는 다음 회계연도/제공처 목표가 기준','forecast_primary_verified':False,'remaining':['미래 FCF 모델 미구축','실적 가이던스 원문 대조 미완료','목표가 개별 리포트 날짜 미제공','부채 만기표 미수집'],'rule_note':'컨센서스와 명시적 문턱값에 따른 선별. 내재가치 산정/확률/개인 맞춤 매매 지시 아님.'}

def collect_symbol(symbol,name,market,sector,base,audit,benchmark,now):
    import yfinance as yf
    source_symbol=symbol+'.KS' if market=='KR' else symbol
    ticker=yf.Ticker(source_symbol);errors=[]
    def call(label,fn,default):
        try:
            v=fn();time.sleep(.25);return v
        except Exception as e:
            errors.append({'field':label,'error':type(e).__name__+': '+str(e)[:160]});return default
    session=latest_session(market,now)
    raw=call('ohlcv',lambda:ticker.history(period='1y',auto_adjust=False,actions=True,raise_errors=True),None)
    bars=bars_from(raw,session);info=call('quote_and_balance',ticker.get_info,{})
    history_price=bars[-1]['close'] if bars else None
    estimates=frame_rows(call('earnings_estimate',ticker.get_earnings_estimate,None));trends=frame_rows(call('eps_trend',ticker.get_eps_trend,None))
    targets=call('analyst_price_targets',ticker.get_analyst_price_targets,{}) or {}
    calendar=clean(call('earnings_calendar',lambda:ticker.calendar,{}) or {})
    revisions=frame_rows(call('eps_revisions',ticker.get_eps_revisions,None))
    f=forecast_data(estimates,trends,info,history_price);t=target_data(targets,info,history_price)
    financial_ccy=info.get('financialCurrency');quote_ccy=info.get('currency');expected='KRW' if market=='KR' else 'USD'
    ccy_ok=financial_ccy==quote_ccy==expected
    fresh=bool(bars and bars[-1]['date']==session['date'] and ccy_ok)
    if not ccy_ok:errors.append({'field':'currency','error':'주가/재무 통화 일치 확인 불가'});f['status']='currency_mismatch'
    tech=technical(bars,benchmark)
    cash,debt,ebitda=[num(info.get(k)) for k in ('totalCash','totalDebt','ebitda')]
    b={'cash':cash,'debt':debt,'ebitda':ebitda,'net_debt_ebitda':(debt-cash)/ebitda if cash is not None and debt is not None and ebitda and ebitda>0 else None,'currency':financial_ccy,'asof':datetime.fromtimestamp(info['mostRecentQuarter'],UTC).date().isoformat() if num(info.get('mostRecentQuarter')) else None,'basis':'제공처 집계; EBITDA 기간·리스 포함·금융자회사 범위는 독립 대조 전'}
    if symbol in ('005380',):b['net_debt_ebitda']=None;b['basis']='자동차 금융자회사 연결 영향: 일반 기업용 순차입금/EBITDA 판정 제외'
    proof=historical_audit(base,audit,now)
    earnings=calendar.get('Earnings Date') or [];days=None
    if earnings:
        try:days=(datetime.fromisoformat(str(earnings[0])[:10]).date()-now.date()).days
        except ValueError:pass
    news=call('news',lambda:ticker.get_news(count=3),[]) or []
    links=[]
    for item in news:
        content=item.get('content') or item;link=(content.get('canonicalUrl') or {}).get('url') or content.get('link')
        if link and link.startswith('https://'):links.append({'title':content.get('title'),'url':link,'published':content.get('pubDate'),'source':(content.get('provider') or {}).get('displayName'),'status':'headline_only_not_causal_evidence'})
    data_url='https://finance.yahoo.com/quote/'+source_symbol
    return {'symbol':symbol,'name':name,'market':market,'sector':sector,'collected_at':datetime.now(UTC).isoformat(),'status':'current' if fresh else 'incomplete','currency':expected,
            'price':history_price,'price_session':bars[-1]['date'] if bars else None,'expected_session':session,'technical':tech,
            'forecasts':f,'targets':t,'balance':b,'eps_revisions':revisions,'earnings_calendar':calendar,'earnings_calendar_status':'provider_estimate_not_company_confirmed','news':links,
            'official_history':proof,'short':short_decision(tech,fresh,days),'long':long_decision(f,t,b,proof,fresh),
            'flow':{'status':'not_connected','reason':'외국인·기관 순매수는 거래량으로 추정하지 않음. 별도 수급 데이터 연결 필요.','url':'https://finance.naver.com/item/frgn.naver?code='+symbol if market=='KR' else 'https://www.sec.gov/edgar/search/'},
            'sources':{'history':data_url+'/history/','estimates':data_url+'/analysis/','balance':data_url+'/balance-sheet/','cashflow':data_url+'/cash-flow/','news':data_url+'/news/','official':proof.get('source_url')},
            'errors':errors,'disclosure':'Yahoo 단일 제공처의 개인 연구용 참고 데이터. 공식 실적 검증과 전망치/목표가 검증은 다름. 공개 재배포·상용 사용 전 제공처 사용권한 별도 확인.'}

def main():
    import yfinance as yf
    now=datetime.now(UTC)
    base=read('stock-value-radar-data.json',{});audit=read('stock-official-audit.json',{})
    bases={x.get('symbol'):x for x in base.get('rows',[])}
    benchmarks={}
    for market,sym in [('US','SPY'),('KR','^KS11')]:
        try:benchmarks[market]=bars_from(yf.Ticker(sym).history(period='1y',auto_adjust=False,actions=True,raise_errors=True),latest_session(market,now))
        except Exception:benchmarks[market]=[]
    rows=[]
    for symbol,name,market,sector in UNIVERSE:
        try:row=collect_symbol(symbol,name,market,sector,bases.get(symbol,{}),audit,benchmarks[market],now)
        except Exception as e:row={'symbol':symbol,'name':name,'market':market,'sector':sector,'status':'failed','collected_at':datetime.now(UTC).isoformat(),'errors':[{'field':'collector','error':type(e).__name__+': '+str(e)[:160]}]}
        rows.append(row);print(symbol,row['status'],row.get('short',{}).get('label'),row.get('long',{}).get('label'),flush=True)
    result={'version':VERSION,'generated_at':datetime.now(UTC).isoformat(),'max_age_hours':18,'rules':RULES,'companies':rows,
            'counts':{'tracked':len(rows),'current_price':sum(r.get('status')=='current' for r in rows),'forecasts':sum(r.get('forecasts',{}).get('status')=='ok' for r in rows),'targets':sum(r.get('targets',{}).get('status')=='ok' for r in rows),'news_links':sum(len(r.get('news',[])) for r in rows)},
            'pending_setup':{'DART_API_KEY':'configured' if os.getenv('DART_API_KEY') else 'pending','investor_flow_api':'not_connected'},
            'provenance':'시세·추정실적·목표가는 이번 실행에서 새로 수집. 실패 항목에 이전 값을 덮어써 최신인 것처럼 보이지 않음.',
            'limitations':['고정 10개 관심종목; 전체 시장 스캔 아님','애널리스트 컨센서스는 공식 기업 전망/확률이 아님','단기 뉴스 방향·원인 자동 확정 없음','별도 훈련/모의투자 위젯 변경 없음']}
    OUT.write_text(json.dumps(clean(result),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    Path('stock-decision-run-summary.json').write_text(json.dumps({'generated_at':result['generated_at'],'counts':result['counts'],'states':[{'symbol':r['symbol'],'short':r.get('short',{}).get('state'),'long':r.get('long',{}).get('state'),'errors':r.get('errors',[])} for r in rows]},ensure_ascii=False,indent=2)+'\n')
    if result['counts']['current_price']==0:raise SystemExit('완료 시세가 한 종목도 없어 실행 실패로 표시')

if __name__=='__main__':main()
