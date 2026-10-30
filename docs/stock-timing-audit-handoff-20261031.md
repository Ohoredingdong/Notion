# Independent audit handoff after forecast completion — 2026-10-31

**Scope:** read-only engineering verification. Does **not** modify the forecast model, stored market data, labels, timing-utility acceptance policy, strict-green-1.0, orders, notifications, or credentials.

## Frozen observations and prior work

- Pinned study base: main `88898498f5dcfd44083a8fff951b6087952ee258`; first read the three preapproved acceptance, direction-specialist and bounded-autopilot contracts.
- Prior work: PR #73–#76 added independent evidence guards, PR #79–#82 logged previous sensitivity/shadow research. None added a successful-main forecast-completion event trigger to the independent audit workflow.
- Forecast Actions [41139310341](https://github.com/Ohoredingdong/Notion/actions/runs/41139310341) completed at 2026-10-30 22:39 UTC. It generated **42 independently scoreable frozen cases** (13 correct) and **42 learning events**, with six new predictions and 12 new labels in that cycle. It did not promote a model. Source is Yahoo historical OHLC, not exchange-verified executable quotes.
- The most recent preceding [Independent Forecast Evidence Audit 41127359873](https://github.com/Ohoredingdong/Notion/actions/runs/41127359873) ran at 20:58 UTC, before the newly matured labels, and consequently only audited **30 cases** (11 correct). The hourly scheduled audit is best-effort, and its existing push paths cover code changes but not action-generated market evidence.
- GitHub documentation confirms that ordinary pushes made using the workflow's `GITHUB_TOKEN` do not initiate a new `push`-triggered Actions workflow. Adding the data file paths to `on.push` alone is therefore not a reliable repair. See [Triggering a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

**Pre-registered hypothesis:** a read-only `workflow_run: completed` dependency, restricted to `Stock Prospective Forecasts` on the repository's own `main`, will request an independent post-completion audit even when the upstream workflow publishes via `GITHUB_TOKEN`. Require upstream success and same-repository head; do not run for a failed or foreign branch execution. Retain the existing hourly/manual controls. This verifies evidence freshness, **not** directional accuracy or timing utility.

## Reproduction and bounded change

1. Added a five-test synthetic/static handoff contract to `scripts/test_stock_timing_audit_handoff.py`. The [RED PR job 41146661634](https://github.com/Ohoredingdong/Notion/actions/runs/41146661634) failed exactly two expected checks: the completion trigger did not exist, and the conditional success/same-repository gate did not exist. The other three control tests passed. This is **not** a failure of production forecast data.
2. Limited the change to `.github/workflows/stock-forecast-independent-audit.yml`: `workflow_run` for a completed main forecast, a fail-closed job `if` requiring upstream success / main / same repository, and restricted read-only `pull_request` CI that checks out the review head. Retained `contents: read`, no secret/ordering mutations, concurrency serialization, manual and hourly invocation.
3. [GREEN PR job 41146700487](https://github.com/Ohoredingdong/Notion/actions/runs/41146700487) successfully ran all five new controls, historical independent self-tests and immutable learning/coverage/timing guards. On the pinned prospective evidence it independently recalculated **42 scored, 13 correct**, **42 unique learning events**, **552 attempts**, and **0/24 groups** at the policy's sample gate. The completion guard returned `not_proven` without integrity errors.
4. The run did not independently obtain raw exchange candles, post-delivery executable quotes, actual user notification receipts or after-cost simulated-trading returns. The older 30/11 audit remains valid for its earlier snapshot; the 42/13 replay is a separate verification of the newer immutable snapshot, **not** 12 extra new predictions created by this change.

## Exit conditions and limitations

- This PR changes an **audit trigger**, not the production forecast, candidates (including `movement_then_direction`), fixed neutral bands, any scoring criteria, or evidence files. The test itself does not establish that GitHub will deliver a future `workflow_run` event. Only an actual successfully completed main forecast **after merge**, followed by an independently successful audit whose logs include its newest evidence, can verify the end-to-end handoff. Keep this item open until that happens.
- Audit success alone does not satisfy the preapproved acceptance contract: 120 non-overlapping future targets and 20 sessions **per group**, both directional classes, actual receipts, exchange-venue prices and executable quotes, after-cost prospective paper benefit and untouched follow-up all remain unproven.
- Attempt count is not future sample count; repeated audits must not be double-counted as new learning or performance. Failure and retry budgets recorded here: one deliberately failing RED PR run and one successful GREEN PR run, with **no forecast-model tuning or candidate selection trials**.
- Strict-green-1.0, original evidence, other workflows and the separate radar-error monitor are out of scope. No new user action or automatic completion notification is warranted.
