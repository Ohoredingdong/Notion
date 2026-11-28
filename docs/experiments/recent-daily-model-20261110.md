# Recent daily model experiment — preregistered 2026-11-10

Pinned main: `9814e420317ba7a3506583b4370b3ea9184a2196`.
User requests improved actual accuracy, not a rewritten scoreboard. No 100% guarantee.
Read acceptance, direction-specialists and bounded-autopilot policies. Existing PRs 82/140/145/146 and supplied experiment notes were checked; this is a model trial, not another audit-only repair.

## Observed motivation (not proof of causation)
The current daily predictor reuses the model fitted on the first 60% of a five-year history after its 20% calibration and 20% historical test. In the fixed current JSON, several 2026-11-10 forecasts have trained_through dates in November 2024 and calibrated_through dates in November 2025. New input prices do not make those coefficients recently trained. Frozen forward score remains 96/256 (37.5%); it must never be rewritten. Training-age reduction alone does not establish better forecasts.

## One fixed candidate; no hyperparameter search
Name: recent_daily_logistic_v1. Same 12 incumbent price features, same logistic C=0.2, same StandardScaler, same neutral bands, same next-exchange-session open-to-close target. Daily only; all 20 current daily symbols are requested, no choosing stocks by outcomes.
For each prediction origin, use only target_end strictly before that origin. Last 60 available origin sessions form calibration; at most the preceding 756 origin sessions form training. Purge training targets overlapping calibration origins. At least 500 training rows and 40 nonoverlapping calibration rows, all three training classes, and at least two calibration classes are required. Temperature calibration has the unchanged [0.5,5] bound; no fitting to future labels. Missing history is an explicit failed group, not a successful exclusion.

## Historical diagnostic fixed before results
Use the last 126 eligible daily targets in six fixed blocks of 21; refit once before each block. Later blocks may use earlier block outcomes only once they had resolved before that block's origin, which is ordinary sequential historical replay, not an untouched independent confirmation.
Compare identical targets with the original incumbent, its frozen training-frequency baseline, and the reviewed movement_then_direction recipe fitted/calibrated on the original chronological split. Report all requested groups, missing groups, per-direction recall/precision, accuracy, balanced accuracy, Brier/log loss and date-cluster diagnostics. No failed groups hidden. No changing the above recipe after seeing results. One recipe trial; repeated software repairs are counted separately.
These are calculations on currently retrieved Yahoo history, not point-in-time-vintage evidence, exchange-authenticated prices or newly published historical forecasts. Diagnostic predictions are not appended to the original ledger and have no backdated issuance time.

## Fresh research-only outputs
Where an actual future target remains valid after model fitting, freeze the new candidate and contemporaneous reference probabilities with real observation/receipt/issue times, original band, target, source/code/history/model hashes. Otherwise mark no_call. Preserve outputs in an isolated Actions artifact/research branch only. An artifact is not a human receipt or proved timely public delivery. No trading recommendation, strict-green override or automatic promotion.

## Decision and future gates
An engineering pass requires chronological/identity/preservation regressions. Historical improvement requires higher pooled accuracy, nonworse up/down recall, improved balanced accuracy and lower Brier/log loss versus the identical incumbent cohort; report every condition, do not relabel partial success. Even a historical pass authorizes only shadow research, not replacing the incumbent.
The existing four challengers, including movement_then_direction, retain all existing comparison thresholds. Any future promotion of this extra candidate requires separately recorded forward comparisons with all original candidates and baseline, >=120 nonoverlapping targets and >=20 observed days per symbol/mode, class/call counts and original direction/error gates; selection diagnostics must account for five total challengers (tail no larger than 0.05/10). Untouched confirmation, actual delivery/quotes/cost/risk remain mandatory for usefulness. No count pooling across symbols to satisfy those gates. No automatic promotion is implemented by this experiment.

## Safety and preservation
No original forecast/outcome/learning/source/policy/UI file modified. No original scores changed, no new training of existing online state, no order, paid service, account/auth/secret, separate monitor or other schedule changes. Real source failures remain failures. Production stays unchanged unless a separately reviewed and fully tested shadow-only integration is justified.
