"""Synthetic guards for read-only late-session missing-outcome diagnosis."""
from datetime import datetime, timedelta, timezone
import unittest

from diagnose_stock_timing_kr_late_session import (
    expected_five_minute_starts, gap_classification, missing_matured,
    first_issue_nonoverlapping, instant,
)


class SourceCompletenessNegativeControls(unittest.TestCase):
    def setUp(self):
        self.target = {
            "start": "2026-11-02T06:00:00+00:00",
            "end": "2026-11-02T06:30:00+00:00",
        }
        self.times = expected_five_minute_starts(self.target)

    def test_one_absent_raw_bar_keeps_unverified(self):
        observed = self.times[:4] + self.times[5:]
        result = gap_classification(self.target, observed, observed)
        self.assertEqual(result["status"], "source_snapshot_missing_five_minute_timestamp")
        self.assertEqual(result["raw_present"], 5)
        self.assertEqual(result["regular_present"], 5)
        self.assertEqual(result["missing_raw_utc"], ["2026-11-02T06:20:00+00:00"])

    def test_raw_present_but_regular_session_filter_rejects(self):
        result = gap_classification(self.target, self.times, self.times[:-1])
        self.assertEqual(result["status"], "regular_session_or_ohlc_filter_excluded_timestamp")
        self.assertEqual(result["raw_present"], 6)
        self.assertEqual(result["regular_present"], 5)

    def test_complete_current_provider_does_not_invent_outcome(self):
        result = gap_classification(self.target, self.times, self.times)
        self.assertEqual(result["status"], "complete_in_new_snapshot_but_outcome_still_unstored")
        self.assertEqual(result["missing_raw_utc"], [])
        self.assertEqual(result["missing_regular_utc"], [])

    def test_future_target_not_a_matured_missing_outcome(self):
        forecast = self.row("a", "2026-11-04T06:00:00+00:00", "2026-11-04T06:30:00+00:00")
        proof = self.proof([forecast])
        r = missing_matured([forecast], [], [proof], instant("2026-11-03T13:25:16Z"))
        self.assertEqual(r["pending"], 1)
        self.assertEqual(len(r["missing"]), 0)

    def row(self, ident, start, end, issued="2026-11-02T05:45:00+00:00"):
        return {"id": ident, "symbol": "^KS11", "market": "KR", "mode": "intraday",
                "issued_at": issued, "target": {"start": start, "end": end}}

    def proof(self, forecasts):
        return {"status": "public_verified", "snapshot_generated_at": "2026-11-02T05:46:00Z",
                "verified_at": "2026-11-02T05:47:00Z",
                "prediction_ids": [x["id"] for x in forecasts]}

    def test_first_issuance_and_overlap_are_excluded_before_missing(self):
        first = self.row("first", "2026-11-02T06:00:00+00:00", "2026-11-02T06:30:00+00:00")
        later = self.row("later", "2026-11-02T06:00:00+00:00", "2026-11-02T06:30:00+00:00",
                         "2026-11-02T05:45:30+00:00")
        overlap = self.row("overlap", "2026-11-02T06:10:00+00:00", "2026-11-02T06:40:00+00:00")
        rows, dup, excluded = first_issue_nonoverlapping([overlap, later, first])
        self.assertEqual((dup, excluded, len(rows)), (1, 1, 1))
        self.assertEqual(rows[0]["id"], "first")
        r = missing_matured([overlap, later, first], [],
                            [self.proof([first])], instant("2026-11-03T13:25:16Z"))
        self.assertEqual([x["id"] for x in r["missing"]], ["first"])
        self.assertEqual((r["duplicates"], r["overlaps"]), (1, 1))

    def test_non_30minute_target_rejected_not_interpolated(self):
        with self.assertRaisesRegex(ValueError, "not_a_30_minute_target"):
            expected_five_minute_starts({"start": self.target["start"],
                                         "end": "2026-11-02T06:25:00+00:00"})


if __name__ == "__main__":
    unittest.main()
