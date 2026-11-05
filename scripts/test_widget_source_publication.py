"""Synthetic source bindings and real local-git publication races only.

No production source, report, history or remote service is mutated by these tests.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import publish_widget_data as publisher

RAW = publisher.OPPORTUNITY_SOURCE
CASES = "stock-investment-cases.json"
SUMMARY = "stock-investment-cases-summary.json"
T0 = "2026-01-01T00:00:00Z"
T1 = "2026-01-02T00:00:00Z"
T2 = "2026-01-03T00:00:00Z"


def wire(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def raw(stamp=T0, price=100):
    return wire({"generated_at": stamp, "companies": [{"symbol": "SYNTHETIC", "price": price}]})


def derived(source, stamp=T2, with_hash=True):
    result = {"generated_at": stamp, "source_generated_at": json.loads(source)["generated_at"],
              "companies": [], "synthetic_test_only": True}
    if with_hash:
        result["source_sha256"] = hashlib.sha256(source).hexdigest()
    return wire(result)


def command(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, check=True).stdout.strip()


class CandidateBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / RAW).write_bytes(raw())

    def test_same_source_reports_and_generation_only_summary_are_allowed(self):
        publisher.verify_source_bindings(self.root, {
            CASES: derived(raw()), SUMMARY: derived(raw(), with_hash=False)})

    def test_fresher_report_cannot_bind_to_older_raw(self):
        (self.root / RAW).write_bytes(raw(T1, 200))
        with self.assertRaisesRegex(RuntimeError, "publication_source_generation_mismatch"):
            publisher.verify_source_bindings(self.root, {CASES: derived(raw(), T2)})

    def test_changed_content_with_same_generation_requires_exact_byte_hash(self):
        (self.root / RAW).write_bytes(raw(T0, 200))
        with self.assertRaisesRegex(RuntimeError, "publication_source_hash_mismatch"):
            publisher.verify_source_bindings(self.root, {CASES: derived(raw())})

    def test_full_report_cannot_omit_its_existing_source_hash(self):
        with self.assertRaisesRegex(RuntimeError, "publication_source_hash_mismatch"):
            publisher.verify_source_bindings(self.root, {CASES: derived(raw(), with_hash=False)})

    def test_coherent_bundle_uses_candidate_raw_even_if_derived_appears_first(self):
        source = raw(T1, 200)
        publisher.verify_source_bindings(self.root, {
            CASES: derived(source), SUMMARY: derived(source, with_hash=False), RAW: source})
        self.assertEqual((self.root / RAW).read_bytes(), raw())

    def test_summary_mismatch_and_optional_wrong_hash_are_blocked(self):
        for output in (derived(raw(T1), with_hash=False),
                       wire({"source_generated_at": T0, "source_sha256": "0" * 64})):
            with self.subTest(output=output):
                with self.assertRaisesRegex(RuntimeError, "publication_source_.*_mismatch"):
                    publisher.verify_source_bindings(self.root, {SUMMARY: output})

    def test_raw_only_update_does_not_require_untouched_downstream_reports(self):
        (self.root / CASES).write_bytes(derived(raw(T0)))
        publisher.verify_source_bindings(self.root, {RAW: raw(T1, 200)})

    def test_audit_only_and_unrelated_widgets_do_not_infer_nested_dependencies(self):
        (self.root / RAW).unlink()
        publisher.verify_source_bindings(self.root, {
            "stock-radar-accuracy-audit.json": wire({"source": {"opportunity_generated_at": T0}}),
            "stock-radar-health.json": wire({"source": {"raw": {"generated_at": T0}}}),
            "news-link-data.json": wire({"generated_at": T2, "items": []})})

    def test_known_dependency_cannot_be_missing(self):
        (self.root / RAW).unlink()
        with self.assertRaisesRegex(RuntimeError, "publication_source_missing"):
            publisher.verify_source_bindings(self.root, {CASES: derived(raw())})

    def test_current_direct_dependency_schemas_are_explicit(self):
        self.assertEqual(len(publisher.OPPORTUNITY_BINDINGS), 15)
        for name, (generation_field, require_hash) in publisher.OPPORTUNITY_BINDINGS.items():
            value = {generation_field: T0}
            if require_hash:
                value["source_sha256"] = hashlib.sha256(raw()).hexdigest()
            with self.subTest(file=name):
                publisher.verify_source_bindings(self.root, {name: wire(value)})


class SourcePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.remote = self.root / "remote.git"
        self.local, self.other = self.root / "local", self.root / "other"
        command(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        command(self.root, "clone", str(self.remote), str(self.local))
        command(self.local, "config", "user.name", "Source binding test")
        command(self.local, "config", "user.email", "test@example.invalid")
        (self.local / RAW).write_bytes(raw())
        (self.local / CASES).write_bytes(derived(raw(), T0))
        (self.local / SUMMARY).write_bytes(derived(raw(), T0, with_hash=False))
        (self.local / "stock-entry-ledger.jsonl").write_text('{"id":"original","value":1}\n')
        command(self.local, "add", ".")
        command(self.local, "commit", "-m", "synthetic initial snapshot")
        command(self.local, "push", "origin", "main")
        command(self.root, "clone", str(self.remote), str(self.other))
        command(self.other, "config", "user.name", "Concurrent source test")
        command(self.other, "config", "user.email", "other@example.invalid")

    def remote_json(self, name, branch="main"):
        return json.loads(command(self.remote, "show", branch + ":" + name))

    def advance_source(self, stamp=T1, price=200):
        (self.other / RAW).write_bytes(raw(stamp, price))
        command(self.other, "add", RAW)
        command(self.other, "commit", "-m", "synthetic concurrent raw update")
        command(self.other, "push", "origin", "main")

    def test_old_checkout_raw_is_not_used_after_remote_source_advances(self):
        self.advance_source()
        before = command(self.remote, "rev-parse", "main")
        (self.local / CASES).write_bytes(derived(raw(), T2))
        # RAW is requested but unchanged versus checkout HEAD, so it is absent
        # from the actual payload. The candidate must use current remote RAW.
        with self.assertRaisesRegex(RuntimeError, "publication_source_generation_mismatch"):
            publisher.publish(self.local, [RAW, CASES], "synthetic stale derived report")
        self.assertEqual(command(self.remote, "rev-parse", "main"), before)
        self.assertEqual(self.remote_json(CASES)["generated_at"], T0)

    def test_same_source_publication_preserves_concurrent_unrelated_work(self):
        (self.other / "unrelated.txt").write_text("preserve independent work")
        command(self.other, "add", "unrelated.txt")
        command(self.other, "commit", "-m", "synthetic unrelated update")
        command(self.other, "push", "origin", "main")
        (self.local / CASES).write_bytes(derived(raw(), T2))
        publisher.publish(self.local, [CASES], "synthetic same-source report")
        self.assertEqual(self.remote_json(CASES)["generated_at"], T2)
        self.assertEqual(command(self.remote, "show", "main:unrelated.txt"), "preserve independent work")

    def test_full_coherent_bundle_and_append_only_entry_ledger_publish_together(self):
        source = raw(T1, 200)
        (self.local / RAW).write_bytes(source)
        (self.local / CASES).write_bytes(derived(source, T2))
        (self.local / SUMMARY).write_bytes(derived(source, T2, with_hash=False))
        (self.local / "stock-entry-ledger.jsonl").write_text('{"id":"new","value":2}\n')
        publisher.publish(self.local, [CASES, SUMMARY, RAW], "synthetic coherent bundle",
                          append_ledgers=("stock-entry-ledger.jsonl",))
        self.assertEqual(self.remote_json(RAW)["generated_at"], T1)
        self.assertEqual(self.remote_json(CASES)["source_sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(self.remote_json(SUMMARY)["source_generated_at"], T1)
        ledger = [json.loads(line) for line in command(self.remote, "show", "main:stock-entry-ledger.jsonl").splitlines()]
        self.assertEqual([row["id"] for row in ledger], ["original", "new"])

    def test_newer_remote_raw_preserves_entire_bundle_not_only_raw_file(self):
        self.advance_source(T2, 300)
        before = command(self.remote, "rev-parse", "main")
        source = raw(T1, 200)
        (self.local / RAW).write_bytes(source)
        (self.local / CASES).write_bytes(derived(source, "2026-01-04T00:00:00Z"))
        self.assertIsNone(publisher.publish(self.local, [CASES, RAW], "synthetic obsolete bundle"))
        self.assertEqual(command(self.remote, "rev-parse", "main"), before)
        self.assertEqual(self.remote_json(RAW)["generated_at"], T2)
        self.assertEqual(self.remote_json(CASES)["generated_at"], T0)

    def test_source_guard_is_rechecked_after_a_real_push_race(self):
        (self.local / CASES).write_bytes(derived(raw(), T2))
        original_git, raced = publisher.git, []
        def race(root, *args, **kwargs):
            if args[:1] == ("push",) and not raced:
                raced.append(True)
                self.advance_source()
            return original_git(root, *args, **kwargs)
        with patch.object(publisher, "git", side_effect=race), patch.object(publisher.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "publication_source_generation_mismatch"):
                publisher.publish(self.local, [CASES], "synthetic racing report", attempts=3)
        self.assertEqual(raced, [True])
        self.assertEqual(self.remote_json(RAW)["generated_at"], T1)
        self.assertEqual(self.remote_json(CASES)["generated_at"], T0)

    def test_explicit_branch_uses_that_branch_source_and_preserves_main(self):
        branch = "fix/synthetic-source-test"
        command(self.other, "checkout", "-b", branch)
        (self.other / RAW).write_bytes(raw(T1, 200))
        command(self.other, "add", RAW)
        command(self.other, "commit", "-m", "synthetic branch raw")
        command(self.other, "push", "origin", branch)
        before = command(self.remote, "rev-parse", "main")
        (self.local / CASES).write_bytes(derived(raw(T1, 200), T2))
        publisher.publish(self.local, [CASES], "synthetic branch report", branch=branch)
        self.assertEqual(command(self.remote, "rev-parse", "main"), before)
        self.assertEqual(self.remote_json(CASES, branch)["source_generated_at"], T1)


if __name__ == "__main__":
    unittest.main()
