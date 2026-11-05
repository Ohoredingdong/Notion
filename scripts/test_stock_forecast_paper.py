"""Synthetic negative controls only; fixtures never become production evidence."""
from copy import deepcopy
from datetime import timedelta
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import stock_forecast_paper as paper
import verify_stock_forecast_public as public

NOW = paper.instant("2026-11-05T13:00:00Z")
AFTER = paper.instant("2026-11-05T15:01:00Z")


def frozen():
    return {"id": "synthetic-paper-only", "symbol": "TEST", "market": "US", "mode": "intraday",
            "status": "research_prediction", "observed_until": "2026-11-05T11:55:00Z",
            "received_at": "2026-11-05T11:56:00Z", "issued_at": "2026-11-05T12:00:00Z",
            "target": {"start": "2026-11-05T14:30:00Z", "end": "2026-11-05T15:00:00Z"},
            "probabilities": {"down": .1, "flat": .1, "up": .8}, "direction": "up",
            "neutral_band_pct": .3, "frozen_baseline_probabilities": {"down": .2, "flat": .5, "up": .3}}


def proof(record):
    row = {"status": "public_verified", "snapshot_generated_at": "2026-11-05T12:00:30Z",
           "verified_at": "2026-11-05T12:01:00Z", "prediction_ids": [record["id"]],
           "human_notification_received": False}
    return {**row, "verification_id": paper.digest(row)}


def schedule():
    return {"market": "US", "basis": "explicit_assumption", "source_url": "https://example.org/synthetic-cost-test",
            "recorded_at": "2026-11-05T12:50:00Z", "effective_from": "2026-11-05T00:00:00Z",
            "effective_until": "2026-11-06T00:00:00Z", "buy_fee_bps": 10, "sell_fee_bps": 10,
            "sell_tax_bps": 20, "assumed_slippage_bps_per_side": 5}


def plan(with_cost=True):
    record = frozen()
    rules = paper.policy_for(None, NOW)
    result, _ = paper.register_plans([record], [proof(record)], rules, [],
                                    {"US": schedule()} if with_cost else {}, NOW)
    return result[0]


def quote(time, bid, ask):
    return {"symbol": "TEST", "market": "US", "currency": "USD", "venue": "XNYS",
            "session": "regular", "kind": "observed_bid_ask", "source_kind": "licensed_broker",
            "source_event_id": "synthetic-" + time, "raw_sha256": "0" * 64,
            "observed_at": time, "received_at": (paper.instant(time) + timedelta(seconds=1)).isoformat(),
            "bid": bid, "ask": ask, "bid_size": 200, "ask_size": 200}


def evidence(p):
    return {"plan_id": p["id"], "forecast_id": p["forecast_id"], "recorded_at": AFTER.isoformat(),
            "plan_publication": {"plan_id": p["id"], "plan_sha256": paper.digest(p),
                                 "verified_at": "2026-11-05T13:02:00Z"},
            "human_receipt": {"kind": "human_receipt", "forecast_id": p["forecast_id"],
                              "receipt_id": "synthetic-receipt", "received_at": "2026-11-05T13:10:00Z"},
            "corporate_action_clear": True,
            "quotes": [quote("2026-11-05T14:30:01Z", 109.9, 110),
                       quote("2026-11-05T14:59:01Z", 105, 105.1)]}


class PublicPlanEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.p = plan()
        self.policy = paper.policy_for(None, NOW)
        paper.write_json(self.root / paper.POLICY_FILE, self.policy)
        (self.root / paper.PLAN_FILE).write_text(json.dumps(self.p) + "\n")
        self.snapshot = {name: (self.root / name).read_bytes() for name in (paper.POLICY_FILE, paper.PLAN_FILE)}
        self.observed = NOW + timedelta(minutes=2)

    def verify(self, observed=None, getter=None):
        return public.verify_paper_publication(self.root, getter or self.snapshot.__getitem__,
                                                lambda: observed or self.observed)

    def publication(self):
        return paper.read_lines(self.root / paper.PUBLICATION_FILE)[0]

    def test_exact_bytes_create_public_proof_but_never_a_human_receipt(self):
        summary = self.verify()
        self.assertEqual(summary, {"new_checks": 1, "before_target": 1, "late_checks": 0, "human_receipts_created": 0})
        row = self.publication()
        self.assertEqual(row["verified_at"], self.observed.isoformat())
        self.assertFalse(row["human_notification_received"])
        self.assertNotIn("human_receipt", row)
        self.assertEqual(paper.verified_plan_publication(self.p, self.policy, [row], AFTER), row)
        self.assertTrue(all((self.root / name).read_bytes() == body for name, body in self.snapshot.items()))

    def test_equal_json_with_different_public_bytes_is_rejected(self):
        remote = dict(self.snapshot)
        remote[paper.PLAN_FILE] = json.dumps(self.p, separators=(",", ":")).encode() + b"\n"
        with self.assertRaisesRegex(ValueError, "public_paper_bytes_not_equal"):
            self.verify(getter=remote.__getitem__)
        self.assertFalse((self.root / paper.PUBLICATION_FILE).exists())

    def test_network_failure_creates_no_public_proof(self):
        def unavailable(name):
            raise OSError("synthetic network failure")
        with self.assertRaises(OSError):
            self.verify(getter=unavailable)
        self.assertFalse((self.root / paper.PUBLICATION_FILE).exists())

    def test_observation_clock_runs_after_http_verification(self):
        fetched = []
        def getter(name):
            fetched.append(name)
            return self.snapshot[name]
        def clock():
            self.assertEqual(fetched, [paper.POLICY_FILE, paper.PLAN_FILE])
            return self.observed
        public.verify_paper_publication(self.root, getter, clock)
        self.assertEqual(self.publication()["verified_at"], self.observed.isoformat())

    def test_repeat_keeps_first_actual_proof_bytes(self):
        self.verify()
        before = (self.root / paper.PUBLICATION_FILE).read_bytes()
        self.assertEqual(self.verify(self.observed + timedelta(minutes=1))["new_checks"], 0)
        self.assertEqual((self.root / paper.PUBLICATION_FILE).read_bytes(), before)

    def test_late_first_check_is_preserved_but_not_eligible(self):
        summary = self.verify(AFTER)
        self.assertEqual(summary["late_checks"], 1)
        self.assertFalse(self.publication()["public_before_target_verified"])
        self.assertIsNone(paper.verified_plan_publication(self.p, self.policy, [self.publication()], AFTER))
        before = (self.root / paper.PUBLICATION_FILE).read_bytes()
        with self.assertRaisesRegex(ValueError, "invalid_paper_publication_proof"):
            self.verify(self.observed)
        self.assertEqual((self.root / paper.PUBLICATION_FILE).read_bytes(), before)

    def test_rehashed_late_proof_cannot_claim_before_target(self):
        self.verify(AFTER)
        forged = self.publication()
        forged["public_before_target_verified"] = True
        forged["verification_id"] = paper.digest({k: v for k, v in forged.items() if k != "verification_id"})
        with self.assertRaisesRegex(ValueError, "invalid_paper_publication_proof"):
            paper.verified_plan_publication(self.p, self.policy, [forged], AFTER)

    def test_plan_cannot_change_while_public_bytes_are_checked(self):
        def getter(name):
            if name == paper.PLAN_FILE:
                (self.root / paper.PLAN_FILE).write_bytes(self.snapshot[name] + b"\n")
            return self.snapshot[name]
        with self.assertRaisesRegex(ValueError, "local_paper_changed"):
            self.verify(getter=getter)
        self.assertFalse((self.root / paper.PUBLICATION_FILE).exists())

    def test_ledger_fallback_removes_only_publication_blocker(self):
        self.verify()
        row = self.publication()
        result = paper.evaluate_plan(self.p, [], AFTER, public_proof=row)
        self.assertTrue(result["plan_public_before_target_verified"])
        self.assertIn("human_receipt_missing", result["blockers"])
        self.assertIn("observed_quotes_missing", result["blockers"])
        self.assertNotIn("plan_publication_proof_missing", result["blockers"])
        self.assertNotIn("strategy_return_pct", result)

    def test_real_public_check_can_supply_missing_inline_proof_only(self):
        self.verify()
        e = evidence(self.p)
        del e["plan_publication"]
        result = paper.evaluate_plan(self.p, [e], AFTER, public_proof=self.publication())
        self.assertEqual(result["status"], "quote_based_paper_diagnostic")
        self.assertFalse(result["actual_fill_verified"])
        e["human_receipt"]["received_at"] = (NOW + timedelta(minutes=1)).isoformat()
        result = paper.evaluate_plan(self.p, [e], AFTER, public_proof=self.publication())
        self.assertIn("human_receipt_after_target_start_or_before_publication", result["blockers"])

    def test_publication_ledger_replay_remains_not_proven(self):
        self.verify()
        for name, content in {"stock-forecast-ledger.jsonl": json.dumps(frozen()) + "\n",
                              "stock-forecast-outcomes.jsonl": "",
                              "stock-forecast-deliveries.jsonl": json.dumps(proof(frozen())) + "\n"}.items():
            (self.root / name).write_text(content)
        before = (self.root / paper.PUBLICATION_FILE).read_bytes()
        result = paper.run(self.root, AFTER)
        self.assertEqual(result["status"], "not_proven")
        self.assertEqual(result["paper_publication"]["plans_public_before_target"], 1)
        self.assertEqual(result["paper_publication"]["human_receipts_created"], 0)
        self.assertEqual(result["blocker_counts"], {"human_receipt_missing": 1, "observed_quotes_missing": 1})
        self.assertEqual((self.root / paper.PUBLICATION_FILE).read_bytes(), before)
        self.assertFalse((self.root / paper.EVIDENCE_FILE).exists())


