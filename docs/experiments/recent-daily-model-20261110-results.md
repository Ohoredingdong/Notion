# Recent daily model — measured results and non-promotion decision

Measured at 2026-11-10T09:25:38.744385Z (18:25:38 KST).
Fixed main: `9814e420317ba7a3506583b4370b3ea9184a2196`.
Tested code: `209c391e1c6e65ee06090ddef6419b19ecd4f655`.
Prereq hypothesis: docs/experiments/recent-daily-model-20261110.md, committed before implementation/results.

## What actually ran

[Research Recent Daily Model / Actions 42790476451](https://github.com/Ohoredingdong/Notion/actions/runs/42790476451), job 129742305599, completed all stages successfully: new-candidate guards, original regressions, twenty requested real Yahoo daily-history collections, one fixed candidate recipe, and an independent standard-library arithmetic/chronology check. This is an engineering execution success, NOT a model-acceptance pass.

Artifact: `recent-daily-model-one-recipe-proof`, ID `13750188846`, SHA256 `f8f4592b3437a368377418d926797b519cc6bf943c238dd2ffdf6e13ff176077` (30-day retention). Contains exact code, all diagnostic rows for all 20 groups, per-fold training/calibration boundaries, fresh shadow records, test logs and independent-check.json. Local archive digest matched the GitHub artifact digest. A second standalone local standard-library oracle independently matched all four methods' 2,520-row confusion matrices, correct counts and Brier loss (10,080 method/row comparisons), without importing model or audit code.

22 new candidate tests, 194 original model/learning/paper/data regressions, 149 timing guards and 19 auditor self-tests passed: 384 Python tests. Original 13 UI schema checks + 9 bounded-recovery checks also passed. 685 tracked source/evidence files remained byte-identical during the real experiment; final git status contains only untracked Python bytecode. No forecast ledger, outcome, learning state, existing model/policy/UI/monitor/schedule or main ref was changed.

## Apples-to-apples historical diagnostic (NOT actual forward score)

All 20 requested groups completed; no source group was dropped. Each has the last 126 eligible daily targets (2,520 total), six fixed chronological blocks of 21, with only earlier resolved labels used for each refit. Across groups the diagnostic target timestamps span 2026-05-04 through 2026-11-10. Data are currently retrieved historical prices, not point-in-time-vintage/exchange-authenticated prices. Later blocks can use previously resolved earlier blocks as preregistered; these blocks are not an untouched final confirmation.

| Measure | Incumbent on same historical targets | Recent daily candidate |
|---|---:|---:|
| Correct / targets | 971 / 2,520 | 997 / 2,520 |
| Accuracy | 38.531746% | 39.563492% |
| Balanced accuracy | 37.467740% | 37.776757% |
| Actual down captured | 163 / 844 (19.312796%) | 187 / 844 (22.156398%) |
| Actual up captured | 250 / 720 (34.722222%) | 188 / 720 (26.111111%) |
| Actual flat captured | 558 / 956 | 622 / 956 |
| Up precision | 33.200531% | 32.695652% |
| Down precision | 37.129841% | 39.618644% |
| Brier loss (lower is better) | 0.6705477303596312 | 0.6659985848190090 |
| Log loss (lower is better) | 1.110865436410897 | 1.0993739519859604 |

Accuracy rose by 26 correct predictions / 1.031746 percentage points, but **62 additional actual rises were missed**. The fixed direction nonregression criterion failed. Do not choose only the twelve improved groups or suppress the seven worsened groups. One group tied.

Other unchanged reference recipes on exactly the same 2,520 targets: training-frequency baseline 892 correct (35.396825%), Brier 0.6641731921416033; reviewed movement_then_direction 976 correct (38.730159%), Brier 0.6661089966741705. The new candidate's Brier remains worse than the frequency baseline.

135-date, date-equal-weight bootstrap diagnostic accuracy-gain interval: [-0.265586, +3.296451] percentage points. Brier-gain interval: [-0.0006216501, +0.0126786424]. Both include zero. Serial dependence and repeated-analysis selection are not resolved; these are not significance/promotion claims.

## Complete group results (126 targets each)

| Symbol | Incumbent | Recent candidate |
|---|---:|---:|
| 000660.KS | 60/126 (47.62%) | 56/126 (44.44%) |
| 005380.KS | 50/126 (39.68%) | 50/126 (39.68%) |
| 005930.KS | 46/126 (36.51%) | 50/126 (39.68%) |
| 035420.KS | 51/126 (40.48%) | 62/126 (49.21%) |
| 207940.KS | 47/126 (37.30%) | 53/126 (42.06%) |
| 403870.KQ | 37/126 (29.37%) | 40/126 (31.75%) |
| AAPL | 48/126 (38.10%) | 37/126 (29.37%) |
| AMZN | 49/126 (38.89%) | 52/126 (41.27%) |
| DOCS | 53/126 (42.06%) | 55/126 (43.65%) |
| EXLS | 46/126 (36.51%) | 47/126 (37.30%) |
| FN | 50/126 (39.68%) | 49/126 (38.89%) |
| META | 46/126 (36.51%) | 44/126 (34.92%) |
| MSFT | 50/126 (39.68%) | 48/126 (38.10%) |
| NVDA | 43/126 (34.13%) | 45/126 (35.71%) |
| ON | 43/126 (34.13%) | 53/126 (42.06%) |
| TSLA | 46/126 (36.51%) | 57/126 (45.24%) |
| ^GSPC | 60/126 (47.62%) | 50/126 (39.68%) |
| ^IXIC | 51/126 (40.48%) | 54/126 (42.86%) |
| ^KQ11 | 51/126 (40.48%) | 47/126 (37.30%) |
| ^KS11 | 44/126 (34.92%) | 48/126 (38.10%) |

## New prospective research records

Twenty fresh shadow predictions were actually produced between 2026-11-10T09:25:26.892675Z and 09:25:38.614277Z. Targets: twelve US next-regular-session open-to-close targets on November 10, and eight KR next-regular-session targets on November 11. Exact probabilities, bands, real observation/receipt/issuance timestamps, contemporaneous incumbent/cascade references and model/source hashes are in each group's artifact file. Their result count is zero as of this experiment; candidate_forward_accuracy is null, NOT 100%.

Current candidate training end advanced to 2026-08-07 (KR) or 2026-08-12 (US), with separate calibration through November 9 (KR) or November 6 (US). The 60-session calibration partition remains separate. This demonstrates more recent fitting, not better future performance. It does not justify using recent candidate coefficients to retroactively revise old predictions.

The research artifact is not proof of timely public website delivery, human receipt or an executable quote. No completed prospective candidate target is claimed. No profitable trading, real-time connection or complete approval is established.

## Decision

**Do not replace production.** The preregistered historical candidate condition failed on up recall, uncertainty intervals cross zero, and independent future results do not yet exist. Preserve this one recipe and its mixed/failed results as a draft research candidate. No additional hyperparameter/model search on the same evaluation window.

The original published prospective score remains 96/256 (37.50%) at the pinned source. It is not replaced by 39.56% historical accuracy. No 100% score has been achieved or guaranteed. Existing per-symbol/mode forward gates, all original challengers including movement_then_direction, untouched follow-up, source/receipt/quote/cost/risk requirements and strict-green remain intact.
