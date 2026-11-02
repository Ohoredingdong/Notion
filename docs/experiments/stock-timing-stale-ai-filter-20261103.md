# Research-only prospective timing UI: exclude expired/unknown forecasts from actionable-seeming signal filters

Preregistered 2026-11-03 KST on pinned main `7ec4d36fbc4372e02fb26f26e5138de0ae84982d`. Status: hypothesis and negative controls frozen **before** observing any RED/GREEN changes. This is an engineering usability/safety test, not a new direction model, new historical result, trade recommendation or completed timing-usefulness validation.

## Immutable scope
Read in full: `docs/stock-timing-acceptance-20261029.md` (blob `69526101025c0394b13a55bfb73b9be5240e5fca`), `docs/stock-direction-specialists.md` (`6d5498666cd6da4d4528c46a4f1cb911715e90bd`), `docs/stock-bounded-autopilot.md` (`a5176f6aa075c49a090e6a3ec01b64fb323420ed`). Existing earlier #82 observations and existing unrelated UI PR #58/#71 checked. No changes permitted to forecast ledger, outcomes, original source timestamps, learning, strict-green-1.0, orders, credentials, monitoring automation, schedule or approval thresholds.

## Reproduction hypothesis (bounded)
The current **production-loaded** `assets/stock-radar-flow-v2.js` makes `fxPrediction(...).active=true` for a valid stored `research_prediction` **even if its frozen `target.end` has already elapsed**, and `fxUniverse` uses only `active` for the `AI 신호` and `상승/하락` list filters. Thus historical forecasts, despite correctly showing `기간 종료` in the chip, are surfaced as apparent current signal-filter matches during periods without a fresh producer publication. Missing target end clocks have the analogous issue. This is a display/selection issue and does NOT prove an actual trade happened; do not discard old records or relabel results.

## Frozen RED/GREEN controls (synthetic only; no price evidence)
A fixed-clock Node VM test loads the actual JavaScript asset, injects only a read-only test handle and `Date.now()` clock, never changes the operating script at test time.
1. At fixed `2026-11-02T22:00:00Z`, an originally issued UP signal with target end `2026-11-02T21:00:00Z` remains displayed/accessible in the **all** list, and `fxPrediction` marks it `stale`, but it must NOT appear under `ai` or `up` *current signal filters*. Existing code is expected to fail this test (RED).
2. A valid unexpired prospective UP signal remains under both `ai` and `up`.
3. A no-call remains excluded from current signal filters; a timestamp-missing/unknown active record must also be excluded, but retained in the unfiltered history.
4. The DOWN filter must not accidentally admit UP examples. Original directions, probabilities, targets and history are not rewritten.

## Fix and safe termination
Exactly one small change confined to `fxUniverse` in `assets/stock-radar-flow-v2.js`: test `fxPrediction.stale` and `fxPrediction.unknown` as exclusions only for `ai` and directional signal list filters. Keep `fxPrediction` historical classification/chip and `all` mode unchanged. Run RED once, then GREEN once, including existing Node forecast invariant tests, independent read-only forecast audit and acceptance guard and Chromium flow browser regression if possible. Stop on unexplained failure, do not relax criteria or silently rerun. All research changes remain on this branch until full regression, independent audit, public deployment checks and review; a green unit/branch check is NOT public-deployment or usefulness proof.

## Fixed factual baseline, not a newly observed score
At pinned main: 107 forecast issuance rows, 86 distinct future event keys, 21 repeat issues, eight overlapping excluded, 78 nonoverlapping. 54 eligible scored with 14 correct (25.93%) and 3-class mean Brier 0.6786795164555172, 12 mature missing late KR intraday targets and 12 future daily targets at 2026-11-02T19:34:17Z. Original 81 saved results are internally arithmetically consistent; no independent official exchange raw candles, executable quotes, user alert receipt, after-cost prospective simulation or untouched follow-up. All 24 evaluation groups fail minimum sample gate. This engineering fix cannot change `not_proven` and cannot issue a buy approval.

## Experiment record
Preregistered, awaiting RED. Record test count, failures and full Actions run links after actual executions. No unchecked changes merged to main.
