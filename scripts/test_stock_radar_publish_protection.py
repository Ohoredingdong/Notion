"""Protect the custom home from legacy writers and bound forecast tag insertion.

The forecast publisher legitimately stages three HTML templates to add missing
runtime tags. Exercise its actual insertion block in temporary files, without
importing the publisher or running its collection, Git or publication code.
"""
import ast
from pathlib import Path
import re
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
main=(ROOT/"stock-value-radar.html").read_text(encoding="utf-8")
assert 'data-custom-radar-ui="flow-v3"' in main
assert "stock-radar-clean-bridge.js" in main and "stock-radar-flow-v2.js" in main
assert "stock-radar-neutral.js" not in main
assert "height:100dvh" in main

for name,variable in [
    ("scripts/publish_stock_opportunities.py","UI"),
    ("scripts/publish_stock_market_groups.py","UI"),
    ("scripts/publish_stock_investment_cases.py","FILES"),
]:
    body=(ROOT/name).read_text(encoding="utf-8")
    line=next(x for x in body.splitlines() if x.startswith(variable+"="))
    assert "'stock-value-radar.html'" not in line, (name,line)

decisions=(ROOT/".github/workflows/update-stock-decisions.yml").read_text(encoding="utf-8")
for line in decisions.splitlines():
    if re.search(r"\bgit add\b",line):
        assert "stock-value-radar.html" not in line, line

installer=(ROOT/"scripts/install_stock_radar_v8.py").read_text(encoding="utf-8")
assert 'data-custom-radar-ui="flow-v3"' in installer
for name in ("scripts/install_stock_decision_ui.py","scripts/install_stock_audit_ui.py"):
    assert 'data-custom-radar-ui="flow-v3"' in (ROOT/name).read_text(encoding="utf-8")

def forecast_html_update():
    """Compile only the publisher's literal HTML loop; no module side effects."""
    source = ROOT / "scripts/publish_stock_forecasts.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"HTML", "TAGS"}:
                    constants[target.id] = ast.literal_eval(node.value)
    publish = next(node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "publish")
    loops = [node for node in ast.walk(publish)
             if isinstance(node, ast.For) and isinstance(node.iter, ast.Name)
             and node.iter.id == "HTML"]
    if len(loops) != 1:
        raise AssertionError("Expected exactly one forecast HTML insertion block")
    block = ast.Module(body=loops, type_ignores=[])
    code = compile(ast.fix_missing_locations(block), str(source), "exec")
    return constants, code


FORECAST_HTML, FORECAST_CODE = forecast_html_update()


class ForecastHtmlProtectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="forecast-html-test-")
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)

    def write_templates(self, html):
        for name in FORECAST_HTML["HTML"]:
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")

    def update(self):
        # No publisher imports, Git helpers, network clients or source checkout
        # paths are supplied to the extracted production code.
        exec(FORECAST_CODE, {
            "__builtins__": {"RuntimeError": RuntimeError},
            "work": self.work,
            **FORECAST_HTML,
        })

    def test_exact_template_and_runtime_allowlist(self):
        self.assertEqual(FORECAST_HTML["HTML"], [
            "stock-value-radar.html", "assets/stock-radar-v8.html",
            "stock-forecast.html",
        ])
        assets = [tag.split('src="')[1].split("?")[0]
                  for tag in FORECAST_HTML["TAGS"]]
        self.assertEqual(assets, [
            "./assets/stock-forecast.js", "./assets/stock-forecast-learning.js",
            "./assets/stock-forecast-directions.js",
            "./assets/stock-forecast-autopilot.js",
        ])

    def test_missing_tags_preserve_approved_markup_and_are_idempotent(self):
        original = ('<!doctype html><html><head><title>승인된 시안</title>\n'
                    '<style>.approved { padding: 17px; }</style></head>\n'
                    '<body data-custom-radar-ui="flow-v3"><main id="approved">'
                    '기존 사용자 화면과 구도</main></body></html>\n')
        self.write_templates(original)
        self.update()
        for name in FORECAST_HTML["HTML"]:
            actual = (self.work / name).read_text(encoding="utf-8")
            self.assertEqual(actual.partition("</head>")[2],
                             original.partition("</head>")[2])
            restored = actual
            for tag in FORECAST_HTML["TAGS"]:
                self.assertEqual(actual.count(tag), 1, name)
                restored = restored.replace(tag + "\n", "", 1)
            self.assertEqual(restored, original, name)
        before = {name: (self.work / name).read_bytes()
                  for name in FORECAST_HTML["HTML"]}
        self.update()
        self.assertEqual(before, {name: (self.work / name).read_bytes()
                                  for name in FORECAST_HTML["HTML"]})

    def test_existing_asset_with_different_query_is_not_duplicated(self):
        tags = [tag.replace("?v=", "?v=approved-existing-")
                for tag in FORECAST_HTML["TAGS"]]
        original = ('<html><head>\n' + "\n".join(tags) +
                    '\n</head><body><main>승인된 화면</main></body></html>')
        self.write_templates(original)
        self.update()
        for name in FORECAST_HTML["HTML"]:
            self.assertEqual((self.work / name).read_text(encoding="utf-8"),
                             original, name)

    def test_current_snapshots_change_only_by_missing_runtime_tags(self):
        originals = {}
        for name in FORECAST_HTML["HTML"]:
            originals[name] = (ROOT / name).read_text(encoding="utf-8")
            path = self.work / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(originals[name], encoding="utf-8")
        self.update()
        for name, original in originals.items():
            actual = (self.work / name).read_text(encoding="utf-8")
            restored = actual
            for tag in FORECAST_HTML["TAGS"]:
                asset = tag.split('src="')[1].split("?")[0]
                if asset not in original:
                    self.assertEqual(actual.count(tag), 1, name)
                    restored = restored.replace(tag + "\n", "", 1)
            self.assertEqual(restored, original, name)
        before = {name: (self.work / name).read_bytes() for name in originals}
        self.update()
        self.assertEqual(before, {name: (self.work / name).read_bytes()
                                  for name in originals})

    def test_missing_template_is_rejected(self):
        self.write_templates("<html><head></head><body>keep</body></html>")
        missing = self.work / FORECAST_HTML["HTML"][0]
        missing.unlink()
        with self.assertRaisesRegex(RuntimeError, "^radar_template_missing$"):
            self.update()
        self.assertFalse(missing.exists())

    def test_missing_head_is_rejected_without_rewriting_template(self):
        original = "<html><body>승인된 본문을 보존</body></html>"
        self.write_templates(original)
        with self.assertRaisesRegex(RuntimeError, "^template_head_missing$"):
            self.update()
        for name in FORECAST_HTML["HTML"]:
            self.assertEqual((self.work / name).read_text(encoding="utf-8"),
                             original, name)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ForecastHtmlProtectionTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    print("PASS: checked legacy publishers exclude the custom home; "
          "forecast HTML insertion preserves approved markup and existing runtimes "
          f"({result.testsRun} isolated checks)")
