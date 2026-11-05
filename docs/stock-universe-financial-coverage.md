# Stock universe: genuine financial statements and AI coverage

**Status (2026-11-05, initial tested feature-branch snapshot):** official issuer catalogue 8,546 (KR 2,617 / US 5,929). The SEC/DART collection has retrieved **2,579 Korean issuer records**, while US SEC mapping requests returned **403** from GitHub Actions. This is **partial coverage**, not 8,546 complete financial statements. The separate rotating AI research feed has 36 attempted names, including 21 valid future-dated research predictions at the observed time. Those predictions are not proven profitable or calibrated buy-success rates.

## Two independent datasets

- `stock-universe-catalog.json`: source-attributed listing directory (KRX KIND, Nasdaq Trader). Presence in the directory does not imply an actual operating company with a published financial report or a valid AI prediction. Exclusions for non-common shares/ETNs/SPACs may require follow-up.
- `stock-financial-coverage.json`: real, reported accounts with exact source and period, keyed by `KR:<6-digit>` or `US:<symbol>`. A missing record is **not collected yet**; `source_unavailable`/`source_not_configured` means no trusted data was obtained. Prior verified values are never replaced by temporary provider failures. DART multi-company API supplies selected reported accounts, **not the complete cash-flow statement**; absent FCF and EPS remain null. SEC uses companyfacts XBRL reporting periods and matching-year balance-sheet instant data; it is not analyst forecast EPS. Older filings are marked stale.
- `stock-extended-direction-forecast.json`: independent bounded price-only research. Only actually issued and unexpired target rows may show probabilities. No record, provider error, insufficient evidence, or an expired target must display **unavailable**, never a made-up percentage. Research confidence has not met real-money performance acceptance criteria.

## Real official provider source constraints

- Korea: DART `corpCode.xml` ZIP maps 6-digit ticker to 8-digit filing company code. Its `fnlttMultiAcnt.json` permits up to 100 issuers/request. Requires `DART_API_KEY` **Actions secret**. Earlier successful collection confirms the connected secret works in the feature-branch runner. The 38 remaining Korean listings require investigation of mapping, filing availability, and instrument type; zero-filled financials are prohibited.
- United States: the SEC officially supplies `company_tickers_exchange.json` and `data.sec.gov/api/xbrl/companyfacts/CIK...json`. GitHub Actions received **HTTP 403** for the SEC CIK mapping. Before enabling US collection, the repository owner must configure `SEC_USER_AGENT` in GitHub **Settings → Secrets and variables → Actions → Variables** to identify the organization **and a real monitored contact email** (never put contact details or credentials in public JavaScript). Even with a correct user agent, the SEC can continue blocking a cloud-hosted IP; approved alternative hosting or a licensed fundamental-data provider may be necessary. The collector now fails closed instead of repeatedly hammering a rejecting source.
- The SEC's public per-company companyfacts API and bulk ZIP differ in access patterns, permitted usage and download size. For genuinely concurrent coverage of many thousands of issuers, prefer a provider-authorized bulk ingestion service with suitable quotas; an ordinary GitHub Pages static frontend cannot fetch SEC XBRL directly due to CORS, nor train ~8,500 forecasts synchronously.

## Operational workflow

1. Run **Stock Official Financial Coverage** workflow on the feature branch (bounded requests and finance parser tests); existing valid records remain intact.
2. Run **Stock Extended Research Coverage** workflow independently; its underlying source/target tests prevent fictional predicted returns.
3. Run **Radar Universe, AI and News PR QA**: source-data safeguards, genuine browse/search, source/date explanations, mobile/desktop/Notion-sized iframe, no fabricated financials or prices.
4. Inspect source-provider failures and coverage counters. **Do not merge while critical provider coverage remains blocked** or describe unmodeled listings as AI complete.
5. After explicit user approval only: merge reviewed code, then verify production Pages and real Notion embed, GitHub financial-data Actions, and source timestamps.

## Why a 100% promise would be misleading

Some listed instruments do not have issuer financial statements under SEC companyfacts or DART in the same normalized form. Some companies have delayed, amended, foreign-currency or taxonomy-specific reports. AI `P(up)` is a time-bound **model estimate**, not a persistent field which remains valid after a market session ends; generating a number for every ticker without price-history eligibility and independent calibration would misrepresent its meaning. The widget must report exactly which issuers have current-source statements, a current research prediction, neither, or failed-source status.
