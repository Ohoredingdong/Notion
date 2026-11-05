---
name: stock-radar-validation
description: Safely implement and verify investment radar data, AI direction probabilities, due-diligence decisions, finance updates, and GitHub Actions without fabricating results or interrupting production.
---

# Investment radar validation

- Canonical page: \`stock-value-radar.html\`; runtime: \`assets/stock-radar-flow-v2.js\` + \`assets/stock-radar-clean-bridge.js\`.
- Production source files are generated root JSON/JSONL (e.g. \`stock-opportunity-data.json\`, \`stock-direction-forecast.json\`, \`stock-investment-cases.json\`, \`stock-forecast-learning.json\`). The \`.github/workflows/stock-forecasts.yml\`, \`update-stock-opportunities.yml\` and connected publishers can write to main; **do not disable, retarget, or require PR CI for scheduled data publication**.
- Treat source/issued/observed/target/expires timestamps and market sessions separately. An old or no-call forecast is not live; a missing ticker is not an implied neutral/positive signal.
- AI \`P(up/flat/down)\` is a research classification, not expected price appreciation or buy-success probability. Independently validated official reporting, cash flow, earnings, valuation, downside, debt, macro/policy and liquidity are separate investment evidence gates.
- Before displaying investment conclusions, validate symbol, currency, price session, forecast period and source version alignment. Fail closed for missing/contradictory inputs. No arbitrary probability uplift, invented target, or synthetic price/time fallback.
- For changes to live financial pipelines run **existing** \`scripts/test_stock_forecasts.py\`, \`scripts/test_stock_forecast_wiring.cjs\`, \`scripts/test_stock_evidence_review.cjs\`, provenance/rollback tests where relevant, and current browser tests. Do not change an established audit threshold to get a green build.
- For UI changes validate market strip, four index cards, sentiment toggle, company selection, chart intervals, 4-question investment verdict, explicit no-signal messaging, uncertainty disclosures and source status.
- Check production schedule and workflow logs independently of the UI refresh interval; GitHub cron is best-effort and may delay or drop runs. Keep immutable issued records and existing publication conflict checks.
- Preserve screenshots/evidence; open a draft PR. Never deploy or merge without user approval.
