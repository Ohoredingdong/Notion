# Independent public evidence identity experiment — 2026-10-30

Pinned main: `214933caeecca203b0ffbb75a886d928e24d2493` (read-only production evidence). Research branch: `research/timing-public-verification-identity-20261030-r11`.

## Pre-registered hypothesis (one integrity hypothesis, no model selection)

The independent forecast auditor selects the earliest `public_verified` timestamp for each forecast but does not reject two *different* publication evidence rows sharing the same `verification_id`. A conflicting second record can falsely imply that a prediction appeared publicly before the target, even if the authentic verification was after the target had started. The user must not mistake this for human notification or independent exchange quote evidence.

Existing PR #45 checked copied outcome publication times; #54 checked unexpected forecast/outcome row status. Neither checked contradictory public verification IDs. No production fraud is alleged. The pinned ledger had 65 frozen predictions, 45 stored observed outcomes and 17 publication verification records, with no conflicting IDs, 18 eligible scores and 7 correct.

## Red / green criterion

Construct a synthetic intraday forecast issued 13:36 UTC, target 14:00–14:30 UTC. Genuine publication verification has a fixed ID, snapshot 14:05 and verification 14:06 (too late). Add a distinct synthetic record using the **same** fixed verification ID but a purported 13:36:30 snapshot and 13:37 verification. Under the old earliest-publication logic this changes the event from untimely to timely. The regression MUST fail before the patch by requiring `integrity_errors` with `conflicting_public_verification_id`; after a small read-only audit change it MUST pass. Identical replay must remain idempotent; legacy IDs absent in unrelated synthetic records are not backfilled or assumed authentic. All original 65/45/17 records must keep their evidence, and the 18/7 baseline must not change.

Only include code, focused tests, the independent audit invocation and this experiment note in the proposed patch. No source/model/trading/strict-green/notification/production-data changes. RED and GREEN CI status, attempted tests, test failures and limitations must be recorded before merge. No shadow promotion or predictive-utility claim.

## External evidence still missing

The calculation authenticates neither GitHub's actual user receipt nor official exchange candles. Independent executable bid/ask, fees/taxes/slippage and untouched prospective holdout are not connected. GitHub schedule/build success cannot satisfy the timing-utility acceptance contract.
