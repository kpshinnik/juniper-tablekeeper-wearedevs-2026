# Stage 4 implementation invariants

Source: exact accepted Stage 3 `4ce583cca13a033dd2f548ca982deec7200f8ad6`, copied after Coordinator gate `f2bfa8297f77353675c2942fb765b18113b35266` and all seven native task/spec parts. Earlier contexts remain unchanged. The inherited evidence directories are historical, not Stage 4 runs.

## Commit boundary and failures

All operations run against a private cloned candidate under the existing request lock. Validation, optimization, response preparation, exact state serialization and compression finish before the sole state assignment in Store.request. Failed planning, stale revisions, conflicting assignments, invalid amendments and preparation faults publish neither records nor receipts/counters. Network loss after publication preserves the original receipt for retry.

## Planner

Consider every confirmed booking overlapping the proposed half-open closure interval, ordered by reference. Use each booking's accepted capacities and complete interval. Singles/pairs retain fixture rank, and pair order remains declared order. Check fixed bookings, all joint assignments and prior/proposed closures. Exactly minimize moved table-set count, unused seats, then rank vector; no heuristic acceptance, binary rounding or integer magnitude cap. The mandated limits are six tables, four pairs and six considered bookings. Exact numeric cost arithmetic must remain compact across huge decimal exponent gaps and subtraction; only public JSON output may expand required decimal digits.

Preview publishes a plan and its receipt only. Apply preserves identity, owner, party, timestamps, accepted terms and permanent series exception flags; moved bookings gain exactly one reassigned event/revision, affected series increment once each, restaurant increments once even with zero moves. Original-key replay precedes current state checks; a new key on an applied plan is plan_already_applied. Unrelated restaurants do not invalidate a plan.

## Series amendment and migration

Validate expected revision and input before occurrence changes. Use original scheduled dates, skip cancelled/permanent exception members, retain current table selections, keep no-op terms/counters. Check all real changes' old accepted cutoff and new-date policy in index order before collective occupancy. One transaction, one restaurant/series increment if anything changes, no new exceptions.

Preserve the accepted Stage 3 module for validation of authentic earlier journals. Stage 4 snapshots have a validated prior-stage baseline plus actual Stage 4 operation journal; replay checks plans, closures, counters, histories and original receipts. Older successful bodies are never reinterpreted under newly introduced endpoints/fields. Any compact internal cost encoding is opaque snapshot representation only and cannot alter public numeric values or unknown request identity.

## Boundary and interoperability checks

Cover no considered bookings, no feasible plan, all bookings including initially unaffected seating, fixed overlap outside closure boundaries, adjacent half-open intervals, prior closures, changed accepted capacities, exact huge costs differing by one, ties/rank order, concurrency, plan replay after later changes, fractional explicit-offset instants, original scheduled dates, permanent exceptions, cancelled and empty eligible series, no-ops after policy change, old and current export/import, checksum-valid semantic corruption and pre-publication faults. Browser checks fetch a real committed 201 then abort before planner repair and retry; original receipt and current assignment remain distinct. Keep exact 401-digit input and 375px label/layout regressions.

Independent constrained Docker, official/frozen and huge-client qualification belongs to Verifier. Builder checks are separate local evidence, with every failed attempt retained. Product code does not import independent QA/oracles.
