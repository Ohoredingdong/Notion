# Audit default weights of never-trained groups — bounded engineering experiment

Date: 2026-10-30 Asia/Seoul. Frozen main `33643f2e5b6bc2026732a0f46e3316123460e5aa`. Acceptance: `timing-utility-acceptance-1.0`. The forecast is research-only; this experiment does not evaluate or promote a model.

## Preregistered falsifiable hypothesis (before any guard edit)

The independent learning-evidence audit correctly binds trained groups to immutable terminal learning-weight hashes (PR #43), but skips weight inspection for groups with zero `learn_after_score` events. New groups are initialized by `stock_forecast_learning.ensure` to an exact 3 × 13 zero matrix. If an existing group has `learned=0`, yet a well-formed nonzero correction is inserted without a learning event, the current read-only audit will accept the forged state. The issue is different from PR #42 chronology, #43 trained terminal hashes and #47 staged trained-weight lineage. No actual tampering is asserted.

Single fault family, one new synthetic negative fixture, no candidate search or model trials. First test an unchanged audit with both a valid zero-weight untrained group (must pass) and forged finite nonzero untrained weights (must fail). Record valid RED action. Then add a minimal zero-learning invariant to the independent auditor only; refuse malformed matrices and nonzero corrections before staging/publishing. Existing trained groups still use the unchanged terminal event-hash chain.

## Real-evidence baseline (read-only)

Frozen main: 59 ledger records; 38 unique event windows; 21 repeat issuances; 8 overlapping targets excluded; 30 nonoverlapping; 12 pending future; 18 scored / 7 correct, spanning two origin sessions (2026-10-28 and 2026-10-29), all 45 stored outcome arithmetic checks consistent. Actual down 4/0 hits, up 2/0, flat 12/7. Public snapshots 16, user receipt zero; 18 learning events; 24 history groups in the latest autonomous cycle, no new forecast/learning changes, zero promotions. Original source is unofficial delayed Yahoo; independently licensed exchange candles, executable bid/ask, user delivery and post-cost prospective evidence absent. Latest bounded controller `research_cycle_verified` is not usefulness proof. No trade or authentication action is allowed.

## Verification plan

- Execute new test on isolated research branch **before** changing the auditor. CI must show the forged untrained state was accepted (a meaningful RED), with the valid case passing.
- Add only zero-event invariant to `scripts/audit_stock_learning_evidence.py`, no producer/model/ledger/weights edits.
- Run branch independent audit tests against current real ledger and all existing event lineage, prospective/directional/autopilot tests if feasible. Check no original ledger/output files differ.
- Revert temporary branch CI allowlist before PR merge. Include actual failing/success Actions IDs in this record and keep implementation only after GREEN.
- Do not change 120/20, direction thresholds, movement_then_direction shadow status, strict-green, notification or user authentication controls.

## Actual RED evidence (before audit patch)

- [Actions 40980316835](https://github.com/Ohoredingdong/Notion/actions/runs/40980316835) checkout on isolated research branch at `fa938cf9c0305ea65d4150bd8be01aafba1cd785`: 12 base forecast auditor tests and 4 source as-of tests passed; saved-price audit of real 59 ledger/45 outcomes returned 18 scored, 7 correct, no integrity errors. The new negative test `test_untrained_group_zero_weights_baseline_and_forgery_rejected` **failed meaningfully**: untouched zero group passed, but tampering an untrained group's finite weight from 0 to 0.125 was wrongly accepted (`learning_evidence_consistent` instead of `integrity_errors`). All 15 existing learning lineage tests passed; 1/16 new test failed as preregistered.
- The demonstrated defect is a blind spot in untrained *state provenance*, not proof that the live state was changed or that real trades are profitable. Frozen main has 30 groups, 12 with zero learning and valid all-zero 3×13 weights; learned 18 groups retain their terminal hash guard.

## Verified GREEN and promotion boundary

- [Actions 40980450597](https://github.com/Ohoredingdong/Notion/actions/runs/40980450597) succeeded on research commit `4f4f27b5a878e62930d5a63a1f715df6d381e127`: original zero-weight synthetic control passed, forged 0.125 nonzero no-event correction failed closed with the new error. All **16** independent learning tests, **12** independent price/chronology self-tests, **4** source-time tests, **26** prospective target tests, **88** learning/directional/autopilot tests, source/session guards, **9** forecast UI invariants and **7** bounded-recovery checks passed. Live unaltered data: 18 scored / 7 correct; learning lineage: 18 events / 18 updates; errors zero. The branch runner performed tests and read-only independent audit, **not** a production data collection/publish transaction.
- Scoped code change: independent audit now checks never-trained groups for the producer's 3×13 exactly zero correction. Trained groups retain immutable terminal hash checks; no trained weight, original false prediction, stored price, publication time, acceptance criterion, candidate/strict-green or active model was changed. This repairs a synthetic provenance blind spot, not a demonstrated deployed attack or predictive timing edge.
- Exactly **one** research hypothesis, **one** intentionally failing RED run, **one** passing GREEN run, zero classifier/model-selection trials or new shadow candidates. No missing baseline probabilities were fabricated. Exit without usefulness notification; still requires 120 nonoverlapping targets / 20 days per group and bid/ask-delivered after-cost independent forward confirmation.
- The temporary branch-specific workflow allowlist and research-only regression step were **reverted before PR**. No workflows or other automated monitors are in the final diff.
