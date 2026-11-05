# Investment Radar: full issuer search, extended AI coverage and global policy desk

Status: **feature branch, awaiting human approval; not deployed to production main**.

## 1. What is actually covered

| Layer | Scope | Meaning |
|---|---|---|
| Directory | Real KRX KIND KOSPI/KOSDAQ + Nasdaq Trader NASDAQ/other-exchange listings (SEC EDGAR fallback if US download fails) | Searchable **company name, symbol, exchange and source**. Does not guarantee price or financials. |
| Existing deep analysis | Tracked ~104 issuers with separately fetched original finance data | Income/cash/valuation/research data where available; incomplete items remain unavailable. |
| Core AI | Original separate `stock-direction-forecast.json` with prospective targets | Original independently audited experimental probabilities, never broker orders. |
| Extended AI | Separate `stock-extended-direction-forecast.json`, rotating up to 12 real-source issuer attempts per run | Some stocks have an active prospective prediction; the majority will show not yet researched or no-call. **Not complete real-time coverage of all ~8.5k listings**. |
| International / Korea / company news | Existing attributed RSS `news-link-data.json`, official macro `stock-market-context.json`, existing company-event and calendar data | Clearly labeled news *reports*, original URLs, publication time, stale data; no claimed verified price reaction or fabricated impact. |

## 2. Ingestion source and data provenance

- `scripts/build_stock_universe_catalog.py` reads the Nasdaq Trader symbol directory (NASDAQ-listed and other-exchange), and the KRX KIND market-specific company list; filters test issues/ETFs/obvious non-common instruments where identified.
- US fallback is SEC EDGAR `company_tickers_exchange.json` **only if the Nasdaq directory is too small**. SEC cautions that its ticker associations are not complete/guaranteed.
- A missing/blocked provider produces an explicit `partial` result and source error; a total response below the minimum **fails without publishing or truncating the existing file**.
- The source list is a catalogue of **listed instruments after documented filters**, not a count of all world public companies or every eligible common stock; unusual symbols, funds and some securities are excluded.
- `stock-universe-catalog.json` embeds source names/URLs, collection time, per-country counts and errors. This is search-only — do not merge its rows with `stock-opportunity-data.json` and infer price, EPS or cash flow.

## 3. Forecast coverage and limitations

- `scripts/run_stock_extended_forecasts.py` processes **at most 16, normally 12** candidate symbols per invocation and avoids overloading rate-limited price providers.
- Every prediction requires actual provider OHLC + the existing time-safe `stock_forecast_model` model. A failed/expired session yields `no_call`, never a made-up probability. The current stored signal remains until its target expires if a later provider request transiently fails.
- Tracked companies are prioritized while round-robin progress gradually adds new searchable issuers. This **cannot supply simultaneously up-to-date forecasts for all 8,546 names** under the current free provider/GitHub runner constraints. An expanded paid licensed quote/price warehouse plus queue/worker infrastructure would be needed for that service-level objective.
- The extended feed deliberately does not alter the immutable core forecast ledger, core accuracy audit, existing 104-name fundamentals or automatically execute trades.
- The front end combines the two sources only when a genuine signed future target and proper probability distribution are present. All percentages are directional research, not buy success or realized returns.

## 4. Production automation only after approval

- `.github/workflows/update-stock-universe-catalog.yml`: daily official listing refresh, parser tests, minimum count/source validation, fail-closed publication. It writes **only its declared JSON**.
- `.github/workflows/stock-extended-coverage.yml`: bounded batch research during defined UTC windows, integrity tests, publication of **only the separate extended JSON**.
- On this feature branch, `push` triggers collect **only into that branch**. After approved merge to `main`, their scheduled jobs can update the declared files on main using the existing GitHub Pages data publication pattern; production core forecast Actions are untouched.
- The build/CI relies on GitHub scheduled events, which may be delayed or omitted. Browser refresh retrieves newly published snapshots; it does not cause new analysis by itself.
- No PR automatic merge, Pages source change, branch protection modification, backup deletion, data reset, or secrets publication.

## 5. UI and risk disclosures

- Canonical `stock-value-radar.html`: existing home, fear/greed and detail CSS remain intact.
- The "AI 종목" screen now contains official stock directory search, including companies **not** in the 104-name fundamentals table; unknown companies open an explicit information-only preview.
- Existing navigation's news icon opens a compact `fx-world-page`: sourced macro cards, domestic/global news columns, company/cross-enterprise events and forthcoming economic calendar.
- RSS headline discovery is **not** proof of an event or a causal market reaction; open the original cited article, official filing and policy release before trading.
- Desktop, mobile and a local Notion-sized iframe are validated; a real linked Notion workspace has not yet been opened.

## 6. Validation and rollout gate

Run unit tests:
```bash
python -m unittest scripts.test_stock_universe_catalog scripts.test_stock_extended_forecasts -v
node --check assets/stock-catalog-ui.js
node --check assets/stock-world-brief.js
node scripts/test_stock_evidence_review.cjs
node scripts/test_stock_forecast_wiring.cjs
```

In CI, serve the branch locally and run `scripts/test_stock_universe_browser.py`, existing `scripts/test_stock_detail_v6.py`, and `scripts/compare_radar_before_after.py` with a read-only checkout of the original `main`. Preserve screenshot diffs and all failing traces.

**Only after user approval:** review the PR diff and tests, confirm existing finance workflows are healthy, merge without rewriting older financial source data, verify new catalog and extended forecast jobs, check public Pages and source freshness, then test real Notion embeds. If any production regression appears, roll back code to the approved baseline without deleting financial history.
