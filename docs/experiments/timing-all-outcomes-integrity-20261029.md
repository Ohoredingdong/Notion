# Timing evidence experiment: validate ALL observed outcome rows, 2026-10-29

Base main pinned: `7dc81c2a33aed3b6680751cc56d1ff53bb3e0797`.
Research branch: `research/timing-all-outcomes-integrity-20261029`.

## Preregistered hypothesis (before changing auditor code)
The independent read-only audit checks stored return, class, correct/incorrect flag and Brier arithmetic only for the non-overlapping, timely-public subset selected for forward scoring. A malformed outcome on a real but overlapping event can therefore be stored while `status=ledger_arithmetic_consistent` remains true. This is an evidence-integrity gap, NOT evidence of a real malformed price, predictive-skill problem, or executable trading return.

Counterexample (synthetic TEST records, not real prices): First forecast targets 14:00–14:30, second same symbol/mode targets 14:05–14:35. Both issued 13:36, publicly available before targets. First outcome is coherent (100 -> 99, -1%, actual down). Second claimed outcome is intentionally inconsistent (100 -> 101, +1%, yet recorded -1%, actual down). The second target is overlapping and must stay excluded from performance (scored remains 1), but the whole-evidence auditor should reject its fabricated outcome rather than report full integrity.

Acceptance: add a failing reproduction before the fix; then check every stored `status=observed` outcome against its immutable forecast id, target, prices, originally fixed band, direction, probability and evaluation timestamp, even when excluded from performance; do not change first-issue/nonoverlap/published scoring selection or anything in source/model/learning/strict-green. Preserve all historical records; no external exchange or human-delivery claims. Invalid rows must not be accepted as useful observations.

## Independently measured pinned baseline (no external exchange verification)
- 53 immutable forecast rows; 32 unique target event keys, 21 re-issues; 24 non-overlapping event targets and 8 overlaps.
- 21 saved outcomes; independent separate JS read-only arithmetic check found 21/21 internally consistent; no linked outcome missing; 6 scored timely-public targets, 3 correct, 3 missed down, 0 actual-up in scored set.
- 18 additional non-overlapping future targets pending at observed cutoff. 192 attempts (93 research_prediction, 99 no_call); 12 public snapshot verifications, 0 human receipts. Public snapshots are not push delivery.
- Baseline `scripts/audit_stock_forecast_independent.py` validates outcome arithmetic after overlap and public eligibility selection, so all 21/21 currently correct outcome values do not prove the auditor would detect future corrupted overlapping rows.

Tests: deliberate regression failure before patch in GitHub Actions; minimal read-only audit change; rerun auditor self-tests, all stored outcomes and existing forecast/learning/directional/autopilot unit suites, check that scored count, correctness, direction counts, no-buy/no-orders and thresholds are unchanged. Independent branch CI only; no production data edit or publish. Review PR/CI before promoting.

Candidate hypothesis count: **1**; no optimization of forecast parameters or repeated performance tests. `movement_then_direction` remains shadow. Status: experiment staged, not a timing-usefulness result.

Acceptance for any user completion notice remains `docs/stock-timing-acceptance-20261029.md` in full; independent executable quotes, cost-after-delivery strategy and untouched future holdout remain unproven.
