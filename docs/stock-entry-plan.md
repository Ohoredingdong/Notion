# Investment entry plan — entry-plan-1.1

The radar now separates research ranking, strict business diligence, technical timing, and point-in-time observations. No live order or validated return probability is enabled. OpenDART configuration and all strict-green-1.0 requirements remain unchanged.

## Data and timing

The exact original source SHA-256 and timestamp must match cases, depth and the review bundle. Actual per-company `collected_at` is used, never a regenerated JSON timestamp. The latest completed session is recalculated at evaluation time with the exchange calendar, including a 30-minute close buffer. A stale cached expected-session label cannot make yesterday's quote current after today's close. Calendars are community-maintained, not a claim of official real-time exchange verification.

The actual collector provides MA20/MA60, ATR14, previous 20-session high, ten-session support, volume ratio and market-relative price performance. The policy uses those fields, not nonexistent RSI/MA50 values. An inferred next-year fiscal-end display is explicitly distinguished from a confirmed provider date.

Initial uncalibrated hypotheses:

- Breakout: confirmed close at or above the previous 20-session high, above MA20 and MA60, volume ratio at least 1.5, positive relative performance.
- Pullback: MA20 at or above MA60, close no more than 2% above MA20, volume ratio at least 0.8, nonnegative relative performance.
- Early rebound: MA20 recovered but MA60 not recovered. Observation only, not an approved entry.

Both entry hypotheses still require complete strict diligence, current data, liquidity, EPS trend, independent valuation, acceptable extension, risk references and no imminent estimated earnings event. Timing references are shown as dated observation levels even when diligence is incomplete; they are never substituted for independent value or a purchase recommendation.

The next-session review ceiling is the lowest of the independent valuation reference, the frozen price plus 2%, MA20 plus 5%, and the frozen price plus half ATR14. No ceiling is supplied before data and diligence are complete. All numerical thresholds are explicit research policy, not empirically demonstrated optimums. Fresh quotes and disclosures must be rechecked next session. A support or invalidation price does not guarantee a fill or maximum loss.

## Audit and performance

The append-only ledger freezes the original date, collection time, price, EPS and its fiscal-period basis, evidence fingerprint, blockers, technical conditions and plan for the full covered universe. It does not backdate records or generate approval records. Observations begin only after the recorded decision. Future/unavailable data, revised reference prices, corporate actions and missing benchmarks cannot count as success.

The 1/5/20-session comparison is a price observation, not a filled-order strategy return. It includes index comparison, an explicitly assumed 30bp cost subtraction and observed close-price downside; dividends, execution, live spread and actual fees are not verified. No historical point-in-time fundamentals or out-of-sample profitable strategy are claimed.

Market scenarios are transparent conditional branches, not a claim that today's rally was forecast. Market breadth, sector contribution and actual investor-flow confirmation remain incomplete.

## Verification and deployment

Run `PYTHONPATH=scripts python -m unittest discover -s scripts -p test_stock_entry_plan.py`, `node tests/stock-entry-ui.test.cjs` and the desktop/mobile browser test. The workflow publishes without overwriting concurrent source updates and verifies the public JavaScript hash and source snapshot. A repository commit alone is not proof of public deployment. The dependency-install failure in the first run was corrected; only an actually successful later run can verify deployment.
