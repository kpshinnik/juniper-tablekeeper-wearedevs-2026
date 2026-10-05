# Stage 2 independent review — ACCEPT

**Accepted Stage 2 product: `d8941d7e630c9f2787623d1222f647d49b40ae91`.** Verifier independently rebuilt this exact commit and completed the applicable gate. V-S2-001 passes its unchanged direct regression and additional confirmation/lookup/cancellation checks. All seven earlier Stage 1 defect families also pass direct regressions on this revision. **No product defect remains open in this review.** Coordinator must reconcile the gate before Stage 3 begins.

Room: `e04c2728-8535-41c8-be50-88eb8068fa09`. Clean standalone checkout: `/Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/d8941d7e630c9f2787623d1222f647d49b40ae91-e18b8411`. Service build context: its `stage-2/` directory. Stage 1 remains identical to accepted `fd843b83db16ec8585d66af7ac0d6fac89aae82c`. This is Stage 2 acceptance only; later-stage functionality and final packaging remain pending.

The [machine-readable review inventory](REVIEW-d8941d7.json) records the exact attempts, source/QA revisions, manifests, environment, outcomes and measurements. The [case matrix](case-matrix-d8941d7.json) binds every distinct pytest definition to original/adapted observations. The [coverage matrix](../../qa/COVERAGE.md) contains the full requirements and stage applicability; the [defect ledger](../defects.json) preserves all earlier rejected observations. The evidence commit is delivered in the native room decision after this report is committed, avoiding a self-referential hash.

## Repair verification

The product change from rejected `a96b13048d19a5d93d75bb6c51ee100e44a2d8fd` is confined to layout CSS: the mobile flow uses `minmax(0,1fr)`, grid children can shrink, and restaurant headings in availability/lookup wrap. Backend, browser JavaScript and accepted Stage 1 bytes are unchanged. The repair does not hide page overflow, truncate the heading or impose an input cap.

The unchanged D215 fixture places the literal text `<img src=x onerror="window.__qa_xss=1">` in valid restaurant, table and display labels. At 375px it previously produced a 392px document and failed; Builder's separate local reproduction measured 439px in its font environment. Both failures and hashes remain preserved. The original independent test source is unchanged: SHA256 `d921d62b9e682b1c1fb5512140c83b751f14a9fab065530cc36c428711f77762`.

Current [original browser regression attempt](20261005T093419.642127Z-stage2-browser-d8941d7-6c9587f9/) executes all eight definitions successfully, including both D215 widths. The [mobile capture](20261005T093419.642127Z-stage2-browser-d8941d7-6c9587f9/browser/test_D215_routes_labels_keyboard_layout_and_untrusted_text_D215-mobile_/final.png) shows full labels wrapping inside the viewport, usable time cells and form, visible focus, and no executed markup.

Two new, separately counted D218 definitions extend those labels through successful booking, unchanged retry, confirmed lookup and cancellation. These are additional flow coverage; the original D215 test was not rewritten. Source: `qa/derived/test_stage2_label_lifetime.py`, SHA256 `661a3491fe182019c66c9457e304e1cca9d3da52211e2c4793b32358a7263c25`; QA commit `3e97bde5e9f203380706c111f7b88137ce9a2a6b`. [D218 attempt](20261005T093900.649306Z-stage2-label-lifetime-d8941d7-c88f5ae3/) retains each geometry measurement, screenshot and trace.

| D218 measured state | Mobile document / viewport | Desktop document / viewport |
|---|---:|---:|
| Public availability grid | 375 / 375 | 1360 / 1360 |
| Signed-in grid | 375 / 375 | 1360 / 1360 |
| Booking form | 375 / 375 | 1360 / 1360 |
| Successful confirmation | 375 / 375 | 1360 / 1360 |
| Unchanged retry | 375 / 375 | 1360 / 1360 |
| Confirmed lookup | 375 / 375 | 1360 / 1360 |
| Cancelled lookup | 375 / 375 | 1360 / 1360 |

The full literal labels remain in the current-user, booking/confirmation and lookup text. The real create/retry statuses are 201/200, with identical body/key/receipt and exactly one diner booking. Cancellation remains usable and removes its action afterward. XSS nonexecution passes throughout. The measured width repair therefore extends beyond the original form-only counterexample.

## Counts and retained raw outcomes

