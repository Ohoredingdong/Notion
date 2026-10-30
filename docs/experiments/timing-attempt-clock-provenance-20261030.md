# Timing attempt-clock provenance — preregistered 2026-10-30

Frozen baseline: main `4b99bc40132513fd99cedd61e91ea6fc991f10bf`.
Scope: read-only scheduler-attempt evidence audit only. No forecast model, raw data, score, thresholds, strict-green, order, secret, push, or unrelated workflow changes.

## Hypothesis before changes
`scripts/audit_stock_forecast_attempt_coverage.py` reconciles 504 scheduler attempts and 77 frozen forecast references, but does not currently inspect archived `checked_at` clock values. A synthetic attempt logged *after* its own summary `generated_at`, one without timezone, or contradictory `checked_at` values within one producer `run_id` may still be declared `attempt_coverage_consistent`. That failure would weaken provenance of the reported run-level coverage, although it would NOT prove a false trading signal or price tampering.

## One bounded test plan
1. Preserve a positive control from the existing independent attempt audit. Extend ONLY synthetic fixtures with explicit, timezone-aware attempt check times and report generation time.
2. Three independent negative controls: invalid/missing timezone, impossible checked-at after report generation, inconsistent timestamps within a run. An equal instant with a different UTC offset remains valid. Record RED before changing the audit.
3. Minimal fail-closed, read-only validation. No assumption that attempt `checked_at` equals forecast `issued_at`: an existing frozen forecast can be referenced in a later scheduler check, and initial check time can precede issuance by milliseconds.
4. GREEN synthetic plus real 504 archived attempts, existing independent evidence/learning/acceptance audits and, when relevant, broad forecast regression. Revert any temporary research-branch CI routing before review.
5. Track all failed and corrected attempts, branch diff, sha and checks. If real data fails, diagnose rather than overwrite history.

## Predeclared interpretation
Synthetic controls test the audit's ability to reject inconsistent *archived* clocks. Successful historical test or a successful pipeline does NOT demonstrate externally authenticated GitHub runner time, delivery to a user, executable venue quotes, after-cost strategy returns, model directional edge, or untouched future-confirmation performance. Keep timing usefulness as `not_proven` and the existing acceptance minima unchanged.

Current frozen direction evidence (from real report): 77 ledger entries, 56 unique future targets, 48 non-overlapping, 30 eligible scored / 11 correct, 2 observation days; paired baseline 18 events with incumbent 7 vs baseline 9 correct; all 24 groups below 120 targets / 20 days. Source is delayed historical Yahoo, not independent exchange raw bid/ask. The planned patch is engineering integrity only and must never trigger a completion notice.

## Actual experiment history and correction

- Original synthetic RED (test-only commit `1de1451aa69cffdb9468adcf62a2f32b280f73fe`) was written before the audit code; malformed/missing or timezone-naive clocks and future checks were not examined by the previous audit. No claim that archived times were forged.
- First GREEN candidate `0633d8e7a8a9c95d8dbf61fd06957a37158ae719` **failed** in [independent CI 41051280215](https://github.com/Ohoredingdong/Notion/actions/runs/41051280215): 504 archived attempts contained a legitimate repeated GitHub `run_id=41018457023` with two separate `checked_at` batches (2026-10-30 07:11:47Z and 07:17:38Z). This was a false positive from the experiment's overly strong assumption that one run ID implies one execution clock. The failure was preserved and not rewritten as a source anomaly.
- Revised scope (commits `ccf3cc9db67b8a3e5d188a2c4f4d45742105df67`, `7aec7fda60fd70a2e279df6be74d6d860cce11c6`): permit multiple real check batches in one GitHub run, reject malformed/naive `checked_at`, saved check timestamps strictly after the generated coverage summary, or missing/naive report generation time. Add explicit valid rerun positive control. No model/price/backfill edits.
- The initial "per-run timestamp must agree" hypothesis is **falsified for this producer** and cannot be claimed as a successful negative control. No new timestamp means a verified human notification or trading quote.

## Final research-branch verification

- Revised [GREEN run 41051638459](https://github.com/Ohoredingdong/Notion/actions/runs/41051638459), commit `7aec7fda60fd70a2e279df6be74d6d860cce11c6`: all 14 synthetic attempt-audit cases including timezone normalization and legitimate rerun passed; existing audit self-tests and learning-evidence tests passed; archived 504 attempts / 234 scheduler prediction attempts / 270 no-calls / 42 distinct original forecast references / 20 run IDs verified with no clock error. 234 ordinary out-of-session, 33 late-window, two cache locks, one provider limit are not all system failures.
- The independent raw stored-price audit remained 30 eligible events / 11 correct, down 1/7 and up 1/8, and independent learning evidence remained 30 events consistent. Acceptance guard remains `not_proven`, all 24 groups below sample minimum. These are frozen historical checks, not new forward results or proof of exchange prices.
- The narrowly corrected test hypothesis now verifies an archived check cannot be missing/naive or occur after its *own generated summary*; it does not infer market-time executable offers, actual user receipt or live-profit improvement. Repeating a GitHub run does not create a new unique forecast. Proposed operational change is a read-only auditor and synthetic tests only; a temporary branch-only CI routing edit must be removed before merge.

Experiments performed: one initial overrestrictive candidate **failed** the real archive, one revised candidate **passed** archived and synthetic checks. No unrestricted search or reused-outcome model selection.
