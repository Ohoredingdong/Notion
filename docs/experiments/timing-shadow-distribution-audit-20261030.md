# Shadow probability evidence-integrity experiment — 2026-10-30

Pinned baseline main: `a1c010ccb911fce56edecf31c5c67a3753da4d9d`.
Research branch: `research/timing-shadow-distribution-audit-20261030`.
Research hypotheses attempted: **1**. Model hyperparameters and thresholds: **0** attempted or changed.

## Preregistered hypothesis and expected failing reproduction

The read-only independent auditor checks the primary 3-way direction distribution, but its current `validate(r)` does not validate *stored shadow challenger* distributions in `directional_specialists.candidates`. If a stored challenger contains a nonfinite, negative, >1, nonsumming or direction-inconsistent probability, the evidence audit could incorrectly report overall ledger consistency even though that candidate's frozen evidence is internally invalid. This is a data-integrity test gap, **not a demonstrated defect in actual model predictions, exchange prices, execution or model performance**.

Construct a synthetic research prediction with a valid primary probability, coherent chronology, empty outcome and an existing `directional_specialists.candidates.movement_then_direction` shadow candidate. Deliberately corrupt its probability distribution while keeping the primary distribution valid. Existing `audit` should incorrectly return `ledger_arithmetic_consistent`; require `integrity_errors` after patch. Test a different corruption where candidate direction disagrees with the maximum probability. For existing rows, verify that all frozen shadow candidate distributions and directions remain valid and that main forecast score remains 6 evaluated, 3 correct. No re-scoring, backfilling, model selection or new shadow recipe.

## Safe experiment and acceptance

1. Add an explicit failing self-test before production code change and record failing CI evidence (red).
2. Extend **only** independent forecast evidence validation to cover nested, already-frozen shadow distributions, with strictly finite 0–1 values, sum 1, and direction=argmax. Do not require absent historical candidates to exist. Primary prediction, publication timing, overlap exclusion, scoring and thresholds must not change.
3. Run branch-only independent auditor self-tests, actual pinned ledger/outcome/delivery audit, existing forecast/source/direction/autopilot regressions. Require actual stored outcomes remain 21/21 internally consistent and six prospective scores with three correct. Branch tests must not publish data.
4. If tests pass, review isolated PR; no merge without verified regressions. Record failed and successful experiment runs. Leave `timing_utility:not_proven`.

Known evidence limits at baseline: 53 ledger rows, 32 unique event targets, 21 duplicate issuances, 24 non-overlapping targets, 21 stored outcomes, 6 eligible scored (3 flat hits, 3 down misses, no actual-up), 12 public snapshot checks and zero human notifications. Main source is delayed Yahoo; neither raw exchange candles, executable bid/ask nor after-cost post-delivery strategies have been independently established. This remains a **shadow-only research integrity guard**, not a timing-utility certification.

All immutable predictions, outcomes, public-delivery timestamps, learning updates, source files, strict-green-1.0, OpenDART auth, Toss settings, trade/order paths and unrelated automation stay untouched.


## Executed synthetic red/green and pinned actual evidence

- **Red test, before fix:** [Actions 40900174814](https://github.com/Ohoredingdong/Notion/actions/runs/40900174814), `test_shadow_candidate_probability_corruption_must_be_reported` failed as intended: existing independent auditor returned `ledger_arithmetic_consistent` for an intentionally corrupted shadow candidate; expected `integrity_errors`. This was entirely synthetic.
- **Minimal patch:** add *read-only validation* of already-stored `directional_specialists.candidates` distributions to `scripts/audit_stock_forecast_independent.py` (finite numeric down/flat/up, each within [0,1], sum within 1e-6 of 1, recorded direction equals argmax). Historical forecasts without shadow candidates remain permissible. This does not re-score old outcomes, adjust thresholds, add recipes or change any model weights.
- **Green test on research branch:** [Actions 40900357722](https://github.com/Ohoredingdong/Notion/actions/runs/40900357722) success. New negative tests, **8** audit self-tests, **26** forecast tests and **86** existing learning/directional/autopilot tests passed (120 in total), plus source/session guards. Read-only audit of 53 pinned forecast rows and all **21/21** already stored observed outcomes showed no integrity errors; the prospective non-overlap set remained **6 scored / 3 correct**, 3 down misses, no actual-up sample. False alarms: flat predicted 6 with three actual-down miscalls; there are no real bid/ask execution results.
- Separate **independent JS computation** checked all 21 saved outcomes against frozen primary direction/probabilities, fixed neutral bands, stored open/close arithmetic, Brier score and chronological issue/receipt timestamps; no mismatch. Frozen ledger also contains **18** shadow candidate probability distributions across 6 newly issued forecasts, 3 bounded candidate names each; **18/18** are internally normalized, finite and direction-consistent. No externally obtained exchange candles or actual human push receipt were validated.
- Scope: engineering audit hardening only. **No new eligible future outcome, promotion, rollback, live order, verified after-cost strategy or timing usefulness claim**. Candidate `movement_then_direction` stays shadow. Acceptable forecast direction and strict-green purchase thresholds remain untouched. Experiment search/attempt count: **one preregistered audit-integrity hypothesis, one red and one green test; zero model parameter searches**.

If this limited patch is merged, verify the existing independent-audit main workflow without changing the live forecast, delivery or strict-green pipelines. The external quote, legal feed, human notification, cost-after-delivery and untouched forward block requirements remain explicitly unmet.
