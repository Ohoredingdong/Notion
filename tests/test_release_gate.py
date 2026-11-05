"""Exercise production denials and public artifacts using disposable Git repos."""
import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("release_gate", Path(__file__).resolve().parents[1] / "scripts/release_gate.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class ReleaseAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.policy = {"enabled": True}
        self.evidence = {"candidate_sha": self.sha, "tested_sha": self.sha}

    def authorize(self, **kwargs):
        args = dict(policy=self.policy, candidate=self.sha, main_sha=self.sha,
                    confirmation="DEPLOY " + self.sha, dry_run=False,
                    pages_config={"build_type": "workflow"}, evidence=self.evidence)
        args.update(kwargs)
        return gate.authorize(**args)

    def test_all_explicit_conditions_allow_exact_sha(self):
        self.assertTrue(self.authorize()["authorized"])

    def test_machine_check_flag_returns_json_without_authorizing_publish(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = gate.main(["--check", "--candidate", self.sha, "--main-sha", self.sha])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue()), {"candidate_sha": self.sha})

    def test_repository_policy_is_disabled_by_default(self):
        policy = gate.load_policy(Path(__file__).resolve().parents[1] / ".github/release-policy.json")
        self.assertIs(policy["enabled"], False)
        with self.assertRaisesRegex(gate.ReleaseDenied, "disabled"):
            self.authorize(policy=policy)

    def test_dry_run_cannot_authorize_production(self):
        with self.assertRaisesRegex(gate.ReleaseDenied, "Dry run"):
            self.authorize(dry_run=True)

    def test_sha_must_be_full_lowercase_hex(self):
        for value in ("main", "a" * 7, "g" * 40, "A" * 40, "a" * 40 + ";false"):
            with self.subTest(value=value), self.assertRaises(gate.ReleaseDenied):
                gate.check_candidate(value, value)

    def test_stale_main_fails_without_resetting_any_branch(self):
        with self.assertRaisesRegex(gate.ReleaseDenied, "Main advanced"):
            self.authorize(main_sha="b" * 40)

    def test_checkout_must_match_candidate(self):
        with self.assertRaisesRegex(gate.ReleaseDenied, "Checked-out"):
            gate.check_candidate(self.sha, self.sha, "b" * 40)

    def test_confirmation_cannot_be_approximate(self):
        for text in ("DEPLOY", self.sha, "deploy " + self.sha, "DEPLOY " + self.sha + " "):
            with self.subTest(text=text), self.assertRaisesRegex(gate.ReleaseDenied, "confirmation"):
                self.authorize(confirmation=text)

    def test_legacy_or_unobserved_pages_requires_approved_migration(self):
        for config in ({"build_type": "legacy"}, {}, {"build_type": None}):
            with self.subTest(config=config), self.assertRaisesRegex(gate.ReleaseDenied, "separately approved"):
                self.authorize(pages_config=config)

    def test_artifact_and_tested_sha_must_match_candidate(self):
        for field in ("candidate_sha", "tested_sha"):
            with self.subTest(field=field), self.assertRaisesRegex(gate.ReleaseDenied, "exact tested"):
                self.authorize(evidence={**self.evidence, field: "b" * 40})


class PublicArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="release-gate-test-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / "repo"
        self.root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "tests@example.invalid")
        self.git("config", "user.name", "Release gate tests")
        self.write("index.html", "<html>existing widget</html>")
        self.git("add", "index.html")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.files = {
            "stock-value-radar.html": "<html>canonical radar</html>",
            "stock-radar-dashboard.html": "<html>redirect</html>",
            "stock-opportunity-data.json": '{"companies": []}',
            "assets/widget.js": "const widget = true;",
            "assets/model.webp": "tracked public asset",
            ".nojekyll": "",
            "AGENTS.md": "private development instructions",
            "scripts/private.py": "TOKEN = 'test-only'",
            "services/private/config.json": '{"test_secret":"not public"}',
            "private.json": '{"test_secret":"not allowlisted"}',
            "backups/old.html": "excluded backup",
            ".github/workflows/private.yml": "permissions: {}",
        }
        for name, content in self.files.items():
            self.write(name, content)
        self.git("add", ".")
        self.git("commit", "-qm", "candidate")
        self.candidate = self.git("rev-parse", "HEAD").strip()
        self.policy = {"enabled": False, "public_root_files": ["index.html", "stock-value-radar.html",
                       "stock-radar-dashboard.html", "stock-opportunity-data.json", ".nojekyll"],
                       "asset_extensions": [".js", ".webp", ".html"]}
        self.site, self.manifest = self.directory / "site", self.directory / "evidence/manifest.json"
        self.validation = self.directory / "validation.json"
        self.browser = self.directory / "browser.json"
        self.radar = self.directory / "radar.json"
        self.radar.write_text(json.dumps({"head": self.candidate, "scope": "explicit_files", "status": "passed",
                                         "selected": [{"id": name, "status": "passed"} for name in
                                                      ("radar-browser", "radar-publish-protection", "radar-evidence-review",
                                                       "radar-forecast-wiring", "event-ui")], "uncovered": []}))
        self.validation.write_text(json.dumps({"head": self.candidate, "base": self.base, "scope": "commit_diff",
                                               "status": "passed", "selected": [{"status": "passed"}], "uncovered": []}))
        fingerprints = {name: gate.digest(content.encode()) for name, content in self.files.items()
                        if name.startswith("stock-")}
        self.browser.write_text(json.dumps({"suite": "canonical-investment-radar", "passed": True,
                                           "checks": [{"pass": True}], "checks_failed": 0,
                                           "source_sha256_before": fingerprints, "source_sha256_after": fingerprints}))

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True, stderr=subprocess.PIPE)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def package(self):
        return gate.package(self.root, self.candidate, self.policy, self.site, self.manifest,
                            self.validation, self.browser, self.radar)

    def verify(self):
        return gate.verify_artifact(self.root, self.candidate, self.policy, self.site, self.manifest,
                                    self.validation, self.browser, self.radar)

    def test_artifact_only_contains_allowlisted_git_objects(self):
        self.write("assets/untracked-editorial.js", "earlier user work")
        self.write("editorial-studio.html", "earlier user work")
        result = self.package()
        paths = {item["path"] for item in result["files"]}
        self.assertEqual(paths, set(self.policy["public_root_files"]) | {"assets/widget.js", "assets/model.webp"})
        self.assertNotIn("private.json", paths)
        self.assertNotIn("assets/untracked-editorial.js", paths)
        self.assertFalse(self.manifest.is_relative_to(self.site))
        self.assertEqual(self.verify()["candidate_sha"], self.candidate)

    def test_dirty_tracked_content_is_not_packaged_or_hidden(self):
        self.write("index.html", "untested change")
        with self.assertRaisesRegex(gate.ReleaseDenied, "Tracked checkout changed"):
            self.package()
        self.assertFalse(self.site.exists())

    def test_existing_outputs_are_never_cleared(self):
        self.site.mkdir()
        (self.site / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(gate.ReleaseDenied, "nonempty"):
            self.package()
        self.assertEqual((self.site / "keep.txt").read_text(), "keep")

    def test_provenance_cannot_enter_public_site(self):
        self.manifest = self.site / "manifest.json"
        with self.assertRaisesRegex(gate.ReleaseDenied, "outside the public site"):
            self.package()

    def test_failed_or_planned_validation_cannot_package(self):
        for mutation in ({"status": "planned"}, {"status": "failed"}, {"head": "b" * 40},
                         {"scope": "working_tree"}, {"selected": []}, {"uncovered": ["file.js"]}):
            report = {"head": self.candidate, "base": self.base, "scope": "commit_diff", "status": "passed",
                      "selected": [{"status": "passed"}], "uncovered": [], **mutation}
            self.validation.write_text(json.dumps(report))
            with self.subTest(mutation=mutation), self.assertRaises(gate.ReleaseDenied):
                self.package()

    def test_browser_evidence_must_match_the_exact_candidate(self):
        report = gate.read_json(self.browser)
        report["source_sha256_before"]["stock-value-radar.html"] = "0" * 64
        report["source_sha256_after"] = copy.deepcopy(report["source_sha256_before"])
        self.browser.write_text(json.dumps(report))
        with self.assertRaisesRegex(gate.ReleaseDenied, "different content"):
            self.package()

    def test_mandatory_radar_checks_cannot_be_omitted(self):
        report = gate.read_json(self.radar)
        report["selected"] = [{"id": "radar-browser", "status": "passed"}]
        self.radar.write_text(json.dumps(report))
        with self.assertRaisesRegex(gate.ReleaseDenied, "missing or failed"):
            self.package()

    def test_browser_failure_cannot_package(self):
        report = gate.read_json(self.browser)
        report["checks"][0]["pass"] = False
        self.browser.write_text(json.dumps(report))
        with self.assertRaisesRegex(gate.ReleaseDenied, "contain failures"):
            self.package()

    def test_modified_artifact_or_added_private_file_cannot_verify(self):
        self.package()
        (self.site / "private.json").write_text("{}")
        with self.assertRaisesRegex(gate.ReleaseDenied, "extra or missing"):
            self.verify()
        (self.site / "private.json").unlink()
        (self.site / "index.html").write_text("different content")
        with self.assertRaisesRegex(gate.ReleaseDenied, "differs"):
            self.verify()

    def test_evidence_hashes_bind_reports_to_manifest(self):
        self.package()
        self.validation.write_text(self.validation.read_text() + "\n")
        with self.assertRaisesRegex(gate.ReleaseDenied, "modified after packaging"):
            self.verify()

    def test_manifest_traversal_and_duplicate_files_are_denied(self):
        self.package()
        original = gate.read_json(self.manifest)
        for mutation in ([{"path": "../private.txt"}], original["files"] + [original["files"][0]]):
            self.manifest.write_text(json.dumps({**original, "files": mutation}))
            with self.subTest(mutation=mutation), self.assertRaises(gate.ReleaseDenied):
                self.verify()

    def test_public_symlinks_are_rejected(self):
        (self.root / "assets/link.js").symlink_to("../private.json")
        self.git("add", "assets/link.js")
        self.git("commit", "-qm", "symlink candidate")
        candidate = self.git("rev-parse", "HEAD").strip()
        with self.assertRaisesRegex(gate.ReleaseDenied, "symlinks"):
            gate.public_blobs(self.root, candidate, self.policy)

    def test_unsafe_paths_are_rejected(self):
        for path in ("/etc/passwd", "assets/../secret.js", "assets\\private.js", "./index.html", "assets//x.js", ".env"):
            with self.subTest(path=path), self.assertRaises(gate.ReleaseDenied):
                gate.safe_path(path)


if __name__ == "__main__":
    unittest.main()
