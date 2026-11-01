# Research only — logical forecast attempt replay guard (2026-11-02 KST)

Pinned base main: `52dacc45bb060e4edf62a7871dbd878d59e61b81`.

## Preregistered narrow hypothesis
The independent scheduler-attempt auditor detects repeated *row IDs*, but can still accept a second row with a **different ID and the identical (workflow run ID, checked UTC instant, symbol, mode)** when the public coverage summary is recomputed to match the forged extra row. This would count one logical scheduler check twice without adding a new frozen forecast or actual trading opportunity. This is an audit-hardening hypothesis, not evidence of actual tampering or better forecasting.

## Existing evidence and contrasts
- Read three approved contracts `docs/stock-timing-acceptance-20261029.md`, `docs/stock-direction-specialists.md`, `docs/stock-bounded-autopilot.md`; retain all thresholds and shadow-only candidates.
- Frozen attempt blob `d93539cbf69b4a66daa3a3aa6b8e83969712bd2e`: 672 rows = 310 reference calls + 362 no-calls, 27 run IDs, 28 clock batches. GitHub Actions run `41018457023` has `run_attempt=2` and two genuine 24-group batches with **different** checked timestamps; these MUST continue to pass.
- One rerun group's first outcome was deferred, later outcome was a valid already-frozen forecast reference; this is not extra forward performance. Raw attempt call rate = 310/672; first/last run-group sensitivity is descriptive, not performance.
- Immutable forecast ledger blob `1f254b2302dc1350ad95363ac4fbba5a4b145a46` contains 89 rows, 68 unique targets; 60 nonoverlapping. Frozen 69 outcome rows yield 42 scored, 13 correct and Brier 0.6493241094; public verification and 42 learning events are unchanged.

## RED before code change
Add synthetic tests to `scripts/test_stock_timing_attempt_coverage.py`:
1. Same logical scheduler check but a fresh row ID and recomputed headline counts MUST be rejected.
2. The same instant in a different timezone offset MUST still count as the same logical check.
3. Two rerun checks with the same run ID/group but **different** UTC instants MUST remain accepted.
4. A copied no-call with a fresh ID and revised no-call summary MUST be rejected.
An initial RED is valid only if tests (1), (2), (4) fail specifically because `duplicate_logical_attempt` is not returned, with original controls still GREEN. Do not claim a failing test proves actual ledger corruption.

## Minimum implementation, independent GREEN gates
Use only `(run_id, checked_instant(checked_at), symbol, mode)` as the logical identity. Keep row-ID checks, timestamp checks, raw evidence and all counters unchanged. Do not collapse, delete, restamp or regenerate existing attempts. Add the two audit/test paths to PR-triggered independent-audit workflow checks so future auditor changes execute on PRs. Require all independent audit tests, the actual immutable-data audit and PR regression to pass. Since no UI, predictor, data, published JS or model changes are proposed, a new public widget build does not validate this guard. Do not merge if required CI fails.

## Boundaries
No orders or funded paper trades; no invented exchange quotes, execution receipt or new samples; no source/model/forecast edits; no strict-green-1.0 changes; no widened bounded autopilot recovery. Existing 24-group 120/20 gate, after-cost paper edge, untouched follow-up and human receipt all remain unmet; timing utility `not_proven`. Keep unsuccessful attempts and the test count in the PR experiment log.
