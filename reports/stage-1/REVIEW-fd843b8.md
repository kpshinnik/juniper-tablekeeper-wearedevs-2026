# Stage 1 independent decision: ACCEPT

Exact product **fd843b83db16ec8585d66af7ac0d6fac89aae82c**, room
`e04c2728-8535-41c8-be50-88eb8068fa09`. Verifier independently rebuilt a clean,
standalone checkout of the committed bytes and completed the applicable Stage 1
gate. All seven previously demonstrated defect families have passing direct
regressions here. No demonstrated Stage 1 product violation remains open.

This accepts the Stage 1 service at this SHA. Coordinator alone reconciles the
copy-forward gate. Stages 2–4, their upgrade edges and browser workflows, final
`--all`, final delivery `harness check`, documentation/export and presentation
gates remain pending. There is no hidden-test or exhaustive-input claim.

The [execution inventory](REVIEW-fd843b8.json) records every attempt, command,
product/QA revision, manifest, environment, timing and outcome. The
[case matrix](case-matrix-fd843b8.json) maps original, adjudicated and adapted
executions to logical definitions. Earlier rejected reports and evidence remain
unchanged. The evidence commit is transmitted separately after committing.

## Complete defect reconciliation

| Defect | Current exact-SHA observation |
|---|---|
| V-S1-001: continuously renewed request timeout | Frozen slow-body/header tests pass. Direct raw sockets receive controlled 400 and actual peer EOF at 3.00219 s / 3.00265 s; health 200 and destination state unchanged. The 6.5 s field is the planned drip upper limit, not actual drip duration. |
| V-S1-002: closing boundary in spring gap | Both zones retain valid early availability and bookings, reject nonexistent starts and late ends, and preserve true elapsed DST duration. Gap-opening regression also passes in unchanged developer checks. |
| V-S1-003: wrong reset reservations type mutates or returns wrong error | All six wrong-type regressions return 400 malformed_request and retain exact destination state. |
| V-S1-004: numeric snapshot carrier loses exact values | Unchanged numeric and upgrade suites pass the accepted-value lifetime and ordinary JSON carrier checks; original receipts preserve exact ignored numbers. |
| V-S1-005: checksum-valid forged receipt semantics accepted | Five adapted semantic corruptions and cross-owner B003 reject with exact nonmutation; unchanged valid controls and original receipts after amendment/cancel remain importable. |
| V-S1-006: valid local calendar edges exceed UTC host years | Four original offset/UTC cases and two additional full lifetimes pass availability/create, half-open occupancy, conflicts, list ordering, cutoff or amendments/moves/cancellation, replacement import and original retry. |
| V-S1-007: historical offset seconds violate RFC3339 | Both original historical cases pass strict syntax and exact instants. Four new calendar×zone lifetimes pass; Berlin year0001 is rendered 0001-01-01T00:00:32+00:54, retaining the exact instant −3,208,000,000 microseconds from the year1 UTC origin. Local booking time and restaurant timezone are unchanged. |

Primary current attempts, under this report directory:

- `20261005T080905.062080Z-common-fd843b8-eff73342/`
- `20261005T080928.813501Z-derived-fd843b8-13b0a578/`
- `20261005T080924.711898Z-numeric-fd843b8-bfe989e3/`
- `20261005T080943.362242Z-snapshot-adapted-fd843b8-829f3c04/`
- `20261005T080816.942869Z-calendar-edges-fd843b8-ecaa7cab/`
- `20261005T080819.653283Z-calendar-lifetime-fd843b8-59c898c3/`
- `20261005T080809.291565Z-historical-timestamps-fd843b8-a24cb1b1/`
- `20261005T080814.157049Z-timestamp-boundaries-fd843b8-115dd538/`

All case source hashes and primary manifest hashes are in the linked inventory
and matrix. Each original failure, offending SHA, expected/observed outcome and
repair observation remains in [the defect ledger](../defects.json).

## Definitions, executions and retained failures

| Lane | Raw outcome | Definition accounting |
|---|---|---|
| Unchanged official isolated harness | 120 PASS | 120 applicable official definitions |
| Original baseline | 100 PASS, 4 FAIL | 104 security/load definitions, original bytes retained |
| Supplied adjudicated baseline | 104 PASS | Same 104; no additional definitions |
| Common frozen suite | 43 PASS, 1 selector FAIL | 44 PASS after separate B003 adapter |
| Unchanged Stage 1 numeric | 12 PASS | 12 definitions |
| Unchanged upgrade 1→1 | 6 PASS | Six definitions; later edges pending |
| Main derived | 42 PASS | 42 definitions |
| Original semantic selectors | 5 selector FAIL | Same five logical cases as their adapters |
| Opaque state adapters | 6 PASS | Five semantic cases plus B003; zero new definitions |
| Additional pipeline/corruption | 9 PASS | Nine definitions |
| Calendar edge and full lifetime | 4 PASS + 2 PASS | Six definitions |
| Historical timestamps | 2 PASS | Two definitions |
| Historical/calendar cross-boundary lifetime | 4 PASS | Four definitions |
| Unchanged official detail execution | 120 PASS | Repeat official definitions with case-level instrumentation |

