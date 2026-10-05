# Stage 3 implementation invariants

Room: `e04c2728-8535-41c8-be50-88eb8068fa09`. Copy source: accepted Stage 2 `d8941d7e630c9f2787623d1222f647d49b40ae91`; independent evidence `3fadcd24ccf507e14c0551ceebf5d9405f6e16a1`; Coordinator gate `28beab7ee99f1e3583868174e9439af1083bf730`. All six Stage 3 handoff parts were visible before copying. Stage 1/2 are not edited. Stage 4 is not implemented.

## Before implementation

* Policy 0 preserves the uncapped valid fixture. Published policies alone enforce their stated bounds. Select by resulting local start date, greatest effective date then version. Original restaurant detail stays unchanged.
* Accepted terms are immutable snapshots on each booking and history entry. A real amendment checks expected revision then old cutoff before validating all resulting fields. A no-op checks editability but retains terms, end, revision and history.
* Every real mutation has one transaction: occupancy, records, histories, reservation/series/restaurant counters and immutable receipt are prepared together. Existing Store clones candidate state, encodes response and candidate, prepares compression, then publishes once. Any exception before publication discards everything.
* History is owner-only, including unauthenticated 404; ordered exact field changes and accepted terms reflect real operations. Imported Stage 1/2 records begin with an explicit current revision/terms baseline and empty history, since their producer recorded no history. Their old receipts retain the original shape and ignored-field identity.
* Adoption retains the exact anchor and creates each later occurrence under its own date's rules. Original scheduled dates, identities and references never change. Individual real changes permanently mark exceptions. Cancellation retains occurrences and exception flags. Batch increments each affected series once and its restaurant once.
* Numeric party/capacity values remain exact and compact through terms, history, snapshots and retries. Published policy bounds do not cap imported or seeded policy 0. DST duration and calendar extrema continue to use accepted Stage 2 arithmetic/formatting.
* Boundary failures include missing/wrong types, both explain rules false, stale revision before cutoff, policy ties and out-of-order publication, no-op after a restrictive publication, DST adoption gaps, date overflow, conflicts among generated occurrences and preexisting bookings, partial batch/series failure, and invalid semantic imports.

## Portable proof of successful operations

The Stage 3 state keeps an immutable, validated prior-format baseline plus a private journal of successful Stage 3 writes. Each entry records the request, authenticated owner, idempotency scope, actual operation time and allocated identities. Pure domain replay validates the journal and reconstructs policies, accepted terms, histories, series linkage, counters and original receipts. A mismatch rejects import atomically. This is application provenance, not a QA oracle import.

The journal contains no fabricated historical operations for old producers. A native reset can record genuine seeded creation at its baseline; an old import cannot. Account/token registries are validated independently and retain the baseline identities. Journal replay uses the recorded original clock for cutoff checks and exact allocated identities, never regenerates references or times, and never performs network access. The opaque outer snapshot still contains exact JSON text, protecting arbitrary finite numbers through ordinary JSON carriers.

Authentication, static assets, strict HTTP framing and absolute request deadlines remain the accepted service. Existing browser behavior, exact party text and pending retry identity remain unchanged. Local checks are developer evidence; constrained Docker, extreme uncapped-client runs and independent acceptance belong to Verifier.
