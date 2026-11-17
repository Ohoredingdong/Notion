# 2026-11-19 regular-session correction (local candidate)

## Evidence and limits

- KRX KIND explicitly confirms **KOSPI** regular market 10:00–16:30 KST on 2026-11-19:
  https://kind.krx.co.kr/external/2026/11/05/000141/20261105000216/99303.htm
- Hanwha Investment & Securities official customer notice (2026-11-10) explicitly includes **KOSDAQ and KONEX** in the same regular-session change:
  https://www.hanwhawm.com/main/bbs/indexView.cmd?cc_gubun=1&mode=center&nn_id=69155&pageVal=1&vc_bid=notice
- Separate KRX-origin KOSDAQ notice was not located. KOSPI notice alone does not prove KOSDAQ scope. No after-hours or derivatives change is inferred.

## Reproduction and fix

Pinned exchange_calendars 4.13.1 returns 09:00–15:30 for this date. At 16:00 KST the prior collector/entry clocks incorrectly accept the 11/19 daily close; it is still trading until 16:30. The unchanged 30-minute reporting buffer requires 17:00 instead.

One repository-local XKRX subclass adds only this date's one-hour open/close offset. Vendor objects and raw data are not mutated. Existing holidays, US short days/DST and earlier CSAT dates remain inherited. All six production calendar construction paths use the same factory, including schedule DataFrame consumers, prediction bounds, entry eligibility, market context, charts and world flow. A future upstream inclusion is not shifted twice.

This patch does not assert general coverage of future emergency holidays. It does not refresh data or improve forecast performance, grant data redistribution rights, change schedules, or publish anything. Existing 11/16 Korean index staleness is independent of this upcoming 11/19 defect. Financial approval-pending code is excluded.

No live provider collection, workflow dispatch, remote push, merge or deployment performed. Review KOSDAQ evidence limitation before operational rollout.

## Offline verification

171 tests passed: special-session boundaries (6), data pipeline, price evidence, forecast model, world flow, universe forecasts, and market context. Regression checks cover 09:59/10:00, 16:29/16:30, 16:59:59/17:00 KST, entry rejection before reporting buffer, daily-bar truncation, schedule/property agreement, adjacent normal days, Christmas/weekend and US short session. An initial central-factory cache retained a mocked US calendar across tests; removed that redundant cache, reran all 171 successfully. Existing per-consumer calendar caches remain unchanged.

Command: `PYTHONPATH=/workspace/shared/radar-calendar-deps:scripts python -m unittest scripts.test_stock_special_sessions scripts.test_stock_data_pipeline scripts.test_stock_price_evidence scripts.test_stock_forecasts scripts.test_stock_world_flow scripts.test_stock_universe_forecasts scripts.test_market_context -q`