Raw instrumented pytest executions: **464 = 454 PASS + 10 FAIL**. The four
malformed-email original expectations demand 401, while Stage 1 §6 expressly
requires 422 for email outside local@domain. The separately supplied adjudicated
checks assert 422 and nonmutation. Six other raw failures are demonstrable opaque
selector/checksum mismatches caused by the string payload. Their original sources
and failure bytes are preserved; separate adapters decode/reseal the opaque payload
and retain the actual corruption/nonmutation assertions and valid control.

Reconciled distinct outcomes: **166/166 frozen**, **68/68 derived** and
**120/120 official PASS**. The baseline supplies **84 security + 20 load inputs**.
There are no pytest ERROR or SKIP results. The official Stage 2 overshoot probe
records one expected failure and 24 unexecuted checks, outside Stage 1 applicability.
Its failure is preserved and is not counted as a Stage 1 pass.

## Separate experiment and portability lanes

**37/37 unchanged developer methods PASS**, independently executed. These remain
separate from the independent and frozen definition totals.

Source publication experiments have eight defined operations, eight executed
controls and eight **actually injected operation names**: signup, login, create,
patch, cancel, moves, reset and import. Three fault-point types—response_encode,
candidate_encode and compression—produce **20 actual injection executions, all
PASS**. Reset's candidate_encode actually triggers ValueError, leaves exact state
unchanged and retries 204. These experiments make zero HTTP requests. Raw evidence:
`20261005T081035.829544Z-source-faults-fd843b8-0099abb0/`.

Four additional independent source formatter experiments pass both calendar
extrema with both signs of a fixed 3,208-second offset. They compare strict RFC3339
output against an independently calculated integer instant, with no product time
helper used as the oracle. These are **synthetic fixed-offset source experiments**,
not HTTP cases or a claim that IANA zones retain second offsets in year9999.
The maximum-boundary negative-offset result is `9999-12-31T23:59:27-00:54`,
preserving the exact instant. Evidence:
`20261005T081212.664980Z-formatter-bounds-fd843b8-95359e5e/`.

**Three actual producer-removal executions PASS across two integration definitions.**
Ordinary producers were current `fd843b8` and original `8958251`. Both verify old
tokens, hashed-password login, identities, changed/cancelled current records,
immutable creation/batch receipts, new writes and repeated replacement. The third
uses actual historical producer **15d1f178b387e744bf919b6e8bb77fff2b5aeb23**.
It creates four Berlin/New York bookings at year1800/year0001 through HTTP, exports,
removes the source container, verifies inspect fails, and only then starts a fresh
`fd843b8` destination. No opaque snapshot is constructed or modified.

Historical destination assertions pass: both existing tokens work; four current
lookup/list/availability projections use strict RFC3339 and exact IANA instants;
local fields and identities persist; occupancy rejects conflicts; original retries
return the **exact legacy receipt JSON**; reads/retries do not mutate imported state;
a new destination booking uses current formatting; repeated replacement restores
four records; password login and health work. Immutable old receipt responses
intentionally retain their producer's historical spelling. Current reads and all
new receipts use valid RFC3339; rewriting completed legacy receipt JSON would violate
the separate original-response preservation requirement. This is compatibility with
a prior defective producer, not permission for new invalid timestamp responses.

Historical primary evidence:
`20261005T081031.644789Z-upgrade-historical-removed-fd843b8-7623c76a/`.
The retained private snapshot hash is
`4eaac9107fefc185162ec8fcde55582d60c85a5e07e8efc8749069379215df11`.
Synthetic credential-bearing files were removed after consumption; safe hashes,
producer/consumer logs and actual removal proof remain. Other producer evidence is
`20261005T081021.529226Z-upgrade-current-fd843b8-c7fb18a8/` and
`20261005T081027.621294Z-upgrade-original-removed-fd843b8-c434d82d/`.

## Environment, timing and scope

Docker context colima-tablekeeper; service **2 CPU / 2 GiB**, read-only root,
tmpfs and owned internal network with no runtime outbound access. Client containers
had no added memory cap. Resource-sensitive suites ran sequentially. Two deployment
configurations pass: default PORT8080 and explicit18087, healthy from another
internal-network container in **0.5023 s / 0.5681 s**. Only owned containers/networks
were removed. Build/service/test logs, inspections, JSONL, JUnit, catalogs and source
hashes are retained. All 30 frozen input files and copies were rehashed against
manifest `91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036`.
Every current attempt manifest verifies; the standalone product checkout is clean.

Instrumented pytest traffic: **5,378 HTTP requests**, maximum50 in flight,
p50 **0.01723 s**, p95 **0.12332 s**, maximum **0.90849 s**;
**8,510,858 decompressed received bytes**. Load subset: **2,610 requests**,
p50 **0.01913 s**, p95 **0.12803 s**, maximum **0.82237 s**, maximum50 in flight.
These include setup and repeats. Raw sockets, unchanged official harness traffic,
standalone producer/deployment calls and source experiments are separate;
uninstrumented HTTP totals are unknown. Tests assert atomic state/occupancy and
immutable receipts, not only status codes or latency.

**21 APPLICATION-intent command attempts**, all completed, with no runner error,
timeout or OOM in this revision's execution. Sum of command durations **149.7640 s**;
execution window **2026-10-05 08:08:09.292186–08:12:12.813764 UTC**, **243.5216 s**.
The independent clean-checkout preparation is separately recorded and took5.1428 s.
Actual token use and billing are unavailable. Earlier failures and the prior
revision's QA invocation error remain preserved; no prior PASS is used as this
revision's execution evidence.
