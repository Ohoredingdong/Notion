# Independent learning-weight lineage — preregistered research-only experiment (2026-10-30)

**Frozen main for this experiment:** `a5a6398f407c215feb20605589b257dc7bee516f`. **Scope:** at most one engineering audit-coverage patch, 0 predictive models, 0 threshold trials. No market-price, order, strict-green, public forecast, alert or learning-state changes.

## Evidence gap and predeclared hypothesis

PR #42 introduced a producer-independent learning event audit: unique event IDs, eligibility, published timing, group, actual class and syntactically valid 64-character weight hashes. Source inspection of `scripts/audit_stock_learning_evidence.py` lines 78–80 shows that `weights_before` and `weights_after` are only checked for hexadecimal shape; the verifier does **not** compare a group's final event hash to the immutable saved weights or link consecutive updates. Consequently a well-formed but altered 64-character weight digest could plausibly be accepted. This is an integrity coverage hypothesis, **not** evidence that any real learned weights were altered.

## One predeclared fix and tests

Add a read-only, producer-independent check to `scripts/audit_stock_learning_evidence.py` of existing saved evidence only. Validate per-group chronological weight-hash chaining in the append-only event order; reconcile group `learned` count with the number of saved learning events, terminal event `weights_after` against SHA256 of the persisted group's exact weight list using the existing canonical JSON serializer, and latest `last_train_end` with the frozen forecast target. Never infer missing historical hashes or learning events. A missing/malformed terminal group is an integrity error, not a new performance observation.

**Synthetic red case before fix:** change one stored `weights_after` to another valid 64-character string while leaving forecasts, outcomes, deliveries and saved learning state identical: original independent gate should report consistency, which is an expected failing test. Additional negative fixtures: broken chain across two events in the same group, wrong persisted `learned` count, and wrong persisted terminal weight digest. Valid reference fixture and real frozen source must pass after patch.

An existing issue in `docs/experiments/timing-learning-event-audit-20261030.md` was reviewed to avoid repeating its tests. Only a separate weight-lineage property is targeted. Run original forecast evidence audit, learning audit, applicable model/forward/controller regression tests, and independent audit on unchanged evidence. Branch trial data must not publish and no source/approval/scheduling policy may be changed.

## Acceptance / interpretation

Accept **only** after red failure is reproduced, green tests pass, real saved learning history remains consistent, diffs are limited to this read-only audit and the note, and the independent main audit passes if merged. Reject/revise if an unverified assumption about historic state would make the saved legitimate history fail.

Workflow success, validated hashes and preserved event ordering do not validate raw exchange candles, model skill, executable quotes, human receipt, after-cost simulated edge or untouched forward selection. Timing utility gates in `docs/stock-timing-acceptance-20261029.md` and the frozen movement_then_direction shadow policy remain unaltered.

**Prior related work:** PR #35 (transaction guard), #37 (publication chronology), #38 (all outcomes), #39 (shadow probabilities), #41 (age provenance), #42 (learning-event chronology). This trial adds only terminal weight lineage, not another attempt to improve accuracy on the same six results.

## Completed experiment record (UTC 2026-10-29)

- Frozen main `a5a6398f407c215feb20605589b257dc7bee516f`; work remained on isolated branch until the checks below.
- **Red reproduction:** [Actions 40935164734](https://github.com/Ohoredingdong/Notion/actions/runs/40935164734). An event `weights_after` replaced by another syntactically valid digest was accepted by the prior independent verifier (`learning_evidence_consistent`), making the explicitly expected test fail. This was a synthetic counterexample, not evidence of a production overwrite.
- **Small green fix:** group `learned` counters now match the append-only event count; successive `weights_after` / `weights_before` are linked in event order; the terminal event digest must equal the exact SHA256 of persisted group weights; and `last_train_end` must match the last frozen target. Unseen groups or missing recorded events fail closed. Only an existing read-only audit script was changed.
- **Green branch:** [Actions 40935523627](https://github.com/Ohoredingdong/Notion/actions/runs/40935523627) passed baseline audit/real saved history and one-event negative fixtures plus the valid two-update and broken-chain tests. [Full isolated regression Actions 40935624092](https://github.com/Ohoredingdong/Notion/actions/runs/40935624092) passed 9 standalone price/timing audit tests, 15 learning-integrity tests, 26 prospective tests and 86 learning/direction/bounded-autopilot tests, source/schema and JavaScript guards, and a frozen-source diff check. It independently re-read the same actual 6 learning events without rewriting them.
- **Actual frozen market evidence remains insufficient:** 53 original ledger rows, 32 unique events, 8 overlapping excluded, 24 nonoverlapping target definitions; 21 stored outcomes arithmetically consistent; 6 policy-eligible scored, 3 correct (all six predicted flat, three actual down missed and no actual up sample). As of 2026-10-29 18:49:10 UTC, 12 nonoverlapping targets were still future and another 6 had matured without a stored result after the last source forecast run; this is **missing evaluation evidence**, not an assertion of exchange outage. All 53 stored direction/probability, original observation-to-issue, 30-minute target and training chronology checks passed in a separate read-only calculation. No confirmed human notification receipt, independent venue candle or executable bid/ask, costs-after-delivery or untouched future superiority.
- **Trial count:** one preregistered audit-integrity hypothesis, one bounded read-only patch, one deliberately failing red run, two interim green checks and one full green regression, no predictive candidates/hyperparameter tuning, no baseline backfill, no scoring threshold changes, no production data overwrite. Re-run the independent main audit after merge if a scoped PR is accepted.

This does **not** clear any condition for a timing-utility completion notification, does not certify that historical weights were cryptographically signed by an outside party, and does not turn a prediction into a strict-green buy approval.
