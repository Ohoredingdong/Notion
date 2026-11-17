# 2026-11-17 entry handoff diagnosis (local proposal, not deployed)

Base main: fc22eae46ffc588ad8cd7164de4bbe2981a78864.

At 14:39:27 UTC the monitor's seven findings reproduce exactly. Independent display audit checks 223632 values/contracts and reports 52 errors: one catalog/forecast identity-set mismatch and 51 old entry-plan prices after Korean closes updated.

The 12:47 accuracy run 44086472953 recomputed model audit successfully but correctly refused publication because display integrity failed. Therefore stale audit metadata is a consequence, not something to fix by changing its timestamp.

Forecast run 44072457033 at 11:16 is success-with-no-work: its research-hours gate succeeded and all actual model/checkout/publication steps were skipped. Last actual forecast remains 07:45 UTC. Do not count a green workflow icon as a fresh model result.

Reading and recommendations did publish successfully at 12:41/12:43, while the latest entry run remains 05:13. The exact GitHub event-delivery cause is not proven. This proposal uses the repository's existing explicit-dispatch pattern to make the final recommendation-to-entry handoff observable; it does not assert a particular platform bug.

## Local proposal
- After recommendation publication and syntax validation, explicitly dispatch the current-main entry workflow.
- Remove the reading/recommendation workflow_run entry triggers to avoid duplicate normal-path launches; retain standalone Strict Green Review trigger and schedules.
- Let the existing entry workflow dispatch the final audit after entry publication instead of recommendations dispatching audit prematurely.
- No new permission grant, forecast formula, collector, threshold, ledger or source-data edit.

## Verification
- 61 entry-policy, workflow-graph and audit-publication tests pass, including a new regression proving one entry dispatch, publication/UI ordering, success/main gating, preserved strict-review path and no trigger cycle.
- Original-data isolated replay regenerated entry plans with the existing builder: 52 display errors became 1 (catalog mismatch remains). Existing ledger bytes stayed an exact prefix; only the disposable replay added a new observation. No production ledger was modified.
- Replay output: snapshot_aligned=true; 11 data_wait, 93 diligence_wait, zero paper candidates and zero live recommendations.
- Static workflow tests cannot prove production dispatch permission or eventual event delivery. Not deployed or remotely pushed. No full-universe/model rerun attempted.

## Independent durability extension (local only)
- Rechecked main fc22eae46ffc588ad8cd7164de4bbe2981a78864; Actions API reported no in-progress jobs before editing.
- Recommendations no longer automatically cancels an already running publication/handoff.
- Reading no longer requests an audit before recommendations/entry have completed; independent audit schedules and other producers remain unchanged.
- Three approved handoff targets use a bounded retry helper (three attempts, 5/10 second backoff, failure remains nonzero). This is at-least-once delivery, not exactly-once; ambiguous network failure may create duplicate dispatches. Existing entry serialization and ledger dedup remain essential.
- Entry browser runner is Ubuntu 24.04 with Playwright 1.56.0, matching the version/runner combination independently verified by UI QA. Entry's full browser suite itself has not been run for this patch.
- 67 offline tests pass, including success, transient delivery failure, permanent failure, unsupported target and missing token. No real token/network/dispatch used by helper tests. Shell syntax and diff whitespace checks pass.
- Manual cancellation, runner termination, exhausted API retries, pending-job replacement and branch-policy permission denial are not eliminated. Existing scheduled entry reconciliation remains; this is bounded recovery, not a durable transactional outbox.
- No new permission, raw financial input, financial module pending approval, price/threshold/ledger change or automatic deployment.
- Remote Actions verification would require a separate read-only QA workflow on an explicitly nonproduction branch. Do not dispatch entry/recommendations themselves for QA: their checkout/publish targets are main.
