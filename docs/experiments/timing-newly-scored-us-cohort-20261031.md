# New US scored cohort: independent, research-only shadow checkpoint — 2026-10-31

**Type:** Read-only diagnostic of outcomes **already visible** when this analysis was run; **not a preregistered model-selection trial**, not untouched follow-up, not external-exchange data verification. This document only records the work. No code, model, candidate, signal, order, data-source, policy or strict-green-1.0 modification is authorized by the result.

**Pinned evidence:** `Ohoredingdong/Notion` main `d1caac061b4f0656166a69aadd02785b76304b50` (source bundle published by [Stock Prospective Forecasts 41139310341](https://github.com/Ohoredingdong/Notion/actions/runs/41139310341), 2026-10-30 22:39 UTC).
- Frozen ledger: `stock-forecast-ledger.jsonl` blob `1f254b2302dc1350ad95363ac4fbba5a4b145a46`
- Stored outcomes: `stock-forecast-outcomes.jsonl` blob `f24b7e93f9aa438b8084e857429dbef99031d8fc`
- Public verification: `stock-forecast-deliveries.jsonl` blob `2bf3a9af0cc4b7fbec6e47ac595f68d8729fc20f`
- Learning events: `stock-forecast-learning-events.jsonl` blob `dff634b1d6c5cf4236b8d5d018f92bfb99bf578c`
- Attempts: `stock-forecast-attempts.jsonl` blob `8e86e3a3187394f930e0a15815e4cfd71ee18252`
- Latest independent audit on [41127359873](https://github.com/Ohoredingdong/Notion/actions/runs/41127359873) succeeded at 20:58 UTC **before** the new bundle; it verifies **30** older scored events, not this newly scored set of 42. Do not claim a fresh, separate main Actions audit of these new events.

## Diagnostic hypothesis / bounded comparison

Question: after 12 US events became observable, did the frozen incumbent or one of the **four already reviewed shadow variants** demonstrate a robust, bidirectional improvement? Compare exactly the **same 12 outcome IDs** evaluated at `2026-10-30T22:38:20.322830+00:00`, using probabilities in each original frozen prediction and unchanged neutral bands, without refitting or choosing a winner. One exploratory inspection of five pre-existing variants; **zero new model/parameter trials**. Prior research [#66](https://github.com/Ohoredingdong/Notion/pull/66) used older scored events, and [#81](https://github.com/Ohoredingdong/Notion/pull/81) assessed *missing* US results before these 12 observations arrived, so neither supplies this scored-cohort comparison.

Reproduction: parse the pinned JSONL files; select each first issuance by symbol/mode/target start/end and exclude overlapping targets per group independent of outcome; join its observed result by frozen prediction ID; require publication after issuance and before target start. Compute `100*(close/open-1)`, classify with the frozen neutral-band percentage, and separately recompute the original direction/correctness and multiclass Brier score `sum((p_k - 1[k=actual])^2)`. For each of the same 12 new observed IDs, compute the argmax and multiclass Brier/log losses from originally frozen `probabilities` (incumbent), `online_learning.challenger_probabilities` (adaptive), and `directional_specialists.candidates[variant].probabilities`. Do not backfill candidate values. Compare using **all** 12 rows, not a cherry-picked success subset.

### Independently recalculated facts

| Frozen variant | New matched outcomes | Correct | Mean multiclass Brier | Mean log loss | Predicted down / flat / up |
| --- | ---: | ---: | ---: | ---: | --- |
| Applied incumbent | 12 | 2 | 0.682774 | 1.114592 | 0 / 7 / 5 |
| Existing adaptive shadow | 12 | 2 | 0.682247 | 1.113728 | 0 / 7 / 5 |
| Existing balanced_linear shadow | 12 | 4 | 0.625525 | 1.029534 | 6 / 2 / 4 |
| Existing balanced_nonlinear shadow | 12 | 4 | 0.652173 | 1.072715 | 3 / 3 / 6 |
| Existing movement_then_direction shadow | 12 | 3 | 0.720981 | 1.138680 | 1 / 10 / 1 |

The six **daily** US events all realized `down`; the six **intraday** events realized four `up` and two `flat`. These are correlated observations from a **single US trading date**. For the incumbent, daily 0/6 and intraday 2/6. For balanced_linear, daily 4/6 and intraday 0/6. These opposite regime sensitivities do **not** justify replacing the incumbent; neither candidate meets the fixed directional, probability-calibration and follow-up gates.

All historical scored cohorts now total **42/60** nonoverlapping target opportunities, with **13/42** correct, directional recalls `down=1/13`, `flat=11/17`, `up=1/12`. Remaining unique nonoverlap targets: **6** outcomes missing source support and **12** future targets. The immutable ledger has **89** issuances, **68** unique targets, **21** reissuances and **8** overlapping targets excluded. The 12 newly observed results add **12** unique learning-event IDs; total 42. The scheduler-attempt file has **552** rows, including **250** prediction attempts and **302** no-calls; do not treat these attempts as 552 independent market opportunities.

Arithmetic checks on the frozen file: **zero** stored return/direction/Brier mismatches, **zero** observation-receipt-issuance/target-start inversions, **zero** learned IDs without an observed outcome, **zero** duplicate learning IDs, and **zero** malformed shadow-probability distributions / argmax mismatches. These are internal checks and do **not** authenticate exchange OHLC or actual executable quotes.

### Decision, limitations and audit status

**No promotion or code change.** This single session is far below the **120 nonoverlapping targets and 20 observation days per group** and the class-specific counts. All five variant scores are exploratory; using the newly seen labels to choose a winner would consume this cohort, so **do not reuse it as untouched confirmation**. The most recent successful separate independent Actions audit predates these 12 new scored rows; a subsequent independent Actions audit must be observed before claiming it verified them.

Public HTML snapshots were verified (last at 2026-10-30 22:39:16 UTC), but **human push receipt is not proven**. Yahoo OHLC internal arithmetic is **not** exchange raw-minute / quote validation. Real post-notification executable bid/ask, spread, fees, tax, slippage, fill likelihood, forward paper P&L and an unselected follow-up block are **not connected / not validated**. GitHub schedule execution is not continuous real-time monitoring. No strict-green approval, order, credential, source, acceptance threshold, original prediction, outcome, learning event or other scheduled task was changed. The correct classification remains `not_proven`.

**Next safe evidence action:** let the existing independent audit run against this published main snapshot, retain its actual logs, and accumulate truly new future eligible outcomes and execution evidence without retroactive patching or additional candidate search. No additional user action was found.
