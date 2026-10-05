# Stage3 renewed pair-repair review — ACCEPT

**ACCEPT exact Stage3 product `301caf55085280f12197e393ab6b4735ef4046c3`.** Independent execution closes V-S2-003 on Stage3 and directly rechecks all nine earlier defect families. No observed applicable Stage3 product defect remains open. Coordinator alone reconciles advancement. Stage4 `e538cd16bbd96d4206d89f17a67791e759c00823` remains REJECTED; this decision does not qualify or authorize its repair.

All six complete Builder review parts were actually assembled at **13:57:30.610897 UTC**, before the first application attempt at **13:59:22.504303 UTC**. [Recipient assembly](ASSEMBLY-301caf5.json) binds the native IDs and full authored mirror SHA256 `d98f1c74f4fda35e79ef198e1d6d3799a1d7cabc615f34a0d060eb1cd32d1f61`. The mirror supplements native delivery and is not a room export. Renewed Stage2 Coordinator gate is `b0e69e22fa1fd30e89516e09b0fecac45b74a2eb`.

The standalone immutable checkout is `/Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/301caf55085280f12197e393ab6b4735ef4046c3-faabff40`. All **9,730 tracked files** match the commit. Stage3 has **300 files**; Stage1/Stage2/Stage4 retain **28/289/233 files** byte-identical to accepted Stage2 product `4b2236fb6576b636d168b2cacf1a5d91921cf582`. The sole runtime change from reopened Stage3 `4ce583cca13a033dd2f548ca982deec7200f8ad6` is `stage-3/web/app.js`: it omits the actual unavailable pair button for that slot. Server/domain/legacy/numeric/CSS/HTML are unchanged. Browser SHA256 is `5088924cbc05d11d027dde80a3b1b5fd1110262d44b076c57125b616a9722701`, matching accepted Stage2. [Source binding](SOURCE-BINDING-301caf5.json) records the exact comparison and Builder identity.

Primary artifacts: [review JSON](REVIEW-301caf5.json), [all case observations and reconciliations](case-matrix-301caf5.json), [checkout provenance](provenance-301caf5.json), [final audit](FINAL-AUDIT-301caf5.json), [test-source audit](CASE-SOURCE-AUDIT-301caf5.json), [execution plan](RUN-PLAN-301caf5.json), [cumulative requirements](../../qa/COVERAGE.md), [defect ledger](../defects.json). **37 manifests / 1,004 artifact files** verify, comprising36 application-command attempts and one separate tooling retention attempt. Forty executed test source files match the recorded QA revision `66d360a98f2c8ef84ff21037d7fb02575dac6750` or the unchanged read-only official package. The evidence commit is supplied after committing this report.

## Direct repair and browser lifetime

Minimal counterexample retained from the rejected context: UTC restaurant, tables a2/b2/c4, pair[b,a], duration60; book a at2030-01-01T18:00 for2, then search party4. API excludes the pair18:00 and includes19:00. Both new unchanged D222 cases now find **zero18:00 pair cells**, an available19:00 pair and the required false single cell. The actual choice is absent, not merely renamed. Original375/1360 failures at4ce583c remain in the [historical addendum](ADDENDUM-4ce583c-V-S2-003.json).

| Fresh lane | Definitions | Result |
|---|---:|---|
| [D222 unchanged](20261005T135922.503593Z-stage2-pair-visibility-301caf5-f2821ace/) | 2 | PASS at375/1360: partial-day pair absence, later available pair and false singles |
| [D223–D225](20261005T135935.576139Z-stage2-pair-repair-301caf5-2318b7af/) | 8 | PASS: all-day/capacity exclusion, ordered literal labels/keyboard,409 form/body/key preservation, refresh completing while real committed201 is held then aborted, original200 retry and exactlyone diner booking |
| [D219 unchanged](20261005T135950.635303Z-stage2-native-range-301caf5-9a1be98d/) | 2 | PASS:401-digit search and booking controls, ordinary keyboard and fill, exact query/raw numeric JSON, actual201-loss/original200 retry |
| [D220](20261005T135959.118594Z-stage2-numeric-geometry-301caf5-6cbdc1ab/) / [D221](20261005T140007.756720Z-stage2-integer-validation-301caf5-8421b84a/) | 2 / 2 | PASS:375/1360 full-value geometry through search/form/uncertainty/confirmation/lookup; invalid-text rejection/nonmutation and focused keyboard recovery |
| [D211–D215](20261005T140247.188102Z-stage2-browser-301caf5-e1a8f42d/) / [D218](20261005T140301.763720Z-stage2-label-lifetime-301caf5-cead85cb/) | 8 / 2 | PASS: current seating after two-booking or pair-to-single repair before original retry, stale search exclusion, refusal recovery, XSS labels and full literal-label lifetime |

