# Outcome-claimed public time consistency — preregistered research experiment (2026-10-30)

Frozen main: `6bc1ea2cc2105f4f89e52cfb9dbc79a6dc4369be`. Scope: read-only audit and synthetic unit fixture; zero forecast or model experiments. Policy: timing-utility-acceptance-1.0. This is not confirmation of timing usefulness.

## Pre-change hypothesis

The independent audit reconstructs the first verified public snapshot from the immutable deliveries ledger for scoring, but may not check the *separate* `delivery_verified_at` timestamp copied into each observed outcome. A synthetic outcome with a forged earlier `delivery_verified_at`, while its genuine public snapshot remains later, may still be reported `ledger_arithmetic_consistent`. The copied timestamp is public HTML verification, NEVER evidence that a person received an alert. This is a possible consistency/audit-display vulnerability, not evidence of real tampering or live-delivery failure.

## One bounded red/green test

1. Using only synthetic intraday rows and an independently named, already-existing public snapshot, reproduce acceptance of a forged earlier outcome `delivery_verified_at` with otherwise correct 3-class probabilities, neutral band, return, Brier and chronology. Require that the auditor reports `integrity_errors` for an altered stated public timestamp. Record red CI failure before production patch.
2. Add a narrow read-only guard for observed outcomes **when the public-time copy field is present**, checking its timestamp against the earliest valid public verification for that original prediction ID. Historical records lacking the optional copy retain existing evaluation behaviour; no human receipt assertion is introduced. Leave the canonical public-time gate unchanged. Never relabel existing forecasts/outcomes or backfill missing fields.
3. Execute audit self-tests, existing untouched actual 53 ledger/27 observed outcomes/13 public verification records (12 eligible, 6 correct), independent learning-event audit, existing forecast regression where feasible; green branch CI required. Report zero model promotions, zero new candidate tests, zero adjustments of evaluation gates.
4. Preserve the original producer, forecasts, model, strict-green controls, raw market prices, attempts, credentials and unrelated workflows. Merge only if the baseline remains arithmetically consistent and the added synthetic negative test passes. Main independent audit must subsequently pass.

## Limits and accounting

First human receipt, exchange candles/quotes, post-cost execution and untouched prospective post-selection blocks remain unverified. No claim of all-market timing usefulness or completion alert. One audit hypothesis and one synthetic negative fixture; failed attempts and actual actions IDs are to be appended after execution. If a failure cannot be resolved safely, leave branch unmerged.
