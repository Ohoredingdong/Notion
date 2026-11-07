# Development environment inventory — 2026-11-05

Scope: **Ohoredingdong/Notion** at main, with a separate unmerged Codex safety branch. Repository listing and read-only GitHub Actions evidence; this audit does not claim that every feature has passed runtime testing.

## Verified structure

- GitHub repository: public static widget site; default branch **main**. At inspection, GitHub branch metadata returned protected=false and repository rulesets returned **0**.
- 167 root entries, 133 scripts, 45 direct assets, 38 workflow YAMLs and numerous root data JSON/JSONL files (counts reflect inspection time).
- The site uses GitHub Pages deployments on main changes, including changes from workflows that commit refreshed data. **Never treat a passing PR status as an enforced deployment policy**.
- There are active feature, research and older design branches in workflow logs, but no branch naming/review convention was enforced by repository protection.

## Automation inventory (all 38 workflow definitions inspected)

| Group | Workflow names | Observed responsibility |
|---|---|---|
| Forecast/research (11) | audit-stock-radar-accuracy, monitor-stock-value-radar, probe-decision-sources, stock-autopilot-recovery, stock-entry-plan, stock-forecast-independent-audit, stock-forecasts, stock-investment-cases, stock-reading-depth, stock-recommendations, stock-strict-green | Forecast generation, learning/audit, official filings, cash-flow screening, risk gates and alerts; some write to main, others are read-only |
| Stock UI validation (6) | test-stock-decisions-ui, test-stock-neutral-ui, test-stock-radar-canonical, test-stock-radar-integration, test-stock-radar-ui-preview, test-toss-live | Browser and API/preview checks, **some obsolete or failing** |
| Refresh/publish (15) | update-bond-yields, update-commodities, update-cryptocurrency, update-exchange-rates, update-fear-greed, update-korea-fear-greed, update-market-events, update-mortgage-rates, update-news-link-hub, update-real-estate-pulse, update-stock-decisions, update-stock-market-groups, update-stock-opportunities, update-stock-value-radar, update-stocks-dashboard | Time-triggered data ingestion and publishing |
| Other refresh (1) | update-supply-chain | Supply-chain snapshot refresh |
| Miscellaneous validation (5) | validate-real-estate-pulse, verify-investment-embeds, verify-stock-detail-v6, verify-stock-official, verify-stock-value-radar | Domain-specific status, static, data and current V5 detail checks |

Each name above corresponds to one file in .github/workflows with suffix .yml; the grouping is functional, not a claim that only one stage runs per event.

## Existing pipeline dependency map

- **Stock Prospective Forecasts**: scheduled ~10 minutes during a specified UTC window plus a successful **Update News Link Hub** completion trigger. Runs data-source tests/Playwright, research and guarded publishing to main; it does **not** mean 104/104 stocks have valid forecasts.
- **Update Stock Opportunities**: scheduled + completion of **Verify Stock Official Filings**; source, dates, official filings and UI generation before publishing to main.
- **Stock Investment Cases**: scheduled + completion of **Update Stock Opportunities**, further followed by **Stock Three-Year Reading** and **Strict Green Review**; direct publication and conflict controls require intact source snapshots.
- **Update Stock Decisions**, **Stock Entry Plan**, **Update Stock Value Radar**, stock macro/news/sentiment and related publishers also write data to main. Multiple triggers may overlap; retry/race protection should be tested, not deleted.
- GitHub Pages builds also occur on main data commits; a blanket rule requiring new code PR checks on **every** main commit would interrupt those automated financial updates.

## Known red workflows (not marked passed)

Observed examples from Nov 5:
- [Test Stock Radar Integrated UI, run 41982140440](https://github.com/Ohoredingdong/Notion/actions/runs/41982140440): fails assertion "Neutral home must expose market overview, alerts and research picks" while current page uses new V5 DOM. This is a **test–implementation contract mismatch** to investigate and update without weakening requirements.
- [Test Stock Decision UI, run 41982140402](https://github.com/Ohoredingdong/Notion/actions/runs/41982140402): same obsolete selector/home entry assertion. The same browser script is invoked by two workflows; duplicate error reporting and cost.
- [Verify Neutral Production Radar, run 41982140457](https://github.com/Ohoredingdong/Notion/actions/runs/41982140457): Playwright wait-for-function timed out. Do not assume the cause without reproducing it with trace/screenshot.
- [Stock Prospective Forecasts, run 41979762605](https://github.com/Ohoredingdong/Notion/actions/runs/41979762605): publication collision correctly refused with learning_state_changed; later generation succeeded. Keep fail-closed concurrency safeguards.
- [Verify Stock Detail V6, run 41982140437](https://github.com/Ohoredingdong/Notion/actions/runs/41982140437) and [Verify Stock Value Radar, run 41982140413](https://github.com/Ohoredingdong/Notion/actions/runs/41982140413) passed for the current UI. **This does not make the red workflows green.**

## Coverage gaps before this branch

1. No repository-level Codex operating contract or reusable project skills.
2. No unified **PR-only, read-only change classifier** protecting persisted data files and backups from accidental code PR changes.
3. No unified before/after screenshot evidence for desktop/mobile/**Notion-sized iframe** using the same real persisted snapshot.
4. No single code PR status spanning source syntax, existing current V5 browser checks, controlled data freshness and graphical regression.
5. Existing UI tests reference obsolete selectors and are not automatically up-to-date when the canonical page changes.
6. On main, code and data share a direct Pages publication surface, with no branch rule preventing untested code from being pushed.

## Proposed safe protections on the feature branch

- Root AGENTS.md and two task-specific .agents/skills workflows communicate user-approved design, data safety, provenance, scope and review steps to Codex.
- scripts/codex_pr_preflight.py uses git merge-base to scan **only PR changes**; rejects deletion/rename and changes to tracked production JSON/JSONL/backups in a code PR. It reports edits to existing production workflows for separate review.
- .github/workflows/codex-pr-safety.yml is **pull_request only**, contents:read and writes no production data; classifies changes, runs changed-source syntax, existing stock safety tests, and screenshot-based browser checks for UI-relevant changes.
- scripts/pr_widget_browser.py compares original/current canonical investment radar with actual repository JSON/JSONL under identical desktop/mobile/Notion-sized iframe conditions and saves image differences for reviewers. It does not use fabricated quotes or modify the source data. The iframe is **a simulated Notion embed**, not a live Notion account.
- Existing main data publishers, schedules, permissions, Pages config, main branch/rulesets, and user-created files remain **unchanged** by this branch.

## Critical enforcement boundary / future approval

New PR checks **can fail an unsafe pull request** but cannot yet prevent a manual/direct push or a data-writing GitHub Action from reaching unprotected main. To literally guarantee "failed code never deploys", the owner must separately approve an enforcement plan: require the named PR check for code changes, preserve the data robot's write path, and/or move Pages release artifacts to a separate approved branch/environment. **Do not enable any branch protection, ruleset, deployment environment or automatic merge in this PR.**

## Remaining risks and follow-up

- Diagnose and modernize the two duplicated legacy UI assertions and the neutral timeout in their own reviewed code PR; **do not skip/xfail them as a workaround**.
- Investigate current publication collisions and overlapping workflow_run / cron triggers without resetting immutable forecast evidence.
- If the branch remains open while production data advances, rebase/merge latest main into the feature branch with explicit review and re-run tests (do not overwrite newly published finance data).
- Verify production after explicitly approved merge: data freshness, official-source provenance, JS errors, mobile and actual Notion embeds, and rollback.
