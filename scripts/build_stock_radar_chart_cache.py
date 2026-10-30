"""Display-only dated closing-price cache; never modifies decisions or approvals."""
from __future__ import annotations
import datetime as dt
import json, math, re, tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo
UTC=dt.timezone.utc
INDEX=[('^KS11','코스피','KR','KRW'),('^KQ11','코스닥','KR','KRW'),('^IXIC','나스닥','US','USD'),('^GSPC','S&P 500','US','USD')]
def build(root=Path('.')):
    import exchange_calendars as xc
    import yfinance as yf
    now=dt.datetime.now(UTC)
    raw=json.loads((root/'stock-opportunity-data.json').read_text())
    yf.set_tz_cache_location(tempfile.mkdtemp(prefix='radar-display-'))
    calendars={m:xc.get_calendar(n,start=f'{now.year-1}-01-01',end=f'{now.year+1}-12-31') for m,n in [('KR','XKRX'),('US','XNYS')]}
    cutoff={}
    for market,cal in calendars.items():
        local=now.astimezone(ZoneInfo('Asia/Seoul' if market=='KR' else 'America/New_York'))
        label=cal.date_to_session(local.date().isoformat(),direction='previous')
        if cal.session_close(label).to_pydatetime()+dt.timedelta(minutes=30)>now: label=cal.previous_session(label)
        cutoff[market]=label.date().isoformat()
    specs=[dict(symbol=s,name=n,market=m,currency=c,provider=s) for s,n,m,c in INDEX]
    specs += [dict(symbol=str(r['symbol']),name=r['name'],market=r['market'],currency=r.get('currency'),provider=r.get('source_symbol') or r['symbol']) for r in raw['companies'] if r.get('market') in calendars]
    specs=list({r['symbol']:r for r in specs}.values())
    def collect(r):
        if not re.fullmatch(r'[A-Za-z0-9.^=-]{1,24}',r['provider']):return r['symbol'],{**r,'status':'unavailable','bars':[],'error':'invalid_provider_symbol'}
        try:
            frame=yf.Ticker(r['provider']).history(period='6mo',interval='1d',auto_adjust=False,actions=True,repair=False,timeout=12,raise_errors=True)
            bars=[];events=[]
            for stamp,row in frame.iterrows():
                date=stamp.date().isoformat();close=float(row.get('Close',float('nan')))
                if date>cutoff[r['market']] or not math.isfinite(close) or close<=0:continue
                if not calendars[r['market']].is_session(date):continue
                volume=float(row.get('Volume',0))
                bars.append({'date':date,'close':close,'volume':volume if math.isfinite(volume) else None})
                split=float(row.get('Stock Splits',0) or 0)
                if math.isfinite(split) and split:events.append({'date':date,'split':split})
            bars=sorted({b['date']:b for b in bars}.values(),key=lambda b:b['date'])
            if len(bars)<2:raise ValueError('insufficient_dated_closes')
            return r['symbol'],{**r,'status':'ok' if bars[-1]['date']==cutoff[r['market']] else 'stale','collected_at':dt.datetime.now(UTC).isoformat(),'price_session':bars[-1]['date'],'expected_session':cutoff[r['market']],'source_url':'https://finance.yahoo.com/quote/'+r['provider'],'bars':bars,'corporate_actions':events}
        except Exception as e:return r['symbol'],{**r,'status':'unavailable','bars':[],'error':type(e).__name__}
    series={}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(collect,r) for r in specs]):
            k,v=f.result();series[k]=v
    payload={'version':'radar-display-closes-1.0','generated_at':dt.datetime.now(UTC).isoformat(),'source_generated_at':raw['generated_at'],'source':'Yahoo Finance via yfinance; unofficial delayed data','basis':'제공처 Close · 완료 정규장 일봉 · 배당 재투자·환율 반영 없음','calendar_cutoff':cutoff,'counts':{k:sum(v['status']==k for v in series.values()) for k in ['ok','stale','unavailable']},'series':series,'orders_enabled':False,'used_for_investment_approval':False}
    (root/'stock-radar-chart-data.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({'chart_cache':payload['counts'],'cutoff':cutoff},ensure_ascii=False))
if __name__=='__main__':build()
