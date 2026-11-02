# Current-main Stock Radar flow verification — bounded research, 2026-11-03 KST

## Preregistered scope and frozen evidence
- Repository `Ohoredingdong/Notion`; source baseline main `9c4451f3b5ee3f4cae175bbbf5f3d2e9443e6a5f`; original source test blob `acfcbb3b6c9407f2d89c7d36495d9773125b9a4c`.
- Acceptance blobs: `docs/stock-timing-acceptance-20261029.md` = `69526101025c0394b13a55bfb73b9be5240e5fca`, `docs/stock-direction-specialists.md` = `6d5498666cd6da4d4528c46a4f1cb911715e90bd`, `docs/stock-bounded-autopilot.md` = `a5176f6aa075c49a090e6a3ec01b64fb323420ed`.
- Unmodified financial inputs, forecast outcomes, acceptance thresholds, trading approvals and credentials. No orders, provider authentication, new models, retrospective signals or actual alert messages.
- Prior research-only flow run [41464395687](https://github.com/Ohoredingdong/Notion/actions/runs/41464395687) failed an obsolete market-card CSS selector; corrected follow-up [41465010579](https://github.com/Ohoredingdong/Notion/actions/runs/41465010579) reached a second obsolete detail-title selector and failed. It used an older HTML blob. The JavaScript flow/bridge blobs match current main; the current HTML/CSS blob `c96d8fd67ea16b7716704e7ffb2a500f36ed7e73` is NEW and not yet validated in the prior isolated suite. Existing main integrated browser checks [41470919332](https://github.com/Ohoredingdong/Notion/actions/runs/41470919332) are red at a legacy-neutral-home ID assertion, not proof that modern flow succeeds or fails.

## Single fixed hypothesis before this execution
In the current HTML/CSS build, the two failing assertions are obsolete element locations rather than missing market cards or ticker information. The unchanged bridge/flow JS renders four market index cards under `.fx-v5-markets.nr-market-grid` and renders the selected ticker explicitly in `.fx-detail-intro p` (adjacent to the company-name heading). Replace **only** those two test selectors, while preserving: exactly four market cards, ticker string equality, detail content presence, real chart, no page overflow, all navigation, scenarios, monitoring persistence, portfolio forms and no JS errors.

## Fixed test budget and falsification
One isolated push-triggered headless Chromium run against the pinned current-main HTML/JS and repository-saved JSON. All other assertions stay unchanged; no test skipping or success-criteria relaxation. If any further assertion fails, record the failure as RED and stop; **do not** merge, promote any model, or call deployment success predictive usefulness. A green run only supports that UI suite, not other failed legacy regression gates, real-time quotes, user notification receipt or after-cost investment performance. No additional candidate searches or repeated retesting in this trial.

## Outcome
Pending independent GitHub Actions run; this placeholder is not a success claim.
