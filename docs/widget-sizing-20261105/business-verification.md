# Kitchen widget functional verification

**PASS**: 8/8 suites, 26/26 mandatory profile cases; every subprocess exit 0.
Input root: `/workspace/.notion-cloud/widget-sizing-20261105/after-build-v2`.
The selected results are included in `verification.json` and the screenshots here. Full runtime results and 60 PNG files remain in the external input/evidence directories above; they are not all committed to this folder.

| Suite | Mandatory profiles passed |
|---|---:|
| Recipe native core/navigation (320/390) | 4/4 |
| Recipe opaque iframe (320/390) | 2/2 |
| Records native (320/390/801) | 3/3 |
| Records opaque iframe (320/390/801) | 3/3 |
| Records missing-data/paging edge native | 3/3 |
| Records missing-data/paging edge opaque iframe | 3/3 |
| Growth decor/reward transactions (320/390) | 4/4 |
| Growth three goals before/after first record | 4/4 |

Actual DOM controls verified: recipe paging/filter/detail/favorites/notes;
plan save/edit without consuming inventory or recording nutrients/expense;
actual meal rapid double-save writes once with exact lot deductions and scaled
known nutrients; unknown nutrients remain null; undo restores stock/prior meals;
multiple plans retain IDs/date/slot/selection; native reload exact state;
supplement date/product toggles and reversal; six-week month controls;
shopping → actual expense/receipt without stock or nutrient changes; manual
meal selected-date create/edit/cancel; missing-price indications and product
pagination; initial typed legacy data unchanged; decor draft preview/cancel
read-only and exact restoration, Apply costs once, owned props free, reload
exact; first recipe reward once across two records; chosen goal/model/UI agree.

B6 product fix verified at both 320 and 390: content scroll range **0**, and all
three primary buttons initially fully inside content, height **44px** each.
320: content y8–380.8, buttons y336.8–380.8. 390: content y8–446.6,
buttons y402.6–446.6. The original business assertions were preserved; the
strict aggregator additionally gates both widths on the B6 geometry.

All four HTML hashes remained unchanged throughout execution.
`build-provenance.json` verifies all six source and four generated-file hashes
against `final-build-manifest.json`. All 147 original `assert` AST nodes remain
exact in the external adapted scripts. No checkout files were edited here.

Earlier failure evidence is preserved, not counted as passing:

- Checked-in historical scripts failed on the original52c source baseline
  (`baseline-complete-flow/`, `baseline-tabs/`), due to obsolete visible-label
  and expiry-summary assumptions; later stale selectors also exist.
- First candidate failed B6 no-scroll/initial-action visibility in
  `business-regression/`; final candidate fixes it.
- Old external records helper required content above a bottom navigation;
  corrected only the helper's geometry contract to viewport intersect active
  page/panel and all clipping ancestors. Both old and new rectangle predicates
  remain in diagnostic JSONL. Original assertions remain unchanged.
- An iframe clock initialization race was reproduced and fixed in the explicit
  external QA fixture environment; one rejected two-clock attempt and all
  before/after probes are retained in `business-adapters/`.

These tests use explicit isolated QA fixtures, local servers and disposable
browser contexts. Opaque iframe storage is temporary and wrapper reload loss
is explicitly tested as an existing limitation, not called persistence.
Native and opaque widget entries receive business-flow tests; app entries here
are integrity-only. Separate visual/app-regression tests own design approval.
This does not claim real Notion, Safari, or production-site validation.
No deployment, production API calls, or personal-data modifications occurred.
