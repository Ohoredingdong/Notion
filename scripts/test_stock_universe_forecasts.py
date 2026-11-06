"""Offline regression tests; every generated candle below is TEST-ONLY synthetic.

No provider is contacted. Tests exercise issuer identity, actual attempt counts,
bounded stopping, cache reuse/revisions, timestamps and whole-run aggregation.
"""
from datetime import datetime, timedelta, timezone
import gzip
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd
from scripts import run_stock_universe_forecasts as x

UTC = timezone.utc


class Clock:
    def __init__(self):
        self.current = datetime(2026, 11, 6, 7, tzinfo=UTC)
        self.elapsed = 0.0

    def now(self):
        return self.current

    def monotonic(self):
        return self.elapsed

    def advance(self, seconds):
        self.elapsed += seconds
        self.current += timedelta(seconds=seconds)


class TestCalendar:
    def __init__(self, market):
        self.market = market

    def date_to_session(self, day, direction="previous"):
        value = pd.Timestamp(day)
        while value.weekday() > 4:
            value -= pd.Timedelta(days=1)
        return value

    def previous_session(self, value):
        return self.date_to_session(str(pd.Timestamp(value) - pd.Timedelta(days=1))[:10])

    def session_close(self, value):
        hours = 6.5 if self.market == "KR" else 21
        return pd.Timestamp(str(value)[:10], tz="UTC") + pd.Timedelta(hours=hours)


class TestModel:
    """An explicit test double: real production uses stock_forecast_model."""
    def __init__(self, clock, error=None):
        self.clock, self.error = clock, error
        self.fit_calls = []

    def calendar(self, market, year):
        return TestCalendar(market)

    def normalise_history(self, frame, market, mode, received):
        rows = []
        cal = TestCalendar(market)
        for index, row in frame.iterrows():
            day = pd.Timestamp(index).date().isoformat()
            if pd.Timestamp(day).weekday() > 4:
                continue
            end = cal.session_close(day)
            if end.to_pydatetime() > received - timedelta(seconds=5):
                continue
            rows.append({"session": day, "start": end-pd.Timedelta(hours=6.5), "end": end,
                         **{k: float(row[k.capitalize()]) for k in ("open", "high", "low", "close")}})
        if not rows:
            raise ValueError("no_completed_regular_session_bars")
        return pd.DataFrame(rows)

    def fit_model(self, bars, mode, market=None):
        self.fit_calls.append((mode, market, self.clock.now()))
        self.clock.advance(3)
        if self.error:
            raise ValueError(self.error)
        return {"test_only": True, "model_sha256": "a"*64}

    def make_prediction(self, bars, fitted, symbol, market, mode, received, issued_at=None):
        contract = x.model_contract()
        observed = bars.iloc[-1]["end"].to_pydatetime()
        features = {key: .001 for key in contract["FEATURES"]}
        record = {"symbol": symbol, "market": market, "mode": mode,
                "version": contract["VERSION"], "policy_revision": contract["POLICY"]["policy_revision"],
                "policy_sha256": x.sha256(x.canonical(contract["POLICY"])),
                "status": "research_prediction", "received_at": received.isoformat(),
                "issued_at": issued_at.isoformat(), "observed_until": bars.iloc[-1]["end"].isoformat(),
                "origin_session": bars.iloc[-1]["session"], "model_sha256": fitted["model_sha256"],
                "training_samples": 500, "calibration_samples": 40,
                "trained_through": (observed-timedelta(days=100)).isoformat(),
                "calibrated_through": (observed-timedelta(days=40)).isoformat(),
                "strict_green_override": False, "history_is_point_in_time_vintage": False,
                "delivery_verified": False, "feature_values": features, "neutral_band_pct": .30,
                "probabilities": {"down": .2, "flat": .3, "up": .5}, "direction": "up",
                "target": {"start": (issued_at+timedelta(hours=1)).isoformat(),
                           "end": (issued_at+timedelta(hours=8)).isoformat()},
                "origin_reference_price": float(bars.iloc[-1]["close"]),
                "validation": {"test_samples": 40, "test_sessions": 40, "live_validated": False,
                               "live_success_rate": None,
                               "test_start": (observed-timedelta(days=30)).isoformat(),
                               "test_end": (observed-timedelta(days=1)).isoformat()}}
        record["input_sha256"] = x.sha256(x.canonical({"origin": record["observed_until"],
                                                      "features": features, "received_at": record["received_at"]}))
        record["id"] = x.sha256(x.canonical({"symbol": symbol, "mode": mode, "origin": record["observed_until"],
                                            "target": record["target"], "model": record["model_sha256"],
                                            "version": record["version"]}))
        return record


