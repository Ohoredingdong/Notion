# Preregistered negative control: equal-time first issuance, 2026-10-30

**Pinned main:** `436c86d30ae29323dcc2f7973e581ddc641d63c0`.  
**Scope:** Independent read-only forecast evidence audit; no model training, candidate search, changed evaluation gates, source mutation, order, trade, API connection, or public forecast publication.

## Hypothesis fixed before tests

Two **distinct immutable forecast IDs** for the same (symbol, market, mode, target.start, target.end), having the **same instant of issuance** but contradictory frozen directions, cannot establish which one was first. The current `originals` map retains the first *file-order* row on an exact issued-at tie. Reversing JSONL row order can silently change scored outcomes. This is a provenance defect, even if the synthetic example never occurred in the live ledger.

### Negative control / test design

1. Construct only synthetic US 30-minute records with identical event key and `issued_at`, different IDs and opposing directions. Independently supplied outcome values (one correct, one wrong) and a timely public snapshot prove that reversing ledger line order changes which forecast is scored.
2. **RED:** Both reversed input orders must raise `integrity_errors` with `ambiguous_first_issuance_tie`; original audit is expected to incorrectly accept them. Control: non-tied later issuance must preserve original first issuance and validity.
3. **GREEN:** Add an audit-only guard comparing normalized issued-time instants for distinct ID ties and reject ambiguous event provenance without selecting a winner. Run the negative-control test, existing independent audit, attempts/learning/acceptance checks and existing operational-regression suites. Restore temporary CI configuration before merging.
4. Preserve all operating raw ledger/outcomes/deliveries/learning/attempts and their first forecasts. Rejecting a tie is not permission to rewrite or retroactively relabel one. If tests fail or current data show a tie, do not merge without further examination.

**Trials budget:** one preregistered hypothesis, one failure demonstration, one bounded fix, and one full regression; record technical failures. **No claim** of predictive superiority, exchange quote validation, or user delivery. This only closes a narrow evidence-order ambiguity.

**Initial baseline:** 77 archived forecasts, 56 unique event targets, 21 later issuance duplicates, 8 overlapping target exclusions, 48 nonoverlapping targets, 30 scored, 11 correct, and zero equal-instant distinct-ID ties in the pinned operational records (independent read-only recomputation). All 24 groups below directional minimum. These existing samples are NOT new forward observations.
