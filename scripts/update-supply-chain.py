from __future__ import annotations
import json,re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

OUT=Path("supply-chain-data.json")
KST=ZoneInfo("Asia/Seoul")
UA={"User-Agent":"Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36"}
NYFED="https://www.newyorkfed.org/research/policy/gscpi"
TE="https://tradingeconomics.com/world/supply-chain-pressure-index"
ISM="https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/pmi/"
DREWRY="https://www.drewry.co.uk/trackers-and-indices/latest-trackers-and-indices/world-container-index-assessed-by-drewry"

def get(url):
    r=requests.get(url,headers=UA,timeout=30);r.raise_for_status()
    return BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True)

def existing():
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}

def parse_gscpi(text,old):
    m=re.search(r"(?:decreased|increased|fell|rose) to\s+(-?\d+(?:\.\d+)?)\s+points?\s+in\s+([A-Za-z]+).*?from\s+(?:a\s+downwardly\s+revised\s+)?(-?\d+(?:\.\d+)?)",text,re.I|re.S)
    if not m: raise ValueError("GSCPI parse failed")
    val=float(m.group(1));prev=float(m.group(3))
    hist=(old.get("gscpi") or {}).get("history",[])
    if not hist:
        hist=[{"label":"02","value":0.58},{"label":"03","value":0.68},{"label":"04","value":1.84},{"label":"05","value":1.81},{"label":"06","value":1.19},{"label":"07","value":0.79}]
    if abs(hist[-1]["value"]-val)>1e-9:
        hist.append({"label":datetime.now(KST).strftime("%m"),"value":val})
    return {"value":val,"previous":prev,"reference_month":datetime.now(KST).strftime("%Y-%m"),"history":hist[-6:],"primary_source":"Federal Reserve Bank of New York","numeric_mirror":"Trading Economics"}

def parse_ism(text):
    md=re.search(r"Supplier Deliveries Index.*?registered\s+([0-9.]+)\s+percent.*?(?:from|compared to)\s+(?:the\s+)?([0-9.]+)\s+percent",text,re.I|re.S)
    mp=re.search(r"Prices Index.*?registered\s+([0-9.]+)\s+percent.*?(?:from|compared to).*?([0-9.]+)\s+percent",text,re.I|re.S)
    if not md or not mp: raise ValueError("ISM parse failed")
    sd,sdprev=float(md.group(1)),float(md.group(2));pr,prprev=float(mp.group(1)),float(mp.group(2))
    return {"supplier_deliveries":{"value":sd,"previous":sdprev,"change":round(sd-sdprev,1),"reference_month":"latest"},"ism_prices":{"value":pr,"previous":prprev,"change":round(pr-prprev,1),"reference_month":"latest"}}

def parse_wci(text):
    m=re.search(r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}).*?World Container Index.*?(increased|decreased)\s+([0-9.]+)%\s+to\s+\$([0-9,]+)\s+per\s+40ft",text,re.I|re.S)
    if not m: raise ValueError("WCI parse failed")
    pct=float(m.group(3))*(1 if m.group(2).lower()=="increased" else -1)
    return {"value":int(m.group(4).replace(",","")),"change_pct":pct,"reference_date":m.group(1)}

def main():
    now=datetime.now(KST);old=existing();data=dict(old);errors=[]
    try:data["gscpi"]=parse_gscpi(get(TE),old)
    except Exception as e:errors.append(str(e))
    try:data.update(parse_ism(get(ISM)))
    except Exception as e:errors.append(str(e))
    try:data["wci"]=parse_wci(get(DREWRY))
    except Exception as e:errors.append(str(e))
    data["generated_at"]=now.isoformat();data["data_as_of"]=now.date().isoformat()
    data["sources"]={"nyfed":NYFED,"ism":ISM,"drewry":DREWRY,"gscpi_numeric_mirror":TE}
    data["stale"]=bool(errors)
    if errors:data["last_errors"]=errors
    else:data.pop("last_errors",None)
    OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":main()
