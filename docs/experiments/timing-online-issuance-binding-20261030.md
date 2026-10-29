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
