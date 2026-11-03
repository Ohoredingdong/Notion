"""Negative controls use synthetic run metadata, never prices or forecasts."""
import unittest
from audit_stock_schedule_coverage import CRONS, NAME, audit, check_workflow, due, expected, utc

ASOF = utc("2026-11-03T15:30:00Z")
START = utc("2026-11-03T12:30:00Z")


def event(when, *, name=NAME, trigger="schedule", result="success"):
    return {"name": name, "event": trigger, "created_at": when,
            "conclusion": result, "status": "completed"}


class LaunchCoverageNegativeControls(unittest.TestCase):
    def test_fixed_window_has_twelve_due_slots(self):
        x = expected(START, ASOF)
        self.assertEqual(len(x), 12)
        self.assertEqual(x[0], "2026-11-03T13:07:00+00:00")
        self.assertEqual(x[-1], "2026-11-03T14:57:00+00:00")

    def test_no_start_is_gap_but_not_dropped_event_proof(self):
        x = audit([], START, ASOF, complete=True)
        self.assertEqual(x["status"], "unobserved_schedule_coverage")
        self.assertEqual(x["unattributed_count_gap"], 12)
        self.assertFalse(x["timing_utility_proven"])

    def test_earlier_delayed_start_does_not_cover_newer_window(self):
        x = audit([event("2026-11-03T11:21:16Z")], START, ASOF, complete=True)
        self.assertEqual(x["observed_schedule_created_count"], 0)
        self.assertEqual(x["latest_created_at"], "2026-11-03T11:21:16+00:00")

    def test_push_manual_and_foreign_workflow_not_counted(self):
        rows = [event("2026-11-03T13:07:00Z", trigger="workflow_dispatch"),
                event("2026-11-03T13:17:00Z", name="Update Stock Decisions")]
        self.assertEqual(audit(rows, START, ASOF, complete=True)["observed_schedule_created_count"], 0)

    def test_failure_still_counts_creation_but_not_success(self):
        rows = [event("2026-11-03T13:30:00Z", result="failure")]
        x = audit(rows, START, ASOF, complete=True)
        self.assertEqual(x["observed_schedule_created_count"], 1)
        self.assertEqual(x["conclusions_in_window"], {"failure": 1})

    def test_after_cutoff_never_backfilled(self):
        rows = [event("2026-11-03T15:31:00Z")]
        self.assertEqual(audit(rows, START, ASOF, complete=True)["observed_schedule_created_count"], 0)

    def test_grace_keeps_recent_due_slots_pending(self):
        self.assertEqual(len(expected(START, ASOF, grace=30)), 12)
        self.assertEqual(len(expected(START, ASOF, grace=0)), 15)

    def test_weekend_without_due_slots_is_not_incident(self):
        a, b = utc("2026-11-01T12:00:00Z"), utc("2026-11-01T16:00:00Z")
        self.assertEqual(audit([], a, b, complete=True)["status"], "no_due_slots")

    def test_incomplete_history_fails_closed(self):
        x = audit([], START, ASOF, complete=False)
        self.assertEqual(x["status"], "history_incomplete")
        self.assertIsNone(x["unattributed_count_gap"])

    def test_equal_run_count_does_not_prove_timely_signals(self):
        rows = [event(f"2026-11-03T13:{m:02d}:05Z") for m in (7, 17, 27, 37, 47, 57)]
        x = audit(rows, utc("2026-11-03T13:00:00Z"),
                  utc("2026-11-03T14:30:00Z"), complete=True)
        self.assertEqual(x["status"], "created_run_count_only")
        self.assertFalse(x["notification_enabled"])

    def test_exact_cron_contract_and_weekdays(self):
        self.assertTrue(due(utc("2026-11-03T13:07:00Z"), CRONS[0]))
        self.assertFalse(due(utc("2026-11-01T13:07:00Z"), CRONS[0]))
        check_workflow("\n".join("    - cron: '" + x + "'" for x in CRONS))
        with self.assertRaisesRegex(ValueError, "cron_changed"):
            check_workflow("    - cron: '* * * * *'")

    def test_bad_timezone_or_unsupported_cron_refused(self):
        with self.assertRaises(ValueError):
            utc("2026-11-03T13:07:00")
        with self.assertRaises(ValueError):
            due(utc("2026-11-03T13:07:00Z"), "* * * * *")


if __name__ == "__main__":
    unittest.main()
