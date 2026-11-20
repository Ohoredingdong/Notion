# Read-only forward-cohort failure-mode audit — research plan

Recorded: 2026-11-14 (UTC); branch base **cd774513cfe8667eb4d83d5fd13b40dcdc315341**.
This is **an engineering diagnostic protocol, not a new model hypothesis**. The November 13 US daily outcomes were already visible before this plan; nothing here is an untouched, blinded confirmation or a prospective performance-registration claim.

## Known source and reason for bounded work
- Original operating files at the fixed commit: ledger blob `7eace60187c32cafa1bf10b628c2fd33c020de72`, outcomes `e102f7a9cc5b53dad00740d72abc49897c79d896`, learning events `f4f61b06a7f39450a263014a8dd0f8aae549c2dc`, public verification `814bd0cf4e80ffa390adb54f4c29a75b70252183`.
- The new twelve **US daily regular-session** targets run strictly from 2026-11-13 14:30 UTC to 2026-11-13 21:00 UTC. Outcomes were recorded on 2026-11-14 00:58 UTC. This is **one correlated market-date cohort**, not twelve independent observation days.
- Old eligible scores 166/404, new 170/416; original errors are never removed. Earlier research test on 2,520 old history targets and archive shadow 20 are already used and **not** available as fresh holdouts.
- Existing PR #146 protects original provenance, #147 documents failed daily retraining (worse up recall), #150 diagnoses prior KR missing-window cases. Do not duplicate those repairs, recalibrate probability thresholds, or reinterpret their evaluation data.
- Read existing acceptance, direction-specialists and bounded-autopilot documents without changing their gates. One candidate family experiment per run remains the maximum; **this run's new model hypotheses and refits are zero**.

## Frozen audit design and test budget
Only add a self-contained, read-only Node.js cohort **diagnostic** and synthetic regression tests. A single real-data audit of the already-observed, fixed US November 13 cohort plus one test workflow run is permitted. No hyperparameter trials, threshold adjustment, model selection, or new probabilistic prediction are authorized. Code may be corrected to make its invariant checks work, but every attempted correction must be explicit in CI/history. All methods must use exactly the probability vectors *already present in each original issued forecast*:
1. applied incumbent;
2. originally frozen training-frequency baseline;
3. originally frozen online-learning challenger;
4. movement_then_direction shadow;
5. balanced_linear shadow;
6. balanced_nonlinear shadow.

The cohort key is `market=US, mode=daily, target.start=2026-11-13T14:30:00+00:00, target.end=2026-11-13T21:00:00+00:00`. Join through the original `id` and the actual eligibility-learning IDs; include every original eligible US symbol in the cohort. Do not substitute current daily JSON model scores, recreated past challenger probabilities, corrected thresholds, price forecasts from news, or look-ahead OHLC.

For every candidate preserve: original direction/probabilities and original neutral band; class totals, directional calls/hits/missed/false calls, *separate* precision and recall with null on no calls; flat counts, Brier and log loss, actual date clusters, source-record fingerprints, publication chronology, and missing evidence. Independently recompute original price return/label/scoring. Reject duplicate IDs, absent/mismatched original target, label or score inconsistency, or outcome-before-target and learning-before-observation. Publication is not human notification; broker quotes/exchange-certified raw bars are absent.

## Evidence gate / stop conditions
This cohort cannot meet per-group 120 nonoverlapping future targets or 20 observation days. A method that only predicts flat or only down must be flagged as one-sided even if its raw cohort accuracy looks higher. Any candidate improvement on the already-seen date is **exploratory only**; do not promote or retune based on it. The earliest possible independent confirmation for already-frozen future forecasts requires a separate, unused subsequent period, sufficient samples, original eligibility and timing, both directions, and independent executable quote/cost/receipt validation. If an input fails, stop with a visible research-only failure, do not repair the original data, and leave operational models/strict-green/data monitors/orders untouched.

## Changes allowed
Only `scripts/research_forward_cohort_audit.cjs`, `scripts/test_research_forward_cohort_audit.cjs`, this note/result document, and a narrowly scoped research-branch Actions workflow may be added. Workflow must not publish main outputs or request secrets or live orders. Its success establishes diagnostics, **not timing utility**.
