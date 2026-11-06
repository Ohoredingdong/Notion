# Development rules

## Scope and preservation

- Follow the user's current scope. Auction work must preserve the investment radar, financial JSON, scheduled collectors, and other widgets.
- Use the existing checkout and a separate work branch. Create a worktree only if the user requests one.
- Preserve existing code, configuration, user notes, and local-storage keys. Never reset data to make a test pass.
- Main publishes changes. Push or merge to main only when the user has authorized production publication; authorization already given in the session remains valid.

## Auction source and publication

- Edit auction runtime code **only in `_auction/`**. Its HTML, JavaScript, CSS, and fictional photos are the development source.
- Root `auction-study.html`, root `assets/auction-study*`, and root `assets/auction-practice/` are generated, verified public files. Do not hand-edit them or their `auction-release.json` manifest.
- Keep the existing Pages settings and financial update workflows. A main commit that changes `_auction/` can trigger the existing site build, but the operating auction entry still uses the previous verified public files.
- `.github/workflows/auction-widget.yml` validates the development source, packages those exact bytes, then promotes only that artifact to the public paths. A failed validation must never promote files.
- `scripts/auction_release.py` verifies hashes, permitted paths, and the canonical source tree. Newer auction source blocks a stale promotion; unrelated data commits may proceed. Never force-push a release.
- Bump the asset query version in `_auction/auction-study.html` when runtime assets change so existing browsers load a consistent release.
- Keep old runtime assets in the source inventory unless the user explicitly authorizes removing them. Publication does not delete files or modify unrelated widgets.

## Product and copy

- Preserve the accepted restrained iOS-style layout. Use clear typography, simple cards, short headings, and consistent terms.
- Standard navigation: 모의경매 / 서류 연습 / 경매 절차 / 검토 요약 / 권리 분석 / 투자금 계산 / 지역·시세 / 최종 검토.
- Prefer short noun headings and action buttons. Keep a concise summary visible; move necessary detail into expandable explanations. Remove repeated explanations and decorative English labels.
- Keep fictional data and AI photos clearly marked. Documents, images, observations, questions, and explanations must describe the same case.
- Never disguise missing rights, unknown costs, invalid numbers, failed storage, or failed requests with invented results.
- Use the shared amount formatter. Preserve raw calculations; show small differences accurately and round bid ceilings down.
- Storage conflicts must preserve the stored original and the current draft. Deleting a note requires a clear, cancellable confirmation and successful persistence before removing it from the screen.

## Validation

- Start a static server from the repository root, then use the **development** URL `/_auction/auction-study.html` for local checks. The root URL displays the last published version.
- Reuse the existing auction unit and browser suites. CI installs Playwright 1.56.0 and uses the runner's installed Chrome when available; local tests can use `/workspace/.notion-dev/bin/python` and `BROWSER_EXECUTABLE=/usr/bin/chromium`.
- Compare before/after screens on desktop, mobile, a short landscape viewport, and a Notion-size iframe. Check keyboard focus, scrolling, calculations, notes, backup/restore, and relevant error paths.
- Add meaningful regressions for reproduced defects. Do not weaken assertions, disable tests, or describe an unrun check as passed.
- Investigate failures and rerun affected checks. After relevant checks pass, avoid unrelated test expansion.
- Distinguish actual device or Notion-app testing from viewport/iframe proxies. Report checks that remain unverified.
- Before reporting publication, confirm the workflow result, public manifest and runtime hashes, and public browser checks. Report an external blocker explicitly instead of claiming success.

See `docs/auction-study.md` for commands and the release workflow.
