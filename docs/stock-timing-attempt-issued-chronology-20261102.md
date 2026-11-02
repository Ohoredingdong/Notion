# Research-only: attempt-to-forecast issuance chronology — 2026-11-02

## Pinned source and prior-art review (preregistered before fault injection)
- Fixed `main` baseline: `0534b9a2b046bc6060fb0db303d2ee634b9d63a8`.
- Read and preserved `docs/stock-timing-acceptance-20261029.md`, `docs/stock-direction-specialists.md`, and `docs/stock-bounded-autopilot.md`; their acceptance minima and strict-green purchase gates must not change.
- Inspected source ledger (89 forecasts), attempt ledger (696 attempts; 322 research_prediction references), 69 outcomes, 31 public proofs, 42 learning events, the controller's latest `not_proven` status, and actual producer/audit/recovery Actions results. All 322 forecast references resolve to frozen ledger IDs.
- Existing PR #92 prevents repeated logical attempts; PR #96 binds outcome issuance timestamps; PR #98 fixes audit workflow triggers. This trial covers a different gap: **attempt chronology relative to the frozen forecast issuance**.
- Archived provider-pipeline scheduling stamps can precede issuance by a few tens of milliseconds: 48 of 322 referencing attempts precede `issued_at`, worst by **47 milliseconds**, while later runs legitimately reference earlier forecasts. No observed real record is claimed corrupted.

## Hypothesis / expected negative control
The read-only attempt auditor checks that a research_prediction references an existing forecast and matching symbol/mode, but not that the claimed attempt time could have referred to a forecast that already existed. A forged attempt pointing at a forecast issued **minutes later** could be counted if the coverage summary was changed consistently.

Before code change, add a synthetic test moving an attempt's `checked_at` to two minutes *before* its frozen forecast `issued_at` while keeping the report consistent. Expected intentional RED: the negative control fails to detect this contradiction.

## Minimal intended change
- For referenced `research_prediction` attempts, reject `checked_at` earlier than the referenced `issued_at` by **more than one second**. One-second allowance covers the archived pipeline's known subsecond checking/issuance clock order, not any trading latency or proof of availability. Do not compare with user-delivery timestamps or claim timely actionable signals.
- Preserve later-run references and normal no_call handling. Reject malformed *present* issuance timestamps as integrity errors; missing older optional provenance is not fabricated.
- Re-run the new negative control, legitimate same-run subsecond check, and existing attempt/independent/acceptance regression suite in GitHub Actions. No model/prediction/outcome/state data changes. Only the test + read-only attempt auditor + this research document can change.

## Decision and limits
- Trial classification: engineering evidence-integrity hardening, **not** forecasting improvement, exchange quote validation, paper return, or human push delivery.
- No shadow candidate promotion; no retrospective candidate creation; no actual orders; original event timing, acceptance thresholds, strict-green-1.0 and existing anomaly-monitoring automation remain unchanged.
- Failure attempts (including intentional RED) and actual GitHub Actions/job results must be recorded here before any merge. If tests cannot be verified, keep the PR unmerged and mark blocked.

## Actual RED trial (not a model result)
- PR: https://github.com/Ohoredingdong/Notion/pull/99; intentional failing independent-audit run: https://github.com/Ohoredingdong/Notion/actions/runs/41369651007.
- Job `125037164350`, 2026-11-02 00:54 UTC: 20 attempt-coverage tests; exactly one negative-control test failed as hypothesized: `AssertionError: 'attempt_forecast_not_yet_issued' not found in []`. The 50 ms legitimate-clock test passed. Other tests preceding the new control passed.
- New audit logic guards the frozen referenced forecast's `issued_at` against scheduler `checked_at` with the preregistered one-second tolerance. This is an integrity alarm, not evidence of actual historical mis-issuance.
