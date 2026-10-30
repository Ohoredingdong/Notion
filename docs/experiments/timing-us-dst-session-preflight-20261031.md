# US DST market-session boundary preflight (2026-10-31)

**Research-only; documentation of a bounded independent synthetic clock experiment, not a predictive improvement or model promotion.**

- Frozen source commit: `92cc1c111e6934fd133bde83872f30881110d942` (main, inspected before this experiment).
- Source implementation examined: `scripts/stock_forecast_model.py` uses `exchange_calendars.get_calendar('XNYS'/'XKRX')`, `session_open`, `session_close`, `next_session`, and a 30-minute intraday gap + 30-minute target. Workflow pins `exchange-calendars==4.13.1`.
- Approval contract: `docs/stock-timing-acceptance-20261029.md` and `docs/stock-direction-specialists.md`; no acceptance gate is relaxed.
- Distinct question, not a repeat of `timing-freshness-evidence-20261030.md`: The US clock falls back on Sunday 2026-11-01. Does the exchange calendar's session UTC representation shift by one hour, reject the Sunday, preserve Korean market sessions, and respect early closes? This is a **clock-boundary engineering hypothesis**, not a forecast performance hypothesis.
- No candidate recipe, model parameter, sampled outcomes, or historical accuracy was used to choose a result. Model/hyperparameter trials: **0**. Clock test trials: **1**, five predefined assertions; failures: **0**.

## Predeclared test assertions and observed execution

An offline synthetic unit test used the same pinned `exchange-calendars==4.13.1` dependency, without external quotes or any simulated fills. Five predefined assertions completed successfully on the first run:

1. XNYS opened at 13:30 UTC on Friday 2026-10-30 but opens at **14:30 UTC** on Monday 2026-11-02; Monday close is 21:00 UTC.
2. Sunday 2026-11-01 is not an XNYS session and the next session after 2026-10-30 is 2026-11-02.
3. XNYS early close on Friday 2026-11-27 is 18:00 UTC; do not treat a full-length session as available.
4. XKRX open is 00:00 UTC on both 2026-10-30 and 2026-11-02, unaffected by US clock changes.
5. A hypothetical last five-minute bar ending at 19:50 UTC on 2026-11-02 leaves enough room for the frozen 30-minute lead plus 30-minute horizon; a bar ending at 20:05 UTC does not. This tests session-end rejection, not the executable source workflow.

Run result: **5/5 synthetic assertions passed**, Python `unittest`, `exchange_calendars 4.13.1`, `pandas 2.2.3`. The local standalone test is independent of production financial data and did not exercise the full `stock_forecast_model.py` or its web deployment; consequently this is **not** a whole-pipeline green claim. Results on actual post-DST sessions remain unobserved as of this preflight.

## Real evidence inspected separately

Pinned immutable source and evidence: forecast-ledger blob `b1af95894d1dd49ae7a0d86f19cda347d3200f08`, outcomes `2e4213bcca37c17a4e2feee327f702437e048b0b`, deliveries `29aa31eabfe9e7c14b3edb617282ba2fa471e960`, attempts `4f9ee2beee2078bee997fe29981e48dc110c3309`. Independent first-event and nonoverlap reconstruction on this same snapshot yielded 77 ledger entries, 56 unique targets, 8 overlap exclusions, 48 nonoverlapping targets; 30 scored with 11 correct, 6 matured missing, 12 pending. The 57 recorded outcomes passed independent return/band/class/Brier arithmetic checks, and issuance/receipt/observation/target chronology had no detected violations. These were **existing events**, not new predictions or learning.

[Stock Prospective Forecasts run 41049013008](https://github.com/Ohoredingdong/Notion/actions/runs/41049013008) actually tested, collected 24 delayed-source groups, published a verified research cycle with **0 new frozen forecasts** and **0 new learning updates**. [Independent Forecast Evidence Audit run 41087132337](https://github.com/Ohoredingdong/Notion/actions/runs/41087132337) checked 30/11 outcomes, 30 learning events, 504 issuance/no-call attempts and rejected timing-usefulness completion (`not_proven`). [Stock Autopilot Bounded Recovery run 41049316239](https://github.com/Ohoredingdong/Notion/actions/runs/41049316239) was skipped (no eligible infrastructure failure).

The prior documented GitHub forecast schedule/run gap remains **unresolved**; another workflow executing on time is not proof the forecast schedule ran. No new inference about GitHub's cause is made. A verified public JSON response is not human push receipt, and internal Yahoo-price arithmetic is not external exchange OHLC, KRX/NXT venue verification, executable bid/ask or cost-after-delivery paper performance.

## Decision and safe boundaries

**Result: no new reproducible DST session-boundary defect in the isolated exchange calendar checks.** No production-code change or forecast/learning/output edit is justified by this experiment. Retain `timing_utility:not_proven`, the four shadow candidate comparison policy including `movement_then_direction`, the strict-green-1.0 twelve checks, and separate stock-radar data-error monitoring. No orders, credential change, account/API authorization, source-price alteration, training replay, model swap, or new user action. This is a documentation-only record.
