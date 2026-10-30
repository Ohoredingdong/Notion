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


## Executed experiment and independent recheck

- **RED, expected failure**: [Actions 41054647007](https://github.com/Ohoredingdong/Notion/actions/runs/41054647007), code before guard. Three synthetic ambiguous-first controls failed because the auditor returned `ledger_arithmetic_consistent`; two valid controls passed. Actual model output, production outcome rows and market data were not mutated.
- **GREEN, localized guard**: [Actions 41054791589](https://github.com/Ohoredingdong/Notion/actions/runs/41054791589) passed the equal-time synthetic suite and read-only evidence regressions. Guard detects distinct IDs tied at the **earliest normalized instant**, irrespective of file order/UTC offset; it excludes the ambiguous event from scoring while raising `integrity_errors`. Identical ID replays and ties among non-first reissues are not falsely rejected.
- **GREEN, expanded regressions**: [Actions 41054947616](https://github.com/Ohoredingdong/Notion/actions/runs/41054947616) passed six negative/control tests, existing prospective forecast tests (26), learning/directions/autopilot tests (88), independent stored-price audit, immutable learning and attempts audit, timing acceptance guard, preexisting source/time/public/probability negative controls and JavaScript syntax/UI checks. No live pipeline was invoked to publish synthetic data.
- **Pinned operational state before change**: 77 archived rows, 56 distinct future target keys, 21 reissuances, 8 overlaps, 48 nonoverlapping targets, 12 future outcomes, six missing matured outcomes, **30/11** scored/correct, 24 groups on only two observational dates. No equal-time distinct-ID first issuance found. The existing comparison from 18 paired cases remained model 7 correct versus frozen baseline 9; neither proves forward superiority.
- **What this did not test or improve**: tradeable quote/size, US or KR market execution, true exchange raw bars, actual user alert receipt, costs and slip, sufficient forward samples, untouched postselection evaluation or any live brokerage order. Forecast and outcome evidence stay unchanged; this is strictly a scoring-provenance guard. No new user action discovered.

**Experiment count:** one preregistered tie hypothesis, three synthetic negative conditions with two additional controls and a later-tie regression, one bounded audit-only patch. Tests and failures are retained in Actions; no forward-performance tuning or retry-until-good model search was performed.
