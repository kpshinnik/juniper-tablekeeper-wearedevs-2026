# Run Juniper Tablekeeper — Stage 4

From this directory, build and start the complete, single-container browser product and API:

```sh
docker build -t juniper-tablekeeper-stage4 .
docker run --rm --name juniper-stage4 --cpus=2 --memory=2g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -e PORT=8080 -p 8080:8080 juniper-tablekeeper-stage4
```

The image includes Python and IANA timezone data. It binds `0.0.0.0`; `PORT` defaults to `8080`. The service starts with empty state and requires no runtime network or writable filesystem. `GET /health` returns `{"status":"ok"}`. To choose another port, set `PORT` and map that same container port. For a network-isolated check, attach the service and an HTTP test client to a Docker network created with `docker network create --internal`.

Open `http://localhost:8080/`. The directly reachable browser routes are `/`, `/signup`, `/login`, and `/lookup`; all scripts/styles are bundled. The service starts empty. `POST /_test/reset` accepts the Stage 1 fixture plus optional declared `combinable` pairs and cancelled seeds. Test controls are deliberately unauthenticated. Use synthetic data only. Signup/login return non-expiring bearer tokens. Public reads are `/restaurants`, `/restaurants/{id}` and `/availability`. Authenticated diners can create, list, look up, amend and cancel reservations, and atomically move 1–8 reservations through `/reservation-moves`.

Create/PATCH/moves accept either `table_id` or `table_ids` (one or two IDs), never both. Only declared pairs are allowed. Pair order in responses follows the fixture. New reservation responses carry `table_ids` and carry `table_id` only for singles. Availability retains single-table IDs and adds ordered single/pair options with exact summed capacities. The browser omits unavailable pair choices for each slot while retaining unavailable single-table cells; a pair available later remains selectable then. Cancelling a pair releases both tables. Party sizes remain exact integers through browser search, form and raw request JSON, including above JavaScript's safe integer and native numeric-input ranges. Guest controls preserve decimal text with a numeric keyboard hint; validation rejects invalid positive-integer text before sending a request. Long guest summaries wrap without truncation.

Creation and atomic moves require `Idempotency-Key` (1–255 characters). Preserve the entire request body and key when a response is uncertain. A successful replay returns the original receipt with 200, even if the current reservation changed. Look up the reference to obtain its current state. Rejected writes claim no key.

`GET /_test/export` returns an atomic snapshot; `POST /_test/import` replaces state from that unchanged object, including exports from accepted Stages 1–3. Snapshots include password hashes and live session tokens and must be treated as private test data. No source process or external storage is needed. State is in memory and is lost on container restart unless explicitly exported/imported. Reset clears all data and sessions. Browser sessions use local storage; a pending booking body/key remains in page memory during replacement import, but recovery across a page reload is not promised.

Every response closes its HTTP connection. Standard clients reconnect automatically. Ambiguous framing is rejected before dispatch. The service accepts exact finite JSON numbers without binary rounding and keeps unknown fields in idempotent request identity. Large pair capacities use compact decimal spans for comparison and bounded-memory output preparation. The original old-stage receipt shape is retained on replay; current reads gain Stage 3 fields. A lost booking response shows uncertainty and retries the original body/key; confirmation uses the original reference and a fresh read of current seating. Stage 3 adds dated policies, accepted terms, truthful history and recurring agreements. Stage 4 adds operator closure planning and whole-series amendments below.

For lightweight local developer verification with Python 3.12+, run `python checks/run_developer.py`. Two unchanged inherited fixture methods directly alter native snapshots to resemble older formats; their original errors are retained, and the runner explicitly substitutes the schema-1 compatibility adapter described in `checks/EVIDENCE.md`. Independent judged-container and frozen-suite results belong to the verifier's evidence, not this command.

For the optional synthetic local demonstration, load the bundled fixture from this directory:

```sh
curl -i -X POST http://localhost:8080/_test/reset -H 'Content-Type: application/json' --data-binary @demo-fixture.json
```

Sign in as `ada@example.test` with the synthetic password `juniper-demo-2026`, search a future date, and choose a single or combined seating option. This fixture replaces all service state. It contains no real restaurant or customer data and makes no real booking.

With Playwright and its local Chromium cache installed, `python checks/browser_flow.py` runs the developer browser cases against an ephemeral local service and writes a unique evidence directory. The supplied workstation uses `PLAYWRIGHT_BROWSERS_PATH=/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers`. This is an optional development dependency; the delivered service image has no Playwright or runtime package downloads.


