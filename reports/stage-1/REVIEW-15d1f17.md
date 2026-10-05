# Stage 1 independent decision: REJECT

Product: **15d1f178b387e744bf919b6e8bb77fff2b5aeb23**. Room:
`e04c2728-8535-41c8-be50-88eb8068fa09`. The complete three-part handoff was received;
Verifier independently rebuilt the exact committed bytes from a clean standalone
checkout. All six previously demonstrated defects pass direct regressions here.
**V-S1-007**, a historical timestamp representation defect, prevents acceptance.

The [JSON inventory](REVIEW-15d1f17.json) records every attempt, QA revision, source
and manifest hash, duration and raw outcome. The [case matrix](case-matrix-15d1f17.json)
maps each logical definition to its original and adapted executions. Earlier reviews
and failures are unchanged. The evidence commit is delivered separately after commit
to avoid a self-referential revision claim.

## V-S1-007: accepted historical dates emit invalid RFC3339 offsets

Stage 1 §3.4 requires RFC3339 response timestamps; §4 permits any calendar date;
§9 requires the IANA offset rules and exact absolute duration. RFC3339 numeric
offsets have the form `+HH:MM` or `-HH:MM`; seconds in an offset do not fit that syntax.

Reproduction for each zone: reset one synthetic restaurant `r` with tables `a` and
`b` of capacity 4, all weekdays open 17:00–23:00, slot 30 minutes, duration 60 minutes,
cutoff 0, and one seeded user. Log in. Request availability for `1800-01-01`, party 2,
then create using a fresh key and
`{"restaurant_id":"r","table_id":"a","starts_at_local":"1800-01-01T18:00","party_size":2}`.

| Zone | Actual availability/create `starts_at` | Actual creation `ends_at` |
|---|---|---|
| Europe/Berlin | `1800-01-01T18:00:00+00:53:28` | `1800-01-01T19:00:00+00:53:28` |
| America/New_York | `1800-01-01T18:00:00-04:56:02` | `1800-01-01T19:00:00-04:56:02` |

Both requests return the expected 200/201 and health stays 200, but the timestamp
syntax is invalid. Expected: valid RFC3339 strings retaining the exact instants and
duration. For these finite examples, exact UTC strings can represent the starts as
`1800-01-01T17:06:32+00:00` and `1800-01-01T22:56:02+00:00`, respectively. Rounding
away the historical offset seconds would change the instants and would not satisfy
the requirement. `starts_at_local` must retain the requested wall-clock value.

Primary attempt:
`reports/stage-1/20261005T075300.059103Z-historical-timestamps-15d1f17-30362bc0/`.
Its manifest SHA256 is
`6240df45c873b84274a5a159d4828572054b53834ada32c6b5eec9ed30a602b9`.
The independent test [test_historical_timestamps.py](../../qa/derived/test_historical_timestamps.py)
has SHA256 `2ff091b1087b880110387bad51c764e0f197a730b796b8190055e5f457a5a9e2`.
Both actual timestamp observations are recorded before the failing assertion.
Later lookup/import/retry assertions were not reached and are not counted as PASS.
The test imports no product code. This is a response-format check, not a demand that
the service use Python's datetime representation internally.

## Earlier defect reconciliation

| Defect | Evidence at this exact revision |
|---|---|
| V-S1-001 | Frozen slow header/body cases and direct raw-socket EOF/nonmutation regressions pass. |
| V-S1-002 | Both spring-gap closing-boundary cases pass; ordinary gap/fold and absolute-duration tests remain green. |
| V-S1-003 | All six reset reservations wrong-type cases return the required error and retain destination state. |
| V-S1-004 | All six unchanged upgrade definitions and 12 applicable numeric definitions pass, including ordinary JSON carrier precision/overflow/underflow lifetimes. |
| V-S1-005 | Five adapted checksum-valid semantic corruptions reject without mutation; unchanged controls, original historical receipts after changes/cancel and replacement retries pass. |
| V-S1-006 | All four original extrema/UTC controls pass. Both added offset lifetimes pass explicit start/end values, half-open adjacency, overlap rejection, list order, past cutoffs or future PATCH/moves/cancel, ordinary JSON replacement import and original creation/batch receipt replay. |

Calendar lifetime evidence is
`20261005T074717.802078Z-calendar-lifetime-15d1f17-75b0ec5c/` and
`20261005T074808.828358Z-calendar-edges-15d1f17-65262ba7/` under this report directory.
These results close V-S1-006 at this SHA; they do not suppress the separate V-S1-007 failure.

## Definitions, executions and retained failures

