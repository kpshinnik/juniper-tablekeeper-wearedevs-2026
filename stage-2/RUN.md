# Run Juniper Tablekeeper — Stage 2

From this directory, build and start the complete, single-container browser product and API:

```sh
docker build -t juniper-tablekeeper-stage2 .
docker run --rm --name juniper-stage2 --cpus=2 --memory=2g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -e PORT=8080 -p 8080:8080 juniper-tablekeeper-stage2
```

The image includes Python and IANA timezone data. It binds `0.0.0.0`; `PORT` defaults to `8080`. The service starts with empty state and requires no runtime network or writable filesystem. `GET /health` returns `{"status":"ok"}`. To choose another port, set `PORT` and map that same container port. For a network-isolated check, attach the service and an HTTP test client to a Docker network created with `docker network create --internal`.

Open `http://localhost:8080/`. The directly reachable browser routes are `/`, `/signup`, `/login`, and `/lookup`; all scripts/styles are bundled. The service starts empty. `POST /_test/reset` accepts the Stage 1 fixture plus optional declared `combinable` pairs and cancelled seeds. Test controls are deliberately unauthenticated. Use synthetic data only. Signup/login return non-expiring bearer tokens. Public reads are `/restaurants`, `/restaurants/{id}` and `/availability`. Authenticated diners can create, list, look up, amend and cancel reservations, and atomically move 1–8 reservations through `/reservation-moves`.

Create/PATCH/moves accept either `table_id` or `table_ids` (one or two IDs), never both. Only declared pairs are allowed. Pair order in responses follows the fixture. New reservation responses carry `table_ids` and carry `table_id` only for singles. Availability retains single-table IDs and adds ordered single/pair options with exact summed capacities. Cancelling a pair releases both tables. Party sizes remain exact integers through browser search, form and raw request JSON, including above JavaScript's safe integer range.

Creation and atomic moves require `Idempotency-Key` (1–255 characters). Preserve the entire request body and key when a response is uncertain. A successful replay returns the original receipt with 200, even if the current reservation changed. Look up the reference to obtain its current state. Rejected writes claim no key.

`GET /_test/export` returns an atomic snapshot; `POST /_test/import` replaces state from that unchanged object, including exports from the accepted Stage 1. Snapshots include password hashes and live session tokens and must be treated as private test data. No source process or external storage is needed. State is in memory and is lost on container restart unless explicitly exported/imported. Reset clears all data and sessions. Browser sessions use local storage; a pending booking body/key remains in page memory during replacement import, but recovery across a page reload is not promised.

Every response closes its HTTP connection. Standard clients reconnect automatically. Ambiguous framing is rejected before dispatch. The service accepts exact finite JSON numbers without binary rounding and keeps unknown fields in idempotent request identity. Large pair capacities use compact decimal spans for comparison and bounded-memory output preparation. The original old-stage receipt shape is retained on replay; current reads gain Stage 2 fields. A lost booking response shows uncertainty and retries the original body/key; confirmation uses the original reference and a fresh read of current seating. Policies, histories, recurring agreements and operator closure planning are not part of Stage 2.

For lightweight local developer verification with Python 3.12+, run `python -m unittest discover -s checks -v`. Independent judged-container and frozen-suite results belong to the verifier's evidence, not this command.

For the optional synthetic local demonstration, load the bundled fixture from this directory:

```sh
curl -i -X POST http://localhost:8080/_test/reset -H 'Content-Type: application/json' --data-binary @demo-fixture.json
```

Sign in as `ada@example.test` with the synthetic password `juniper-demo-2026`, search a future date, and choose a single or combined seating option. This fixture replaces all service state. It contains no real restaurant or customer data and makes no real booking.

With Playwright and its local Chromium cache installed, `python checks/browser_flow.py` runs the developer browser cases against an ephemeral local service and writes a unique evidence directory. The supplied workstation uses `PLAYWRIGHT_BROWSERS_PATH=/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers`. This is an optional development dependency; the delivered service image has no Playwright or runtime package downloads.

The browser repair for V-S2-002 uses decimal-text guest controls with a numeric keyboard hint, preserving positive-integer validation without the native number input's finite range. `python checks/browser_numeric_entry.py` reproduces the 401-digit search and booking cases using both fill and ordinary key events, then checks real POST 201 response loss, exact body/key replay, lookup/cancel and mobile width. `python checks/browser_labels.py` retains the earlier full-label layout regression. These are local checks; their earlier independent acceptance is preserved as historical evidence. The new V-S2-003 pair-cell finding reopens Stage 2 and requires renewed qualification.

The scoped V-S2-003 correction renders a pair button only at slots that offer that pair; single-table cells still show both available and unavailable states. It preserves the selected booking form and exact pending retry during board refresh. `python checks/browser_pair_visibility.py` runs complementary real-browser cases at 375/1360px. From this repository, `python checks/run_browser_review.py` executes the unchanged independent D222 definitions against a lightweight local service without changing QA source. See [the repair evidence](checks/PAIR-VISIBILITY-REPAIR.md) for the original failures, corrected runs and explicit limits. Stage 3/4 copy-forward remains gated on successive renewed acceptances.
