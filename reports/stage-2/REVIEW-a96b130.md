# Stage 2 independent review — REJECT

Product: **`a96b13048d19a5d93d75bb6c51ee100e44a2d8fd`**. Room: `e04c2728-8535-41c8-be50-88eb8068fa09`. Reviewer: Verifier.

**V-S2-001 remains open:** valid literal restaurant, table and diner labels cause horizontal page scrolling at a 375 CSS-pixel viewport. The measured document width is 392px. This violates Stage 2's explicit mobile requirement and AC04. The passing suites do not override this counterexample. Stage 3 is not authorized by this review.

The exact clean checkout is `/Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/a96b13048d19a5d93d75bb6c51ee100e44a2d8fd-3bc9767d`. The service was independently built from its `stage-2/` context. Stage 1 bytes remain identical to accepted `fd843b83db16ec8585d66af7ac0d6fac89aae82c`; Stage 1 acceptance and its original evidence are preserved. The evidence commit is delivered in the native room decision after this report is committed, avoiding a self-referential hash.

The machine-readable [review inventory](REVIEW-a96b130.json) binds every application attempt, manifest, recorded QA revision, source hash, outcome and metric. The [case matrix](case-matrix-a96b130.json) preserves each distinct definition and its original/adapted observations. [Coverage](../../qa/COVERAGE.md) maps the full supplied requirements and future applicability; [the defect ledger](../defects.json) retains every earlier rejection.

## Required repair and minimal reproduction

Case: `qa/derived/test_stage2_browser.py::test_D215_routes_labels_keyboard_layout_and_untrusted_text[D215-mobile]`.

1. Reset the synthetic D215 fixture: UTC restaurant, 2030-01-01, ordinary tables and one diner. Use literal text `<img src=x onerror="window.__qa_xss=1">` after the restaurant name `Garden `, table-a label `Window ` and diner display name `Browser diner `.
2. At a 375px viewport, log in, search 2030-01-01 for party size 2, and open `slot-a-18:00`.
3. Read `document.documentElement.scrollWidth` and `innerWidth`.

Expected: labels remain literal text and the page fits 375px without horizontal scrolling. Observed: XSS nonexecution assertions pass, but **392 > 375**, a 17px overflow. The actual screenshot confirms the layout defect. Preserve full valid labels and the required workflows when repairing their layout; an invented label restriction does not satisfy the input contract.

Primary attempt: [20261005T090918.334404Z-stage2-browser-a96b130-a10dc62b](20261005T090918.334404Z-stage2-browser-a96b130-a10dc62b/). It contains the original log, JSONL, JUnit, trace and screenshots. [Failing mobile capture](20261005T090918.334404Z-stage2-browser-a96b130-a10dc62b/browser/test_D215_routes_labels_keyboard_layout_and_untrusted_text_D215-mobile_/final.png).

| Artifact | SHA256 |
|---|---|
| Test source | `d921d62b9e682b1c1fb5512140c83b751f14a9fab065530cc36c428711f77762` |
| cases.jsonl | `0f446cf7b80b503a8209b6eb0b02c24e5e309aee6bfc6eb92a88af12ed13daaf` |
| tests.log | `4ebc14b8c113f5b5a36ca9608829ec8df43165e15e9b739526840551dcf159d4` |
| manifest | `c7141837a4fd676e5360094d5c617168ef747a8c150aced5547f903826b0cfd9` |
| final.png | `1a9120a4901d0d926d102eec79cf6e8577986662a6845daef3103ba5fa65f290` |

Builder must supply a fresh exact commit and complete review handoff. Acceptance requires this unchanged direct regression to pass there, plus applicable regression coverage at that same revision. No product files were repaired by Verifier. There are no other unreconciled product defects from this completed review.

## Results and counting

| Lane | Distinct definitions / experiments | Current outcome |
|---|---:|---|
| Frozen security and load | 104 | 104 reconciled PASS; original four email failures retained |
| Frozen common boundary/auth/JSON/protocol/audit | 44 | 44 reconciled PASS; one opaque selector adaptation |
| Frozen compact occupied pair | 1 | PASS |
| Unchanged numeric lifetime, STAGE_UNDER_TEST=2 | 14 | PASS, including original extreme client |
| Frozen transfer | 6 | All PASS on both 1→2 and 2→2; count six once |
| **Frozen applicable total** | **169** | **169 PASS after explicit reconciliation** |
| Prior independent pytest definitions | 68 | PASS, including all seven earlier defect families |
| New pair/resource pytest definitions | 11 | PASS |
| New browser pytest definitions | 8 | 7 PASS, **D215-mobile FAIL** |
| Live browser transfer D216 | 1 | PASS on both edges; count once |
| **Independent pytest total** | **88** | **87 PASS / 1 FAIL** |
| Unchanged official Stage 1 + Stage 2 | 145 | 120 + 25 PASS |
| Unchanged Builder developer checks, independently executed | 47 methods | PASS; separate from independent definitions |
| Source publication fault injection | 20 executions | PASS; eight actual operation names, three fault-point types |
| Source formatter boundary experiments | 4 | PASS; synthetic offsets, not HTTP |
| Actual producer removal | 3 integration definitions, 5 executions | PASS; separate from pytest totals |
| Deployment configurations | 2 | PASS; default and overridden PORT |

