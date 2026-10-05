# Stage 2 independent repair review — ACCEPT

**ACCEPT Stage 2 product `63cf798cf60baf3134a64e4db599c92d81561e3e`.** Fresh independent execution closes V-S2-002 and directly retains all eight earlier defect-family repairs. No observed Stage 2 product defect remains open. Coordinator must reconcile this gate before Builder carries the correction into Stage 3. Existing Stage 3 `0c0a386…` remains rejected; this decision does not qualify its unchanged browser code.

Room: `e04c2728-8535-41c8-be50-88eb8068fa09`. All five Coordinator recovery handoff parts were visible before execution. Clean standalone checkout: `/Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/63cf798cf60baf3134a64e4db599c92d81561e3e-effba660`; build context `stage-2/`. Its 3,791 tracked files match the committed revision. Stage 1 remains byte-identical across 28 files to accepted `fd843b83db16ec8585d66af7ac0d6fac89aae82c`; existing rejected Stage 3 remains byte-identical across 120 files to `0c0a3867fc38fff0824ec2f887a135a2965bb60f`.

Primary inventory: [REVIEW JSON](REVIEW-63cf798.json), [complete case matrix](case-matrix-63cf798.json), [product/source provenance](provenance-63cf798.json), [cumulative requirement matrix](../../qa/COVERAGE.md), [defect ledger](../defects.json). All **31 attempt manifests / 810 artifact files** verify. The evidence commit is supplied in the native room decision after committing these files. Prior [acceptance](REVIEW-d8941d7.md), [reopening addendum](ADDENDUM-d8941d7-V-S2-002.md), and [Stage 3 rejection](../stage-3/REVIEW-0c0a386.md), including every original failure, remain intact.

## Repair and direct evidence

The product changes both guest controls to decimal text with numeric keyboard hints, retaining whole-number validation, and wraps long search-summary text. Backend and Docker bytes are unchanged. The review independently rebuilt the committed image with 2 CPU / 2 GiB, read-only root, tmpfs and internal runtime networks; no mutable product checkout or Builder local pass substitutes for these results.

| Fresh browser evidence | Definitions | Result |
|---|---:|---|
| [D219 original search/booking entry](20261005T105553.230863Z-native-range-63cf798-c4959dd3/) | 2 | PASS: exact 401-digit input through real committed 201 loss, identical body/key, original receipt 200 and one booking |
| [D220 new geometry lifetime](20261005T105614.174563Z-numeric-geometry-63cf798-867683ad/) | 2 | PASS: 375/375 and 1360/1360 document/viewport at search, form, uncertainty, retry-confirmation and current lookup |
| [D221 new invalid-entry recovery](20261005T110028.234718Z-integer-validation-63cf798-b49291cf/) | 2 | PASS: eight invalid values per control, visible errors, no request/state mutation; labelled focused keyboard input corrected to 2 creates one booking |
| [D211–D215 prior browser regressions](20261005T105821.993158Z-stage2-browser-63cf798-93c2ad45/) | 8 | PASS: single/pair lost response with repaired current assignment, exact 9007199254740993, refused requests, stale search, XSS-safe labels and both widths |
| [D218 full-label lifetime](20261005T105837.422026Z-stage2-label-lifetime-63cf798-329cd75e/) | 2 | PASS: confirmation, retry, current lookup and cancellation retain literal labels and viewport bounds |

D219 source is unchanged: SHA256 `94c5f02b0cb6eb01eeacb555ca013e52a28a4ce562ccd1a39ac44865a0ff1346`. D220 source is `a55a576ea949294e47a8922248cc093da15c6b34913aa1db71e8d2cc80074994`; D221 is `4728290cc86090112196be20621fcb8a2c198fdfaf11c8d06905b51488e982af`. Initial QA revision is `096c598bb9affe4df73ec4df773b0a4082aee960`; D221 and later execution lanes use `1980eff20b6cf18ec56b65db6f231d4f6e57c911`. The earlier QA login helper synchronization (`a534f9c…`) waits for the product's real redirect; original D215 assertions remain. Its previous navigation-race failures stay in the Stage 3 report.

