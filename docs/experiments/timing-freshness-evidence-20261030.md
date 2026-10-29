# Independent forecast evidence freshness diagnostic — 2026-10-30

**Preregistered before code changes; research-only, no trading, no new model recipe.**

Pinned main: `02fff1e758dd854f96e5064aa68e3b0e163bd1d3` (data-only commit), immutable sample SHA for forecast ledger: `859cd1ced83b0eade2b698eb4283763568cd2287`. Branch `research/timing-freshness-evidence-20261030`.

## Falsifiable hypothesis and expected red test

The read-only independent forecast auditor can return `ledger_arithmetic_consistent` without exposing how old the latest underlying source observation, receipt, issue, or confirmed public snapshot is as of a given cutoff. An old verified snapshot must never imply fresh executable signal or human receipt. The current status is correctly an *arithmetic* status, but the missing independent freshness evidence makes the elapsed gap harder to inspect.

At cutoff `2026-10-29T16:13:11Z`, GitHub showed the last successful Stock Prospective Forecasts Actions execution at 2026-10-29 13:45–13:47 UTC (run 40884823206), with last stored independently verified public snapshot `2026-10-29T13:47:26.310461Z`. The configured weekday workflow schedules multiple intervals between those times. No additional forecast run was visible in the GitHub Actions runs queried. This is an **observed run gap**, NOT proof of the root cause, an exchange-session outage, or missing minute candles. GitHub itself states scheduled runs can be delayed/dropped. Never label scheduled Actions continuous live monitoring.

Test: a synthetic time-consistent forecast at 13:36 UTC with observed data at 13:30, received 13:31, and a snapshot public 13:36:25. Re-audit as of 16:13:11. Baseline auditor lacks a `freshness_evidence` object; the red self-test expects a recorded last-observed/received/issued/public timestamp, public age >150 minutes, and two false capability flags. It must fail before the code changes.

## Narrow permitted research change

- Expose **read-only, cutoff-scoped** `freshness_evidence` in the independent audit: last underlying `observed_until`, `received_at`, `issued_at`, valid `public_verified.verified_at`, and age in minutes, with missing values as null.
- Never translate age to a confirmed session outage: exchange calendars, legal exchange tick/candle archives and actual user receipt are not in this auditor. Leave `exchange_session_freshness_verified=false`, `human_delivery_verified=false`.
- Do not change status, scoring selection, immutable forecasts, outcomes, attempts, learning, source state, strict-green, promotion thresholds, or publication workflows. No new model/candidate or backfill.
- One preregistered audit-evidence hypothesis, **zero** model/hyperparameter searches. Red and green are engineering tests, not financial performance.

## Gates and limitations

Run red/green isolated GitHub Actions on branch; original auditor unit suite; 21 stored outcomes arithmetic; same six eligible nonoverlapping scored forecasts/three correct/three down misses, 24 non-overlap and 8 overlap. Also run forecast/model/learning/autopilot regression, unchanged public site and no data publishing. The accepted event group policy (120 nonoverlap/20 days/min 10 each direction, direction metrics, cost-after-delivery, untouched later data, real notifications) stays unfulfilled. If any gate fails, leave this as a research branch and do not merge. The schedule gap's **cause and resolution remain unverified**; this patch only improves evidence visibility.

## Actual isolated red/green experiment and decision

- **Red, synthetic reproducible gap:** [GitHub Actions 40910563220](https://github.com/Ohoredingdong/Notion/actions/runs/40910563220), code commit `2053a7413a3bfb5a70bb5c415c94b24e82fbf0dd`, failed the new test as expected with `KeyError: 'freshness_evidence'`; other 8 independent auditor unit tests passed.
- **Green, isolated audit metadata:** [GitHub Actions 40910717718](https://github.com/Ohoredingdong/Notion/actions/runs/40910717718), commit `0b4a968b11c9983a41979d4d17d888652803f3b4`, completed success. **9** audit unit tests, **26** existing forecast unit tests, **83** existing learning/direction/autopilot tests, plus source/session guards passed; no output published to main.
- Pinned 2026-10-29T16:13:11Z recomputation preserved **53** predictions, **32** unique target keys, **24** nonoverlapping, **8** overlaps, **21/21** internally consistent stored outcomes, **6** eligible first/timely-public future outcomes, **3** correct, **3** missed down, **0** actual-up samples, and no changes to original scoring.
- Read-only evidence at cutoff: latest source observation 2026-10-29T13:45:00Z, source receipt 13:46:21.941724Z, forecast issue 13:46:24.264343Z, public snapshot verification 13:47:26.310461Z. **Public snapshot age 145.7448 minutes.** This is NOT a proof of a market feed outage and NOT actual user notification delivery. It also does not verify exchange candles/quotes or post-cost trades.
- One preregistered hypothesis, **one failing synthetic red** and **one passing green**; no model candidates or parameter selection were tried. Existing 6 scored samples were rechecked, not new future outcomes.
- Root cause of missing scheduled run observations remains **unresolved**. GitHub scheduled Actions are best-effort; bounded recovery only sees completed failed workflow runs and cannot repair a run that never triggered. Do not claim schedule gap fixed by adding observability. Main independent audit after a code merge is required before calling the metadata published.
- **Decision:** safe audit-only provenance metadata; no evidence of predictive edge, trading utility or a valid completion alert. Acceptance status remains `timing_utility:not_proven`.
