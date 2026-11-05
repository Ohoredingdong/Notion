# Prospective quote and cost paper evidence — 2026-11-05

## Preregistration

This hypothesis and the controls below were written before implementation in
this session. The machine-readable registration uses the actual first-run time;
it is never backdated to a document's date. One engineering experiment; zero new
model recipes, parameter searches or model promotions.
The binding timing, direction and strict-green acceptance policies are unchanged.

The existing entry observer measures later daily closes against an earlier saved
reference and subtracts an explicitly assumed 30bp cost. This is correctly
labelled a price observation; it cannot measure an entry after a person receives
a signal. A stored reference of 100, subsequent buy offer of 110 and exit bid of
105 gives a positive reference-price observation and a losing quote-based paper
round trip. This distinction is the predeclared test case, not a claim of a new
live-price defect or predictive improvement.

## Bounded implementation

Add a separate orderless experiment with immutable rules and append-only plans.
Register only first-issued, already-public forecasts whose target has not started;
never reconstruct a plan for a past target. Index levels are not tradeable shares
and are excluded. A direction of up selects a hypothetical long position; flat
and down select cash. There is no short sale. Compare on the same available
quote pair with cash, always-long and the direction of the already-frozen
frequency baseline, using the same one-share maximum position and initial
capital. Missing historical baseline vectors stay missing.

Entry is the first received regular-session quote at or after target start and
within 60 seconds. Exit is the first quote in the fixed window from 60 seconds
before target end through target end. A daily close needs a pre-close quote:
this module does not turn an
after-hours quote into a regular-session fill. Quotes must follow an actual
human receipt, identify the same symbol, market, currency and venue, have usable
sizes, have observation-to-receipt latency no more than 5 seconds and have spread
no more than 50bp. Quotes at the boundaries must be observed contemporaneously;
delayed historical OHLC does not qualify. A bad first entry quote cancels the
entry; the evaluator must not search for a more profitable replacement. A bad or
missing exit remains unresolved, not a zero-return success or assumed stop fill.

Transaction fee/tax schedules, when supplied, must be frozen into the plan before
target start with an identified source and effective dates. Slippage is an
explicit, preregistered assumption; it is never relabelled measured. No schedule,
receipt, quote, size, plan-publication proof or fill is manufactured. Missing
evidence remains visible in every plan's result. Declared external evidence can
be checked for arithmetic and chronology here; this module does not authenticate
an exchange, broker, notification provider or actual execution.

The initial installation has no executable-quote, human-receipt or fee adapter.
`timing_utility` therefore remains `not_proven`, and no completion notification,
buy approval or order can result. Even a calculable paper return cannot by itself
establish actual fillability, realised slippage, capital/risk-matched superiority
or the independent follow-up requirements in the original acceptance contract.

## Independent frozen-candidate report

Separately recalculate the recorded candidate probabilities against the existing
independently selected future outcomes. Report each candidate and incumbent on
its identical cohort, class-wise calls/misses/false calls, proper probability
losses, per-group counts, absent candidate coverage and a source fingerprint.
Do not refit, choose a winner, create probabilities for old records, change the
four-candidate catalogue or reuse these observations as an untouched confirmation
block. Existing candidate eligibility and promotion gates stay unchanged.

## Predeclared verification

- The 100/110/105 control must lose after the buy offer, even though the old
  reference-price observation rises; entry uses ask and exit uses bid.
- Fees, tax and assumed slippage must reduce proceeds with dimensional arithmetic;
  a perfect prediction is not a cost-free trade.
- Website checks must not satisfy human receipt; missing, late or future evidence,
  bad quote identity/size/spread, changed plan inputs, mismatched policy and
  retroactive registration must fail closed.
- Repeated runs preserve policy, plan and original forecast/answer bytes; historical
  targets remain ineligible and no execution evidence file is created.
- Fixed candidate probability fixtures must match a separately calculated
  confusion matrix and Brier/log-loss; missing vectors cannot be backfilled.
- Run the existing independent stored-price auditor, directional/autopilot
  regressions and the new controls. Report actual immutable input counts and
  unfilled evidence requirements without claiming new predictive success.

## Integration

The bounded controller stages the five paper outputs with its existing transaction.
The publisher copies them with the matching forecast and learning bundle.
Optional external execution evidence and cost schedules are read-only inputs;
they are not invented or sent to a provider. A scheduled research run can register
new future plans and re-evaluate supplied evidence, but this does not create a new
automation or a quote/notification connection.

The existing publication workflow now also verifies the paper policy and plan
files after their public build. `verify_stock_forecast_public.py --paper-only`
requires each actual HTTP body to equal the corresponding local bytes exactly,
then records the observation time in the separate append-only
`stock-forecast-paper-publication-verifications.jsonl`. The original policy,
plans, forecasts and answers are not rewritten. The same bundle publisher
preserves this proof ledger and recalculates diagnostics against merged evidence.
Each forecast cycle requests one public build: initial bundle publication,
build, forecast check, paper check against that same published snapshot, then
one publication preserving both proof ledgers. New plans registered during that
last publication, and its updated diagnostics, wait for the next scheduled
public build. They remain pending until the actual public check; a late check
cannot establish before-target publication. This intentional delay avoids two
extra build requests per cycle. No additional automation is created.