D220 reads actual text fragments and clipping ancestors without modifying the DOM. The full count remains rendered where the search summary appears; input values stay exact even when the editable control scrolls internally. Lookup checks current labels, page geometry and the exact current API record. I inspected current mobile confirmation, desktop long-count search, mobile literal-label/focus, mobile pair uncertainty and desktop refused-form captures. Full labels/counts wrap, feedback states remain distinct, and primary controls remain usable. This is scoped visual evidence, not an exhaustive accessibility certification.

Builder's intermediate **3407px at 375px** observation remains source-hash-attributed in [D220 preparation attribution](../preparation/D220-geometry-preparation.json) and the committed `stage-2/checks/evidence/20261005T103516.073561Z-numeric-entry/` artifacts. It is not described as an independent failure on an accepted SHA. The original d894/0c0 input failures and their unreached browser retry continuations remain raw FAIL evidence; this fresh run reaches and passes those continuations.

## Counts and unresolved-case disposition

| Lane | Distinct definitions / separate experiments | Current result |
|---|---:|---|
| Frozen security/load | 104 | Reconciled PASS; original four email-oracle FAILs retained |
| Frozen common boundary/auth/JSON/protocol/audit | 44 | Reconciled PASS; original B003 selector mismatch retained |
| Frozen compact pair / original numeric / upgrade | 1 / 14 / 6 | PASS; six transfer definitions on both 1→2 and 2→2 count once |
| **Frozen applicable** | **169** | **169 PASS** |
| **Independent pytest** | **96** | **96 PASS**; previous 92 plus D220 two and D221 two |
| **Unchanged official Stage 1–2** | **145** | **145 PASS** |
| Unchanged developer methods | 47 | PASS, separate lane |
| Source publication fault injections | 20 executions / 8 actual operation names / 3 fault types | PASS, separate from HTTP counts |
| Source formatter / deployment | 4 / 2 | PASS, separate lanes |
| Actual producer removal | 3 definitions / 5 executions | PASS, separate from pytest definitions |

Thirty application command attempts record **527 raw pytest executions: 517 PASS, 10 FAIL, zero ERROR/SKIP**. Four unchanged malformed-email login expectations require 401 while Stage 1 §6 explicitly requires 422; the separately adjudicated baseline and independent auth contract pass, including nonmutation. Six raw opaque-selector failures (B003 and five D116 variants) remain intact; separately executed representation adapters preserve the corruption assertions and pass 422/exact destination nonmutation alongside unchanged valid controls. They create no extra definitions. No real product failure is erased by an aggregate pass count.

The unchanged isolated harness also passes Stage 1 and Stage 2, highest contiguous 2, on this clean exact checkout. Its raw automatic Stage 3 probe fails on the expected missing policy endpoint; that next-stage probe is outside this Stage 2 gate, is preserved, and grants no Stage 3 conformance. The report's required checks are 120 + 25 PASS. No applicable check is skipped or left unresolved.

## Cumulative criterion matrix

The complete definitions and individual observations are in the linked matrix; these groupings cover every applicable requirement row without using prior passes to qualify this revision.