## Stage 3 policies, history and recurring agreements

A reset restaurant may declare `manager_user_ids` (default `[]`). Only those users can publish a policy; management does not grant access to other diners' reservations. The bundled demo makes `demo-diner` a manager as well as a diner. This is synthetic demonstration data, not a role-management endpoint.

| Method and path | Access and body |
| --- | --- |
| `GET /restaurants/{id}/policies` | Public; policies in publication order, excluding policy 0 |
| `POST /restaurants/{id}/policies` | Manager + idempotency key; complete policy below |
| `GET /availability?...&explain=true` | Public; independent capacity/no-overlap rules for each table |
| `GET /reservations/{reference}/history` | Owner only; oldest-first actual recorded events |
| `GET /reservations/{reference}/decision` | Owner only; current revision and accepted terms |
| `POST /series` | Diner + idempotency key; `anchor_reference`, `count` 2–12, `interval_weeks` 1–4 |
| `GET /series/{series_id}` | Owner only; current occurrences and permanent exceptions |

A policy requires `effective_from` (local YYYY-MM-DD), `slot_minutes` and `reservation_duration_minutes` (1–1440), `cancellation_cutoff_minutes` (0–10080), `opening_hours`, and `capacities` naming every table exactly (1–100 each). These publication bounds do not restrict the original fixture or policy 0. Choose the greatest effective date no later than the booking date, then greatest publication version. The original restaurant detail never changes.

Bookings gain `revision` and a complete `accepted_terms` snapshot. Publishing a policy does not edit old bookings. A real amendment checks its old accepted cutoff, validates all resulting fields under the resulting date's policy, and records one revision/history change. A no-op keeps its original terms and end time. Optional positive `expected_revision` on PATCH and individual atomic moves rejects stale writes before cutoff/change validation. `explain` accepts only `true`; omit it to retain the prior availability shape.

Series adoption keeps the anchor's identity, terms, revision, times and history. Generated members select their own date's policy and are committed together. Individual edits permanently mark an occurrence as an exception; cancellation retains the occurrence and its existing flag. A batch increments each affected series once. Generated dates remain tied to the original pattern even after individual edits. Whole-series time amendments are available in Stage 4 as described below.

History and decision, and GET series, return owner-only 404 even when signed out. Native histories record actual creations, real changes and first cancellation; no-op/retry writes add no events. Imported Stage 1/2 bookings receive a current revision 1 and policy-0 terms, but no invented past events. Their original successful receipt JSON remains unchanged, even when it lacks the newer fields or includes ignored fields that now have meaning.

The opaque export includes a validated earlier-format baseline and the actual successful operation journal. Import reconstructs histories, receipts, scheduled dates, exceptions and counters before comparing the complete current state, then publishes once. A recomputed outer checksum alone does not make inconsistent state valid. Unknown request values retain exact JSON identity. This journal is private snapshot data; it is not an additional public API or an external service.

For the accepted browser carry-forward regression, run `python checks/browser_numeric_entry.py` with the same local Chromium cache. It exercises actual 401-digit keyboard entry, real committed-response loss, exact retry and responsive lifetime; results and earlier failures are retained in `checks/BROWSER-REPAIR.md`. This Stage 4 copy retains those historical Stage 3 artifacts; fresh Stage 4 independent qualification is pending. See checks/STAGE4-EVIDENCE.md for current local results.

## Stage 4 seating plans and series amendments

All three new writes require authentication, a JSON object and an idempotency key. Unknown fields remain ignored by the operation but belong to request identity. First success is 201; unchanged replay is 200 with the original response, before current plan/revision checks.

| Method and path | Access and required body |
| --- | --- |
| `POST /restaurants/{id}/replans` | Manager; `table_id`, explicit-offset RFC3339 `from` and `to`, with `from < to` |
| `POST /restaurants/{id}/replans/{plan_id}/apply` | Manager; `{}` |
| `POST /series/{series_id}/amend` | Owner; positive integer `expected_revision`, integer `from_index` in 0..count−1, strict `local_time` HH:MM |

A preview considers every confirmed reservation overlapping the proposed half-open closure, including reservations seated at other tables. Each retains its time, duration, party and accepted policy. Candidate singles and declared pairs must fit its own accepted capacities and avoid all fixed bookings, other resulting assignments, previous closures and the proposed closure over the entire booking interval. The exact objective minimizes changed table sets, then total unused seats, then fixture/combination option ranks in ascending reference order. Support is limited to six tables, four declared pairs and six considered bookings; larger planning inputs return 422 `planning_limit`. Ordinary booking and fixture sizes do not acquire that planning limit.

