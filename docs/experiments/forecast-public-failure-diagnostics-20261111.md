# Forecast public-verification failure diagnostics — preregistered 2026-11-11

Type: engineering observability / research-only, **zero new prediction model hypotheses**.
Pinned operating main: `dd13dbb3c3c07be274c874f2363a2de75fcff5db`.
Prior review: PR #146 (immutable original evidence), PR #147 (failed recent_daily_logistic_v1 up-recall gate), and PR #116 (distinct existing first-public vs recheck telemetry). Existing recent-daily 2,520 historical diagnostic targets are exhausted for selection and are not reused.

## Reproduced new evidence and pre-fix defect

[Stock Prospective Forecasts run 42846282842](https://github.com/Ohoredingdong/Notion/actions/runs/42846282842), job 129934503929, started at 2026-11-10 15:37 UTC. It executed collection, original guard tests, research transaction, browser tests and published immutable transaction commit `33ca1c36295ce649c77e882b8386985b0e590d77`. The 16-attempt website verification then failed with **`RuntimeError: public_deployment_unverified: ValueError`** at 15:40:57 UTC. The verifier itself discards the known ValueError's public asset identity, making a genuine JSON-vs-JS-vs-HTML mismatch impossible to distinguish from its log. This is a reproducible diagnostics defect in `scripts/verify_stock_forecast_public.py`, **not proof of the underlying Pages deployment cause, a wrong forecast, or an exchange price error**. The separate recovery run 42846915866 correctly returned `published_bundle_requires_public_only_recovery`, retry=false; linked independent audit 42846916091 skipped. Do not blindly rerun already-published research.

## Single bounded engineering hypothesis, tests and stop

Hypothesis: preserve only a fixed allowlist of **asset-family/file identifier** in the final failure text after the same 16 attempts, so future independent audits can tell which public artifact differed while retaining the same byte comparison, chronology, issuance proof gates, error exit, and zero exposure of page query strings, URLs, tokens or arbitrary exception text. This does not itself repair Pages replication.

Modify only `scripts/verify_stock_forecast_public.py` plus an isolated synthetic test module and one push-only research workflow. Tests: correct JSON/JS/HTML bytes pass; mismatched JSON and JS bytes each raise a specific safe diagnostic; missing HTML integration is identified; an arbitrary malformed/network exception cannot leak a URL or secret; a mismatch cannot append delivery proof; existing forecast-paper and post-validation self-tests remain unchanged. RED negative control must reproduce absent file identity before the code patch. GREEN tests + independent forecast audit self-test and original verifier-related regression are required. Branch-only no production merge or new forecast execution. At most one engineering patch attempt; no model changes, no historical performance retuning or baseline adjustments.

## Completion and non-approval gates

Engineering success requires actual GitHub Actions green and a subsequent repository-file inspection confirming source/test/workflow files only; model acceptance remains HOLD. No new model trial (0), no new trained outcome, no score promotion. The 20 originally frozen PR #147 research shadow targets (US regular session ends 2026-11-10 21:00 UTC; KR next session ends 2026-11-11 06:30 UTC) remain pending as of 2026-11-10 16:27 UTC; never mark them correct/incorrect from target start, and never count unobserved external prices.

Do not touch original ledger/outcomes/deliveries/attempts/events/learning, strict-green-1.0, market-venue separation, data error monitor, schedules, live orders, APIs, accounts, credentials, or production model. Production forward accuracy remains 96/256=37.5% from old data, with 0/40 minimum-sample-group gates and no executable quotes/user receipts/cost-after-edge/untouched follow-up. User completed-timing-usefulness alert is prohibited.
