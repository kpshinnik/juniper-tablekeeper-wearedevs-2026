# Juniper Tablekeeper

Juniper is a restaurant reservation service with a warm diner browser, exact retries, portable state, dated booking policies and recurring reservations. Managers can preview and apply exact seating plans after a table closure. Three real BAND coding-agent seats built and independently reviewed the four stages from the supplied specifications. All demonstration data is synthetic.

## Accepted product and delivery status

**All four product stages are accepted.** Final product `25ade1c7add9a5701a511e07f79a619a3cb21b51` has independent ACCEPT evidence `96329db1347c0e8b555282e22a35785643020d04` and Coordinator gate `693f9ec5d4c2df6353a15f002ffb601bf765d13a`, recorded 2026-10-05 at 15:23:07 UTC. The unchanged clean isolated all-stage harness passed. The genuine native room export remains unresolved, and the final concrete-delivery packaging check is a separate step after these guides; product acceptance does not mean submission completeness.

| Stage and scope | Accepted product | Independent evidence / Coordinator gate |
| --- | --- | --- |
| 1 — Reservation API, atomic moves, portable state | `fd843b83db16ec8585d66af7ac0d6fac89aae82c` | `b5578cdd018398bde579322a78a161add719de4c` / `0fde6cc725d472cd0c9db36fa2969a6ecb747654` |
| 2 — Diner browser and declared pairs | `4b2236fb6576b636d168b2cacf1a5d91921cf582` | `92dc4c42b8f562d1548f4e36a53437a28f151a3f` / `b0e69e22fa1fd30e89516e09b0fecac45b74a2eb` |
| 3 — Policies, histories and recurring agreements | `301caf55085280f12197e393ab6b4735ef4046c3` | `f31cf3ab27938453c42b4d495ec54953c990153a` / `63617e70f29f564ddb490f48fa83e49d737bb4ee` |
| 4 — Exact seating plans and recurring amendments | `25ade1c7add9a5701a511e07f79a619a3cb21b51` | `96329db1347c0e8b555282e22a35785643020d04` / `693f9ec5d4c2df6353a15f002ffb601bf765d13a` |

Current authority: [acceptance ledger](acceptance.md), [Stage 4 review](reports/stage-4/REVIEW-25ade1c.md) and [gate provenance](provenance/stage-4-pair-acceptance.json). Earlier rejected revisions, repairs and raw failures remain in [history](demo/HISTORY.md). Review-pending notes inside unchanged stage RUN/check documents describe their product-submission time. This table and the acceptance ledger identify current accepted revisions; all four stage folders, including RUN.md, remain byte-identical to the qualified product. The proposed RUN clarification remains [unapplied historical material](demo/review-handoffs/stage4-25ade1c7-run-asof-proposed.patch).

## Run accepted Stage 4 locally

Docker is the runtime prerequisite. From this delivery repository, the first command checks that all tracked stage files still match the accepted product. Each stage is independently buildable; this example uses the complete Stage 4 service.

```sh
git diff --exit-code 25ade1c7add9a5701a511e07f79a619a3cb21b51 -- stage-1 stage-2 stage-3 stage-4
cd stage-4
docker build -t juniper-tablekeeper-stage4 .
docker run --rm --name juniper-local-25ade1c --cpus=2 --memory=2g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -e PORT=8080 -p 8080:8080 juniper-tablekeeper-stage4
```

In a second terminal, from the repository root, load the synthetic fixture (reset replaces all local service state):

```sh
curl -i -X POST http://localhost:8080/_test/reset -H 'Content-Type: application/json' --data-binary @stage-4/demo-fixture.json
```

Open `http://localhost:8080/`. Sign in as `ada@example.test` / `juniper-demo-2026`. The fixture grants this synthetic diner manager rights at `juniper-garden`, so the same service supports booking, policies, series, closure preview/apply and recurring amendments. Choose a future date for cancellation/amendment demonstrations. No real restaurant, payment or external booking system is connected.

The service binds `0.0.0.0`, starts empty and uses `PORT`, default `8080`. For port 18087, use `-e PORT=18087 -p 18087:18087` and that URL. Runtime assets and IANA timezone data are bundled; no outbound runtime network is needed. The demonstration port mapping alone is not proof of isolation: independent qualification used an internal network and a separate container client. Required service limits are 2 CPU, 2 GiB, up to 50 requests in flight, readiness within 60 seconds, ordinary requests within 5 seconds and test controls within 10 seconds. Measurements below describe finite executed cases. Use a unique container name if the example name is already occupied; stop only your own demo.

