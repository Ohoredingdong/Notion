# Forecast horizon clarity research — 2026-11-04

Preregistered before code in issue #107; operating main fixed to
147af2254a4fc8cdf0640a5b40bf4a18591f03c8.
Each forecast classifies start-of-target OPEN to target-end CLOSE
with its fixed neutral band. It does not classify prior close
to current close. The existing UI outcomes table does not explain
this critical difference, especially on gap-down trading sessions.
Nov 3, 2026 KR archived stock predictions illustrate this difference;
Yonhap and Chosun reported same-day KRX-index and selected stock closes.
Those articles are not independent venue minute bars or order books.

RED: Synthetic UI negative controls require target open-to-close
horizon wording and explicit non-equivalence to prior close. Keep
everything else unchanged. If RED reproduces, one narrow GREEN adds
only the two adjacent explanatory notes to the existing main renderer.

No new forecasts, price substitution, model adjustment, threshold changes,
strict-green action, orders, secrets, workflow schedule, user receipt
claims, or completion notice. Research branch is unmerged HOLD until
fresh-main / browser / exact deployed JS verification and reconciliation
with separate draft #102.
