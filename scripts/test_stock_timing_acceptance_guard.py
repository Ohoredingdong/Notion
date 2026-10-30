"""Synthetic negative controls for independent timing-completion-claim guard.

These fixtures are NOT price evidence, not live performance, and cannot approve a trade.
"""
import unittest
from datetime import datetime, timedelta, timezone
from copy import deepcopy

from audit_stock_timing_acceptance_guard import audit_acceptance


def fixture(n=120, days=20, symbol="TEST", market="US", mode="intraday"):
    base = datetime(2026, 10, 1, 13, 30, tzinfo=timezone.utc)
    ledger, rows = [], []
    for i in range(n):
        # Multiple separate windows per day; no overlaps or fake future outcomes.
        start = base + timedelta(days=i % days, minutes=(i // days) * 35)
        end = start + timedelta(minutes=30)
        issued = start - timedelta(minutes=20)
        actual = ("down", "flat", "up")[i % 3]
        target = {"start": start.isoformat(), "end": end.isoformat()}
        ident = "synthetic-" + str(i)
        ledger.append({"id": ident, "status": "research_prediction",
                       "symbol": symbol, "market": market, "mode": mode,
                       "issued_at": issued.isoformat(), "target": target,
                       "direction": actual})
        rows.append({"id": ident, "symbol": symbol, "predicted": actual,
                     "actual": actual, "correct": True, "target": target,
                     "public_at": (start - timedelta(minutes=10)).isoformat()})
    summary = {"status": "ledger_arithmetic_consistent",
               "scored": n, "correct": n, "prediction_rows": n, "rows": rows}
    controller = {"timing_utility": {"status": "not_proven"}}
    return summary, ledger, controller


class TimingAcceptanceNegativeControls(unittest.TestCase):
    def test_synthetic_balanced_sample_cannot_claim_trading_usefulness(self):
        summary, ledger, controller = fixture()
        result = audit_acceptance(summary, ledger, controller)
        self.assertEqual(result["status"], "not_proven")
        self.assertEqual(result["integrity_errors"], [])
        self.assertEqual(result["groups_with_minimal_sample_gate"], 1)
        self.assertFalse(result["actual_executable_quotes_verified"])
        self.assertFalse(result["actual_human_receipt_verified"])
        self.assertFalse(result["after_cost_forward_paper_edge_verified"])
        self.assertFalse(result["untouched_followup_verified"])

    def test_false_completion_claim_cannot_pass(self):
        summary, ledger, controller = fixture()
        controller["timing_utility"]["status"] = "proven"
        result = audit_acceptance(summary, ledger, controller)
        self.assertEqual(result["status"], "integrity_errors")
        self.assertIn("unverified_completion_claim", result["integrity_errors"])

    def test_aggregating_two_small_groups_is_not_a_pass(self):
        summary, ledger, controller = fixture()
        for i, row in enumerate(ledger):
            if i >= 60:
                row["symbol"] = "OTHER"
                summary["rows"][i]["symbol"] = "OTHER"
        result = audit_acceptance(summary, ledger, controller)
        self.assertEqual(result["groups_with_minimal_sample_gate"], 0)
        self.assertEqual(len(result["groups"]), 2)

    def test_one_day_of_rows_cannot_meet_twenty_sessions(self):
        summary, ledger, controller = fixture(n=120, days=1)
        result = audit_acceptance(summary, ledger, controller)
        self.assertEqual(result["groups_with_minimal_sample_gate"], 0)
        self.assertIn("insufficient_observed_sessions", next(iter(result["groups"].values()))["blockers"])

    def test_collapsed_direction_predictions_cannot_pass(self):
        summary, ledger, controller = fixture()
        for row in summary["rows"]:
            row["predicted"] = "flat"
        for row in ledger:
            row["direction"] = "flat"
        result = audit_acceptance(summary, ledger, controller)
        self.assertEqual(result["groups_with_minimal_sample_gate"], 0)
        self.assertIn("insufficient_down_predictions", next(iter(result["groups"].values()))["blockers"])

    def test_duplicate_audited_id_is_not_a_new_target(self):
        summary, ledger, controller = fixture()
        summary["rows"][1] = deepcopy(summary["rows"][0])
        summary["correct"] = 120
        result = audit_acceptance(summary, ledger, controller)
        self.assertIn("duplicate_scored_id", result["integrity_errors"])
        self.assertNotEqual(result["status"], "not_proven")

    def test_unknown_scored_id_is_an_integrity_error(self):
        summary, ledger, controller = fixture()
        summary["rows"][0]["id"] = "unissued-test-forecaster"
        result = audit_acceptance(summary, ledger, controller)
        self.assertIn("scored_unknown_frozen_id", result["integrity_errors"])

    def test_ledger_issued_label_and_target_must_match(self):
        summary, ledger, controller = fixture()
        ledger[0]["direction"] = "up"
        summary["rows"][1]["target"] = deepcopy(summary["rows"][0]["target"])
        result = audit_acceptance(summary, ledger, controller)
        self.assertIn("scored_row_mismatches_frozen", result["integrity_errors"])

    def test_invalid_independent_audit_is_not_a_success(self):
        summary, ledger, controller = fixture()
        summary["status"] = "integrity_errors"
        result = audit_acceptance(summary, ledger, controller)
        self.assertEqual(result["status"], "integrity_errors")
        self.assertIn("upstream_audit_not_consistent", result["integrity_errors"])


if __name__ == "__main__":
    unittest.main()