| Criteria | Fresh evidence and disposition |
|---|---|
| AC01 provenance | Complete same-SHA handoff; standalone checkout/source inventory; frozen hashes and owned Verifier commits. PASS for this review; genuine full room export remains final delivery work. |
| AC02 runtime | Rebuilt single image; internal-network clients, resource limits/read-only/tmpfs; health at default 8080 in 0.514891s and configured 18087 in 0.506768s. PASS. |
| S1-01–06, S1-12–19 | Official120, baseline104, common44, independent HTTP/calendar/historical families and numeric14: occupancy/serializability, reset/model, exact JSON/types/errors, public availability, identity/cutoff/DST. PASS. |
| S1-07–11 | Auth contract, original/adjudicated baseline, exact equality/unknown fields/key scope/precedence and original receipts. PASS with disclosed four-email adjudication. |
| S1-20–25 | Snapshot adapters, numeric lifetimes, moves/concurrency, six transfers on both edges and actual source removals: replacement, nonmutation, preserved credentials/receipts and atomic batches. PASS. |
| S2-01–07 / AC04 / AC04.5 | Official UI, D211–D221, live browser transfers: routes/testids/auth/grid/form/confirmation/lookup, stale exclusion, actual loss/refusal/current assignment, exact integers, labels/focus and mobile/desktop geometry. PASS. |
| S2-08–12 | Official pairs, D201–D208, compact pair, numeric and transfer cases: declaration order/nontransitivity/selection errors/exact summed capacity/occupancy/cancelled seeds/batches. PASS. |
| AC03 publication boundary | Full applicable API lanes plus 20 actual preparation/encoding/compression injections across signup/login/create/patch/cancel/moves/reset/import. Exact rollback and successful retry asserted; actual postcommit loss exercised separately. PASS. |
| AC07 | All 169 frozen, 96 independent and 145 official definitions executed and reconciled; all nine observed defect families directly pass. PASS. |
| AC08 | Current clean exact-SHA per-stage isolated harness PASS. Final four-stage clean `--all` and packaging gate pending. |
| AC05 / AC06 | Stage 3/4 policy/history/series/optimizer requirements are outside this Stage 2 acceptance. Existing Stage 3 rejected candidate awaits correction and full review; Stage 4 gated. |
| AC09 | Current guides accurately label repair review pending at product commit and retain prior failures. Final guides/storyboard/mandates/full native export/local delivery remain assigned final-stage work; no public submission is claimed. |
| AC10 | Exact revisions/source hashes, original failures, separate definitions/executions/requests/injections and measured resource/time limits recorded. PASS for evidence; token usage and billing unknown. |

Direct repair regression bindings: **V-S1-001** R002/R003/D117 continuous absolute transport deadlines; **002** R008 spring-gap closing boundary; **003** D116 reset-type/nonmutation; **004** original numeric and U003–U005 ordinary JSON exact receipts; **005** B003/five D116 semantic corruptions; **006** D122/D123 calendar extrema lifetimes; **007** D124–D127 historical second-offset/current strict instants and actual old producer; **V-S2-001** D215/D218 full literal-label geometry; **V-S2-002** unchanged D219 plus D220/D221. All PASS at this revision. Earlier failed artifacts and repaired-stage histories remain.

## Portability, resource measurements and limits

Live D216 browser transfer passes 1→2 and 2→2 with retained token/form/key/body/reference. The explicit Stage 1 transport adapter loads real Stage 2 HTML and uses real old API state before import; it does not inject session/DOM state. Separate integration executions actually remove the populated source before starting a fresh destination: D115 accepted Stage 1, current Stage 2 and old object-state producer `89582510…`; D126 historical producer `15d1f178…`; D217 accepted Stage 1 ignored-selector identity. Two old tokens, password login, references, original create/batch or historical receipts, repeated replacement and new target writes pass. Source removal is proven by failed post-removal inspection, not merely stopping requests.

[Original extreme numeric run](20261005T105845.042934Z-numeric-63cf798-34580668/) receives/decompresses **1,100,002,780 bytes in 3.121308264s**, within the unchanged 5s assertion. Complete original Decimal JSON parsing takes **5.309245447s** separately and returns the complete dictionary; peak uncapped client RSS is **2,843,452 KiB**. The service remains bounded to 2 CPU / 2 GiB. Gzip declared Content-Length is 4,801,658; server-only generation and independently measured wire bytes are not claimed. The later case property `response_bytes:342` describes a subsequent response. Full accepted-value mutation/export/import/cancel/original retry passes; the occupied excluded pair remains compact. This finite execution is not a universal performance bound.

Instrumented httpx records **5,753 requests**, max concurrency **50**, p50 **0.018285238s**, p95 **0.265712423s**, max **3.121308264s**, no 5xx. The load subset is **2,610 requests**, concurrency **50**, p50 **0.024379529s**, p95 **0.277274470s**, max **0.834336118s**, with occupancy/state/original-receipt assertions. Counts exclude raw sockets, browser traffic, standalone clients, source injections and isolated-harness traffic; their total HTTP count is unknown. Later-stage history counters are not asserted as Stage 2 features.

Application command durations total **282.899720s**, within a **366.211938s** window from **10:55:53.231527 to 11:01:59.443465 UTC**. All 30 frozen source files match the pinned manifest. The clean checkout remains unchanged. No Verifier test container or network remains. Resource-sensitive runs were sequential; unrelated demos/resources were untouched. Final Stage 3/4 and delivery gates remain pending.
