# Research safety hypothesis — public proof status must fail closed (2026-11-02)

Baseline fixed at main `fdc8e46603f5f230c9b9924b0789bf9b6ffe4ca0`. Read and preserve the approved timing acceptance, direction-specialist, and bounded-autopilot contracts. Existing #82 diagnostics and PR #88/#89/#90/#92 were reviewed before this experiment; none tested an unknown status inside the append-only `stock-forecast-deliveries.jsonl` audit.

## Hypothesis, recorded before fault injection

The independent audit validates a delivered proof's optional canonical fingerprint and then silently `continue`s for any `status != public_verified`. A malformed or tampered delivery entry that is present in the supposed successful-publication ledger could be dropped from scoring instead of causing `integrity_errors`, permitting favorable post-selection of which frozen misses are scored. Rehashing such a modified row would not change the problem. This is a **synthetic integrity-vulnerability hypothesis**, not an assertion of actual tampering or of any verified user receipt.

## Fixed RED → minimal GREEN experiment

1. Add one synthetic self-test to independent audit: a valid public proof with a deliberately changed status, including a recomputed canonical proof ID, must return `integrity_errors` rather than silently discarding the proof. Absence of required status is also invalid.
2. Run the repository's independent audit PR workflow and confirm the test initially fails while original evidence stays unchanged.
3. If RED occurs, alter **only** the audit delivery-status guard; do not change scoring definitions, model, raw forecasts/outcomes/learning, acceptance thresholds, UI, credentials, strict-green, orders, or other monitor.
4. Require GREEN audit unit tests, independent immutable-evidence audit, acceptance guard, workflow checks, and exact original source blob protection before any merge. Do not declare predictive utility or market price validation.

Production delivery evidence currently contains 30 `public_verified` entries, all marked `human_notification_received=false`. No alternate delivery status is documented as valid inside this append-only successful-publication ledger. Future schema changes require a separately reviewed policy; no historical status is silently rewritten.

**Attempts budget:** one RED candidate and one minimal fix; no model search or validation-set reuse. If the expected RED cannot be reproduced or CI fails after the fix, keep the branch unmerged and document why.