| Lane | Raw execution outcomes | Reconciliation |
|---|---|---|
| Unchanged official isolated harness | 120 PASS | 120 distinct applicable official definitions |
| Original baseline | 100 PASS, 4 FAIL | Original malformed-email oracle conflicts retained |
| Supplied adjudicated baseline | 104 PASS | Same 104 definitions; §6 requires 422, with nonmutation checked |
| Common frozen cases | 43 PASS, 1 selector FAIL | 44 PASS after separately executed B003 adapter |
| Unchanged Stage 1 numeric | 12 PASS | 12 definitions |
| Unchanged upgrade 1→1 | 6 PASS | Six definitions; later-stage edges pending |
| Main derived | 42 PASS | 42 definitions |
| Original semantic selectors | 5 selector FAIL | Original selector/checksum failures preserved |
| Opaque state adapters | 6 PASS | Five semantic cases plus B003; zero additional definitions |
| Additional pipeline/corruption | 9 PASS | Nine definitions |
| Calendar boundary controls | 4 PASS | Four definitions |
| Full offset calendar lifetimes | 2 PASS | Two additional definitions |
| Historical RFC3339 timestamps | 2 FAIL | Two additional definitions; V-S1-007 |
| Additional unchanged official detail run | 120 PASS | Repeat official definitions with case-level records |

Raw instrumented pytest executions: **460 = 448 PASS + 12 FAIL**. Classification:
four original email oracle conflicts, six opaque selector mismatches, and two current
product failures. Reconciled distinct outcomes: **166/166 frozen PASS**, **62/64 derived
PASS**, **120/120 official PASS**. No aggregate overrides the two contradictory cases.
There are no pytest ERROR or SKIP results. The official next-stage probe preserves
one expected Stage 2 failure followed by 24 unexecuted checks; those are outside
Stage 1 applicability and are not Stage 1 passes.

The opaque adapter preserves the original assertions, validates an unchanged
control, and explicitly decodes/re-seals the string payload. It is a separate
representation adaptation; the original test sources and raw failures are untouched.

Separate lanes, excluded from pytest and HTTP-definition totals:

- **31/31 unchanged developer methods PASS**, independently executed.
- **Eight defined operations, eight executed controls, eight actually injected
  operations**, namely signup, login, create, patch, cancel, moves, reset, import.
  **Three fault-point types**—response_encode, candidate_encode, compression—produce
  **20 actual injection executions, all PASS**. Reset's candidate_encode trigger is
  recorded, raises the synthetic ValueError, retains exact state and retries 204.
  Import has the same preparation coverage. These source experiments generate zero
  HTTP requests. See the earlier [count clarification](CLARIFICATION-source-fault-counts-20261005.md).
- **Three actual producer-removal executions PASS**, repeating one integration
  definition. Sources were current `15d1f17`, original `8958251` and previous `7d76438`,
  each removed before a fresh `15d1f17` destination started. Each preserved two old
  tokens, two immutable receipts, current references, hashed-password login, new
  writes and repeated replacement. Full SHA identities are in the JSON inventory.
- **Two deployment configurations PASS**: default PORT 8080 and explicit 18087,
  first healthy response in 0.5374 s and 0.4527 s from another internal-network container.

## Resource, timing and evidence limits

Docker context `colima-tablekeeper`; judged service 2 CPU / 2 GiB, read-only root,
tmpfs and internal network without outbound access. Clients had no added memory cap.
Docker suites ran sequentially. Exact builds, image/service/client/network inspections,
commands, logs, case JSONL, JUnit and manifests are retained. All 30 frozen input files
and unchanged QA copies were rehashed against the pinned manifest. Every current
attempt manifest verified. The product checkout remains clean and standalone.

Instrumented pytest traffic: **5,272 HTTP requests**, maximum 50 in flight,
p50 0.01773 s, p95 0.11868 s, maximum 0.83612 s, 8,145,142 decompressed received bytes.
Load subset: **2,610 requests**, p50 0.02153 s, p95 0.12189 s, maximum 0.83612 s,
maximum 50 in flight. Setup and repetitions are included. Raw sockets, unchanged
official harness traffic, standalone producer/deployment requests and source-level
injections are separate; uninstrumented HTTP totals remain unknown.

**20 command attempts** have APPLICATION intent, including one preserved QA invocation
error that stopped before contacting the service: deployment_probe.py rejected the
unsupported `--stage 1` option. Its attempt
`20261005T075041.746127Z-deployment-15d1f17-6cfe1cab/` remains intact. The new
`20261005T075257.290677Z-deployment-corrected-15d1f17-927f4a63/` executes both deployment
configurations successfully. Thus 19 command attempts reached their application or
source experiment; the CLI failure is not an application PASS or product defect.

Summed command duration is **154.5844 s**. The execution window is
2026-10-05 07:47:17.802816–07:53:03.311275 UTC, **345.5085 s**, including analysis gaps.
Actual token usage and billing remain unknown. No failed attempt, timeout or error
was erased or converted into a pass.

Builder received V-S1-007 with exact reproduction and primary hashes during this
review. A fresh exact-SHA repair must pass that lifetime and all prior regressions
before acceptance. Coordinator alone reconciles Stage 1 advancement. Stage 2–4,
remaining upgrade edges, final all-stage clean delivery and final packaging remain
pending.
