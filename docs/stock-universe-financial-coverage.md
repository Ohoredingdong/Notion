# Official issuer catalogue and financial coverage

## Identity repair — 2026-11-05

The original 8,546-row catalogue was not a verified 8,546-issuer dataset. Its Korean parser removed alphabetic characters: `0001A0` (덕양에너젠) became `000010`, and `0009K0` (에임드바이오) became `000090`. This could collapse different listings or attach financial records to the wrong company. Do not relabel that old catalogue or infer corrected codes from its altered keys.

The corrected collector re-fetches the official KRX and Nasdaq sources. Korean six-character codes retain letters and numeric leading zeroes; conflicting company identities fail validation. A fresh catalogue carries `identifier_policy: kr-six-character-alphanumeric-v2`. The recovered total must be taken from the actual new collection, not forced back to 8,546.

Official reference examples:

- [DART: 덕양에너젠, 0001A0](https://englishdart.fss.or.kr/dsbc001/selectPopup.ax?selectKey=01516933)
- [Samsung Securities: 에임드바이오, 0009K0](https://www.samsungpop.com/ux/kor/customer/notice/notice/noticeViewContent.do?MenuSeqNo=23272)

## What can appear as verified financial information

A displayable financial record must have `identity_policy: official-issuer-identity-v2` and `identity_verified: true`.

For Korea, the collector verifies the exact official ticker, DART corporation code, and catalogue/company name. Ambiguous historical code reuse is never resolved by taking the last XML row. A bounded company-profile request can confirm a changed formal name or listing name. Financial responses must preserve the requested official stock/corporation identity. Records carry `corp_code`, official name, identity evidence, `rcept_no`, and a direct DART filing link.

For the United States, the official ticker-to-CIK map must agree with the CIK inside the actual SEC companyfacts response. Records carry the CIK and identity evidence. A missing or mismatched identity cannot receive fabricated values.

Previous rows without this evidence move to `data-quarantine/stock-financial-coverage.json`. The archive preserves each original record, previous key, reason, source timestamp and SHA-256. It is forensic evidence only: the UI must not load it, promote it, or automatically re-key its numbers. Previously verified rows survive a temporary source failure with their original observation time and an explicit refresh error.

## Selected published accounts, not full financial statements

The DART multi-company endpoint supplies selected income and balance-sheet accounts. The response reports actual currency, filing, consolidation basis and period. Consolidated and separate statements, different currencies, reporting periods and current/cumulative income amounts are not mixed.

The collector requests ended reporting periods in chronological order and falls back only when a newer report has not been published. For example, January collection can use the previous year's Q3 while the annual report is pending. Period comparisons use dates; lexical `H1`/`Q1` ordering is prohibited.

Cash flow, capital expenditure, free cash flow and EPS remain unavailable when not obtained from a matching official report. Every record says `full_financial_statements: false`, lists `missing_metrics`, and identifies the selected-account scope. SEC FCF is calculated only from operating cash flow and capex for the identical reporting interval. Reported accounts are not analyst forecast EPS, current prices, an investment recommendation, or an AI success probability.

Authoritative API contracts:

- [DART corporation-code mapping](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018)
- [DART company profile](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019002)
- [DART multi-company major accounts](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS002&apiId=2019017)

## Independent source configuration and truthful refresh state

Korean DART requests use `DART_API_KEY` (Actions secret). They use an honest project User-Agent independently of SEC settings, with an optional `DART_USER_AGENT` override.

SEC requests require `SEC_USER_AGENT` identifying the real organization and a monitored contact email. Do not invent contact details or copy a private address into a public file. Until legitimately configured, US requests are explicitly skipped. An existing 403 may remain even after configuration; the code must not bypass provider access controls.

Historical coverage and this run's results are independent:

- `financial_available`: identity-verified rows retained in the current snapshot.
- `run.US` / `run.KR`: actually attempted, available, blocked, provider-error, identity-error and no-report counts for this execution.
- `refresh_status`: `success`, `partial`, `blocked`, or `not_requested`.
- `current_run_failed`: a source/configuration/identity error occurred. The CLI and workflow report failure even if historical rows remain.
- `last_successful_observation_at`: the most recent actual observation among verified financial rows, not the JSON build time.
- `provider_readiness`: configuration readiness, not a guarantee of provider access.

## Collection and publication

`stock-financial-coverage.yml` is the sole publisher of the coherent official catalogue and financial snapshot. It runs the regression tests, re-fetches a complete catalogue, performs bounded financial collection, validates every financial identity, preserves quarantine, and commits the aligned files together. If sources or collector inputs changed during the run, it refuses a stale publication. A failed provider refresh may publish an explicit failure state with preserved trustworthy historical rows, but the workflow remains failed.

The catalogue-only workflow is a manual, read-only diagnostic that uploads its result as an artifact. It does not independently change the published financial universe.

The initial repair can be started with a separate reviewed commit to `fix/radar-integrity-20261105` changing `.github/radar-financial-recovery-request.json`:

```json
{"kr_batch":3000,"us_batch":0,"reason":"official-issuer-identity-recovery"}
```

Ordinary code/test commits do not launch heavy financial collectors. Explicit workflow dispatch allows a Korean budget of 0–3,000 and US budget of 0–120; the ordinary maintenance schedule remains bounded. Root handles the recovery marker, repository publication, final CI, merge and deployed-page verification.

Run before publication:

```bash
python -m unittest scripts.test_stock_universe_catalog scripts.test_stock_financial_coverage -v
python -m scripts.validate_stock_financial_coverage
```

The second command must use freshly collected, aligned sources. It is expected to reject the historical broken snapshot before recovery. No test fixture may be written into production data.
