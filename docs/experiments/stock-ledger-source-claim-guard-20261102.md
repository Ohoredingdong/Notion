# Research: reject unsupported frozen ledger raw-source claims (2026-11-02)

Status: preregistered research-only negative control, not evidence of timing usefulness.
Pinned main: `d1da7366bd9b3c81253ae98b0c3b64d237ecfa93`.
Policy blobs: timing acceptance `69526101025c0394b13a55bfb73b9be5240e5fca`; directional specialists `6d5498666cd6da4d4528c46a4f1cb911715e90bd`; bounded autopilot `a5176f6aa075c49a090e6a3ec01b64fb323420ed`.
Independent auditor baseline blob: `be49bf7b48d2da05d7afa2139d8b7c1071c0779d`.
Examined prior PR #52 (model input as-of chronology), #100 (claims copied into outcome records), #82 (current operations); none independently checks *ledger* official-exchange/vintage assertions.

## Falsifiable engineering hypothesis

The independent frozen ledger validator checks chronological source usage but not the optional source-claim flags `provider_is_official_exchange` and `history_is_point_in_time_vintage`. A forged positive on either flag (including a truthy string or integer) may be accepted even though the source is only delayed Yahoo/yfinance history, not independently certified exchange raw candles or original point-in-time historical vintages. Any resulting RED failure would be a **potential integrity loophole**, not evidence of a forged original record or that a market-price prediction is profitable.

At the pinned main, all 101 actual frozen ledger rows explicitly use collector `yfinance`, `source_type=provider_historical_prices`, `provider_is_official_exchange=false`, `history_is_point_in_time_vintage=false`. Frozen evidence hashes: ledger `9fdaf49701bec7c28cb1dcdfba2f97cc8a66b6a2`, stored outcomes `05ba3bbd2d42fc9479d2b4456f6f608017186e7c`, deliveries `3e0b034e6954c46f22c1219df01e26ae0e0978bc`. There are **no discovered positives on the live data**. Claiming independent authentication of Yahoo price candles would be unjustified.

## One bounded negative-control family, fixed before change

- Negative: for each of the two claim fields, try `true`, `"true"`, and numeric `1` in an otherwise valid **synthetic** frozen record, with unchanged legitimate time, direction, probability and neutral-band fields; reject every unsupported claim.
- Positive: identical synthetic record with both claims explicitly `false`, and a legacy record without either optional field, pass without backfilling missing fields.
- Observe CI **RED** on the test-only branch before adding the validator guard. A deliberately failing test is a required research result and must not be merged.
- Minimal GREEN patch in independent read-only `validate()`: when these claims are present, require literal boolean `false` unless an independent authenticated source-evidence mechanism is subsequently designed and separately approved. No changes to forecast collection, past rows, historical labels, publishing logic, source authorizations, or evaluation thresholds.
- Run unchanged full independent evidence audit and new unit negatives at PR head. If impossible to obtain real GREEN or protected source is inconsistent, leave draft, do not merge or claim resolution. After any merge, require successful postmerge independent audit and required deployment checks; a passed test never proves trading utility.

Budget: one preregistered hypothesis, two fields × three synthetic falsified values, two valid control states; zero candidate model searches; record RED and GREEN attempts as they occur. No actual orders, API authentication, credential changes, additional tools subscriptions, strict-green relaxation, or changes to other monitors.

## Baseline timing acceptance

101 original predictions, 80 unique target intervals, 21 reissues, 8 overlaps, 72 nonoverlapping. 48 eligible scored / 14 correct (29.17%), mean three-class Brier 0.6653148943430279; 24 operating groups below 120 nonoverlapping targets and 20 sessions. Official exchange raw/quotes, authenticated human delivery, cost-adjusted prospective paper edge and untouched later segment all remain **unproven**. Latest successful research bundle (2026-11-02 05:48Z) and independent audit (07:56Z) are not prediction evidence. Keep `movement_then_direction` shadow and timing utility status `not_proven`.
