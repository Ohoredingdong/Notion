# US 2026-11-13 daily forward cohort — independent failure-mode result

Status: **research-only diagnostic PASS; model direction improvement NOT proven; no model selection or operational promotion.** Reviewed after the outcomes were observed; **not** an untouched or prospective preregistration of performance. Read the [pre-code engineering plan](forward-cohort-audit-20261114-plan.md).

## Immutable evidence and independent execution
- Pinned operating main commit `cd774513cfe8667eb4d83d5fd13b40dcdc315341` (2026-11-14 ~01:02 UTC), original Git blobs: ledger `7eace60187c32cafa1bf10b628c2fd33c020de72`, results `e102f7a9cc5b53dad00740d72abc49897c79d896`, learning `f4f61b06a7f39450a263014a8dd0f8aae549c2dc`, public delivery `814bd0cf4e80ffa390adb54f4c29a75b70252183`.
- [Original operational research #43537512282](https://github.com/Ohoredingdong/Notion/actions/runs/43537512282): 2026-11-14 00:58 UTC collection, **12 newly resolved US daily** original forecasts, 12 newly recorded forecasts for later targets, 12 new learning events; 40 research attempts, 18 `research_prediction` references, 22 `no_call`. New 12 outcomes are the **Nov 13 US 14:30–21:00 UTC** regular-session cohort, originally issued before the market target on **Nov 12 23:54 UTC**. This date has already been examined; the next session must be treated separately.
- After the live append: original immutable forecasts **527**, saved price outcomes **493**, eligible learned/scored **416**, distinct first-public verification events **92**. Eligible overall **170/416 = 40.8654%**, up from the original **166/404 = 41.0891%** in count but **not** in accuracy. All 404 older eligible results, including misses, remain intact.
- [Research diagnostic Actions #43538992356](https://github.com/Ohoredingdong/Notion/actions/runs/43538992356) **success** on commit `34e9f7ac01975604cfaf6e987c8f0029e5a8ba14`. **7/7** synthetic negative-control tests passed; a separate **Python standard-library arithmetic oracle** independently reproduced all **six** already-frozen methods' exact 12-row confusion matrices, Brier and log loss: `PYTHON_INDEPENDENT_FROZEN_COHORT_RECOMPUTATION_OK 12 market_date_clusters 1`. Read-only report artifact **14089978814** (short retention); no operating file writes.
- Original outcome math independently matched each saved open/close, original neutral-band class, saved Brier/correctness, learned-after-outcome chronology and timely public verification. On these 12, **no** ID duplicate, label mismatch or time-order mismatch. The same Yahoo-derived saved prices are used by both oracles: this is **not external exchange feed corroboration**.

## One correlated market date, same 12 original events, same frozen forecasts

Actual events: **down 7 / up 1 / flat 4**. A single day of 12 correlated US stocks/indexes is not 12 independent market days. All methods use probability vectors already recorded *before* the exact target; no hindsight threshold or reissue.

| Frozen method | Correct | Down hit / 7; calls | Up hit / 1; calls | Flat hit / 4 | Brier |
|---|---:|---:|---:|---:|---:|
| Operating incumbent | **4/12** | **2/7; 4** | **0/1; 1** | 2/4 | 0.671506 |
| Original frequency baseline | 4/12 | 2/7; 2 | 0/1; 5 | 2/4 | 0.685080 |
| Online learning challenger (frozen) | 3/12 | 0/7; 1 | 0/1; 3 | 3/4 | 0.725183 |
| movement_then_direction (shadow) | 4/12 | **0/7; 0** | **0/1; 0** | 4/4 | 0.677257 |
| balanced_linear (shadow) | 5/12 | 3/7; 5 | 0/1; 1 | 2/4 | 0.657244 |
| balanced_nonlinear (shadow) | 5/12 | 3/7; 5 | 0/1; 2 | 2/4 | 0.618667 |

Precision is **hits / calls** and recall is **hits / actual class**. Therefore the operating down **precision 2/4 = 50%** versus down **recall 2/7 = 28.57%**; up **precision 0/1 = 0%, recall 0/1 = 0%**. It missed down on AMZN, FN, ON, TSLA, and incorrectly called up on NVDA (actual -4.14% under the original band); also missed META actual up. The only **correct down** calls were the two indices `^GSPC` and `^IXIC`; calling the index down and many shares flat did not resolve cross-symbol under-detection. Balanced candidates' 3/7 down recall is a descriptive signal on an **already-inspected**, strongly down-biased day, not an endorsed win; both still missed the only up. `movement_then_direction` selected **flat for all 12**; zero up/down calls implies **null precision**, not perfect precision.

## Gate, research budget, and limits
- The existing minimum is **120 nonoverlapping targets and 20 observed market days per symbol/mode**, plus each actual class and up/down calls at least 10, nonregression of both directions, calibrated probability and unmatched follow-up; this **one-date group fails**. Overall 40 evaluation groups meeting the prior minimum: **0/40**.
- New model recipes proposed/fit/tested in this work: **0**. Previous candidate #147's 2,520 examined historical targets, its already scored 20 shadow forecasts, and the cohort above are not reusable final unseen holdouts. The **39.56%** former historical candidate accuracy and the original **37.5%** forward baseline were produced at different times and must not be conflated.
- As of this source version, remaining original forecasts without saved results: 34, comprising previously immature future targets and earlier unverified Korean intraday segments; no synthetic success/failure was assigned. Research scheduler attempts **3264**, with **1285 research prediction attempts** and **1979 no-calls**; this is scheduler coverage, *not* whole-market opportunity coverage.
- No human receipt is demonstrated: existing public HTTP proof ≠ a delivered user notification. No venue-original intraday candles, authenticated transaction quotes, fee/tax/spread/slippage verified cost schedule or untouched follow-up, hence `timing_utility=not_proven`.
- Read-only tool and workflow have **no production rollout authorization**. Leave operating model and all original errors, PR #146 provenance guards, #147 failed candidate, #150 Korean missing-window diagnosis, strict-green-1.0, and data-error monitoring unchanged. No orders, credentials, paid service, or other schedule changed.

**Decision:** Keep PR #151 draft / do not merge or promote from these results. With the next *previously frozen* forecast cohort, evaluate a new genuinely later date without changing this one, and collect the full two-direction evidence before any candidate selection. A finite past cohort cannot guarantee all future movements or 100% prediction.