def item(symbol="AAPL", country="US", exchange="NASDAQ", name=None):
    return {"symbol": symbol, "source_symbol": symbol, "country": country,
            "exchange": exchange, "name": name or "TEST-ONLY " + symbol}


def catalogue(items):
    return {"version": "radar-universe-catalog-v1", "identifier_policy": x.IDENTITY_POLICY,
            "status": "complete", "generated_at": "2026-11-06T03:00:00Z", "items": items,
            "counts": {"total": len(items), "KR": sum(i["country"] == "KR" for i in items),
                       "US": sum(i["country"] == "US" for i in items)}}


def metadata(target):
    exchanges = {"KOSPI": "KSC", "KOSDAQ": "KOE", "NASDAQ": "NMS", "NYSE": "NYQ"}
    return {"symbol": target["provider_symbol"], "exchangeName": exchanges[target["catalog_exchange"]],
            "exchangeTimezoneName": "Asia/Seoul" if target["market"] == "KR" else "America/New_York",
            "currency": "KRW" if target["market"] == "KR" else "USD", "instrumentType": "EQUITY"}


def candles(target, dates=None, scale=1):
    dates = dates or ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
    rows = []
    for day in dates:
        price = 100 + datetime.fromisoformat(day).day
        rows.append({"date": day, "open": price*scale, "high": (price+2)*scale,
                     "low": (price-2)*scale, "close": (price+1)*scale, "volume": 1000., "splits": 0.})
    return x.rows_frame(rows, target["market"])


def real_model_candles(model, target):
    """TEST-ONLY synthetic prices on the production exchange calendar."""
    import numpy as np
    sessions = model.calendar("US", 2026).sessions_in_range("2021-01-01", "2026-11-05")[-900:]
    rng, price, rows = np.random.default_rng(478), 100., []
    for session in sessions:
        opened = price * (1+rng.normal(0, .001))
        price = opened * np.exp(rng.normal(.0001, .012))
        rows.append({"date": session.date().isoformat(), "open": opened,
                     "high": max(opened, price)*1.002, "low": min(opened, price)*.998,
                     "close": price, "volume": 1000., "splits": 0.})
    return x.rows_frame(rows, target["market"])


class WholeUniverseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.catalog = self.root / "catalog.json"
        self.cache = self.root / "cache"
        self.clock = Clock()

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, items=None, shards=1):
        x.write_json(self.catalog, catalogue(items or [item()]))
        return x.create_manifest(self.catalog, shards=shards, run_id="test-run", source_commit="1"*40,
                                 clock=self.clock.now)

    def collector(self, target, start=None):
        self.clock.advance(10)
        return candles(target), metadata(target)

    def collect(self, manifest, index=0, **kwargs):
        options = {"cache_dir": self.cache, "model": TestModel(self.clock), "collector": self.collector,
                   "clock": self.clock.now, "monotonic": self.clock.monotonic, "sleeper": self.clock.advance,
                   "request_delay": 0, "backoff_base": 1}
        options.update(kwargs)
        return x.execute_shard(manifest, index, **options)

    def shard_files(self, shards):
        paths = []
        for shard in shards:
            path = self.root / f"shard-{shard['shard_index']}.json"
            x.write_json(path, shard)
            paths.append(path)
        return paths

    def test_manifest_covers_every_issuer_and_maps_share_classes_explicitly(self):
        values = [item("0001A0", "KR", "KOSDAQ"), item("BRK.B", exchange="NYSE"),
                  item("MOG.A", exchange="NYSE"), item("V", exchange="NYSE")]
        manifest = self.manifest(values, shards=32)
        targets = {t["key"]: t for t in manifest["targets"]}
        self.assertEqual(len(targets), 4)
        self.assertEqual(targets["KR:0001A0"]["provider_symbol"], "0001A0.KQ")
        self.assertEqual(targets["US:BRK.B"]["symbol"], "BRK-B")
        self.assertEqual(targets["US:MOG.A"]["symbol"], "MOG-A")
        self.assertEqual(targets["US:MOG.A"]["catalog_symbol"], "MOG.A")
        self.assertTrue(all(t["supported"] for t in targets.values()))
        x.validate_manifest(manifest)

    def test_provider_alias_collision_is_blocked_for_both_catalogue_rows(self):
        manifest = self.manifest([item("MOG.A", exchange="NYSE"), item("MOG-A", exchange="NYSE")])
        shard = self.collect(manifest, collector=lambda *args: self.fail("collision must not fetch"))
        self.assertEqual(shard["counts"]["failed"], 2)
        self.assertEqual(shard["counts"]["not_attempted"], 0)
        self.assertEqual(shard["counts"]["source_collection_attempted"], 0)
        self.assertTrue(all(r["error_kind"] == "provider_collision" for r in shard["records"]))

    def test_duplicate_or_corrupted_catalogue_identity_cannot_start_collection(self):
        with self.assertRaisesRegex(ValueError, "duplicate_catalogue"):
            self.manifest([item(), item()])
        bad = item("0001A0", "KR", "KOSDAQ")
        bad["source_symbol"] = "000010"
        with self.assertRaisesRegex(ValueError, "unverified_korean"):
            self.manifest([bad])

    def test_manifest_hash_detects_target_mutation(self):
        manifest = self.manifest()
        manifest["targets"][0]["catalog_name"] = "different issuer"
        with self.assertRaisesRegex(ValueError, "manifest_hash"):
            self.collect(manifest)

    def test_fetch_and_issue_timestamps_follow_actual_completion(self):
        start = self.clock.now()
        manifest = self.manifest()
        model = TestModel(self.clock)
        shard = self.collect(manifest, model=model)
        row = shard["records"][0]
        self.assertEqual(x.instant(row["price_provenance"]["fetched_at"]), start+timedelta(seconds=10))
        self.assertEqual(x.instant(row["received_at"]), start+timedelta(seconds=10))
        self.assertEqual(x.instant(row["issued_at"]), start+timedelta(seconds=13))
        self.assertEqual(model.fit_calls[0][:2], ("daily", "US"))
        self.assertEqual(row["status"], "research_prediction")
        self.assertEqual(row["source_response_symbol"], "AAPL")
        self.assertTrue(row["source_identity_verified"])

    def test_current_cache_avoids_network_without_relabeling_observation_time(self):
        manifest = self.manifest()
        first = self.collect(manifest)["records"][0]
        self.clock.advance(60)
        second = self.collect(manifest, collector=lambda *args: self.fail("current cache must not fetch"))["records"][0]
        self.assertEqual(second["collection_status"], "cache_current")
        self.assertFalse(second["source_collection_attempted"])
        self.assertEqual(second["source_fetch_attempts"], 0)
        self.assertEqual(second["price_provenance"]["fetched_at"], first["price_provenance"]["fetched_at"])
        self.assertEqual(second["price_provenance"]["history_sha256"], first["price_provenance"]["history_sha256"])
        self.assertGreater(x.instant(second["issued_at"]), x.instant(first["issued_at"]))

    def test_stale_cache_fetches_overlap_and_merges_unique_actual_bars(self):
        manifest = self.manifest()
        first = self.collect(manifest)["records"][0]
        self.clock.advance(4*86400)
        calls = []
        def incremental(target, start):
            calls.append(start)
            self.clock.advance(2)
            return candles(target, ["2026-11-05", "2026-11-06", "2026-11-09"]), metadata(target)
        second = self.collect(manifest, collector=incremental)["records"][0]
        self.assertEqual(calls, ["2026-10-22"])
        self.assertEqual(second["price_provenance"]["last_session"], "2026-11-09")
        self.assertEqual(second["price_provenance"]["bars"], 6)
        self.assertNotEqual(first["price_provenance"]["history_sha256"], second["price_provenance"]["history_sha256"])

    def test_historical_revision_refetches_consistent_full_history(self):
        manifest = self.manifest()
        self.collect(manifest)
        self.clock.advance(4*86400)
        calls = []
        def revised(target, start):
            calls.append(start)
            self.clock.advance(1)
            dates = ["2026-11-05", "2026-11-06", "2026-11-09"] if start else ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-09"]
            return candles(target, dates, scale=.5), metadata(target)
        row = self.collect(manifest, collector=revised)["records"][0]
        self.assertEqual(calls, ["2026-10-22", None])
        self.assertEqual(row["source_fetch_attempts"], 2)
        cached = x.load_cache(self.cache, manifest["targets"][0], self.clock.now())
        self.assertTrue(all(r["close"] < 60 for r in cached["rows"]))

    def test_corrupt_cache_does_not_become_valid_price_evidence(self):
        manifest = self.manifest()
        self.collect(manifest)
        path = x.cache_path(self.cache, manifest["targets"][0])
        value = json.loads(gzip.decompress(path.read_bytes()))
        value["rows"][0]["close"] = 9999999
        path.write_bytes(gzip.compress(x.canonical(value)))
        row = self.collect(manifest)["records"][0]
        self.assertEqual(row["collection_status"], "fetched")
        self.assertEqual(row["source_fetch_attempts"], 1)

    def test_invalid_ohlc_rows_are_removed_with_exact_response_counts(self):
        target = self.manifest()["targets"][0]
        frame = candles(target)
        frame.iloc[0, frame.columns.get_loc("High")] = frame.iloc[0]["Open"]-1
        frame.iloc[1, frame.columns.get_loc("Close")] = float("nan")
        frame.iloc[2, frame.columns.get_loc("Low")] = 0
        quality = {}
        rows = x.frame_rows(frame, "US", quality=quality)
        self.assertEqual(len(rows), 2)
        self.assertEqual(quality, {"basis": "latest_provider_response", "original_rows": 5,
                                  "valid_rows": 2, "discarded_rows": 3,
                                  "discarded_reasons": {"inconsistent_ohlc": 1, "nonfinite_ohlc": 1,
                                                        "nonpositive_ohlc": 1}})

    def test_invalid_prices_do_not_relax_duplicate_or_date_guards(self):
        target = self.manifest()["targets"][0]
        frame = candles(target)
        frame["Close"] = 0
        duplicate = pd.concat([frame, frame.iloc[[0]]])
        with self.assertRaisesRegex(ValueError, "duplicate_provider_daily_bar"):
            x.frame_rows(duplicate, "US")
        frame.index = pd.DatetimeIndex([pd.NaT] + list(frame.index[1:]))
        with self.assertRaisesRegex(ValueError, "invalid_provider_daily_date"):
            x.frame_rows(frame, "US")

    def test_all_invalid_prices_are_no_call_with_counts_and_no_fit(self):
        manifest = self.manifest()
        target, model = manifest["targets"][0], TestModel(self.clock)
        frame = candles(target)
        frame["Close"] = 0
        record = self.collect(manifest, model=model, collector=lambda *_: (frame, metadata(target)))["records"][0]
        self.assertEqual(record["status"], "no_call")
        self.assertIn("no_valid_candles", record["reason"])
        self.assertEqual(record["source_row_quality"]["original_rows"], 5)
        self.assertEqual(record["source_row_quality"]["discarded_rows"], 5)
        self.assertFalse(record["price_available"])
        self.assertIsNone(record["probabilities"])
        self.assertEqual(model.fit_calls, [])

    def test_legacy_valid_cache_remains_usable_with_explicit_count_basis(self):
        manifest = self.manifest()
        self.collect(manifest)
        target = manifest["targets"][0]
        path = x.cache_path(self.cache, target)
        cache = json.loads(gzip.decompress(path.read_bytes()))
        cache.pop("row_quality")
        cache["source_sha256"] = x.cache_source_hash(cache)
        x.save_cache(self.cache, target, cache)
        record = self.collect(manifest, collector=lambda *_: self.fail("legacy valid current cache is usable"))["records"][0]
        self.assertEqual(record["status"], "research_prediction")
        self.assertEqual(record["collection_status"], "cache_current")
        quality = record["price_provenance"]["row_quality"]
        self.assertEqual(quality["basis"], "legacy_verified_cache_rows")
        self.assertEqual(quality["discarded_rows"], 0)
        self.assertEqual(quality["original_rows"], len(cache["rows"]))

    def test_incremental_invalid_bar_cannot_return_from_older_cache(self):
        manifest = self.manifest()
        self.collect(manifest)
        self.clock.advance(4*86400)
        target = manifest["targets"][0]
        frame = candles(target, ["2026-11-05", "2026-11-06", "2026-11-09"])
        frame.iloc[0, frame.columns.get_loc("High")] = 1
        record = self.collect(manifest, collector=lambda *_: (frame, metadata(target)))["records"][0]
        cache = x.load_cache(self.cache, target, self.clock.now())
        self.assertNotIn("2026-11-05", [row["date"] for row in cache["rows"]])
        self.assertEqual(record["price_provenance"]["row_quality"]["original_rows"], 3)
        self.assertEqual(record["price_provenance"]["row_quality"]["discarded_rows"], 1)
        self.assertEqual(record["price_provenance"]["bars"], 5)

    def test_rate_limit_backoff_is_bounded_and_rest_are_not_claimed_attempted(self):
        manifest = self.manifest([item(s) for s in ("AAPL", "MSFT", "NVDA", "ON")])
        calls = []
        def rate_limited(target, start):
            calls.append(target["key"])
            raise RuntimeError("HTTP 429 Too Many Requests")
        shard = self.collect(manifest, collector=rate_limited, rate_limit_retries=2)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(set(calls)), 1)
        self.assertEqual(shard["counts"]["failed"], 1)
        self.assertEqual(shard["counts"]["not_attempted"], 3)
        self.assertEqual(shard["counts"]["source_collection_attempted"], 1)
        self.assertEqual(shard["counts"]["source_fetch_attempts"], 3)
        self.assertEqual(shard["provider_circuit_reason"], "rate_limited")
        self.assertTrue(all(row["probabilities"] is None and row["target"] is None for row in shard["records"]))

    def test_repeated_transport_timeouts_open_a_separate_bounded_circuit(self):
        manifest = self.manifest([item(s) for s in ("AAPL", "MSFT", "NVDA", "ON", "FN")])
        calls = []
        def timeout(target, start):
            calls.append(target["key"])
            raise TimeoutError("timeout")
        shard = self.collect(manifest, collector=timeout)
        self.assertEqual(len(calls), 3)
        self.assertEqual(shard["counts"]["failed"], 3)
        self.assertEqual(shard["counts"]["not_attempted"], 2)

    def test_deadline_preserves_completed_result_and_marks_remaining_unrequested(self):
        manifest = self.manifest([item("AAPL"), item("MSFT")])
        shard = self.collect(manifest, max_seconds=12)
        self.assertEqual(shard["counts"]["prediction"], 1)
        self.assertEqual(shard["counts"]["not_attempted"], 1)
        self.assertEqual(shard["counts"]["source_fetch_attempts"], 1)
        self.assertEqual(shard["records"][1]["collection_status"], "deadline_skipped")

    def test_zero_budget_makes_no_requests_and_no_probabilities(self):
        manifest = self.manifest()
        shard = self.collect(manifest, max_seconds=0, collector=lambda *args: self.fail("deadline must not fetch"))
        self.assertEqual(shard["counts"]["attempted"], 0)
        self.assertEqual(shard["counts"]["not_attempted"], 1)

    def test_wrong_or_missing_provider_identity_is_explicitly_unverified(self):
        for changed in ({}, {"symbol": "MSFT"}, {"exchangeTimezoneName": "Asia/Tokyo"}, {"exchangeName": "HKG"}):
            with self.subTest(changed=changed):
                manifest = self.manifest()
                def wrong(target, start):
                    response = {} if not changed else {**metadata(target), **changed}
                    return candles(target), response
                row = self.collect(manifest, collector=wrong)["records"][0]
                self.assertEqual(row["error_kind"], "source_identity_unverified")
                self.assertFalse(row["price_available"])
                self.assertFalse(row["source_identity_verified"])
                self.assertIsNone(row["probabilities"])

    def test_other_share_class_cannot_be_attached_to_requested_company(self):
        manifest = self.manifest([item("BRK.B", exchange="NYSE")])
        def wrong(target, start):
            return candles(target), {**metadata(target), "symbol": "BRK-A"}
        row = self.collect(manifest, collector=wrong)["records"][0]
        self.assertEqual(row["catalog_symbol"], "BRK.B")
        self.assertEqual(row["provider_symbol"], "BRK-B")
        self.assertEqual(row["source_response_symbol"], "BRK-A")
        self.assertEqual(row["error_kind"], "source_identity_unverified")

    def test_latest_split_is_held_in_fresh_and_current_cache_paths(self):
        manifest = self.manifest()
        model = TestModel(self.clock)
        def split_collector(target, start=None):
            frame, meta = self.collector(target, start)
            frame.loc[frame.index.strftime("%Y-%m-%d") == "2026-11-05", "Stock Splits"] = 1.5
            return frame, meta
        first = self.collect(manifest, collector=split_collector, model=model)["records"][0]
        self.assertEqual(first["reason"], "latest_session_split_review_required")
        self.assertTrue(first["price_available"])
        self.assertEqual(first["collection_status"], "fetched")
        second = self.collect(manifest, model=model, collector=lambda *_: self.fail("current split cache must not request again"))["records"][0]
        self.assertEqual(second["reason"], "latest_session_split_review_required")
        self.assertEqual(second["collection_status"], "cache_current")
        self.assertEqual(model.fit_calls, [])
        self.assertIsNone(second["probabilities"])

    def test_old_split_does_not_block_an_otherwise_valid_new_forecast(self):
        manifest = self.manifest()
        def old_split(target, start=None):
            frame, meta = self.collector(target, start)
            frame.loc[frame.index.strftime("%Y-%m-%d") == "2026-11-03", "Stock Splits"] = 1.5
            return frame, meta
        record = self.collect(manifest, collector=old_split)["records"][0]
        self.assertEqual(record["status"], "research_prediction")

    def test_equity_identity_rejects_another_instrument_or_exchange(self):
        for field, changed in (("instrumentType", "ETF"), ("exchangeName", "PNK")):
            with self.subTest(field=field):
                manifest = self.manifest()
                def bad_source(target, start=None):
                    frame, meta = self.collector(target, start)
                    meta[field] = changed
                    return frame, meta
                record = self.collect(manifest, collector=bad_source)["records"][0]
                self.assertEqual(record["error_kind"], "source_identity_unverified")
                self.assertFalse(record["price_available"])

    def test_500_sample_gate_stays_a_no_call_with_real_price_provenance(self):
        manifest = self.manifest()
        row = self.collect(manifest, model=TestModel(self.clock, "fewer_than_500_daily_training_samples"))["records"][0]
        self.assertTrue(row["price_available"])
        self.assertTrue(row["source_collection_attempted"])
        self.assertEqual(row["error_kind"], "insufficient_history")
        self.assertIsNone(row["probabilities"])
        self.assertIsNone(row["target"])

    def test_unsupported_is_terminal_failure_but_not_a_provider_attempt(self):
        manifest = self.manifest([item("ABC.WS", exchange="NYSE")])
        shard = self.collect(manifest, collector=lambda *args: self.fail("unsupported must not fetch"))
        self.assertEqual(shard["counts"]["failed"], 1)
        self.assertEqual(shard["counts"]["attempted"], 1)
        self.assertEqual(shard["counts"]["not_attempted"], 0)
        self.assertEqual(shard["counts"]["source_collection_attempted"], 0)

    def test_yahoo_metadata_reader_never_issues_an_extra_intraday_query(self):
        manifest = self.manifest()
        target = manifest["targets"][0]
        calls = []
        class Instrument:
            _price_history = SimpleNamespace(_history_metadata=metadata(target))
            def history(self, **kwargs):
                calls.append(kwargs)
                return candles(target)
            @property
            def history_metadata(self):
                raise AssertionError("public metadata accessor may issue an extra request")
        fake_yf = SimpleNamespace(Ticker=lambda symbol: Instrument())
        fake_sources = SimpleNamespace(prepare_sessions=lambda: None, read_history_serially=lambda fn: fn())
        with patch.dict(sys.modules, {"yfinance": fake_yf}), patch.object(x, "sources_module", return_value=fake_sources):
            frame, response = x.YahooCollector()(target)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["period"], "5y")
        self.assertEqual(response["symbol"], "AAPL")

    def test_whole_run_aggregate_preserves_exact_counts_and_provenance(self):
        manifest = self.manifest([item("AAPL"), item("ABC.WS", exchange="NYSE"), item("0001A0", "KR", "KOSDAQ")], shards=2)
        shards = [self.collect(manifest, i) for i in range(2)]
        result = x.aggregate(manifest, self.shard_files(shards), self.catalog, clock=self.clock.now)
        self.assertEqual(result["coverage"]["total"], 3)
        self.assertEqual(result["coverage"]["prediction"], 2)
        self.assertEqual(result["coverage"]["failed"], 1)
        self.assertEqual(result["coverage"]["not_attempted"], 0)
        self.assertEqual(result["run"]["attempted"], result["run"]["research_prediction"] + result["run"]["no_call"])
        self.assertEqual(result["source_catalog_sha256"], manifest["catalog_sha256"])
        self.assertEqual(result["generation_mode"], "full_universe")
        self.assertEqual(result["run_id"], manifest["run_id"])
        self.assertEqual(result["source_commit"], manifest["source_commit"])
        self.assertEqual(result["run"]["retained_predictions"], 0)
        self.assertEqual(len(result["run"]["shards"]), 2)

    def test_missing_empty_shard_and_duplicate_shard_are_rejected(self):
        manifest = self.manifest(shards=2)
        shards = [self.collect(manifest, i) for i in range(2)]
        paths = self.shard_files(shards)
        with self.assertRaisesRegex(ValueError, "missing_shards"):
            x.aggregate(manifest, paths[:1], self.catalog, clock=self.clock.now)
        with self.assertRaisesRegex(ValueError, "duplicate_or_invalid_shard"):
            x.aggregate(manifest, paths + paths[:1], self.catalog, clock=self.clock.now)

    def test_aggregation_rejects_wrong_identity_counts_run_or_new_catalogue(self):
        for mutation, expected in (("identity", "identity_mismatch"), ("counts", "counts_do_not_match"),
                                   ("run", "mixed_run"), ("catalogue", "catalogue_changed")):
            with self.subTest(mutation=mutation):
                manifest = self.manifest()
                shard = self.collect(manifest)
                if mutation == "identity":
                    shard["records"][0]["catalog_name"] = "another issuer"
                elif mutation == "counts":
                    shard["counts"]["prediction"] = 999
                elif mutation == "run":
                    shard["run_id"] = "some-other-run"
                else:
                    value = x.read_json(self.catalog)
                    value["items"][0]["name"] = "new current issuer"
                    x.write_json(self.catalog, value)
                with self.assertRaisesRegex(ValueError, expected):
                    x.aggregate(manifest, self.shard_files([shard]), self.catalog, clock=self.clock.now)

    def test_expired_and_postdated_predictions_cannot_be_published(self):
        manifest = self.manifest()
        shard = self.collect(manifest)
        paths = self.shard_files([shard])
        self.clock.advance(9*3600)
        with self.assertRaisesRegex(ValueError, "expired"):
            x.aggregate(manifest, paths, self.catalog, clock=self.clock.now)
        shard["records"][0]["issued_at"] = (self.clock.now()+timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "time_contract"):
            x.aggregate(manifest, self.shard_files([shard]), self.catalog, clock=self.clock.now)

    def test_aggregate_rejects_forged_model_evidence_and_reused_issuance(self):
        manifest = self.manifest()
        shard = self.collect(manifest)
        mutations = (
            ("direction", lambda r: r.update(direction="down")),
            ("policy", lambda r: r.update(policy_sha256="f"*64)),
            ("model_hash", lambda r: r.update(model_sha256="short")),
            ("input_hash", lambda r: r.update(input_sha256="f"*64)),
            ("training_time", lambda r: r.update(trained_through=r["issued_at"])),
            ("samples", lambda r: r["validation"].update(test_samples=3)),
            ("green", lambda r: r.update(strict_green_override=True)),
            ("band", lambda r: r.update(neutral_band_pct=99)),
            ("prior_issuance", lambda r: r.update(issued_at=(x.instant(shard["started_at"])-timedelta(seconds=1)).isoformat())),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                altered = json.loads(json.dumps(shard))
                mutate(altered["records"][0])
                with self.assertRaises(ValueError):
                    x.aggregate(manifest, self.shard_files([altered]), self.catalog, clock=self.clock.now)

    def test_aggregate_cli_requires_only_standard_library(self):
        manifest = self.manifest([item("ABC.WS", exchange="NYSE")])
        shard = self.collect(manifest)
        # Use historical no-call timestamps so this CLI test is independent of wall time.
        manifest["created_at"] = "2020-01-01T00:00:00+00:00"
        manifest["manifest_sha256"] = x.sha256(x.canonical({k: v for k, v in manifest.items() if k != "manifest_sha256"}))
        shard.update(manifest_sha256=manifest["manifest_sha256"], started_at="2020-01-01T00:00:01+00:00", completed_at="2020-01-01T00:00:02+00:00")
        shard["records"][0]["issued_at"] = "2020-01-01T00:00:01+00:00"
        self.shard_files([shard])
        mpath, output = self.root/"manifest.json", self.root/"result.json"
        x.write_json(mpath, manifest)
        completed = subprocess.run([sys.executable, "-S", x.__file__, "aggregate", "--manifest", str(mpath),
                                    "--shard-dir", str(self.root), "--catalog", str(self.catalog), "--output", str(output)],
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(x.read_json(output)["coverage"]["total"], 1)

    @unittest.skipUnless(importlib.util.find_spec("exchange_calendars"), "full model dependencies are installed in CI")
    def test_existing_real_model_contract_passes_the_full_shard_and_aggregate_path(self):
        model = x.model_module()
        manifest = self.manifest()
        target = manifest["targets"][0]
        frame = real_model_candles(model, target)
        shard = self.collect(manifest, model=model, collector=lambda *_: (frame, metadata(target)))
        row = shard["records"][0]
        self.assertEqual(row["status"], "research_prediction", row.get("reason"))
        result = x.aggregate(manifest, self.shard_files([shard]), self.catalog, clock=self.clock.now)
        self.assertEqual(result["coverage"]["prediction"], 1)
        self.assertEqual(row["version"], "direction-forecast-1.1")

    @unittest.skipUnless(importlib.util.find_spec("exchange_calendars"), "full model dependencies are installed in CI")
    def test_real_model_skips_few_bad_bars_without_bridging_missing_sessions(self):
        model = x.model_module()
        manifest = self.manifest()
        target = manifest["targets"][0]
        frame = real_model_candles(model, target)
        bad_days = [frame.index[i].date().isoformat() for i in (50, 200, 300)]
        frame.iloc[50, frame.columns.get_loc("High")] = 1
        frame.iloc[200, frame.columns.get_loc("Close")] = float("nan")
        frame.iloc[300, frame.columns.get_loc("Low")] = -1
        shard = self.collect(manifest, model=model, collector=lambda *_: (frame, metadata(target)))
        row = shard["records"][0]
        self.assertEqual(row["status"], "research_prediction", row.get("reason"))
        self.assertEqual(row["price_provenance"]["row_quality"]["original_rows"], 900)
        self.assertEqual(row["price_provenance"]["row_quality"]["discarded_rows"], 3)
        cache = x.load_cache(self.cache, target, self.clock.now())
        self.assertEqual(len(cache["rows"]), 897)
        self.assertEqual(cache["row_quality"], row["price_provenance"]["row_quality"])
        bars = model.normalise_history(x.rows_frame(cache["rows"], "US"), "US", "daily", self.clock.now())
        labels = model.target_rows(bars, "daily", market="US")
        calendar = model.calendar("US", 2026)
        for day in bad_days:
            previous = str(calendar.previous_session(pd.Timestamp(day)))[:10]
            index = bars.index[bars["session"].eq(previous)][0]
            self.assertFalse(labels.loc[index, "valid"])
        samples, _, _ = model.samples(bars, "daily", market="US")
        self.assertGreaterEqual(len(samples), 500)
        result = x.aggregate(manifest, self.shard_files([shard]), self.catalog, clock=self.clock.now)
        self.assertEqual(result["coverage"]["prediction"], 1)

    @unittest.skipUnless(importlib.util.find_spec("exchange_calendars"), "full model dependencies are installed in CI")
    def test_invalid_latest_bar_cannot_move_an_expired_target_to_a_future_day(self):
        model = x.model_module()
        manifest = self.manifest()
        target = manifest["targets"][0]
        frame = real_model_candles(model, target)
        frame.iloc[-1, frame.columns.get_loc("High")] = 1
        record = self.collect(manifest, model=model, collector=lambda *_: (frame, metadata(target)))["records"][0]
        self.assertEqual(record["status"], "no_call")
        self.assertEqual(record["reason"], "target_already_started_or_delivery_window_too_short")
        self.assertEqual(record["price_provenance"]["last_session"], "2026-11-04")
        self.assertEqual(record["price_provenance"]["row_quality"]["discarded_rows"], 1)
        self.assertIsNone(record["target"])
        self.assertIsNone(record["probabilities"])


if __name__ == "__main__":
    unittest.main()
