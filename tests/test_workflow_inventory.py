"""Inventory failures must remain visible; these tests never run workflow jobs."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "workflow_inventory", Path(__file__).resolve().parents[1] / "scripts/audit_workflows.py"
)
inventory_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory_module)


class WorkflowInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / ".github/workflows").mkdir(parents=True)
        (self.root / "scripts").mkdir()

    def workflow(self, filename, content):
        (self.root / ".github/workflows" / filename).write_text(content)

    def test_on_is_not_yaml_boolean_and_discovery_is_counted(self):
        (self.root / "scripts/test_data.py").write_text("# offline regression\n")
        self.workflow("verify.yml", """name: Verify
on:
  pull_request:
  schedule:
    - cron: '0 * * * *'
permissions:
  contents: read
jobs:
  tests:
    steps:
      - run: python -m unittest discover -s scripts -p 'test_*.py'
""")
        report = inventory_module.inventory(self.root)
        self.assertEqual(report["workflow_count"], 1)
        self.assertEqual(report["summary"]["pull_request_workflows"], 1)
        self.assertEqual(report["workflows"][0]["events"]["schedule"][0]["cron"], "0 * * * *")
        self.assertEqual(report["test_files_not_named_in_workflows"], [])
        self.assertEqual(report["errors"], [])

    def test_missing_script_is_error_not_successful_inventory(self):
        self.workflow("broken.yml", """on: push
jobs:
  test:
    steps:
      - run: python scripts/missing.py
""")
        report = inventory_module.inventory(self.root)
        self.assertEqual(len(report["errors"]), 1)
        self.assertIn("Missing literal script target", report["errors"][0]["error"])

    def test_missing_syntax_checked_asset_is_also_an_error(self):
        self.workflow("syntax.yml", """on: pull_request
jobs:
  test:
    steps:
      - run: node --check assets/removed-widget.js
""")
        report = inventory_module.inventory(self.root)
        self.assertEqual(len(report["errors"]), 1)
        self.assertIn("assets/removed-widget.js", report["errors"][0]["error"])

    def test_multiple_pythonpath_unittest_modules_are_recognized(self):
        for name in ("test_learning", "test_directions"):
            (self.root / "scripts" / (name + ".py")).write_text("# unit test\n")
        self.workflow("forecasts.yml", """on: push
jobs:
  test:
    steps:
      - run: PYTHONPATH=scripts python -m unittest test_learning test_directions -v
""")
        report = inventory_module.inventory(self.root)
        self.assertEqual(report["test_files_not_named_in_workflows"], [])
        self.assertEqual(report["errors"], [])

    def test_publish_helper_and_pages_requests_are_not_hidden_as_tests(self):
        (self.root / "scripts/publish_widget_data.py").write_text("# not executed\n")
        self.workflow("publish.yml", """name: Tests and publication
on: [push, workflow_dispatch]
permissions: {contents: write, pages: write}
jobs:
  publish:
    steps:
      - name: Publish data
        run: python scripts/publish_widget_data.py --message test data.json
      - name: Pages build
        run: gh api --method POST repos/example/site/pages/builds
""")
        report = inventory_module.inventory(self.root)
        workflow = report["workflows"][0]
        self.assertEqual(report["summary"]["workflows_with_publication_steps"], 1)
        self.assertEqual(workflow["publication_steps"][0]["helpers"], ["scripts/publish_widget_data.py"])
        self.assertEqual(report["summary"]["explicit_pages_build_workflows"], 1)

    def test_ignored_failure_and_duplicate_command_are_reported(self):
        (self.root / "scripts/test_data.py").write_text("# test\n")
        for name in ("first", "second"):
            self.workflow(name + ".yml", f"""name: {name}
on: push
jobs:
  test:
    steps:
      - run: python scripts/test_data.py
        continue-on-error: true
""")
        report = inventory_module.inventory(self.root)
        self.assertEqual(report["summary"]["workflows_with_continue_on_error"], 2)
        self.assertEqual(len(report["duplicate_test_commands"]["python scripts/test_data.py"]), 2)

    def test_malformed_workflow_and_duplicate_names_fail(self):
        self.workflow("invalid.yml", "on: [\n")
        for filename in ("a.yml", "b.yaml"):
            self.workflow(filename, "name: Same\non: push\njobs: {test: {steps: []}}\n")
        report = inventory_module.inventory(self.root)
        self.assertEqual(len(report["errors"]), 2)
        self.assertTrue(any("Duplicate workflow name" in item["error"] for item in report["errors"]))

    def test_unreferenced_tests_are_explicitly_an_coverage_hint(self):
        (self.root / "scripts/test_uncovered.py").write_text("# real test\n")
        self.workflow("docs.yml", "on: push\njobs: {check: {steps: []}}\n")
        report = inventory_module.inventory(self.root)
        self.assertEqual(report["test_files_not_named_in_workflows"], ["scripts/test_uncovered.py"])
        self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
