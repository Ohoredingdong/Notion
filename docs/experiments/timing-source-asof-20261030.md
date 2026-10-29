# Outcome source-time availability: bounded prospective evidence audit experiment

Date: 2026-10-30 KST. Baseline frozen main: `50a16238421c424f9b02a37a797284039445a402`. Policy: `timing-utility-acceptance-1.0`.

## Before modification — falsifiable hypothesis

The independent stored-outcome audit checks the target-end and evaluation time, but never checks the optional `source_checked_at` field. Therefore a **synthetic** outcome whose price was first checked **after the stated evaluation time** (or before the target end) could be accepted as `ledger_arithmetic_consistent` even if all price arithmetic and publication proofs are consistent. This would obscure when the result was actually available, and is an evidence-timing weakness, **not evidence that any real outcome was forged**.

This is distinct from PR #45, which guarded the copied *public web verification* time rather than the *market result source-check* time. Actual baseline 27 observed outcomes have the same `source_checked_at` and `evaluated_at`; no observed mismatch was found. An absent legacy timestamp should not be synthesized or retrospectively stamped.

## Single bounded red/green trial

1. In an isolated research branch, add synthetic fixture `scripts/test_stock_timing_source_asof.py`. Valid synthetic price return and publication; three source availability cases: source checked after evaluated_at, before target.end, and a valid check between target.end and evaluated_at. Require the first two to fail audit integrity and the last to pass. Absent legacy field remains compatible.
2. Run test against unchanged audit code first (**RED**). If the test unexpectedly passes, investigate rather than force a code change.
3. If reproduced, add only a read-only validator in `scripts/audit_stock_forecast_independent.py`, conditional on the optional field: `target.end <= source_checked_at <= evaluated_at <= audit cutoff`. Do not claim source correctness or exchange-verified data.
4. Run synthetic test, the original self-tests, real frozen 53 ledger/27 observed outcomes/13 public verifications/12 learning events, regression for forecast/direction/autopilot and public UI/source checks where appropriate. Merge only with a tested green branch and an unchanged production ledger/forecast/model/strict-green.
5. Record every CI run (including failed attempts), code/PR hashes, and test counts. Maximum **one new audit hypothesis, one synthetic fault family, no model candidate search or promotion**.

## Pre-test observations and limits

At baseline, the independent rerun on a separate JS implementation found 53 forecast rows, 32 unique targets, 21 duplicate issuances, 8 overlapping targets excluded, 24 nonoverlapping targets, 6 pending, 6 without saved observed outcome, 12 scored/6 correct; actual down 3 missed, up 2 missed, flat 6/7 hits. All 27 saved return/label/Brier computations and copied public timestamps matched. Two groups of evidence remain insufficient for acceptance: directional ability and actionable post-cost strategy. Only 2026-10-29 forecast origin sessions contributed to independently scored cases, not 20 days. No raw exchange minute bars, executable bid/ask, actual alert receipt or independent untouched later confirmation can be proven from this GitHub repository.

The real `stock-forecast-autopilot.json` status `research_cycle_verified`, previously passed workflow, and public JSON verification do not certify usefulness. This experiment is a research evidence audit only and must not change training or previously recorded facts.

## Actual trial results

- **RED (intentional):** [Actions 40958571442](https://github.com/Ohoredingdong/Notion/actions/runs/40958571442) ran the synthetic tests against untouched independent audit code. Exactly **2/4** failed as preregistered: a source timestamp at 14:40 after claimed 14:31 evaluation and a 14:29:59 source timestamp before the 14:30 target end both incorrectly returned `ledger_arithmetic_consistent`. This is an audit blind spot demonstrated by fabricated records, not observed production tampering.
- **GREEN initial:** [Actions 40958652275](https://github.com/Ohoredingdong/Notion/actions/runs/40958652275) passed after adding a conditional read-only source timestamp guard. No baseline production data or forecast output changed.
- **GREEN final, corrected fixture:** [Actions 40958733864](https://github.com/Ohoredingdong/Notion/actions/runs/40958733864) passed after fixing the *legacy-absent-field fixture itself* to actually omit that field. Four new synthetic tests, 12 existing independent audit tests, 15 independent learning-event lineage tests, 26 prospective forecast tests, 86 learning/direction/autopilot tests, session/source guards, nine UI invariants and seven bounded-recovery checks passed.
- **Real immutable baseline unchanged:** 53 recorded predictions, 32 unique target windows, 21 duplicate issuances, 8 overlapping excluded, 24 nonoverlapping windows, 6 pending and 6 missing stored outcomes. All 27 stored outcome returns/labels/Brier internally consistent; 12 independently scored, 6 correct (down: 0/3, up: 0/2, flat: 6/7). All 12 existing learning events retained. The source field was present and matched `evaluated_at` in all 27 observed rows before the code change.
- **Scope:** Added only a verification of **claimed source retrieval time**, never independent verification of exchange minute prices, executable quotes, actual alert receipt, or after-cost edge. Original predictions, weights, outcomes, scoring gates, candidate catalogue and human approval controls remain unchanged. Zero model trials, zero new shadow candidates, zero promotions, zero training updates. The run's single research hypothesis produced two deliberately failing negative cases, one guard fix, and one corrected legacy fixture; no repeated selection of a better-scoring model.
- **Continuing limitations:** insufficient future independent targets/observation days and no bid/ask+fees+slippage post-delivery prospective simulation or untouched follow-up block. No timing-utility completion assertion or user progress notification.
