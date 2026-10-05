# Stage 1 independent decision: REJECT

Product revision: **7d7643857eeac6396467a791d93b0fa7c43b8fa2**. Room:
`e04c2728-8535-41c8-be50-88eb8068fa09`. Verifier independently rebuilt the
committed bytes in the clean standalone checkout recorded in [the machine-readable
report](REVIEW-7d76438.json). No product files were edited by Verifier.

The five previously demonstrated defect families pass their direct regressions at
this revision. A new finite counterexample, **V-S1-006**, prevents acceptance.
Stage 2 remains gated by Coordinator. The earlier rejected reviews and raw failures
remain preserved; this result does not revise those historical outcomes.

## Open defect: valid local calendar extrema

Stage 1 §4 permits any calendar date. Sections 8–9 require local availability and
bookings using IANA offsets and absolute duration. Both cases below use valid local
dates, local starts and local ends entirely within opening hours. They fail when
an intermediate UTC datetime would lie outside Python's representable calendar.

Reset a fixture with a seeded user, restaurant `r`, tables including `a` capacity 4,
slot interval 30, duration 30, cutoff 0, and identical opening hours on all seven
weekdays. Log in. Then call public availability with the given date and party size 2,
and authenticated `POST /reservations` with a fresh key and body
`{"restaurant_id":"r","table_id":"a","starts_at_local":"DATE T START","party_size":2}`,
substituting the date/start below without spaces around `T`.

| Case | Fixture / request | Expected | Observed |
|---|---|---|---|
| D122-min-plus01 | `Etc/GMT-1` (+01:00), opens 00:00, closes 01:00, date `0001-01-01`, start 00:00 | Availability 200 including 00:00; create 201 ending 00:30+01:00 | Both 422 `validation_failed` |
| D122-max-minus01 | `Etc/GMT+1` (-01:00), opens 22:00, closes 23:59, date `9999-12-31`, start 23:00 | Availability 200 including 23:00; create 201 ending 23:30-01:00 | Availability 400 `malformed_request`; create 422 `validation_failed` |

Reset and login succeed; health remains 200. The same two local date boundaries in
UTC pass creation, export, import and original receipt replay. The offset cases
fail before that lifetime can be exercised, so their unexecuted later assertions
are not reported as passed.

Primary evidence:
`reports/stage-1/20261005T072858.901328Z-calendar-edges-7d76438-740406c1/`.
The independent test is [test_calendar_edges.py](../../qa/derived/test_calendar_edges.py),
SHA256 `bd4910aaa2b1db726ce70c783a0cd2c97ebc6eb276fe321d5b16e7efd99a501c`.
It implements the calendar extrema obligation already recorded under D109 before
implementation review. Run it through `qa/run_suite.py --suite calendar-edges`
against the clean product checkout, using `qa/attempt.py` for a new evidence directory.

## Reconciliation of earlier defects

| Defect | Independent evidence at this revision |
|---|---|
| V-S1-001 slow request lifetime | Frozen R002/R003 pass; D117 raw socket EOF at 3.0068 s for headers and 3.0020 s for body. Health and exact snapshot nonmutation pass. |
| V-S1-002 nonexistent DST closing boundary | Both frozen spring-gap closing cases pass with valid earlier availability. |
| V-S1-003 reset reservations wrong JSON type | All six D116 reset cases pass, requiring 400 and exact destination nonmutation. |
| V-S1-004 numeric snapshot carrier portability | All six unchanged upgrade definitions pass, including overflow, underflow and precision carrier cases; unchanged numeric Stage 1 suite 12/12 passes. |
| V-S1-005 inconsistent historical receipts | All five separately adapted semantic corruption cases reject with exact nonmutation. Unchanged historical receipt controls, later amendment/cancel/replacement retries and actual producer removal pass. |

The six original selector failures remain raw FAIL results: the current opaque
state payload is a JSON string, while B003 and the original five semantic selectors
expect an object. The separate adapter decodes the opaque payload and re-seals its
checksum; it retains the original assertions and validates an unchanged control.
Those six adapter executions add **zero** logical definitions. Original source
hashes, failed selector executions and adapted results are all retained.

## Executions and counts

