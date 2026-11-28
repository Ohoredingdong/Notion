# Recent daily model: archived 20 shadow forecasts, later same-target provider outcomes (2026-11-13)

**Research-only appendendum.** This is not a new model recipe, parameter search, production ledger issue, user delivery or acceptance/promotion. Existing preregistration and failed historical experiment remain intact at `docs/experiments/recent-daily-model-20261110.md` and `docs/experiments/recent-daily-model-20261110-results.md`. Original experiment recipe budget remains **one**; **zero** new model recipes or predictions were generated in this check. The 2,520 previously examined historical targets are already used for model selection and may not be relabeled as untouched confirmation.

## Immutable input identity and chronology

- Frozen research source: [Research Recent Daily Model Actions #42790476451](https://github.com/Ohoredingdong/Notion/actions/runs/42790476451), `recent-daily-model-one-recipe-proof`, **artifact ID 13750188846**, GitHub and downloaded ZIP SHA256 `f8f4592b3437a368377418d926797b519cc6bf943c238dd2ffdf6e13ff176077`.
- Original **20** research-only `fresh_shadow` predictions issued Nov 10, 2026 between `09:25:26.892675Z` and `09:25:38.614277Z`, each with frozen candidate probabilities, contemporaneous incumbent and `movement_then_direction` reference probabilities, original neutral band, target start/end and provenance. Not public-issued operating forecasts; `human_notification_received` and executable quote validation are **not proven**.
- Subsequent price evidence read, without modifying any rows, from main commit `6b74b4a4afd703a18e8575103c23512b9cbe731f` at Nov 13, 2026, 16:25 KST: `stock-forecast-outcomes.jsonl` immutable blob `61dabb7550c51776cf3a3121f2034488dcbd3f5d`. Compare with original main operating ledger blob `77b270a33048dfabd29ff7cf950b8b1080bdcfb1` only for independent source identity; **never** treat research shadows as those operating rows.
- Matching method: one and only one actual observed outcome per (symbol, `daily`, exact target.start, exact target.end), **20/20** matches. US 12 targets: Nov 10, 14:30–21:00 UTC (price checked Nov 10, 21:27 UTC); KR 8 targets: Nov 11, 00:00–06:30 UTC (checked Nov 11, 07:52 UTC). Original shadow target times, neutral bands and predicted probabilities were held fixed; actual class was independently recalculated from stored `(close/open-1)*100` and that exact original shadow band. No new backdated probability, outcome, issuance or learning event was created.
- Research calculation performed with a standalone Python JSON/ZIP oracle and **separate Node.js** re-implementation, all 20 per-symbol results and aggregate confusion, Brier and log loss matched. This is *independent code arithmetic*, **not** independent exchange-market data authentication. The prices came from the same originally archived single-provider research collection, not official KRX/NXT or US exchange candles/quotes.
- There are **two correlated market-date clusters**, not 20 trading days or 20 independent temporal confirmations. Research comparison uses identical 20 target events for all 3 already-frozen recipes, but this cohort was not an untouched independent confirmation after candidate selection, and it was not received as a user alert.

## 20 later observed targets: first frozen research-shadow score

Actual classes: **up 9, down 5, flat 6**. Precision is correct among calls; recall is captured actual directions. A direction with zero calls has **null precision**, never 100%.

| Originally frozen recipe | Correct | KR / 8 | US / 12 | Up recall | Up precision | Down recall | Down precision | Brier (lower better) | Log loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| recent_daily_logistic_v1 (research candidate) | **2/20 (10.0%)** | 0/8 | 2/12 | 0/9 | 0/4 | 0/5 | 0/4 | 0.784095237 | 1.277588267 |
| Frozen contemporaneous incumbent reference | **3/20 (15.0%)** | 3/8 | 0/12 | 1/9 | 1/6 | 0/5 | 0/1 | 0.790293884 | 1.301089870 |
| Frozen movement_then_direction reference | **6/20 (30.0%)** | 2/8 | 4/12 | 0/9 | null (0 calls) | 0/5 | null (0 calls) | 0.739927730 | 1.193153834 |

Candidate **up:** actual 9, called 4, hit 0, missed 9, false calls 4; **down:** actual 5, called 4, hit 0, missed 5, false calls 4; **flat:** actual 6, called 12, hit 2, missed 4, false calls 10. Candidate's small Brier advantage over incumbent (0.784095 vs 0.790294) is not a directional edge: candidate missed **all 14 actual directional events**. `movement_then_direction` had a better total score only by calling **flat on every one of the 20 events**, also missing all up/down moves. These cannot be certified as two-direction improvement. Candidate history score **997/2,520 (39.56%)** is a retrospective, previously used diagnostic; it must NOT be substituted for this **2/20** archived shadow follow-up or the original operating prospective score.

| Symbol | Market | Actual (saved provider price + original band) | Candidate frozen call | Incumbent frozen reference | movement_then_direction |
|---|---|---|---|---|---|
| 000660.KS | KR | up | flat | flat | flat |
| 005380.KS | KR | flat | up | flat | flat |
| 005930.KS | KR | up | flat | flat | flat |
| 035420.KS | KR | flat | down | flat | flat |
| 207940.KS | KR | down | flat | flat | flat |
| 403870.KQ | KR | up | flat | flat | flat |
| ^KQ11 | KR | up | down | up | flat |
| ^KS11 | KR | up | flat | flat | flat |
| AAPL | US | down | flat | flat | flat |
| AMZN | US | up | flat | flat | flat |
| DOCS | US | flat | up | up | flat |
| EXLS | US | up | flat | flat | flat |
| FN | US | down | flat | flat | flat |
| META | US | flat | flat | down | flat |
| MSFT | US | down | flat | up | flat |
| NVDA | US | down | up | up | flat |
| ON | US | up | down | flat | flat |
| TSLA | US | up | down | flat | flat |
| ^GSPC | US | flat | up | up | flat |
| ^IXIC | US | flat | flat | up | flat |

## Explicit decision and unchanged safeguards

**Reject production promotion.** The sole preregistered candidate already failed the historical up-recall non-regression gate, and this frozen forward research cohort shows up/down recall both zero. One 20-target cluster comparison cannot meet per-group **120 non-overlapping future targets, 20 observation days, balanced precision/recall/Brier**, let alone a separate untouched verification period or practical after-cost trade timing. Do not tune this used period again or select only winning stocks. No main commits, original ledger/outcomes, learning state, prior failures, first-issue times, data monitor, user alert system, strict-green-1.0 checks, trading permissions, or policy thresholds are changed. `timing_utility=not_proven`.

Known remaining evidence gaps: independent exchange-authenticated source candles / executable bid/ask, genuine signal/user receipt, after-cost forward paper rules/results, proper eligible-market opportunity coverage, and untouched subsequent validation. The shadow artifact itself is not evidence of timely public user delivery or a trade fill. This report is an **archival new outcome analysis**, not a new predictive model experiment or a claim that all future moves can be 100% predicted.
