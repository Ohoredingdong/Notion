# Prospective price direction — direction-forecast-1.0

This is an implemented statistical forecasting pipeline, not a declaration that its predictions are profitable. The original strict-green-1.0 controls, document approvals, authenticated OpenDART and trade permissions are unchanged. No order API is used. Initial coverage is four market indices and eight existing watched companies; it is not a recommendation list.

## Targets and timing

Daily: the next regular session's open-to-close direction, issued BEFORE that session's open. An intraday run must not relabel yesterday's close-to-today movement as a new daily forecast.

Intraday policy revision `provider-latency-30m-v1`: completed 5-minute bars, a fixed **30-minute gap from the last observed bar end**, then a fixed **30-minute open-to-close target** inside the same regular session. Training labels and prospective issuance use exactly the same gap. This replaces the original 5-minute gap because the initial real collection returned roughly 15-minute-delayed Korean data. The change is an operational latency correction, not a claim of improved returns. Exact target start/end and input age are stored. A forecast is rejected if its target already started or if the session cannot accommodate it. This is not necessarily 'the next 30 minutes from now'.

No fake future bars, no unfinished daily close, no overnight extrapolation, no retroactive issue date. The new model only forecasts periods after its implementation; it did not predict earlier moves on the implementation date.

Collection uses Yahoo history through yfinance until the authorized real-time provider/server is actually connected. KOSPI uses a strict raw-chart parser through the same Yahoo client to avoid a provider-library live-row array mismatch. Unequal OHLC arrays and duplicate timestamps are rejected, not truncated to force agreement. This is the same unofficial provider, not independent verification. Historical prices can be retrospectively adjusted; evaluation is NOT a point-in-time-vintage backtest.

## Model and validation

A regularized three-class logistic model uses lagged returns, volatility, moving-average distance, candle range/body and past high/low drawdown. It does not pretend to consume missing investor flows, orderbook, events, volume signals or company forecasts. The separate Toss watch engine was not changed by this addition. Price-return bands are preset research policy, not guaranteed losses or optimized entry recommendations.

Sessions are split chronologically 60/20/20 into train, probability-temperature calibration and test. Labels crossing boundaries are purged. Scaling uses training observations only. The model remains frozen on the training part; it is not quietly refit on its test data. Non-overlapping test windows are used for accuracy, multiclass Brier/log loss and comparison with a smoothed training class-frequency baseline. Session bootstrap diagnostics do not control all multiple testing or establish live alpha. Research probabilities may be displayed even when the baseline is not beaten, but the lack of verified edge is explicitly marked. A high estimate is not investment success probability or strict-green approval.

## Prospective ledger and public timing

The append-only forecast ledger freezes issued_at, actual retrieval time, observed bar boundary, future target window, model hash, source-run ID, input features/hash, fixed class band and complete original probabilities. Duplicate IDs retain the original timestamp. After the interval closes, actual target open and close are compared with the previously frozen definition. Missing prices and invalid timing cannot count as success.

A separate delivery ledger records the first verified public HTTP response of the exact snapshot and JavaScript. This is proof of public availability, NOT human push-notification acknowledgement. Publicly late forecasts are excluded from the timely-forward summary. Research price observations are not executable trade returns. Initial forward baseline comparison and sufficient future performance history remain pending. Different model revisions must not be interpreted as independent market events.

## Operational boundaries

GitHub schedules run at 17/47 past the hour in configured KR/US windows and can be delayed. The browser refreshes each minute; only the exact displayed target period is valid. Missing or stale data yields no_call. This is not a persistent minute-stream processor. Existing authenticated OpenDART is unaffected; disabled Toss configuration is not silently enabled.

Model unit tests cover leakage, purging, future targets, session guards, unfinished bars, missing candles, duplicate ledger entries, calibration separation and later scoring. UI tests check invalid probabilities and temporal contracts. Synthetic fixtures exist only in test files; production has no synthetic-data fallback. Desktop/mobile browser checks use actual generated JSON. Exact public JSON, JavaScript hash and main radar integration are checked separately from repository publication.