[Stage 1 RUN](stage-1/RUN.md), [Stage 2 RUN](stage-2/RUN.md), [Stage 3 RUN](stage-3/RUN.md), [Stage 4 RUN](stage-4/RUN.md) and the [demonstration sequence](demo/DEMO.md) retain detailed setup and contracts.

## Diner experience and booking rules

Search lives at `/`, account screens at `/signup` and `/login`, and reference lookup at `/lookup`. The seating board presents restaurant and table labels, local times, singles and approved pairs. The browser is designed for responsive use at 375px and desktop widths, with visible labels, keyboard focus and distinct loading, empty, unavailable, selected, confirmed, refused and uncertain states. All assets work locally.

A late search response cannot replace newer results. An occupied-table refusal preserves the selected form and refreshes availability. A lost booking response preserves the exact request body and key, shows uncertainty and allows a truthful retry. After recovering the original reference, the UI reads the current assignment before showing confirmation. Guest counts remain decimal text through entry and numeric JSON construction, without binary rounding or an invented upper limit; prior exact-input regressions cover `9007199254740993` and the decimal form of `1e400`.

Unavailable pair choices are absent for that slot; unavailable single cells remain visible. Only declared `combinable` pairs are bookable. Combining is not transitive. A booking occupies every selected table for its full duration; cancellation frees them all. Create, PATCH and atomic moves accept either `table_id` or `table_ids`, never both. Current responses contain `table_ids`, with `table_id` also present for singles. Pair order follows the restaurant declaration.

Occupancy is a half-open UTC interval: a booking ending at 20:30 permits another to start at 20:30. Times are entered in the restaurant's IANA timezone. A skipped local time fails; a repeated time uses its first occurrence. Duration is real elapsed time. Past starts are permitted, while cancellation and amendment cutoffs use the actual current clock. Atomic moves affect 1–8 own bookings at one restaurant; failed validation or occupancy checks leave all of them unchanged.

## Stage 3 policies, history and recurring bookings

A restaurant's fixture `manager_user_ids` grants policy publication, without access to other diners' private bookings. Policies are complete, immutable dated records. For a booking's local date, choose the greatest applicable effective date, then the greatest publication version on a tie. Restaurant detail continues to show the original fixture. `explain=true` adds every table's independent capacity and occupancy decisions; other values fail validation.

Published grid and duration are integers 1–1440, cutoff 0–10080, and capacities 1–100 for exactly all restaurant tables. These publication limits do not narrow valid original fixtures, policy 0 or previously accepted terms. Existing bookings do not change when a policy is published.

Current bookings expose `revision` and `accepted_terms`. A real diner edit checks its old accepted cutoff, validates all resulting fields against the resulting date's policy, replaces terms and end time together, increments revision once and records only actual changes. A no-op retains terms, end time and history but still requires an editable confirmed booking. Optional `expected_revision` on PATCH and batch members rejects stale edits before cutoff checks. History stores each event's own resulting terms. Cancellation adds one final event; repeated cancellation and idempotent retries add nothing.

Series adoption takes an editable confirmed anchor, count 2–12 including that anchor, and interval 1–4 weeks. The anchor's identity, revision, timestamps, terms and history remain unchanged. Each generated date independently selects policy and passes DST, opening and occupancy checks; failure creates no partial series. Real individual edits permanently mark exceptions. Cancellation retains an occurrence and its existing exception flag. A batch increments each affected series once. Original scheduled dates remain fixed.

Stage 3 accepts authentic Stage 1/2 exports. Imported current bookings gain the new representation without fabricated historical events; original receipt JSON keeps its original shape. History, decisions and series reads return 404 to non-owners, including signed-out callers.

## Stage 4 seating plans and recurring amendments

Stage 4 adds three independently qualified API operations to the earlier browser and service. No new screens are required. Confirmation, lookup and availability reflect the current seating after an applied plan.

A manager previews closure seating with a table and explicit-offset `from`/`to` instants. The planner considers **every** confirmed booking overlapping that half-open interval, including bookings seated elsewhere. Each candidate preserves identity, owner, party, start, end and accepted terms. Capacity uses that booking's own terms, and conflicts are checked across its full interval against fixed bookings, other assignments and previous/proposed closures.

