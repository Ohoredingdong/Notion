"""Bounded rotating *research-only* price-direction coverage.

Runs separately from the immutable primary forecast ledger and its audits.
Never rewrites core forecasts or promotes any signal to an investment approval.
Only provider-observed OHLC and prospective targets can become predictions.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

UTC = timezone.utc
VERSION = "stock-extended-direction-v1"
OUTPUT = Path("stock-extended-direction-forecast.json")
QUARANTINE_OUTPUT = Path("data-quarantine/stock-extended-direction-forecast.json")
SOURCE_IDENTITY_POLICY = "kr-six-character-alphanumeric-v2"
MAX_BATCH = 16


def read_json(path, default):
    file = Path(path)
    return json.loads(file.read_text(encoding="utf-8")) if file.is_file() else default


def ticker(country, exchange, symbol):
    symbol = str(symbol).strip().upper()
    if country == "US":
        # Valid Yahoo-style plain stock tickers; reject complex preferred/rights symbols.
        return symbol if re.fullmatch(r"[A-Z]{1,5}", symbol) else None
    if country == "KR" and re.fullmatch(r"[0-9A-Z]{6}", symbol):
        if exchange == "KOSPI":
            return symbol + ".KS"
        if exchange == "KOSDAQ":
            return symbol + ".KQ"
    return None


def compile_targets(summary, directory):
    if directory.get("identifier_policy") != SOURCE_IDENTITY_POLICY:
        raise RuntimeError("extended_research_requires_verified_catalogue_identifiers")
    if directory.get("status") != "complete" or directory.get("counts",{}).get("total") != len(directory.get("items",[])):
        raise RuntimeError("extended_research_requires_complete_official_catalogue")
    if any(row.get("country") == "KR" and row.get("source_symbol") != row.get("symbol")
           for row in directory.get("items",[])):
        raise RuntimeError("extended_research_catalogue_source_symbol_mismatch")
    tracked, broad = [], []
    for row in summary.get("states", []):
        sym = str(row.get("symbol") or "").strip().upper()
        # Neither the market nor company identity may be inferred from digit-only
        # rules or an older summary. Exact current official identity is required.
        matches = [item for item in directory.get("items", []) if item.get("symbol") == sym]
        if len(matches) != 1:
            continue
        match = matches[0]
        country, exchange = match.get("country"), match.get("exchange")
        normalized = ticker(country, exchange, match["symbol"])
        if not normalized:
            continue
        tracked.append((normalized, str(match["name"]), country))
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


def current_identities(catalog):
    identities = {}
    for item in catalog["items"]:
        normalized = ticker(item["country"],item["exchange"],item["symbol"])
        if normalized:
            identity = {"symbol":normalized,"market":item["country"],
                        "catalog_symbol":item["symbol"],"catalog_name":item["name"],
                        "catalog_exchange":item["exchange"]}
            if normalized in identities and identities[normalized] != identity:
                raise ValueError("conflicting_extended_provider_identity")
            identities[normalized] = identity
    return identities


def valid_research_result(record):
    if record.get("status") == "no_call":
        return record.get("probabilities") is None and record.get("target") is None
    if record.get("status") != "research_prediction":
        return False
    probabilities = record.get("probabilities") or {}
    if set(probabilities) != {"up","flat","down"} or any(
            isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1
            for value in probabilities.values()) or abs(sum(probabilities.values())-1)>0.001:
        return False
    try:
        issued=datetime.fromisoformat(record["issued_at"])
        start=datetime.fromisoformat(record["target"]["start"])
        end=datetime.fromisoformat(record["target"]["end"])
        return bool(issued.tzinfo and start.tzinfo and end.tzinfo and issued<start<end and
                    issued<=datetime.now(UTC))
    except (KeyError,TypeError,ValueError):
        return False


def retain_verified_cache(previous, identities, generated):
    retained, quarantine = {}, []
    for record in previous.get("records",[]):
        if not isinstance(record,dict):
            quarantine.append({"reason":"malformed_extended_record","record":record})
            continue
        identity = identities.get(record.get("symbol"))
        valid = (previous.get("source_identity_policy") == SOURCE_IDENTITY_POLICY and identity and
                 record.get("source_identity_policy") == SOURCE_IDENTITY_POLICY and
                 record.get("identity_verified") is True and
                 valid_research_result(record) and
                 all(record.get(key)==value for key,value in identity.items()) and
                 record.get("name") == identity["catalog_name"])
        if valid:
            retained[record["symbol"]] = record
        else:
            quarantine.append({"reason":"unverified_or_changed_catalogue_identity","record":record})
    for item in quarantine:
        item["quarantined_at"] = generated
        item["source_generated_at"] = previous.get("generated_at")
        item["sha256"] = hashlib.sha256(json.dumps(item["record"],ensure_ascii=False,sort_keys=True,
                                                  separators=(",",":")).encode()).hexdigest()
    return retained, quarantine


def preserve_quarantine(root, quarantined, generated):
    archive = read_json(root/QUARANTINE_OUTPUT,{"version":"extended-issuer-identity-quarantine-v1",
                        "not_for_display_or_analysis":True,"records":[]})
    known = {x["sha256"] for x in archive["records"]}
    additions = [x for x in quarantined if x["sha256"] not in known]
    if additions:
        archive["records"].extend(additions)
        archive["updated_at"] = generated
        path=root/QUARANTINE_OUTPUT
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(archive,ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n",
                             encoding="utf-8")
        temporary.replace(path)
    return len(archive["records"])


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
    if not 1 <= batch_size <= MAX_BATCH:
        raise ValueError("research_batch_out_of_bounds")
    root=Path(root)
    summary=read_json(root/"stock-opportunity-summary.json",{})
    catalog=read_json(root/"stock-universe-catalog.json",{})
    previous=read_json(root/OUTPUT,{})
    tracked, directory=compile_targets(summary,catalog)
    trusted_cursor=previous if previous.get("source_identity_policy") == SOURCE_IDENTITY_POLICY else {}
    selected,cursor=choose_batch(tracked,directory,trusted_cursor,batch_size)
    if collector is None:
        from stock_forecast_sources import history as collector_history
        collector=lambda symbol:collector_history(symbol,"daily")
    predict=predictor or predict_one
    generated=datetime.now(UTC).isoformat()
    identities=current_identities(catalog)
    previous_results,quarantined=retain_verified_cache(previous,identities,generated)
    outcomes=[]
    retained_after_failure=0
    # Serialized requests avoid public provider rate-limit bursts and shared sqlite cache locks.
    for spec in selected:
        result=predict(spec,collector)
        if (result.get("symbol")!=spec[0] or result.get("market")!=spec[2] or
                result.get("status") not in ("no_call","research_prediction")):
            raise ValueError("invalid_predictor_response")
        if not valid_research_result(result):
            raise ValueError("invalid_probability_or_prospective_target")
        result.update(identities[spec[0]])
        result.update({"source_identity_policy":SOURCE_IDENTITY_POLICY,"identity_verified":True,
                       "name":spec[1],"recommendation":False,"live_validated":False,
                       "model_scope":"extended_research_only"})
        # Count the current attempt before retaining an earlier valid forecast.
        outcomes.append(dict(result))
        old=previous_results.get(spec[0])
        if (result["status"]=="no_call" and old and old.get("status")=="research_prediction"):
            # Keep only a GENUINE, previously issued forecast whose target is
            # still in the future; a transient data failure cannot erase it.
            end=(old.get("target") or {}).get("end")
            try:
                ending=datetime.fromisoformat(end) if end else None
            except (TypeError, ValueError):
                ending=None
            if ending and ending.tzinfo and ending>datetime.now(UTC):
                result={**old,"latest_attempt":{"status":"no_call",
                        "checked_at":generated,"reason":result.get("reason")}}
                retained_after_failure+=1
        previous_results[spec[0]]=result
    quarantine_count=preserve_quarantine(root,quarantined,generated)
    output={"version":VERSION,"source_identity_policy":SOURCE_IDENTITY_POLICY,
            "generated_at":generated,"status":"research_only_partial_coverage",
            "real_time_connected":False,"automatic_orders":False,
            "scope_note":"기간 유효/실제 시세가 있는 종목에 한정된 미검증 방향 연구. 전체 상장종목에 대한 당일 확률 아님.",
            "source_summary_generated_at":summary.get("generated_at"),
            "source_catalog_generated_at":catalog.get("generated_at"),
            "universe":{"tracked":len(tracked),"directory":len(directory),
                        "attempted_total":len(previous_results)},
            "run":{"attempted":len(outcomes),
                   "research_prediction":sum(x["status"]=="research_prediction" for x in outcomes),
                   "no_call":sum(x["status"]=="no_call" for x in outcomes),
                   "retained_unexpired_after_no_call":retained_after_failure},
            "quarantined_records":quarantine_count,"quarantine_file":str(QUARANTINE_OUTPUT),
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
