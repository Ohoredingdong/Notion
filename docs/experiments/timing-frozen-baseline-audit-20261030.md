# Frozen baseline probability integrity — bounded audit experiment (2026-10-30)

## Fixed evidence and preregistration (before changing auditor)

- Base main commit: `99309ee385f3ac8b6b86fa47948f3032975c52d4` (source of code and immutable evidence for this trial).
- Contract: `docs/stock-timing-acceptance-20261029.md` and unchanged `docs/stock-direction-specialists.md` / `docs/stock-bounded-autopilot.md`.
- Original ledger: 77 rows, 56 unique future targets, 21 repeated issuances, eight overlapping windows excluded, 48 nonoverlapping; 12 future targets, six matured without stored results, 30 scored / 11 correct on two scored dates. Among 30: actual down 7 / hit 1, flat 15 / hit 9, up 8 / hit 1. All 57 stored outcomes internally recompute; this is not external venue-price proof.
- Frozen baseline probability fields exist on 36 ledger rows. All 36 currently have three finite, nonnegative, normalized values. Nothing in the read-only independent auditor's `validate` checks this optional frozen field, even though downstream `baseline_paired` uses it for model comparison. Source evidence SHA: ledger `b1af95894d1dd49ae7a0d86f19cda347d3200f08`, outcomes `2e4213bcca37c17a4e2feee327f702437e048b0b`, deliveries `51daccada19b8e8dc20160da9c3f82807ccbd7b1`.

## Falsifiable hypothesis and RED reproduction

A synthetic frozen forecast with an otherwise coherent probability vector but a deliberately invalid `frozen_baseline_probabilities` object (negative component, sum not 1, non-finite component or omitted class) will incorrectly pass the independent read-only audit. It must instead fail as evidence-integrity error; valid vectors and older forecasts without this optional field must keep the old path. These are **synthetic mutations**, not assertions of actual corrupt operational rows.

## Bounded, safety-preserving candidate fix

Add only optional baseline vector validation to `scripts/audit_stock_forecast_independent.py`, with negative-control tests in that auditor's self-tests. No retroactive creation of absent baseline probabilities; no rewriting old baselines, forecasts or outcomes; no model selection, weight change, calibration, comparison-gate reduction, recipient or trade assumption. The validator can check vector shape and numeric consistency, but **cannot authenticate a changed valid vector from an external immutable point-in-time feed**; leave that limitation explicit.

**Predeclared test procedure:** (1) branch-only RED failing synthetic negative controls before implementation; (2) GREEN same tests; (3) full independent audit/learning audit and existing forecast/direction/autopilot regression; (4) no main publication until temporary branch CI routing has been removed and relevant checks actually pass. Record failed trials, meaningful success and all action identifiers. Model family trial count: zero. Integrity hypothesis count: one. Never count synthetic tests, old 30 labels, GitHub publication or test success as timing usefulness.

## Acceptance contract remains blocked

Per group 120 nonoverlapping future targets and 20 days plus direction counts and superiority; post-user-receipt executable bid/ask and after-cost risk-adjusted prospective paper comparison; unused later holdout and independent reproduction; actual quote/notification delivery evidence. Current web snapshots are not human receipt. KRX/NXT/US venue/session separation and strict-green-1.0 unchanged. No live orders, key changes, subscriptions, new accounts or alteration of the other radar watchdog.

## Results

Not yet run at preregistration. Preserve the initial RED and all later results here without rewriting these hypotheses.