The exact objective minimizes changed table sets, then total unused seats, then option ranks in ascending reference order. Singles rank before declared pairs in fixture order. Supported planning size is six tables, four pairs and six considered bookings; larger planning inputs may return `422 planning_limit`. This is not a guest-count or fixture-capacity limit. Exact arithmetic preserves small differences beside very large numbers.

Preview stores a plan and original receipt without changing occupancy, histories or counters. An infeasible plan returns `409 no_feasible_plan`. Apply rejects an intervening restaurant revision with `stale_plan`, or a previously applied plan under a different key with `plan_already_applied`. A successful apply commits closure and assignments together. Only moved bookings gain one revision and `reassigned` history event with `table_ids` and `plan_id`; accepted terms and times stay unchanged. Each affected series increments once without changing exception flags, and the restaurant increments once even if no booking moved. Closures thereafter block singles and pairs in search, creation and amendments.

Series amendment takes positive `expected_revision`, `from_index` in 0..count−1 and strict `local_time` HH:MM. It uses original scheduled dates and current table selections, skipping cancelled and exception members. Each real change checks old cutoff and new policy; non-occupancy errors take precedence in occurrence order, before collective occupancy. Successful real changes increment each changed booking and the series/restaurant once, without creating exceptions. All-no-op and empty eligible sets preserve terms and counters. Failures roll back the whole operation; original retries remain immutable. Stage 4 supports earlier exports and validates plans, closures and operation provenance before state replacement.

## Cumulative HTTP interface


API responses with a body use JSON. Successful `POST /_test/reset` and `POST /_test/import` return `204 No Content` with no body. Error responses contain JSON with `error.code` and a human-readable `error.message`.

| Method and path | Access | Purpose |
| --- | --- | --- |
| `GET /health` | Public | Readiness |
| `POST /auth/signup` | Public | Create a diner account and session |
| `POST /auth/login` | Public | Create another non-expiring session |
| `GET /restaurants` | Public | List restaurants |
| `GET /restaurants/{id}` | Public | Original restaurant/table configuration |
| `GET /availability` | Public | Search by `restaurant_id`, local `date`, decimal `party_size` |
| `POST /reservations` | Bearer token + idempotency key | Create one booking |
| `GET /reservations` | Bearer token | Own bookings, newest start first |
| `GET /reservations/{reference}` | Owner | Current booking |
| `PATCH /reservations/{reference}` | Owner | Atomically change table, time or party size |
| `POST /reservations/{reference}/cancel` | Owner | Cancel and free occupancy |
| `POST /reservation-moves` | Bearer token + idempotency key | Atomically change 1–8 own bookings |
| `GET /restaurants/{id}/policies` | Public | Published policies in publication order (Stage 3) |
| `POST /restaurants/{id}/policies` | Manager + idempotency key | Publish a complete dated policy (Stage 3) |
| `GET /reservations/{reference}/history` | Owner, otherwise 404 including signed out | Actual recorded events (Stage 3) |
| `GET /reservations/{reference}/decision` | Owner, otherwise 404 including signed out | Current revision and accepted terms (Stage 3) |
| `POST /series` | Diner + idempotency key | Adopt an anchor, count 2–12, interval 1–4 weeks (Stage 3) |
| `GET /series/{series_id}` | Owner, otherwise 404 including signed out | Current recurring occurrences (Stage 3) |
| `POST /restaurants/{id}/replans` | Manager + idempotency key | Preview exact closure seating (Stage 4) |
| `POST /restaurants/{id}/replans/{plan_id}/apply` | Manager + idempotency key | Apply a current plan atomically (Stage 4) |
| `POST /series/{series_id}/amend` | Owner + idempotency key | Amend eligible recurring times with expected revision (Stage 4) |
| `POST /_test/reset` | Public test control | Replace all state with a fixture |
| `GET /_test/export` | Public test control | Atomic portable snapshot |
| `POST /_test/import` | Public test control | Validate and replace state with a snapshot |

All 24 routes above are present in the accepted Stage 4 service. Earlier independent stage folders retain their respective subsets. API response bodies use `application/json; charset=utf-8`; successful 204 test-control responses are bodyless, and the four screen routes return HTML. Errors contain `error.code` and a human-readable `error.message`. Detailed request bodies, type rules and error precedence are in each stage's RUN.md.

## Data, retries and persistence