There were **28 application command attempts** and a separate clean-checkout preparation attempt. Instrumented pytest recorded **664 raw executions: 652 PASS, 11 FAIL, 1 ERROR, zero SKIP**. The failures are one open product defect, four original email-oracle conflicts and six opaque-selector mismatches. The error is a retained QA invocation/setup error. A separate failed collection attempt executed no cases. Repeated suites, edges, corrected oracles, adapters, requests and developer methods do not create new independent definitions.

The unchanged isolated official command was run from the read-only official directory with `--track tablekeeper --repo <exact-clean-checkout> --stage 2 --mode isolated`. It reports both required stages passing and highest contiguous stage 2. Its expected next-stage probe records one Stage 3 failure after collecting seven; the remaining probe cases are not passes. This is neither a Stage 2 defect nor authorization to implement Stage 3. A separate detailed execution of all 145 unchanged required official definitions also passes.

## Explicit requirement and acceptance binding

The row IDs below refer to the full requirement text in `qa/COVERAGE.md`; the case matrix supplies individual expected/observed outcomes, durations, hashes and attempt bindings. PASS here means the listed evidence completed, not a proof of all possible inputs.

| Requirement rows | Evidence at this exact product | Outcome / scope |
|---|---|---|
| AC01 provenance | Clean standalone SHA, unchanged Stage 1 tree, frozen manifest and all 30 original/copied files rehashed, genuine full handoffs and owned QA commits | PASS for review provenance; final full room export belongs to final delivery |
| AC02 runtime | Internal-network service and client, 2 CPU/2 GiB, read-only root/tmpfs, default and custom PORT, independent build and isolated harness | PASS; readiness 0.471401s at 8080 and 0.435950s at 18087 |
| S1-01, S1-14–18 | Official reservations, security/load, D112/D118–120, pair/member concurrency | PASS: occupancy, ownership, identities, cutoff, amendments/cancels and retry effects |
| S1-02–06, S1-12–13 | Official reset/restaurants/availability, common44, D101–103/D106–107/D109–110, numeric14 | PASS: reset, types, JSON, unknown fields, exact query values, grid and local boundaries |
| S1-07–11 | Original/adjudicated104, auth8, exact-body and scope cases D104–108/D119 | PASS after explicit four-email adjudication: auth, password hashing, multiple tokens, key scope/precedence and immutable original replay |
| S1-19 | Official time tests, audit30, spring boundary regressions, D122–127 | PASS: true elapsed DST, first fold, absent gaps, historical RFC3339 and local calendar extrema |
| S1-20–22 | Frozen six transfers on both edges, B003/D116 adapted semantic corruption, D121, numeric lifetime and five actual-removal executions | PASS: replacement, invalid-state nonmutation, detached portability, old tokens/references and original receipts |
| S1-23–25 | Official moves, load, D113/D119, D204–206, numeric and transfer receipts | PASS: ordered atomic batches, no-op/cutoff/error precedence, failure key reuse and original replay |
| S2-01–04 | Official 17 UI definitions, D211–215 and real captures | Required routes/auth/testids/search/form/confirmation/lookup behavior PASS; overall visual gate fails as below |
| S2-05 | D213 single/pair refusals, D214 actual delayed earlier search | PASS: preserved inputs/error, refreshed grid, no false confirmation; late A does not restore B's grid/labels/form |
| S2-06 | D211 single two-booking swap and pair-to-single repair, D212 exact party with real loss | PASS: real POST201 fetched then aborted; unchanged body/key/form; original receipt and current confirmation/lookup/grid distinguished |
| S2-07 | D216 on 1→2 and 2→2; separate D115/D217 source removal | PASS: retained live page/session/form/retry/reference; explicit Stage 1 transport adapter below |
| S2-08–12 | Official pair API/UI, D201–208, compact-pair input, numeric14 and transfer | PASS: declarations/nontransitivity/order/capacity, selector errors, cancelled seeds, full-member occupancy, atomic moves, pair labels and singleton compatibility |
| AC03 / preparation failure boundary | D114 source injections, exact-state checks, real postcommit loss/replay cases | PASS for exercised failures and all applicable API definitions |
| AC04 visual/mobile | D215×2 plus inspected desktop/mobile/loading/empty/refused/uncertain/success captures | **FAIL V-S2-001 at 375px with valid literal text** |
| AC04.5 exact browser numbers | D212 party 9007199254740993 through query, form, raw JSON, committed loss and unchanged retry | PASS; no JS safe-integer rounding |
| AC07 complete applicable execution | Frozen169, independent88, official145, prior failures and extra experiment lanes | Execution complete; gate **FAIL** until V-S2-001 is repaired and independently reverified |
| AC05 / AC06 / S3 / S4 | Later policies/history/series/optimizer/closures and remaining transfer edges | Not applicable to Stage 2; pending later gates, not skipped as PASS |
| AC08 | This review uses a clean exact checkout; final `--all` immutable delivery remains future work | Current checkout/harness evidence PASS; final requirement pending |
| AC09 | Final multilingual guides/storyboard/mandates/native room export | Final delivery remains pending with assigned owners; no publication or real booking performed |
| AC10 | Raw artifacts, source hashes, counts, measured times and explicit unknown usage | PASS for this review; actual token usage and billing unknown |

