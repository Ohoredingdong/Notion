#!/usr/bin/env python3
import json, math, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131 Safari/537.36','Accept':'application/json,text/plain,*/*','Accept-Language':'en-US,en;q=0.9'}
CNN={**UA,'Origin':'https://www.cnn.com','Referer':'https://www.cnn.com/markets/fear-and-greed'}
COMP={'vix':'market_volatility_vix','momentum':'market_momentum_sp500','strength':'stock_price_strength','put_call':'put_call_options','junk':'junk_bond_demand'}

def now_iso(): return datetime.now(timezone.utc).isoformat()
def num(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def get(url,headers=None,retries=3):
    last=None
    for attempt in range(retries):
        try:
            sep='&' if '?' in url else '?'
            req=urllib.request.Request(f'{url}{sep}_ts={int(time.time())}',headers=headers or UA)
            with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
        except Exception as e:
            last=e
            if attempt<retries-1: time.sleep(2*(attempt+1))
    raise last

def cls(v):
    v=num(v)
    if v is None:return 'neutral'
    if v<25:return 'extreme fear'
    if v<45:return 'fear'
    if v<55:return 'neutral'
    if v<75:return 'greed'
    return 'extreme greed'

def latest_raw(block):
    for row in reversed((block or {}).get('data') or []):
        x=num(row.get('y'))
        if x is not None:return x
    return None

def path(name): return ROOT/name
def read_old(name):
    try:return json.loads(path(name).read_text(encoding='utf-8'))
    except Exception:return {}
def write(name,data): path(name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def us():
    raw=get('https://production.dataviz.cnn.io/index/fearandgreed/graphdata',CNN)
    fg=raw.get('fear_and_greed') or {}; hist=[]
    for row in (raw.get('fear_and_greed_historical') or {}).get('data') or []:
        x,y=row.get('x'),num(row.get('y'))
        if x is not None and y is not None:hist.append({'timestamp':int(x),'value':y,'rating':row.get('rating') or cls(y)})
    score=num(fg.get('score'))
    if score is None: raise RuntimeError('CNN score missing')
    comp={}
    for k,src in COMP.items():
        b=raw.get(src) or {}; comp[k]={'score':num(b.get('score')),'rating':b.get('rating'),'raw_value':latest_raw(b)}
    vals=[x['value'] for x in hist]
    source_ts=fg.get('timestamp')
    return {'market':'us','updated_at':now_iso(),'source_timestamp':source_ts,'source_name':'CNN Fear & Greed','source_cadence':'intraday','headline':{'score':score,'rating':fg.get('rating') or cls(score),'timestamp':source_ts,'previous_close':num(fg.get('previous_close')),'previous_1_week':num(fg.get('previous_1_week')),'previous_1_month':num(fg.get('previous_1_month')),'previous_1_year':num(fg.get('previous_1_year'))},'one_year_average':sum(vals)/len(vals) if vals else None,'history':hist[-30:],'components':comp,'note':'미국 증시 투자심리를 CNN Fear & Greed 기준으로 표시합니다.'}

def crypto():
    raw=get('https://api.alternative.me/fng/?limit=120&format=json')
    rows=list(reversed(raw.get('data') or [])); hist=[]
    for row in rows:
        v=num(row.get('value')); ts=row.get('timestamp')
        if v is not None and ts is not None:hist.append({'timestamp':int(ts)*1000,'value':v,'rating':(row.get('value_classification') or cls(v)).lower()})
    if not hist:raise RuntimeError('Alternative.me data unavailable')
    cur=hist[-1]['value']; p1=hist[-2]['value'] if len(hist)>1 else None; p7=hist[-8]['value'] if len(hist)>7 else None; p30=hist[-31]['value'] if len(hist)>30 else None
    def avg(n):
        a=[x['value'] for x in hist[-n:]]; return sum(a)/len(a) if a else None
    def item(label,icon,value,meta):return {'label':label,'icon':icon,'value':('—' if value is None else f'{value:.1f}'.rstrip('0').rstrip('.')),'meta':meta,'rating':cls(value)}
    source_ts=datetime.fromtimestamp(hist[-1]['timestamp']/1000,tz=timezone.utc).isoformat()
    return {'market':'crypto','updated_at':now_iso(),'source_timestamp':source_ts,'source_name':'Alternative.me','source_cadence':'daily','headline':{'score':cur,'rating':cls(cur),'timestamp':source_ts,'previous_close':p1,'previous_1_week':p7,'previous_1_month':p30,'previous_1_year':avg(90)},'one_year_average':avg(120),'history':hist[-30:],'indicators':[item('7일 평균','7D',avg(7),'단기 심리'),item('30일 평균','30',avg(30),'중기 심리'),item('90일 평균','90',avg(90),'장기 심리'),item('24시간 변화','Δ',cur-p1 if p1 is not None else None,'어제 대비'),item('1주 변화','W',cur-p7 if p7 is not None else None,'1주 전 대비')],'note':'암호화폐 시장의 전반적인 위험선호를 Alternative.me 지수로 표시합니다.'}

def chart(symbol):
    s=urllib.parse.quote(symbol,safe='')
    r=((get(f'https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=6mo&interval=1d&includePrePost=false').get('chart') or {}).get('result') or [None])[0]
    if not r:raise RuntimeError(symbol)
    t=r.get('timestamp') or []; c=(((r.get('indicators') or {}).get('quote') or [{}])[0].get('close') or [])
    return [(int(ts)*1000,num(v)) for ts,v in zip(t,c) if ts is not None and num(v) is not None]

def pos(series,window=20,invert=False):
    v=[x[1] for x in series][-window:]
    if len(v)<2:return 50.0
    lo,hi,cur=min(v),max(v),v[-1]; p=50.0 if hi==lo else (cur-lo)/(hi-lo)*100
    return 100-p if invert else p

def mom(series,window=20):
    v=[x[1] for x in series]
    if len(v)<window:return 50.0
    cur=v[-1]; ma=sum(v[-window:])/window; p=(cur/ma-1)*100
    return max(0,min(100,50+p*8))

def korea():
    k=chart('^KS11'); q=chart('^KQ11'); fx=chart('KRW=X')
    kp,qp,fp,mp=pos(k),pos(q),pos(fx,invert=True),mom(k); score=(kp+qp+fp+mp)/4
    hist=[]; start=max(20,len(k)-30)
    for i in range(start,len(k)):
        s1=pos(k[:i+1]); s2=pos(q[:min(i+1,len(q))]); s3=pos(fx[:min(i+1,len(fx))],invert=True); s4=mom(k[:i+1]); v=(s1+s2+s3+s4)/4
        hist.append({'timestamp':k[i][0],'value':round(v,2),'rating':cls(v)})
    p1=hist[-2]['value'] if len(hist)>1 else None; p7=hist[-8]['value'] if len(hist)>7 else None; p30=hist[0]['value'] if hist else None
    def item(label,icon,value,meta):return {'label':label,'icon':icon,'value':f'{value:.1f}'.rstrip('0').rstrip('.'),'meta':meta,'rating':cls(value)}
    source_ts=datetime.fromtimestamp(k[-1][0]/1000,tz=timezone.utc).isoformat()
    return {'market':'korea','updated_at':now_iso(),'source_timestamp':source_ts,'source_name':'Custom Korea Model','source_cadence':'market data','headline':{'score':round(score,2),'rating':cls(score),'timestamp':source_ts,'previous_close':p1,'previous_1_week':p7,'previous_1_month':p30,'previous_1_year':50.0},'one_year_average':50.0,'history':hist[-30:],'indicators':[item('KOSPI 위치','Ⓚ',kp,'20일 범위 기준'),item('KOSDAQ 위치','Ⓠ',qp,'20일 범위 기준'),item('USD/KRW','₩',fp,'원화 강세 = 위험선호'),item('20일 모멘텀','↗',mp,'KOSPI 기준'),item('종합 위험선호','◎',score,'커스텀 종합 점수')],'note':'한국에는 CNN과 동일한 공식 Fear & Greed가 없어 KOSPI·KOSDAQ·환율·모멘텀을 조합한 커스텀 지수로 표시합니다.'}

def safe_update(name,fn):
    checked=now_iso(); old=read_old(name)
    try:
        data=fn(); data['checked_at']=checked; data['status']='live'; data.pop('error',None); write(name,data); print(f'OK {name}')
    except Exception as e:
        if not old: raise
        old['checked_at']=checked; old['status']='stale'; old['error']=f'{type(e).__name__}: {e}'[:180]; write(name,old); print(f'STALE {name}: {e}')

if __name__=='__main__':
    safe_update('fear-greed-data.json',us)
    safe_update('crypto-fear-greed-data.json',crypto)
    safe_update('korea-market-sentiment.json',korea)
