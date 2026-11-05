"""Fail CI if any legacy collector can stage or overwrite the custom homepage."""
from pathlib import Path
import re

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
for name in ("scripts/install_stock_decision_ui.py","scripts/install_stock_audit_ui.py",
             "scripts/install_stock_radar_neutral.py","scripts/install_stock_strict_green.py",
             "scripts/install_stock_investment_cases.py"):
    body=(ROOT/name).read_text(encoding="utf-8")
    assert ('data-custom-radar-ui="flow-v3"' in body or
            ('from verify_stock_canonical_pipeline import verify_canonical' in body and
             'if verify_canonical(' in body)), name

print("PASS: automated data collectors cannot stage or replace the independent radar home")

