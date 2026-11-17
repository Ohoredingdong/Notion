# Remaining source diagnostics (local proposal)

Base: 70c86c263896666f103238ce8f839164e1996ff8. No source JSON, ledger, gate threshold or unpublished financial feature is changed.

## Korean index window mismatch
Stored macro evidence collected at 2026-11-17 15:14 UTC reports that both 3mo and bounded absolute-window retries ended on 11/16 for KOSPI and KOSDAQ. The stale flags and expected 11/17 session are correct. In contrast, canonical chart evidence collected at 12:38 UTC used 6mo and had verified 11/17 closes for both indices. This proves differing stored provider responses, not that any fresh 6mo response will always be current.

The small proposal aligns exchange-index fetch windows to the existing canonical chart's 6mo. FX remains 3mo. Existing identity validation, session cutoff, exact 20-session calculation, one bounded retry and stale-result handling are unchanged. It does not copy chart values into macro data or retimestamp old observations.

Two bounded live Yahoo probes returned HTTP 429. Further retries stopped. Live recovery is unverified; successful fresh collection and public-session checks are needed after any deployment.

## Full-universe mismatch
Current catalog: 8583 issuers, generated 11/17 05:03 UTC. Published sweep: 8584 issuers, generated 11/16 16:52 UTC using the 11/14 catalog.
The set difference is 5 new keys and 6 prior-only keys, not simply one record to delete. An offline current-catalog manifest generated 8583 unique targets across 32 shards without provider calls or publication. No full model sweep was run. The existing source-lease and identity/count gates are correct; repair requires a genuine current-catalog run, not changed timestamps/hashes or reused old predictions.

## Tests and scope
56 catalog, public-universe, price-evidence and market-context tests pass. New tests cover the canonical index window, still-stale responses and preserved absolute retry, plus unchanged FX window. Tests use synthetic provider responses and do not demonstrate live source availability. No in-progress main workflow existed when this independent diagnosis began. No remote change or manual dispatch was made.
