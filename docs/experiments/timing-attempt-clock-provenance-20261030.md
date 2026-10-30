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
