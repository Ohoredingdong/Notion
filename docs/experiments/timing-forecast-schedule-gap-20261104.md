# Scheduled forecast launch-coverage investigation — 2026-11-04

Pre-registered before writing code at https://github.com/Ohoredingdong/Notion/issues/105.
Frozen main ecf2bdb921fa9ee02593fd3a279edd82ce532c5b (2026-11-03 15:22:06 UTC).

Observed GitHub Actions repository-wide run listing at ~2026-11-03 15:30 UTC:
last scheduled Stock Prospective Forecasts created 2026-11-03 11:21:16 UTC (run 41626828963).
Configured UTC weekday schedule permits 12 proposed launches in 13:07–14:57 UTC;
zero matching scheduled forecast run creations are visible in the comparison window
2026-11-03 12:30–15:30 UTC, with 30-minute grace at 15:00 UTC.
Created run timestamps do not identify originating cron slots: never claim a
specific trigger was lost or a confirmed scheduler root cause. GitHub cron
can legitimately run late or drop events under high load, per GitHub docs.

Independent archived forecast arithmetic: 131 immutable rows, 21 repeat target
issuances, 14 overlaps, 96 nonoverlapping prospective targets, 72 eligible
scored/23 correct, Brier 0.669372163936, UP 1/23 recall, DOWN 7/28 recall.
12 matured targets have missing outcomes; 12 more are pending. 0/24 groups
meet directional minimums; real executable quotes, human receipt, cost-after
forward paper returns and untouched later replication remain unavailable.
No new prediction, backfill, model or strategy replacement is approved.

Script is read-only, uses Python standard library, exact pinned cron configuration
and at most five paginated GitHub API pages. Missing pagination is reported as
incomplete evidence. All tests use synthetic metadata, never market data.
Research Actions explicitly uses read-only access and saves a 7-day audit artifact.

Stop condition: no main deployment, schedule/monitor edits, custom real-time
service, external paid account, order, API-key print, price backfill or user alert.
This result diagnoses launch-coverage observability, not fixes GitHub scheduling
and not evidence of investment-timing utility.
