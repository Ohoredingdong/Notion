# Frozen shadow-candidate catalogue integrity — 2026-10-30

Pinned main at research start: `d011ae6f3040a50d349a2c30ce94b677a27ea2d8`.
Branch: `research/timing-shadow-catalogue-audit-20261030-r12`.
One predefined engineering/audit hypothesis, **zero model searches** and no changes to any historical forecast, model, evaluation or market-input record.

## Pre-registered hypothesis and why it matters

The independently run `scripts/audit_stock_forecast_independent.py` validates each `directional_specialists.candidates` member's probability distribution but does **not** reject an unfamiliar candidate name. A synthetically injected, well-formed `oracle_future_peek` challenger can therefore pass the candidate validation, despite `docs/stock-direction-specialists.md` and `docs/stock-bounded-autopilot.md` limiting experiments to a reviewed catalogue. This is an integrity/accounting gap, **not proof that production data is forged or uses future candles**.

The reviewed shadow names for the current `direction-specialists-1.0` schema are `balanced_linear`, `balanced_nonlinear` and `movement_then_direction`. The separate `adaptive` and `incumbent` variants are held in `online_learning`, not extra arbitrary shadow entries. At the pinned commit, 24 frozen rows have exactly these three reviewed shadow names; earlier rows without shadow metadata stay on their original path.

## Fixed RED/GREEN design

1. Create **synthetic** intraday records with valid issue/observation/target times, finite 3-class probabilities and a correctly selected direction.
2. Positive controls: legacy record without candidates and a current record using a reviewed candidate must pass.
3. Negative controls: an invented `oracle_future_peek` candidate (alone and alongside a reviewed candidate) must raise `unreviewed_shadow_candidate`, even though its probability vector is numerically valid.
4. RED: run the unchanged auditor on these tests; the negative controls should fail to reject. GREEN: add only an explicit reviewed-name allowlist in the independent auditor. Do not change the producer, selection/score policy or probabilities.
5. Recompute all pinned immutable 71 predictions, 51 stored outcomes, 18 public proof records and 24 learning events: existing 24 eligible / 8 correct, down 0/4, up 1/8 must remain unchanged. Confirm no newly claimed timing utility.
6. Run existing independent audit, learning, forward/direction/autopilot regressions on the isolated branch. A branch-only test must not publish forecasts, learn new results, change main, send user alerts or place orders. Revert any temporary branch-CI settings before proposing a PR.
7. Merge only if CI passes and the PR diff is limited to the independent auditor, focused synthetic regression, audit-workflow invocation and this experiment record. Do not infer model skill from CI success.

## Existing work and exclusion

Previous experimental audits addressed frozen probabilities/IDs (#44), source/check times (#46/#52), learned weight evidence (#43/#49/#51), directional summary (#48), neutral band (#50), row status (#54), and public proof identity (#56). None of those tests establishes an allowlist for arbitrary **shadow candidate names**. This experiment does not add a fifth challenger, weaken pre-existing requirements, use the outcome block for model selection, or authorize trading.

## Preconditions still unsatisfied

The actual forward samples, independent exchange executable quotes and raw minutes, real user receipt timestamps, after-cost forward paper comparison, and untouched follow-up segment are unproven. Historical stored-price arithmetic is not external price verification. The automated recovery controller only handles predefined bounded cases.

## Recorded attempts

Pending RED/GREEN run links; add the actual GitHub Actions outcomes and any failed attempts before review. 
