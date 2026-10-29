# Staged direction-summary integrity: preregistered bounded experiment (2026-10-30 KST)

Frozen main: `899a93b0cc982bba3ea7dfce7657a9e3d1b65756`. Policy: `timing-utility-acceptance-1.0`; existing direction-specialists and bounded-autopilot gates unchanged.

## Falsifiable engineering hypothesis (before patch)
The prepublication `verify_stage` guard checks immutable source/learning evidence and only the staged dashboard's `overall.samples` and `overall.correct` against the independent auditor. It does not compare `overall.recall`, `confusion_matrix`, `accuracy` or `brier_loss`. Thus a synthetic staged report can claim perfect detection of actual down moves even when its frozen target was a missed down move. This concerns **staged displayed evidence**, not demonstrated real fraud or prediction quality.

## One bounded RED/GREEN trial
1. On this research branch only, build the already existing synthetic test fixture: one frozen timely-public flat prediction, a real-result analogue labelled down (miss), one learning event and intact weight chain. Verify untouched correct staged summary passes.
2. Corrupt only the staged output report's down recall (and independently the displayed accuracy / confusion / Brier within the same summary-corruption family); require rejection. Run the new negative test before patch and record RED Actions.
3. Add a small fail-closed guard in `stock_forecast_autopilot.verify_stage` that independently reconstructs direction counts, recall, confusion matrix, mean Brier and accuracy from prepublication audit rows, **only when scored observations exist**. Keep zero-sample synthetic contract valid. Preserve all output rows, original forecasts, learning and all scoring criteria. Do not add candidates or alter weights.
4. Run the new fixture, existing 26 forecast unit tests, learning/directional/autopilot suites, independent audit, source/session and UI checks, branch research transaction **without publishing**. Check frozen real 59 ledger rows, 45 observed outcomes, 18 eligible scored / 7 correct. Confirm no live quote, alert receipt or after-cost evidence is invented. Only merge code/test/note after verified GREEN and review; remove any temporary workflow branch allowlisting.
5. Exactly one hypothesis, one synthetic output-integrity fault family and no hyperparameter search/model promotion. Record failed and successful trial run IDs and unchanged evidence in this note before any merge.

## Frozen independently recomputed observations
59 ledger rows, 38 unique future event windows, 21 duplicate issuances; 8 overlaps excluded, 30 nonoverlapping events, 12 pending future targets and 18 scored / 7 correct. All 45 observed price arithmetic calculations internally consistent; actual down 4 (0 hits), up 2 (0 hits), flat 12 (7 hits), two historical origin-session dates (2026-10-28/29). Not independent exchange data; no executable bid/ask, post-receipt costs or untouched follow-up confirmation. Existing report `research_cycle_verified` is **not** proof of timing usefulness. No user completion notification.

## Execution evidence
Pending bounded RED/GREEN runs. Unchanged main/immutable production rows.
