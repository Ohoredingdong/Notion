# Codex safe development & PR procedure

**Operational boundary:** this documentation and the accompanying PR workflow live on a feature branch. No Pages source, `main` protections, scheduled stock publishers or financial files are changed by adopting this PR alone.

## Day-to-day
1. Create a branch from the current `main`: `codex/<task>-YYYYMMDD`. Inspect only the relevant project modules and their tests.
2. Record requirements and baseline URL/screenshots. Use the current approved iOS visual contract, preserve localStorage IDs, JSON schemas, and live data provenance.
3. Implement small edits. Use no production writes or fake data; for a data schema migration, obtain approval and prepare a reversible plan.
4. Run preflight and source tests locally when possible. The PR workflow runs syntax checks, the existing finance/radar tests, browser checks, and baseline/candidate screenshot comparisons when relevant.
5. Review PR artifacts: desktop, mobile, Notion iframe, changed-pixel report and browser errors. Inspect user-visible differences against the approved reference; green tests do not automatically approve a redesign.
6. Open a **draft PR**, resolve regressions, and include a reviewer checklist. Do not merge until the user explicitly approves.
7. Only after approval: verify code checks, confirm financial data writers still succeed, take a rollback SHA, merge approved changes, then validate live Pages deployment + data freshness; report any deviation honestly.

## Existing production architecture
- Main directly receives writes from forecast, opportunities, filings, macro, sentiment, news and other timed workflows.
- GitHub Pages builds from main changes (both code and data). An ordinary push from these Actions can generate a Pages build without a PR.
- PR-only validation uses **read-only** permissions, changes no branch protection, triggers no Pages deploy, and must never write to live financial snapshots.
- To *enforce* "no failed code may reach main", a future **separately approved** change to branch protection/rulesets and/or a dedicated deployment source is required. Until then, CI reports a result but cannot physically block users/apps with write permissions from pushing main.

## Suggested PR description
- Requested change; approved screenshot / user requirement
- Baseline commit and exact changed paths
- Data/automation impact (read-only; no schema migration, or explicitly approved migration)
- Tests actually run: command, result, run URL
- Before/after screenshots: desktop, mobile and Notion embed; unexpected pixel changes explained
- Known failing or unverified checks (never marked green)
- Rollback approach and **approval required before merge/deploy**

## Smoke/check commands
```bash
python scripts/codex_pr_preflight.py --self-test
python scripts/codex_pr_preflight.py --base origin/main --out pr-checks/changes.json
node --check assets/stock-radar-flow-v2.js
node --check assets/stock-radar-clean-bridge.js
node scripts/test_stock_evidence_review.cjs
node scripts/test_stock_forecast_wiring.cjs
python scripts/test_stock_detail_v6.py            # requires local HTTP server on :8765 + Playwright
python scripts/test_stock_radar_canonical_browser.py # same server
```

PR CI uses two local HTTP servers for before/after visual comparison and a unified, genuine repository data snapshot during comparison. It does not alter or regenerate persisted financial data. A captured screenshot is test evidence, **not** a substitute for function or source verification.

## Known legacy checks
As of 2026-11-05, `test-stock-radar-integration.yml` and `test-stock-decisions-ui.yml` still exercise obsolete `#nr-market-overview`, `#nr-home-alerts` and v7/v8-style navigation on the current V5 page. `test-stock-neutral-ui.yml` has a separate browser timeout. These are **unresolved red tests**, not waived or "passed". Their modernization belongs in a scoped follow-up PR; do not silently weaken assertions. Current V5 detail and canonical-browser tests are reusable immediately.
