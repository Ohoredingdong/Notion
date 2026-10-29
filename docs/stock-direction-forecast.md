# Prospective price direction — direction-forecast-1.0

This is an implemented statistical forecasting pipeline, not a declaration that its predictions are profitable. The original strict-green-1.0 controls, document approvals, DART credentials and trade permissions are unchanged. No order API is used. The first collection scope is four market indices and eight existing watched companies; it is not a new recommendation list.

## Targets and timing

Daily: the next regular session's open-to-close direction, issued BEFORE that session's open. An intraday run must not re-label yesterday's close-to-today movement as a new daily forecast. Intraday: completed 5-minute bars, one full 5-minute gap, then a fixed 30-minute open-to-close target inside the same regular session. Exact target start/end are displayed. No fake future rows, no partial daily close, no overnight extrapolation, no retroactive issue date.

Collection uses existing public Yahoo history through yfinance until the user's authorized real-time provider/server is actually connected. This is unofficial single-provider historical data and scheduled best-effort operation, NOT a realtime Toss connection. Historical prices can be retrospectively adjusted; evaluation is NOT a point-in-time-vintage backtest.

## Model and validation

A regularized three-class logistic model uses only lagged returns, volatility, moving-average distance, candle range/body and past high/low drawdown. It does not pretend to consume missing investor flows, orderbook, events or company forecasts. Price-return bands are preset research policy, not guaranteed losses or calibrated entry recommendations.

Sessions are split chronologically 60/20/20 into train, probability-temperature calibration and untouched test. Labels crossing boundaries are purged. Scaling uses training observations only. The final model remains frozen on the training part; it is not quietly refit on its test data. Non-overlapping test windows are used for reported accuracy, multiclass Brier/log loss and comparison with a smoothed training class-frequency baseline. A session bootstrap diagnostic does not control all multiple testing or establish live alpha. Display research probabilities even when the baseline is not beaten, but explicitly mark the lack of verified edge. A high model estimate is not an investment success probability or a strict-green approval.

## Prospective ledger and public timing

The immutable forecast ledger freezes issued_at, actual retrieval time, observed bar boundary, future target window, model hash, source-run ID, input features/hash, fixed class band and the complete original probabilities. Duplicate issuance retains the original timestamp; it cannot be refreshed into a new successful call. After the future interval closes, actual target open and close are compared with the previously frozen definition. Missing prices and invalid timing are not successful predictions.

A separate delivery ledger records the first verified public HTTP response of the exact snapshot and JavaScript. This is proof of public availability, NOT a human push notification acknowledgement. Publicly late forecasts are excluded from the timely-forward success summary. No research observation return is claimed as an executable trade return.

## Operational boundaries

GitHub schedules run at 17/47 past the hour in the configured KR/US windows and can be delayed. The browser refreshes each minute; only the exact future window is valid. Unavailable or stale data yields no_call. This does not turn GitHub into a persistent minute-stream processor. Existing authenticated OpenDART is unaffected; disabled Toss configuration is not silently enabled.

Tests cover leakage, purging, future targets, overnight/session guards, unfinished bars, missing candles, duplicate ledger entries, calibration separation, invalid probability sums, and later scoring. Synthetic fixtures exist only in test files. The production runner has no synthetic-data fallback. Desktop/mobile browser checks use the actual generated JSON. Source history: official scikit-learn time-series split and calibration documentation, exchange-calendars, and yfinance history interface.
