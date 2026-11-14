# Frozen November 10 research shadows — first matured outcome check (2026-11-15)

**Scope: research-only, additive follow-up to Draft PR #147. NOT a new recipe trial, NOT an operating-ledger update or model promotion.** This document was written after the outcome dates; it never represents a backdated forecast or human delivery. The November 10 experiment report is unchanged.

## Evidence and source pinning

- Pre-registered recipe and historic test: `docs/experiments/recent-daily-model-20261110.md` and `recent-daily-model-20261110-results.md`, branch `research/recent-daily-model-20261110`, study Actions [42790476451](https://github.com/Ohoredingdong/Notion/actions/runs/42790476451). **Exactly one model recipe** was tested; the used 2,520 historical targets are not an untouched interval.
- Original prospective shadows: **20** records from artifact **13750188846**, file `recent-daily-model-one-recipe-proof.zip`, verified SHA256 `f8f4592b3437a368377418d926797b519cc6bf943c238dd2ffdf6e13ff176077`. Archive was retrieved and its entire ZIP SHA256 independently matched the originally recorded digest. ZIP `experiment/<symbol>.json` carries exact initial probability vector, frozen band, target, observed/received/issued timestamps, and contemporaneous reference vectors. Research artifact expiry currently listed as **2026-12-10 09:25:39 UTC**; no retroactive production issuance.
- Follow-up **single-provider stored price** source: immutable repository main **`b27cf48b6058afc203bba821f24ec951022a789c`**, `stock-forecast-outcomes.jsonl` Git blob **`e102f7a9cc5b53dad00740d72abc49897c79d896`**; 493 outcome rows total. Precisely **one observed, matured daily outcome per original shadow symbol and exact frozen target interval** was matched (20/20). Checked source times are **2026-11-10 21:27:32.245768 UTC** (12 US rows) and **2026-11-11 07:52:31.439901 UTC** (8 KR rows), both after respective target ends. No target or issue time was revised.
- The operating outcome row and archived candidate shadow are **distinct forecasts** of the same later price interval. We used the operating source's stored target open/close solely as an *unverified proxy outcome for research*, **not** its incumbent prediction or probability for the new candidate. No inference of independent exchange-authenticated bars, specific KRX/NXT venue, executable quotes, contemporaneous user receipt, or source vintage.
- Reproduction: two separately implemented checks, a Python ZIP-reader and a JavaScript calculation reading the pinned GitHub stored outcomes, returned the same **20 matching intervals, all 20 directions and confusion matrix**. The Python reader independently checked probability sums and `observed_until <= received_at <= issued_at < target.start` for each archived shadow. Python calculated the three frozen model vectors' Brier/log losses, unrounded probabilities; displayed rows below are rounded for inspection. This is a cross-check of arithmetic against the *same* provider, not an external price validation.

## Fixed scoring and provisional cohort results

Use each shadow's ORIGINAL neutral band `b` and target open/close, `r_pct=100*(close/open-1)`: actual up iff `r_pct > b`, actual down iff `r_pct < -b`, else flat. Frozen candidate call is argmax of the original (down, flat, up) probability vector. No target post-selection, no missing calls discarded, no changes to bands or verdicts.

| Metric (single-provider, 20 targets only) | Recent daily candidate | Contemporaneous incumbent reference | Contemporaneous movement_then_direction reference |
|---|---:|---:|---:|
| Correct / original predictions | **2/20 (10.00%)** | 3/20 (15.00%) | 6/20 (30.00%) |
| KR 11 Nov, 8 fixed targets | **0/8 (0%)** | 3/8 (37.50%) | 2/8 (25%) |
| US 10 Nov, 12 fixed targets | **2/12 (16.67%)** | 0/12 (0%) | 4/12 (33.33%) |
| Up precision / calls | **0/4 (0%)** | 1/6 (16.67%) | 0 calls (undefined) |
| Up recall / actual rises | **0/9 (0%)** | 1/9 (11.11%) | 0/9 (0%) |
| Down precision / calls | **0/4 (0%)** | 0/1 (0%) | 0 calls (undefined) |
| Down recall / actual falls | **0/5 (0%)** | 0/5 (0%) | 0/5 (0%) |
| Overall multiclass Brier (lower better) | 0.784095 | 0.790294 | 0.739928 |
| Overall log loss (lower better) | 1.277588 | 1.301090 | 1.193154 |

Actual labels: **9 up, 5 down, 6 flat**. Candidate calls: **4 up, 4 down, 12 flat**. Candidate confusion matrix, actual rows / predicted columns in `[down,flat,up]` order: `[[0,4,1],[1,2,3],[3,6,0]]`; 18 errors total. The six-correct movement comparator **called flat in all 20**: higher accuracy here is not evidence of two-sided capability. The recent candidate happened to have slightly lower Brier than the contemporaneous incumbent on this particular, tiny set while direction recall and accuracy were worse. No selective success or unilateral improvement qualifies it for use.

## Every original shadow retained (no exclusions)

Below, `issued` means **2026-11-10 UTC** time of archived *research* issuance (not user receipt); `P(d/f/u)` and bands are **rounded display values only**, not source replacement. KR target: **2026-11-11 00:00–06:30 UTC**, US target: **2026-11-10 14:30–21:00 UTC**. Open/close reproduce the pinned saved-provider outcomes; no external venue authentication.

| Symbol | Issued UTC | Market | Target open | Target close | Frozen band % | Frozen P(d/f/u) | Candidate | Actual | Incumbent ref | Movement ref |
|---|---|---|---:|---:|---:|---|---|---|---|---|
| 000660.KS | 09:25:30.489520 | KR | 1206000 | 1277000 | 2.075196 | .339106/.473090/.187804 | flat | up | flat | flat |
| 005380.KS | 09:25:38.614277 | KR | 273000 | 272500 | 1.107628 | .279293/.304826/.415881 | up | flat | flat | flat |
| 005930.KS | 09:25:29.839269 | KR | 197100 | 206000 | 1.593848 | .337621/.401290/.261089 | flat | up | flat | flat |
| 035420.KS | 09:25:30.692408 | KR | 194200 | 194300 | .968832 | .407096/.397270/.195634 | down | flat | flat | flat |
| 207940.KS | 09:25:38.480018 | KR | 1473000 | 1430000 | 1.491218 | .199786/.517963/.282251 | flat | down | flat | flat |
| 403870.KQ | 09:25:31.639460 | KR | 36500 | 40100 | 1.951848 | .328709/.350713/.320578 | flat | up | flat | flat |
| ^KQ11 | 09:25:27.927056 | KR | 668.47998047 | 705.09997559 | 1.193884 | .424678/.322481/.252841 | down | up | up | flat |
| ^KS11 | 09:25:26.892675 | KR | 5209.70996094 | 5375.35986328 | 1.275273 | .308790/.383211/.307999 | flat | up | flat | flat |
| AAPL | 09:25:32.427660 | US | 351.35000610 | 348.51000977 | .578347 | .308857/.357169/.333974 | flat | down | flat | flat |
| AMZN | 09:25:36.546422 | US | 266.20999146 | 270.86999512 | .912533 | .127940/.661307/.210753 | flat | up | flat | flat |
| DOCS | 09:25:35.545499 | US | 32.49000168 | 32.41999817 | .981116 | .315221/.333220/.351558 | up | flat | up | flat |
| EXLS | 09:25:36.461549 | US | 43.15000153 | 44.29999924 | .631985 | .342820/.369633/.287547 | flat | up | flat | flat |
| FN | 09:25:34.614242 | US | 361.69000244 | 348.51998901 | 2.679115 | .292010/.412413/.295577 | flat | down | flat | flat |
| ^GSPC | 09:25:28.630829 | US | 7513.08984375 | 7520.93017578 | .470378 | .330574/.334318/.335107 | up | flat | up | flat |
| ^IXIC | 09:25:28.829062 | US | 25047.44726562 | 25065.875 | .654713 | .262425/.376891/.360684 | flat | flat | up | flat |
| META | 09:25:38.405074 | US | 637.25 | 641.39001465 | .927090 | .323182/.341945/.334873 | flat | flat | down | flat |
| MSFT | 09:25:33.055966 | US | 543.40997314 | 533.15997314 | .785672 | .277776/.475586/.246637 | flat | down | up | flat |
| NVDA | 09:25:33.268473 | US | 173.97999573 | 168.88999939 | 1.031921 | .327280/.328082/.344638 | up | down | up | flat |
| ON | 09:25:34.382578 | US | 67.51000214 | 69.61000061 | 1.536773 | .405230/.393091/.201680 | down | up | flat | flat |
| TSLA | 09:25:36.700804 | US | 370.54000854 | 379.77999878 | 1.292477 | .408780/.403503/.187718 | down | up | flat | flat |

## Decision / experiment accounting

**Candidate promotion remains BLOCKED.** The originally preregistered historical nonregression gate already failed (62 extra actual up misses in 2,520 used historical targets). This new 20-target *shadow* check is worse in directional performance and nowhere near original per-group minimum of 120 nonoverlapping targets/20 days. The comparison is only **one KR date + one US date**, with strong within-market dependence and no unused, separately reserved final confirmation. A pooled result is descriptive, **never** a substitute for each group's gate. This 20-row cohort is now observed/inspected and **must not be reused as untouched model-selection or confirmation data**.

The operating cumulative ledger is untouched and still independently reports **170/416 (40.87%)** with all historical errors, separately from this shadow score. Historical candidate accuracy **997/2520 (39.56%)** is NOT its forward accuracy. PR #147 remains Draft; no parameter tuning, new candidate, new model-hypothesis test, original scoring change, reissuance, retroactive addition, data rewrite, research-pipeline promotion, order or alert. Research new-recipe trials this run: **0**; previous total on this experiment: **1**. Original artifact, outcome data and controls remain unchanged.

These stored Yahoo-derived prices are not authoritative venue-certified candles, no KRX/NXT venue was resolved, and no trading quote, actual user delivery, after-cost strategy benefit, independent follow-up advantage or external raw-bar match was established. Research audit tests / GitHub CI do not establish usefulness. Applicable decision stays **`timing_utility=not_proven`**; do not send a completion notification.
