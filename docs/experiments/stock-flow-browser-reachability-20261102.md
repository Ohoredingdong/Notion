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

## One executed isolated trial (post-hypothesis, no test modification)

- Research workflow source commit: `a68156aa2341feb9d1938d746741e0d87c104541`; [run 41464395687](https://github.com/Ohoredingdong/Notion/actions/runs/41464395687), job `125341349729`.
- Browser dependency installation and JS/Python syntax checks passed. The pre-registered modern browser suite **ran for real** on the unmodified HTML/JS/data, and the job **failed** at `scripts/test_stock_radar_flow_browser.py:96`: `AssertionError: Market index cards`.
- Fault isolation: the current code's `fxHome()` builds a section `.fx-v5-marketline` holding `.fx-v5-markets.nr-market-grid`, with market cards supplied by `StockRadarV2Bridge.helpers.indices()` (four index specifications). The unchanged test instead selects `.fx-market-row .nr-index`; `fx-market-row` is absent in the current flow script. This explains the false-negative selector expectation. It **does not prove** the actual four cards are rendered in a browser or any later navigation works. The test stopped at the first failed assertion after earlier layout checks, so its remaining controls were **not executed**.
- Failure evidence is preserved as run logs and [research-modern-radar-flow-evidence artifact](https://github.com/Ohoredingdong/Notion/actions/runs/41464395687). Exactly **one** isolated execution, **zero** new model candidates and **zero** test/production code fixes in this trial. No green UI release claim.
- Next engineering hypothesis, **not executed in this experiment**: on a separately reviewed branch adjust only obsolete selectors to the actual v5 DOM while preserving the four-card requirement and all other behavior/layout/security assertions. Run the full modern suite, legacy regressions, independent forecast audit and public check before any merge. Merely renaming a selector is not evidence of real functionality.
- Original integrated CI remained red; independent trading/timing acceptance is still `not_proven`. Do not present this isolated experiment as a successful code repair.

## Separately preregistered bounded test-only repair — after the first RED run

**New fixed hypothesis:** `fxHome()` intentionally migrated market index cards to `.fx-v5-markets.nr-market-grid`; the first isolated browser RED was an obsolete parent CSS selector, not a proven missing-card regression. In a **single** research-only correction, change only `.fx-market-row .nr-index` to `.fx-v5-markets .nr-index` in the browser suite, preserving the requirement for exactly **four** cards and every other functional/layout/security assertion. Extend only this research workflow's `push.paths` to run the changed test once. Leave the entire production UI, forecast scripts, input evidence, labels, acceptance criteria and existing main workflows unmodified.

**Falsifier and stop rule:** if the rerun fails anywhere else, do not broaden the rewrite within this trial and do not claim a passing browser suite. If green, it verifies only the existing suite against this research head and does **not** override old main UI regression failures. **Maximum one** test-only change and **one** rerun, record both outcomes. No merge or production UI changes before the complete required regressions and published public bytes pass.