D222 source remains `254a3e674d0c00a6b61e2ff6df4e5d5e96241e46d6e6288ae3c41a41dcf18d93`; D219 remains `94c5f02b0cb6eb01eeacb555ca013e52a28a4ce562ccd1a39ac44865a0ff1346`. Browser loss intercepts a real fetched committed201 before aborting its delivery. Original receipts remain immutable while current confirmation/lookup reads display the changed assignment. Four actual captures were visually inspected and hash-bound in [visual review](visual-review-301caf5.json). This is scoped visual/flow evidence, not exhaustive accessibility certification.

## Counts and every nonpass

| Evidence lane | Distinct definitions or separate experiments | Disposition |
|---|---:|---|
| Frozen baseline | 104 | ReconciledPASS; original4 malformed-email oracle FAILs retained |
| Frozen common / compact pair / original numeric / upgrade | 44 / 1 / 24 / 6 | ReconciledPASS;6 upgrade definitions repeated across3 edges count once |
| **Frozen applicable** | **179** | **179PASS** |
| **Independent pytest** | **214** | **214PASS**, including73 Stage3 domain and35 counter/integrity cases |
| **Official Stage1–3** | **152** | **152PASS** plus separately recorded unchanged isolated120+25+7PASS |
| Source publication injection | 35 actual experiments across13 operation names and3 fault types | PASS;13 controls defined/executed, not35 HTTP definitions |
| Source formatter / deployment | 4 / 2 | PASS; separate from pytest/HTTP counts |
| Removed-producer integration | 3 standalone definitions / 6 executions | PASS; no repeated-definition inflation |
| Unchanged developer / explicit supplied adapter | 64 / 62 methods | Original62PASS/2ERROR retained; separate adapter62PASS |

There are **669 raw instrumented pytest executions:659PASS/10FAIL, zeroERROR/SKIP**. Four FAILs are the unchanged baseline email expectations: Stage1§6 requires422 for malformed email, while the original oracle demands401. The service returns422 `validation_failed`; the separately adjudicated same104 and independent auth/nonmutation checks pass. Six FAILs are opaque selectors (B003 and fiveD116 variants) attempting object access on the exported string payload. [Explicit representation adapter](20261005T140220.575556Z-snapshot-adapted-301caf5-014eb2cf/) passes all six original intended corruption/422/exact-destination-nonmutation checks and valid import controls. Original assertions/bytes/rawFAILs remain; adapters add zero definitions.

The unchanged developer errors are `test_legacy_offset_seconds_receipt_remains_original` and `test_old_receipt_unknown_table_ids_remains_ignored_on_import`. They directly edit native journal-backed snapshots without consistent authentic operation provenance. Their errors are retained; the explicit schema1 adapter and independently removed real old producers exercise the actual compatibility requirement successfully. Developer errors are separate from the669pytest total. The developer wrapper ran in a **separate exact-SHA clone**. Its generated logs were copied byte-for-byte to the separate retention attempt, with source/destination hashes; the qualifying checkout remained clean throughout.

The final unchanged command, from read-only official cwd, was:

```sh
/Users/kirillpsinnik/Code/wearedevelopers-hackathon/.venv/bin/python -m harness run --track tablekeeper --repo /Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/301caf55085280f12197e393ab6b4735ef4046c3-faabff40 --stage 3 --mode isolated --out /Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final/reports/stage-3/20261005T140500.411104Z-official-isolated-clean-301caf5-d71c80de/official
```

[Isolated evidence](20261005T140500.411104Z-official-isolated-clean-301caf5-d71c80de/) exits0 and records exact revision301caf, highest contiguous3, claimed3, `overshoot:null`. Its automatic next-stage probe collected6 Stage4 cases, executed4PASS/1FAIL and stopped before1remaining case. Those raw logs/counts are retained outside the Stage3 gate; no Stage4PASS or skip-as-PASS is inferred. The isolated run executes157 cases in total:156PASS/1Stage4FAIL, with152 applicable passes. It repeats152 official definitions rather than adding new ones.

## Cumulative acceptance mapping

