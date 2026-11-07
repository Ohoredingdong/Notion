# Codex development agreement — Ohoredingdong/Notion

This is a live collection of static GitHub Pages widgets backed by scheduled, versioned financial and other data files. **Safe changes, truthful data and approved visual design outweigh speed.**

## Default operating rules
1. Work in a **new feature branch**, not `main`. Open a PR and request approval; **never merge, push to main, force-push, deploy, or change GitHub Pages/branch protection without explicit user approval**.
2. Do not delete, reset, seed, backfill, overwrite, fabricate or silently "repair" production JSON/JSONL, saved state, assets, backups, financial observations, or localStorage schemas. Back up and plan migrations explicitly when genuinely needed.
3. Protect the existing data pipelines. Production GitHub Actions publish data **directly to main**. Do not add PR write permissions, cancel them, repoint their checkouts, or make code PR checks a hard dependency of scheduled data publication. Inspect dependent workflow triggers before editing any publisher.
4. Treat user-approved screenshots and existing working behavior as the design contract. Prefer a restrained light iOS aesthetic: neutral white/soft grey, subtle borders, one blue accent, readable typography and spacing, no excessive color/decoration. Do **not** replace a requested working widget with a generated image or mockup.
5. Preserve desktop (1366/1440/1920), mobile (~390px) and **Notion embed iframe** interactions. Before/after screenshots are required for UI work; compare the same screen, viewport and real stored data. Review unexpected differences and keep screenshot artifacts with the PR.
6. Never invent stock prices, predictions, financial signals, sources, real-time connectivity, test results or completed tasks. Missing, stale, misaligned or failed data is an explicit **unknown/blocked** state, never a positive score.
7. Find root causes before making another CSS override or adjusting layouts. Prefer scoped styles, existing design tokens and minimal diffs; check nearby screens and unrelated cards for regression.
8. Run targeted syntax, unit, browser and visual checks. Record exact commands, actual results, remaining failures and what was **not** tested. Never claim success from source inspection alone or reclassify a failing test as passed.
9. Use PR review for code and UI changes, not the scheduled production-data workflows. **A green PR does not itself deploy**; current main is unprotected and GitHub Pages still builds from main, so human review is mandatory until an approved protection/release-policy change.

## Where to look
- Current canonical investment radar: `stock-value-radar.html`, `assets/stock-radar-flow-v2.js`, `assets/stock-radar-clean-bridge.js`. Other `stock-*-radar` files may be legacy or previews: determine ownership before editing.
- Production data: root `*.json` / `*.jsonl`; their generation scripts live under `scripts/` and schedules under `.github/workflows/`.
- Current radar checks: `scripts/test_stock_detail_v6.py`, `scripts/test_stock_radar_canonical_browser.py`, `scripts/test_stock_evidence_review.cjs`, `scripts/test_stock_forecast_wiring.cjs`. Some older v7/v8 UI tests are **known failing** and cannot be treated as passing; see `docs/development-system-audit-20261105.md`.
- Repeatable procedures: `.agents/skills/widget-safe-pr/SKILL.md` and `.agents/skills/stock-radar-validation/SKILL.md`.
- Proposed PR checks and rollout constraints: `docs/codex-development-workflow.md`.

## Finish a development request
Identify scope and data dependencies → note baseline commit/screenshots → change only approved files on the branch → run relevant checks → compare before/after (desktop, mobile, embed) → fix & rerun failures → open a **draft PR** with evidence, changelog, known failures and rollback plan → wait for explicit approval to merge or deploy.

Ask before operations that irreversibly alter data or production; if testing is blocked, state the blocker and leave production untouched.
