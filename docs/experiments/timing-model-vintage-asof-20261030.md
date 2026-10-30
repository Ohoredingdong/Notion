# Research experiment: model-vintage as-of chronology (2026-10-30)

Pinned main: `03db89b91c61d0f1fcb0404d835d22b8263c5da6`. Policy: timing-utility-acceptance-1.0.
Experiment family: one provenance invariant; no candidate selection, zero parameter searches, no real price/order changes.

## Preregistered hypothesis (before patch)
The read-only independent `validate()` checks `trained_through` and `calibrated_through` against `issued_at` but not `observed_until`; it also does not constrain `validation.test_end` to the frozen observation. A synthetic record may therefore claim training/calibration/holdout data **later than its declared observed price snapshot**, while still earlier than issuance, and pass audit. This indicates a provenance consistency gap, not demonstrated live future-data leakage or model improvement. Earlier PRs #41–#51 address separate publication, outcome, distribution, band and learning lineage invariants.

## Fixed RED/GREEN test
- Preserve all original forecasts, outcomes, state and timestamps.
- Synthetic negative cases: training-through, calibration-through or holdout end 20 seconds after frozen observed_until, yet 40 seconds before issuance; training-through after calibration-through. Existing audit should accept these inconsistent records (RED test fails).
- Positive cases: valid chronology, absent legacy metadata (do not invent missing historical fields).
- Patch only read-only `scripts/audit_stock_forecast_independent.py`: for present dates require training/calibration/test end no later than observed_until; require training no later than calibration when both exist. Compare UTC-aware timestamps; reject malformed present timestamps.
- Audit the pinned **65 frozen prediction rows**, holding all evidence/evaluation fixed. Precheck found 0 violations of these four conditions (minimum training observation lag ~833.75h, minimum calibration lag ~380.67h). No provider/exchange authenticity inferred.
- Verify failing CI on test-only branch, then green exact same tests, the full existing independent audit and source/band/learning guards; branch-only CI modifications must be removed before PR merge.
- Stop with unresolved failure on any regression. No changes to model weights, prediction issuance, strict-green policy, order/trade/notification/auth, other scheduling or old outcomes.

## Evidence
Preregistered; RED pending. Do not report timing usefulness, actual trader receipt, executable quotes, after-cost P&L or untouched future segment as verified.

## RED reproduction executed
- [Actions 40996854940](https://github.com/Ohoredingdong/Notion/actions/runs/40996854940): checkout the isolated research ref, execute six synthetic tests. Two control cases passed; all **four** preregistered inconsistent chronology mutations failed with `AssertionError: ValueError not raised`. This is a valid failing reproduction, not a live-data incident.
- Patch scope: one read-only `validate()` check in `scripts/audit_stock_forecast_independent.py`. No forecast state or data rewritten.
- GREEN/review: pending separately verified branch CI, original frozen audit and existing regression checks; no claim of utility.

## Initial GREEN verified (before broader regressions)
- [Actions 40996976976](https://github.com/Ohoredingdong/Notion/actions/runs/40996976976), head `f3f4a9fbc059f3c818c85397172870b4966b69a1`: all six preregistered synthetic tests passed, original independent audit self-tests 12/12, source-time tests 4/4, frozen-band tests 6/6, 17 learning-evidence tests, frozen scored 18 (7 correct), 18 learning rows, no integrity errors. No real market outcome changed.
- Broader model/direction/autopilot source regression run is now scheduled by temporary branch-only CI changes, no production publishing.

## Full GREEN regression and final scope
- [Actions 40997073121](https://github.com/Ohoredingdong/Notion/actions/runs/40997073121) passed on research head `9ce0ff0580b86de7b659bdce97e2ae2530f9d39d`: new as-of tests 6/6; original audit 12/12, source-time 4/4, fixed band 6/6, learning evidence 17/17; frozen score 7/18 and learning rows 18 unchanged. Separate existing prospective-forecast tests 26/26, learning/direction/bounded-autopilot tests 88/88, source guard checks, recovery tests 7/7 succeeded. Installing dependencies and the tests were confined to CI; no publish or training on production outputs.
- Final branch restores main-only trigger, `checkout ref: main`, and original CI timeout; retains only new test invocation/path in existing independent audit workflow. Original model/price source/ledger/outcomes/learning/strict-green/other automations are unchanged. No public UI changed; source exchange candles, human receipt, execution-ready quotes, after-cost strategy, untouched future interval remain unproven.
- Test attempts: one preregistered hypothesis; one valid RED workflow, first GREEN, broader GREEN; zero model/threshold candidates tested.
