# Online-learning issuance fingerprint / selected-probability audit experiment

Date: 2026-10-30 (Asia/Seoul)
Frozen source commit: `908812f4eb377d5683152f341d0dacdaf15e9916`
Policy: timing-utility-acceptance-1.0; audit-only; **not** trading-usefulness approval.

## Pre-change hypothesis and anticipated failure

The standalone independent forecast audit validates the primary class probabilities and the shadow specialist distributions, but it does not bind the originally issued active probability distribution to the separately frozen `online_learning` selected distribution. It also does not verify the issuance ID for the records that include the `online_learning` fingerprint. A synthetic post-issuance mutation of the primary `probabilities` and matching `direction`, while retaining the immutable `online_learning` fields and the old ID, may therefore pass the ledger audit even if an attacker also updates the calculated outcome labels. This is an evidence-integrity weakness to test, **not** evidence of actual tampering or model misprediction.

## One fixed experiment / acceptance and stop criteria

1. Reproduce a synthetic forged primary probability with an unchanged `online_learning` snapshot. The pre-fix `validate` is expected to accept it. Also test a malformed online record ID independently.
2. Add a narrow read-only check only for rows containing `online_learning`: ensure incumbent/adaptive probability distributions are finite and normalized; the issued main probabilities equal the selected frozen distribution; and the existing issuance ID matches the deterministic digest of frozen event, policy, base-model SHA and online metadata.
3. Existing records lacking `online_learning` continue to use their historical validation path; no retroactive IDs, claims or probabilities are invented.
4. Run the synthetic red test, then passing green tests against the current **unmodified** saved ledger/outcomes/deliveries/learning evidence and existing regression suite. A failed baseline/evidence check blocks any merge.
5. Keep changes to the independent auditor, its tests and this experiment log. No producer, training, model, thresholds, data, orders, auth, live connection, strict-green, other automations or workflow policy changes.

## Prohibited interpretations

A passing fingerprint consistency test verifies *internal* issuance metadata consistency only. It does not prove historic GitHub file immutability, an exchange-sourced price, first human receipt, execution after costs, candidate superiority, or satisfaction of the 120-target/20-day acceptance requirement. Synthetic tests are never counted as market observations.

## Pre-specified comparison

Compare existing audit status, eligible non-overlapping scored count, direction-specific result, learning integrity, and public-before-target chronology before and after the change. Expected number of model promotions: zero; expected difference in forecast values and outcome/learning files: zero. Fail closed and retain research branch on any mismatch.

## Experiment accounting

One audit hypothesis, one synthetic bypass reproduction, one bounded read-only code change, and one full regression. Record red and green workflow evidence separately, including failed attempts. No model candidate search or parameter tuning.

## Executed evidence / negative-results disclosure

Pinned immutable working input commit: `908812f4eb377d5683152f341d0dacdaf15e9916`. The repository supplied 53 ledger rows, 32 unique future targets, 8 overlapping targets excluded, 24 nonoverlapping targets, 27 observed outcomes, and 12 currently eligible publicly pre-target-scored results. Current scored accuracy is 6/12 (50%); actual down 3/3 missed and actual up 2/2 missed. The 12 learned outcomes all matched their post-public evidence and learning-event/terminal-weight integrity in the revised independent audit. Earlier hourly audit reports for 6/3 apply to a *prior snapshot*, not a new performance claim. The first human notification receipt, exchange-grade bars/quotes, realistic executable order costs, independent untouched post-selection block and sufficient forward sessions remain unverified.

- **RED:** [Actions 40942376485](https://github.com/Ohoredingdong/Notion/actions/runs/40942376485) on the research branch, 10 synthetic audit tests, exactly one expected failure: `AssertionError: ValueError not raised` for an altered primary probability/direction with the same frozen online metadata and ID. Actual forecast rows and outputs were untouched.
- **Failed intermediate attempt 1:** [Actions 40942490214](https://github.com/Ohoredingdong/Notion/actions/runs/40942490214) still failed the bypass test because an initial helper-only change was insufficient. This attempt is retained in the experiment history, not counted as a successful fix.
- **Failed intermediate attempt 2:** [Actions 40942523646](https://github.com/Ohoredingdong/Notion/actions/runs/40942523646) passed synthetic tests but rejected six legitimate US intraday records. Investigation of the actual producer revealed `stock_forecast_directions.apply_variant()` adds an immutable *second-stage* directional-selection digest around the first online-learning ID. Treating those records as single-stage IDs was incorrect; no source rows were changed or relabeled.
- **GREEN corrected two-stage version:** [Actions 40942764624](https://github.com/Ohoredingdong/Notion/actions/runs/40942764624) passed the expanded synthetic fixture, the original ledger/outcome arithmetic, all 12 existing learning updates, and independent saved-weight lineage checks.
- **Full existing regression:** [Actions 40942864383](https://github.com/Ohoredingdong/Notion/actions/runs/40942864383) passed 26 prospective-model tests, 86 learning/direction/autopilot tests, 11 independent audit tests, 15 learning-evidence tests, session/source safeguards, 9 UI time/probability invariants, 7 bounded-recovery checks and JavaScript syntax checks. On the frozen dataset: `ledger_arithmetic_consistent` (12 scored, 6 correct, no integrity errors), `learning_evidence_consistent` (12 learning events, no integrity errors). This is a repository research-branch test, not live broker/quote verification.

**Outcome of the hypothesis:** A real independent-integrity blind spot was reproduced with synthetic rows. The fix compares each issued main distribution against the frozen incumbent/adaptive or selected directional-specialist distribution and independently reconstructs the correct one- or two-stage issuance fingerprint. Historical records without online metadata remain compatible. The two unsuccessful intermediate attempts remain recorded. No new candidate family, selection rule, score threshold, past probability, data update, model promotion, model rollback, real trade or executable quote was introduced. This does **not** satisfy timing-utility acceptance, nor justify a user completion notification.
