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


## Follow-up cutoff 2026-11-24 03:24:33 UTC (12:24:33 KST)

Pinned main `fdcc609274d964f2f9d04acd4aab9e69b90a1ea1`. Compared with `ef5a6eb63c6ca4db8f1ca9c92557bd6a7e7ec238`: 11 commits; original forecast, outcome, delivery, learning and attempt streams and model/controller unchanged. Direct independent JavaScript recomputation from their original Git blobs (ledger `7aa259e1231eccdf121ebc9e5d93525d5e1a674e`, outcomes `02441567a1f5e66fb0d3f7c11ada116138e3ef27`, deliveries `aab4ec1b46ef255c034ba7a3d6fbb4cc5f41a375`, learning events `2bfc40ee64d167382a26eb7b818c0b1f9f2a5a`, attempts `c901fae0c9b5037750223c28b30ca5550ac417a1`): 856/822/126/705/4864 rows respectively. Checks of unique IDs, probability sum and max direction, observed/received/issued/target chronology, stored-price return and fixed-band labels, Brier, pre-target public evidence, learning joins and overlaps among eligible targets found zero mismatches. Confusion rows actual down/flat/up, columns predicted down/flat/up: [35,180,51], [30,223,35], [15,115,21]. 279/705 correct, Brier 0.6575671260426619; version totals 69/208 and 210/497. 1895 provided, 2969 no-call. 34 matured unmatched raw IDs as before, not new failures or new learning. No human receipt flags true. Not external price verification.

