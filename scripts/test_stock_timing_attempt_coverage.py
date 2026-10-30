"""Synthetic negative controls for an independent *attempt* coverage audit.
No synthetic rows become a market-price or trading-performance observation.
"""
import copy
import unittest
from audit_stock_forecast_attempt_coverage import audit_attempt_coverage


def fixture():
    ledger = [
        {"id": "forecast-A", "symbol": "TEST", "mode": "daily", "status": "research_prediction"},
    ]
    attempts = [
        {"id": "attempt-1", "run_id": "101", "symbol": "TEST", "mode": "daily",
         "status": "research_prediction", "prediction_id": "forecast-A", "reason": None,
         "checked_at": "2026-10-29T13:00:00+00:00"},
        {"id": "attempt-2", "run_id": "101", "symbol": "TEST", "mode": "intraday",
         "status": "no_call", "prediction_id": None, "reason": "insufficient_regular_session_time",
         "checked_at": "2026-10-29T13:00:00+00:00"},
        {"id": "attempt-3", "run_id": "102", "symbol": "TEST", "mode": "daily",
         "status": "no_call", "prediction_id": None,
         "reason": "target_already_started_or_delivery_window_too_short",
         "checked_at": "2026-10-29T13:10:00+00:00"},
    ]
    report = {"generated_at": "2026-10-29T13:20:00+00:00",
              "recorded_predictions": 1, "coverage": {
        "attempts": 3, "prediction_attempts": 1, "no_calls": 2,
        "call_rate": 1 / 3, "definition": "scheduler-attempt coverage, not whole-market coverage",
        "no_call_reasons": {
            "insufficient_regular_session_time": 1,
            "target_already_started_or_delivery_window_too_short": 1}}}
    return attempts, ledger, report


class AttemptCoverageTests(unittest.TestCase):
    def test_original_consistent_attempts_pass(self):
        a, l, r = fixture()
        result = audit_attempt_coverage(a, l, r)
        self.assertEqual(result["status"], "attempt_coverage_consistent")
        self.assertEqual(result["facts"]["attempts"], 3)
        self.assertEqual(result["facts"]["unique_run_ids"], 2)
        self.assertEqual(result["facts"]["session_deferred"], 1)
        self.assertFalse(result["human_notification_receipt_verified"])
        self.assertFalse(result["eligible_market_opportunity_coverage_verified"])

    def test_forged_publication_summary_must_fail(self):
        for field, value in [
            ("call_rate", 1.0), ("prediction_attempts", 3),
            ("no_calls", 0), ("attempts", 30),
        ]:
            with self.subTest(field=field):
                a, l, r = fixture()
                r["coverage"][field] = value
                got = audit_attempt_coverage(a, l, r)
                self.assertEqual(got["status"], "attempt_coverage_integrity_errors")
                self.assertIn("reported_coverage_mismatch", got["errors"])

    def test_forged_reason_distribution_must_fail(self):
        a, l, r = fixture()
        r["coverage"]["no_call_reasons"]["insufficient_regular_session_time"] = 2
        self.assertIn("reported_coverage_mismatch", audit_attempt_coverage(a, l, r)["errors"])

    def test_duplicate_attempt_id_must_fail(self):
        a, l, r = fixture()
        a.append(copy.deepcopy(a[0]))
        self.assertIn("duplicate_attempt_id", audit_attempt_coverage(a, l, r)["errors"])

    def test_unknown_frozen_prediction_reference_must_fail(self):
        a, l, r = fixture()
        a[0]["prediction_id"] = "not-in-ledger"
        self.assertIn("attempt_unknown_prediction_id", audit_attempt_coverage(a, l, r)["errors"])

    def test_forecast_symbol_mode_binding_must_fail(self):
        a, l, r = fixture()
        a[0]["symbol"] = "WRONG"
        self.assertIn("attempt_prediction_symbol_mode_mismatch", audit_attempt_coverage(a, l, r)["errors"])

    def test_no_call_with_prediction_id_or_missing_reason_must_fail(self):
        a, l, r = fixture()
        a[1]["prediction_id"] = "forecast-A"
        a[2]["reason"] = None
        got = audit_attempt_coverage(a, l, r)
        self.assertIn("no_call_has_prediction_id", got["errors"])
        self.assertIn("no_call_missing_reason", got["errors"])

    def test_unreviewed_status_must_fail(self):
        a, l, r = fixture()
        a[2]["status"] = "perfect_signal"
        self.assertIn("unexpected_attempt_status", audit_attempt_coverage(a, l, r)["errors"])

    def test_repeated_attempt_is_not_new_forecast(self):
        a, l, r = fixture()
        new = copy.deepcopy(a[0]); new["id"] = "attempt-4"; new["run_id"] = "102"
        new["checked_at"] = "2026-10-29T13:10:00+00:00"
        a.append(new)
        r["coverage"].update(attempts=4, prediction_attempts=2, call_rate=.5)
        got = audit_attempt_coverage(a, l, r)
        self.assertEqual(got["status"], "attempt_coverage_consistent")
        self.assertEqual(got["facts"]["distinct_frozen_forecasts_referenced"], 1)
        self.assertEqual(got["facts"]["prediction_attempts"], 2)


    def test_missing_or_timezone_naive_attempt_clock_rejected(self):
        for forged in (None, "2026-10-29T13:00:00", "not-a-timestamp"):
            with self.subTest(forged=forged):
                a, l, r = fixture()
                if forged is None:
                    a[0].pop("checked_at")
                else:
                    a[0]["checked_at"] = forged
                got = audit_attempt_coverage(a, l, r)
                self.assertIn("invalid_attempt_checked_at", got["errors"])

    def test_attempt_clock_after_saved_report_rejected(self):
        a, l, r = fixture()
        a[0]["checked_at"] = "2026-10-29T13:21:00+00:00"
        got = audit_attempt_coverage(a, l, r)
        self.assertIn("attempt_after_coverage_report", got["errors"])

    def test_inconsistent_checked_at_within_same_run_rejected(self):
        a, l, r = fixture()
        a[1]["checked_at"] = "2026-10-29T13:01:00+00:00"
        got = audit_attempt_coverage(a, l, r)
        self.assertIn("inconsistent_run_checked_at", got["errors"])

    def test_same_instant_across_timezone_offsets_is_valid(self):
        a, l, r = fixture()
        a[1]["checked_at"] = "2026-10-29T22:00:00+09:00"
        got = audit_attempt_coverage(a, l, r)
        self.assertEqual(got["status"], "attempt_coverage_consistent")


if __name__ == "__main__":
    unittest.main()
