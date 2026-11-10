# Source-bound post-validation — 2026-11-10

## Scope

User requested complete post-validation, not fabricated perfect performance. Freeze source main `41072669d14b89f4cdabea3147488b61673a362c` and cutoff `2026-11-10T08:26:05Z` (17:26:05 Asia/Seoul). The original timing-utility, direction-specialist and bounded-autopilot contracts remain unchanged. The prior timestamp normalization and census in PR #145 were already merged; this is a distinct bounded follow-on repair.

## Reproduced defect and repair

A stored green independent audit could be passed to the census with changed ledger provenance, public-proof verification ID or outcome publication claim. All three synthetic counterexamples returned a false green census before this repair. This does NOT mean these fields were corrupted in the real ledger.

The independent audit now fingerprints all fields and ordered rows of ledger, outcomes and deliveries using canonical JSON SHA-256. The census independently reconstructs that binding and refuses missing or mismatched proof. Hash binding proves internal snapshot consistency, not provider authenticity. An attacker who rewrites every file and checksum is not defeated by these hashes alone.

Future collector context cannot explain an earlier missing outcome. Derived output cannot overwrite inputs or the upstream audit, including symlink/hardlink aliases. Input bytes are checked around an atomic output write. These safeguards are not a claim of complete filesystem-race security.

## Fixed-snapshot results

|Original record disposition|Rows|
|---|---:|
|Scored nonoverlapping, timely-public targets|256|
|Later reissue of same target|21|
|Overlapping target excluded|22|
|Outcome missing in saved snapshot|12|
|Public timing requirement unmet|12|
|Future target pending|20|
|Total original ledger|343|

All 309 stored observed outcomes were independently recomputed, including rows excluded from performance. No new internal arithmetic disagreement was detected. Scored result: **96 correct / 256 = 37.50%**; 160 incorrect. Balanced accuracy: **37.1087%**. Brier loss: **0.6735330688860411**. Log loss: **1.1265162470600438**. Nine observed market-local dates; **0/40** groups meet the preregistered minimum sample gate.

|Actual direction|Actual|Calls|Hits|Missed|False calls|Recall|Precision|
|---|---:|---:|---:|---:|---:|---:|---:|
|Up|75|54|16|59|38|21.33%|29.63%|
|Down|93|34|15|78|19|16.13%|44.12%|
|Flat|88|168|65|23|103|73.86%|38.69%|

Paired frozen-baseline comparison exists for 244 targets, not all 256. Model: 92 correct, Brier 0.6744959203027607. Original baseline: 87 correct, Brier 0.6585626179098185. Thus the modest hit-rate difference does not establish probability quality or timing utility. Twelve missing original baseline probability vectors were not backfilled. Four previously frozen shadow candidates were compared only on their same original available target cohorts; none was selected or promoted.

Attempt ledger: 2224 rows, 925 prediction attempts, 1299 no-calls (936 insufficient regular-session time; 360 missed issuance/delivery window; 2 source locks; 1 rate limit). This is not full market-opportunity or human-delivery coverage. Learning: 256 events for 256 distinct forecasts; no new learning by this audit.

Paper plans: 114. Actual human receipts, executable quotes and preregistered cost evidence remain absent. Pre-target plan web proofs: 76; late proofs: 38. A web proof is not a human notification. Twelve mature missing outcomes remain unresolved and are never assigned invented prices/results. Raw exchange prices, KRX/NXT-specific execution and US extended-session execution, after-cost benefit and untouched confirmation are unverified. Timing usefulness remains **not_proven**, not a buy approval.

## Test-first evidence and failed attempts

Preregistration: PR #145 comment 6762742019. Read-only evidence export: run **42782592118**, artifact **13746287856**.

First RED/GREEN run **42784383881** reproduced all three original synthetic flaws, applied the repair and passed the regression step. Actual independent/census/learning/attempt audits also passed. The harness then failed because it wrote the derived audit under `/tmp` but invoked a guard expecting the default root audit filename. No source repair commit was published by that failed run. The failure was preserved; no assertions were disabled.

Second run **42785887287** supplied the same derived audit to the unchanged acceptance function, and completed all gates successfully. It committed only two tested auditor scripts to the research branch at **07c16f783235b5dca3399ac42770e2512236ab2b**. Artifact **13748363140**, SHA-256 `c22e8f3619a7746f9533e72befda20c0072b2b0adb6d630189cf68370e3a68c0`.

Actual regression counts: **149 timing tests + 19 independent-audit tests + 17 learning-audit tests + 194 forecast/learning/direction/paper/pipeline tests = 379 Python tests**, plus **13 JS forecast contracts and 9 bounded-recovery checks**. Fourteen new source-binding test methods include multiple adversarial subcases. Existing model outputs, scored IDs and all prior independent audit fields except generation time remain identical. **677 other tracked files** remained byte-identical during the verified repair. No model trials, new training or original evidence rewriting.

A separate self-contained fixed report exposes all 343 original rows, dispositions, seven distinct clock categories, initial probabilities and frozen bands. Local Chromium tests checked four viewports (1440,1245,390,360) with 48 assertions, including search/filter counts, no horizontal overflow and unproven status. Local screenshots are not proof of a public deployment. Production merge/deployment claims require their separate actual evidence.

## Preservation

No orders, funds, new accounts, API authentication, secrets, paid data contracts, model/threshold changes, price or ledger rewriting, strict-green relaxation, unrelated widget changes, collection schedule changes or modifications to the existing data-error monitor. Remaining limitations are explicit rather than treated as passing checks.