## Every earlier product defect re-executed

| Defect | Direct current regression evidence | Result |
|---|---|---|
| V-S1-001 | R002/R003 continuous transport; D117 header/body actual peer EOF and exact nonmutation | PASS |
| V-S1-002 | R008 spring-gap opening/closing boundaries in Berlin and New York | PASS |
| V-S1-003 | D116 reset reservations wrong JSON types, 400 and exact state nonmutation | PASS |
| V-S1-004 | Original numeric accepted lifetimes and U003–U005 ordinary-client JSON snapshot portability | PASS |
| V-S1-005 | Five checksum-valid semantic receipt corruptions through separate adapter, B003 and valid unchanged control | PASS |
| V-S1-006 | D122 four calendar edges and D123 two complete boundary lifetimes | PASS |
| V-S1-007 | D124 historical IANA cases, D125 combined year0001/year9999 lifetimes, D126 actual older producer, D127 formatter extremes | PASS |

The original rejected revisions, bytes, logs and their evidence commits remain unchanged. Their Stage 1 resolved SHA remains `fd843b83db16ec8585d66af7ac0d6fac89aae82c`; this report adds Stage 2 regression observations rather than rewriting history.

## Extreme exact-number evidence

Attempt: [20261005T091207.716517Z-numeric-a96b130-7e599d3c](20261005T091207.716517Z-numeric-a96b130-7e599d3c/). All 14 unchanged applicable numeric definitions pass.

For **R2N002-e100000000**, the actual availability response was **1,100,002,780 received/decompressed bytes**. The unchanged five-second HTTP assertion covers send/receive/decompression, measured at **3.1193484340037685 seconds**. Its gzip `Content-Length` header declared 4,801,658 bytes; this is a header observation, not a measured wire-byte count.

The original complete `json.loads(parse_int=Decimal, parse_float=Decimal)` then parsed all **1,100,002,780 input bytes** in **5.204056956994464 seconds**, measured separately from that HTTP assertion. It returned a complete dictionary. The uncapped client's observed peak was **2,867,380 KiB** (before parse, 2,209,356 KiB); the service remained limited to **2 CPU / 2 GiB**. No new client cap, streaming/hash substitute, altered assertion or approximate value was used. The case completed its accepted-value lifetime, including mutations, list/export/import/cancel and immutable original retry. Its later `response_bytes: 342` property belongs to a subsequent response and is **not** the availability size.

This establishes success for this finite case, not a bound on every finite input. Server-only generation time and measured wire bytes were not independently established. Excluded occupied-pair behavior separately passed the unchanged compact-pair case without expanding the unavailable huge sum.

## Portability, publication and browser evidence

Frozen transfer definitions all pass on **1→2** and **2→2**. D216 exercises a real retained browser across both edges without reload, form replacement or session injection. Because Stage 1 has no HTML contract, the 1→2 adapter loads the actual target Stage 2 HTML once, routes its API traffic to the actual Stage 1 source, then switches API routing to the imported destination between requests. This disclosed transport adaptation does not claim Stage 1 served a UI. Actual container removal is verified in the separate integration lane.

Five producer-removal executions genuinely stop and remove the source before creating the fresh destination. The preserved inspection proof records removal and that the destination was not started yet:

