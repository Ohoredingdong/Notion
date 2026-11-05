"""Bounded rotating *research-only* price-direction coverage.

Runs separately from the immutable primary forecast ledger and its audits.
Never rewrites core forecasts or promotes any signal to an investment approval.
Only provider-observed OHLC and prospective targets can become predictions.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

UTC = timezone.utc
VERSION = "stock-extended-direction-v1"
OUTPUT = Path("stock-extended-direction-forecast.json")
MAX_BATCH = 16


def read_json(path, default):
    file = Path(path)
    return json.loads(file.read_text(encoding="utf-8")) if file.is_file() else default


def ticker(country, exchange, symbol):
    symbol = str(symbol).strip().upper()
    if country == "US":
        # Valid Yahoo-style plain stock tickers; reject complex preferred/rights symbols.
        return symbol if re.fullmatch(r"[A-Z]{1,5}", symbol) else None
    if country == "KR" and re.fullmatch(r"\d{6}", symbol):
        return symbol + (".KQ" if exchange == "KOSDAQ" else ".KS" if exchange == "KOSPI" else "")
    return None


def compile_targets(summary, directory):
    tracked, broad = [], []
    for row in summary.get("states", []):
        sym = str(row.get("symbol") or "").strip()
        country = "KR" if re.fullmatch(r"\d{6}", sym) else "US"
        # Mapping from verified market directory takes precedence; guessing is disallowed.
        match = next((item for item in directory.get("items", [])
                     if item.get("symbol") == sym and item.get("country") == country), None)
        exchange = match.get("exchange") if match else ("UNKNOWN" if country == "KR" else "US")
        normalized = ticker(country, exchange, sym)
        if not normalized:
            continue
        tracked.append((normalized, str(row.get("name") or sym), country))
    for item in directory.get("items", []):
        if item.get("country") not in ("KR", "US"):
            continue
        sym = ticker(item["country"],item["exchange"],item["symbol"])
        if sym:
            broad.append((sym, str(item["name"]),item["country"]))
    def stable(rows):
        found = {}
        for item in rows:
            found.setdefault(item[0], item)
        return list(found.values())
    tracked = stable(tracked)
    broad = stable(broad)
    return tracked, broad


def choose_batch(tracked, directory, prior, batch_size=MAX_BATCH):
    if not 1 <= batch_size <= MAX_BATCH:
        raise ValueError("research_batch_out_of_bounds")
    if not tracked and not directory:
        raise RuntimeError("missing_real_listed_symbols")
    cursor = prior.get("cursor") or {}
    t_index = int(cursor.get("tracked", 0))
    d_index = int(cursor.get("directory", 0))
    t_count = min(len(tracked), batch_size//2+batch_size%2)
    result = []
    for k in range(t_count):
        result.append(tracked[(t_index+k) % len(tracked)])
    remainder = batch_size-len(result)
    for k in range(min(len(directory), remainder+len(result))):
        if len(result)>=batch_size:
            break
        item=directory[(d_index+k)%len(directory)]
        if item[0] not in {r[0] for r in result}:
            result.append(item)
    if not directory and len(result)<batch_size and tracked:
        for k in range(t_count, min(t_count+batch_size,len(tracked))):
            item=tracked[(t_index+k)%len(tracked)]
            if item[0] not in {r[0] for r in result}:
                result.append(item)
            if len(result)>=batch_size:break
    return result, {"tracked":(t_index+t_count)%len(tracked) if tracked else 0,
                    "directory":(d_index+remainder)%len(directory) if directory else 0}


def predict_one(spec, collector):
    symbol,name,country=spec
    now=datetime.now(UTC)
    try:
        history=collector(symbol)
        if history is None or history.empty:
            raise ValueError("provider_returned_no_candles")
        from stock_forecast_model import normalise_history,fit_model,make_prediction
        bars=normalise_history(history,country,"daily",now)
        fitted=fit_model(bars,"daily")
        result=make_prediction(bars,fitted,symbol,country,"daily",now)
        result["model_scope"]="extended_research_only"
        result["recommendation"]=False
        result["live_validated"]=False
        result["source_url"]="https://finance.yahoo.com/quote/"+symbol
        result["name"]=name
        if result.get("status")=="research_prediction":
            issued=datetime.fromisoformat(result["issued_at"])
            start=datetime.fromisoformat(result["target"]["start"])
            end=datetime.fromisoformat(result["target"]["end"])
            if not (issued<start<end):
                raise ValueError("prospective_target_not_future")
        return result
    except Exception as exc:
        # Never substitute a prediction for missing history/model input.
        return {"symbol":symbol,"name":name,"market":country,"mode":"daily",
                "status":"no_call","issued_at":now.isoformat(),"target":None,
                "probabilities":None,"recommendation":False,
                "reason":type(exc).__name__+": "+str(exc)[:160],
                "model_scope":"extended_research_only"}


def run(root=Path("."), *, collector=None, batch_size=MAX_BATCH, predictor=None):
    root=Path(root)
    summary=read_json(root/"stock-opportunity-summary.json",{})
    catalog=read_json(root/"stock-universe-catalog.json",{})
    previous=read_json(root/OUTPUT,{})
    tracked, directory=compile_targets(summary,catalog)
    selected,cursor=choose_batch(tracked,directory,previous,batch_size)
    if collector is None:
        from stock_forecast_sources import history as collector_history
        collector=lambda symbol:collector_history(symbol,"daily")
    predict=predictor or predict_one
    generated=datetime.now(UTC).isoformat()
    previous_results={x["symbol"]:x for x in previous.get("records",[]) if isinstance(x,dict) and x.get("symbol")}
    outcomes=[]
    # Serialized requests avoid public provider rate-limit bursts and shared sqlite cache locks.
    for spec in selected:
        result=predict(spec,collector)
        if result.get("symbol")!=spec[0] or result.get("status") not in ("no_call","research_prediction"):
            raise ValueError("invalid_predictor_response")
        previous_results[spec[0]]=result
        outcomes.append(result)
    output={"version":VERSION,"generated_at":generated,"status":"research_only_partial_coverage",
            "real_time_connected":False,"automatic_orders":False,
            "scope_note":"기간 유효/실제 시세가 있는 종목에 한정된 미검증 방향 연구. 전체 상장종목에 대한 당일 확률 아님.",
            "source_summary_generated_at":summary.get("generated_at"),
            "source_catalog_generated_at":catalog.get("generated_at"),
            "universe":{"tracked":len(tracked),"directory":len(directory),
                        "attempted_total":len(previous_results)},
            "run":{"attempted":len(outcomes),
                   "research_prediction":sum(x["status"]=="research_prediction" for x in outcomes),
                   "no_call":sum(x["status"]=="no_call" for x in outcomes)},
            "cursor":cursor,"records":list(previous_results.values())}
    target=root/OUTPUT
    temp=target.with_suffix(".json.tmp")
    temp.write_text(json.dumps(output,ensure_ascii=False,allow_nan=False,
                               separators=(",",":"))+"\n",encoding="utf-8")
    temp.replace(target)
    print("EXTENDED_RESEARCH_BATCH",output["run"],output["universe"],"not_livetrading")
    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--batch-size",type=int,default=MAX_BATCH)
    args=ap.parse_args()
    run(batch_size=args.batch_size)


if __name__=="__main__":
    main()
