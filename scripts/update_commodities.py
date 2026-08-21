#!/usr/bin/env python3
import json, math, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'commodities-data.json'
HEADERS={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/plain,*/*'}
META={'GC=F':('gold','precious','금','GOLD','USD / oz','1g','gold'),'SI=F':('silver','precious','은','SILVER','USD / oz','1g','silver'),'CL=F':('wti','energy','WTI 원유','WTI','USD / bbl','1배럴','energy'),'BZ=F':('brent','energy','브렌트유','BRENT','USD / bbl','1배럴','energy'),'NG=F':('gas','energy','천연가스','NAT GAS','USD / MMBtu','1MMBtu','energy'),'HG=F':('copper','industrial','구리','COPPER','USD / lb','1lb','industrial'),'ALI=F':('aluminum','industrial','알루미늄','ALUMINUM','USD / mt','1톤','industrial')}
def get_json(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def chart(symbol):
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol,safe='')}?range=1mo&interval=1d&includePrePost=false&events=div%2Csplits"
    raw=get_json(u); res=(raw.get('chart',{}).get('result') or [None])[0]
    if not res: raise RuntimeError(symbol)
    m=res.get('meta',{}); ts=res.get('timestamp') or []
    closes=((res.get('indicators',{}).get('quote') or [{}])[0].get('close') or [])
    vals=[float(v) for v in closes if v is not None and math.isfinite(float(v))]
    if not vals: raise RuntimeError(f'no closes: {symbol}')
    price=float(m.get('regularMarketPrice') or vals[-1])
    prev=float(vals[-2] if len(vals)>1 else price)
    ch=((price-prev)/prev*100) if prev else 0
    source_ts=int(m.get('regularMarketTime') or (ts[-1] if ts else datetime.now(timezone.utc).timestamp()))
    return price,ch,vals[-7:],source_ts
def krw(symbol,price,fx):
    if symbol in ('GC=F','SI=F'): return price*fx/31.1034768
    return price*fx
def main():
    prev={}
    if DATA.exists():
        try: prev=json.loads(DATA.read_text(encoding='utf-8'))
        except Exception: pass
    old={i.get('symbol'):i for i in prev.get('items',[])}; fx=prev.get('fx',1394)
    source_times=[]
    try:
        fx,_,_,fx_ts=chart('KRW=X'); source_times.append(fx_ts)
    except Exception: pass
    items=[]
    for symbol,m in META.items():
        ident,group,name,code,unit,krw_label,color=m; stale=False
        try:
            price,ch,hist,source_ts=chart(symbol); source_times.append(source_ts)
        except Exception:
            stale=True; o=old.get(symbol,{})
            price=float(o.get('price',0)); ch=float(o.get('change_pct',0)); hist=o.get('history',[])[-7:]
            source_ts=int(o.get('source_timestamp') or 0)
        items.append({'id':ident,'group':group,'name':name,'code':code,'symbol':symbol,'price':round(price,4),'change_pct':round(ch,4),'unit':unit,'krw_label':krw_label,'krw_value':round(krw(symbol,price,fx),2),'color':color,'history':[round(v,4) for v in hist[-7:]],'source_timestamp':source_ts,'stale':stale})
    source_updated_at=datetime.fromtimestamp(max(source_times),tz=timezone.utc).isoformat() if source_times else prev.get('source_updated_at') or prev.get('updated_at')
    DATA.write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'source_updated_at':source_updated_at,'fx':round(fx,4),'items':items},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__': main()
