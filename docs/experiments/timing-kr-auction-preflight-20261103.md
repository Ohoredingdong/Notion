# KR closing-auction 5-minute grid target preflight — bounded research (2026-11-03)

Status: preregistered engineering hypothesis, **not** evidence of predictive usefulness and **not** a changed trading or promotion criterion.

## Frozen provenance and constraints
- Pinned main before inspection: `24c59607be5a47b046fb8090a945dac74be71bd5` (2026-11-02 17:35:19 UTC). Preserved three approved timing/direction/bounded-autopilot contracts, blob SHAs `69526101025c0394b13a55bfb73b9be5240e5fca`, `6d5498666cd6da4d4528c46a4f1cb911715e90bd`, `a5176f6aa075c49a090e6a3ec01b64fb323420ed`.
- Before change: `scripts/stock_forecast_model.py` `future_target` accepts an intraday target if its end is at or before the **session close**, but `scripts/run_stock_forecasts.py` `complete_target` requires six *consecutive independently sourced five-minute bars* in the target; it refuses to synthesize or fill absent prices.
- Original frozen research forecasts, errors, public timestamps, source snapshots, approved criteria and original strict-green-1.0 controls must remain byte-for-byte unchanged. Existing separate investment radar data monitor must not be changed. No orders, auth, paid feed acquisition, NXT/KRX session mixing or manual price creation.

## External market-structure evidence (venue-specific)
- KRX's official market rules distinguish **continuous trading 09:00–15:20** from **closing call auction 15:20–15:30** for KRX-listed equities: https://regulation.krx.co.kr/contents/RGL/03/03020407/RGL03020407.jsp ; https://global.krx.co.kr/contents/GLB/06/0602/0602020204/GLB0602020204T7.jsp
- This source confirms trading-phase *semantics*, **not** individual raw five-minute vendor bars, order book, exact ticker executions, Yahoo latency or a cross-venue consolidated price.
- A closing auction may produce a final execution at 15:30, but does **not** establish separately executable regular continuous-trade bars for 15:20–15:25 and 15:25–15:30. The six-bar intraday target's semantics must not silently change to a closing-auction price or carried-forward bars.

## Preregistered hypothesis and falsifiable RED/GREEN test
**Hypothesis:** A KR 30-minute regular continuous-trading target scheduled to end at the **15:30 closing auction** is permitted by the current target preflight, even though its last two five-minute intervals cross the closing auction and therefore cannot be scored as six continuous executions. This creates predictable missing-outcome/coverage censoring. It does **not** explain the earlier 2026-10-30 14:45–15:15 KST missing targets, which appear related to incomplete vendor history and require separate independent-source research.

**One small candidate fix for research-only testing:** For `market == "KR"` and `mode == "intraday"` only, reject targets whose `target.end > session_close - 10 minutes`, preserving the existing `insufficient_regular_session_time` no-call reason. Do **not** change: US final 30-minute windows, KR targets ending at 15:20 or earlier, regular session calendar, the six-future-bar scoring rule, frozen target definitions, 120/20 performance gate or any other market.

**Fixed negative/positive controls** (synthetic calendar times only, no fake prices):
1. KR 2026-11-02 15:00–15:30 target: current code should yield target (RED failure). New code must return no-call `insufficient_regular_session_time`.
2. KR 2026-11-02 14:50–15:20 target: must remain a valid future target.
3. US 2026-11-02 15:30–16:00 New York time: US close-aligned target must remain valid.
4. Historical outputs never rescored/revised; any new rejection only affects *future* forecast issuance and remains in no-call coverage accounting.

## Bounded trial and stop policy
One RED run and at most one minimal-code GREEN attempt, both on `research/timing-kr-auction-preflight-20261103` only, with regression tests, independent forecast audit and acceptance guard in a separate read-only CI workflow. Failed tests are **recorded**, not bypassed. No production/main merge until comprehensive regression, independent audit, UI/public deployment and separately documented approvals pass. The safety objective is to avoid **unscorable** forward forecasts, not claim a higher precision, lower Brier or cost-after execution edge. Vendor five-minute source still lacks independent official raw comparison; nothing here establishes real-time prices, user receipt or investment timing utility.

## Observed cohort fixed before this experiment
At pinned main: 107 original forecasts, 86 unique events, 21 duplicated issues, 8 overlaps excluded, 78 non-overlapping; 54 externally *unverified* scored Yahoo-based results / 14 correct (25.93%), Brier 0.6786795164555174; 12 matured KR intraday missing, 12 future-pending. Among missing: six 2026-10-30 14:45–15:15 KST (do not attribute to closing auction), six 2026-11-02 15:00–15:30 KST (auction-spanning). These counts are **historical unchanged** and cannot be used for model selection. Exact source blob hashes and job refs in PR #82.

## Experiment results
Pending RED CI; then at most one constrained GREEN rerun. If source/permissions/tests block verification, leave **unmerged** with an explicit unresolved finding.
