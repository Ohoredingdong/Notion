# Frozen forecast evidence row-status integrity — preregistered 2026-10-30

Pinned main: `d33c5269ab75347edd71d8105f74e9301c107188`.
Research branch: `research/timing-evidence-row-status-20261030`. Acceptance: `timing-utility-acceptance-1.0`.
One fixed engineering hypothesis, zero model candidates/tuning attempts; testing synthetic rows only.

## Hypothesis before modifying audit
The read-only independent auditor silently skips every forecast-ledger row whose `status` is not `research_prediction`, and every stored outcome row whose `status` is not `observed`. Those are **the only documented row types in these append-only evidence files**; `no_call` belongs separately in `stock-forecast-attempts.jsonl`. Consequently, mutating a pending frozen forecast to `no_call`, or mutating an observed outcome to an unknown status, can remove evidence from denominator / audit checks while the independent audit still reports `ledger_arithmetic_consistent`. This is a code-level evidence omission; no claim of actual evidence manipulation or model skill improvement.

## Reproduction and acceptance (do not inspect future test labels for model selection)
1. Synthetic forecast with valid first-issue times, unknown/suppressed status and future target must produce `integrity_errors` instead of disappearing. Control valid forecast remains accepted.
2. Synthetic observed outcome whose `status` is changed to an unexpected value must produce `integrity_errors`, not merely `missing_outcomes`. Control correct outcome remains accepted. These are append-only ledger/outcome files, not attempt/no-call logs.
3. Add RED tests *before* changing independent auditor. Capture branch-only failing GitHub Actions, then fail-closed on unexpected statuses in the two evidence files. Do not alter valid eligibility, target selection, count scoring, source or production publisher.
4. Run GREEN test, all audit and learning checks, stored actual 65 ledger, 45 outcomes, 17 public verifications and 18 eligible / 7 correct at pinned baseline. Confirm 59 modern bands, the 18 learning events, strict-green and no orders unchanged. If tests fail, leave branch unmerged.
5. Retain tested synthetic test as an existing audit CI step, remove branch-specific workflow before PR merge; only audit code, regression test, note and audit-workflow test invocation can reach main. No UI change, live feed claims, or prediction learning modifications.

## Baseline independent read (pinned, 2026-10-30 04:20 UTC)
- All existing 65 ledger statuses = `research_prediction`; 45 outcome statuses = `observed`. Attempt log separately contains 173 `no_call` and 139 research attempts.
- 44 distinct target events, 21 reissuances, eight overlapping targets, 36 nonoverlapping, 12 not-yet-matured, six eligible missing outcomes, 18 forward scores, 7 correct across two origin sessions. All actual down 4 and up 2 were missed; 7 of 12 actual flats hit. Not independently verified exchange prices.
- 17 `public_verified` webpage checks, zero confirmed human alerts, and no executable quotes / post-fee prospective strategy or independent untouched follow-up. Thus timing usefulness remains **not proven** irrespective of audit results.

## Test accounting and restrictions
Exactly one predeclared hypothesis with two negative subcases and control cases. No hypothesis search, no historical model probability backfill, no repeated learning, no parameter promotion, no real orders, no token or account operations. Preserve all recorded predictions, outcomes, deliveries, learning, attempts, original approval policy, strict-green-1.0, and other workflows. Record RED/GREEN URLs and failed attempts before any merge. No user completion notice unless every independent timing-utility acceptance criterion later passes.
