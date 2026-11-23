# New US intraday cohort: all 12 rises missed — 2026-11-23 UTC / 2026-11-24 KST

Research-only diagnosis of newly matured, originally frozen forecasts. No new model recipe or parameter search, no retroactive estimates, no production change or promotion. This cohort has now been examined and must not be reused as an untouched final confirmation.

## Immutable sources and chronology
Pinned main `f23e5971bb19b0622d10f9c908c41b5cf7ec5e4f`, prior `abc86985cdfd844c42f7b99d871e438117fb2f8a`. All five original JSONL streams were downloaded as Git blobs and the previous complete contents compared as exact prefixes: ledger 844→856, outcomes 810→822, learning events 693→705, attempts 4784→4864, deliveries 125→126. All five prefix checks passed.
Current blobs respectively `7aa259e1231eccdf121ebc9e5d93525d5e1a674e`, `02441567a1f5e66fb0d3f7c11ada116138e3ef27`, `2bfc40ee64d167382a26eb7b818c0b0b1f9f2a5a`, `c901fae0c9b5037750223c28b30ca5550ac417a1`, `aab4ec1b46ef255c034ba7a3d6fbb4cc5f41a375`.

- [Issuance run 45248100809](https://github.com/Ohoredingdong/Notion/actions/runs/45248100809): 40 groups, 12 new frozen calls, no new learning; public asset verification passed at 19:24:32.988300 UTC, 10 paper plans later verified before target, zero human receipts. The 12 calls were issued 19:23:33 UTC for 19:50–20:20 UTC (Nov 24 04:50–05:20 KST), US regular session, and all 12 IDs appear in the contemporaneous public receipt record. No actual user receipt.
- [Outcome run 45258747542](https://github.com/Ohoredingdong/Notion/actions/runs/45258747542): 40 groups, 40 no-calls, zero new predictions, 12 new original-policy learning updates at 20:23:59 UTC. Published bundle d6423ed973faa8420bbffa9bf41a5908fcf38967; subsequent public verification failed with the existing generic ValueError. [Recovery 45259406169](https://github.com/Ohoredingdong/Notion/actions/runs/45259406169) declined replay (published_bundle_requires_public_only_recovery); [linked audit 45259406125](https://github.com/Ohoredingdong/Notion/actions/runs/45259406125) skipped. Existing PR #149 diagnoses the generic message; no duplicate repair. A separate [actual independent audit 45259399838](https://github.com/Ohoredingdong/Notion/actions/runs/45259399838) completed stored-price, learning, attempt and acceptance recalculation, 705 eligible, 279 correct, 0/40 sample gates. It does not certify exchange prices or new publication.
- Independent JavaScript joined original IDs and recomputed probability sums/argmax, stored return vs original band, actual/score, Brier and ordering of observation, receipt, issuance, target and evaluation/learning. No mismatches in these checks, no duplicate ledger/outcome/learning IDs. Stored provider prices are not authenticated exchange bars or executable quotes.

## Failure reproduced: all actual up, all incumbent flat
Use only the 12 newly appended learning IDs, original outcomes and already-frozen probabilities for incumbent, original frequency baseline, adaptive, and all 3 directional specialist variants. No fitted model, threshold changes or post-hoc choice. Same 12 outcomes; actual down=0, flat=0, up=12. The entire block represents ONE common 30-minute US market window; it is not 12 independent market regimes.

| Frozen method | Correct/12 | Up calls | Up missed | Down false calls | Flat false calls | Brier |
|---|---:|---:|---:|---:|---:|---:|
| Incumbent | 0 | 0 | 12 | 0 | 12 | 0.9247156660 |
| Training-frequency baseline | 0 | 0 | 12 | 0 | 12 | 0.9930596234 |
| Adaptive | 0 | 0 | 12 | 0 | 12 | 0.9344708732 |
| movement_then_direction | 1 | 1 | 11 | 0 | 11 | 0.8374267806 |
| balanced_linear | 3 | 3 | 9 | 3 | 6 | 0.7410030400 |
| balanced_nonlinear | 4 | 4 | 8 | 5 | 3 | 0.6966234214 |

Up precision is undefined for zero up calls, and 100% on the 1/3/4 respective up calls of the other methods in this exclusively-up cohort. Up recall is respectively 0/12, 0/12, 0/12, 1/12, 3/12, 4/12. Down recall is undefined for every method (no actual down); down precision undefined when no down calls and 0/3 or 0/5 for the balanced candidates. All flat calls are false; flat recall undefined. No bidirectional improvement or candidate selection can follow from this cohort. The nonlinear method also made five wrong down calls. Brier improvement here is not a generalization result. The prior recent-daily trial is a different mode and not retroactively scored here.

| Symbol | Stored return % | Original band % | Incumbent | Movement→direction | Balanced linear | Balanced nonlinear |
|---|---:|---:|---|---|---|---|
| ^GSPC | 0.329308 | 0.15 | flat | up | up | up |
| ^IXIC | 0.371255 | 0.167037 | flat | flat | down | down |
| AAPL | 0.356212 | 0.15 | flat | flat | flat | flat |
| MSFT | 0.680972 | 0.15 | flat | flat | flat | up |
| NVDA | 0.523784 | 0.395640 | flat | flat | flat | flat |
| ON | 0.919947 | 0.278015 | flat | flat | flat | flat |
| FN | 1.051242 | 0.315315 | flat | flat | flat | up |
| DOCS | 0.220603 | 0.180624 | flat | flat | down | down |
| EXLS | 0.724980 | 0.15 | flat | flat | up | up |
| AMZN | 0.539934 | 0.180616 | flat | flat | flat | down |
| TSLA | 0.262852 | 0.204751 | flat | flat | down | down |
| META | 0.302012 | 0.181470 | flat | flat | up | down |

All actual up; baseline and adaptive flat on all 12. Rounded numbers for display; calculation used original full precision. These are newly scored forward outcomes, not a new model hypothesis or a causal proof of why features failed. Same-session common market movement and flat dominance are observed failure modes.

## Cumulative ledger (separate from the candidate's used historical 2,520 and shadow 20)
Original eligible total 279/705 = 39.574468%, previously 279/693. Version 1.0 69/208; 1.1 210/497. Confusion matrix actual rows down/flat/up, predicted columns down/flat/up: [[35,180,51],[30,223,35],[15,115,21]]. Up precision 21/107, recall 21/151, false 86, missed 130; down precision 35/80, recall 35/266, false 45, missed 231; flat correct 223/288 actual, 518 calls. Brier 0.6575671260; balanced accuracy 0.3483191169. Same frozen baseline comparison: 275/693 model versus 282/693 baseline, no advantage. Attempts 1,895 provided and 2,969 no-calls out of 4,864, 38.9597%; not market-opportunity coverage. Original 34 unmatched ledger IDs: 22 matured, 12 pending as of 20:31 UTC; authoritative eligible census separately has 20 missing, 21 duplicate issuances, 22 overlaps, 76 untimely-public, 12 pending. All 705 eligible scores and previous original errors retained.

## Disposition
No new hypothesis or tuning trial (0); one prior recent daily recipe remains rejected, its 2,520 historical rows and already evaluated 20 shadows not reusable for confirmation. This newly observed block is insufficient for bidirectional inference and is now a used diagnostic cohort. The existing bounded adaptive learning updated exactly 12 eligible rows under the existing policy (not an independently demonstrated improvement). No additional code change justified by this already-covered flat-dominance failure, no promotion, no re-execution of published transaction. Future targets must be frozen before observing outcomes and remain separate from this diagnosis. Paper audit has 475 registered plans, 437 timely public, 38 late checks, no actual user receipt or observed execution quotes, missing cost/evidence sources; no actual after-cost utility. Keep strict-green, real-order prohibition, original records, existing monitors and policies. No notification criteria met; timing_utility=not_proven.


## Follow-up cutoff 2026-11-23 23:23:56 UTC (Nov 24 08:23:56 KST)

Read-only follow-up pinned main `ef5a6eb63c6ca4db8f1ca9c92557bd6a7e7ec238`. Comparison to the earlier pinned main `f23e5971bb19b0622d10f9c908c41b5cf7ec5e4f`: 10 commits; none modified the five original forecast/learning/attempt/delivery streams, direction model or bounded-autopilot state. The five exact source blob identities listed above are unchanged. Independent JavaScript rejoined all 856 predictions / 822 results / 705 eligible learning rows, checked original probabilities, direction, bands, return/Brier arithmetic, chronology and pre-target public receipt; zero detected mismatches and zero duplicate IDs in those three streams. Confusion, version totals, 279/705 correct, 1895/4864 provided and Brier 0.6575671260426619 are unchanged, not a new performance result. No verified human receipt.

New time boundary: the 12 US regular-session daily targets (Nov 23 14:30–21:00 UTC) have ended as of this cutoff. No post-target source collection or stored results for them were available in the pinned snapshot: the last forecast cycle observed US daily data only through Nov 20 and ran at Nov 23 20:24 UTC, before the target ended. Thus 34 raw ledger IDs have ended without outcomes (14 KR intraday IDs, 8 KR daily IDs, 12 US daily IDs); none remain future by wall-clock at this cutoff. This is **not** evidence of a new collector defect or 12 additional errors. Keep distinct from the earlier independent census (20 missing, 12 pending, 21 reissues, 22 overlaps, 76 untimely-public, 705 scored at that earlier snapshot). No retroactive records or forced replay of a published transaction.

Latest visible actual [accuracy audit 45260560435](https://github.com/Ohoredingdong/Notion/actions/runs/45260560435) completed its source-aligned calculation and public verification steps; pinned accuracy JSON says data_integrity.check_passed=true and errors=[], with promotion_evidence_sufficient=false and investment_use_approved=false. This does not establish the earlier forecast bundle's timely public proof, a permanent repair of the earlier identity mismatch, or predictive edge. [Health monitor 45260788019](https://github.com/Ohoredingdong/Notion/actions/runs/45260788019) still failed on stale financial/price sources and no valid US extended daily prediction. Last visible prospective, independent audit and bounded recovery runs remain 45258747542, 45259399838 and 45259406169 as documented above; no newer actual forecast collection was visible. Do not interpret recovery's successful job status as a successful replay (retry=false). No new independent root cause established; existing #149/#150/#172 drafts retained. New model hypothesis trials=0, tuning=0, operating changes=0. All prior used cohorts remain used. Timing utility still not proven; no completion criteria met.