class RegistrationTests(unittest.TestCase):
    def test_only_future_plan_and_no_duplicate_registration(self):
        r = frozen(); policy = paper.policy_for(None, NOW)
        additions, skipped = paper.register_plans([r], [proof(r)], policy, [], {}, NOW)
        self.assertEqual(len(additions), 1)
        self.assertIsNone(additions[0]["cost_schedule"])
        self.assertEqual(skipped, {})
        repeated, _ = paper.register_plans([r], [proof(r)], policy, additions, {}, NOW + timedelta(minutes=1))
        self.assertEqual(repeated, [])

    def test_retrospective_target_is_ineligible(self):
        r = frozen(); policy = paper.policy_for(None, AFTER)
        additions, skipped = paper.register_plans([r], [proof(r)], policy, [], {}, AFTER)
        self.assertEqual(additions, [])
        self.assertEqual(skipped["target_started_or_registration_window_too_short"], 1)

    def test_first_issuance_only(self):
        r = frozen(); later = deepcopy(r)
        later.update(id="synthetic-reissue", issued_at="2026-11-05T12:30:00Z")
        additions, _ = paper.register_plans([later, r], [proof(r)], paper.policy_for(None, NOW), [], {}, NOW)
        self.assertEqual([p["forecast_id"] for p in additions], [r["id"]])

    def test_index_has_no_imaginary_share_execution(self):
        r = frozen(); r["symbol"] = "^GSPC"
        additions, skipped = paper.register_plans([r], [proof(r)], paper.policy_for(None, NOW), [], {}, NOW)
        self.assertEqual(additions, [])
        self.assertEqual(skipped["index_is_not_executable_share"], 1)

    def test_unpublished_future_record_is_not_enrolled(self):
        additions, skipped = paper.register_plans([frozen()], [], paper.policy_for(None, NOW), [], {}, NOW)
        self.assertEqual(additions, [])
        self.assertEqual(skipped["first_forecast_not_public_before_registration"], 1)

    def test_overlapping_capital_windows_not_double_counted(self):
        first = frozen(); second = deepcopy(first)
        second.update(id="synthetic-overlap", target={"start": "2026-11-05T14:45:00Z", "end": "2026-11-05T15:15:00Z"})
        additions, skipped = paper.register_plans([second, first], [proof(first), proof(second)], paper.policy_for(None, NOW), [], {}, NOW)
        self.assertEqual(len(additions), 1)
        self.assertEqual(skipped["overlapping_paper_target"], 1)

    def test_old_missing_baseline_is_not_created(self):
        r = frozen(); del r["frozen_baseline_probabilities"]
        additions, _ = paper.register_plans([r], [proof(r)], paper.policy_for(None, NOW), [], {}, NOW)
        self.assertIsNone(additions[0]["baseline_strategy"])

    def test_policy_change_and_future_policy_are_rejected(self):
        policy = paper.policy_for(None, NOW)
        bad = deepcopy(policy); bad["rules"]["maximum_shares"] = 10
        with self.assertRaisesRegex(ValueError, "immutable_paper_policy_mismatch"):
            paper.policy_for(bad, NOW)
        with self.assertRaisesRegex(ValueError, "immutable_paper_policy_mismatch"):
            paper.policy_for(policy, NOW - timedelta(seconds=1))

    def test_recomputed_hash_cannot_change_forecast_direction(self):
        p = plan(); p["strategy"] = "cash"
        p["id"] = paper.digest({key: value for key, value in p.items() if key != "id"})
        with self.assertRaisesRegex(ValueError, "paper_plan_disagrees"):
            paper.register_plans([frozen()], [proof(frozen())], paper.policy_for(None, NOW), [p], {}, NOW)

    def test_cost_schedule_must_exist_before_registration(self):
        costs = schedule(); costs["recorded_at"] = "2026-11-05T13:01:00Z"
        with self.assertRaisesRegex(ValueError, "cost_schedule_not_preregistered"):
            paper.register_plans([frozen()], [proof(frozen())], paper.policy_for(None, NOW), [], {"US": costs}, NOW)


