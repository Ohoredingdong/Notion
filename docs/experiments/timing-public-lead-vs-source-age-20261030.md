# Public-before-target is not actionable receipt — fixed-pin timing audit (2026-10-30)

## Scope, independence, and prior work

**Pinned main:** `0b468558e0d42191b1d5039b2af81c41266746b0`; cutoff **2026-10-30T08:44:39Z**. This is an **exploratory, read-only operational-timing diagnostic on already examined evidence**, NOT a preregistered model-selection test, novel forward labels, external quote verification or an untouched subsequent confirmation block. No performance threshold is revised. See the acceptance contract, direction-specialists policy, bounded-autopilot policy, prior audit/freshness experiment and PR #66's paired-score/shadow negative controls. This note adds a distinct *public lead versus underlying source age versus human receipt* comparison; it does not repeat the PR #66 model-selection experiment or change its results.

Read-only source blobs at the pinned commit:
- First-issue ledger `stock-forecast-ledger.jsonl`: `b1af95894d1dd49ae7a0d86f19cda347d3200f08` (77 records).
- Stored results `stock-forecast-outcomes.jsonl`: `2e4213bcca37c17a4e2feee327f702437e048b0b` (57 records).
- Public webpage verifications `stock-forecast-deliveries.jsonl`: `51daccada19b8e8dc20160da9c3f82807ccbd7b1` (21 records).
- Learning events `stock-forecast-learning-events.jsonl`: `4896e537f99e7468f3d8fe8cf9433912f104f9be` (30 recorded updates).
- Research controller `stock-forecast-autopilot.json`: `2497c43a76f8bf553f915ccbdc65d40173b8b53d`; autopilot events `36b626427888c93af56e7a4b772d31b6eb71895a`.
- Source cooldown `stock-forecast-source-state.json`: `561f588f3fde46e738dc1a2a6e0251b457eaf6bf`.

## Reproducible independent measurement

Sort original ledger rows by `issued_at`. Retain the *first* record of each exact `(symbol, market, mode, target.start, target.end)`; do not replace that original forecast with a later revision. For each such unique record find its earliest delivery row where `status=public_verified`, `prediction_ids` includes its original ID, and `issued_at <= snapshot_generated_at <= verified_at`. Define `public_lead_minutes = (target.start - verified_at)/60,000` and `source_age_at_issue_minutes = (issued_at - observed_until)/60,000`. A verified webpage is NOT an actual user's receipt. Neither interval is an executable bid/ask quote.

For performance accounting only, additionally choose nonoverlapping target intervals within each symbol/market/mode/policy group in ascending target order, independently of actual direction. Only score when target.end elapsed, the first issuance was verifiably public before target.start, and a stored outcome exists. Independently recompute each stored return, frozen-band actual label, correctness, three-class Brier, and source/evaluation chronological checks. Do not treat six matured but unobserved targets as losses, or twelve future targets as wins. Do not mix US regular/extended sessions or Korean KRX/NXT.

## Actual read-only results

77 issued rows -> 56 unique targets (21 repeated issuances); eight overlapping windows excluded -> **48 nonoverlapping**. **30 eligible scored / 11 correct** from the **same previously examined labels**, six matured outcome-missing and twelve future. In those 30: actual down 7/hit 1/missed 6, up 8/hit 1/missed 7, flat 15/hit 9/missed 6. The stored 57 outcomes' price-return, direction, correctness, Brier and source/evaluation time arithmetic yielded **zero internal discrepancies**. Original frozen-baseline matched subset: model 7/18, Brier 0.6239 versus baseline 9/18, Brier 0.5966. These are NOT new successes, training updates, exchange prices, or after-cost trades.

**All 56 unique targets** have a recorded qualifying webpage-public verification before the target begins; **zero** proof rows establish actual human notification receipt. For the 26 **KR intraday** unique targets, webpage lead ranges **9.58–13.66 min**, median **10.45 min**. Underlying provider observations were **15.21–19.29 min** old at issuance (median **18.61 min**). These numbers do not establish a fresh executable quote *at the moment of user action* or a particular KRX/NXT venue, and the apparent lead does not override delayed-source status. The other unique target groups: US intraday n=6, public lead median **27.56 min**; US daily n=12, median **904.72 min**; KR daily n=12, median **3883.78 min** (includes nontrading-day gaps and is not a market-feed delay diagnosis). Across the 30 scored targets, minimum public lead **10.34 min**, median **27.56 min**. All market groups remain separately labelled.

**Critical separation:** recorded public webpage availability 56/56 is evidence of a public response only; **0/56 human push/recipient acknowledgements** and **0/56 independently authenticated executable post-receipt bid/ask observations** are available. It would be invalid to call the signals user-actionable or to manufacture free fills, taxes, spread, slippage, shorts, a completed paper strategy, or trades from those timestamps.

## Executable workflow context and decision

- [Stock Prospective Forecasts run 41020130012](https://github.com/Ohoredingdong/Notion/actions/runs/41020130012): successful 2026-10-30 07:27–07:28 UTC; logged **24 delayed-history source groups, 0 new forecasts, 0 new learning updates**, zero promotion, diagnosis `missed_up_moves` and `missed_down_moves`.
- [Independent Forecast Evidence Audit run 41021892136](https://github.com/Ohoredingdong/Notion/actions/runs/41021892136): successful 07:44 UTC, **30/11** and 30 learning events, a successful integrity check—not proof of signal effectiveness.
- [Stock Autopilot Bounded Recovery run 41020343840](https://github.com/Ohoredingdong/Notion/actions/runs/41020343840) skipped because no eligible recovery was required. Earlier [41018873579](https://github.com/Ohoredingdong/Notion/actions/runs/41018873579) requested a single permitted infrastructure retry; a request is not proof of successful repair.
- Pinned controller remains `research_cycle_verified`, `timing_utility.status=not_proven`, `promotions=0`; scheduled GitHub workflows are not an always-on market feed.

**Decision:** The 120-target/20-day per-group minimum, both-direction improvement, real recipient evidence, independent executable quotes, precommitted *after-cost* prospective comparison, untouched follow-up and independent reproduction remain unmet. No actual new data-integrity defect is demonstrated by this diagnostic; therefore **no operational code/model/UI/threshold/recovery change is justified by the existing labels**. Preserve existing forecasts and errors unchanged. A future *distinct* experiment may assess realized transmission and eligible venue quotes, but only after lawful point-in-time quote/receipt evidence exists and its protocol is fixed **before** looking at outcomes.

**Trial accounting:** one exploratory operational-provenance diagnostic, **zero** additional model recipes, hyperparameter trials, revised selection thresholds, fitted models, promotions/rollbacks, retroactive probability vectors, re-learning events, shadow output publications, fake quotes, real orders, API/credential changes or new user-required actions. No completion or perfection notification. No changes to strict-green-1.0 or the separate stock data-error watchdog.
