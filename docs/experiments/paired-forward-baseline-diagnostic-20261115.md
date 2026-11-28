# Paired prospective model–baseline diagnosis — 2026-11-15 (research only)

**Status: observed-existing-evidence diagnosis; not a new model trial or untouched confirmation.** This note supplements the existing PR #147 failure record without changing model code, prediction times, original forecasts, outcomes, class boundaries, ledger, acceptance criteria, or operating deployment. It is not an alert, order, recommendation, or claim of newly matured market results.

## Evidence fixed before this diagnosis

- Main commit: `0b8fcc4c4da1e36065692f007d1f2d60fb3cc8dd` (2026-11-15); changed since preceding reviewed main `5646257faa53d0e5f4fb91b97b1edbf6c5dd4d76` only in `market-radar-data.json` and `stocks-dashboard-data.json` (one commit). No new original forecast/outcome/learning evidence.
- Stored paired report: `stock-forecast-learning.json`, Git blob `eb8c0531baf9d9fdc02688c1c2aa53a9484aee36` (generated 2026-11-14 00:58:18 UTC).
- Original result rows: `stock-forecast-outcomes.jsonl`, Git blob `e102f7a9cc5b53dad00740d72abc49897c79d896`; learned-event rows: `stock-forecast-learning-events.jsonl`, Git blob `f4f61b06a7f39450a263014a8dd0f8aae549c2dc`.
- Frozen forecast ledger: `stock-forecast-ledger.jsonl`, Git blob `7eace60187c32cafa1bf10b628c2fd33c020de72`. Connector returned empty decoded content for the 4,499,997-byte file; therefore independent issuance/band checks rely on the actual non-skipped [Independent Forecast Evidence Audit 43665836012](https://github.com/Ohoredingdong/Notion/actions/runs/43665836012), not a false claim that the full ledger was independently downloaded in this execution.
- Actual audit recomputed 527 ledger rows, 493 outcomes, 416 eligible scored, 170 correct, 3,264 attempted calls, 1,979 no-calls; 0/40 groups met the minimal prospective sample gate. A later forecast run [43669988482](https://github.com/Ohoredingdong/Notion/actions/runs/43669988482) skipped its research steps due to the time window. No market results for the November 16 targets were fabricated.

## Reproduced direction performance (all 416 eligible original outcomes)

The outcome JSONL and the 416 unique immutable `learn_after_score` prediction IDs join one-to-one; 416 actual/learned labels and observation-availability times agree; stored return-price arithmetic, result `correct` flags and issuance-before-target/score-after-target chronology agree for these 416 rows.

| Actual/predicted direction | Correct | Predictions | Actual events | Precision | Recall | Missed | False calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| Up | 19 | 71 | 98 | 26.76% | 19.39% | 79 | 52 |
| Down | 20 | 50 | 149 | 40.00% | 13.42% | 129 | 30 |
| Flat | 131 | 295 | 169 | 44.41% | 77.51% | 38 | 164 |

Total 170/416 (40.87%), Brier loss 0.6566082974; this is **the unchanged original cumulative historical-forward ledger**, including every incorrect eligible call. Other original exclusions remain separate: 21 reissued, 22 overlaps, 12 missing outcome, 36 not timely public and 20 pending targets. No observed target is retroactively recategorized or hidden.

## Newly isolated diagnostic: same-event frozen training-frequency baseline (404 cases)

The existing report provides a strictly matched **404-row** incumbent–baseline cohort. The remaining 12 scored cases lack eligible contemporaneous baseline metadata and must not be assigned invented baseline probabilities. The 404 are *already observed and previously used*, not a new independent confirmation, new experiment or post hoc candidate pool.

| On the same 404 forecast targets | Applied model | Pre-existing training-frequency baseline |
|---|---:|---:|
| Correct | 166 | 170 |
| Accuracy | 41.09% | 42.08% |
| Up recall | 19/98 = 19.39% | 16/98 = 16.33% |
| Down recall | 20/145 = 13.79% | 16/145 = 11.03% |
| Up precision | 19/68 = 27.94% | 16/51 = 31.37% |
| Down precision | 20/48 = 41.67% | 16/39 = 41.03% |
| Brier loss (lower better) | 0.65668711 | 0.63915446 |
| Log loss (lower better) | 1.09744207 | 1.05782464 |
| Balanced accuracy | 37.35% | 37.69% |

The applied model captured **3 additional rises** and **4 additional declines** on the same paired targets, but **4 fewer total correct calls**, markedly worse probability error, and worse up precision. This is a *tradeoff*, not a verified directional winner or a causal explanation. Same-day market dependence, small number of observation days (12), and selection effects prevent a robust performance-advantage claim. A simple baseline should not be overwritten or made retroactive to the 12 unmatched cases.

The previously rejected one-recipe recent daily candidate had a historical diagnostic of 997/2,520 (39.56%) yet missed 62 additional actual rises; its already-observed original frozen shadow cohort scored 2/20 (10%), zero up/down captures. These historical and shadow results must not be pooled into the operational 416 or reclassified as untouched final confirmation.

## Root-cause boundaries and next permitted action

**Reproduced failure mode**: the operating forecast does not demonstrate simultaneous recall, precision and probability-calibration improvement over the *existing* same-event simple baseline; up/down detection is sparse and most events are classified flat. The old training-vintage hypothesis is plausible but not proven causal; the recently refitted logistic candidate failed its predefined up-recall gate. No existing threshold should be relaxed to compensate.

**No new model recipe, parameters, baseline backfill or retraining was attempted this run (new recipe trials: 0).** No untouched post-selection follow-up data were available. The 2,520 historical targets and 20 observed shadow targets are already used. Wait for independently frozen future outcomes; then separately assess by symbol/market/time window the prespecified precision, recall, abstention, coverage and Brier/log scores plus execution/receipt/cost evidence before proposing even a research-only challenger. The original hard requirement is >=120 nonoverlapping targets and >=20 observed days **per group**, with sufficient up/down real and predicted counts and unchanged directional gates. The production model and strict-green checks must remain unchanged.

## Limits

The arithmetic is against stored single-provider outcomes, **not exchange-authenticated KRX/NXT or US original quote/candle verification**. Public read success is not human receipt. Existing paper audit lacks actual post-delivery executable quotes, human notification receipt, transaction cost evidence, and untouched follow-up. `timing_utility=not_proven`; no recommendation, no buy approval, no user-completion notification.
