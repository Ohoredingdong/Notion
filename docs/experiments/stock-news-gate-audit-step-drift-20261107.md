# Research preregistration — skipped news-triggered forecast audit drift (2026-11-07)

**Status at registration:** RED candidate; no production approval or timing-utility evidence.
**Frozen main:** `6aa64b9431f0d31d62b362bfbea83dc750ab45c2` (2026-11-07 00:34 UTC).
**One hypothesis:** `scripts/audit_stock_timing_trigger.py`'s exact `GATED_STEPS` catalogue omits two steps already present in `.github/workflows/stock-forecasts.yml`. A completed, all-skipped news-driven forecast run is consequently misclassified as an executed forecast. The downstream audit then correctly rejects unmatched archival provenance, producing a false operational failure even though no forecasts, model training or publication ran.

## Pre-change, immutable evidence

- Upstream forecast [run 42318896899](https://github.com/Ohoredingdong/Notion/actions/runs/42318896899), 2026-11-07 00:32 UTC, head `842bf27d7768182a916a5f113d22b96766cba33a`, reported overall success, but its only research job executed **only** the market-hours gate; all 14 subsequent gated steps were skipped.
- Downstream independent audit [run 42318915435](https://github.com/Ohoredingdong/Notion/actions/runs/42318915435), 00:33 UTC, failed at upstream provenance (mismatched controller run ID/source SHA/forecast run ID). Its classifier returned `execution_or_unrecognized_upstream` despite the recorded all-skipped research job, causing a needless audit of older, unchanged archive data. The bounded recovery [42318915479](https://github.com/Ohoredingdong/Notion/actions/runs/42318915479) skipped.
- Existing `GATED_STEPS` does not include `Opportunistic first paper publication proof after automatic Pages build` or `Persist only newly observed paper first-public proofs`, both present in the operational workflow and skipped in the initiating job.
- This is a **classifier/diagnostics false alarm**; neither an exchange price issue nor a forecast accuracy improvement. Rejecting mismatched provenance itself is a correct fail-closed behavior and must remain unchanged.

## Single bounded repair and acceptance plan

1. **RED:** Add an independent regression fixture encoding the actual observed 17-step upstream run, plus a static workflow/catalogue agreement check. Confirm old classifier fails both tests; record CI failure and do not claim success.
2. **GREEN:** Add only the two missing names to the read-only classifier's `GATED_STEPS` tuple. Preserve exact run ID, commit, attempt, branch, step order/status and all fail-closed checks. Any genuinely executed, incomplete, unknown or mismatched upstream still forces full independent audit and may fail.
3. Run the updated classifier suite, workflow provenance guards, existing independent forecast audit and timing acceptance tests via PR CI. Keep original `stock-forecast-*` evidence, live model, publication and strict-green controls unchanged; no manual forecast rerun or main deployment in research mode.
4. Record failures, runs and results; leave change as review-only PR until required checks and deployment procedures are explicitly satisfied.

**Unchanged usefulness gates:** minimum 120 nonoverlapping future targets and 20 days per group, both up/down thresholds, immutable original probabilities including `movement_then_direction` shadow, quote and human-receipt evidence, after-cost prospective comparisons, untouched follow-up, strict-green-1.0, no orders. An audit no-op is never trading readiness. No user completion notification.

## Recorded outcome — research only

- **RED** [independent audit run 42320291853](https://github.com/Ohoredingdong/Notion/actions/runs/42320291853), candidate commit `2b90cce666ea5587fd3c121b3b0e33e24d72e916`: completed **failure**. The two independent tests failed as preregistered; 12 other classifier tests passed. The observed 17-step news run was falsely returned as `execution_or_unrecognized_upstream`; step catalogue differed exactly at the two added paper-proof steps. A missing-summary follow-on error is consequential, not a third independent cause.
- **GREEN** [independent audit run 42320352893](https://github.com/Ohoredingdong/Notion/actions/runs/42320352893), candidate commit `56d7b89a2f3294f8ebefb423e5005bd372632b5a`: completed **success**, all 14 classifier controls passed (including the real-event fixture and static live-workflow step agreement). Existing negative controls for non-skipped steps, mismatched attempts/commit, partial/incomplete jobs and integrity remain passing. Independent ledger arithmetic, learning-event chronology, attempt coverage and timing-acceptance guard passed on the research branch.
- Independent summary recomputed **188 scored / 62 correct**, three-class Brier ~**0.691012336**, 0/40 groups meeting the prospective sample minimum. The 1,784 attempt rows include 739 forecast attempts, 1,045 no-calls (760 session-deferred, 282 missed actionability window, two cache-lock failures and one rate-limit). No evidence was made eligible or retrospectively delivered by this change.
- Final diff relative to pinned main: **three files**, 2 literal step names in read-only classifier, 53 test lines, this experiment note. No production workflow definition, historical forecasts or trading inputs were changed. No public deployment test is relevant to the read-only classifier itself; **postmerge production workflow_run confirmation is not performed**. Branch remains **draft PR #140**, not deployed/merged to main. A green branch test does not resolve the prior failed operational run retroactively.
- **Cost / statistical gate:** Not proven. External exchange candles, executable bid/ask, genuine human receipt, after-cost paired paper execution and untouched out-of-sample evidence are missing. No promotion, model rollback or completion notice.
