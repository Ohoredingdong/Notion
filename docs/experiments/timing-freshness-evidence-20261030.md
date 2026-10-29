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
