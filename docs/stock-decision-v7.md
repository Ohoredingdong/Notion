# Investment Radar — decision v7

This is the investment decision widget, not the separate training widget.

## What is now collected

- Last completed regular-session daily OHLCV. Partial sessions are excluded using XKRX/XNYS calendars and a 30-minute reporting buffer.
- Current/next fiscal year analyst EPS average, low, high, analyst count; next-FY EPS revisions from 30 days ago.
- Analyst target low/median/mean/high and number of opinions.
- Provider-aggregated cash, debt and EBITDA; estimated earnings calendar.
- Official company RSS publication metadata when accessible. OpenDART filing metadata is enabled only when DART_API_KEY is configured.
- Existing separately collected official historical financial reconciliation.

Collection is scheduled at 07:47 and 16:47 Asia/Seoul, also after official-audit workflows finish. GitHub schedule execution may be delayed. Frontend reload reads the saved result, not a new provider/API job.

## Sources and their limits

- yfinance 0.2.66, unofficial Yahoo Finance reader: https://ranaroussi.github.io/yfinance/
- EPS estimate schema: https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_earnings_estimate.html
- EPS trend schema: https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_eps_trend.html
- exchange-calendars 4.11.3: community-maintained exchange calendars, subject to exceptional closure updates.
- OpenDART API: https://opendart.fss.or.kr/
- Actual per-company source URLs and collection timestamps are stored in stock-decision-data.json.

A successful HTTP request is not independent verification. Analyst estimates/targets are not audited company guidance. Their adjustment basis and individual report publication dates are not exposed in the current feed. Never equate target-price dispersion with probability or a downside floor. This is personal research, not a licensed commercial redistribution feed; commercial use requires appropriate data rights.

## Decision rules (explicit assumptions, not empirically optimized)

Short term: trend (close > SMA20 > SMA60), prior 20-session high breakout, volume ratio >= 1.5, positive matched-session relative strength, structural reward/risk >= 2, distance to prior 10-session low <= 8%. A recent split or estimated earnings in the next 3 days blocks the conditional label. The calculation does not guarantee execution at a stop or a future return.

Long term: require a fresh completed close; usable EPS/target ranges with at least 5 analysts; current matching historical revenue/EPS/FCF proof; known debt/cash/EBITDA; EPS 30-day revision. Then distinguish negative outlook/leverage, insufficient price gap, broad forecast dispersion, and conditional review. Target median / 1.20 is only a price-screen assumption requiring 20% target-price room, NOT a DCF or intrinsic-value estimate.

A candidate may still be rejected by a human because primary guidance, macro risk, position sizing, diversification and company-specific debt maturities are not fully modeled.

## Safety and current omissions

- No trades, brokerage credentials, user financial inputs, paper logs or changes to stock-paper-investing.html.
- No invented fallback forecasts, volumes or likelihoods.
- No foreign/institutional-flow inference from trading volume. That feed is not connected.
- No forecast FCF/DCF model, primary guidance parsing, independent target-history reconciliation or company debt-maturity model yet.
- Failed refreshes and results older than 18 hours suppress actionable labels in the new view.
- Historical regulatory verification is invalidated by changes to compared input values, period or expired audit age.
- DART_API_KEY remains a setup dependency. Store it only in repository Actions Secrets; never in public files or chat.

## Verification

The first full data run collected completed prices, EPS ranges and target ranges for all 10 tracked symbols. The official-event wrapper collected 6 recent source links in that run. 24 numerical/decision/market-clock tests passed. A complete checked-out widget with collected JSON passed 22 desktop/mobile browser cases, including selection, source links, absence of training forms, width checks, stale-input suppression, failed-fetch suppression and runtime-error checks. Public HTML returned HTTP 200 and contained the v7 script. These software tests do not validate investment performance.

Files: scripts/update_stock_decisions.py, scripts/refresh_stock_decisions.py, scripts/test_stock_decisions.py, assets/stock-decision-v7.js. Runtime/fixture tests remain separate from investment accuracy claims.