| Lane | Raw result | Reconciled distinct result |
|---|---|---|
| Unchanged official isolated Stage 1 harness | 120 PASS | 120 official definitions PASS |
| Original baseline | 100 PASS, 4 FAIL | Same 104 definitions as adjudicated run |
| Supplied adjudicated baseline | 104 PASS | 104 PASS |
| Common frozen cases | 43 PASS, 1 opaque selector FAIL | 44 PASS with separate B003 adapter |
| Unchanged Stage 1 numeric | 12 PASS | 12 PASS |
| Unchanged upgrade 1→1 | 6 PASS | 6 PASS |
| Derived main cases | 42 PASS | 42 PASS |
| Original semantic corruption selectors | 5 selector FAIL | Same five definitions as separate adapter |
| Separate opaque adapters | 6 PASS | Five semantic definitions plus B003 above |
| Additional pipeline/state corruption | 9 PASS | 9 PASS |
| Calendar extrema | 2 PASS, 2 FAIL | 2 PASS, 2 FAIL; V-S1-006 open |
| Additional unchanged official detail execution | 120 PASS | Repeated official definitions, with per-case records |

Raw instrumented pytest executions total **456: 444 PASS, 12 FAIL**. The failures
comprise four original email oracle conflicts, six opaque selector mismatches and
two current product failures. After explicit reconciliation there are **166/166
applicable frozen definitions PASS**, **58/60 derived definitions PASS**, and
**120/120 official definitions PASS**. This does not imply overall acceptance.
The full case-to-source-to-attempt mapping is in [case-matrix-7d76438.json](case-matrix-7d76438.json).

S064–S067 expect 401 for malformed login email; Stage 1 §6 explicitly requires
422. Their original failures are preserved; the separately supplied adjudicated
run checks 422 and nonmutation. This does not double the 104 definition count.
The official next-stage probe's first failure and subsequent 24 unexecuted Stage 2
checks are preserved as the expected Stage 1 probe boundary, not Stage 1 passes.

Separate experiments, excluded from those pytest/definition totals:

- 27 unchanged developer methods independently executed: PASS.
- Source publication experiment: eight control operation names; 20 actual injected
  fault executions PASS across three distinct injected fault names. Reset and import
  exercise candidate preparation. Source injections are not HTTP requests, and list
  membership is not counted as an injection.
- Actual producer removal: two PASS executions of one integration definition.
  Source revisions `89582510069e984f446060d797e138f4a3bf08f9` and the current
  revision were populated, exported, stopped and removed before fresh destinations
  at the current revision started. Two old tokens, two original receipts, current
  cancelled state, hashed-password login, new writes and repeated replacement passed.
- Deployment: default PORT 8080 and custom PORT 18087 each PASS. First healthy
  responses took 0.5901 s and 0.4451 s. External client containers reached each
  service on an internal Docker network; service resource/read-only settings were
  inspected. These are two deployment configurations, not two new API definitions.

## Environment, timing and limits

The service used Docker context `colima-tablekeeper`, 2 CPU, 2 GiB, read-only root,
tmpfs and an internal network. Clients had no added memory cap. Heavy Docker clients
ran sequentially. The exact clean checkout, image/build logs, service/client/network
inspection, source hashes, raw case JSONL, JUnit and all attempt manifests are retained.
All 30 frozen files were rehashed against the pinned manifest and their unchanged QA
copies. All current attempt manifests verified without mismatches.

Instrumented pytest HTTP traffic: **5,180 requests**, maximum 50 in flight,
p50 0.01749 s, p95 0.10984 s, maximum 0.89058 s, 8,214,312 decompressed received bytes.
The load subset contains **2,610 requests**, p50 0.02013 s, p95 0.11236 s,
maximum 0.82384 s, maximum 50 in flight. Counts include setup and repeated executions.
They exclude raw socket traffic, standalone producer/deployment probes and the
unchanged official harness. Those uninstrumented request totals are unknown, not zero.

Sixteen application command attempts took a summed 144.5136 s. Their execution
window was 2026-10-05 07:18:20.156783–07:29:03.051119 UTC, elapsed 642.8943 s,
including analysis gaps. Actual token usage and billing are unavailable and remain
unknown. No ERROR, SKIP, timeout or OOM has been converted to PASS.

Evidence clarification: D117's raw `stopped_dripping_after_s=6.5` field records the
planned upper limit; its recorded events show the actual send loop ending on peer
closure at about three seconds. The original artifact is preserved. An ancillary
Git status invocation with an outside path returned 128; the corrected `git -C`
check confirmed the product checkout clean. That was a tooling error, not an
application test.

The Stage 1 gate remains rejected until V-S1-006 passes on a newly handed-off exact
revision and all applicable regressions are reconciled there. Later stages, remaining
upgrade edges, final documentation/provenance packaging and the final clean `--all`
run remain pending.
