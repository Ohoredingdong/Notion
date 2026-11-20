# 2026-11-19 research addendum: newly scored Nov 18 US daily + intraday windows (read-only diagnosis)

**Status:** observed frozen-vector failure diagnosis only; **no new model-recipe or hyperparameter trial**, no production change, no promotion, no trade approval. This is an addendum on the already-open research branch behind PR #151. It was written **after** the target outcomes were observed; it is **not** a preregistered new candidate, independent untouched confirmation, backdated publication, or user notification.

## Frozen provenance, prior work and testing budget

- Operating `main` fixed at **`b8036a4c170f0e6ff0a41b9b1b9960ce8d64eaa9`**. Compared with preceding checked main `7379136769c7ea3e7b51543e42f043dd907d7c2e`.
- Immutable source blobs in the current operating snapshot: original ledger `552601dbcc23a862c8b5bc1569b0426787f13c86`, provider-price outcomes `c0696a452f2ce27377baa498e41ee34e855d62bf`, eligible learning events `cf999879e2c1901b29ce9496b1e5551d2a177f2a`, delivery evidence `bccdeb131cf557d4341c9a08fddc0fd21d06bbf7`, attempts `cb5488e306cde7693f9cd3ffbd7b5caf87f3338b`.
- These five append-only files were checked byte-for-byte against the preceding main: ledger **713 → 725 (+12)**, outcomes **667 → 691 (+24)**, eligible learning **558 → 582 (+24)**, deliveries **108 → 109 (+1)**, attempts **4,024 → 4,064 (+40)**. Every old byte remained an exact prefix; older mistakes were **not** removed. Learned model state and generated reports changed as expected; that does not constitute a new recipe trial.
- Prerequisites checked: `docs/stock-timing-acceptance-20261029.md`, `docs/stock-direction-specialists.md`, `docs/stock-bounded-autopilot.md`, merged immutability/source-binding **PR #146**, draft failed recent-daily **PR #147**, and its original `docs/experiments/recent-daily-model-20261110.md` and `recent-daily-model-20261110-results.md` on branch `research/recent-daily-model-20261110`. This branch's earlier research and public-verification PR #149 were checked to avoid duplicate engineering changes.
- Former PR #147 one-recipe historical diagnostic **2,520 targets** were already used, and original artifact **13750188846** shadow **20/20** were previously scored separately (**2/20 candidate**, not an untouched check). No tuning, model family/parameter selection, rewritten neutral-band, changed symbol set, retimed target, fabricated probabilities or enlarged trial budget occurred here. **New model hypotheses attempted this run: 0/1.**
- Real execution: [Stock Prospective Forecasts #44416733563](https://github.com/Ohoredingdong/Notion/actions/runs/44416733563) collected 40 groups, froze **12 new next-session forecasts** (not scored now), added **24 new eligible observed outcomes** and **24 learning events**, with **0 promotions**. Exact public forecast/code HTTP verification finished **2026-11-18 23:02:38 UTC**; 10 new paper first-public checks succeeded, **0 human receipts**. Linked actual [Independent Forecast Evidence Audit #44417353859](https://github.com/Ohoredingdong/Notion/actions/runs/44417353859) independently audited the committed evidence; bounded-recovery run #44417353962 was *skipped*, not a recovery success.

## New evidence and falsifiable diagnostic (not new model fitting)

Hypothesis under inspection: **the current frozen model fails to identify both rising and falling moves, often calling flat in the intraday window; its higher apparent accuracy may merely follow many actual flat outcomes.** Test budget was **one descriptive paired frozen-vector comparison** on *all* 24 newly scored rows, with no adjustment after observing labels. The comparison is diagnostic only; it cannot select or validate another model. Subsequent confirmation must consist of **separately frozen, later unobserved targets** and the unchanged minimum/stop rules, including a distinct untouched final block.

1. **US intraday**: 12 original target windows **2026-11-18 19:40–20:10 UTC**, forecasts originally issued **19:11:23 UTC**, first public at **19:12:26 UTC**. Source price/result actually checked only **23:01:36 UTC**, after target end. **Actual down/flat/up = 1/7/4; active correct 6/12**. The active model called **down 1, flat 11, up 0**. Down precision 0/1, recall 0/1; up precision undefined (zero calls), recall 0/4; flat 6/11 precision and 6/7 recall. Five true directional moves were missed.
2. **US daily**: 12 original target windows **2026-11-18 14:30–21:00 UTC**. Eleven original issues **2026-11-17 23:50:20 UTC** and one FN issue **2026-11-18 04:44:12 UTC**, with original first-public at 23:51:10 or 07:10:56 UTC respectively, all before target. Post-target observation **23:01:36 UTC**. **Actual down/flat/up = 4/7/1; active correct 3/12**. Down precision 1/4 and recall 1/4; up precision 0/3 and recall 0/1; flat precision 2/5 and recall 2/7. All class thresholds are the **original frozen per-row neutral bands**.
3. **Combined descriptive accounting:** active **9/24 (37.50%)**, Brier **0.638765**. Actual down/flat/up **5/14/5**, active calls **5/16/3**; down **precision 1/5 (20%), recall 1/5 (20%), missed 4, false calls 4**; up **precision 0/3 (0%), recall 0/5 (0%), missed 5, false calls 3**; flat **8/16 precision (50%), 8/14 recall (57.14%)**. **This pooling is for error accounting only**: the daily and intraday windows overlap, the 12 names repeat, and the observations share a single market day. These are NOT 24 independent nonoverlapping future targets nor 20 market observation days.
4. Original contemporary frozen vectors on **exactly the same 24 target IDs, no refit**: incumbent **9/24** (Brier 0.638765); frozen training-frequency baseline **12/24** (0.583169); online shadow **10/24** (0.656186); balanced linear **7/24** (0.688743); balanced nonlinear **7/24** (0.706103); `movement_then_direction` **10/24** (0.648197). Balanced nonlinear did catch 4/5 falls but missed 3/5 rises and called flat correctly on only 1/14; balanced linear caught 2/5 in each direction but missed 11/14 flats. **No candidate satisfies two-sided dominance and risk/probability criteria.** These results are *already seen*; they cannot be mined for an apparently successful new recipe and then relabeled an untouched confirmation.

### All 24 originally issued calls retained (real provider-price returns, %; NOT trading P&L)

| Mode/window | Symbol | Frozen call | Post-target class | Return % |
|---|---|---|---|---:|
| Intraday 19:40 | ^GSPC | flat | flat | +0.117139 |
| Intraday 19:40 | ^IXIC | flat | flat | +0.095794 |
| Intraday 19:40 | AAPL | flat | flat | +0.039747 |
| Intraday 19:40 | MSFT | flat | flat | +0.042342 |
| Intraday 19:40 | NVDA | flat | up | +0.232059 |
| Intraday 19:40 | ON | flat | down | -0.267977 |
| Intraday 19:40 | FN | down | flat | +0.031678 |
| Intraday 19:40 | DOCS | flat | up | +0.293830 |
| Intraday 19:40 | EXLS | flat | flat | -0.094364 |
| Intraday 19:40 | AMZN | flat | flat | +0.029955 |
| Intraday 19:40 | TSLA | flat | up | +0.415479 |
| Intraday 19:40 | META | flat | up | +0.254781 |
| Daily 14:30 | ^GSPC | down | flat | -0.435854 |
| Daily 14:30 | ^IXIC | up | flat | -0.229881 |
| Daily 14:30 | AAPL | flat | flat | +0.164838 |
| Daily 14:30 | MSFT | up | flat | +0.629570 |
| Daily 14:30 | NVDA | up | down | -5.169920 |
| Daily 14:30 | ON | flat | down | -2.168216 |
| Daily 14:30 | DOCS | down | down | -1.793146 |
| Daily 14:30 | EXLS | flat | down | -1.343460 |
| Daily 14:30 | AMZN | flat | up | +3.052228 |
| Daily 14:30 | TSLA | down | flat | -0.381630 |
| Daily 14:30 | META | down | flat | -0.657579 |
| Daily 14:30 | FN | flat | flat | -0.305261 |

## Independent arithmetic/reproducibility, failure modes, and stop rule

An independent JS implementation (not importing the Python predictor/auditor) joined **725** frozen forecasts, **691** original outcome rows and **582** unique eligible learning records by original immutable ID. On **all 691** outcomes it recomputed `100*(target_close/target_open - 1)`, mapped to original `neutral_band_pct` (strictly up if > band, down if < -band, otherwise flat), checked original predicted class, correctness and three-class Brier sum. **0 mismatches**; **0 duplicate eligible learning IDs**. The newly added 24 outcomes all link to original frozen forecasts, all have target-end before source-check, and all 24 match original verified-before-target delivery records by prediction ID and **exact first-public verification time**; **0 mismatches**. This is internal data/chronology consistency, **not exchange-authenticated candle, KRX/NXT/US venue, order-book quote, user receipt, or execution evidence**.

**Cumulative with every old error retained:** **245/582 (42.0962%)**, by version: `direction-forecast-1.0` **69/208**, `direction-forecast-1.1` **176/374**. Current full operating directional count: up **19/88 precision (21.59%), 19/121 recall (15.70%), 102 missed, 69 false calls**; down **29/68 precision (42.65%), 29/205 recall (14.15%), 176 missed, 39 false calls**; flat **197/426 precision (46.24%), 197/256 recall (76.95%)**. Do not compare these pooled overlapping targets as 582 independent statistical events. Attempts **4,064**, predicted attempts **1,604**, no-calls **2,460**, raw attempt coverage **39.47%** (not market-wide coverage). The prior total **236/558** has not been overwritten. **0/40** active groups meet the original group-specific `>=120` nonoverlapping targets / `>=20` observation-day minimum.

Newly frozen 12 next-US-daily forecasts from the latest run target **2026-11-19 14:30–21:00 UTC**, in the future of this examination; do not label or learn them now. There are also **12 missing post-target outcomes**, **68 non-timely-public outcomes**, **20 future target records**, **21 repeat issues**, and **22 overlapping exclusions** in the independent census; none is silently promoted to eligible.

**Result:** failure pattern reproduced, **not repaired by guessing a new direction**, no code defects newly demonstrated. New model hypotheses/refits/optimization attempts = **0**; research-only source-bound diagnosis = **1**; operational model swaps/code fixes = **0**. The original PR #147 recent-daily candidate had worsened up recall, including the already-used 2,520-target historical window; it remains held. No additional model search may reuse this cohort for model selection. A *future* candidate would need **prior** registration of recipe, data-availability clock, exact eligible validation cohort, untouched later confirmation block, testing budget and stop rules, followed by separately frozen forward forecasts before future outcomes exist. Existing `movement_then_direction`, original baseline and strict-green-1.0/12-test gates must remain unchanged.

**Acceptance:** `timing_utility=not_proven`. The independent audit found zero arithmetic/lineage errors, but zero qualifying groups, no verified human receipt, no exchange-grade raw quote evidence, no after-fees/tax/spread/slippage paper edge, and no untouched independent follow-up. No live orders or money, new external authentication, secrets/accounts, pricing-band/policy/threshold changes, unrelated scheduler or separate monitor edits. No user completion notification warranted.
