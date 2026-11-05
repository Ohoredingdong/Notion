"""Release gate regression tests using disposable Git repositories.

These synthetic receipts exercise rejection/integrity rules only. They do not
represent executed application checks, financial observations or deploy approval.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

try:
    from scripts import prepare_release as release
except ImportError:
    import prepare_release as release


IDS = ["repository-policy", "workflow-lint", "python-unit", "service-unit", "node-unit",
       "radar-js-unit", "radar-browser", "radar-flow-browser", "radar-entry-browser",
       "radar-advanced-browser", "syntax", "data-integrity"]


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="notion-release-test-")
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.report_path = self.base / "check-receipt.json"
        self.output = self.base / "prepared-candidate"
        self.write("index.html", "<h1>Existing widget</h1>")
        self.write("old-widget.html", '<meta http-equiv="refresh" content="0;url=index.html">')
        self.write("assets/app.js", "window.existingWidget = true;\n")
        self.write("widget-data.json", '{"observed_at":"2026-10-20","value":15}\n')
        self.write("docs/usage.md", "Existing public instructions.\n")
        self.write(".nojekyll", "")
        self.write("CNAME", "example.invalid\n")
        self.write(".github/workflows/existing.yml", "permissions:\n  contents: read\n")
        self.write(".agents/skills/local/SKILL.md", "Developer guidance.\n")
        self.write("services/private.py", "private = True\n")
        self.write("supabase/config.toml", "project = 'not-a-site-asset'\n")
        self.write("tests/not-a-site.test.cjs", "// tests stay out of the site\n")
        self.write("scripts/dev_check.py", "IDS = " + repr(IDS) + "\n"
                   "def build_plan(root, *, all_checks=False, output=None, **kwargs):\n"
                   "    assert all_checks\n"
                   "    return {'checks':[{'id':i} for i in IDS], 'expected_check_ids':IDS}\n")
        self.git("init", "--quiet")
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.commit()
        self.save_report(self.valid_report())

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git("add", "--all")
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Fixture inputs")
        self.sha = self.git("rev-parse", "HEAD")

    def valid_report(self):
        stamp = datetime.now(timezone.utc).isoformat()
        return {
            "schema_version": 1, "head_sha": self.sha, "mode": "all", "status": "passed",
            "working_tree_clean": True, "expected_check_ids": list(IDS),
            "checks": [{"id": name, "status": "passed", "returncode": 0,
                        "started_at": stamp, "ended_at": stamp} for name in IDS],
            "snapshot": release.tracked_snapshot(self.root),
        }

    def save_report(self, value):
        self.report_path.write_text(json.dumps(value))

    def prepare(self, **kwargs):
        options = {"root": self.root, "sha": self.sha,
                   "report_path": self.report_path, "output": self.output}
        options.update(kwargs)
        return release.prepare_candidate(**options)

    def rejected_report(self, change):
        report = self.valid_report()
        change(report)
        self.save_report(report)
        with self.assertRaises(release.ReleaseRejected):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_passed_exact_commit_preserves_site_and_legacy_urls(self):
        before = release.tracked_snapshot(self.root)
        manifest = self.prepare()
        self.assertEqual(release.tracked_snapshot(self.root), before)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(manifest["source_sha"], self.sha)
        self.assertIs(manifest["deployment_authorized"], False)
        expected = {"index.html", "old-widget.html", "assets/app.js", "widget-data.json",
                    "docs/usage.md", ".nojekyll", "CNAME"}
        self.assertEqual(set(manifest["files"]), expected)
        with zipfile.ZipFile(self.output / release.ARCHIVE_NAME) as zipped:
            for name in expected:
                self.assertEqual(zipped.read(name), (self.root / name).read_bytes())
        pin = release.digest((self.output / release.MANIFEST_NAME).read_bytes())
        self.assertEqual(release.verify_candidate(self.output, self.sha, pin), manifest)

    def test_archive_is_reproducible_for_identical_tested_inputs(self):
        self.prepare()
        other = self.base / "second-candidate"
        self.prepare(output=other)
        self.assertEqual((self.output / release.ARCHIVE_NAME).read_bytes(),
                         (other / release.ARCHIVE_NAME).read_bytes())

    def test_failure_skip_and_nonzero_returncode_are_rejected(self):
        for field, value in [("status", "failed"), ("status", "skipped"), ("returncode", 7),
                             ("returncode", None), ("returncode", False), ("returncode", 0.0)]:
            with self.subTest(field=field, value=value):
                self.rejected_report(lambda r: r["checks"][1].__setitem__(field, value))

    def test_failed_related_or_planned_only_runs_are_rejected(self):
        for field, value in [("status", "failed"), ("status", "planned"), ("mode", "related"),
                             ("working_tree_clean", False), ("schema_version", 2), ("schema_version", True)]:
            with self.subTest(field=field, value=value):
                self.rejected_report(lambda r: r.__setitem__(field, value))

    def test_empty_incomplete_duplicate_and_forged_reduced_plans_are_rejected(self):
        changes = [lambda r: r.__setitem__("checks", []),
                   lambda r: r["checks"].pop(),
                   lambda r: r["checks"].append(copy.deepcopy(r["checks"][0])),
                   lambda r: r.__setitem__("expected_check_ids", []),
                   lambda r: (r["checks"].pop(), r["expected_check_ids"].pop())]
        for change in changes:
            with self.subTest(change=repr(change)):
                self.rejected_report(change)

    def test_missing_or_invalid_execution_timestamps_are_rejected(self):
        for field, value in [("started_at", None), ("ended_at", ""), ("started_at", "not a date"),
                             ("ended_at", "2026-10-20T00:00:00"),
                             ("ended_at", "2000-01-01T00:00:00Z")]:
            with self.subTest(field=field, value=value):
                self.rejected_report(lambda r: r["checks"][0].__setitem__(field, value))

    def test_receipt_for_another_commit_is_rejected(self):
        self.rejected_report(lambda r: r.__setitem__("head_sha", "0" * 40))

    def test_abbreviated_malformed_and_noncurrent_requested_shas_are_rejected(self):
        for sha in [self.sha[:8], self.sha.upper(), "main", "0" * 40, "x" * 40]:
            with self.subTest(sha=sha), self.assertRaises(release.ReleaseRejected):
                self.prepare(sha=sha)
        self.assertFalse(self.output.exists())

    def test_stale_missing_extra_and_null_snapshot_hashes_are_rejected(self):
        changes = [lambda r: r["snapshot"].__setitem__("index.html", "0" * 64),
                   lambda r: r["snapshot"].pop("index.html"),
                   lambda r: r["snapshot"].__setitem__("not-tracked.html", "0" * 64),
                   lambda r: r["snapshot"].__setitem__("index.html", None)]
        for change in changes:
            with self.subTest(change=repr(change)):
                self.rejected_report(change)

    def test_uncommitted_untracked_and_staged_changes_are_rejected(self):
        self.write("index.html", "Changed after checking")
        with self.assertRaisesRegex(release.ReleaseRejected, "dirty"):
            self.prepare()
        self.write("index.html", "<h1>Existing widget</h1>")
        self.write("untracked.html", "New untested file")
        with self.assertRaisesRegex(release.ReleaseRejected, "dirty"):
            self.prepare()
        self.git("add", "untracked.html")
        with self.assertRaisesRegex(release.ReleaseRejected, "dirty"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_committing_new_content_cannot_reuse_the_old_receipt(self):
        self.write("index.html", "An untested new commit")
        self.commit()
        with self.assertRaisesRegex(release.ReleaseRejected, "different commit"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_committed_changed_check_plan_requires_a_new_complete_run(self):
        self.write("scripts/dev_check.py", "def build_plan(root, **kwargs):\n"
                   "    return {'checks':[{'id':'new-required-check'}]}\n")
        self.commit()
        report = self.valid_report()
        self.save_report(report)
        with self.assertRaisesRegex(release.ReleaseRejected, "complete check plan"):
            self.prepare()

    def test_tracked_symlinks_are_rejected_even_when_not_site_files(self):
        (self.root / "scripts" / "external-link").symlink_to(self.report_path)
        self.commit()
        with self.assertRaisesRegex(release.ReleaseRejected, "Symlinks"):
            self.prepare()

    def test_report_and_artifacts_must_be_outside_checkout(self):
        with self.assertRaisesRegex(release.ReleaseRejected, "outside"):
            self.prepare(output=self.root / "release-output")
        with self.assertRaisesRegex(release.ReleaseRejected, "outside"):
            self.prepare(report_path=self.root / "receipt.json")

    def test_external_symlinked_report_output_and_parent_are_rejected(self):
        linked_report = self.base / "linked-receipt.json"
        linked_report.symlink_to(self.report_path)
        with self.assertRaisesRegex(release.ReleaseRejected, "Symlink"):
            self.prepare(report_path=linked_report)
        link = self.base / "linked-parent"
        target = self.base / "actual-parent"
        target.mkdir()
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(release.ReleaseRejected, "Symlink"):
            self.prepare(output=link / "candidate")

    def test_existing_artifacts_are_never_overwritten(self):
        self.output.mkdir()
        saved = self.output / "keep.txt"
        saved.write_text("Keep this original")
        with self.assertRaisesRegex(release.ReleaseRejected, "never overwritten"):
            self.prepare()
        self.assertEqual(saved.read_text(), "Keep this original")

    def test_corrupt_missing_or_checked_in_receipts_are_rejected(self):
        self.report_path.write_text("not json")
        with self.assertRaises(release.ReleaseRejected):
            self.prepare()
        self.report_path.unlink()
        with self.assertRaises(release.ReleaseRejected):
            self.prepare()

    def test_content_change_while_packaging_is_rejected(self):
        def altering_plan(root, output):
            # Simulate another process changing a checked file after the first snapshot.
            self.write("assets/app.js", "window.changedWhilePackaging = true;\n")
            return list(IDS)
        with patch.object(release, "current_check_ids", side_effect=altering_plan):
            with self.assertRaisesRegex(release.ReleaseRejected, "changed while"):
                self.prepare()
        self.assertFalse(self.output.exists())

    def test_archive_mutation_is_rejected(self):
        self.prepare()
        path = self.output / release.ARCHIVE_NAME
        path.write_bytes(path.read_bytes() + b"unexpected append")
        with self.assertRaisesRegex(release.ReleaseRejected, "archive was changed"):
            release.verify_candidate(self.output, self.sha)

    def test_manifest_mutation_is_rejected_by_a_pinned_digest(self):
        self.prepare()
        path = self.output / release.MANIFEST_NAME
        pinned = release.digest(path.read_bytes())
        manifest = json.loads(path.read_bytes())
        manifest["scope"] = "tampered manifest"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(release.ReleaseRejected, "trusted digest"):
            release.verify_candidate(self.output, self.sha, pinned)

    def add_archive_entry(self, name, body, mode=stat.S_IFREG | 0o644):
        manifest_path = self.output / release.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_bytes())
        path = self.output / release.ARCHIVE_NAME
        with zipfile.ZipFile(path, "a") as zipped:
            item = zipfile.ZipInfo(name)
            item.external_attr = mode << 16
            zipped.writestr(item, body)
        manifest["archive_sha256"] = release.digest(path.read_bytes())
        manifest["files"][name] = {"sha256": release.digest(body), "bytes": len(body)}
        manifest_path.write_text(json.dumps(manifest))

    def test_archive_path_traversal_and_absolute_entries_are_rejected(self):
        for index, name in enumerate(["../escape.html", "/absolute.html", "assets/../../escape.js",
                                      "assets\\escape.js", "C:/escape.html", "assets/new\nline.js"]):
            with self.subTest(name=name):
                self.output = self.base / ("candidate-" + str(index))
                self.prepare()
                self.add_archive_entry(name, b"malicious archive entry")
                with self.assertRaises(release.ReleaseRejected):
                    release.verify_candidate(self.output, self.sha)
        self.assertFalse((self.base / "escape.html").exists())

    def test_archive_symlink_and_disallowed_source_entries_are_rejected(self):
        for index, (name, mode) in enumerate([("assets/link.html", stat.S_IFLNK | 0o777),
                                              ("scripts/source.py", stat.S_IFREG | 0o644)]):
            with self.subTest(name=name):
                self.output = self.base / ("candidate-" + str(index))
                self.prepare()
                self.add_archive_entry(name, b"../outside", mode)
                with self.assertRaises(release.ReleaseRejected):
                    release.verify_candidate(self.output, self.sha)

    def test_wrong_source_or_deployment_approval_claim_is_rejected(self):
        self.prepare()
        with self.assertRaises(release.ReleaseRejected):
            release.verify_candidate(self.output, "0" * 40)
        manifest_path = self.output / release.MANIFEST_NAME
        value = json.loads(manifest_path.read_bytes())
        value["deployment_authorized"] = True
        manifest_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(release.ReleaseRejected, "approval"):
            release.verify_candidate(self.output, self.sha)

    def test_ignored_runtime_file_cannot_pass_a_clean_checkout_receipt(self):
        self.write(".gitignore", "ignored-runtime.js\n")
        self.write("index.html", '<script src="ignored-runtime.js"></script>')
        self.commit()
        self.write("ignored-runtime.js", "// A local browser could load this untracked input.\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.save_report(self.valid_report())
        with self.assertRaisesRegex(release.ReleaseRejected, "not tracked and packaged"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_html_css_srcset_and_project_base_dependencies_are_packaged(self):
        self.write("index.html", '''<link rel="stylesheet" href="/Notion/assets/theme.css?v=1">
<script src="./assets/app.js?v=1#marker"></script>
<script src="https://cdn.example.invalid/external.js?redacted=private"></script>
<img src="assets/a%20b.png" srcset="data:image/png;base64,AA== 1x, ./assets/b.png 2x">
<svg><use xlink:href="assets/icons.svg#tick"></use></svg>
<iframe src="./frame.html?embedded=1"></iframe>''')
        self.write("frame.html", '<img src="assets/a%20b.png">')
        self.write("assets/theme.css", '@import "./nested/base.css";p{background:url("a%20b.png#part")}')
        self.write("assets/nested/base.css", '@font-face{src:url(../font.woff2?v=2)}')
        self.write("assets/font.woff2", "Font fixture for static closure only")
        self.write("assets/a b.png", "Image fixture for static closure only")
        self.write("assets/b.png", "Image fixture for static closure only")
        self.write("assets/icons.svg", '<svg><symbol id="tick"></symbol></svg>')
        self.commit()
        self.save_report(self.valid_report())
        value = self.prepare()
        dependencies = value["static_dependencies"]
        self.assertEqual(dependencies["site_base_path"], "/Notion/")
        self.assertEqual(dependencies["static_local_resource_count"], 8)
        self.assertEqual(dependencies["external_resources_unverified"],
                         ["https://cdn.example.invalid/external.js"])
        self.assertIn("Dynamic JavaScript", dependencies["scope"])
        release.verify_candidate(self.output, self.sha)

    def test_static_resource_cannot_point_to_an_excluded_source_directory(self):
        self.write("index.html", '<script src="scripts/dev_check.py"></script>')
        self.commit()
        self.save_report(self.valid_report())
        with self.assertRaisesRegex(release.ReleaseRejected, "not tracked and packaged"):
            self.prepare()

    def test_missing_css_import_font_or_image_is_rejected(self):
        bodies = ['@import "missing.css";', '@font-face{src:url("missing.woff2")}',
                  'p{background:url("missing.png")}']
        for body in bodies:
            with self.subTest(body=body):
                self.write("index.html", '<link rel="stylesheet" href="assets/theme.css">')
                self.write("assets/theme.css", body)
                self.commit()
                self.save_report(self.valid_report())
                with self.assertRaisesRegex(release.ReleaseRejected, "not tracked and packaged"):
                    self.prepare()

    def test_runtime_urls_cannot_escape_the_site_base_or_use_file_scheme(self):
        for reference in ["../../escape.js", "%2e%2e/%2e%2e/escape.js",
                          "/assets/app.js", "file:///tmp/private.js"]:
            with self.subTest(reference=reference):
                self.write("index.html", '<script src="' + reference + '"></script>')
                self.commit()
                self.save_report(self.valid_report())
                with self.assertRaises(release.ReleaseRejected):
                    self.prepare()

    def test_a_custom_domain_root_base_is_explicit_and_checked(self):
        self.write("index.html", '<script src="/assets/app.js"></script>')
        self.commit()
        self.save_report(self.valid_report())
        manifest = self.prepare(base_path="/")
        self.assertEqual(manifest["static_dependencies"]["site_base_path"], "/")
        release.verify_candidate(self.output, self.sha)

    def test_modified_dependency_receipt_cannot_claim_external_validation(self):
        self.prepare()
        path = self.output / release.MANIFEST_NAME
        value = json.loads(path.read_bytes())
        value["static_dependencies"]["scope"] = "Pretend every external service was validated"
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(release.ReleaseRejected, "closure receipt"):
            release.verify_candidate(self.output, self.sha)

    def add_template_contract(self):
        template = '<script src="./assets/app.js"></script>'
        self.write("assets/stock-radar-v8.html", template)
        self.write("stock-value-radar.html", template)
        self.write("scripts/install_stock_radar_v8.py", "# A fixture generation source; never executed.\n")
        contract = {"schema_version": 1, "template_contexts": {
            "assets/stock-radar-v8.html": {
                "render_at": "stock-value-radar.html",
                "generator": "scripts/install_stock_radar_v8.py",
                "reason": "Root-relative generation source, not a standalone entry.",
            }}}
        self.write("config/site-sources.json", json.dumps(contract))
        return contract

    def test_declared_generation_template_is_checked_at_its_installed_target(self):
        contract = self.add_template_contract()
        self.commit()
        self.save_report(self.valid_report())
        manifest = self.prepare()
        self.assertEqual(manifest["static_dependencies"]["template_contexts"], contract["template_contexts"])
        self.assertIn("assets/stock-radar-v8.html", manifest["files"])
        self.assertNotIn("config/site-sources.json", manifest["files"])
        self.assertIn("not their source URL", manifest["static_dependencies"]["scope"])
        release.verify_candidate(self.output, self.sha)

    def test_template_contract_requires_tracked_generator_and_installed_page(self):
        contract = self.add_template_contract()
        for field, value in [("generator", "scripts/missing.py"),
                             ("render_at", "missing.html"),
                             ("generator", "../outside.py"), ("reason", "")]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(contract)
                invalid["template_contexts"]["assets/stock-radar-v8.html"][field] = value
                self.write("config/site-sources.json", json.dumps(invalid))
                self.commit()
                self.save_report(self.valid_report())
                with self.assertRaises(release.ReleaseRejected):
                    self.prepare()

    def test_a_template_is_not_allowed_as_a_standalone_iframe_resource(self):
        self.add_template_contract()
        self.write("index.html", '<iframe src="assets/stock-radar-v8.html"></iframe>')
        self.commit()
        self.save_report(self.valid_report())
        with self.assertRaisesRegex(release.ReleaseRejected, "standalone runtime page"):
            self.prepare()

    def test_template_contract_does_not_hide_missing_resources_in_real_entries(self):
        self.add_template_contract()
        self.write("index.html", '<script src="a-real-missing-runtime.js"></script>')
        self.commit()
        self.save_report(self.valid_report())
        with self.assertRaisesRegex(release.ReleaseRejected, "not tracked and packaged"):
            self.prepare()

    def test_a_broken_planner_cannot_omit_a_required_validation_scope(self):
        reduced = [name for name in IDS if name != "radar-browser"]
        self.write("scripts/dev_check.py", "IDS = " + repr(reduced) + "\n"
                   "def build_plan(root, **kwargs):\n"
                   "    return {'checks':[{'id':i} for i in IDS], 'expected_check_ids':IDS}\n")
        self.commit()
        report = self.valid_report()
        report["checks"] = [row for row in report["checks"] if row["id"] in reduced]
        report["expected_check_ids"] = reduced
        self.save_report(report)
        with self.assertRaisesRegex(release.ReleaseRejected, "omits a required validation scope"):
            self.prepare()

    def add_archive_contract(self):
        archive = "backups/stock-radar-v1-20261102.html"
        body = '<script src="./assets/app.js"></script>'
        self.write(archive, body)
        self.write("stock-value-radar.html", body)
        document = {"schema_version": 1, "template_contexts": {}, "preserved_archives": {
            archive: {"original_context": "stock-value-radar.html",
                      "reason": "Historical source snapshot; preserved byte-for-byte, not a standalone entry."}}}
        self.write("config/site-sources.json", json.dumps(document))
        return archive, body, document

    def test_historical_source_archives_keep_their_original_bytes_and_context(self):
        archive, body, document = self.add_archive_contract()
        self.commit()
        self.save_report(self.valid_report())
        manifest = self.prepare()
        self.assertEqual(manifest["static_dependencies"]["preserved_archives"], document["preserved_archives"])
        with zipfile.ZipFile(self.output / release.ARCHIVE_NAME) as zipped:
            self.assertEqual(zipped.read(archive), body.encode())
        release.verify_candidate(self.output, self.sha)

    def test_historical_source_archive_cannot_be_used_as_a_runtime_iframe(self):
        archive, _, _ = self.add_archive_contract()
        self.write("index.html", '<iframe src="' + archive + '"></iframe>')
        self.commit()
        self.save_report(self.valid_report())
        with self.assertRaisesRegex(release.ReleaseRejected, "standalone runtime page"):
            self.prepare()

    def test_historical_archive_contract_must_identify_a_real_original_page(self):
        archive, _, document = self.add_archive_contract()
        document["preserved_archives"][archive]["original_context"] = "missing.html"
        self.write("config/site-sources.json", json.dumps(document))
        self.commit()
        self.save_report(self.valid_report())
        with self.assertRaisesRegex(release.ReleaseRejected, "missing or untracked"):
            self.prepare()

    def test_boolean_file_size_does_not_forge_an_empty_asset_digest(self):
        self.prepare()
        path = self.output / release.MANIFEST_NAME
        value = json.loads(path.read_bytes())
        value["files"][".nojekyll"]["bytes"] = False
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(release.ReleaseRejected, "file manifest"):
            release.verify_candidate(self.output, self.sha)


if __name__ == "__main__":
    unittest.main()