Preview returns `plan_id`, `restaurant_revision`, `closure`, ordered `assignments`, `moved_count` and exact `unused_seats`. It stores only a plan and its receipt, without changing occupancy, histories or counters. Infeasibility returns 409 `no_feasible_plan`. The internal arithmetic retains small differences beside large exponents, including borrowed decimal spans, without binary rounding or a numeric ceiling.

Apply returns the plan ID, new restaurant revision and every considered current reservation in reference order. An intervening restaurant revision gives 409 `stale_plan`; an already applied plan under a new key gives 409 `plan_already_applied`. A successful original-key retry remains valid after later changes. Application records the closure and all assignments atomically. Only moved reservations gain one revision and a `reassigned` history entry naming `table_ids` and `plan_id`. Accepted terms, times, owner and party stay unchanged. Each affected series advances once and retains its exception flags and original dates. The restaurant advances once even for an empty closure plan. Closures exclude availability options, make explanation `no_overlap` false, and reject conflicting new bookings or amendments with `table_unavailable`.

Series amendment changes the requested clock time on each eligible member's original scheduled date at or after `from_index`. Cancelled and permanent exception members are skipped; each member retains its current table set, including a manager's reassignment. A mismatched series revision returns 409 `stale_revision` before occurrence cutoffs or booking validation. Real changes check the old accepted cutoff, then the resulting date's policy. Non-occupancy errors are checked in index order before collective occupancy. Failure publishes nothing. Each changed member gains one ordinary history/revision; the series and restaurant advance once for the entire operation. No new exceptions are marked. All-no-op and empty eligible operations succeed with no counter changes. Their successful receipts still replay unchanged.

Stage 4 snapshots wrap an authentic Stage 3 baseline and a Stage 4 operation journal, plans and closures. Import reconstructs every accepted operation and compares current state before publication. Exact planner costs use a compact opaque representation inside the snapshot. Stages 1–3 exports keep their original receipts, including old response shapes and previously ignored fields. Password login, existing tokens and references remain valid. Export/import compatibility is forward or same-stage; backward import is not promised.

No new screens are required. After a lost booking response, retry recovers the original reference and fetches current seating; an intervening plan can therefore change what confirmation and lookup display without rewriting the original receipt. `python checks/browser_flow.py` includes actual committed-response loss followed by plan application at 375px and 1360px.

This is the renewed Stage 4 repair candidate after Coordinator gate `63617e70f29f564ddb490f48fa83e49d737bb4ee` accepted Stage 3 `301caf55085280f12197e393ab6b4735ef4046c3`. The original Stage 4 `e538cd16bbd96d4206d89f17a67791e759c00823` remains historically REJECTED for V-S2-003 (U402/U404 and D222 at375/1360). Its reports and original local failures remain intact. Only the exact accepted Stage 3 browser file is carried forward; server, planner, codecs, journal, policies, series and all Stage 1–3 contexts are unchanged.

See `checks/PAIR-VISIBILITY-REPAIR.md` for the fresh development observations and `checks/PAIR-CONTINUATION-ASSEMBLY.json` for actual seven-part requirement assembly. From the repository root, with the documented local Python/Chromium dependencies, the browser review can be reproduced with:

```sh
python stage-4/checks/run_browser_review.py test_stage2_native_range.py test_stage2_numeric_geometry.py test_stage2_integer_validation.py test_stage2_pair_visibility.py test_stage2_pair_repair.py frozen/supplemental/test_stage4_ui.py frozen/supplemental/test_stage4_ui_lost.py
```

This wrapper runs unchanged QA test source and assertions against a local ephemeral origin. Its explicit frozen-UI adapter changes only the hardcoded test origin and screenshot directory. It is a developer convenience, not a frozen-suite container qualification. Set `BUILDER_EVIDENCE_ROOT` to an external directory to keep generated logs outside a committed product; never run log-generating wrappers in the Verifier's qualifying immutable checkout.

API responses with bodies are JSON, including `error.code` and `error.message` on errors. Successful reset/import are bodyless204; the four browser routes return HTML. Local checks are developer evidence. Fresh independent full suites, resource-constrained Docker runs, final unchanged isolated harness and packaging checks remain the Verifier's qualification work; no Stage 4 acceptance is claimed here.
