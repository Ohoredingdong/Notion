# Research-only: frozen outcome provenance assertions (2026-11-02)

## Fixed baseline and preregistration (before injecting synthetic faults)
- Main pinned: `48aa34a6c950d5e6e2556fbc84279151d57b1520`.
- Read the unchanged binding contracts: `docs/stock-timing-acceptance-20261029.md`, `docs/stock-direction-specialists.md`, `docs/stock-bounded-autopilot.md`.
- Frozen input blobs: forecast ledger `1f254b2302dc1350ad95363ac4fbba5a4b145a46`, outcomes `f24b7e93f9aa438b8084e857429dbef99031d8fc`, first-public proofs `aff29efabcc6b3aa56f1eae87e76f1c00a2f96fb`, source-state `cc54c3e77834aa0575d512211643b8b1ddf8f34e`.
- Reviewed previous PRs #92-#99 and #82 experiments. PR #97 already rejects unauthenticated *delivery proof* claims of human notification; PR #96 binds outcome issuance time. This is distinct: checking assertions on the *outcome row* itself against previously frozen, independently read records.
- Existing observed 69 outcome rows all have `public_before_target_verified=true`, `price_observation_not_execution_return=true`, `single_provider_not_execution=true`. Independent pre-target proof join agrees with 69/69 rows. No real tampering or real execution return has been observed.

## One fixed hypothesis and negative control
The independent forecast auditor recomputes actual direction, Brier and earliest publication, but appears not to reject an outcome row altered to claim that Yahoo stored prices represent a trade return, a verified external/executable source, or a different public-before-target state. A forged row could retain correct OHLC arithmetic and pass an audit, letting downstream consumers overstate evidence. This is **an integrity risk in synthetic input**, not evidence that any operational outcome was forged.

**Preregistered synthetic test before any fix:** start from one valid frozen forecast + audited public proof + correctly scored observed outcome. Change individually one of the three outcome provenance booleans (`price_observation_not_execution_return=false`, `single_provider_not_execution=false`, `public_before_target_verified=false`) without altering prices, direction, frozen probabilities or issue/public clocks. Assert that each must return `integrity_errors` with a specific cause. Retain a valid positive control; missing historical optional flags remain absent, not fabricated. A late/missing proof with a contradictory `public_before_target_verified=true` is also rejected. Record **one** test family, not a model-selection search.

## Minimal fix authorized if RED reproduces
- In the read-only independent outcomes loop, fail closed if a **present** `price_observation_not_execution_return` or `single_provider_not_execution` is not exactly boolean true, and fail closed if a **present** `public_before_target_verified` does not exactly equal the UTC relation `forecast.issued_at <= first_valid_public_verified_at < target.start`.
- Preserve legacy missing optional fields without backfilling. Do not infer an external quote, human receipt, execution price, or trade return; only compare existing archived metadata with independently logged evidence.
- Change only `scripts/audit_stock_forecast_independent.py` and this document on a separate research branch; keep test fixture synthetic. Run intentional RED CI, minimal GREEN, standard audit/learning/attempt/acceptance regressions, and post-merge audit and public deployment as applicable. If any fails, leave candidate unmerged.
- Do not alter actual forecasts, outcomes, learning, receipt claims, strict-green-1.0, model selection/promotion, shadow model, provider credentials, orders or unrelated workflows.

## Outcome and limits
- Pending actual RED/GREEN trial and independent CI. This document alone is not a successful fix or predictive improvement.
- Prior score remains 42/13 from frozen first issuance and nonoverlap. All 24 groups fall below 120 future targets and 20 observation days; exchange-authoritative quote/execution, human receipt, after-cost prospective paper edge and untouched follow-up remain unverified. Current usefulness: `not_proven`.
