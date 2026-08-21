from __future__ import annotations
import json, xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

OUT=Path("exchange-rates-data.json")
URL="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
SOURCE="https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html"
KST=ZoneInfo("Asia/Seoul")
UA={"User-Agent":"Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36"}
NEEDED=("USD","JPY","CNY","KRW")

def fetch_days():
    r=requests.get(URL,headers=UA,timeout=30);r.raise_for_status()
    root=ET.fromstring(r.content)
    days=[]
    for el in root.iter():
        date=el.attrib.get("time")
        if not date: continue
        rates={}
        for c in list(el):
            code=c.attrib.get("currency"); rate=c.attrib.get("rate")
            if code and rate:
                try: rates[code]=float(rate)
                except: pass
        if all(k in rates for k in NEEDED):
            days.append((date,rates))
    days.sort(key=lambda x:x[0])
    if len(days)<2: raise RuntimeError("ECB history did not contain enough complete days")
    return days

def krw_prices(r):
    return {"USD":r["KRW"]/r["USD"],"JPY":r["KRW"]/r["JPY"]*100,"EUR":r["KRW"],"CNY":r["KRW"]/r["CNY"]}

def row(code,name,cur,prev):
    v,p=cur[code],prev[code]; diff=v-p
    return {"code":code,"name":name,"price_krw":round(v,2),"previous_krw":round(p,2),"change":round(diff,2),"change_pct":round(diff/p*100,2)}

def main():
    now=datetime.now(KST)
    try:
        days=fetch_days(); latest_date,latest=days[-1]; _,previous=days[-2]
        cur,prev=krw_prices(latest),krw_prices(previous)
        history=[{"date":d,"value":round(krw_prices(r)["USD"],2)} for d,r in days[-7:]]
        diff=cur["USD"]-prev["USD"]
        data={
            "generated_at":now.isoformat(),"reference_date":latest_date,"source":"European Central Bank reference rates","source_url":SOURCE,"stale":False,
            "rows":[row("USD","US Dollar",cur,prev),row("JPY","Japanese Yen (100)",cur,prev),row("EUR","Euro",cur,prev),row("CNY","Chinese Yuan",cur,prev)],
            "usdkrw":{"price":round(cur["USD"],2),"previous":round(prev["USD"],2),"change":round(diff,2),"change_pct":round(diff/prev["USD"]*100,2),"history":history},
            "note":"ECB daily reference rates; informational, not transaction quotes."
        }
        OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception as exc:
        if OUT.exists():
            old=json.loads(OUT.read_text(encoding="utf-8"));old["stale"]=True;old["last_error"]=str(exc);old["last_attempt_at"]=now.isoformat();OUT.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding="utf-8")
        else: raise

if __name__=="__main__": main()