- D115: accepted `fd843b83…` Stage 1 → current Stage 2, current Stage 2 → itself, and original `89582510…` object-state producer → current Stage 2. Old tokens, references, password login, original create/move receipts, repeated replacement and new target `table_ids` writes pass.
- D126: actual historical `15d1f178…` producer → current Stage 2. Four exact original receipts, including their legacy timestamp spellings, remain immutable; ordinary current reads have equivalent strict RFC3339 timestamps and exact year0001 instants. No constructed fixture is substituted for this producer execution.
- D217: accepted Stage 1 producer receives legacy bodies containing valid `table_id` and formerly unknown `table_ids`. After source removal/import, original bodies and responses still replay exactly. Changing the formerly ignored field under the old key conflicts; a fresh Stage 2 request containing both selectors rejects atomically; new valid Stage 2 writes succeed.

Source publication testing defines eight operations, executes eight successful controls and **actually injects faults into all eight**: signup, login, create, patch, cancel, moves, reset and import. There are **20 injection executions**, spanning response encoding, candidate encoding and compression; all pass exact nonmutation/retry assertions. Reset's candidate-encoding injection actually raises `ValueError`, leaves exact state unchanged and subsequently retries with 204. Controls and source injections are not HTTP requests. The four independent formatter experiments use synthetic ±3208-second offsets at both calendar extrema; they check strict grammar and independently computed exact integer instants, with no claim about future IANA rules.

Actual inspected browser screenshots show a coherent evergreen/cream hospitality design, readable hierarchy, intentional pair presentation, labeled controls and visible keyboard focus. The single swap capture shows the retained original form alongside the current Garden nook confirmation. The mobile pair-loss capture shows nonempty uncertainty and retry action without false confirmation. The refusal capture shows the corrected layout-independent wording, preserved form and refreshed unavailable grid. Loading and closed-day states are distinct. The long-label mobile final and empty-state captures expose the overflow defect. The failing mobile case did not reach its final style-evidence capture; that unexecuted tail is not a PASS. Visual inspection is not an exhaustive WCAG certification.

## Raw failures, adaptations and tooling reconciliation

Four unchanged baseline login cases expect 401 for malformed emails. Stage 1 §6 explicitly requires 422 for email not of the form `local@domain`; the separate auth suite and corrected baseline assert that rule plus nonmutation. The raw four FAILs and original file hashes remain. The corrected execution is the same 104 definitions, not 104 additions.

One frozen B003 and five prior semantic-corruption cases initially select fields in an earlier opaque state representation. Their six original failures remain. A separately attributed selector adapter decodes the current exact JSON-string carrier and recomputes its checksum for the same corruption assertions; all six adapted cases pass with exact destination nonmutation. This is QA representation adaptation, not a product defect or skipped PASS. Original source hashes and bodies remain in the evidence.

The first detailed official invocation failed collection because Stage 1 and Stage 2 both contain `test_sample.py`. Changing only the QA invocation to `--import-mode=importlib` resolved that collision. Its next attempt ran 144 PASS and one setup ERROR because the required previous-stage service URL was absent. The QA runner then supplied a real constrained Stage 1 container on the same internal network, its previous-base URL, readiness/log/inspection and cleanup. The next attempt executed all 145 definitions successfully. Both tooling failures and original logs are retained; no official test source or assertion was edited. The unchanged official isolated harness separately passed. Earlier preparation errors and the partial superseded `705e187…` execution also remain preserved.

## Measurements and limits

Application command durations sum to **260.88677574694157 seconds**. The execution window is **2026-10-05 09:09:12.545553–09:18:34.193217 UTC**, elapsed **561.647664 seconds**. These are measured command/window durations, not billed model time.

| Instrumented HTTP lane | Requests | Maximum observed in flight | p50 seconds | p95 seconds | Maximum seconds |
|---|---:|---:|---:|---:|---:|
| All recorded pytest httpx calls | 6,228 | 50 | 0.017990252 | 0.260740464 | 3.119348434 |
| Load subset | 2,610 | 50 | 0.023292949 | 0.269747377 | 0.845646552 |

Recorded decompressed bytes total 1,114,273,244; the load subset totals 9,982,060. These counts include instrumented setup/repeated requests. They exclude raw sockets, Playwright browser traffic, standalone producer/deployment clients, source injections and the unchanged isolated harness. Uninstrumented total requests are unknown. The passing load assertions include once-only receipts, conflict serialization and exact final occupancy/state; later-stage histories and revision counters are not applicable yet.

All 30 frozen original/copy hashes match manifest `91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036`. Every current attempt manifest was verified. Evidence contains synthetic project data only. Actual token usage and billing are unknown. No hidden-test, universal numeric bound, final four-stage delivery, public publication or acceptance claim is made.
