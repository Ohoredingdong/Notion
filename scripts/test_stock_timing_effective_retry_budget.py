"""Synthetic negative control for nested source cache-lock fetcher attempts.

No market data, credentials, files or real forecasts are used.
"""
from datetime import datetime, timezone
from unittest import TestCase, main
from unittest.mock import patch

import stock_forecast_autopilot as autopilot
import stock_forecast_sources as source

NOW = datetime(2026, 11, 3, 13, 0, tzinfo=timezone.utc)
SPEC = ("SYNTHETIC", "Test source", "US")


def simulated_failure():
    return {"status": "no_call", "reason": "OperationalError: database is locked",
            "symbol": "SYNTHETIC", "market": "US", "mode": "daily"}, None


class EffectiveRetryBudgetTests(TestCase):
    def test_nested_lock_attempts_respect_effective_autopilot_budget(self):
        fetcher_calls = []

        def locked_fetcher():
            fetcher_calls.append(1)
            raise RuntimeError("database is locked")

        def process(*_):
            try:
                source.read_history_serially(locked_fetcher)
            except RuntimeError as e:
                self.assertIn("database is locked", str(e))
                return simulated_failure()
            self.fail("locked reader must not invent a successful quote")

        collector = autopilot.SafeCollector(
            process, {"cooldowns": {}}, clock=lambda: NOW, sleep=lambda _: None)
        with patch.object(source.time, "sleep", lambda _: None):
            record, bars = collector(SPEC, "daily")
        self.assertIsNone(bars)
        self.assertEqual(record["status"], "no_call")
        self.assertEqual(len(collector.events), autopilot.POLICY["maximum_source_attempts"])
        # Predeclared policy is two effective fetcher calls; baseline has six.
        self.assertLessEqual(len(fetcher_calls), autopilot.POLICY["maximum_source_attempts"])

    def test_transient_lock_success_consumes_at_most_two_outer_fetches(self):
        calls = []
        def fetcher():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("database is locked")
            return "synthetic_complete"

        def process(*_):
            try:
                got = source.read_history_serially(fetcher)
            except RuntimeError:
                return simulated_failure()
            self.assertEqual(got, "synthetic_complete")
            return {"status": "no_call", "reason": "insufficient_regular_session_time",
                    "symbol": "SYNTHETIC", "market": "US", "mode": "daily"}, object()

        collector = autopilot.SafeCollector(
            process, {}, clock=lambda: NOW, sleep=lambda _: None)
        with patch.object(source.time, "sleep", lambda _: None):
            record, bars = collector(SPEC, "daily")
        self.assertIsNotNone(bars)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(collector.events), 2)

    def test_context_resets_even_if_processor_raises(self):
        def processor(*_):
            raise ValueError("unexpected synthetic processor error")
        collector = autopilot.SafeCollector(
            processor, {}, clock=lambda: NOW, sleep=lambda _: None)
        with self.assertRaisesRegex(ValueError, "unexpected synthetic"):
            collector(SPEC, "daily")
        calls = []
        def fetcher():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("database is locked")
            return "standalone_after_error"
        with patch.object(source.time, "sleep", lambda _: None):
            self.assertEqual(source.read_history_serially(fetcher), "standalone_after_error")
        self.assertEqual(len(calls), 3)

    def test_standalone_reader_retains_local_transient_cache_lock_recovery(self):
        calls = []
        def fetcher():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("database is locked")
            return "synthetic_complete"

        with patch.object(source.time, "sleep", lambda _: None):
            self.assertEqual(source.read_history_serially(fetcher), "synthetic_complete")
        self.assertEqual(len(calls), 3)

    def test_nonlock_fatal_error_is_not_retried(self):
        calls = []
        def fetcher():
            calls.append(1)
            raise ValueError("bad synthetic data")

        with self.assertRaisesRegex(ValueError, "bad synthetic data"):
            source.read_history_serially(fetcher)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    main()