Restaurants and tables come only from reset fixtures: users, restaurant timezone/grid/duration/cutoff/opening hours, tables, optional pairs/managers and seeded reservations. Signup creates diners; manager assignment comes from the fixture. Passwords are salted PBKDF2 hashes. A user may hold multiple non-expiring bearer tokens; reservation access remains owner-only.

Creation, atomic moves, policy publication, series adoption, preview, apply and series amendment require `Idempotency-Key` of 1–255 characters. A first success returns 201; an equivalent replay returns 200 with the original JSON response even after later changes. Reusing a successful key with a different body returns 409. Keys are scoped to user, method and path. Failed requests leave the key reusable. Unknown fields are ignored operationally but remain part of exact JSON request identity. Finite numbers and deep JSON values retain meaning through copying, comparison, serialization and retry.

State is in memory and is lost on container restart. Export/import explicitly transfers accounts, hashes, tokens, configuration, stable identities, histories and original receipts; import validates then replaces, rather than merges, state. The source process is not needed after export. Snapshots contain live credentials and must remain private test artifacts. Reset clears everything. Unauthenticated test controls are required by the challenge; production deployment is not claimed.

Browser sessions use local storage. The pending retry's body/key lives in page memory and survives a replacement import between requests; recovery across page reload is not promised. There is no background polling or cross-tab synchronization. HTTP responses close the connection, and normal clients reconnect. Ambiguous framing is rejected before operation dispatch.

## Independent evidence and measured limits

The [full Stage 4 review](reports/stage-4/REVIEW-25ade1c.md) binds **216 frozen / 344 independent / 158 official definitions**, all reconciled PASS. It directly rechecks all ten demonstrated defect families, including unavailable pair exclusion, exact 401-digit entry, full labels, genuine committed response loss and current seating at 375/1360px. These catalogs form a canonical union of 718 definitions; repeated stages, transfers, requests and adapters add no definitions. This is executed coverage, not exhaustive correctness or a hidden-organizer-test claim.

Raw instrumented pytest evidence remains **892 executions: 839 PASS / 53 FAIL / 0 ERROR / 0 SKIP**. Four original email assertions require 401 where Stage 1 specifies 422; the separately executed adjudicated same 104 definitions pass. The other 49 failures use opaque snapshot selectors from earlier layouts; the separately labelled semantic adapter passes those same 49 assertions, including valid import controls and exact failure nonmutation. Separate developer results retain 81 PASS / 2 fixture ERROR, with 81 adapter PASS. Nothing rewrites or counts those errors as a pass. See [every nonpass disposition](reports/stage-4/NONPASS-RECONCILIATION-25ade1c.json).

Separate experiments pass 50 actually triggered publication faults across 18 defined/executed control names and three fault types; four formatter checks; two deployment probes; and seven actual producer-removal executions covering three standalone integration definitions. Faults include reset and newly applicable planning/amendment writes and prove rollback of occupancy, histories, revisions, terms and original receipts. These are distinct evidence lanes, not additional HTTP definitions.

The [ten-edge transfer matrix](reports/stage-4/TRANSFER-MATRIX-25ade1c.json) records all same/forward transfers. Earlier six edges keep their accepted source/evidence; four fresh incoming Stage 4 edges each execute six frozen definitions, live browser recovery and an actual populated source stop/removal before fresh destination import. All ten have removal evidence and nine applicable edges have browser evidence. Original tokens, login, references, histories, series and receipt classes survive; no earlier execution is relabelled as fresh Stage 4 work.

The unchanged official `--all --mode isolated` command exits 0 on a standalone clean checkout of the exact product, with all 11,031 tracked files verified and no Git alternates. Its applicable stage totals are **120 + 145 + 152 + 158 = 575 PASS**, repeating 158 official definitions. Earlier contexts' automatic future-stage probes separately retain 4 PASS / 3 FAIL and 31 collected but unexecuted cases. Combined isolated raw executions are 582: 579 PASS / 3 FAIL, no actual ERROR/SKIP. These expected future-stage outcomes are not final Stage 4 defects. The reported working-tree provenance is independently bound to clean exact commit bytes; `preview:true` is not an event submission. [Exact command and official evidence](reports/stage-4/REVIEW-25ade1c.md).

| Measured scope | Requests / concurrency | p50 / p95 / maximum (seconds) |
| --- | --- | --- |
| Instrumented HTTPX total | 13,838; observed peak 50; no 5xx | 0.005119834 / 0.101003214 / 3.563072849 |
| Baseline load subset | 2,610; observed peak 50 | 0.036946310 / 0.411636146 / 1.144046971 |
| Stage 4 load subset, including setup/assertions | 325; 50 requested workers, observed peak 37 | 0.016398293 / 0.051689933 / 0.067209151 |

