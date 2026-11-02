# Read-only modern Stock Radar flow browser isolation — 2026-11-02 14:34 UTC

## Frozen baseline
- Repository: Ohoredingdong/Notion
- Base main commit: `0b7e6657e0c0ced272aa5a1834eb0a793337ea2e`.
- Timing acceptance, direction-specialists and bounded-autopilot approval documents were read before this experiment. Their unchanged blob SHAs are `69526101025c0394b13a55bfb73b9be5240e5fca`, `6d5498666cd6da4d4528c46a4f1cb911715e90bd`, `a5176f6aa075c49a090e6a3ec01b64fb323420ed`.
- Original forecast data and acceptance criteria are not changed; no orders, credentials or user notification.

## Single preregistered hypothesis
The current integrated CI's old DOM assertion prevents its *subsequent* modern `scripts/test_stock_radar_flow_browser.py` suite from executing. A separate read-only browser job can test the actual modern flow without turning the failed legacy gate green. This is a coverage/observability experiment, **not** a forecast improvement, frontend release or reason to lower old acceptance rules.

## Reproduction and fixed controls
At base main, `stock-value-radar.html` loads `assets/stock-radar-flow-v2.js` and `assets/stock-radar-clean-bridge.js`. Existing [integrated CI run 41452117718](https://github.com/Ohoredingdong/Notion/actions/runs/41452117718) on `f91ba39c2f01ad81d40a2618a1c8b5f2e23a7d36` failed at `scripts/test_stock_decision_browser.py:346`, requiring `#nr-market-overview,#nr-home-alerts,#nr-home-picks`, before reaching the following `python scripts/test_stock_radar_flow_browser.py` command. The modern flow JS, bridge, old browser test, new browser test and workflow have the same Git blob SHAs on that run's head and pinned main. This does not establish that the modern UI works or fails.

## Fixed test and success conditions
Run exactly **one existing** `scripts/test_stock_radar_flow_browser.py` suite in headless Chromium on this isolated branch. Use original repo JSON and existing unmodified HTML/JS. Preserve the original test assertions and capture all screenshots/negative results. A pass is only a pass of this particular browser suite; a failure is logged and not ignored. No candidate search, tuning, retroactive financial label, test skipping, deployment, trading, or model swap. The old CI remains failed until separately corrected and reverified.

## Stop conditions
Record one execution result, error details and GitHub Action URL if obtainable. Do not merge if the full required regressions have not passed. Absence of a runnable action or infrastructure prerequisites means `not_verified`, not success. This branch is research-only.