| Evidence lane | Distinct definitions or separate experiments | Outcome |
|---|---:|---|
| Frozen security + load | 104 | 104 reconciled PASS; four original email oracle FAILs retained |
| Frozen boundary/auth/JSON/protocol/audit | 44 | 44 reconciled PASS; original B003 selector mismatch retained |
| Frozen compact occupied pair | 1 | PASS |
| Unchanged numeric lifetime, Stage 2 applicability | 14 | PASS, including original R2N002 extreme client |
| Frozen transfer | 6 | PASS on 1→2 and 2→2; count six once |
| **Frozen applicable total** | **169** | **169 PASS** |
| Prior independent pytest definitions | 68 | PASS |
| Pair/resource definitions D201–D208 | 11 | PASS |
| Browser definitions D211–D215 | 8 | PASS |
| Live browser transfer D216 | 1 | PASS on both edges; count once |
| Additional full-label lifetime D218 | 2 | PASS |
| **Independent pytest total** | **90** | **90 PASS** |
| Unchanged official Stage 1 + Stage 2 | 145 | 120 + 25 PASS |
| Unchanged Builder developer methods, independently executed | 47 | PASS; separate lane |
| Actual source publication fault injections | 20 executions | PASS across eight operation names and three fault types |
| Source formatter boundary experiments | 4 | PASS; synthetic offsets, not HTTP |
| Actual producer removal | 3 integration definitions, 5 executions | PASS; separate from pytest definitions |
| Deployment configurations | 2 | PASS |

There are **27 application command attempts** plus a separate clean-checkout preparation. Instrumented pytest records **521 raw executions: 511 PASS and 10 FAIL; zero ERROR or SKIP**. The ten failures are four original email-oracle conflicts and six original opaque-selector mismatches, each explicitly reconciled by separately executed checks. None is erased or silently recast as a raw PASS. Repeated suites, transfer edges, corrected oracles, adapters, requests and fault injections never inflate the distinct-definition totals.

The supplied frozen total across all stages remains 216 definitions; only its 169 Stage 2-applicable definitions are claimed here. The independent total increased from 88 to 90 solely because D218 adds two new flow definitions. Re-executing D215, D216 or any earlier defect does not create new definitions.

## Requirements and acceptance matrix

Row IDs refer to the full requirement text in `qa/COVERAGE.md`. Evidence PASS means the identified assertions and observations completed at this exact revision, not a proof of every possible input.

| Requirement rows | Current exact-revision evidence | Outcome / scope |
|---|---|---|
| AC01 provenance | Complete four-part repair handoff; independent standalone clean checkout; original/frozen hashes; own QA/evidence commits and path audit | PASS for this review; final native full room export remains a final-delivery requirement |
| AC02 runtime | Fresh single-container builds, internal offline networks, other-container health, 2 CPU/2 GiB, read-only root/tmpfs, default/custom PORT, isolated harness | PASS; readiness 0.604672s at 8080 and 0.476652s at 18087 |
| S1-01, S1-14–18 | Official reservations, security/load, D112/D118–120 and D207 | PASS: identity, ownership, half-open occupancy, concurrent serialization, cutoffs, mutation and cancellation |
| S1-02–06, S1-12–13 | Official reset/restaurants/availability, common44, D101–103/D106–107/D109–110, numeric14 | PASS: reset, structured errors/types, JSON, ignored fields, exact queries, grid and local boundaries |
| S1-07–11 | Original/adjudicated104, auth8, D104–108/D119 and numeric equality | PASS after explicit four-email adjudication: auth, password hashing, retained sessions, exact-body key scope/precedence and immutable replay |
| S1-19 | Official time tests, audit30, spring closing regressions, D122–127 | PASS: absolute DST duration, first folds, absent gaps, historical RFC3339 and calendar extrema |
| S1-20–22 | Frozen transfers both edges; B003/D116 adapters, D121, numeric lifetime, five actual-removal integrations | PASS: replacement, invalid-state exact nonmutation, detached portability, old credentials/references/receipts |
| S1-23–25 | Official moves, load, D113/D119, D204–206, numeric/transfer receipts | PASS: ordered atomic batches, no-op/cutoff/error precedence, reusable failed keys and original replay |
| S2-01–04 | Official UI17, D211–216 and D218 | PASS: four HTML routes, auth/navigation/testids, exact grid state, retained forms, confirmation and lookup/cancel |
| S2-05 | D213 single/pair confirmed refusals and D214 actual delayed earlier response | PASS: preserved inputs, error/refresh without false confirmation; late A cannot replace B's grid/labels/form |
| S2-06 | D211 real POST201 fetched then aborted; two-booking swap and pair-to-single repair; D212 | PASS: retained body/key/form/uncertainty, original immutable receipt, current confirmation/lookup/grid |
| S2-07 | D216 real retained browser on 1→2/2→2 plus separate D115/D217 removal integrations | PASS; disclosed Stage 1 browser transport adapter below |
| S2-08–12 | Official pair API/UI, D201–208, compact-pair and numeric14, transfer | PASS: declarations/nontransitivity/order, exact capacity, selector errors, cancelled seeds, full-member occupancy, atomic moves and pair/single formats |
| AC03 / publication boundary | Full applicable API definitions, D114 source injections, deep/exact lifetimes and actual postcommit response-loss retries | PASS for exercised boundaries; no observed partial publication |
| AC04 visual/mobile | Unchanged D215 regression, D218 full-label flow, actual inspected desktop/mobile/focus/loading/empty/refused/uncertain/success captures | PASS; V-S2-001 resolved at this exact SHA |
| AC04.5 exact browser integers | D212 party 9007199254740993 through query, form, raw JSON, real loss and unchanged retry | PASS |
| AC07 applicable execution and reconciliation | Frozen169, independent90, official145; all historical counterexamples directly re-executed; distinct raw failures and adapters | PASS; no open observed product counterexample |
| AC05 / AC06 / S3 / S4 | Later policy/history/series/optimizer/closure contracts and remaining upgrade edges | Not applicable yet; pending later stage gates, not counted as PASS |
| AC08 | Current exact clean checkout and unchanged isolated per-stage harness | Current review PASS; final immutable `--all` delivery gate remains pending |
| AC09 | Final guides/storyboard/mandates/full room export and delivery packaging | Pending final delivery with assigned owners; no public action or real booking |
| AC10 | Exact product/evidence attribution, raw artifacts/hashes, independent counts and measured time/usage limits | PASS for review evidence; actual token usage and billing unknown |