The [Stage 4 load supplement](reports/stage-4/LOAD-METRICS-25ade1c.md), commit `117db1a1e0e5d13510845961aaf348416e07e842`, derives nearest-rank metrics from the existing raw logs and adds no execution. Each of three scenarios uses 50 writes plus 25 reads and verifies atomic state, once-only history/revisions and immutable receipts. Both load rows are subsets of the HTTPX total. Raw sockets, uninstrumented browser/standalone traffic, source injections and official harness requests are excluded; their complete grand total is unknown.

The original uncapped huge client receives/decompresses **1,100,002,780 bytes in 3.563072849 seconds**; full Decimal JSON parsing separately takes **6.614927763 seconds**. Client peak RSS is 2,845,436 KiB; the service is limited to 2 CPU / 2 GiB. Compressed Content-Length is 4,801,658 bytes. Separate wire-only and server-generation times are unknown. The accepted-value create/amend/history/export/import/cancel/retry lifetime passes, but this finite boundary does not establish an unbounded output guarantee.

All 45 application commands total **675.231466 seconds** in a **680.465478-second** window, 14:54:20.965722–15:05:41.431200 UTC on 2026-10-05. The audit verifies 45 manifests, 1,296 artifacts and 50 executed test sources. Default/custom-port health probes take 0.751624/0.808844 seconds. The service uses a read-only root, tmpfs and internal-only network. Resource-heavy cases ran sequentially.

The separate [historical inventory](reports/history/20261005T151238.210978Z-final-history-25ade1c-ed3fc0df/inventory/README.md), recorded 15:12:38–15:12:41 UTC, indexes 457 attempts and 8,208 primary rows: 7,914 PASS / 293 FAIL / 1 ERROR / 0 SKIP. It separately indexes 423 historical source injections and retains the same canonical union. These historical totals are not fresh final-product totals. Later documentation, packaging and accounting artifacts remain separate.

## Factory, usage and remaining packaging

Coordinator owns requirements/gates/FACTORY/mandates/provenance; Builder owns product/guides; Verifier independently rebuilds and tests exact commits. All three use Codex / gpt-6-astra in room `e04c2728-8535-41c8-be50-88eb8068fa09`. [FACTORY.md](FACTORY.md) and the three [generic mandates](mandates/) describe reproduction. From Coordinator's first clock at 06:21:47 UTC to the product gate at 15:23:07 UTC elapsed **32,480 seconds**; this is a product-gate duration, not the unfinished packaging duration.

The latest [native room usage observation](provenance/usage-final-observation.json), 2026-10-05 at 15:16:24.353044 UTC, remains **316,529,051 aggregate tokens / $464.81803 catalog-equivalent / three sessions**, unchanged from 13:42. Categories and completeness are unverified; it is neither measured stage-specific usage nor an invoice. Final usage and actual provider billing remain unknown.

The room is readable, but four supported full-transcript download attempts produced no verified event/path; the latest timed out after 45 seconds. [Export observations](provenance/export-readiness.md) do not establish that BAND is unavailable or that Chrome saved nothing. No genuine `room.json` is present. The remaining operator step is the actual room's Conversation options → Download → Download full room transcript; preserve the downloaded bytes and rename only to `room.json`, then bind a later delivery revision and rerun the unchanged checker. Authored handoff mirrors are not room exports.

Verifier will run the unchanged `python -m harness check EXACT_CLEAN_DELIVERY --track tablekeeper` after final documentation and factory commits. Missing native export must remain a raw failure. The older e538 packaging failure and its 743 adjudicated public Docker GPG fingerprints are historical, not a current check result; [original finding adjudication](reports/stage-4/PACKAGING-e538cd1.json) preserves hashes and bytes. The checker is not patched and no credentials are hidden. Current final packaging outcome is pending that separate concrete-delivery check.

The [Russian guide](FEATURES.html), [local demonstration](demo/DEMO.md), [presentation](demo/presentation.html), [4:40 storyboard](demo/VIDEO-STORYBOARD.md) and [submission draft](demo/SUBMISSION-DRAFT.md) are local artifacts. No video has been recorded; size and duration are planned, not measured. No public push, publication, event submission, production deployment or real booking is claimed.
