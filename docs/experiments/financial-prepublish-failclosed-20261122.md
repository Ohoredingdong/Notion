# Financial refresh fail-closed publication gate — preregistered 2026-11-22

## Fixed source and reproduced failure (before code changes)
- Pinned main: `3d03eb7e2cebf6255babbf723111601eb9bfb3a1`. This research branch does not modify main, direction probabilities, original outcome ledger, or approval thresholds.
- Actual GitHub [Stock Official Financial Coverage #44863565739](https://github.com/Ohoredingdong/Notion/actions/runs/44863565739) (2026-11-21 03:55–03:57 UTC): the official catalogue refresh completed (8,580 identifiers); the financial collector reported US attempted=60, provider_errors=60, current_run_failed=true and refresh_status=partial. Validation of historical identities passed, *publication step succeeded*, Pages was requested, then the later final status step failed with `Current provider/identity verification failed`. This is a reproducible **post-publication failure gate** and not an acceptable verified full refresh.
- Resulting new catalogue includes CZZL, SONN and drops MERC, UTZ relative to older extended forecast; exact sets differ by 2 on each side despite equal 8,580 counts. [Strict accuracy audit #44902549594](https://github.com/Ohoredingdong/Notion/actions/runs/44902549594) correctly rejected `catalog_forecast_identity_set_mismatch`. See existing issue #137 comment 7063792575.
- Extended-coverage schedule `55 6 * * 1-5` does not generate a new bundle during the weekend. Financial-coverage cron is **configured** for `11 23 * * 1-5` (due Friday 23:11 UTC), but the actual scheduled run #44863565739 was **created Saturday 2026-11-21 03:55:52 UTC** and published around 03:57 UTC; do not substitute scheduled for observed execution time. The two cadences allow a changed catalog to outrun a prior forecast. This is a contributing mechanism; the US provider failure cause remains unverified.

## Single bounded engineering hypothesis (not a new model trial)
Move the *existing* `current_run_failed` failure gate to **before** committing/pushing a catalogue/financial snapshot. Preserve complete source/identity checks and historical statements. Failure must leave last verified published catalogue/financial bytes intact, surface a nonzero workflow result, and still upload failure evidence as the existing Actions artifact. On a full verified refresh, normal publishing is allowed. Do not suppress failure indicators or bypass an independent audit; no model retraining, shadow candidate, buying decision or order.

## Prespecified tests and exit conditions
1. A fixture with `current_run_failed=true` (even when historical `financial_available` is high) is rejected before any `git push` stage. Missing flag also fails closed; a genuine boolean false permits the gate only (not a claim of verified upstream feeds).
2. Structural regression checks prepublication ordering of the gate and confirms that the workflow artifact remains `if: always()`. The official identity/financial validator remains required.
3. Existing finance and full-universe regression suites must pass in PR CI. No operational promotion until independent review and externally observed post-change published snapshot verification. This test has no market data or new prospective predictions.
4. If tests cannot be run or indicate unintended side effects, hold draft and do not merge. Preserve every prior result, failed run and ledger. Future separate confirmation: observe a genuinely failed refresh held before publication, followed by a complete verified refresh and strict audit on the same snapshot.

## Experimental accounting
- New direction-model hypotheses this execution: **0**. Historic 2,520-target trial is already exhausted; old shadow 20 are not untouched.
- New operational safety hypothesis: **1**, one research branch; no threshold search.
- Untouched future direction-comparison window: unavailable; directional usefulness remains `not_proven`.

## Post-registration chronology correction
The schedule-versus-actual-start distinction above was corrected after the original preregistration commit (`9e322d934217741e15e09de2c5f919d59c593cf5`); the original remains accessible in Git history. No hypothesis, test threshold, date window, or original evidence was rewritten.
