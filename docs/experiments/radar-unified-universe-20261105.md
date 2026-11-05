# Main stock list and issuer catalogue integration

## Reproduced defect

On the deployed `a1af147f9e0811513a6d6ed27e53b893e05fe310` site, the home
list displayed `9 / 104개`. Searching its normal `fx-search-input` for
`0001A0` returned no company, even though the stored official catalogue
contained 덕양에너젠 and its issuer-verified financial statement.

The previous catalogue acceptance test exercised a separate
`fx-catalog-search` input. It did not cover the home or AI list. Its
Fabrinet example was also already in the 104-company raw data.

## Data scope at the verified source commit

| Scope | Companies |
| --- | ---: |
| Official catalogue | 8,586 |
| Korean / US catalogue entries | 2,658 / 5,928 |
| Price and deep-analysis raw data | 104 |
| Raw companies present in the catalogue | 102 |
| Existing raw records absent from this catalogue (`US:YMM`, `US:SSL`) | 2 |
| Union offered by the normal list | 8,588 |
| Issuer-verified official financial coverage | 2,631 |
| Verified financial coverage outside the raw 104 | 2,580 |

Absence from this catalogue is not evidence of delisting. The two existing
raw records remain accessible and are labelled as unmatched to the current
catalogue. A catalogue entry does not imply a price, chart, forecast,
valuation, or completed investment review.

## Implementation

- A cached UI model joins the raw records and the official catalogue by
  country plus the exact normalized ticker. It does not modify or expand
  the source `raw.companies` feed.
- The model retains the original catalogue object separately, so the
  financial statement's exact issuer-name, corporate ID, country, ticker,
  and publication-snapshot checks remain intact.
- Home and AI lists use the same universe, resolver, search, market
  filters, favourites, and incremental row display. Exact ticker and exact
  company-name matches rank first. Both catalogue names and existing raw
  display names remain searchable.
- Existing unambiguous raw selection IDs are preserved. New catalogue
  selections use country-qualified IDs, including alphanumeric Korean
  codes and US tickers containing dots. Ambiguous bare aliases are rejected.
- A catalogue-only selection stays on the same issuer through home, AI
  list, company analysis, scenario, and reload. The profile displays
  available official financial data and source links. Missing prices,
  charts, forecasts, and scenario inputs remain explicitly unavailable.
- The second, independent catalogue search panel is removed from the AI
  page. The ordinary stock search is the single entry point.
- The existing raw-company cockpit, chart, financial review, paper
  portfolio, and price-monitoring inputs retain their sourced data. The
  manual price-based forms remain limited to companies with raw data.
- Rendering caches the filtered pool per view and resolves the selected
  row once, avoiding a full-universe sort for each displayed row.

## Verification contract

The model regression checks cover union cardinality, identity separation,
aliases, collisions, selection round trips, source immutability, catalogue
cache refresh, and preserved financial identity checks. Real-data checks
accept `RADAR_DATA_DIR` so a separately hash-verified current snapshot can
be used without replacing repository data during development.

The browser acceptance uses the ordinary home and AI search boxes. It
asserts that test companies are actually outside the raw set, clicks the
visible rows, verifies the selected issuer and source-linked financials,
and checks navigation, favourites, reload, market filters, and access to
more than 104 real rows. Missing data must stay missing. A named raw
company is used to verify preserved priced-company charts and analysis.

Existing desktop/mobile before-and-after layout limits remain unchanged:
4 pixels for measured geometry and 12 percent for differing pixels.
Locally simulated Notion-size iframes are not represented as tests inside
the user's actual Notion account.

Deployment is complete only after CI succeeds, Pages publishes the merged
revision, and the public site's ordinary home search can select a company
outside the original 104.
