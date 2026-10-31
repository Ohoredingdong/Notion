# Research-only: pin forecast checkout to the triggering event SHA (2026-10-31)

Status: preregistered engineering hypothesis; **not a verified production incident or a predictive improvement**.

## Frozen basis and prior work
- Frozen source: main `6b2e5cd94e14987c6cb510bbe0fe9dc94b887518`. Acceptance: `docs/stock-timing-acceptance-20261029.md`; specialists: `docs/stock-direction-specialists.md`; bounded controller: `docs/stock-bounded-autopilot.md`. Do not change any of these.
- PR #83 established independent audit handoff, PR #84 added a fail-closed guard matching an upstream workflow run's `id/head_sha` to archived `run_id/source_commit`. Neither establishes that the upstream forecast's actual checkout matches the SHA it **reports**.
- In `.github/workflows/stock-forecasts.yml`, `actions/checkout@v4` currently requests `ref: ${{ github.ref }}` (the mutable branch ref). Both `scripts/stock_forecast_autopilot.py` and `scripts/run_stock_forecasts.py` record `GITHUB_SHA` (trigger-time commit). GitHub checkout distinguishes a branch ref from an immutable SHA: https://github.com/actions/checkout .
- Actual successful forecast run 41157151233: event `head_sha=f9db984b97b070ceca198ac023667740aebc3497`; checkout log also reported `git log -1=f9db984b97b070ceca198ac023667740aebc3497`. **No production checkout mismatch observed**.

## Pre-registered hypothesis and negative control
If main changes between an event's creation and checkout, a workflow explicitly checking out `github.ref` can execute another commit while the archived controller still declares `GITHUB_SHA` from the earlier event. An audit that compares archived `GITHUB_SHA` to event `head_sha` could then match two identical labels without proving the code actually used. This is an unobserved but reproducible *configuration risk*, not evidence of manipulated trading data.

Before editing the workflow, add a narrowly scoped independent static regression that rejects mutable-ref checkout for the forecast producer; separately verify both producer scripts still use the event SHA provenance. The checkout regression must first fail on the frozen workflow (RED). Expected repair is **one-line** change to the forecast producer's checkout to `ref: ${{ github.sha }}` while retaining `fetch-depth: 0`. The existing publisher's detached worktree fetches current `origin/main` and uses immutable ledger merge / learning-state compare-and-swap; it need not run from a checked-out branch. Job publication is still limited to `github.ref == refs/heads/main`.

## Required verification and limits
- PR branch only: demonstrate RED before the one-line fix; then run the same regression and the existing independent arithmetic/chronology/learning/attempt/acceptance checks (GREEN) without modifying any data files.
- Confirm no changes to forecast model, candidates (including `movement_then_direction`), features, thresholds, strict-green-1.0, approvals, source data, outcomes, history, learning state, delivery times, notifications or orders.
- On merge, confirm the actual changed-file list and independent audit success. A later real forecast workflow using the new checkout, including logged `git log -1` compared with event `head_sha`, remains required to verify production end-to-end behavior.
- No attempt to prove directional edge or trading utility. At baseline: 89 ledger rows, 68 target events, 60 non-overlapping targets; 42 scoreable, 13 correct; 0/24 groups satisfy the prior sample gate. External exchange candles, executable quotes, user receipt, after-cost forward paper performance and untouched follow-up remain unverified.
- Experiment budget: one checkout-provenance engineering hypothesis, one negative regression, one scoped correction. Zero model/candidate trials and zero actual orders.

