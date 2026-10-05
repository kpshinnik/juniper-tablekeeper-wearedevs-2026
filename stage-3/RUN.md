# Run Juniper Tablekeeper — Stage 3

From this directory, build and start the complete, single-container browser product and API:

```sh
docker build -t juniper-tablekeeper-stage3 .
docker run --rm --name juniper-stage3 --cpus=2 --memory=2g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -e PORT=8080 -p 8080:8080 juniper-tablekeeper-stage3
```

The image includes Python and IANA timezone data. It binds `0.0.0.0`; `PORT` defaults to `8080`. The service starts with empty state and requires no runtime network or writable filesystem. `GET /health` returns `{"status":"ok"}`. To choose another port, set `PORT` and map that same container port. For a network-isolated check, attach the service and an HTTP test client to a Docker network created with `docker network create --internal`.

Open `http://localhost:8080/`. The directly reachable browser routes are `/`, `/signup`, `/login`, and `/lookup`; all scripts/styles are bundled. The service starts empty. `POST /_test/reset` accepts the Stage 1 fixture plus optional declared `combinable` pairs and cancelled seeds. Test controls are deliberately unauthenticated. Use synthetic data only. Signup/login return non-expiring bearer tokens. Public reads are `/restaurants`, `/restaurants/{id}` and `/availability`. Authenticated diners can create, list, look up, amend and cancel reservations, and atomically move 1–8 reservations through `/reservation-moves`.

Create/PATCH/moves accept either `table_id` or `table_ids` (one or two IDs), never both. Only declared pairs are allowed. Pair order in responses follows the fixture. New reservation responses carry `table_ids` and carry `table_id` only for singles. Availability retains single-table IDs and adds ordered single/pair options with exact summed capacities. Cancelling a pair releases both tables. Party sizes remain exact integers through browser search, form and raw request JSON, including above JavaScript's safe integer and native numeric-input ranges. Guest controls preserve decimal text with a numeric keyboard hint; validation rejects invalid positive-integer text before sending a request. Long guest summaries wrap without truncation.

Creation and atomic moves require `Idempotency-Key` (1–255 characters). Preserve the entire request body and key when a response is uncertain. A successful replay returns the original receipt with 200, even if the current reservation changed. Look up the reference to obtain its current state. Rejected writes claim no key.

`GET /_test/export` returns an atomic snapshot; `POST /_test/import` replaces state from that unchanged object, including exports from the accepted Stages 1 and 2. Snapshots include password hashes and live session tokens and must be treated as private test data. No source process or external storage is needed. State is in memory and is lost on container restart unless explicitly exported/imported. Reset clears all data and sessions. Browser sessions use local storage; a pending booking body/key remains in page memory during replacement import, but recovery across a page reload is not promised.

Every response closes its HTTP connection. Standard clients reconnect automatically. Ambiguous framing is rejected before dispatch. The service accepts exact finite JSON numbers without binary rounding and keeps unknown fields in idempotent request identity. Large pair capacities use compact decimal spans for comparison and bounded-memory output preparation. The original old-stage receipt shape is retained on replay; current reads gain Stage 3 fields. A lost booking response shows uncertainty and retries the original body/key; confirmation uses the original reference and a fresh read of current seating. Stage 3 adds dated policies, accepted terms, truthful history and recurring agreements. Operator closure planning and whole-series amendments remain Stage 4 features and are not implemented here.

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

Series adoption keeps the anchor's identity, terms, revision, times and history. Generated members select their own date's policy and are committed together. Individual edits permanently mark an occurrence as an exception; cancellation retains the occurrence and its existing flag. A batch increments each affected series once. Generated dates remain tied to the original pattern even after individual edits. Whole-series time amendments are not available in this stage.

History and decision, and GET series, return owner-only 404 even when signed out. Native histories record actual creations, real changes and first cancellation; no-op/retry writes add no events. Imported Stage 1/2 bookings receive a current revision 1 and policy-0 terms, but no invented past events. Their original successful receipt JSON remains unchanged, even when it lacks the newer fields or includes ignored fields that now have meaning.

The opaque export includes a validated earlier-format baseline and the actual successful Stage 3 operation journal. Import reconstructs histories, receipts, scheduled dates, exceptions and counters before comparing the complete current state, then publishes once. A recomputed outer checksum alone does not make inconsistent state valid. Unknown request values retain exact JSON identity. This journal is private snapshot data; it is not an additional public API or an external service.

For the accepted exact-input carry-forward regression, run `python checks/browser_numeric_entry.py` with the same local Chromium cache. It exercises actual 401-digit keyboard entry, real committed-response loss, exact retry and responsive lifetime; results and earlier failures are retained in `checks/BROWSER-REPAIR.md`.

The V-S2-003 pair-cell correction is copied from accepted Stage 2 product `4b2236fb6576b636d168b2cacf1a5d91921cf582`, after renewed Coordinator gate `b0e69e22fa1fd30e89516e09b0fecac45b74a2eb`. Unavailable pair buttons are absent at each affected slot; unavailable single-table cells remain. All server, policy, history and recurring-agreement code remains unchanged from Stage 3 `4ce583cca13a033dd2f548ca982deec7200f8ad6`. That earlier revision's acceptance and later reopening remain historical evidence. The repaired Stage 3 requires fresh independent qualification.

`python checks/run_browser_review.py` reproduces the unchanged D222 browser definitions from the repository's sibling `qa/` directory against a local ephemeral HTTP service. Additional explicit browser-test filenames may be passed. This optional development wrapper requires the local QA checkout and Playwright; the delivered image does not. It saves raw results under `checks/evidence/`, or under `BUILDER_EVIDENCE_ROOT` when set. Use an external evidence directory for postcommit checks, and never run developer wrappers inside the independent immutable official checkout. [Pair repair evidence](checks/PAIR-VISIBILITY-REPAIR.md) separates original failures, local checks and the pending exact-SHA independent review.
