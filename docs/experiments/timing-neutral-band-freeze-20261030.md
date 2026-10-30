# Immutable neutral decision-band research — 2026-10-30

Pinned main: `50e17bd5f9bd23b432b93b4f64ad5406156f6ded`; acceptance: `timing-utility-acceptance-1.0`.
This is **one evidence-integrity hypothesis**. No forecast optimization, future-target selection, credential use, orders, live quote claims or candidate promotions. Tests are synthetic; they do not count as forecast samples.

## Preregistered hypothesis (written before changing audit code)

The independent read-only forecast auditor validates that `neutral_band_pct` is a non-negative finite number and uses it to classify outcomes, but does not independently reconstruct the frozen policy value from `feature_values.vol20` and `policy_revision`. Consequently, changing an issued forecast's neutral band could change directional labels/scoring while leaving the current one-/two-stage issuance fingerprint unchanged. There is **no claim that actual production evidence was altered**; all 59 pinned real forecast bands independently recompute exactly from the policy.

For `version=direction-forecast-1.0` and `policy_revision=provider-latency-30m-v1`, calculate `max(daily 0.30%, intraday 0.15%, 100 * vol20 * (daily 1 / intraday sqrt(6)) * 0.35)` using the separately frozen volatility feature. Require a finite nonnegative feature, a known mode and error < 1e-9 percentage points. Missing frozen feature must fail closed for these modern records. Older/unknown policies must NOT be backfilled with this formula.

## Bounded RED / GREEN contract

1. RED: synthetic original record passes, synthetic band mutation and deletion are rejected by the **test** but accepted by old audit. Record GitHub Actions failure before changing production audit.
2. GREEN: add only the narrow independent formula validation; no change to producer, issued records, outcome labels, evaluation/promotion gates or stored prices. Test daily floor, daily volatile, intraday volatile, unknown historical policy, malformed/altered/missing band. Independently re-audit all 59 ledger records, 45 observed outcomes, 16 publication checks and 18 eligible scores; scores and file SHAs must remain unchanged. Run existing independent/self tests and learning evidence audit.
3. Revert temporary research CI workflow before merge. Permanently add focused synthetic test to existing independent-audit workflow, preserving its existing gates. Only merge after RED evidence and GREEN regression. If any test fails leave open/abort.
4. Count one prespecified hypothesis; zero optimized models, zero tuned thresholds, zero synthetic forecasts promoted. A test success does not establish timing usefulness. Still missing real-time user receipt, exchange candle/quote source, fees/slippage after delivery, forward unselected period, and groupwise 120/20 directional sample gates.

## Execution log

- RED: [Actions 40985561765](https://github.com/Ohoredingdong/Notion/actions/runs/40985561765) on research branch commit `c9dba991f40a6a0cc6af735d592decf2ed3a49ca`: 6 synthetic tests, 4 passed and exactly 2 adversarial negative tests FAILED as preregistered (unchanged band and legacy rows still accepted). The old independent auditor did not reject a synthetic band shift or removal of the frozen vol20 feature. This is a fabricated counterexample, not evidence of tampering in real markets.
- GREEN (focused): [Actions 40985662854](https://github.com/Ohoredingdong/Notion/actions/runs/40985662854) at commit `e63018df6c5c2ce3c39228c51dacb09c2d092ffe`: 6 synthetic tests all pass, 12 independent forecast self-tests, 16 independent learning tests, and actual independent evidence audit remain consistent (59 frozen predictions, 45 internally verified outcomes, 18 eligible/7 correct). Original 59 real neutral bands independently match the preregistered formula without any correction. Full regression: pending.
- Merge and main audit: pending.
