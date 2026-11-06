"""Checkpointed whole-directory daily research; no invented bars or probabilities.

Manifest and aggregation use the standard library only. A shard lazily imports
the existing model and yfinance. Provider I/O is serial inside each shard; a
bounded rate-limit retry opens a circuit instead of requesting more companies.
Only OHLC observations are cached. Previously issued predictions are never
counted as a new result of this run.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import date, datetime, time as day_time, timedelta, timezone
import gzip
from functools import lru_cache
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import time
from zoneinfo import ZoneInfo

UTC = timezone.utc
IDENTITY_POLICY = "kr-six-character-alphanumeric-v2"
VERSION = "stock-extended-direction-v1"
MANIFEST_VERSION = "stock-universe-forecast-manifest-v1"
SHARD_VERSION = "stock-universe-forecast-shard-v1"
CACHE_VERSION = "verified-yahoo-daily-history-v1"
POLICY = "whole-universe-daily-research-v1"
NOT_ATTEMPTED = {"circuit_skipped", "deadline_skipped"}
COLLECTION_STATUSES = NOT_ATTEMPTED | {"fetched", "cache_current", "source_error", "unsupported"}
IDENTITY_FIELDS = ("key", "symbol", "market", "name", "catalog_symbol", "catalog_name",
                   "catalog_exchange", "provider_symbol")
MODEL_FILES = ("run_stock_universe_forecasts.py", "stock_forecast_model.py", "stock_forecast_sources.py",
               "audit_stock_forecast_independent.py")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def now_utc():
    return datetime.now(UTC)


def instant(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone_required")
    return result.astimezone(UTC)


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def code_hashes():
    root = Path(__file__).resolve().parent
    return {name: sha256((root / name).read_bytes()) for name in MODEL_FILES}


def load_catalog(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if (data.get("version") != "radar-universe-catalog-v1" or
            data.get("identifier_policy") != IDENTITY_POLICY or data.get("status") != "complete"):
        raise ValueError("complete_verified_catalogue_required")
    items = data.get("items")
    if not isinstance(items, list) or not items or data.get("counts", {}).get("total") != len(items):
        raise ValueError("catalogue_count_mismatch")
    instant(data["generated_at"])
    seen = set()
    for item in items:
        if (item.get("country") not in ("KR", "US") or
                any(not isinstance(item.get(key), str) or not item[key].strip()
                    for key in ("symbol", "name", "exchange")) or
                item["symbol"] != item["symbol"].strip().upper()):
            raise ValueError("invalid_catalogue_identity")
        key = item["country"] + ":" + item["symbol"]
        if key in seen:
            raise ValueError("duplicate_catalogue_identity")
        seen.add(key)
        if item["country"] == "KR" and (not re.fullmatch(r"[0-9A-Z]{6}", item["symbol"]) or
                                           item.get("source_symbol") != item["symbol"]):
            raise ValueError("unverified_korean_catalogue_symbol")
    countries = Counter(item["country"] for item in items)
    if any(data["counts"].get(country) != countries[country] for country in ("KR", "US")):
        raise ValueError("catalogue_country_count_mismatch")
    return data, sha256(raw)


def provider_symbol(item):
    symbol, country, exchange = item["symbol"], item["country"], item["exchange"]
    if country == "KR":
        suffix = {"KOSPI": ".KS", "KOSDAQ": ".KQ"}.get(exchange)
        return symbol + suffix if suffix and re.fullmatch(r"[0-9A-Z]{6}", symbol) else None
    if re.fullmatch(r"[A-Z]{1,5}", symbol):
        return symbol
    # A share class is an explicit provider alias, never a rewritten catalogue ID.
    if re.fullmatch(r"[A-Z]{1,5}[.-][A-Z]", symbol):
        return symbol.replace(".", "-")
    return None


def targets_for_catalog(catalog, shard_count):
    targets, providers = [], {}
    for item in sorted(catalog["items"], key=lambda row: (row["country"], row["symbol"])):
        provider = provider_symbol(item)
        target = {"key": item["country"] + ":" + item["symbol"],
                  "market": item["country"], "catalog_symbol": item["symbol"],
                  "catalog_name": item["name"], "catalog_exchange": item["exchange"],
                  "name": item["name"], "symbol": provider or item["symbol"],
                  "provider_symbol": provider, "supported": provider is not None,
                  "unsupported_reason": None if provider else "unsupported_symbol"}
        targets.append(target)
        if provider:
            providers.setdefault(provider, []).append(target)
    for group in providers.values():
        if len(group) > 1:
            for target in group:
                target.update(supported=False, unsupported_reason="provider_collision",
                              provider_symbol=None, symbol=target["catalog_symbol"])
    for index, target in enumerate(targets):
        target["shard_index"] = index % shard_count
    return targets


def create_manifest(catalog_path, *, shards=32, run_id, source_commit, run_attempt="1", clock=now_utc):
    if not isinstance(shards, int) or not 1 <= shards <= 128:
        raise ValueError("invalid_shard_count")
    if not str(run_id).strip() or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("run_and_exact_source_commit_required")
    catalog, catalog_hash = load_catalog(catalog_path)
    manifest = {"version": MANIFEST_VERSION, "source_identity_policy": IDENTITY_POLICY,
                "policy": POLICY, "created_at": clock().isoformat(), "run_id": str(run_id),
                "run_attempt": str(run_attempt), "source_commit": source_commit,
                "implementation_sha256": code_hashes(), "shard_count": shards,
                "catalog_sha256": catalog_hash, "catalog_generated_at": catalog["generated_at"],
                "catalog_counts": catalog["counts"], "targets": targets_for_catalog(catalog, shards)}
    manifest["manifest_sha256"] = sha256(canonical(manifest))
    return manifest


def validate_manifest(manifest, *, verify_code=True):
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if (manifest.get("version") != MANIFEST_VERSION or
            manifest.get("source_identity_policy") != IDENTITY_POLICY or
            manifest.get("manifest_sha256") != sha256(canonical(unsigned))):
        raise ValueError("invalid_manifest_hash_or_policy")
    if verify_code and manifest.get("implementation_sha256") != code_hashes():
        raise ValueError("manifest_code_changed")
    count = manifest.get("shard_count")
    if not isinstance(count, int) or not 1 <= count <= 128:
        raise ValueError("invalid_manifest_shard_count")
    targets = manifest.get("targets", [])
    if len(targets) != manifest.get("catalog_counts", {}).get("total"):
        raise ValueError("invalid_manifest_target_count")
    keys = [target.get("key") for target in targets]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate_manifest_identity")
    for index, target in enumerate(targets):
        if (target.get("shard_index") != index % count or
                target.get("key") != target.get("market", "") + ":" + target.get("catalog_symbol", "")):
            raise ValueError("invalid_manifest_partition")
    instant(manifest["created_at"])
    return manifest


def model_module():
    try:
        return importlib.import_module("stock_forecast_model")
    except ModuleNotFoundError as exc:
        if exc.name != "stock_forecast_model":
            raise
        return importlib.import_module("scripts.stock_forecast_model")


def sources_module():
    try:
        return importlib.import_module("stock_forecast_sources")
    except ModuleNotFoundError as exc:
        if exc.name != "stock_forecast_sources":
            raise
        return importlib.import_module("scripts.stock_forecast_sources")


@lru_cache(maxsize=1)
def audit_module():
    try:
        return importlib.import_module("audit_stock_forecast_independent")
    except ModuleNotFoundError as exc:
        if exc.name != "audit_stock_forecast_independent":
            raise
        return importlib.import_module("scripts.audit_stock_forecast_independent")


@lru_cache(maxsize=1)
def model_contract():
    # Read only literal contract constants from the source already bound by the
    # manifest. Aggregation must not import pandas/sklearn or train a model.
    source = Path(__file__).resolve().with_name("stock_forecast_model.py").read_text(encoding="utf-8")
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("VERSION", "POLICY", "FEATURES"):
                    values[target.id] = ast.literal_eval(node.value)
    if set(values) != {"VERSION", "POLICY", "FEATURES"}:
        raise ValueError("literal_model_contract_missing")
    return values


class YahooCollector:
    def __call__(self, target, start=None):
        import yfinance as yf
        sources = sources_module()
        sources.prepare_sessions()
        instrument = yf.Ticker(target["provider_symbol"])
        args = {"interval": "1d", "auto_adjust": False, "actions": True,
                "prepost": False, "timeout": 18, "raise_errors": True}
        args.update({"start": start} if start else {"period": "5y"})
        def fetch():
            frame = instrument.history(**args)
            # In pinned yfinance 0.2.66 the public metadata accessor can issue an
            # extra 5d/1h request when tradingPeriods is absent. Read only the
            # metadata already received with THIS history response.
            reader = getattr(instrument, "_price_history", None)
            metadata = dict(getattr(reader, "_history_metadata", None) or {})
            return frame, metadata
        return sources.read_history_serially(fetch)


class CollectionStopped(Exception):
    def __init__(self, kind, detail=""):
        self.kind, self.detail = kind, detail
        super().__init__(kind + (": " + detail if detail else ""))


class SourceIdentityError(ValueError):
    def __init__(self, reason, metadata):
        self.metadata = {key: metadata.get(key) for key in
                         ("symbol", "exchangeName", "exchangeTimezoneName", "instrumentType")}
        super().__init__(reason)


def safe_error(exc):
    text = re.sub(r"https?://\S+", "[provider-url]", str(exc))
    return (type(exc).__name__ + ": " + text.replace("\n", " "))[:180]


def is_rate_limit(exc):
    return ("ratelimit" in type(exc).__name__.lower() or
            bool(re.search(r"\b429\b|too many requests|rate.?limit", str(exc), re.I)))


def is_transport_error(exc):
    return isinstance(exc, (TimeoutError, ConnectionError)) or bool(re.search(
        r"timeout|timed out|connection|could not resolve|DNS|\b(?:401|403|500|502|503|504)\b",
        type(exc).__name__ + " " + str(exc), re.I))


class RequestBudget:
    def __init__(self, *, max_seconds, request_delay, retries, backoff, clock, monotonic, sleeper):
        self.clock, self.monotonic, self.sleep = clock, monotonic, sleeper
        self.deadline = monotonic() + max_seconds
        self.delay, self.retries, self.backoff = request_delay, retries, backoff
        self.last_request_end = None
        self.source_fetch_attempts = self.rate_limit_events = self.transport_failures = 0
        self.transport_streak = 0
        self.circuit_reason = None

    def stopped(self):
        if self.monotonic() >= self.deadline:
            return "deadline_skipped"
        return "circuit_skipped" if self.circuit_reason else None

    def pause(self, seconds):
        if self.monotonic() + seconds >= self.deadline:
            raise CollectionStopped("deadline")
        if seconds > 0:
            self.sleep(seconds)

    def fetch(self, collector, target, start):
        for attempt in range(self.retries + 1):
            if self.stopped():
                raise CollectionStopped("deadline" if self.stopped() == "deadline_skipped" else "provider_circuit_open")
            if self.last_request_end is not None:
                self.pause(max(0, self.delay - (self.monotonic() - self.last_request_end)))
            self.source_fetch_attempts += 1
            try:
                observation = collector(target, start)
                completed = self.clock()
                self.last_request_end = self.monotonic()
                self.transport_streak = 0
                return observation, completed
            except CollectionStopped:
                raise
            except Exception as exc:
                self.last_request_end = self.monotonic()
                if is_rate_limit(exc):
                    self.rate_limit_events += 1
                    wait = min(120.0, self.backoff * (2 ** attempt))
                    response = getattr(exc, "response", None)
                    retry_after = (getattr(response, "headers", {}) or {}).get("Retry-After")
                    try:
                        if retry_after is not None:
                            wait = max(wait, float(retry_after))
                    except (TypeError, ValueError):
                        pass
                    if attempt < self.retries and self.monotonic() + wait < self.deadline:
                        self.pause(wait)
                        continue
                    self.circuit_reason = "rate_limited"
                    raise CollectionStopped("rate_limited", safe_error(exc)) from exc
                if is_transport_error(exc):
                    self.transport_failures += 1
                    self.transport_streak += 1
                    if self.transport_streak >= 3:
                        self.circuit_reason = "source_transport_failures"
                raise CollectionStopped("source_error", safe_error(exc)) from exc
        raise AssertionError("unreachable_request_loop")


def cache_identity(target):
    return {key: target[key] for key in ("key", "market", "catalog_symbol", "catalog_name",
                                        "catalog_exchange", "provider_symbol")}


def cache_path(root, target):
    return Path(root) / (sha256(canonical(cache_identity(target))) + ".json.gz")


def validate_provider(target, metadata):
    if not isinstance(metadata, dict) or not metadata.get("symbol"):
        raise SourceIdentityError("provider_identity_metadata_missing", metadata or {})
    if metadata.get("symbol") != target["provider_symbol"]:
        raise SourceIdentityError("provider_symbol_mismatch", metadata)
    if metadata.get("instrumentType") != "EQUITY":
        raise SourceIdentityError("provider_instrument_type_mismatch", metadata)
    zone = metadata.get("exchangeTimezoneName")
    expected = "Asia/Seoul" if target["market"] == "KR" else "America/New_York"
    if zone != expected:
        raise SourceIdentityError("provider_market_timezone_mismatch", metadata)
    exchange = str(metadata.get("exchangeName", "")).upper()
    allowed = {"KOSPI": {"KSC", "KOSPI"}, "KOSDAQ": {"KOE", "KOSDAQ"},
               "NASDAQ": {"NMS", "NGM", "NCM", "NAS", "NASDAQ", "NASDAQGS", "NASDAQGM", "NASDAQCM"},
               "NYSE": {"NYQ", "NYSE"}, "NYSE AMERICAN": {"ASE", "AMEX", "NYSEAMERICAN"},
               "NYSE ARCA": {"PCX", "NYSEARCA"}, "CBOE": {"BTS", "BATS", "CBOE"}}
    if exchange not in allowed.get(target["catalog_exchange"], set()):
        raise SourceIdentityError("provider_exchange_mismatch", metadata)


def frame_rows(frame, market):
    import pandas as pd
    if frame is None or frame.empty:
        raise ValueError("provider_returned_no_candles")
    zone = "Asia/Seoul" if market == "KR" else "America/New_York"
    rows, seen = [], set()
    for index, source in frame.iterrows():
        stamp = pd.Timestamp(index)
        day = (stamp.tz_convert(zone) if stamp.tzinfo else stamp).date().isoformat()
        if day in seen:
            raise ValueError("duplicate_provider_daily_bar")
        seen.add(day)
        values = {key: float(source[column]) for key, column in
                  (("open", "Open"), ("high", "High"), ("low", "Low"), ("close", "Close"))}
        if not all(finite(value) and value > 0 for value in values.values()):
            continue
        if values["high"] < max(values["open"], values["close"]) or values["low"] > min(values["open"], values["close"]):
            raise ValueError("invalid_provider_ohlc_order")
        row = {"date": day, **values}
        for key, column in (("volume", "Volume"), ("splits", "Stock Splits")):
            value = source.get(column)
            row[key] = float(value) if finite(value) else None
        rows.append(row)
    if not rows:
        raise ValueError("provider_returned_no_valid_candles")
    return sorted(rows, key=lambda row: row["date"])


def rows_frame(rows, market):
    import pandas as pd
    zone = ZoneInfo("Asia/Seoul" if market == "KR" else "America/New_York")
    index = pd.DatetimeIndex([datetime.combine(date.fromisoformat(row["date"]), day_time(), zone) for row in rows])
    return pd.DataFrame({column: [row[key] for row in rows] for key, column in
                         (("open", "Open"), ("high", "High"), ("low", "Low"), ("close", "Close"),
                          ("volume", "Volume"), ("splits", "Stock Splits"))}, index=index)


def validate_rows(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty_cache_rows")
    dates = []
    for row in rows:
        dates.append(date.fromisoformat(row["date"]))
        if any(not finite(row.get(key)) or row[key] <= 0 for key in ("open", "high", "low", "close")):
            raise ValueError("invalid_cache_price")
        if row["high"] < max(row["open"], row["close"]) or row["low"] > min(row["open"], row["close"]):
            raise ValueError("invalid_cache_ohlc_order")
    if dates != sorted(set(dates)):
        raise ValueError("unordered_or_duplicate_cache_rows")


def load_cache(root, target, current):
    path = cache_path(root, target)
    if not path.is_file():
        return None
    try:
        value = json.loads(gzip.decompress(path.read_bytes()))
        if (value.get("version") != CACHE_VERSION or value.get("identity") != cache_identity(target) or
                value.get("history_sha256") != sha256(canonical(value.get("rows"))) or
                value.get("source_sha256") != sha256(canonical({"provider": "yahoo", "metadata": value.get("provider_metadata"), "rows": value.get("rows")})) or
                instant(value["fetched_at"]) > current or
                value.get("last_completed_session") != value["rows"][-1]["date"]):
            return None
        validate_rows(value["rows"])
        validate_provider(target, value["provider_metadata"])
        return value
    except (OSError, ValueError, KeyError, TypeError, EOFError):
        return None


def save_cache(root, target, value):
    path = cache_path(root, target)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(gzip.compress(canonical(value), mtime=0))
    temporary.replace(path)


def last_closed_session(model, market, current):
    zone = ZoneInfo("Asia/Seoul" if market == "KR" else "America/New_York")
    cal = model.calendar(market, current.year)
    session = cal.date_to_session(current.astimezone(zone).date().isoformat(), direction="previous")
    if cal.session_close(session).to_pydatetime() > current - timedelta(seconds=5):
        session = cal.previous_session(session)
    return str(session)[:10]


def price_provenance(cache, target, *, cache_hit):
    return {"provider": "Yahoo Finance via yfinance", "provider_is_official_exchange": False,
            "provider_symbol": target["provider_symbol"], "adjustment": "raw", "interval": "1d",
            "fetched_at": cache["fetched_at"], "last_session": cache["last_completed_session"],
            "bars": len(cache["rows"]), "history_sha256": cache["history_sha256"],
            "source_sha256": cache["source_sha256"], "cache_hit": cache_hit,
            "source_response_symbol": cache["provider_metadata"]["symbol"],
            "source_response_exchange": cache["provider_metadata"]["exchangeName"],
            "source_response_timezone": cache["provider_metadata"]["exchangeTimezoneName"],
            "source_response_instrument_type": cache["provider_metadata"]["instrumentType"],
            "last_session_split": cache["rows"][-1].get("splits"),
            "currency": cache["provider_metadata"].get("currency"),
            "source_url": "https://finance.yahoo.com/quote/" + target["provider_symbol"]}


def acquire_bars(target, cache_dir, collector, model, budget, clock):
    current = clock()
    cached = load_cache(cache_dir, target, current)
    expected = last_closed_session(model, target["market"], current)
    if cached and cached["last_completed_session"] == expected:
        received = clock()
        bars = model.normalise_history(rows_frame(cached["rows"], target["market"]), target["market"], "daily", received)
        return bars, received, price_provenance(cached, target, cache_hit=True), "cache_current"
    start = (date.fromisoformat(cached["last_completed_session"]) - timedelta(days=14)).isoformat() if cached else None
    (frame, metadata), fetched = budget.fetch(collector, target, start)
    validate_provider(target, metadata)
    rows = frame_rows(frame, target["market"])
    if cached:
        old = {row["date"]: row for row in cached["rows"]}
        # Splits/provider historical revisions require a fresh consistent series,
        # not a mixture of older raw prices and newly adjusted observations.
        revised = any(row["date"] in old and any(row[key] != old[row["date"]][key]
                      for key in ("open", "high", "low", "close", "splits")) for row in rows)
        new_split = any(row.get("splits") and row["date"] > cached["last_completed_session"] for row in rows)
        if revised or new_split:
            (frame, metadata), fetched = budget.fetch(collector, target, None)
            validate_provider(target, metadata)
            rows = frame_rows(frame, target["market"])
        else:
            old.update({row["date"]: row for row in rows})
            rows = sorted(old.values(), key=lambda row: row["date"])
    bars = model.normalise_history(rows_frame(rows, target["market"]), target["market"], "daily", fetched)
    completed = set(bars["session"].tolist())
    rows = [row for row in rows if row["date"] in completed]
    if not rows:
        raise ValueError("no_completed_provider_bars")
    metadata = {key: metadata.get(key) for key in ("symbol", "exchangeName", "exchangeTimezoneName", "currency", "instrumentType")}
    cache = {"version": CACHE_VERSION, "identity": cache_identity(target), "provider_metadata": metadata,
             "fetched_at": fetched.isoformat(), "last_completed_session": str(bars.iloc[-1]["session"]),
             "history_sha256": sha256(canonical(rows)),
             "source_sha256": sha256(canonical({"provider": "yahoo", "metadata": metadata, "rows": rows})),
             "rows": rows}
    save_cache(cache_dir, target, cache)
    return bars, fetched, price_provenance(cache, target, cache_hit=False), "fetched"


def base_record(target, clock):
    return {**{key: target[key] for key in IDENTITY_FIELDS}, "mode": "daily",
            "identity_verified": True, "source_identity_policy": IDENTITY_POLICY,
            "status": "no_call", "probabilities": None, "target": None, "direction": None,
            "issued_at": clock().isoformat(), "model_scope": "extended_research_only",
            "recommendation": False, "live_validated": False, "source_collection_attempted": False,
            "source_fetch_attempts": 0, "price_available": False, "price_provenance": None,
            "source_identity_verified": False, "source_response_symbol": None}


def no_call(record, *, collection_status, error_kind, reason):
    return {**record, "status": "no_call", "probabilities": None, "direction": None, "target": None,
            "collection_status": collection_status, "error_kind": error_kind, "reason": reason}


def classify_model_error(exc):
    text = str(exc)
    if any(part in text for part in ("fewer_than_500", "insufficient_train", "insufficient_direction", "insufficient_session")):
        return "insufficient_history"
    return "model_error"


def process_target(target, *, model, collector, cache_dir, budget, clock):
    record = base_record(target, clock)
    if not target["supported"]:
        reason = target["unsupported_reason"]
        return no_call(record, collection_status="unsupported", error_kind=reason, reason=reason)
    stopped = budget.stopped()
    if stopped:
        return no_call(record, collection_status=stopped,
                       error_kind="deadline" if stopped == "deadline_skipped" else "provider_circuit_open",
                       reason="collection_deadline_reached" if stopped == "deadline_skipped" else budget.circuit_reason)
    before = budget.source_fetch_attempts
    try:
        bars, received, provenance, collection = acquire_bars(target, cache_dir, collector, model, budget, clock)
        record.update(price_available=True, price_provenance=provenance, received_at=received.isoformat(),
                      collection_status=collection, source_identity_verified=True,
                      source_response_symbol=provenance["source_response_symbol"])
    except Exception as exc:
        attempts = budget.source_fetch_attempts - before
        record.update(source_collection_attempted=attempts > 0, source_fetch_attempts=attempts)
        kind = exc.kind if isinstance(exc, CollectionStopped) else "source_identity_unverified" if isinstance(exc, SourceIdentityError) else "source_error"
        if isinstance(exc, SourceIdentityError):
            record["source_response_symbol"] = exc.metadata.get("symbol")
        status = "deadline_skipped" if kind == "deadline" and not attempts else "source_error"
        return no_call({**record, "issued_at": clock().isoformat()}, collection_status=status,
                       error_kind=kind, reason=safe_error(exc))
    attempts = budget.source_fetch_attempts - before
    record.update(source_collection_attempted=attempts > 0, source_fetch_attempts=attempts)
    if finite(provenance.get("last_session_split")) and provenance["last_session_split"] != 0:
        return no_call({**record, "issued_at": clock().isoformat()}, collection_status=collection,
                       error_kind="model_gate", reason="latest_session_split_review_required")
    try:
        fitted = model.fit_model(bars, "daily", market=target["market"])
        issued = clock()  # Model fitting can be slow; never date an issue before it finishes.
        result = model.make_prediction(bars, fitted, target["symbol"], target["market"], "daily",
                                       received, issued_at=issued)
        if result.get("symbol") != target["symbol"] or result.get("market") != target["market"]:
            raise ValueError("model_returned_wrong_identity")
        record.update(result)
        record.update({key: target[key] for key in IDENTITY_FIELDS})
        record.update(identity_verified=True, source_identity_policy=IDENTITY_POLICY,
                      model_scope="extended_research_only", recommendation=False, live_validated=False)
        if result.get("status") != "research_prediction":
            return no_call(record, collection_status=collection, error_kind="model_gate",
                           reason=result.get("reason") or "model_declined_prediction")
        record.update(error_kind=None, reason=None)
        validate_record(record, target, clock())
        return record
    except Exception as exc:
        return no_call({**record, "issued_at": clock().isoformat()}, collection_status=collection,
                       error_kind=classify_model_error(exc), reason=safe_error(exc))


def counts_for(records):
    total = len(records)
    prediction = sum(record["status"] == "research_prediction" for record in records)
    not_attempted = sum(record["collection_status"] in NOT_ATTEMPTED for record in records)
    failed = total - prediction - not_attempted
    return {"total": total, "prediction": prediction, "no_call": total - prediction,
            "attempted": total - not_attempted, "failed": failed, "not_attempted": not_attempted,
            "source_collection_attempted": sum(record["source_collection_attempted"] for record in records),
            "source_fetch_attempts": sum(record["source_fetch_attempts"] for record in records),
            "price_available": sum(record["price_available"] for record in records),
            "cache_current": sum(record["collection_status"] == "cache_current" for record in records),
            "unsupported": sum(record["collection_status"] == "unsupported" for record in records),
            "error_kinds": dict(sorted(Counter(record["error_kind"] for record in records if record.get("error_kind")).items()))}


def validate_record(record, target, completed):
    if any(record.get(key) != target[key] for key in IDENTITY_FIELDS):
        raise ValueError("result_identity_mismatch")
    if record.get("identity_verified") is not True or record.get("source_identity_policy") != IDENTITY_POLICY:
        raise ValueError("result_identity_not_verified")
    collection = record.get("collection_status")
    if collection not in COLLECTION_STATUSES or type(record.get("source_collection_attempted")) is not bool:
        raise ValueError("invalid_collection_status")
    attempts = record.get("source_fetch_attempts")
    if type(attempts) is not int or attempts < 0 or (attempts > 0) != record["source_collection_attempted"]:
        raise ValueError("invalid_source_attempt_count")
    if collection in NOT_ATTEMPTED | {"unsupported", "cache_current"} and attempts:
        raise ValueError("unrequested_record_has_source_attempts")
    if collection == "fetched" and not attempts:
        raise ValueError("fetched_record_without_source_attempt")
    if type(record.get("price_available")) is not bool:
        raise ValueError("invalid_price_availability")
    if record["price_available"]:
        provenance = record.get("price_provenance") or {}
        if (collection not in ("fetched", "cache_current") or
                record.get("source_identity_verified") is not True or
                record.get("source_response_symbol") != target["provider_symbol"] or
                provenance.get("provider_symbol") != target["provider_symbol"] or
                any(not re.fullmatch(r"[0-9a-f]{64}", str(provenance.get(key, "")))
                    for key in ("history_sha256", "source_sha256")) or
                instant(provenance["fetched_at"]) > instant(record["received_at"])):
            raise ValueError("invalid_price_provenance")
        validate_provider(target, {"symbol": provenance.get("source_response_symbol"),
                                  "exchangeName": provenance.get("source_response_exchange"),
                                  "exchangeTimezoneName": provenance.get("source_response_timezone"),
                                  "instrumentType": provenance.get("source_response_instrument_type")})
        if instant(record["received_at"]) > instant(record["issued_at"]):
            raise ValueError("receipt_after_issue_time_contract")
    if record.get("recommendation") is not False or record.get("live_validated") is not False:
        raise ValueError("invalid_research_disclosure")
    if record.get("status") == "no_call":
        if record.get("probabilities") is not None or record.get("target") is not None or record.get("direction") is not None:
            raise ValueError("no_call_contains_prediction")
        if not record.get("error_kind") or not record.get("reason"):
            raise ValueError("no_call_reason_missing")
        if instant(record["issued_at"]) > completed:
            raise ValueError("future_no_call_timestamp")
        return
    if record.get("status") != "research_prediction" or not record["price_available"]:
        raise ValueError("prediction_without_real_price")
    probabilities = record.get("probabilities")
    if (not isinstance(probabilities, dict) or set(probabilities) != {"up", "flat", "down"} or
            any(not finite(value) or not 0 <= value <= 1 for value in probabilities.values()) or
            abs(sum(probabilities.values()) - 1) > 1e-6 or record.get("direction") not in probabilities):
        raise ValueError("invalid_model_probabilities")
    observed, received, issued = (instant(record[key]) for key in ("observed_until", "received_at", "issued_at"))
    start, end = (instant(record["target"][key]) for key in ("start", "end"))
    if not observed <= received <= issued < start < end or issued > completed or end <= completed:
        raise ValueError("invalid_or_expired_prospective_time_contract")
    contract = model_contract()
    if (record.get("version") != contract["VERSION"] or
            record.get("policy_revision") != contract["POLICY"]["policy_revision"] or
            record.get("policy_sha256") != sha256(canonical(contract["POLICY"])) or
            record.get("mode") != "daily" or record.get("strict_green_override") is not False or
            record.get("history_is_point_in_time_vintage") is not False or
            record.get("delivery_verified") is not False):
        raise ValueError("invalid_model_policy_or_research_claim")
    if any(not re.fullmatch(r"[0-9a-f]{64}", str(record.get(key, "")))
           for key in ("model_sha256", "input_sha256", "id")):
        raise ValueError("invalid_model_or_input_fingerprint")
    features = record.get("feature_values")
    if not isinstance(features, dict) or set(features) != set(contract["FEATURES"]) or not all(finite(value) for value in features.values()):
        raise ValueError("invalid_frozen_model_features")
    if record["input_sha256"] != sha256(canonical({"origin": record["observed_until"],
                                                   "features": features, "received_at": record["received_at"]})):
        raise ValueError("model_input_fingerprint_mismatch")
    if record["id"] != sha256(canonical({"symbol": record["symbol"], "mode": "daily",
                                         "origin": record["observed_until"], "target": record["target"],
                                         "model": record["model_sha256"], "version": record["version"]})):
        raise ValueError("model_issuance_fingerprint_mismatch")
    validation = record.get("validation") or {}
    trained, calibrated, test_start, test_end = (instant(value) for value in
        (record.get("trained_through"), record.get("calibrated_through"),
         validation.get("test_start"), validation.get("test_end")))
    if not trained <= calibrated < test_start < test_end <= observed:
        raise ValueError("model_train_calibration_test_time_contract")
    samples = ((record.get("training_samples"), 150), (record.get("calibration_samples"), 40),
               (validation.get("test_samples"), contract["POLICY"]["minimum_independent_test_samples"]),
               (validation.get("test_sessions"), contract["POLICY"]["minimum_test_sessions"]))
    if any(type(value) is not int or value < minimum for value, minimum in samples):
        raise ValueError("model_validation_sample_gate")
    if (validation.get("live_validated") is not False or validation.get("live_success_rate") is not None or
            not finite(record.get("origin_reference_price")) or record["origin_reference_price"] <= 0):
        raise ValueError("invalid_model_validation_or_origin_price")
    if provenance.get("last_session") != record.get("origin_session"):
        raise ValueError("model_origin_and_price_session_mismatch")
    if finite(provenance.get("last_session_split")) and provenance["last_session_split"] != 0:
        raise ValueError("latest_session_split_review_required")
    audit_module().validate(record)


def execute_shard(manifest, shard_index, *, cache_dir, collector=None, model=None, max_seconds=1800,
                  request_delay=1.0, rate_limit_retries=2, backoff_base=15.0,
                  clock=now_utc, monotonic=time.monotonic, sleeper=time.sleep):
    validate_manifest(manifest)
    if not 0 <= shard_index < manifest["shard_count"]:
        raise ValueError("shard_index_out_of_range")
    if not 0 <= max_seconds <= 21600 or not 0 <= request_delay <= 60 or not 0 <= rate_limit_retries <= 3 or not 0 <= backoff_base <= 120:
        raise ValueError("unbounded_collection_configuration")
    started = clock()
    model = model or model_module()
    collector = collector or YahooCollector()
    targets = [target for target in manifest["targets"] if target["shard_index"] == shard_index]
    budget = RequestBudget(max_seconds=max_seconds, request_delay=request_delay, retries=rate_limit_retries,
                           backoff=backoff_base, clock=clock, monotonic=monotonic, sleeper=sleeper)
    records = []
    for index, target in enumerate(targets, 1):
        records.append(process_target(target, model=model, collector=collector, cache_dir=cache_dir,
                                      budget=budget, clock=clock))
        if index % 25 == 0 or index == len(targets):
            print("UNIVERSE_SHARD_PROGRESS", shard_index, index, "/", len(targets),
                  json.dumps(counts_for(records), ensure_ascii=False, separators=(",", ":")), flush=True)
    completed = clock()
    for record, target in zip(records, targets):
        validate_record(record, target, completed)
    return {"version": SHARD_VERSION, "manifest_sha256": manifest["manifest_sha256"],
            "run_id": manifest["run_id"], "run_attempt": manifest["run_attempt"],
            "source_commit": manifest["source_commit"], "catalog_sha256": manifest["catalog_sha256"],
            "shard_index": shard_index, "shard_count": manifest["shard_count"],
            "started_at": started.isoformat(), "completed_at": completed.isoformat(),
            "counts": counts_for(records), "provider_circuit_reason": budget.circuit_reason,
            "rate_limit_events": budget.rate_limit_events, "transport_failures": budget.transport_failures,
            "records": records}


def aggregate(manifest, shard_paths, catalog_path, *, clock=now_utc):
    validate_manifest(manifest)
    catalog, catalog_hash = load_catalog(catalog_path)
    if catalog_hash != manifest["catalog_sha256"] or targets_for_catalog(catalog, manifest["shard_count"]) != manifest["targets"]:
        raise ValueError("catalogue_changed_since_manifest")
    expected = {target["key"]: target for target in manifest["targets"]}
    records, shards = {}, {}
    completed = clock()
    for path in shard_paths:
        raw = Path(path).read_bytes()
        shard = json.loads(raw)
        index = shard.get("shard_index")
        if type(index) is not int or not 0 <= index < manifest["shard_count"] or index in shards:
            raise ValueError("duplicate_or_invalid_shard")
        if (shard.get("version") != SHARD_VERSION or any(shard.get(key) != manifest[key] for key in
                ("manifest_sha256", "run_id", "run_attempt", "source_commit", "catalog_sha256", "shard_count"))):
            raise ValueError("mixed_run_or_manifest_shard")
        start, end = instant(shard["started_at"]), instant(shard["completed_at"])
        if not instant(manifest["created_at"]) <= start <= end <= completed:
            raise ValueError("invalid_shard_run_timestamps")
        rows = shard.get("records", [])
        required = {target["key"] for target in manifest["targets"] if target["shard_index"] == index}
        if len(rows) != len(required) or {row.get("key") for row in rows} != required:
            raise ValueError("shard_identity_coverage_mismatch")
        for record in rows:
            key = record["key"]
            if key in records:
                raise ValueError("duplicate_result_identity")
            validate_record(record, expected[key], end)
            if instant(record["issued_at"]) < start:
                raise ValueError("result_was_not_issued_in_this_shard_run")
            # A forecast must still have an unfinished target when the result is assembled.
            if record["status"] == "research_prediction" and instant(record["target"]["end"]) <= completed:
                raise ValueError("prediction_expired_before_aggregation")
            records[key] = record
        if shard.get("counts") != counts_for(rows):
            raise ValueError("shard_counts_do_not_match_records")
        shards[index] = {"index": index, "sha256": sha256(raw), "started_at": shard["started_at"],
                         "completed_at": shard["completed_at"], "records": len(rows),
                         "provider_circuit_reason": shard.get("provider_circuit_reason"),
                         "rate_limit_events": shard.get("rate_limit_events", 0)}
    if set(shards) != set(range(manifest["shard_count"])) or set(records) != set(expected):
        raise ValueError("missing_shards_or_identities")
    ordered = [records[target["key"]] for target in manifest["targets"]]
    coverage = counts_for(ordered)
    coverage.update(manifest_complete=True, coverage_complete=coverage["not_attempted"] == 0)
    run = {"id": manifest["run_id"], "attempt": manifest["run_attempt"],
           "started_at": min(shard["started_at"] for shard in shards.values()),
           "completed_at": completed.isoformat(), "source_commit": manifest["source_commit"],
           "manifest_sha256": manifest["manifest_sha256"], "catalog_sha256": manifest["catalog_sha256"],
           "implementation_sha256": manifest["implementation_sha256"],
           "attempted": coverage["attempted"], "research_prediction": coverage["prediction"],
           "no_call": coverage["failed"], "failed": coverage["failed"],
           "not_attempted": coverage["not_attempted"],
           "source_collection_attempted": coverage["source_collection_attempted"],
           "source_fetch_attempts": coverage["source_fetch_attempts"],
           "retained_unexpired_after_no_call": 0, "retained_predictions": 0,
           "shard_count": len(shards), "shards": [shards[index] for index in sorted(shards)]}
    return {"version": VERSION, "source_identity_policy": IDENTITY_POLICY, "policy": POLICY,
            "generation_mode": "full_universe", "source_catalog_sha256": manifest["catalog_sha256"],
            "run_id": manifest["run_id"], "source_commit": manifest["source_commit"],
            "implementation_sha256": manifest["implementation_sha256"],
            "generated_at": completed.isoformat(), "source_catalog_generated_at": catalog["generated_at"],
            "status": "research_only_partial_coverage", "real_time_connected": False,
            "automatic_orders": False, "scope_note": "공식 명부 전체의 실제 수집·학습 결과. 보류·미처리는 확률을 생성하지 않으며 연구 확률은 매수 성공률이 아닙니다.",
            "manifest_sha256": manifest["manifest_sha256"],
            "universe": {"total": len(ordered), "directory": len(ordered), "attempted_total": coverage["attempted"]},
            "coverage": coverage, "run": run, "records": ordered}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("manifest")
    build.add_argument("--catalog", required=True)
    build.add_argument("--output", required=True)
    build.add_argument("--shards", type=int, default=32)
    build.add_argument("--run-id", required=True)
    build.add_argument("--source-commit", required=True)
    build.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    collect = commands.add_parser("shard")
    collect.add_argument("--manifest", required=True)
    collect.add_argument("--shard-index", type=int, required=True)
    collect.add_argument("--output", required=True)
    collect.add_argument("--cache-dir", required=True)
    collect.add_argument("--max-seconds", type=float, default=1800)
    collect.add_argument("--request-delay", type=float, default=1.0)
    collect.add_argument("--rate-limit-retries", type=int, default=2)
    collect.add_argument("--backoff-base", type=float, default=15.0)
    combine = commands.add_parser("aggregate")
    combine.add_argument("--manifest", required=True)
    combine.add_argument("--shard-dir", required=True)
    combine.add_argument("--catalog", required=True)
    combine.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "manifest":
        value = create_manifest(args.catalog, shards=args.shards, run_id=args.run_id,
                                source_commit=args.source_commit, run_attempt=args.run_attempt)
        write_json(args.output, value)
        print("UNIVERSE_MANIFEST", len(value["targets"]), "shards", args.shards, value["manifest_sha256"], flush=True)
    elif args.command == "shard":
        value = execute_shard(read_json(args.manifest), args.shard_index, cache_dir=args.cache_dir,
                              max_seconds=args.max_seconds, request_delay=args.request_delay,
                              rate_limit_retries=args.rate_limit_retries, backoff_base=args.backoff_base)
        write_json(args.output, value)
        print("UNIVERSE_SHARD_COMPLETE", args.shard_index, json.dumps(value["counts"], separators=(",", ":")), flush=True)
    else:
        paths = sorted(Path(args.shard_dir).rglob("shard-*.json"))
        value = aggregate(read_json(args.manifest), paths, args.catalog)
        write_json(args.output, value)
        print("UNIVERSE_AGGREGATE", json.dumps(value["coverage"], ensure_ascii=False, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
