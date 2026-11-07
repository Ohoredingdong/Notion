---
name: widget-safe-pr
description: Implement or modify a GitHub Pages/Notion widget safely using an approved design, real data and a reviewed PR. Use for HTML/CSS/JS widget changes, layout fixes, mobile/iframe behavior, or interactivity.
---

# Widget-safe PR workflow

1. Verify requested artifact is a **working widget**, not a rendered image. Reuse the approved screenshots, functionality and existing layout; preserve other widgets.
2. Find the canonical HTML entry point, its current JS/CSS, source JSON dependencies and the GitHub Actions that publish them. Check for redirects, legacy files and overriding CSS; avoid editing a historical copy.
3. Record a baseline: commit SHA, existing user-facing URL, current screenshot(s), source timestamp, states/localStorage. Do not call cached data "real time".
4. Work on an isolated feature branch. Keep edits minimal, scoped and reviewable. No live-site or production data writes.
5. Validate real interactions (clicks, filters, search, drag/drop where applicable), JS errors, DOM content, and data-error states; check desktop, mobile and Notion embed iframe. Use actual repository snapshots, not fabricated results. Re-test unrelated navigation and layout neighbors.
6. Produce baseline and candidate screenshots at identical viewport sizes and record changed pixels plus unexpected layout differences. Intentional visual changes require explicit user review.
7. Run `python scripts/codex_pr_preflight.py --self-test`, the affected targeted test suite and PR CI. Fix failures, then re-run; mark unrelated legacy failures as unresolved, never successful.
8. Open a draft PR with changed files, screenshots, source/date checks, passed and failed commands, unverified items, and safe rollback path. **Stop before merge/deployment.**

For stock market forecasts or official financial filings, also follow `stock-radar-validation`.
