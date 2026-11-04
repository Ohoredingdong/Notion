"""Regression tests for forward-only event outlook and no-claim policy."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "event_outlook", Path(__file__).with_name("build_stock_event_outlook.py"))
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
UTC = timezone.utc
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def calendar_at(when, *, generated=NOW, actual=None, ident="1"):
    return {
        "generated_at": generated.isoformat(), "source_url": "https://www.tradingview.com/economic-calendar/",
        "stale": False, "events": [
            {"id": ident, "title_ko": "미국 소비자물가지수", "country": "US",
             "category": "inflation", "impact_level": 3,
             "datetime_kst": when.isoformat(), "actual": actual}
        ],
    }


def official():
    return {
        "verified_at": "2026-11-04", "events": [
            {"id": "scheduled", "title": "한국은행 기준금리 결정", "region": "KR",
             "category": "rate", "event_date": "2026-11-26",
             "timezone": "Asia/Seoul",
             "source_url": "https://www.bok.or.kr/portal/main/contents.do?menuNo=200755"}
        ],
    }


class EventOutlookTests(unittest.TestCase):
    def test_only_future_unreported_events(self):
        good = calendar_at(NOW + timedelta(hours=5))
        result = engine.build(good, {}, NOW)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["category"], "inflation")
        self.assertIsNone(result["events"][0]["hypotheses"]["probability"])
        self.assertFalse(result["returns_backtested"])
        self.assertFalse(result["automatic_orders"])
        self.assertEqual(engine.build(calendar_at(NOW-timedelta(minutes=1)), {}, NOW)["events"], [])
        self.assertEqual(engine.build(calendar_at(NOW+timedelta(hours=5), actual=2.1), {}, NOW)["events"], [])

    def test_stale_feed_is_not_presented_as_fresh(self):
        stale = calendar_at(NOW + timedelta(hours=5), generated=NOW-timedelta(days=2))
        result = engine.build(stale, official(), NOW)
        self.assertEqual(result["status"], "partial_calendar_stale")
        self.assertFalse(result["calendar_fresh"])
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["kind"], "official_policy_schedule")

    def test_reject_nonofficial_seed_urls(self):
        x = official()
        x["events"][0]["source_url"] = "https://fake-federalreserve.example.com/event"
        result = engine.build({}, x, NOW)
        self.assertEqual(result["events"], [])

    def test_date_only_remains_date_only(self):
        result = engine.build({}, official(), NOW)
        entry = result["events"][0]
        self.assertEqual(entry["event_date"], "2026-11-26")
        self.assertEqual(entry["event_timezone"], "Asia/Seoul")
        self.assertEqual(entry["time_precision"], "date_only")
        self.assertEqual(entry["source_type"], "official_schedule")

    def test_timezone_required_for_calendar(self):
        invalid = calendar_at(NOW + timedelta(hours=5))
        invalid["events"][0]["datetime_kst"] = "2026-11-05T09:00:00"
        self.assertEqual(engine.build(invalid, {}, NOW)["events"], [])

    def test_invalid_data_never_creates_return_forecast(self):
        bad = calendar_at(NOW + timedelta(hours=2))
        bad["events"][0]["impact_level"] = "high"
        self.assertEqual(engine.build(bad, {}, NOW)["events"], [])
        good = engine.build(calendar_at(NOW+timedelta(hours=2)), official(), NOW)
        self.assertTrue(good["research_only"])
        self.assertFalse(good["probabilities_available"])
        self.assertTrue(all(e["hypotheses"]["interpretation"].endswith("매매 신호 아님")
                            for e in good["events"]))


if __name__ == "__main__":
    unittest.main()
