# Research safety: independent audit PR path parity (2026-11-02 KST)

## Pinned sources and preregistered engineering hypothesis (before RED)
- Base main commit: `2384fb490f5e04fef469ba91f1c17f51cefc133c`.
- Read unchanged: `docs/stock-timing-acceptance-20261029.md`, `docs/stock-direction-specialists.md`, `docs/stock-bounded-autopilot.md`.
- Examined immutable forecast ledger 89 rows, outcomes 69, public proofs 31, learning events 42, attempts 696 and latest bounded controller (0 newly frozen, 0 new learning), as well as actual producer, independent audit and skipped recovery Actions.
- Reviewed previous PR #82 research history and merged PR #89/#90/#92–#97. PR #92 added premerge trigger coverage for attempt-audit files only. This hypothesis concerns the remaining independent-audit executable files, not a duplicate logical-attempt or proof-integrity test.

**Hypothesis:** `.github/workflows/stock-forecast-independent-audit.yml` runs some evidence-acceptance tests/scripts but its `pull_request.paths` filters do not contain those script paths, even though the `push.paths` filters do. A PR changing only `scripts/audit_stock_timing_acceptance_guard.py` or its tests might not invoke the independent-audit PR gate before merge. That is a CI premerge review blind spot; it does NOT imply current forecast data are corrupt or that the model's timing edge is real.

## Fixed one-trial RED → narrowly scoped GREEN
1. Add a unit/static negative control to the existing `scripts/test_stock_timing_audit_handoff.py`, which itself is already in `pull_request.paths`. For each policy/evidence test or executable directly invoked by the independent-audit workflow, require the exact path in its `pull_request.paths`. Deliberately run this against unchanged workflow path filters and expect one RED test failure. This test is not market data.
2. After actual failing GitHub Actions PR evidence, add the *missing paths only* to the audit workflow's existing `pull_request.paths`. Preserve workflow event types, schedule, same-repo successful-main guard, checkout ref, read-only permission, concurrency, and all commands. No changes to production forecast, audit acceptance logic, originals, outcomes, baseline, source, model, UI, strict-green-1.0, orders, notifications, credentials or other workflows.
3. Require GREEN independent audit unit suite + audit on original evidence (42 original scored/13 correct, 42 learning events, 696 attempts, acceptance `not_proven`). Independently inspect PR diff and successful main/public gates if needed. Do not merge while RED or with an unexplained failure; retain separate draft branch.
4. The path filter test checks static expected path wiring only; it does not prove a future GitHub PR will arrive, price source rights, executable quotes, user push receipts, trade-cost edge, or prospective model usefulness. This experiment counts as **one bounded CI-safety engineering trial, zero model-selection or tuning trials**.

## Frozen source hashes before trial
- Ledger `1f254b2302dc1350ad95363ac4fbba5a4b145a46`
- Outcomes `f24b7e93f9aa438b8084e857429dbef99031d8fc`
- Public proofs `aff29efabcc6b3aa56f1eae87e76f1c00a2f96fb`
- Attempts `972eb510a3d108b003633f45cd168783436a3c8a`
- Learning events `dff634b1d6c5cf4236b8d5d018f92bfb99bf578c`
- Controller `7fe2da584cfdd82c186bc4894c8cbdd2f48c2e97`

**Current verified status: `not_proven`**. Zero of 24 groups meet 120 non-overlapping future targets and 20 observed sessions. No verified human receipt, official exchange raw quotations, executable post-delivery orders/quotes, cost-after-paper edge, or untouched confirmation interval. Existing 12 Nov 2 future targets are pending, six previous Korean intraday outcomes remain missing for previously diagnosed provider-coverage reasons. No user-action requirement is established.
