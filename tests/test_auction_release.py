"""Local-only release integrity checks; no remote Git or network requests."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/auction_release.py"
SPEC = importlib.util.spec_from_file_location("auction_release", SCRIPT)
release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release
SPEC.loader.exec_module(release)


class AuctionReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="auction release tests ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "site root"
        self.source = self.root / "_auction"
        self.bundle = self.base / "verified bundle"
        self.files = {
            "auction-study.html": b"<!doctype html><title>Auction fixture</title>",
            "assets/auction-study.js": b"window.auctionFixture = true;\n",
            "assets/auction-study.css": b"body{color:#123}\n",
            "assets/auction-study-model.js": b"window.fixtureModel = {};\n",
            "assets/auction-study-format.js": b"window.fixtureFormat = {};\n",
            "assets/auction-study-simulation.js": b"window.fixturePractice = {};\n",
            "assets/auction-practice/example image.png": b"\x89PNG\r\nfixture\x00bytes",
        }
        for name, body in self.files.items():
            self.write(self.source / name, body)
            self.write(self.root / name, b"old served " + body)
        self.write(self.root / "financial-data.json", b'{"keep":"latest financial data"}\n')
        self.write(self.root / "assets/other-widget.js", b"do not touch\n")
        self.git("init", "-q")
        self.git("config", "user.name", "Release Fixture")
        self.git("config", "user.email", "release-fixture@example.invalid")
        self.commit("initial fixture")
        self.sha = self.git("rev-parse", "HEAD")
        release.package(self.source, self.bundle, self.sha)

    @staticmethod
    def write(path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args],
                                check=True, capture_output=True, text=True)
        return result.stdout.strip()

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)

    def snapshot(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob("*")
                if path.is_file() and ".git" not in path.relative_to(self.root).parts}

    def manifest(self):
        return json.loads((self.bundle / release.MANIFEST).read_bytes())

    def rewrite_manifest(self, manifest):
        (self.bundle / release.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    def test_package_manifest_and_promoted_bytes_are_identical_and_unrelated_files_survive(self):
        bundle = release.verify_bundle(self.bundle)
        self.assertEqual(bundle.contents, self.files)
        self.assertEqual(bundle.manifest["source_sha"], self.sha)
        self.assertEqual(set(bundle.manifest["files"]), set(self.files))
        before = self.snapshot()
        release.promote(self.bundle, self.root)
        for name, body in self.files.items():
            self.assertEqual((self.root / name).read_bytes(), body)
        self.assertEqual((self.root / release.MANIFEST).read_bytes(), bundle.manifest_bytes)
        self.assertEqual((self.root / "financial-data.json").read_bytes(), before["financial-data.json"])
        self.assertEqual((self.root / "assets/other-widget.js").read_bytes(), before["assets/other-widget.js"])
        for name, body in self.files.items():
            self.assertEqual((self.source / name).read_bytes(), body)
        release.check_public(self.root)

    def test_tampered_bundle_is_rejected_before_any_root_change(self):
        before = self.snapshot()
        (self.bundle / "assets/auction-study.js").write_bytes(b"tampered")
        with self.assertRaisesRegex(release.ReleaseError, "hash mismatch"):
            release.promote(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)

    def test_manifest_rejects_traversal_absolute_backslash_and_malformed_sha(self):
        original = self.manifest()
        for bad in ("../financial-data.json", "/tmp/auction-study.html", "assets/../auction-study.js",
                    "assets\\auction-study.js", "assets//auction-study.js"):
            with self.subTest(path=bad):
                value = json.loads(json.dumps(original))
                value["files"][bad] = "0" * 64
                self.rewrite_manifest(value)
                with self.assertRaises(release.ReleaseError):
                    release.verify_bundle(self.bundle)
        for bad in ("main", "0" * 39, "g" * 40, None):
            with self.subTest(source_sha=bad):
                value = json.loads(json.dumps(original))
                value["source_sha"] = bad
                self.rewrite_manifest(value)
                with self.assertRaises(release.ReleaseError):
                    release.verify_bundle(self.bundle)

    def test_duplicate_manifest_keys_and_missing_required_runtime_are_rejected(self):
        (self.bundle / release.MANIFEST).write_text('{"version":1,"version":1}', encoding="utf-8")
        with self.assertRaisesRegex(release.ReleaseError, "Duplicate"):
            release.verify_bundle(self.bundle)
        shutil.rmtree(self.bundle)
        (self.source / "assets/auction-study-format.js").unlink()
        with self.assertRaisesRegex(release.ReleaseError, "required"):
            release.package(self.source, self.bundle, self.sha)
        self.assertFalse(self.bundle.exists())

    def test_unlisted_bundle_files_and_unapproved_source_files_are_rejected(self):
        before = self.snapshot()
        extra = self.bundle / "financial-data.json"
        extra.write_bytes(b"must not publish")
        with self.assertRaisesRegex(release.ReleaseError, "unlisted"):
            release.promote(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)
        self.write(self.source / "assets/foreign-widget.js", b"not auction runtime")
        with self.assertRaisesRegex(release.ReleaseError, "Unapproved"):
            release.package(self.source, self.base / "other bundle", self.sha)

    def test_source_and_bundle_symlinks_are_rejected(self):
        leaf = self.source / "assets/auction-study-model.js"
        outside = self.base / "outside.js"
        outside.write_bytes(leaf.read_bytes())
        leaf.unlink()
        leaf.symlink_to(outside)
        with self.assertRaisesRegex(release.ReleaseError, "Symlink"):
            release.package(self.source, self.base / "linked bundle", self.sha)
        bundled = self.bundle / "assets/auction-study-model.js"
        bundled.unlink()
        bundled.symlink_to(outside)
        with self.assertRaisesRegex(release.ReleaseError, "Symlink"):
            release.verify_bundle(self.bundle)

    def test_source_and_destination_parent_symlinks_are_rejected_before_writes(self):
        original_html = (self.root / "auction-study.html").read_bytes()
        original_assets = self.root / "assets"
        moved = self.base / "real assets"
        original_assets.rename(moved)
        original_assets.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(release.ReleaseError, "Symlink"):
            release.promote(self.bundle, self.root)
        self.assertEqual((self.root / "auction-study.html").read_bytes(), original_html)
        self.assertFalse((self.root / release.MANIFEST).exists())
        source_assets = self.source / "assets"
        source_assets.rename(self.base / "real source assets")
        source_assets.symlink_to(self.base / "real source assets", target_is_directory=True)
        with self.assertRaisesRegex(release.ReleaseError, "Symlink"):
            release.package(self.source, self.base / "linked parent bundle", self.sha)

    def test_financial_only_head_advance_keeps_source_compatible(self):
        self.write(self.root / "financial-data.json", b'{"keep":"newer financial data"}\n')
        self.commit("financial only")
        self.assertNotEqual(self.git("rev-parse", "HEAD"), self.sha)
        release.check_source(release.verify_bundle(self.bundle), self.root)
        release.promote(self.bundle, self.root)
        self.assertEqual((self.root / "financial-data.json").read_bytes(), b'{"keep":"newer financial data"}\n')

    def test_newer_auction_source_rejects_old_promotion_without_changing_served_files(self):
        self.write(self.source / "assets/auction-study.js", b"newer canonical source\n")
        self.commit("new auction source")
        before = self.snapshot()
        with self.assertRaisesRegex(release.ReleaseError, "source changed"):
            release.check_source(release.verify_bundle(self.bundle), self.root)
        with self.assertRaisesRegex(release.ReleaseError, "source changed"):
            release.promote(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)

    def test_missing_source_tree_or_unknown_commit_cannot_bypass_source_binding(self):
        shutil.rmtree(self.source)
        self.commit("remove canonical fixture")
        with self.assertRaises(release.ReleaseError):
            release.check_source(release.verify_bundle(self.bundle), self.root)
        self.git("checkout", "-q", self.sha)
        value = self.manifest()
        value["source_sha"] = "0" * 40
        self.rewrite_manifest(value)
        with self.assertRaises(release.ReleaseError):
            release.check_source(release.verify_bundle(self.bundle), self.root)

    def test_failed_atomic_replacement_rolls_back_earlier_replacements(self):
        before = self.snapshot()
        replace = os.replace
        calls = 0
        def fail_once(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected replacement failure")
            return replace(source, destination)
        with patch.object(release.os, "replace", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "injected"):
                release.promote(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)

    def test_check_public_allows_other_widgets_but_rejects_known_runtime_tampering(self):
        release.promote(self.bundle, self.root)
        self.write(self.root / "another-widget.json", b"other site content")
        release.check_public(self.root)
        self.write(self.root / "assets/auction-study-model.js", b"unverified manual edit")
        with self.assertRaisesRegex(release.ReleaseError, "hash mismatch"):
            release.check_public(self.root)

    def test_legacy_public_manifest_is_valid_without_formatter_but_new_bundles_still_require_it(self):
        legacy = self.manifest()
        del legacy["files"]["assets/auction-study-format.js"]
        for name, body in self.files.items():
            if name != "assets/auction-study-format.js":
                self.write(self.root / name, body)
        (self.root / "assets/auction-study-format.js").unlink()
        self.write(self.root / release.MANIFEST, json.dumps(legacy).encode())
        verified = release.check_public(self.root)
        self.assertNotIn("assets/auction-study-format.js", verified.contents)
        self.rewrite_manifest(legacy)
        (self.bundle / "assets/auction-study-format.js").unlink()
        with self.assertRaisesRegex(release.ReleaseError, "required"):
            release.verify_bundle(self.bundle)

    def test_unlisted_existing_runtime_is_preserved_and_blocks_invalid_publication(self):
        extra = self.root / "assets/auction-study-retained.js"
        self.write(extra, b"retained old auction asset")
        before = self.snapshot()
        with self.assertRaisesRegex(release.ReleaseError, "must stay"):
            release.promote(self.bundle, self.root)
        self.assertEqual(self.snapshot(), before)
        extra.unlink()
        release.promote(self.bundle, self.root)
        self.write(extra, b"unlisted allowed runtime")
        with self.assertRaisesRegex(release.ReleaseError, "unlisted"):
            release.check_public(self.root)

    def test_cli_supports_paths_with_spaces_and_preserves_failure_exit_status(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "verify", "--bundle", str(self.bundle)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write(self.bundle / "assets/auction-study.js", b"tampered")
        result = subprocess.run([sys.executable, str(SCRIPT), "verify", "--bundle", str(self.bundle)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("hash mismatch", result.stderr)

    def test_public_verification_checks_all_bytes_manifest_query_and_summary_with_bounded_retry(self):
        bundle = release.verify_bundle(self.bundle)
        payloads = {**bundle.contents, release.MANIFEST: bundle.manifest_bytes}
        calls = []
        class Response:
            status = 200
            def __init__(self, body): self.body = io.BytesIO(body)
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read1(self, size): return self.body.read(size)
        class Opener:
            def open(inner, request, timeout):
                calls.append((request.full_url, timeout))
                parsed = urlsplit(request.full_url)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parse_qs(parsed.query), {"SOURCE_SHA": [self.sha]})
                name = unquote(parsed.path.removeprefix("/Notion/"))
                return Response(b"stale" if len(calls) == 1 else payloads[name])
        report = self.base / "step summary.md"
        with patch.object(release, "build_opener", return_value=Opener()), \
                patch.object(release.time, "sleep") as sleep, \
                patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(report)}), \
                patch("sys.stdout", new_callable=io.StringIO):
            release.verify_public(self.bundle, "https://example.invalid/Notion", attempts=2, delay=0)
        self.assertEqual(len(calls), len(payloads) + 1)
        self.assertTrue(any("example%20image.png" in address for address, _ in calls))
        self.assertTrue(all(0 < timeout <= 15 for _, timeout in calls))
        sleep.assert_called_once_with(0)
        self.assertIn("VERIFIED_PUBLIC_AUCTION_RELEASE " + self.sha, report.read_text())

    def test_public_verification_rejects_insecure_urls_and_reports_a_real_deadline_failure(self):
        for url in ("http://example.invalid/Notion", "https://user:pass@example.invalid/Notion",
                    "https://example.invalid/Notion?release=x"):
            with self.subTest(url=url), self.assertRaises(release.ReleaseError):
                release.verify_public(self.bundle, url)
        with self.assertRaises(release.ReleaseError):
            release.HTTPSRedirectsOnly().redirect_request(None, None, 302, "", {}, "http://example.invalid")
        with patch.object(release, "build_opener") as opener, \
                patch.object(release.time, "monotonic", side_effect=[0, 2, 2]), \
                patch("sys.stdout", new_callable=io.StringIO), \
                self.assertRaisesRegex(release.ReleaseError, "deadline exceeded"):
            release.verify_public(self.bundle, "https://example.invalid/Notion", max_seconds=1)
        opener.return_value.open.assert_not_called()

    def test_public_response_stream_is_size_bounded_and_rechecks_the_total_deadline(self):
        self.assertEqual(release.public_body(io.BytesIO(b"oversized"), 2, float("inf")), b"ove")
        now = [0]
        class SlowStream:
            def read1(self, size):
                now[0] += 2
                return b"x"
        with patch.object(release.time, "monotonic", side_effect=lambda: now[0]):
            with self.assertRaisesRegex(TimeoutError, "deadline exceeded"):
                release.public_body(SlowStream(), 1000, 1)


if __name__ == "__main__":
    unittest.main()