class PaperEvidenceTests(unittest.TestCase):
    def test_saved_reference_gain_is_a_quote_based_loss(self):
        p = plan(); result = paper.evaluate_plan(p, [evidence(p)], AFTER)
        self.assertEqual(result["status"], "quote_based_paper_diagnostic")
        self.assertGreater((105 / 100 - 1) * 100, 0)  # Reference-price observation only.
        self.assertLess(result["strategy_return_pct"], (105 / 110 - 1) * 100)
        self.assertFalse(result["actual_fill_verified"])
        self.assertFalse(result["external_evidence_authenticated"])

    def test_bid_ask_fees_tax_and_explicit_slippage(self):
        p = plan(); result = paper.evaluate_plan(p, [evidence(p)], AFTER)
        expected_buy = 110 * 1.0005 * 1.001
        expected_sell = 105 * .9995 * .997
        self.assertAlmostEqual(result["strategy_return_pct"], (expected_sell / expected_buy - 1) * 100)
        self.assertEqual(result["frozen_baseline_return_pct"], 0)
        self.assertTrue(result["slippage_is_assumed"])
        self.assertFalse(result["actual_execution_return"])

    def test_no_evidence_does_not_manufacture_cash_success(self):
        p = plan(with_cost=False); result = paper.evaluate_plan(p, [], AFTER)
        self.assertEqual(result["status"], "missing_execution_evidence")
        self.assertNotIn("strategy_return_pct", result)
        self.assertIn("preregistered_cost_schedule_missing", result["blockers"])

    def test_website_proof_is_not_a_persons_receipt(self):
        p = plan(); e = evidence(p); e["human_receipt"] = proof(frozen())
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertIn("human_receipt_missing", result["blockers"])

    def test_late_receipt_cannot_buy_a_past_quote(self):
        p = plan(); e = evidence(p); e["human_receipt"]["received_at"] = "2026-11-05T14:31:00Z"
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertIn("human_receipt_after_target_start_or_before_publication", result["blockers"])

    def test_bad_first_entry_is_cancelled_without_better_replacement(self):
        p = plan(); e = evidence(p)
        e["quotes"][0]["ask_size"] = 0
        e["quotes"].insert(1, quote("2026-11-05T14:30:03Z", 99.9, 100))
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertEqual(result["status"], "entry_cancelled")
        self.assertIn("insufficient_quote_size", result["blockers"])
        self.assertNotIn("strategy_return_pct", result)

    def test_missing_exit_is_not_assumed_liquidation(self):
        p = plan(); e = evidence(p); e["quotes"].pop()
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertEqual(result["status"], "exit_unresolved")
        self.assertNotIn("strategy_return_pct", result)

    def test_postmarket_exit_does_not_become_regular_close(self):
        p = plan(); e = evidence(p); e["quotes"][1]["session"] = "after_hours"
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertEqual(result["status"], "exit_unresolved")
        self.assertIn("quote_venue_or_session_mismatch", result["blockers"])

    def test_different_venues_are_not_mixed(self):
        p = plan(); e = evidence(p); e["quotes"][1]["venue"] = "XNAS"
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertIn("entry_exit_venue_mismatch", result["blockers"])

    def test_stale_quote_is_rejected(self):
        p = plan(); e = evidence(p); e["quotes"][0]["received_at"] = "2026-11-05T14:30:20Z"
        self.assertIn("stale_quote", paper.evaluate_plan(p, [e], AFTER)["blockers"])

    def test_wrong_symbol_excessive_spread_and_ohlc_rejected(self):
        changes = [("symbol", "OTHER", "quote_identity_mismatch"),
                   ("ask", 120, "spread_above_preregistered_limit"),
                   ("kind", "historical_ohlc", "executable_quote_source_missing")]
        for field, value, expected in changes:
            with self.subTest(field=field):
                p = plan(); e = evidence(p); e["quotes"][0][field] = value
                self.assertIn(expected, paper.evaluate_plan(p, [e], AFTER)["blockers"])

    def test_future_and_duplicate_evidence_do_not_count(self):
        p = plan(); e = evidence(p)
        future = deepcopy(e); future["recorded_at"] = (AFTER + timedelta(seconds=1)).isoformat()
        self.assertIn("future_execution_evidence", paper.evaluate_plan(p, [future], AFTER)["blockers"])
        self.assertIn("duplicate_execution_evidence", paper.evaluate_plan(p, [e, e], AFTER)["blockers"])

    def test_costs_cannot_be_attached_after_plan_registration(self):
        p = plan(with_cost=False); e = evidence(p); e["cost_schedule"] = schedule()
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertIn("preregistered_cost_schedule_missing", result["blockers"])

    def test_quote_and_public_proof_cannot_postdate_evidence_record(self):
        p = plan(); e = evidence(p); e["recorded_at"] = "2026-11-05T14:40:00Z"
        self.assertIn("quote_not_recorded_before_evidence", paper.evaluate_plan(p, [e], AFTER)["blockers"])
        e = evidence(p); e["recorded_at"] = "2026-11-05T13:01:00Z"
        self.assertIn("plan_publication_proof_missing_or_late", paper.evaluate_plan(p, [e], AFTER)["blockers"])

    def test_nonfinite_price_cannot_generate_a_return(self):
        p = plan(); e = evidence(p); e["quotes"][0]["ask"] = float("nan")
        self.assertIn("finite_number_required", paper.evaluate_plan(p, [e], AFTER)["blockers"])

    def test_malformed_private_receipt_does_not_leak_through_error(self):
        p = plan(); e = evidence(p)
        e["human_receipt"]["received_at"] = "synthetic-private-identifier"
        result = paper.evaluate_plan(p, [e], AFTER)
        self.assertIn("invalid_evidence_schema", result["blockers"])
        self.assertNotIn("synthetic-private-identifier", json.dumps(result))