## Every earlier defect reconciled at the repair SHA

| Defect | Direct evidence | Outcome |
|---|---|---|
| V-S1-001 | R002/R003 continuous transport, D117 header/body actual peer EOF, health and exact nonmutation | PASS |
| V-S1-002 | R008 spring-gap opening/closing boundaries in Berlin and New York | PASS |
| V-S1-003 | D116 wrong reset reservations JSON types, 400 and exact nonmutation | PASS |
| V-S1-004 | Original numeric accepted lifetimes and U003–U005 ordinary-client JSON replacement portability | PASS |
| V-S1-005 | Five checksum-valid semantic receipt corruptions and B003 through separate selectors, unchanged valid controls | PASS |
| V-S1-006 | D122 four calendar edges and D123 two full offset-extrema lifetimes | PASS |
| V-S1-007 | D124 historical IANA, D125 year0001/year9999, actual old producer D126 and source formatter D127 | PASS |
| V-S2-001 | Unchanged D215-mobile and desktop; additional D218 confirmation/retry/lookup/cancel geometry and full labels | PASS |

Original Stage 1 resolved SHA remains `fd843b83…`; its old failures and repair history are preserved. Original Stage 2 rejection `a96b130…`, evidence `06653fae61e2c505ac3a9eb863e24982a675dcee`, remains unchanged. Its 392px independent and 439px Builder observations are not overwritten by the current result. The superseded `705e187…` partial review also remains historical evidence.

## Exact extreme-number lifetime

[Numeric attempt](20261005T093635.958253Z-numeric-d8941d7-0b70505e/): all 14 original applicable definitions pass. R2N002-e100000000 received/decompressed **1,100,002,780 availability bytes in 3.790672237999388 seconds**, satisfying its unchanged five-second HTTP assertion. The service was constrained to **2 CPU / 2 GiB**; the original client had **no added memory cap**.

The original complete `json.loads` with Decimal integer/float callbacks then parsed all **1,100,002,780 input bytes** in **4.882439195993356 seconds**, separately measured. It returned a complete dictionary. Observed client peak RSS was **2,843,532 KiB**, with 2,233,556 KiB before that parse. Content-Encoding was gzip; declared Content-Length was 4,801,658, a header observation rather than independently measured wire bytes. The later case property `response_bytes: 342` is a subsequent response, not availability size.

No frozen source/assertion was changed, no approximate numeric value or streaming/hash substitute was used, and full accepted-value create/mutation/list/export/import/cancel/original-retry assertions completed. Occupied excluded pairs separately remain compact/fast under the original compact-pair case. This demonstrates the specified finite example; it does not establish a bound on every finite input. Server-only generation time was not separately measured.

## Transfers and publication faults

The six unchanged transfer definitions pass on **1→2** and **2→2**. D216 additionally retains a real live browser's session, form, original body/key and reference while state is exported/imported between requests. Stage 1 does not serve required HTML; the explicit 1→2 adapter loads actual Stage 2 HTML once, routes API requests to the real Stage 1 producer, then switches API traffic to the imported destination. There is no DOM/session injection or page reload. This browser lane does not claim source removal; the following separate integration lane does.

Five actual removal executions use three integration definitions. In each, source export is retained privately, the source container is stopped/removed, a failed subsequent source inspection proves removal, and only then is the fresh destination created. Password login, two retained tokens, references, exact original receipts, repeated replacement and new target operations pass where applicable:

- D115: accepted Stage 1 `fd843b83…` → current Stage 2; current Stage 2 → itself; original object-state producer `89582510…` → current Stage 2. Create and batch receipts remain original, and new target `table_ids` writes work.
- D126: historical producer `15d1f178…` → current Stage 2. Four original legacy receipts retain their stored values exactly; current output has strict RFC3339 coordinates for the same exact instants, including two year0001 records. No synthetic legacy fixture replaces this producer run.
- D217: real accepted Stage 1 bodies include formerly unknown `table_ids` alongside valid `table_id`. Original receipt body identity survives removal/import. Changed ignored values with the old key conflict; fresh Stage 2 both-selector requests reject atomically; current valid target writes succeed.

Publication testing defines eight operations, executes eight controls, and **actually injects faults into all eight**: signup, login, create, patch, cancel, moves, reset and import. There are **20 injection executions** spanning response encoding, candidate encoding and compression, all PASS. Reset's candidate encoding genuinely raises ValueError, leaves exact state unchanged and retries successfully with 204. These source experiments are not HTTP requests; control-list membership is not substituted for an actual injection. Four separate source formatter experiments verify both signs of synthetic ±3208-second offsets at both calendar extrema against independent integer instants; they are not HTTP tests or predictions of future IANA rules.

## Visual review

Real current captures were inspected for mobile literal-label form, successful label confirmation, cancelled label lookup, mobile closed day, mobile pair uncertainty/current confirmation, desktop two-booking repair/current confirmation, desktop pair refusal, delayed-search loading and mobile signup keyboard focus.

They show a consistent evergreen/cream restaurant interface with readable hierarchy, prominent human labels, intentional combined-table options and distinct selected/available/unavailable states. Primary actions and form labels remain clear at 375px and desktop. The focus indicator is visible. Empty and loading feedback are distinct; confirmed refusal retains inputs and refreshes the grid; uncertainty contains a truthful retry instruction with no false confirmation. Success after repair shows current server assignment while the original form and receipt remain unchanged. Long literal restaurant/table/diner text wraps fully on the relevant screens without enlarging the viewport or executing markup. Computed-style and focus records supplement the screenshots. This is an evidence-based visual review of exercised states, not exhaustive WCAG certification.

## Oracle, representation and historical tooling reconciliation

Four unchanged baseline malformed-email login expectations say 401, contrary to Stage 1 §6's explicit 422 rule. The original four failures remain. The unchanged frozen auth suite independently substantiates the rule; the separately corrected baseline passes with exact nonmutation assertions. Its repeated 104 definitions count once.

One B003 and five original semantic-corruption cases use selectors for an older opaque representation. Their six failures remain. The separate adapter selects within the current exact JSON-string payload, recomputes the envelope digest and applies the same corruption assertions. All six adapted cases reject with 422 and exact destination nonmutation, alongside accepted unchanged controls. This is an attributed selector adaptation, not a hidden product fix, ignored failure or extra definition.

The rejected a96b130 review's two detailed-official tooling failures remain untouched: duplicate `test_sample.py` module names prevented first collection; the next run had a missing previous-service setup error after 144 passes. Its corrected run and unchanged isolated harness remain separate artifacts. On **this** revision the corrected detailed invocation uses importlib and a real previous-stage container from the outset, and all 145 unchanged required definitions pass. No official source or assertion changed. This revision has no pytest ERROR/SKIP.

The unchanged isolated harness separately passes required Stage 1 and Stage 2 contexts, reporting highest contiguous stage 2. Its expected Stage 3 probe collects seven and stops after one failure; unexecuted probe cases are not counted as passes. The probe does not authorize Stage 3 product work.

## Measurement and integrity limits

The 27 application command durations total **223.57367087341845 seconds**. Execution window: **2026-10-05 09:34:19.642701–09:39:08.002761 UTC**, **288.36006 seconds**. These are command/window durations, not billed model time.

| Instrumented HTTP lane | Requests | Max observed in flight | p50 seconds | p95 seconds | Max seconds |
|---|---:|---:|---:|---:|---:|
| All recorded pytest httpx | 5,699 | 50 | 0.016628968 | 0.237800753 | 3.790672238 |
| Load subset | 2,610 | 50 | 0.018332688 | 0.246516425 | 0.807768672 |

Recorded decompressed bytes total 1,114,221,801; load subset 10,015,592. Counts include instrumented setup and repeated requests and exclude raw sockets, Playwright traffic, standalone producer/deployment clients, source experiments and unchanged isolated-harness calls. Uninstrumented HTTP totals remain unknown. Passing load assertions verify atomic state, occupancy and original receipts; later-stage histories and revision counters are not applicable yet.

All current attempt manifests verify. All 30 frozen originals/copies match pinned manifest **`91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036`**. Product checkout remains clean and accepted Stage 1 unchanged. Evidence is local synthetic project data. Actual token usage and billing are unknown. Final four-stage `--all`, full room export, final documentation/delivery and public submission are not claimed by this Stage 2 acceptance.
