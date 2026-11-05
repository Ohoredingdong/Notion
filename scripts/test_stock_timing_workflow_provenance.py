"""Synthetic fail-closed controls for GitHub-triggered audit evidence provenance.

No generated fixture is market data or proof of prediction edge. The positive
test only validates alignment of one GitHub event and archived research output.
"""
from copy import deepcopy
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from stock_forecast_identity import (CODE_ROOT, RESOLVED, SourceIdentityError,
                                     execution_identity)

try:
    from audit_stock_timing_workflow_provenance import examine
except ImportError:
    examine = None


WORKFLOW = (Path(__file__).resolve().parents[1]
            / ".github/workflows/stock-forecast-independent-audit.yml")
FORECAST_WORKFLOW = (Path(__file__).resolve().parents[1]
                     / ".github/workflows/stock-forecasts.yml")
CONTROLLER_SCRIPT = (Path(__file__).resolve().parent / "stock_forecast_autopilot.py")
FORECAST_SCRIPT = (Path(__file__).resolve().parent / "run_stock_forecasts.py")
RUN = "41157151233"
SHA = "f9db984b97b070ceca198ac023667740aebc3497"
CHECKOUT_SHA = "c" * 40


def fixture():
    return (
        {"status": "research_cycle_verified",
         "version": "bounded-autopilot-1.0",
         "run_id": RUN, "source_commit": SHA,
         "generated_at": "2026-10-31T01:50:36.749289+00:00"},
        {"source_run_id": RUN,
         "generated_at": "2026-10-31T01:50:36.602632+00:00"},
        {"generated_at": "2026-10-31T01:50:36.602632+00:00"},
    )


def explicit_fixture(source=CHECKOUT_SHA, event=SHA):
    controller, forecast, learning = fixture()
    identity = {"event_commit": event, "source_commit": source,
                "source_identity_status": RESOLVED}
    controller.update(identity)
    forecast.update(identity)
    return controller, forecast, learning


