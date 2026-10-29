# Staged learning lineage must be checked before transactional publication — 2026-10-30

**Pinned baseline**: `458fceb70c8c86bc23738c53919887244519e5fe`; preregistered acceptance: `timing-utility-acceptance-1.0`. Scope: one **synthetic** fault-injection and one narrow research-pipeline guard. No new model, recipe, tuning, data source, threshold or trading execution.

## Before testing: falsifiable hypothesis

The bounded autonomous research transaction calls `verify_stage` before copying its staged research bundle into the publishable working directory. That verifier independently audits stored outcome arithmetic/timing and checks `trained_events` identifiers/counts, but does **not** call the separately existing `audit_stock_learning_evidence.examine` on the staged learning **event-to-saved-weight fingerprint chain**. Therefore a synthetic stage whose saved terminal learning weights are altered (while prediction/outcome/publication evidence and learned-event identifiers remain unchanged) may pass `verify_stage` and be eligible for publication. This is a gap in prepublication verification, not evidence of production tampering or predictive skill.

## Bounded red/green protocol

1. On an isolated research branch with no public output rights, use the **existing synthetic** independent-learning fixture (one prospective forecast, one observed result, first public snapshot, one learning event). Check that the unaltered synthetic stage is accepted by `verify_stage`.
2. Tamper **only in-memory/synthetic staged** terminal weights while retaining event hashes. Require `verify_stage` to raise `staged_learning_evidence_rejected`. Execute this test against untouched producer first; record the expected RED result. No real data or credentials in fixtures.
3. If RED reproduces the blind spot, call the existing read-only `audit_stock_learning_evidence.examine` from `verify_stage` on the complete staged ledger/outcomes/deliveries/learning events/state; reject the stage on any error **before any staged files are copied**. Do not change the existing acceptance criteria or fallback behavior.
4. Re-run the synthetic case and all existing forecast/direction/learning/autopilot, independent audit, source/session and UI checks. Independently verify the existing real evidence remains internally consistent, and run branch research without publishing to main. Review resulting branch diff, restore temporary branch-only CI allowlisting, and merge only if no production evidence/approval/model changes are included.
5. Maximum one hypothesis, one synthetic corruption family, one producer guard, no model trials, zero promotions. Record intentional failure and any failed attempts; this test is a safety invariant, not a performance result.

## Evidence and results

Pending RED/GREEN CI results. Same held-out market evidence is not a new independent trial. External executable quotes, exchange candles, user notification receipt, after-cost edge and untouched follow-up confirmation remain unverified; the timing-utility completion gate remains closed.
