# Stage3 opaque-state and counter audit contract

Prepared from the full Stage3 specification and Coordinator counter/migration
reading before any Stage3 implementation inspection. **Application NOT_RUN.**
These obligations need a representation adapter after the complete exact-SHA
Builder handoff. An adapter error is not a product defect or a pass. Keep the
unchanged opaque-selector attempts and their hashes alongside adapted results.

## Counter observations

Locate the restaurant revision and series provenance in an ordinary exported
snapshot; document the selector, source SHA and format. Decode and re-encode the
opaque carrier exactly, recomputing its declared digest when testing semantics.
Public reservation/series responses and histories are independent cross-checks.
Use only synthetic private state. Hash snapshots in public evidence instead of
publishing session tokens/password hashes unnecessarily.

The counter observation sequence must establish each row, including valid
controls. All assertions apply to the same transaction as records and receipts.

| Stable obligation | Expected restaurant revision delta | Other required observations |
|---|---:|---|
| D333-reset-seeds | reset to0 | Seeded reservations revision1, original policy0; no invented operation increments |
| D333-create | +1 | New reservation revision1 and one genuine created entry |
| D333-policy | +1 | Policy version+1, existing records/history/terms unchanged |
| D333-adoption | +1 for entire series | Anchor exact; generated histories genuine; series starts1 |
| D333-patch | +1 | Changed booking+1/event1, member series+1, permanent exception |
| D333-cancel | +1 | Changed booking+1/event1; member series+1, exception flag retained |
| D333-batch | +1 for entire batch | Each changed booking+1/event1; each affected series+1, not per member |
| D333-noop | 0 | No-op PATCH/batch retain terms/end/history/all revisions; still editable and revision-valid |
| D333-repeat | 0 | Cancel again and all original-receipt replays allocate nothing |
| D333-reject | 0 | Validation, stale, occupancy, cutoff and failed adoption preserve every state byte |
| D333-isolation | 0 on other restaurant | Publication and reservation operations do not advance unrelated restaurant |

## Semantic corruption definitions to bind after handoff

Each mutation starts with a valid, populated exported snapshot. First import the
unchanged control successfully. Import each independently corrupted copy into a
different populated destination. Expect422 `validation_failed` and the exact
destination export unchanged. Import the valid original again afterward and check
tokens, current state, original receipts and normal operations. Preserve any
original FAIL and adapter mismatch; never silently replace an attempt.

| Stable obligation | Checksum-valid semantic inconsistency |
|---|---|
| D334-policy-version | Duplicate/out-of-order publication version; policy version counter below/above successful publications |
| D334-policy-shape | Missing/foreign capacity member, wrong policy date/type/range, mutated immutable policy0 attribution |
| D334-current-terms | Current accepted terms inconsistent with its accepted policy/version or duration-derived end instant |
| D334-history-order | Seq gap/duplicate, decreasing instants, a created/change event after terminal cancellation |
| D334-history-revision | Resulting revisions below/above authentic operation count, stale accepted terms injected into newer event |
| D334-history-fields | Invented/omitted/reordered changed fields, broken before/after linkage, false no-op event |
| D334-series-owner | Foreign anchor/member owner, duplicate reference/index, missing member or reservation link |
| D334-anchor-linkage | Occurrence0 replaced by a different reservation, changed adoption anchor identity/history/terms |
| D334-original-dates | Original scheduled calendar date or interval inconsistent with authentic adoption receipt/pattern |
| D334-series-lower-bound | Revision too small for separately proven real operations, missing permanent exception after real individual amendment |
| D334-series-upper-bound | Revision inflated without corresponding operations, fabricated adoption/change history |
| D334-cancel-flags | Cancellation erases a prior exception or marks an otherwise unmodified member as an exception |
| D334-receipts | Policy/series/moves original receipt altered, reordered, owned by another caller, or detached from original method/path/body |
| D334-restaurant-bounds | Counter below or above proven successful operations, with reset seeds and whole-batch/adoption counting distinguished |

Use histories and original create/adoption/batch receipts to prove lower **and**
upper bounds where the final format has sufficient provenance. Do not reject a
valid old snapshot for failing a provenance claim its producer never recorded.
Valid legacy current states may establish new current fields; they cannot invent
past events or rewrite old receipt shapes. The D325 removed-producer integration
checks this independently for1→3,2→3 and3→3.

Include a valid control with two series whose original date patterns overlap,
then individually change/cancel some occurrences before export. Original dates
and permanent exception flags must survive. Treat overlap of original *scheduled*
dates separately from actual occupied table/time intervals: it is not by itself
corruption. Run unchanged old and final roundtrips before and after mutations.

## Publication boundary

`fault_publication.py --stage 3` prepares thirteen operation controls and thirty-five
injection executions across candidate encoding, response encoding and compression.
New policy/adoption and member PATCH/cancel/moves must actually reach injected
faults. Existing reset/import controls begin with populated policies, histories and
series. Exact before/after state encoding proves rollback of versions, revisions,
histories, exception flags, occupancy and original receipts together.

These are **defined** counts only. Report executed controls, actually injected
operation names, actually triggered fault types and each outcome separately after
execution. Confirm the product's fallible preparation steps and commit point at
the exact handed-off SHA; extend the adapter if the implementation changes. A
control-list match alone never establishes injection.