The existing news workflow requests a public build only outside the exact UTC
research window used by the forecast workflow. During that window the existing
news-completion trigger delegates publication to the forecast workflow. The
schedule is best effort and does not establish a real-time delivery guarantee.
GitHub documents a soft limit of 10 Pages builds per hour for this publishing
mode; there is no change to a custom Pages deployment system. Source:
[GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

A first public check at or after target start is retained with
`public_before_target_verified: false`; it cannot be backdated or turned into an
eligible earlier publication. A valid before-target check can satisfy only the
plan-publication requirement. The evaluator still requires a real human receipt
after that check, executable quotes and a previously frozen cost schedule.
Publication telemetry creates zero human receipts, orders, quotes or fills.

Results are recorded after the fixed tests and replay below; any implementation
failures are retained as engineering findings, not additional model trials.

## Executed local verification and frozen-data replay

At the actual first run, 2026-11-05 10:59:37 UTC, the separate policy and 16
future-target plans were registered. All 16 were `awaiting_execution_evidence`:
there was no real receipt, executable quote, public-plan proof or preregistered
fee schedule. This is registration, not a simulated fill or successful strategy.
A second run created zero duplicate plans and preserved policy/plan bytes.
The forecast/answer/publication/learning ledgers are byte-identical to the input
checkout. Each report includes the three original evidence-file SHA-256 values;
optional receipt/quote/cost input hashes are null when absent.

The existing independent auditor selected 132 non-overlapping, already-public
future observations from 199 frozen records and 165 stored outcomes. The applied
model remained 41/132 correct. The independent paired calculations were:

| Frozen variant | Paired cases | Correct | Incumbent correct on the same cases | Brier improvement vs incumbent |
| --- | ---: | ---: | ---: | ---: |
| Adaptive | 120 | 38 | 37 | -0.013046 |
| Balanced linear | 114 | 35 | 34 | +0.027012 |
| Balanced nonlinear | 114 | 35 | 34 | +0.017035 |
| Movement then direction | 114 | 34 | 34 | -0.005278 |
| Frozen frequency baseline | 120 | 37 | 37 | +0.042446 |

Positive Brier improvement means lower probability error in that descriptive
cohort. These cohorts differ, so this table is not a ranking across candidates.
Every variant had zero of 24 evaluated groups at even the unchanged 120-target,
20-day count requirement. Directional superiority, provider authentication,
execution, after-cost benefit and an untouched follow-up are not established.
No model was refitted, selected or promoted, and no old probability was created.

Validation commands and results:

- `python -m unittest discover -s scripts -p 'test_stock_forecast_paper.py'`: 31 controls passed, including the independently fixed 100/110/105 calculation,
  same-cohort candidate comparison, missing evidence, public-vs-human receipt,
  false timestamps, immutable rules, and a partial-copy rollback of paper files.
- `python -m unittest discover -s scripts -p 'test_stock_autopilot.py'`: 27 passed.
- `python -m unittest discover -s scripts -p 'test_stock_forecast_directions.py'`: 24 passed.
- `python -m unittest discover -s scripts -p 'test_stock_timing_transaction_rollback.py'`: 4 passed.
- `python scripts/audit_stock_forecast_independent.py --self-test`: 19 passed.
- `python scripts/stock_forecast_paper.py`: real stored-evidence replay completed,
  status `not_proven`, zero quote-based paper returns, no input mutation.

One initial rollback-only regression stopped before its intended injected copy
failure because its intentionally incomplete synthetic ledger reached the newly
added auditor. That test already mocked the old auditor; its scope was retained
by also mocking the new audit result. Production audit rules were not relaxed.
A separate new test verifies rollback of actual new paper-output paths.

No claim is made here that these local checks are a completed GitHub Actions run,
a public deployment, externally authenticated quote receipt or predictive gain.

## Publication-connection verification

After inspection identified the missing plan-publication connection, 11
additional controls were added to the existing paper suite. All 42 paper tests,
27 controller tests, 24 direction tests, 4 transaction rollback tests and 19
independent-auditor controls passed (116 total). The additional controls cover
exact-byte comparison, HTTP failures, timestamps taken after completed fetches,
idempotent append-only proof retention, late-proof ineligibility, a rehashed
false before-target flag, concurrent local changes, receipt chronology, optional
ledger fallback, and the continuing `not_proven` result without execution data.
The UI review separately passed its 10 issuer-identity controls and canonical
runtime/feed syntax contract; those are not paper-strategy evidence.

The local real-data replay has zero actual public-plan checks until the deployed
workflow observes the public URL. Its empty proof ledger is an explicitly empty
input, not proof of delivery. Existing 16 plans have no frozen cost schedule;
later acquisition of a fee feed cannot rewrite those plans. Only new prospective
plans registered with that schedule could satisfy the cost requirement.
