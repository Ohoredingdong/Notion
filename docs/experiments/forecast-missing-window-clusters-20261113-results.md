# Research results — exact-window missing-outcome census, Nov 13 2026

Status: **research-only engineering pass, production unchanged, timing usefulness NOT proven**.
Prerecorded before code: [forecast-missing-window-clusters-20261113.md](forecast-missing-window-clusters-20261113.md). Original main pinned `f5164c80f20d8c90d9d9367f506ad58f67e242c3` at 2026-11-13 ~18:12 KST, original ledger blob `73ea036876aa316a1a06b0d1ce09a07223dbe1d2`, outcome blob `b8c4408ef1ed24c94f99efefaf947e92b02416b7`, delivery blob `ae9066dbb801b304f252db7077d8380ac24e5309`. New provider collection at 2026-11-13 08:43 UTC originated from Stock Prospective Forecasts [43395223407](https://github.com/Ohoredingdong/Notion/actions/runs/43395223407); later independent operating audit [43395663074](https://github.com/Ohoredingdong/Notion/actions/runs/43395663074) completed. All stored price calculations are Yahoo-derived, **not** exchange-certified raw five-minute candles or actionable bids/asks.

## Fresh matured 16 operating targets, never reissued or edited

The full 2026-11-13 KR daily cohort (00:00–06:30 UTC) comprised 8 original calls, 4 correct; actual down 5, flat 3, up 0, down hits 1/5. The full KR intraday cohort (04:55–05:25 UTC) comprised 8 original calls, 1 correct; actual down 8, flat 0, up 0, down hits 1/8. Hence **5/16 = 31.25% correct**, actual down 13, up 0, flat 3; down calls 2 / true 2 / false 0 / missed 11 (precision 2/2, recall 2/13). Up calls 2 / true 0 / false 2 (precision 0/2; recall **null** because no actual up). The cohort is one market day with correlated symbols; **not** proof that down direction is now 100% precise in future. Recent down errors include SK Hynix (daily flat predicted against -5.882%), Samsung Electronics (daily flat against -3.738%), KOSPI (daily flat against -2.969%), and SK Hynix/KOSPI (intraday predicted up against material down). A permanently frozen neutral band determines labels: do not relabel provider returns by a retroactively chosen zero threshold.

Using only probabilities frozen **before** each identical future target, a separate JavaScript arithmetic oracle produced:
| Frozen method | Correct / 16 | Down hit / 13 | Up false calls | Three-class Brier |
|---|---:|---:|---:|---:|
| operating incumbent | 5 | 2 | 2 | 0.736535 |
| original frequency baseline | 4 | 2 | 0 | 0.717155 |
| movement_then_direction | 6 | 3 | 1 | 0.712428 |
| balanced_linear | 8 | 5 | 4 | 0.663259 |
| balanced_nonlinear | 5 | 3 | 7 | 0.618272 |
| adaptive (previously frozen) | 5 | 2 | 2 | 0.720613 |

These frozen comparisons explain a **real downward-movement miss pattern**, not model-selection approval. No actual upward event occurred in this new cohort; selecting a candidate from its down-only performance would violate the both-direction and untouched-period gates. This cohort, and prior 2,520 historical evaluation targets and 20 shadow records, are **already examined**, not unused final holdouts.

## Independently rejoined complete original record (no selective reset)

515 original forecast records, 481 stored outcomes and 404 eligible scored, 166 correct (41.0891%), model-version disjoint cohort 1.0 = 69/208 and 1.1 = 97/196 (different periods; NOT matched-model improvements). All 481 stored outcomes independently checked against each original frozen probability/band and stored open/close: **0 internal arithmetic/label/Brier mismatches**, and observed/received/issued/target/source-check time ordering showed **0 errors** in inspected records.

Actual down **142**, calls **46**, hits **18**, missed **124**, false calls **28**, precision **18/46 (39.13%)**, recall **18/142 (12.68%)**. Actual up **97**, calls **70**, hits **19**, missed **78**, false calls **51**, precision **19/70 (27.14%)**, recall **19/97 (19.59%)**. Flat 129/165 captured with 288 flat calls. Baseline Brier and all old wrong decisions retained; group minimum accepted **0/40**.

Independent disjoint accounting: **21** later reissues, **22** overlapping, **36** non-timely-public, **12** matured missing, **20** future pending = 515 original. Last scheduler has 40 attempt records, 20 research_prediction but only **8 new immutable IDs** (other 12 reference previous daily predictions), 20 no_call due insufficient regular-session time. Overall archived research attempts **1,267**, no-call **1,877**, total **3,144**. Neither ratio is market-wide coverage; public verification is not personal recipient delivery.

## Newly reproducible data-evidence defect and restricted fix

All 12 currently **missing despite a later provider snapshot** belong to the same six KR intraday symbols `000660.KS`, `005930.KS`, `035420.KS`, `403870.KQ`, `^KS11`, `^KQ11` in exactly two 30-minute target time windows:
- 2026-10-30 **05:45–06:15 UTC** / 14:45–15:15 KST: 6 missing
- 2026-11-02 **06:00–06:30 UTC** / 15:00–15:30 KST: 6 missing

Operational `run_stock_forecasts.py::complete_target` requires **six** consecutive 5-minute bars of one regular-session identity and rejects incomplete target coverage. The precise missing candle(s) and upstream cause cannot be reproduced **without archived exact-source/independent official raw five-minute bars**; do not claim missing labels, exchange outages, auction cause or source correction. The known direct-scorer middle-bar guard lives in separate held-open PR [#110](https://github.com/Ohoredingdong/Notion/pull/110), which this change does not copy.

We implemented an additive read-only census field `missing_target_windows` including normalized exact UTC time windows, explicit venue-or-unverified, forecast IDs, symbols, counts and original missing-context distribution; root cause remains `unverified` and exchange bars `false`. Existing numerators, denominators, eligibility and source identity remain unchanged. The true future followup will be **new unobserved forward events after Nov 16**, if any, not tuning the previous two known windows.

## Engineering independent verification, scope and decisions

- Three new synthetic tests for offset aliases, venue isolation, unobserved/pending/reissue separation, plus original immutability and missing-context controls all passed.
- Actual [Forecast Postvalidation Source Binding #43400720810](https://github.com/Ohoredingdong/Notion/actions/runs/43400720810) passed 41 combined target/source/census tests, 19 independent-auditor tests, 17 learning-evidence tests and 9 acceptance negative controls. Real original data re-audited **404/166, 12 missing**, source-binding preserved, **79 original tracked stock evidence files byte-identical**, `TIMING_USEFULNESS not_proven`.
- Separate [Independent Forecast Evidence Audit #43400720725](https://github.com/Ohoredingdong/Notion/actions/runs/43400720725) passed and returned same source-bound scoring / new sampling gate **0/40**. Unrelated full-universe AI contracts [#43400720632](https://github.com/Ohoredingdong/Notion/actions/runs/43400720632) also passed; none proves profit or causality.
- PR [#150](https://github.com/Ohoredingdong/Notion/pull/150) remains **DRAFT/HOLD**. We did not merge or release into main. Source issuer's `research_cycle_verified` is a working pipeline status, not a verified timing edge.

**Experiment budget:** new model recipes **0**, tuned parameter candidates **0**, engineering hypotheses **one** (missing-window grouping), new synthetic controls **three**, actual original-row overwrites **0**, original wrong outcomes deleted **0**, research branch code amendments **one**; any completed market-session forecasts are only counted after actual later provider observation. No changes to strict-green-1.0, original policy, source collector, old model, stock data accuracy monitor, order permissions, authentication, other schedules or user notification. Real human signal receipt, raw official venue bars, executable prices, trade-cost and untouched independent followup remain absent. Final `timing_utility=not_proven`.