New operational evidence: [health run 45311601154](https://github.com/Ohoredingdong/Notion/actions/runs/45311601154), job 138168411232, actually published error state at 02:20:35 UTC: forecast stale 5.9h (2h limit), finance stale 70.4h (48h limit), opportunity 104/104, charts 108/108 and market 4/4 stale source-session checks. Latest visible repository Actions listing through 02:20 UTC includes no subsequent Stock Prospective Forecasts run after 45258747542 (20:22 UTC prior date); current workflow config has 7,17,27,37,47,57 minutes in UTC hours 0–7 weekdays and explicitly describes cron delay/drop. This shows an observed scheduling/collection gap during the configured KR window, not a proven scheduler root cause or exchange data failure. No assumption that cron ran, no fabricated predictions at missed starts. [Decision UI run 45304356545](https://github.com/Ohoredingdong/Notion/actions/runs/45304356545) rejected stale strict-review evidence, not grounds to loosen freshness gates. Existing monitor owns these warnings.

Fetched original prospective job 137987450429 log: public verification failed with public_deployment_unverified: ValueError. Independent audit job 137989767742 explicitly reports 705 eligible rows, 0 groups meeting sample gate, no integrity errors, and required receipt/quote/cost/untouched follow-up missing. Recovery job 137989790345 explicitly says retry=false, reason=published_bundle_requires_public_only_recovery; no automatic re-execution. Existing #149 diagnostics and #150 missing-window research remain applicable. #172 remains draft. No new reproducible model defect or independent future outcome, no evidence of a newly failed source request, no new hypothesis or tuning, no production modification or unsafe replay. Original policies and all previous cohorts preserved; timing_utility=not_proven. The last visible Actions listing is not proof of absence after its own newest timestamp.


## New daily cohort — cutoff 2026-11-24 05:27 UTC (14:27 KST)

Pinned main `e20aa853d3402cf51d490aaefc3c72d0155420ec`; prior `fdcc609274d964f2f9d04acd4aab9e69b90a1ea1`. 23 intervening commits; forecast changes consist of data publication/learning evidence, no model or controller source code change. PR #146's actual patch binds input row fingerprints and prevents derived-output aliases/overwrites. PR #147 remains held; both preregistration/results and prior shadow replay were read again. Artifact 13750188846 is not expired (expires 2026-12-10 09:25:39 UTC; digest matches prior record), but its 20 predictions were already evaluated in the prior replay, not new independent evidence. Historical 2,520 targets remain used. No repeated model selection on either cohort.

Direct Git blob retrieval independently compared exact old prefixes in all five original streams (all true). Counts ledger 856→884, outcomes 822→842, learning 705→725, attempts 4864→4944, deliveries 126→128. New blob SHAs in that order: `c4d1bef316fba10b907493f48497624e6372f45e`, `1fca7de7e3971106086ea1b5ecdad262ec559a5d`, `2a076ed7242c0db255a4c2ab3898ac4e713f55c5`, `1140f0fa1d83c5281a2e23a5ad437e2beee3c53b`, `f927d899e0a869ff361aa052331369fafa5e8cdc`. Separate JS recalculation of original probabilities/argmax, original band, actual stored return, Brier, receipt/issue/target/evaluation/learning chronology, duplicate IDs, pre-target public proof, and within-group eligible overlap yielded no detected errors; not independent exchange authentication. No true human receipt flag. The twenty newly learned original daily rows are exactly the previously pending KR 8 and US 12, with outcomes available at 04:21:15 UTC. All original labels and errors preserved.

### Actual observed operational recovery, not scheduler repair

[Run 45325614694](https://github.com/Ohoredingdong/Notion/actions/runs/45325614694), job 138214380512, actually collected 40 groups, froze 20 predictions and learned 20 new eligible outcomes; public verification and 16 timely paper plan proofs passed. [Run 45329920400](https://github.com/Ohoredingdong/Notion/actions/runs/45329920400), job 138228392421, collected 40 groups, froze 8 predictions, learned zero, public verification and 6 additional timely paper-plan checks passed. The preceding collection gap ended in observed successful runs; no scheduler root cause established, no backfilled issuance. [Independent audit 45330370248](https://github.com/Ohoredingdong/Notion/actions/runs/45330370248), job 138229859991, independently recomputed 725 scored/288 correct, 0/40 minimum sample gates, no integrity errors; attempt coverage consistent. [Bounded recovery 45330370137](https://github.com/Ohoredingdong/Notion/actions/runs/45330370137) skipped its recovery job, as expected after success (no replay; skipped job log unavailable). [Health 45330451536](https://github.com/Ohoredingdong/Notion/actions/runs/45330451536) published failure for financial age 73.1h versus 48h and stale completed source sessions opportunity 104/104, charts 108/108, market 4/4. Forecast freshness at that check was restored; broader readiness not restored. Existing diagnostics #149/#150/#172 not duplicated.

### New failure reproduction: 20 originally frozen daily forecasts, no fitting

Targets are Nov 23 KR 00:00–06:30 UTC and US 14:30–21:00 UTC; market/mode kept separate. Actual down 4, flat 13, up 3, only two market-session clusters. Compare only original frozen vectors on exactly these twenty outcomes, no candidate fitting, no adjusted band, no new candidate selection. A 0 denominator means undefined, not 0% or 100%.

| Method | KR correct / 8 | US correct / 12 | Pooled correct / 20 | Up precision; recall | Down precision; recall | Brier ↓ |
|---|---:|---:|---:|---|---|---:|
| incumbent | 5 | 4 | 9 | 2/6; 2/3 | 1/7; 1/4 | 0.6916516826 |
| baseline | 6 | 5 | 11 | 1/5; 1/3 | 2/4; 2/4 | 0.6282879529 |
| adaptive | 5 | 3 | 8 | 1/1; 1/3 | 2/11; 2/4 | 0.7426227909 |
| movement_then_direction | 6 | 5 | 11 | 0/1; 0/3 | 0/1; 0/4 | 0.6301162401 |
| balanced_linear | 5 | 3 | 8 | 1/5; 1/3 | 1/7; 1/4 | 0.6910081250 |
| balanced_nonlinear | 3 | 5 | 8 | 0/4; 0/3 | 1/9; 1/4 | 0.6658600480 |

The incumbent missed all two KR down targets and had no KR up examples; in US it missed one of three up and one of two down. The apparent 11/20 baseline/cascade advantage is not bidirectional improvement: cascade makes one false down call and one false up call, capturing neither direction; baseline misses two of three rises. The prior intraday failure is different mode, not pooled to justify promotion. Individual wrong signals preserved below (all six methods use original probabilities; rounded numbers are display only).

| Market | Symbol | Actual | Return % | Frozen band % | incumbent | baseline | adaptive | movement_then_direction | balanced_linear | balanced_nonlinear |
|---|---|---|---:|---:|---|---|---|---|---|---|
| KR | ^KS11 | flat | -0.556714 | 1.174866 | flat | flat | flat | flat | flat | flat |
| KR | ^KQ11 | flat | 0.081902 | 1.219369 | flat | flat | flat | flat | flat | down |
| KR | 005930.KS | flat | -0.056306 | 1.482193 | flat | flat | flat | flat | flat | down |
| KR | 000660.KS | flat | 0.556070 | 1.997773 | flat | flat | flat | flat | flat | flat |
| KR | 035420.KS | down | -4.153355 | 1.114445 | up | flat | flat | flat | up | up |
| KR | 403870.KQ | flat | 0.949796 | 2.270269 | flat | down | flat | flat | flat | flat |
| KR | 207940.KS | down | -3.012048 | 1.048951 | flat | down | flat | flat | flat | up |
| KR | 005380.KS | flat | 0.609756 | 0.876970 | down | flat | down | flat | down | up |
| US | ^GSPC | flat | 0.135038 | 0.563976 | down | flat | down | down | down | down |
| US | ^IXIC | flat | -0.742437 | 0.744511 | down | up | down | flat | down | flat |
| US | AAPL | flat | 0.347829 | 0.608549 | down | up | down | flat | down | down |
| US | MSFT | down | -2.679524 | 0.827577 | up | flat | down | flat | up | up |
| US | NVDA | flat | -1.191326 | 1.413157 | up | up | down | up | up | flat |
| US | ON | flat | 0.375827 | 1.643205 | up | up | down | flat | up | down |
| US | FN | flat | -0.399349 | 2.665983 | flat | flat | down | flat | flat | flat |
| US | DOCS | flat | 0.303843 | 0.907471 | down | flat | down | flat | down | flat |
| US | EXLS | up | 3.657364 | 0.533989 | down | up | down | flat | down | down |
| US | AMZN | down | -1.871210 | 0.946599 | down | down | down | flat | down | down |
| US | TSLA | up | 2.860650 | 1.375665 | up | down | flat | flat | flat | down |
| US | META | up | 0.993714 | 0.870411 | up | flat | up | flat | up | down |

### Original operating history and remaining evidence

Cumulative original eligible confusion rows actual down/flat/up vs predicted down/flat/up = [[36,181,53],[35,229,37],[16,115,23]]. 288/725 = 39.7241%, wrong 437, Brier 0.6585073896719839. Up 23/113 precision, 23/154 recall, false 90, missed 131; down 36/87 precision, 36/270 recall, false 51, missed 234; flat correct 229/301 actual, 525 calls. Version 1.0 69/208, version 1.1 219/517. Provided 1935 / 4944 attempts (39.1383%), held 3009; actual market opportunity coverage unverified. Same frozen baseline cohort 713: operating 284, baseline 293, no asserted edge from this comparison. Independent audit census at 05:01 UTC: 725 scored, 21 later reissues, 22 overlaps excluded, 12 outcome missing at snapshot, 76 untimely public, 28 future target at that snapshot; raw unmatched 42 IDs at 05:27 UTC, split {"KR intraday ended":22,"US daily future":12,"KR intraday future":8}. Newly matured intraday targets without a later source collection are awaiting evidence, not new errors. New issuance windows and actual first verification:

- 45325614694 / US / daily / 2026-11-24T14:30:00+00:00 / 2026-11-24T21:00:00+00:00: {"n":12,"timely":12,"earliest":"2026-11-24T04:21:16.079011+00:00","latest":"2026-11-24T04:21:16.087910+00:00","firstPublic":"2026-11-24T04:22:23.232753+00:00"}
- 45325614694 / KR / intraday / 2026-11-24T04:35:00+00:00 / 2026-11-24T05:05:00+00:00: {"n":8,"timely":8,"earliest":"2026-11-24T04:21:16.077731+00:00","latest":"2026-11-24T04:21:16.089094+00:00","firstPublic":"2026-11-24T04:22:23.232753+00:00"}
- 45329920400 / KR / intraday / 2026-11-24T05:10:00+00:00 / 2026-11-24T05:40:00+00:00: {"n":8,"timely":8,"earliest":"2026-11-24T04:59:22.326566+00:00","latest":"2026-11-24T04:59:22.334061+00:00","firstPublic":"2026-11-24T05:00:24.225864+00:00"}

No human receipt or executable quote, paper cost schedule or independent untouched follow-up. The independently audited paper evidence still has no after-cost validated edge. No new hypothesis trial, no refit by this assistant (existing adaptive update 20 is not a new experiment), no operational code change, no promotion. This cohort is now used as a diagnostic, not an untouched confirmation. Preserve all source/policy/strict-green/monitoring/order protections. No completion criteria met; timing_utility=not_proven.


## New Korean intraday cohort — run 45345340838 (2026-11-24 07:11:59 UTC / 16:11:59 KST cutoff)

Pinned main `16a968e9fb55738fa2351730255bc8e227f483bd`; comparison to `e20aa853d3402cf51d490aaefc3c72d0155420ec` shows 34 commits, no model/controller code change. Reviewed actual acceptance/specialist/bounded policies, PR #146 source-binding and protection patch, PR #147 and its original preregistration/results/20-shadow replay, #149/#150/#172 existing diagnostics. The 2,520 historical targets and prior 20 shadow targets are already used, not a new confirmation. No new candidate fit or model recipe this run.

Git blob read and independent JavaScript recalculation (separate from production scorer): ledger 884→892, outcomes 842→858, learning events 725→741, attempts 4944→4984, deliveries 128→129. Exact previous bytes are prefixes in all five streams. New original blob SHAs respectively: `e8440bb49cfcabfe08b25ee46ad6ca4cd2380e9d`, `895c55729177a727a2ff066966251d0fc302b057`, `6d871ca30a327764091567c001eb39aba89f46e9`, `7ecc25dac77714a666636427021d1d7e0bcc5063`, `6a680a916955c077cc00e2178a351416cf3776d7`. Recomputed all 858 observed returns from stored open/close and frozen band; checked frozen vectors/argmax, Brier, observed/received/issued/target/evaluated/learned chronology, duplicate IDs, pre-target public proof for 741 learning events and within-symbol/mode overlaps among learned rows. Zero detected inconsistencies in these checks. No externally authenticated raw exchange prices, venue-level KRX/NXT confirmation or human receipt.

[Actual prospective run 45345340838](https://github.com/Ohoredingdong/Notion/actions/runs/45345340838), job 138278416192: 40 groups collected, 8 newly frozen daily KR predictions and 16 new learning updates, 0 promotions/rollbacks. The independent audit [45345803709](https://github.com/Ohoredingdong/Notion/actions/runs/45345803709), job 138279933621, completed actual arithmetic, census, learning and attempt reconciliation: 741/296 scored/correct (i.e. 296 correct out of 741), 0/40 sample-gate groups, no integrity errors. Bounded recovery [45345803673](https://github.com/Ohoredingdong/Notion/actions/runs/45345803673) job skipped, as expected after success; no rerun or recovery success claim. The actual public forecast/code check succeeded 07:08:32.748565 UTC, six paper plan proofs observed before target at 07:09:09 UTC; zero human receipts. Eight new KR daily rows target Nov 25 00:00–06:30 UTC, issued 07:07:17 UTC Nov 24; all have pre-target public proof and none have matured. No source cooldowns in latest state. Paper status: 497 registered plans, 487 missing execution evidence, 10 awaiting, no external quote/human receipt adapters.

### New result diagnostic — two distinct 30-minute target windows, same eight Korean symbols

Nov 24 04:35–05:05 and 05:10–05:40 UTC; all 16 were previously frozen with timely public proof. Actual down 2, flat 9, up 5; both windows share the same market/day, not 16 independent market regimes. No changes to frozen probabilities, target definitions or bands. No new parameters fit. All six methods compared from originally saved vectors, including the baseline and cascade; denominators of zero are undefined.

| Method | First window correct/8 | Second window correct/8 | Total correct/16 | Up precision; recall | Down precision; recall | Brier ↓ |
|---|---:|---:|---:|---|---|---:|
| incumbent | 6 | 2 | 8 | 0/0; 0/5 | 0/1; 0/2 | 0.6436531222 |
| baseline | 6 | 3 | 9 | 0/0; 0/5 | 0/0; 0/2 | 0.6452768849 |
| adaptive | 6 | 2 | 8 | 0/0; 0/5 | 0/1; 0/2 | 0.6478750645 |
| movement_then_direction | 5 | 4 | 9 | 1/2; 1/5 | 0/0; 0/2 | 0.6466015312 |
| balanced_linear | 3 | 2 | 5 | 2/5; 2/5 | 0/8; 0/2 | 0.6644667605 |
| balanced_nonlinear | 1 | 2 | 3 | 1/5; 1/5 | 2/11; 2/2 | 0.6921067660 |

Failure reproduced: incumbent 15 flat calls, one false down, zero up; misses all seven material moves; adaptive exactly matches the incumbent's class decisions. Cascade captures one rise but no falls; nonlinear catches both falls but issues nine false falls, four false rises, and no flat calls, worsening Brier and overall results. This is an observable class-decision imbalance, not proof of the underlying causal feature defect. No direction thresholds changed. The two narrow flat results (first-window ^KQ11 +0.147063% vs band 0.15%, second-window 005930.KS +0.208442% vs band 0.209567%) retain their original classifications; neither is relabelled. No candidate passes the bilateral gates. The new observed cohort is now used as a diagnostic, not untouched follow-up.

| UTC start | Symbol | Return % | Band % | Actual | incumbent | baseline | adaptive | cascade | linear | nonlinear |
|---|---|---:|---:|---|---|---|---|---|---|---|
|04:35|^KQ11|0.147063|0.150000|flat|flat|flat|flat|flat|down|up|
|04:35|^KS11|0.026769|0.201743|flat|flat|flat|flat|flat|flat|down|
|04:35|005930.KS|-0.104112|0.284881|flat|flat|flat|flat|flat|flat|up|
|04:35|000660.KS|-0.169062|0.336216|flat|flat|flat|flat|flat|flat|down|
|04:35|035420.KS|0.255428|0.150000|up|flat|flat|flat|flat|down|down|
|04:35|403870.KQ|0.000000|0.348376|flat|flat|flat|flat|flat|down|down|
|04:35|207940.KS|-0.614439|0.150000|down|flat|flat|flat|flat|up|down|
|04:35|005380.KS|0.000000|0.333276|flat|flat|flat|flat|up|up|up|
|05:10|^KS11|0.180109|0.174149|up|flat|flat|flat|flat|down|down|
|05:10|^KQ11|0.204930|0.150000|up|flat|flat|flat|flat|up|down|
|05:10|005930.KS|0.208442|0.209567|flat|flat|flat|flat|flat|down|up|
|05:10|000660.KS|-0.084746|0.264660|flat|down|flat|down|flat|down|down|
|05:10|035420.KS|-0.063613|0.150000|flat|flat|flat|flat|flat|down|down|
|05:10|403870.KQ|0.480192|0.319311|up|flat|flat|flat|flat|down|up|
|05:10|207940.KS|-0.616333|0.159658|down|flat|flat|flat|flat|up|down|
|05:10|005380.KS|0.723327|0.345677|up|flat|flat|flat|up|up|down|

Cumulative eligible history 296/741 (39.9460%), 445 wrong, Brier 0.658186649754159; confusion (actual down/flat/up vs predicted down/flat/up) [[36,183,53],[36,237,37],[16,120,23]]. Up precision 23/113 (20.35%), recall 23/159 (14.47%), false 90, missed 136. Down precision 36/88 (40.91%), recall 36/272 (13.24%), false 52, missed 236. Flat 237/310 actual captured, 540 calls. Version 1.0 69/208, 1.1 227/533. Baseline paired cohort 729: incumbent 292, baseline 302. Raw attempt provision 1955/4984 = 39.2255%, held 3029; coverage is not full market-opportunity coverage. Census: 21 reissues, 22 overlaps excluded, 12 missing despite later source, 76 untimely public, 20 pending. Raw unmatched IDs 34 = 14 matured KR intraday, 12 future US daily, 8 future KR daily; not interchangeable with deduplicated census counts. No newly established source/validation bug separate from existing diagnostics. No new hypothesis experiment, refit by assistant, production code changes, promotion or policy change. Existing actual bounded update 16 is not a new model experiment. Prior research and failure records preserved; no independent quote/cost/risk/receipt evidence or untouched follow-up, no completion claim. timing_utility=not_proven.


## US opening collection gap — health run 45415824465 (2026-11-24 14:56:58 UTC cutoff)

Pinned main `366703ba9ab0bc777068ab4423cd44580b6f9e2c`; 21 commits since `e82e18986529c5dfe588302e3ef818e85880ff29`, none changes the prospective model or the five original evidence streams. The original ledger/outcomes/learning/attempts/delivery blob SHAs are identical to the preceding cohort entry. Latest visible main Actions listing (100 entries, spanning 06:56–14:44 UTC) contains no later Stock Prospective Forecasts run than [45345340838](https://github.com/Ohoredingdong/Notion/actions/runs/45345340838). The existing cron covers 13–22 UTC at minutes 7,17,27,37,47,57 on weekdays. [Health 45415824465](https://github.com/Ohoredingdong/Notion/actions/runs/45415824465), job 138521601621, reported the prospective forecast snapshot age 7.5h (2h limit) during the US regular session; this is a new session of the already observed collection-gap symptom, not a proven independent root cause. No observed new forecast execution or source response after the earlier successful run in the available listing; a scheduled opportunity is not an actual run. Do not fabricate missed signals or presume source/scheduler fault. [Accuracy audit 45417557749](https://github.com/Ohoredingdong/Notion/actions/runs/45417557749), job 138527848094, again blocked publication at catalog_forecast_identity_set_mismatch; no weakening or duplication of #172. The existing health monitor owns these warnings.

Independent JavaScript read of all five immutable Git blobs reconfirmed 892 forecasts, 858 outcomes, 741 eligible learning events, 4,984 attempts, 129 public-proof rows. Zero detectable discrepancies in probability vectors/argmax, frozen-band returns, Brier loss, chronology, duplicate IDs, learned-public proof and overlap. Same 296/741 correct, 445 wrong; up precision 23/113 and recall 23/159 (90 false, 136 missed); down precision 36/88 and recall 36/272 (52 false, 236 missed); flat 237/310 actual; Brier 0.658186649754159; version 1.0 69/208, 1.1 227/533; 1,955 provided/3,029 held, paired baseline 302/729 versus operating 292/729. These are unchanged observations, not new training or independent confirmation. Raw unmatched: 14 matured KR intraday, 12 pending US daily, 8 pending KR daily. Maximum per symbol/mode learned sample count 33, maximum UTC observation-date count 18; no group meets the minimum. Prior independent audit 45345803709 actually recomputed the evidence; recovery 45345803673 job skipped (no recovery execution). Current paper audit reports 503 registered plans, 487 missing execution evidence, 16 awaiting; no actual human receipt or external quote adapter, after-cost edge, or untouched confirmation. Artifact 13750188846 metadata still shows unexpired; the prior 20-shadow evaluation and 2,520 historical targets remain used, not fresh test data. No new model hypothesis, refit, promotion, policy/production change or backfill. Root cause of the renewed gap remains unverified, no separate reproducible engineering defect established. timing_utility=not_proven.
