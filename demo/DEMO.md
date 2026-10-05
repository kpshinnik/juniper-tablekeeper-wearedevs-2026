# Juniper local demonstration

Accepted product `25ade1c7add9a5701a511e07f79a619a3cb21b51`; independent evidence `96329db1347c0e8b555282e22a35785643020d04`; Coordinator gate `693f9ec5d4c2df6353a15f002ffb601bf765d13a`. All four stages are accepted. Product folders remain unchanged. Full current status is in the [English guide](../README.md), [Russian guide](../FEATURES.md) and [acceptance ledger](../acceptance.md). Earlier rejections and repairs remain in [HISTORY.md](HISTORY.md).

## Start accepted Stage 4

This is a runnable synthetic demonstration plan, not a recorded session. From the repository root:

```sh
git diff --exit-code 25ade1c7add9a5701a511e07f79a619a3cb21b51 -- stage-1 stage-2 stage-3 stage-4
cd stage-4
docker build -t juniper-tablekeeper-stage4 .
docker run --rm --name juniper-local-25ade1c --cpus=2 --memory=2g --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -e PORT=8080 -p 8080:8080 juniper-tablekeeper-stage4
```

In another terminal, from the repository root:

```sh
curl -i -X POST http://localhost:8080/_test/reset -H 'Content-Type: application/json' --data-binary @stage-4/demo-fixture.json
```

Open `http://localhost:8080/`; sign in as `ada@example.test` / `juniper-demo-2026`. This Stage 4 fixture gives the same synthetic diner manager rights at `juniper-garden`. Tables are window (2), garden (4), corner (4), round (6); declared pairs are window+garden and garden+corner. It contains no bookings initially. Choose dates safely in the future. The service starts empty before reset; resetting replaces all local data. For custom port 18087 use `-e PORT=18087 -p 18087:18087` and that URL. [Exact Stage 4 RUN](../stage-4/RUN.md) retains the product-submission status note; the current accepted revision is above.

## Diner flow

1. At 375px and desktop width, search a future date for six guests. Select an available declared pair; labels and times should be readable without page scrolling horizontally.
2. Submit, keep the form, then submit unchanged. Show the same reference, with no second booking. Find the reference at `/lookup` and show the current table labels.
3. Show a partial-day unavailable pair absent from the grid while unavailable single cells remain. Use the independently retained [D222 / D223–D225 evidence](../reports/stage-4/REVIEW-25ade1c.md) if not executing an additional demonstration.
4. Cancellation frees every table in the booking. A confirmed refusal keeps the form and inputs and refreshes availability.

## Policies, histories and recurring agreements

Use a local HTTP client with the synthetic account's bearer token; do not show tokens in a recording. Public policy listing is `/restaurants/juniper-garden/policies`. Manager publication to the same path requires a complete dated policy and an idempotency key, including all four capacities. Search `/availability` with `explain=true`. Read a created booking's `/reservations/{reference}/decision` and `/history`.

Adopt an editable anchor through `POST /series` with `{"anchor_reference":"<actual reference>","count":3,"interval_weeks":1}` and a fresh key. The anchor identity, accepted terms and history stay unchanged. Individually amend occurrence 1 to create a permanent exception; cancel occurrence 2 and show it remains recorded. Use a separate untouched series for a collective time amendment if both later members are now excluded.

## Closure plan and series amendment

Create a fresh future two-person booking on `window`. As manager, send `POST /restaurants/juniper-garden/replans` with a fresh key and `{"table_id":"window","from":"2030-01-07T18:00:00+01:00","to":"2030-01-07T21:00:00+01:00"}` for a booking overlapping that interval; if the demonstration date is later, replace both instants with the actual chosen future interval and correct offset. Preview stores a plan without changing occupancy or the booking. Use its returned plan_id at `POST /restaurants/juniper-garden/replans/{plan_id}/apply`, body `{}` and another fresh key. Do not make an intervening restaurant mutation between preview and apply.

Show the same reference, party, times and accepted terms with planned tables; only moved bookings gain a reassigned event. Current search/lookup reflects the closure. Replay the original application key/body: it returns the original response without another mutation. A different key for that applied plan is refused.

For the separate series, read its actual current revision and send `POST /series/{series_id}/amend` with a fresh key and `{"expected_revision":<actual revision>,"from_index":1,"local_time":"20:00"}`. Original scheduled dates and current tables remain; cancelled and exception members are excluded. Show one series/restaurant increment for any real changes and immutable replay. These are request templates; substitute actual IDs/revisions rather than literal angle-bracket text.

## Genuine lost-response evidence

The accepted [independent review](../reports/stage-4/REVIEW-25ade1c.md) includes real POST201 fetch followed by aborted browser delivery, a subsequent two-booking/pair-to-single or planner repair, and the original retry. Show those authentic traces or execute the same controlled live sequence: uncertainty must retain body/key/form; no manufactured success JSON. Retry recovers the original receipt, while a fresh read shows current seating. Exactly one diner booking exists. A failure before commit is not evidence of postcommit loss.

## Show the factory and evidence

Open actual room `e04c2728-8535-41c8-be50-88eb8068fa09`, its real roster, full handoffs, preserved rejections and repaired exact-SHA decisions. The Verifier decision contains the review; the Coordinator's [six-part final continuation](../provenance/final-delivery-handoff.md) supplies verbatim specifications. These mirrors supplement native posts and are not room exports.

Final evidence: 216 frozen / 344 independent / 158 official definitions reconcile PASS; raw pytest 839 PASS / 53 retained FAIL across 892 executions, with separate developer fixture errors and explicit adapters. The clean exact-product official all-stage run has 575 applicable PASS. Show [the load supplement](../reports/stage-4/LOAD-METRICS-25ade1c.md) as 325 requests and observed peak 37 versus requested 50 workers; it is part of the 13,838 HTTPX total. Full timing and finite numeric-boundary limits are in the root guides. Do not merge definitions, repeated executions, requests, source injections or historical counts.

The [presentation](presentation.html) contains an unchanged actual historical Stage 2 capture, labelled with its source/revision. Use the running accepted Stage 4 service for current video scenes. State is memory-only; explicit export/import preserves private snapshots. No real restaurant or external booking service is connected.

Latest [native usage](../provenance/usage-final-observation.json), observed 2026-10-05 15:16:24.353044 UTC, is 316,529,051 aggregate tokens / $464.81803 catalog-equivalent / three sessions, unchanged from 13:42. Categories/completeness are unverified; final usage and actual billing are unknown. This is not an invoice or stage-specific measurement.

The native full-room export remains unresolved: the room is readable, but four supported attempts produced no verified file. The later operator step is Conversation options → Download → Download full room transcript in the actual room, preserving bytes and renaming only to room.json. A later delivery revision needs the unchanged packaging check. No room.json is synthesized. Final concrete-delivery checker outcome is pending the post-documentation snapshot; the earlier e538 failure is historical. No video is recorded and nothing is publicly submitted.

The [4:40 storyboard](VIDEO-STORYBOARD.md) and [local submission draft](SUBMISSION-DRAFT.md) are prepared materials only.
