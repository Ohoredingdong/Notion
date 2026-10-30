# Research hypothesis: anchor the first learning-weight fingerprint (2026-10-30)

Pinned main: `f41b4cbc37824d1d7e0d116e1151cceeb293fe74`. Acceptance policy: `timing-utility-acceptance-1.0`.

## Preregistered engineering hypothesis — before any code change

The independent learning-evidence audit verifies (i) SHA-shaped before/after weight fingerprints, (ii) the chain between adjacent updates in a group, (iii) final saved weight hash, and (iv) zero weights for groups with **no** learning. However, a group that **has** events does not bind the **first** event's `weights_before` to the canonical zero-initialized 3-by-13 correction matrix. A synthetic altered first-event fingerprint can therefore be accepted despite the terminal state and subsequent chain remaining intact. This is a provenance/audit gap, NOT evidence that production weights are corrupt or that predictive skill changed.

The existing initial training correction in `scripts/stock_forecast_learning.py` is a 3-by-13 zero matrix; its canonical SHA256 is `ea165d153f6c5dad75c71db2a0b51ede3e30132e0d2bb6ae8ea2361ffa22599f`. At the pinned commit, all 18 training-event groups each have one event and all first fingerprints equal that canonical value; therefore a narrow change should not alter any real data or score. This is separate from PR #43 (terminal hash), #49 (untrained groups), and #50 (frozen decision-band formula). PR #48 validates published performance summaries, not the genesis of trained groups.

## Bounded RED/GREEN plan

1. Add one synthetic negative test: mutate only a trained group's first `weights_before` to an alternative 64-character lowercase SHA, leaving the terminal saved matrix, event id, label and timestamps valid. The test must FAIL on the old auditor. Keep a normal two-event chain acceptance fixture. No prediction selection, threshold tuning, alternative models, or outcomes are read to choose the parameter.
2. Patch only `audit_stock_learning_evidence.examine` to require the first trained event to reference the fixed zero-initialization hash (rather than merely matching the second event). Align the synthetic fixture with the true 3-by-13 state structure. A first event with an undocumented starting vector must fail closed. Do not rewrite any existing saved row.
3. Verify RED with GitHub Actions before patch, then GREEN using independent-audit self-tests on real, frozen data, existing regression, bounded-autopilot tests and UI contract tests as applicable. Only then merge. A research-branch workflow trigger is temporary and must not ship to main.
4. Audit 59 frozen original predictions / 45 internally arithmetically consistent observed outcomes / 18 eligible scores (7 right); independently review 18 learning-event hashes. Exchange minute bars, post-delivery executable quotes, user receipt, post-cost paper execution and untouched forward confirmation remain unverified. Tests are synthetic and MUST NOT count as new outcome samples.
5. Record all failed attempts and verified passes. No model promotion, data backfill, new recipe, credential change, orders, strict-green change or modifying other schedules.

## Execution record

Pending reproducible RED / GREEN evidence. This section will be updated only with actual observed CI results.
