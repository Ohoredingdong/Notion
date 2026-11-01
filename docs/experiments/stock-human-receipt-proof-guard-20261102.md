# Bounded audit experiment: unsupported human-receipt claim (2026-11-02 KST)

## Frozen baseline and hypothesis (recorded before test/code mutation)

- Main SHA: `f7d0768a0ea62ccc78e9851341229185000c7376`. The three approved timing/direction/bounded-autopilot contracts were read at this SHA and **must remain unchanged**.
- Prior issue and experiment review: PR #82 and PR #89/#92/#93/#94/#95/#96; previous public-proof status/membership/payload and outcome-public-time audits are distinct. Those tests did not validate the separate `human_notification_received` statement as evidence of genuine user delivery.
- Frozen blob baselines: forecasts `1f254b2302dc1350ad95363ac4fbba5a4b145a46` (89), saved outcomes `f24b7e93f9aa438b8084e857429dbef99031d8fc` (69), public verifications `aff29efabcc6b3aa56f1eae87e76f1c00a2f96fb` (31), immutable learning events `dff634b1d6c5cf4236b8d5d018f92bfb99bf578c` (42), attempts `972eb510a3d108b003633f45cd168783436a3c8a` (696).
- Observed production state: all 31 public proof entries say `human_notification_received=false`; the latest independent audit reported 42 scored/13 correct and `not_proven`. There is NO authenticated recipient-acknowledgement evidence or executable quote record. This is a **hypothetical evidence-integrity gap**, not observed production tampering.

**Pre-fixed hypothesis:** The independent price/public audit verifies a `public_verified` delivery's canonical payload hash, timestamp and forecast IDs but may accept a synthetic delivery whose `human_notification_received` is changed from false to **true**, even after recomputing the untrusted canonical hash. If so, the stored evidence could falsely assert a human receipt without any separate recipient acknowledgment, while the audit returns `ledger_arithmetic_consistent`. A public HTML response by itself is NOT proof of user receipt.

## Exactly one synthetic RED/GREEN experiment, no model trials

1. Create valid synthetic intraday forecast + one legitimate public proof. Confirm independent auditor accepts `human_notification_received=false`.
2. Change only that proof's claimed receipt to `true`, recompute `verification_id` canonical hash to rule out detecting only a stale digest; require `integrity_errors` / `unsupported_human_receipt_claim` in the separate audit. This negative should fail **before** changing implementation (RED). Also assert malformed nonboolean receipt is rejected; missing legacy field remains missing and is not backfilled.
3. Once RED is verified in an actual pull-request CI run, make the smallest possible read-only auditor correction: when `human_notification_received` exists, accept only literal false without independent authenticated receipt adapter; reject true and nonboolean values. This guard does **not** turn a future genuine receipt into a success: a separate reviewed, independently authenticated delivery-evidence contract must precede such a change. Keep existing valid/missing legacy publication logic.
4. Run identical synthetic GREEN and all existing independent, learning/attempt, timing acceptance and necessary public-build regressions. Only then consider a merge; otherwise leave the PR draft. No production data, baseline labels, candidate/weight search, benchmark, promotion, human receipt claim, live order, strict-green gate, API secrets or other monitoring is changed.

## Trial budget and no-alert decision

One preregistered receipt-claim integrity hypothesis (false/true/malformed synthetic control within one fixture), **zero model candidates**, **zero forecast rescoring or new learned outcomes**. Record RED/GREEN Actions IDs, test counts, final changed-file list, immutable evidence checks and incomplete requirements here or in PR comments. Success strengthens *audit honesty only*, never authenticates human receipt, exchange prices, after-cost utility, 120-target/20-session support or a held-out later interval. No user completion notice unless the separate acceptance contract becomes fully satisfied.
