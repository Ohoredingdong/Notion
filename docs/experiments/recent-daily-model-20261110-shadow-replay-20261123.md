# Frozen recent-daily shadow 20 — later stored-outcome replay (2026-11-23)

**Research-only independent read-only analysis. No new candidate recipe, no tuning, no backdated production predictions, no promotion.** This evaluates the **previously frozen** 20 shadow predictions from the one-recipe trial on their exact originally stated targets. These 20 targets are **used** for this diagnostic and MUST NOT be called an untouched future confirmation window. They are distinct from the original production forward ledger; their outcomes MUST NOT be appended to production learning, scoring or deliveries.

## Provenance and chronology

- Frozen original shadow: [Actions 42790476451](https://github.com/Ohoredingdong/Notion/actions/runs/42790476451), artifact **13750188846**, ZIP SHA-256 `f8f4592b3437a368377418d926797b519cc6bf943c238dd2ffdf6e13ff176077`. All **20** original `experiment/*.json` `fresh_shadow` objects extracted; none regenerated or altered. Their observation, receipt and issue times are each before target.start. They were issued 2026-11-10 09:25 UTC, before **US Nov 10** open-to-close or **KR Nov 11** open-to-close targets respectively. Original candidate probabilities, direction, target and per-record neutral band retained.
- Later recorded original provider outcomes: [Actions 45109154136](https://github.com/Ohoredingdong/Notion/actions/runs/45109154136), artifact **14788532969** (archived source files), from pinned main `c91faf8c2a2ac3ba476f227940080ce4e34e757c`. The independent replay verified Git blob SHA **`0ff476d878c80f657a9f4688f0a57967e13a35d3`** for `stock-forecast-outcomes.jsonl` (802 original outcome rows), and **`a60130e5ec8643c9961f89cc2e0e0a5c22758ba2`** for `stock-forecast-ledger.jsonl` (844 original predictions). Exact one-to-one join by **symbol + daily mode + target.start + target.end + market**, 20/20 unique matches; original corresponding outcome IDs cross-checked with the original ledger. Outcomes were recorded **after target.end** (US 2026-11-10 21:27 UTC; KR 2026-11-11 07:52 UTC). Prices are delayed yfinance stored target open/close, **not exchange-authenticated venue bars**; Korean KRX/NXT venue cannot be externally settled from these records.
- A separate independent Python scorer (not importing the prediction model or outcome scorer) recomputed `100*(close/open-1)`, **each shadow's own frozen** `neutral_band_pct`, three-class actual, argmax of the original probabilistic vector, Brier error and per-direction confusion/precision/recall. Verified all vector sums, saved candidate argmax, target chronology and target completeness. These are post-target scored research shadows, **not timely publicly delivered alerts, user receipt or executable bids/asks**. The same stored target prices feed the paired comparisons; they do not establish independent exchange-price authenticity.

## Paired diagnostic at the originally frozen shadow target and neutral band

| Method (same 20 targets) | Correct | 3-class Brier ↓ | Rising calls: correct / calls; captured / actual | Falling calls: correct / calls; captured / actual |
|---|---:|---:|---|---|
| **Recent daily shadow candidate** | **2/20 (10%)** | **0.78409524** | **0/4; 0/9** | **0/4; 0/5** |
| Contemporaneous incumbent reference | 3/20 (15%) | 0.79029388 | 1/6; 1/9 | 0/1; 0/5 |
| Contemporaneous movement_then_direction reference | 6/20 (30%) | 0.73992773 | 0/0; 0/9 | 0/0; 0/5 |

The actual classes **under the shadow's frozen per-item bands** are 9 up, 5 down, 6 flat. Shadow candidate: **up precision 0/4 = 0%, up recall 0/9 = 0%, 4 false-up, 9 missed-up; down precision 0/4 = 0%, down recall 0/5 = 0%, 4 false-down, 5 missed-down; flat 2/12 correct, 4 missed-flat, 10 false-flat**. The movement_then_direction reference made **20/20 flat calls**: its up/down precision is **undefined (0 calls)**, not 100%, despite its greater overall count. Incumbent and candidate were compared using the exact same outcome class and neutral band **from each shadow row**, not retrospective incumbent bands or inferred historical probabilities. Their reference vectors were actually saved contemporaneously in the original artifact.

By market, keeping US/KR separate: **US Nov 10, candidate 2/12**, incumbent 0/12, movement 4/12; **KR Nov 11, candidate 0/8**, incumbent 3/8, movement 2/8. Only **one observation day per market**; pool of 20 is not the required 120 distinct targets / 20 days per group. Symbols share market and date factors; no confidence or model-improvement claim can be drawn from the pooled count alone.

## Full per-symbol record (no failure hidden)

Here `↑` = up, `↓` = down, `—` = flat. `✓` means a forecast class matched the stored provider result using its original candidate shadow band, `✗` means not. This is a diagnostic table, not a production score revision.

| Symbol | Result % | Band ±% | Actual | Candidate | Incumbent | Movement→direction |
|---|---:|---:|:---:|:---:|:---:|:---:|
| 000660.KS | +5.8872 | 2.0752 | ↑ | — ✗ | — ✗ | — ✗ |
| 005380.KS | −0.1832 | 1.1076 | — | ↑ ✗ | — ✓ | — ✓ |
| 005930.KS | +4.5155 | 1.5938 | ↑ | — ✗ | — ✗ | — ✗ |
| 035420.KS | +0.0515 | 0.9688 | — | ↓ ✗ | — ✓ | — ✓ |
| 207940.KS | −2.9192 | 1.4912 | ↓ | — ✗ | — ✗ | — ✗ |
| 403870.KQ | +9.8630 | 1.9518 | ↑ | — ✗ | — ✗ | — ✗ |
| ^KQ11 | +5.4781 | 1.1939 | ↑ | ↓ ✗ | ↑ ✓ | — ✗ |
| ^KS11 | +3.1796 | 1.2753 | ↑ | — ✗ | — ✗ | — ✗ |
| AAPL | −0.8083 | 0.5783 | ↓ | — ✗ | — ✗ | — ✗ |
| AMZN | +1.7505 | 0.9125 | ↑ | — ✗ | — ✗ | — ✗ |
| DOCS | −0.2155 | 0.9811 | — | ↑ ✗ | ↑ ✗ | — ✓ |
| EXLS | +2.6651 | 0.6320 | ↑ | — ✗ | — ✗ | — ✗ |
| FN | −3.6412 | 2.6791 | ↓ | — ✗ | — ✗ | — ✗ |
| META | +0.6497 | 0.9271 | — | — ✓ | ↓ ✗ | — ✓ |
| MSFT | −1.8862 | 0.7857 | ↓ | — ✗ | ↑ ✗ | — ✗ |
| NVDA | −2.9256 | 1.0319 | ↓ | ↑ ✗ | ↑ ✗ | — ✗ |
| ON | +3.1106 | 1.5368 | ↑ | ↓ ✗ | — ✗ | — ✗ |
| TSLA | +2.4937 | 1.2925 | ↑ | ↓ ✗ | — ✗ | — ✗ |
| ^GSPC | +0.1044 | 0.4704 | — | ↑ ✗ | ↑ ✗ | — ✓ |
| ^IXIC | +0.0736 | 0.6547 | — | — ✓ | ↑ ✗ | — ✓ |

## Decision and separation from original ledger

**Keep the 2026-11-10 one-recipe candidate in rejected/held research state; do not promote.** Its original historical 2,520-target replay (`997/2520 = 39.56%`) failed the preregistered up-recall gate and this later 20-shadow paired diagnostic also **does not** establish bidirectional improvement. A small sample with all candidate up/down calls wrong is not proof all future calls will be wrong; conversely neither an arbitrary all-correct sample nor a controller/test pass guarantees future performance. Do not choose a new recipe on these same used dates. Preserve the preexisting 0/40 acceptance groups, operational forward score **279/693 (40.26%)** in a separate cohort (not `281/713` or any merged score), all historical errors, and all original production targets/times/probabilities. New research model hypotheses this run: **0**; new tuning trials: **0**; model/production/strict-green/other monitors/orders changes: **0**.

This second source is the stored delayed-price outcome stream, **not independent official exchange bars**, point-in-time price-vintage certification or executable quote evidence. Signal publication and human receipt for the shadow are **false/unverified**. Untouched subsequent days, 120/20 per-group forward evidence, separate market/venue controls, official price comparison, actual quote/cost/receipt proof and risk-adjusted paper advantage are still missing. Status remains `timing_utility=not_proven`; no completion alert warranted.
