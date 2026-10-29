# Timing evidence experiment 2026-10-29: snapshot-publication chronology guard

Base main commit (pinned): `a2ffb87d494af3ff04d1d5fc0c011ea51ad608fa`.
Research branch: `research/timing-delivery-snapshot-20261029`.
Pre-registered before editing audit logic.

## Hypothesis and scope

The independent read-only auditor currently derives first public availability from the `public_verified.verified_at` timestamp and the set of `prediction_ids` without checking `snapshot_generated_at`. A malformed published record could list a prediction issued *after* the supposedly published snapshot was generated, yet be scored as prospectively available. This is an evidence-integrity guard only; it cannot improve future directional accuracy, guarantee a timely human notification, validate exchange prices, or prove trading utility.

## Counterexample (synthetic, not a production price)

Original forecast: issued 13:36 UTC, future 14:00–14:30 UTC target; an internally consistent outcome exists. A published delivery entry says snapshot generated 13:35 UTC (before the call), verification at 13:37 UTC (after the call), containing the forecast ID. The prior auditor would accept this as timely because only `verified_at` is tested. Expected stricter behavior: reject that publication claim for forward scoring. Also reject snapshot generation later than verification. Do not backfill another public time from forged/invalid evidence.

## Existing data and independence

At the pinned commit: 47 ledger rows, 26 event keys, 21 duplicate issuances, 18 non-overlapping future targets, 6 eligible scored; 21 observed outcomes include overlaps; 11 published-snapshot records have 122 forecast-ID links. Independent reread found zero `issued_at > snapshot_generated_at` and zero `snapshot_generated_at > verified_at` among the existing links. Outcome arithmetic, stored label thresholds and directions match on all 21 raw outcomes; only six are independently eligible. This is stored-price evidence, not an external exchange or executable quote audit. No human notification receipt, cost-after-execution comparison or untouched future validation exists.

## Test and change boundary

First add a deliberately failing reproduction test to `scripts/audit_stock_forecast_independent.py` on this branch and capture the CI failure. Then add the minimal guard in the independent audit's delivery map. Preserve existing immutable forecast, outcome and publication records. Run auditor self-tests and the full pinned evidence audit on a branch-only GitHub Actions runner. Compare scored counts, direction counts, and status to the pinned base. No automatic orders, model changes, green approvals, threshold changes, or main publication. Leave research unmerged if regression/tests fail.

Candidate experiment count: 1. No optimization to observed outcomes. No promotion based on test success.

## Acceptance status

Direction/after-cost timing/untouched holdout/human receipt: **unproven** regardless of this engineering test. Notify user only if the separate timing-utility acceptance contract is fully met; this integrity patch is not a completion notice.

## Executed results (2026-10-29)

- **Counterexample reproduced before the fix:** on branch commit `0687872c562cd5ede12e4416ac4cdf6ce3950f8c`, [GitHub Actions failure 40881522849](https://github.com/Ohoredingdong/Notion/actions/runs/40881522849) shows `test_snapshot_created_before_forecast_cannot_be_claimed_as_public` failed with `AssertionError: 1 != 0`. A forecast issued after snapshot generation was incorrectly accepted as publicly available.
- **Minimal patch:** `scripts/audit_stock_forecast_independent.py` checks both `snapshot_generated_at <= verified_at` and each included forecast's `issued_at <= snapshot_generated_at`. Any invalid or missing timestamp is an explicit integrity error; do not count it as a timely public forecast. Historical rows are untouched. Previous ordinary synthetic public fixture now includes a coherent snapshot-generation timestamp.
- **Regression and independent recomputation passed:** at commit `d031584d563909c122b4d5e1323659c4d523d72e`, [GitHub Actions success 40881748652](https://github.com/Ohoredingdong/Notion/actions/runs/40881748652) ran the new three-case chronology counterexample, auditor self-tests, existing forecast/model/learning/autopilot test suites, and a fresh independent read of the pinned ledger/outcomes/deliveries. The original six eligible calls, three correct, arithmetic consistency, lack of exchange-candle validation and lack of human notification receipt remained unchanged.
- The temporary branch-only CI workflow was deleted after its successful run; it does not change main scheduling or credentials.
- **Outcome:** evidence-integrity bug fixed in research branch only. This is **not** a new or improved prediction result, an executable quote source, or proof of cost-after-entry timing value. No model promotion, revision to strict-green, or live orders.

## Follow-up gates

Review diff and merge audit-only code/doc without mixing UI or source refresh. Main audit can run with the guard; separately track time-stamped source candles, human receipt and fixed-cost prospective execution validation. Never count today's historical 6 cases as new forward evidence.
