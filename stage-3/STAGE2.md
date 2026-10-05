# Stage 2 design and provenance

Copied from the team's accepted Stage 1 product `fd843b83db16ec8585d66af7ac0d6fac89aae82c` only after Coordinator gate `0fde6cc725d472cd0c9db36fa2969a6ecb747654` and all five Stage 2 handoff parts were visible in room `e04c2728-8535-41c8-be50-88eb8068fa09`. Stage 1 remains unchanged. `DESIGN.md` records the inherited foundation and its seven repaired defect families; this file defines Stage 2 additions before implementation.

## Domain invariants and publication

* A selection is one table or one declared unordered pair, returned in declared order. Combining is not transitive; duplicate IDs are invalid, and a pair occupies both members for the full half-open interval.
* Every occupancy comparison uses set intersection and exact UTC instants. Atomic moves validate the complete resulting state before one publication; a rejected pair, swap, reset or import changes nothing.
* All new responses include `table_ids`, with `table_id` only for singles. Old snapshot records can retain their shape internally, while current read projections gain the new field. Original old receipts retain their exact JSON shape and values.
* Pair capacities are exact sums of positive integer decimal values. Comparison uses compact decimal spans. Excluded pairs never expand a huge zero run. Only an actually returned capacity is serialized; a prepared response represents zero runs compactly and streams or compresses them with bounded memory. This is a representation choice, not a numeric cap.
* Validation, normalization, candidate cloning and response preparation finish before publication. New formatting/compression errors cannot publish partial writes. The original socket-loss retry boundary remains unchanged.
* Import verifies old and new record/receipt shapes, original request/result correspondence, canonical table order, ownership, time consistency, and mutual occupancy. It does not fabricate a new original receipt or compare historical seating with present occupancy.

## Browser invariants

* Search owns a generation number and a frozen query. Restaurant detail, result grid and selected form are published only for the latest generation. A late response cannot change any of them.
* Party size travels as validated decimal text from input through query and raw JSON request construction. JavaScript binary floats never determine a submitted party size. Response parsing preserves numeric tokens as text for display; IDs and labels remain strings.
* A booking attempt captures exact body text and one key. An unchanged retry retains both, including across replacement import. Transport loss shows uncertainty with no false error or success. Confirmed refusal shows an error and refreshes availability while preserving the form. Changed input creates a new request identity.
* Success obtains the original reference from the server receipt, then reads the current reservation before rendering assignment details. Lookup and grid remain authoritative after intervening repair. No automatic booking, background polling or cached success is invented.
* All dynamic labels use DOM text nodes. Routes, navigation and session display work without external assets. Empty/loading/refused/uncertain/success states have distinct wording and styling. Visible labels, keyboard focus and 375px width are acceptance constraints.

## Visual plan and review

Juniper is a calm dining-room ledger with an evergreen navigation rail and a light tablecloth-colored working surface. The memorable element is an airy, time-led seating board: rows of legible time buttons grouped by human table labels, with pairs named as intentional shared seating. Search controls precede that board; a booking slip sits alongside it on desktop and below it on mobile.

Palette: evergreen `#173e35`, leaf `#326456`, porcelain `#fcfbf7`, oat `#ebe8dc`, ink `#202b28`, amber `#875817`. Georgia supplies restrained dining-menu headings; the system sans-serif supplies compact labels and controls. No remote fonts. Main content is left-aligned, with a readable maximum width and a two-column search/booking flow that collapses at 760px.

The initial menu-card idea was simplified: repeated rounded cards would obscure the time/table comparison. The board uses sections and a wrap layout; only the booking slip is a raised surface. Decorative statistics, stock hero art and technical identifiers are omitted from the diner flow. The actual search and seating choices carry the page.

## Verification boundaries

Builder runs lightweight domain/HTTP/browser checks and preserves failed attempts. Verifier exclusively owns heavy Docker and extreme numeric-client execution, including the unchanged full-receive/decompression/parse test. A small local compression check is not evidence for the extreme official/frozen case. Stage 3 and Stage 4 product code remain gated.
