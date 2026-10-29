# Independent learning-event chronology gate — experiment 2026-10-30

Status: preregistered research-only hypothesis, before test or code changes. Frozen main: `010128112855f816cfec4ca5fd72d5af0666ca48`. No model or threshold trials.

## Hypothesis and failure mode
The existing independent read-only evidence audit checks immutable forecasts, outcomes, publication chronology, and outcome arithmetic. Its interface reads only those three record streams; learning-event history/state are checked by the same pipeline controller, not by the standalone independent audit workflow. A synthetic `learn_after_score` row with an already-used event key, a mismatched direction, a label available after learning, or an event absent from the frozen ledger could therefore leave the independent evidence job green. This is an **independent-evidence coverage gap**, not proof that the six existing learning records are wrong or that the controller has failed.

## Predeclared one-attempt fix
Add a separate standard-library-only, read-only learning-event evidence verifier invoked by the independent audit workflow. Verify each already-stored learning event against the frozen prediction/outcome/public records, immutable target key and learned state: event ID/key uniqueness; forecast and outcome existence; original group and outcome class; outcome availability only after target end; learning never before the actual outcome and timely public snapshot; no future timestamps as of the audit cutoff; training-event keys and update counts reconciled. Preserve older model reports and all source rows. Fail closed on detected inconsistency, without taking orders or changing a state file.

Synthetic negative controls: duplicate event key, wrong outcome label, learning before outcome, missing/unknown forecast, forged fingerprint; a valid reference fixture must pass. Original audit + current immutable repository data must remain unchanged. No retroactive candidate outcomes or baseline probabilities.

## Evidence and interpretation
Pinned at preregistration: 53 ledger rows, 21 observed outcomes, 12 publicly verified response snapshots, 6 learn-after-score events, 6 learning state updates. 6 independently eligible scored results, 3 correct, all 3 actual down moves missed, no actual up examples. `movement_then_direction` is still a shadow candidate on 6 frozen forecasts, with no eligible paired future outcomes.

This engineering check cannot prove exchange prices, notification receipt, post-cost fills, model skill, or timing usefulness. A diagnostic may be merged only if synthetic negative controls, the prior independent arithmetic audit, and available regression tests pass on a research branch; otherwise leave main untouched. Trial accounting: 1 preregistered integrity hypothesis; 0 model/hyperparameter candidates. If test tooling cannot run, keep the PR unmerged and record the blocker.

## Existing work not duplicated
PR #35 already enforces staged learning safety *within the producer*; PR #38 audits all existing outcome arithmetic; PR #39 validates shadow probability distributions; PR #41 exposes evidence timestamp provenance. This experiment verifies learning events independently, without loosening those checks.