def isolated_function(path, name, namespace):
    """Execute the real producer function without importing model libraries."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"),
         namespace)
    return namespace[name]


class UpstreamRunEvidenceBinding(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(examine, "the provenance checker does not yet exist")
        self.controller, self.forecast, self.learning = fixture()

    def check(self, run=RUN, sha=SHA):
        return examine(self.controller, self.forecast, self.learning, run, sha)

    def test_matched_event_and_main_snapshot(self):
        result = self.check()
        self.assertEqual(result["status"], "upstream_run_evidence_matched")
        self.assertEqual(result["errors"], [])

    def test_rejects_newer_main_snapshot_for_older_trigger(self):
        self.controller["run_id"] = "41157151234"
        self.forecast["source_run_id"] = "41157151234"
        self.assertIn("controller_run_id_mismatch", self.check()["errors"])

    def test_rejects_upstream_commit_mismatch(self):
        self.controller["source_commit"] = "0" * 40
        self.assertIn("controller_source_commit_mismatch", self.check()["errors"])

    def test_rejects_forecast_generated_from_other_run(self):
        self.forecast["source_run_id"] = "41157151234"
        self.assertIn("forecast_run_id_mismatch", self.check()["errors"])

    def test_rejects_missing_or_reordered_snapshot_times(self):
        self.learning.pop("generated_at")
        self.assertIn("missing_or_invalid_generation_time", self.check()["errors"])
        self.learning["generated_at"] = "2026-10-31T01:55:00+00:00"
        self.assertIn("snapshot_generation_order_mismatch", self.check()["errors"])

    def test_rejects_invalid_event_identity(self):
        self.assertIn("invalid_expected_run_id", self.check(run="").get("errors", []))
        self.assertIn("invalid_expected_head_sha", self.check(sha="bad").get("errors", []))
        self.assertIn("invalid_expected_head_sha", self.check(sha="0" * 40).get("errors", []))


class WorkflowIsolation(unittest.TestCase):
    def test_forecast_producer_keeps_latest_branch_checkout_for_queued_runs(self):
        workflow = FORECAST_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("- uses: actions/checkout@v4", workflow)
        checkout = workflow.split("- uses: actions/checkout@v4", 1)[1].split("- uses:", 1)[0]
        self.assertIn("ref: ${{ github.ref_name }}", checkout)
        self.assertNotIn("ref: ${{ github.sha }}", checkout)
        self.assertIn("fetch-depth: 0", checkout)

    def test_local_metadata_cannot_substitute_the_event_for_unknown_code(self):
        with tempfile.TemporaryDirectory() as dirname:
            identity = execution_identity(Path(dirname), {"GITHUB_SHA": SHA})
            controller, forecast, learning = fixture()
            controller.update(identity)
            forecast.update(identity)
            result = examine(controller, forecast, learning, RUN, SHA)
            self.assertEqual(identity["event_commit"], SHA)
            self.assertIsNone(identity["source_commit"])
            self.assertEqual(result["status"], "upstream_run_mismatch")
            self.assertIn("controller_source_identity_unverified", result["errors"])

    def test_event_only_read_only_provenance_step(self):
        s = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python scripts/audit_stock_timing_workflow_provenance.py", s)
        self.assertIn("github.event.workflow_run.id", s)
        self.assertIn("github.event.workflow_run.head_sha", s)
        self.assertIn("if: github.event_name == 'workflow_run'", s)
        self.assertIn("permissions:\n  contents: read", s)
        self.assertIn("python scripts/audit_stock_forecast_independent.py", s)
        self.assertIn("python scripts/audit_stock_timing_acceptance_guard.py", s)
        self.assertIn("  workflow_dispatch:", s)
        self.assertIn("  schedule:\n    - cron: '33 * * * *'", s)


class ExplicitEventCheckoutBinding(unittest.TestCase):
    def setUp(self):
        self.controller, self.forecast, self.learning = explicit_fixture()

    def check(self):
        return examine(self.controller, self.forecast, self.learning, RUN, SHA)

    def test_accepts_a_newer_checkout_without_relabelling_the_event(self):
        before = deepcopy((self.controller, self.forecast, self.learning))
        result = self.check()
        self.assertEqual(result["status"], "upstream_run_evidence_matched")
        self.assertEqual(result["event_commit"], SHA)
        self.assertEqual(result["source_commit"], CHECKOUT_SHA)
        self.assertEqual(result["identity_mode"], "event_and_checkout")
        self.assertEqual((self.controller, self.forecast, self.learning), before)

    def test_rejects_a_forged_event_even_with_valid_checkout_fields(self):
        self.controller["event_commit"] = self.forecast["event_commit"] = "d" * 40
        errors = self.check()["errors"]
        self.assertIn("controller_event_commit_mismatch", errors)
        self.assertIn("forecast_event_commit_mismatch", errors)

    def test_new_identity_missing_event_does_not_take_legacy_fallback(self):
        self.controller.pop("event_commit")
        self.controller["source_commit"] = SHA
        self.assertIn("invalid_controller_event_commit", self.check()["errors"])

    def test_rejects_invalid_or_missing_actual_source_identity(self):
        for value in (None, "bad", "0" * 40, True):
            with self.subTest(source=value):
                self.controller["source_commit"] = value
                self.assertIn("invalid_controller_source_commit", self.check()["errors"])

    def test_rejects_missing_forecast_identity_and_different_code_bundles(self):
        self.forecast["source_commit"] = "d" * 40
        self.assertIn("forecast_source_commit_mismatch", self.check()["errors"])
        for name in ("event_commit", "source_commit", "source_identity_status"):
            self.forecast.pop(name)
        errors = self.check()["errors"]
        self.assertIn("invalid_forecast_event_commit", errors)
        self.assertIn("invalid_forecast_source_commit", errors)
        self.assertIn("forecast_source_identity_unverified", errors)

    def test_unverified_local_metadata_cannot_satisfy_upstream_audit(self):
        self.controller["source_identity_status"] = "unverified"
        self.assertIn("controller_source_identity_unverified", self.check()["errors"])

    def test_historical_reports_retain_their_original_fallback_rule(self):
        old = fixture()
        before = deepcopy(old)
        result = examine(*old, RUN, SHA)
        self.assertEqual(result["status"], "upstream_run_evidence_matched")
        self.assertEqual(result["identity_mode"], "legacy_source_commit_event_fallback")
        self.assertEqual(old, before)
        old[0]["source_commit"] = CHECKOUT_SHA
        self.assertIn("controller_source_commit_mismatch",
                      examine(*old, RUN, SHA)["errors"])


class ExecutionIdentityTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def test_real_checkout_can_advance_past_its_initiating_event(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Local provenance fixture")
            self.git(root, "config", "user.email", "fixture@example.invalid")
            self.git(root, "commit", "-qm", "event fixture", "--allow-empty")
            event = self.git(root, "rev-parse", "HEAD")
            self.git(root, "commit", "-qm", "queued checkout fixture", "--allow-empty")
            checkout = self.git(root, "rev-parse", "HEAD")
            self.assertNotEqual(event, checkout)
            identity = execution_identity(root, {"GITHUB_ACTIONS": "true", "GITHUB_SHA": event})
            self.assertEqual(identity, {"event_commit": event, "source_commit": checkout,
                                        "source_identity_status": RESOLVED})
            report = examine(*explicit_fixture(checkout, event), RUN, event)
            self.assertEqual(report["status"], "upstream_run_evidence_matched")

    def test_non_git_local_fixture_is_explicitly_unverified_and_not_written(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            identity = execution_identity(root, {})
            self.assertIsNone(identity["event_commit"])
            self.assertIsNone(identity["source_commit"])
            self.assertEqual(identity["source_identity_status"], "unverified")
            self.assertEqual(list(root.iterdir()), [])

    def test_ci_without_a_resolvable_code_checkout_fails_closed(self):
        with tempfile.TemporaryDirectory() as dirname:
            with self.assertRaisesRegex(SourceIdentityError, "ci_code_checkout_identity_unavailable"):
                execution_identity(Path(dirname), {"GITHUB_ACTIONS": "true", "GITHUB_SHA": SHA})
            self.assertEqual(list(Path(dirname).iterdir()), [])

    def test_ci_requires_a_valid_event_before_trying_git(self):
        with patch("stock_forecast_identity._checked_out_commit") as git:
            for event in (None, "bad", "0" * 40):
                with self.subTest(event=event), self.assertRaisesRegex(
                        SourceIdentityError, "ci_event_commit_missing_or_invalid"):
                    execution_identity(environ={"GITHUB_ACTIONS": "true", "GITHUB_SHA": event})
            git.assert_not_called()

    def test_default_code_root_is_the_script_checkout(self):
        with patch("stock_forecast_identity._checked_out_commit", return_value=CHECKOUT_SHA) as git:
            self.assertEqual(execution_identity(environ={})["source_commit"], CHECKOUT_SHA)
            git.assert_called_once_with(CODE_ROOT)


class ProducerPreflightTests(unittest.TestCase):
    def test_forecast_identity_failure_precedes_readers_collectors_and_writes(self):
        for function in ("process", "run"):
            with self.subTest(function=function), tempfile.TemporaryDirectory() as dirname:
                root = Path(dirname) / "not_created"
                reader, collector = Mock(), Mock()
                namespace = {"Path": Path, "execution_identity": execution_identity,
                             "learning": SimpleNamespace(load_state=reader), "collect": collector}
                producer = isolated_function(FORECAST_SCRIPT, function, namespace)
                with patch("stock_forecast_identity.CODE_ROOT", Path(dirname)), \
                        patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_SHA": SHA}):
                    with self.assertRaisesRegex(SourceIdentityError, "ci_code_checkout_identity_unavailable"):
                        producer(root=root) if function == "run" else producer(("SYNTH", "Synthetic", "US"), "daily")
                reader.assert_not_called()
                collector.assert_not_called()
                self.assertFalse(root.exists())

    def test_actual_forecast_process_attaches_identity_without_rewriting_prediction_values(self):
        identity = {"event_commit": SHA, "source_commit": CHECKOUT_SHA,
                    "source_identity_status": RESOLVED}
        received = datetime(2026, 11, 1, tzinfo=timezone.utc)
        bar = SimpleNamespace(start=received, open=11, high=12, low=10, close=11.5)
        bars = SimpleNamespace(itertuples=lambda: iter([bar]))
        prediction = {"id": "synthetic-existing-id", "status": "research_prediction",
                      "issued_at": "2026-11-01T00:00:01+00:00",
                      "received_at": received.isoformat(), "price": 11.5,
                      "target": {"start": "2026-11-02T00:00:00+00:00"}}
        namespace = {"execution_identity": Mock(return_value=identity), "os": os,
                     "collect": Mock(return_value=(bars, received)),
                     "fit_model": Mock(return_value={"baseline": {}}),
                     "directions": SimpleNamespace(fit=Mock(return_value={})),
                     "learning": SimpleNamespace(pdict=Mock(return_value={})),
                     "make_prediction": Mock(return_value=deepcopy(prediction)),
                     "digest": Mock(return_value="synthetic-history-digest"),
                     "datetime": datetime, "UTC": timezone.utc}
        producer = isolated_function(FORECAST_SCRIPT, "process", namespace)
        with patch.dict(os.environ, {"GITHUB_RUN_ID": RUN}):
            record, history = producer(("SYNTH", "Synthetic-only", "US"), "daily")
        self.assertIs(history, bars)
        for key, value in prediction.items():
            self.assertEqual(record[key], value, key)
        for key, value in identity.items():
            self.assertEqual(record[key], value, key)
        self.assertEqual(record["source_run_id"], RUN)
        namespace["fit_model"].assert_called_once_with(bars, "daily")

    def test_controller_identity_failure_precedes_model_imports_and_writes(self):
        import stock_forecast_autopilot as controller
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname) / "not_created"
            pipeline, clock = Mock(), Mock()
            with patch("stock_forecast_identity.CODE_ROOT", Path(dirname)), \
                    patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_SHA": SHA}), \
                    patch.object(controller, "read") as reader, \
                    patch.dict(sys.modules, {"run_stock_forecasts": None}):
                with self.assertRaisesRegex(SourceIdentityError, "ci_code_checkout_identity_unavailable"):
                    controller.run(root=root, pipeline=pipeline, clock=clock)
                reader.assert_not_called()
            pipeline.assert_not_called()
            clock.assert_not_called()
            self.assertFalse(root.exists())

    def test_successful_controller_archives_both_identities_in_new_output_only(self):
        import stock_forecast_autopilot as controller
        fixed = datetime(2026, 11, 1, tzinfo=timezone.utc)
        identity = {"event_commit": SHA, "source_commit": CHECKOUT_SHA,
                    "source_identity_status": RESOLVED}
        model = SimpleNamespace(process=lambda *_: ({
            "symbol": "SYNTH", "market": "US", "mode": "daily", "status": "no_call",
            "reason": "insufficient_regular_session_time"}, object()))

        def pipeline(root, processor):
            processor(("SYNTH", "Synthetic-only", "US"), "daily")
            for name in controller.CORE_OUTPUTS:
                if name.endswith(".jsonl"):
                    (root / name).touch()
            controller.write(root / "stock-direction-forecast.json", {"records": []})
            controller.write(root / "stock-forecast-learning-state.json", {"training_updates": 0})
            controller.write(root / "stock-forecast-learning.json", {
                "overall": {"samples": 0, "correct": 0}, "learning": {"training_updates": 0}})

        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            old = b'{"id":"old-synthetic-row","source_commit":"legacy-label"}\n'
            (root / "stock-forecast-ledger.jsonl").write_bytes(old)
            with patch.object(controller, "execution_identity", return_value=identity), \
                    patch.object(controller, "verify_stage", return_value={
                        "status": "ledger_arithmetic_consistent", "scored": 0, "correct": 0}), \
                    patch.dict(sys.modules, {"run_stock_forecasts": model,
                                           "stock_forecast_cascade": SimpleNamespace(RECIPE={"synthetic_only": True})}), \
                    patch.dict(os.environ, {"GITHUB_RUN_ID": RUN}):
                report = controller.run(root=root, pipeline=pipeline, clock=lambda: fixed)
            self.assertEqual(report["status"], "research_cycle_verified")
            saved = json.loads((root / controller.REPORT).read_text())
            for key, value in identity.items():
                self.assertEqual(saved[key], value, key)
            self.assertEqual((root / "stock-forecast-ledger.jsonl").read_bytes(), old)


if __name__ == "__main__":
    unittest.main()