| Criterion | Executed evidence and scope |
|---|---|
| AC01 | Full native six-part handoff before execution, independent standalone checkout/no alternates, all source/frozen hashes, own QA/reports ownership. Final room export remains outstanding packaging work. |
| AC02 | Independently built Stage3 context, no outbound runtime network,2CPU/2GiB/read-only/tmpfs; default8080 and custom18087 health0.606650s/0.552550s. Stage1/2/4 contexts unchanged. |
| AC03 / S1-01–25 | Frozen/official and independent HTTP framing, drip deadlines, connection boundaries, type/error/auth/privacy, exact nestedJSON/numbers/Unicode, cutoff/DST/calendar extrema, identity, half-open occupancy, concurrent50-client state, atomic batches, original retries and replacement snapshots all reconcilePASS. |
| AC04 / S2-01–12 | All required routes/testids, warm responsive375/1360 flows, labels/focus, stale-search ordering, truthful refusal/uncertainty, exact guest entry, current assignment versus original receipt and declared ordered pair rules pass. D222/D223–225 close the reopening. |
| AC05 / S3-01–16 | Independent explain rules even bothfalse/absent shape; public immutable policy order/date+version choice; manager boundaries and owner-only404; uncapped policy0; old accepted cutoff/noops; per-event terms/history; stale concurrency; unchanged anchor, occurrence-date policy/DST/index-first rollback; permanent exceptions/cancellation retention; once-per-series/batch accounting; native/old snapshot authenticity pass. |
| AC05 semantic imports | D333 accounting,33D334 semantic corruptions with valid controls and422exactnonmutation, D335 valid original schedules, all three transfers and real old producer integrations pass. No old events are invented. |
| AC03 publication |35 actual response/candidate-encoding/compression injections cover signup,login,create,patch,cancel,moves,reset,import,policy,series,series_patch,series_cancel,series_moves. Exact rollback includes occupancy/versions/history/terms/revisions/receipts; normal retries pass. Postcommit browser loss is tested separately. |
| AC06 | Stage4 optimizer/closures/series-amendment requirements NOT_APPLICABLE to this Stage3 gate; originalStage4REJECT remains. |
| AC07 | Every applicable179frozen/214independent/152official definition executed and reconciled;104 distinct baseline security/load definitions actually exercised; all10 defect families directly pass at this SHA. Counts do not claim exhaustive proof. |
| AC08 | Clean exact-SHA unchanged per-stage isolated harness passes. Final four-stage immutable `--all` and concrete delivery check remain later gates. |
| AC09 | ExactStage3 RUN documents all added endpoints/roles, policy0, genuine migration/history, retries and ephemeral persistence, synthetic demo and review-pending limits. Full guides/demo/video/native-export completion remains separately assigned; no public submission, real booking or fabricated recording. |
| AC10 | Exact product/QA/source/artifact identities, stableID union, failures/experiments/request counts and durations retained. Actual total tokens and billing remain unknown. |

Direct prior-defect bindings: V-S1-001 R002/R003/D117 absolute drip deadlines;002 R008 DST-gap closing;003 D116 reset/nonmutation;004 original numeric/U003–U005 exact ordinary-envelope lifetime;005 B003/D116 original and adapted receipt corruptions;006 D122/D123 calendar extrema;007 D124–D127 historical second offsets/formatters and removed historical producer; V-S2-001 D215/D218 labels;002 unchangedD219/D220/D221 exact party;003 unchangedD222 plusD223–225. Historical acceptances, reopenings and raw failures are not rewritten.

## Transfers, measured resources and limits

Six frozen upgrade definitions plus retained-browser D216 execute separately on **1→3** from `fd843b83db16ec8585d66af7ac0d6fac89aae82c`, **2→3** from `4b2236fb6576b636d168b2cacf1a5d91921cf582`, and **3→3** from this exactcandidate. Each also populates/exports a producer, actually stops/removes it, records failed post-removal inspection, and only then starts a fresh destination. Old password login/tokens/references/original booking+batch+series receipts and current states survive; earlier histories remain authentic, imported-anchor adoption and new target operations pass. Additional historical-offset, old-object and ignored-selector producers bring the detached integrations to6 executions/3definitions. Live browser replacement and process-removal integrations are separately evidenced; source removal is never inferred from a snapshot-only transfer.

The original R2N002-e100000000 client receives/decompresses **1,100,002,780bytes in3.258420881s**, within5s; complete original DecimalJSON parse separately finishes in **5.784212040s**. Client peakRSS **2,845,512KiB**; no client cap was added. The service is configured2CPU/2GiB. Declared gzip Content-Length4,801,658bytes is distinct from decompressed bytes; no separate wire-only or server-generation timing is claimed. The full accepted-value amendment/export/import/cancel/original-retry lifetime and compact excluded occupied pair pass. This finite executed case is not a universal output-performance guarantee.

Instrumented HTTPX: **7,871requests**, peak50inflight, p50 **0.018676276s**, p95 **0.307291030s**, max **3.258420881s**, no5xx. The load subset is **2,610requests**, peak50, p50 **0.033459928s**, p95 **0.359856657s**, max **0.940833859s**, with occupancy/atomic state/original-receipt assertions. Raw sockets/browser traffic, standalone clients, source injections and isolated-harness requests are outside this instrumented total; their aggregate is unknown.

The36 application commands total **376.231443s**, in a **379.989932s** window from **13:59:22.504303 to14:05:42.494235UTC**. The additional log-retention tooling attempt is not an application execution. All frozen30files match manifest `91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036`. No Verifier containers/networks remain; unrelated demos were untouched. Resource-sensitive work ran sequentially. The complete final delivery, native room export and Stage4 qualification remain outstanding under their own gates.
