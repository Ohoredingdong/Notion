# Public verification follow-up — 2026-11-23 (research evidence only)

This is a **new real-run observation**, not a second model hypothesis, not a redefinition of the 2026-11-11 preregistration, not a new scored future outcome and not approval to merge PR #149. Earlier research hypotheses, acceptance thresholds and original evidence remain untouched.

## Frozen evidence and reproduced failure

- Pinned observed `main`: `c91faf8c2a2ac3ba476f227940080ce4e34e757c`; six following commits after published transaction `f09a3a814f2a17de67403164e9202c6fc1a3065d` changed only radar health and unrelated brain-training / game pages, not model or forecast sources.
- [Stock Prospective Forecasts run 45109154136](https://github.com/Ohoredingdong/Notion/actions/runs/45109154136), job 137477282882: completed original tests, 40-group collection, staged transaction and actual publication at **2026-11-23 04:01:29 UTC**, requested Pages build at 04:01:29–04:01:33 UTC, then failed `Verify public autonomous cycle and code` at **04:03:34 UTC** after 16 checks. Actual terminal error: `RuntimeError: public_deployment_unverified: ValueError`. Paper public-verification and publication-proof stages were skipped. This is **not** a success merely because the controller JSON says `research_cycle_verified`.
- The original production verifier only logs `type(exc).__name__` after exhausting checks, losing the JSON-vs-JS-vs-HTML mismatch identifier. The generic label is independently reproducible by reading the exact production source and comparing its exception paths. This is **the previously preregistered and GREEN-tested diagnosis in draft PR #149**, not a newly discovered Pages root cause. Which public asset was stale/inconsistent in the November 23 run is **unknown**. No outside authenticated public-byte capture was available.
- Existing [PR #149](https://github.com/Ohoredingdong/Notion/pull/149) already has the bounded, allowlisted per-asset error-label fix and synthetic mismatch/secret-redaction regressions, but it is draft/unmerged. Do not duplicate the fix, weaken byte equality, or replay a published forecast transaction solely to verify the website. Existing [PR #103](https://github.com/Ohoredingdong/Notion/pull/103) separately explores Pages propagation lag; it is also draft.

## New frozen predictions are not new answers

- Main original ledger has **844 unique forecast IDs** (previous snapshot 836), and the November 23 research cycle issued **eight** new Korean intraday predictions at **04:01:07 UTC**, with target **04:15–04:45 UTC**, original probability vectors and neutral bands unchanged.
- At the run-history inspection cutoff **2026-11-23 04:37 UTC**, these eight targets had not fully matured and had **zero** outcome rows. They also had **zero matching stored public verification / delivery proof rows** following the failed verification. They are **not** counted as observed winners, losers or human-delivered alerts. Their later actual outcome, exchange venue raw-price authenticity, and subsequent public status remain unverified.
- Other legacy missing outcome targets: 14 matured-without-outcome and 20 future targets. Total now 42 unscored of 844. Never backfill the missing 14 from guesses. The separate intraday missing-window issue is already recorded in draft PR #150.
- Across all stored attempts: 4,744, research-prediction status 1,871, no_call 2,873 (scheduler-attempt call rate **39.44%**, not market coverage). Public verification ledger has 124 rows, none proves a human notification receipt.

## Independently recomputed unchanged qualifying results

An independent JavaScript replay joined all **693** learning-event `prediction_id` values with exactly matching frozen original ledger records and existing outcomes, independently recomputing price return, fixed original neutral-band class, stored prediction, three-class Brier and observable event chronology. All 693 linked; **zero** duplicate prediction IDs among evaluated learning events, **zero** internal return/class/Brier/match mismatches and **zero** observed chronology inversions. This is internal stored-source validation, **not** official exchange verification.

- All-time forward eligible: **279/693 = 40.26%**, 3-class Brier **0.6529411772984456**; v1.0 **69/208**, v1.1 **210/485**.
- Real down = 266; called down = 80; correct down = 35, precision **43.75%**, recall **13.16%**, false down = 45, missed down = 231.
- Real up = 139; called up = 107; correct up = 21, precision **19.63%**, recall **15.11%**, false up = 86, missed up = 118. Flat class correctly called: 223.
- Same-original-event reference comparison still 275/681 model vs 282/681 baseline; 0/40 groups meet 120 independent targets / 20 observed days. The old 2,520 historical test targets and the previously scored research shadow 20 remain **used** and cannot be relabeled as an untouched final confirmation.

## Status, bounded follow-up

Research-only evidence record on the existing PR #149 branch: **zero new model hypotheses / hyperparameter trials, zero research model changes, zero production commits, zero retrospective alterations, zero eligible new outcomes, zero promotion**. The existing diagnostics patch can only explain **future** failed asset checks if independently reviewed and merged; it is not proof of a repaired Pages deployment. Retain `timing_utility=not_proven`. External exchange-origin bars, actionable bid/ask, real user receipt, after-cost paper-trading edge and unused later confirmation remain absent. No strict-green, source/venue, historical loss, orders, account/secret, schedule or other monitor changes are authorized.