class IndependentReportTests(unittest.TestCase):
    def test_metric_arithmetic_and_direction_denominators(self):
        pairs = [("down", {"down": .8, "flat": .1, "up": .1}),
                 ("flat", {"down": .6, "flat": .3, "up": .1}),
                 ("up", {"down": .2, "flat": .2, "up": .6})]
        result = paper.metrics(pairs)
        self.assertEqual(result["confusion_matrix"], [[1, 0, 0], [1, 0, 0], [0, 0, 1]])
        self.assertEqual(result["correct"], 2)
        self.assertAlmostEqual(result["brier_loss"], (0.06 + .86 + .24) / 3)
        self.assertAlmostEqual(result["log_loss"], -math.log(.8 * .3 * .6) / 3)
        self.assertIsNone(result["directions"]["flat"]["precision"])
        self.assertEqual(result["directions"]["down"]["false_calls"], 1)

    def test_missing_candidate_is_not_backfilled_or_promoted(self):
        r = frozen()
        report = paper.compare_frozen([r], {"scored": 1, "rows": [{"id": r["id"], "actual": "down"}]}, AFTER)
        self.assertEqual(report["comparisons"]["adaptive"]["candidate"]["samples"], 0)
        self.assertEqual(report["comparisons"]["adaptive"]["missing_frozen_vector"], 1)
        self.assertEqual(report["comparisons"]["frozen_baseline"]["candidate"]["samples"], 1)
        self.assertEqual(report["promotions"], 0)
        self.assertEqual(report["timing_utility"], "not_proven")

    def test_candidate_uses_identical_incumbent_cohort_not_all_records(self):
        first = frozen(); first["id"] = "synthetic-paired"
        first["directional_specialists"] = {"candidates": {"balanced_linear": {
            "probabilities": {"down": .8, "flat": .1, "up": .1}, "direction": "down"}}}
        absent = frozen(); absent["id"] = "synthetic-unpaired"
        audit = {"scored": 2, "rows": [{"id": first["id"], "actual": "down"},
                                       {"id": absent["id"], "actual": "up"}]}
        report = paper.compare_frozen([first, absent], audit, AFTER)
        comparison = report["comparisons"]["balanced_linear"]
        self.assertEqual(comparison["candidate"]["samples"], 1)
        self.assertEqual(comparison["candidate"]["accuracy"], 1)
        self.assertEqual(comparison["incumbent_on_identical_cohort"]["accuracy"], 0)
        self.assertEqual(report["comparisons"]["active"]["candidate"]["accuracy"], .5)
        self.assertEqual(comparison["cohort_sha256"], paper.digest([first["id"]]))
        self.assertEqual(comparison["missing_frozen_vector"], 1)

    def test_repeat_run_preserves_originals_and_plan_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); r = frozen()
            inputs = {"stock-forecast-ledger.jsonl": json.dumps(r) + "\n",
                      "stock-forecast-outcomes.jsonl": "",
                      "stock-forecast-deliveries.jsonl": json.dumps(proof(r)) + "\n"}
            for name, content in inputs.items():
                (root / name).write_text(content)
            first = paper.run(root, NOW)
            before = {name: (root / name).read_bytes() for name in inputs}
            policy_bytes, plan_bytes = (root / paper.POLICY_FILE).read_bytes(), (root / paper.PLAN_FILE).read_bytes()
            second = paper.run(root, NOW + timedelta(minutes=1))
            self.assertEqual(first["registered_plans"], 1)
            self.assertEqual(second["new_plans"], 0)
            self.assertEqual(policy_bytes, (root / paper.POLICY_FILE).read_bytes())
            self.assertEqual(plan_bytes, (root / paper.PLAN_FILE).read_bytes())
            self.assertTrue(all((root / name).read_bytes() == content for name, content in before.items()))
            self.assertFalse((root / paper.EVIDENCE_FILE).exists())
            self.assertFalse((root / paper.COST_FILE).exists())
            self.assertFalse(second["after_cost_forward_edge_verified"])
            self.assertFalse(second["automatic_completion_notice"])
            self.assertEqual(second["status"], "not_proven")

    def test_new_paper_outputs_share_transaction_rollback(self):
        import stock_forecast_autopilot as controller
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); stage = root / "stage"; stage.mkdir()
            previous = {paper.POLICY_FILE: b"original-policy\n", paper.PLAN_FILE: b"original-plans\n"}
            for name, content in previous.items():
                (root / name).write_bytes(content)
            for name in paper.PAPER_OUTPUTS:
                (stage / name).write_bytes(b"synthetic-staged-output\n")
            original_copy = controller.shutil.copy2
            def fail_report_copy(source, target, *args, **kwargs):
                if Path(target).name == paper.REPORT_FILE:
                    Path(target).write_bytes(b"partial")
                    raise OSError("synthetic-paper-copy-failure")
                return original_copy(source, target, *args, **kwargs)
            with patch.object(controller.shutil, "copy2", side_effect=fail_report_copy):
                with self.assertRaisesRegex(OSError, "synthetic-paper-copy-failure"):
                    controller.commit_stage_with_rollback(root, stage)
            for name, content in previous.items():
                self.assertEqual((root / name).read_bytes(), content)
            self.assertFalse((root / paper.REPORT_FILE).exists())
            self.assertFalse((root / paper.SHADOW_FILE).exists())


if __name__ == "__main__":
    unittest.main()
