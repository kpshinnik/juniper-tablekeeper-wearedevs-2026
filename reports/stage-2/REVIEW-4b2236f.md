# Stage 2 pair-cell repair — independent ACCEPT

**ACCEPT Stage 2 product `4b2236fb6576b636d168b2cacf1a5d91921cf582`.** Fresh complete execution closes V-S2-003 for Stage 2 and directly passes all nine earlier defect families. Coordinator must reconcile this renewed gate before Builder carries the repair into Stage 3. Existing Stage 3 `4ce583cca13a033dd2f548ca982deec7200f8ad6` remains reopened and Stage 4 `e538cd16bbd96d4206d89f17a67791e759c00823` remains rejected. Their historical acceptances, full rejection, addenda and raw failures are unchanged.

Room: `e04c2728-8535-41c8-be50-88eb8068fa09`. All five Builder task/specification/setup messages were fully assembled before application execution; [recipient assembly](ASSEMBLY-4b2236f.json) retains native identities. Exact standalone checkout: `/Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/4b2236fb6576b636d168b2cacf1a5d91921cf582-3b718032`. All **8,494 tracked files** were rehashed after execution and remain identical; Git status is clean, with no object alternates. Stage 2 has 289 files. Stage 1's 28 files remain identical to accepted `fd843b83db16ec8585d66af7ac0d6fac89aae82c`; Stage 3's 168 and Stage 4's 233 files remain unchanged from their reopened/rejected sources.

Primary evidence: [execution inventory](REVIEW-4b2236f.json), [every case and observation](case-matrix-4b2236f.json), [product/source hashes](provenance-4b2236f.json), [final artifact audit](FINAL-AUDIT-4b2236f.json), [full command plan](RUN-PLAN-4b2236f.json), [cumulative coverage](../../qa/COVERAGE.md), [defect ledger](../defects.json). **33 unique attempt manifests covering 901 artifact files verify**, including the preparation checkout attempt and 32 application command attempts. The evidence commit is supplied in the native decision after committing this report.

## Repair and direct reproduction

Only runtime change from Stage 2 `63cf798cf60baf3134a64e4db599c92d81561e3e` is `stage-2/web/app.js`: unavailable two-table choices are omitted from each slot. The exact JavaScript SHA256 is `5088924cbc05d11d027dde80a3b1b5fd1110262d44b076c57125b616a9722701`. Server, numeric codec, CSS and HTML are unchanged. Each application lane independently builds committed bytes with a service constrained to 2 CPU / 2 GiB, read-only root, tmpfs and an internal runtime network. Builder's local results are not counted as independent evidence.

Minimal original counterexample: UTC restaurant, a/b capacity 2, c capacity 4, declared pair `[b,a]`; book a at `2030-01-01T18:00` for 60 minutes, then search party 4. The API excludes the pair at 18:00 and offers it at 19:00. Previously `slot-b+a-18:00` remained as a false pair cell. At this revision **the actual unavailable pair button is absent**, the 19:00 pair remains ordered and labelled, and unavailable single cells remain present with `data-available=false`.

| Browser family | Definitions | Fresh result |
|---|---:|---|
| Unchanged D222 at 375/1360 | 2 | PASS: occupied-member pair absent at the affected slot, later pair available, false singles retained |
| D223 all-day occupancy / insufficient capacity × two widths | 4 | PASS: excluded pair row and actual choices absent; initially available pair has ordered literal labels and works by keyboard |
| D224 refusal and unchanged-form recovery × two widths | 2 | PASS: real 409 refresh removes pair choice; selection/form/body/key survive; after external cancellation, 201 then 200 retain the original receipt and one confirmed diner booking |
| D225 refresh while committed response is pending × two widths | 2 | PASS: held availability refresh completes while real POST201 is pending; fetched 201 is then aborted; uncertainty appears without false error/confirmation; unchanged retry200 retains body/key/reference and one booking |
| D219 exact 401-digit search/booking controls | 2 | PASS: actual201 loss, exact body/key original200 retry, exactly one booking |
| D220 full-value geometry / D221 invalid-entry keyboard recovery | 2 / 2 | PASS: mobile/desktop five-state geometry; invalid text causes no request or mutation, corrected keyboard input succeeds |
| D211–D215 prior browser flows / D218 literal-label lifetime | 8 / 2 | PASS: repaired current assignment versus original receipt, pairs, stale search, XSS-safe literal labels, refusal and responsive flows |
| D216 retained browser across 1→2 and 2→2 | 1 repeated on two edges | PASS: same session/form/body/key, original reference and current authoritative state |

D222 source remains SHA256 `254a3e674d0c00a6b61e2ff6df4e5d5e96241e46d6e6288ae3c41a41dcf18d93`; D219 remains `94c5f02b0cb6eb01eeacb555ca013e52a28a4ce562ccd1a39ac44865a0ff1346`. New independent D223–D225 add **eight definitions**, separate from Builder's local cases. QA revision is `b22d2d4a7578987223409074e67f68779e6f8696`; each case records source hash and line. [Scoped visual inspection](visual-review-4b2236f.json) records four current captures: mobile uncertainty and 401-digit confirmation, desktop restored pair confirmation and literal-label lookup. Required controls and feedback remain readable; full displayed labels/counts wrap within the viewport. This is scoped visual evidence, not exhaustive accessibility certification.

## Counts and preserved nonpasses

| Lane | Distinct definitions or separate experiment count | Result |
|---|---:|---|
| Frozen security/load | 104 | Reconciled PASS; original four email-oracle FAILs retained |
| Frozen common boundary/auth/JSON/protocol/audit | 44 | Reconciled PASS; original B003 selector mismatch retained |
| Frozen compact pair / original numeric / upgrade | 1 / 14 / 6 | PASS; repeated transfer edges do not add definitions |
| **Frozen applicable total** | **169** | **169 PASS** |
| **Independent pytest** | **106** | **106 PASS**: prior96 + unchanged D222 two + new eight |
| **Official Stage 1–2** | **145** | **145 PASS** |
| Unchanged developer methods | 47 | PASS, separate lane |
| Publication fault injections | 20 / 8 actual operation names / 3 fault types | PASS, separate from HTTP and pytest counts |
| Source formatter / deployment configurations | 4 / 2 | PASS, separate lanes |
| Actual producer removal integrations | 3 definitions / 5 executions | PASS, separate from pytest definitions |

The 32 application commands preserve **537 raw pytest executions: 527 PASS / 10 FAIL / 0 ERROR / 0 SKIP**. Four unchanged malformed-email login expectations ask for 401; Stage 1 §6 explicitly requires 422 for malformed email. The separately adjudicated same104 baseline and auth contract pass with nonmutation. Six original opaque-selector failures (B003 and five D116 corruptions) occur before their intended corruption assertion: the old selectors/checksum encoding do not match the opaque string payload. Separate representation adapters execute the unchanged semantic corruption assertions, valid controls and exact destination nonmutation successfully. They create zero additional definitions. Every raw source, failure and hash remains intact. A post-run integrity audit initially looked for an official source under the QA Git tree and received git exit128; the corrected mapping verifies all37 case source files against either the recorded QA revision or the read-only official files. This bookkeeping correction executed no application case and adds no definition; the final audit retains it.

The unchanged official isolated command is captured under `20261005T132224.280002Z-official-isolated-4b2236f-9bce6bb8`, run from the read-only official directory:

```text
/Users/kirillpsinnik/Code/wearedevelopers-hackathon/.venv/bin/python -m harness run --track tablekeeper --repo /Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/4b2236fb6576b636d168b2cacf1a5d91921cf582-3b718032 --stage 2 --mode isolated --out /Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final/reports/stage-2/20261005T132224.280002Z-official-isolated-4b2236f-9bce6bb8/official
```

It exits 0 and reports the exact product revision, 120 Stage1 +25 Stage2 passes, highest contiguous stage2. The harness also probes Stage3 against the Stage2 image; that raw expected missing-policy failure is preserved and lies outside this gate. No applicable official error/skip is hidden. Detailed official145 execution is separately retained without counting repeated definitions. This clean checkout was never used with a developer wrapper that writes logs into it.

## Cumulative requirements and defect regressions

| Criteria | Exact-revision evidence |
|---|---|
| AC01–02 | Complete native handoff assembly; separate immutable checkout and own QA; source/context hashes; single-image offline/resource/read-only execution; default8080 health0.497464s and configured18087 health0.455818s |
| S1-01–06,12–19 / AC03 | Official120, baseline104, common44, independent HTTP/calendar/historical cases and originalnumeric14: occupancy, reset/model, exact JSON/error types, malformed framing and partial-input deadlines, public availability, identity, cutoff, DST and calendar extrema |
| S1-07–11 | Authentication/privacy, multiple tokens/password login, exact unknown-field and number identity, method/path/user key scope, precedence, concurrent exactly-once creation and immutable receipts |
| S1-20–25 | Valid and corrupt snapshot controls, numeric lifetimes, atomic moves, both transfer edges and actual removed producers: replacement, nonmutation, preserved credentials/reference/original receipts and failed-key reuse |
| S2-01–07 / AC04 / AC04.5 | OfficialUI, D211–D225, retained-browser transfers: routes/testids/auth/grid/form/lookup, stale exclusion, actual loss/refusal, current assignment, exact numbers, keyboard/labels/mobile/desktop geometry |
| S2-08–12 | Official pairs, D201–D208, compact/numeric/transfer cases and D222–D225: declarations/order/nontransitivity, exact capacity, occupancy/cancelled seeds/atomic batches, available-only pair choices |
| Publication boundary | 20 actual preparation/encoding/compression injections across signup/login/create/patch/cancel/moves/reset/import; exact rollback and successful retry; source injections are not HTTP requests |
| AC07,10 | All applicable169 frozen/106 independent/145 official definitions reconciled; all ten defect families directly pass; exact attempts, sources, durations and count categories retained |
| AC08 | Fresh clean exact-SHA per-stage isolated harness PASS. Final repaired four-stage `--all` and clean delivery check remain later work |
| AC05–06,09 | Stage3/4 correction and new exact-SHA gates remain required. Final docs/presentation/storyboard/mandates/native full room export and packaging remain separate final-delivery work; no publication, fabricated recording or export is claimed |

Direct prior-family bindings: **V-S1-001** R002/R003/D117 absolute transport deadlines; **002** R008 DST closing boundary; **003** D116 reset-type/nonmutation; **004** originalnumeric/U003–U005 ordinary JSON exact receipts; **005** B003/five D116 semantic corruptions; **006** D122/D123 calendar lifetimes; **007** D124–D127 historical second-offset/current strict instants and old producer; **V-S2-001** D215/D218 literal-label geometry; **002** unchanged D219 with D220/D221; **003** unchanged D222 plus D223–D225. All pass on this candidate. No Stage3/4 defect is closed by this Stage2 decision.

## Portability, resources and measured limits

Six frozen definitions execute on each of 1→2 and 2→2; D216 live browser passes both. Separate populated-source-removal integrations pass with accepted Stage1 `fd843b83db16ec8585d66af7ac0d6fac89aae82c`, current Stage2 `4b2236fb6576b636d168b2cacf1a5d91921cf582`, historical object producer `89582510069e984f446060d797e138f4a3bf08f9`, historical offset producer `15d1f178b387e744bf919b6e8bb77fff2b5aeb23`, and the accepted Stage1 ignored-selector lifetime. Each removal is proven by failed post-removal inspection before the fresh destination starts. Password login, retained tokens, references, original receipts, repeated replacement and new target operations pass. The explicit old-API browser adapter serves actual Stage2 HTML without injecting session or DOM state.

The unchanged R2N002-e100000000 original client receives/decompresses **1,100,002,780 bytes in 2.843900266s**, within its 5s assertion. Complete original Decimal JSON parsing returns the complete dictionary in **5.749942583s**, measured separately. Peak uncapped client RSS is **2,845,616 KiB**. Service remains limited to 2 CPU / 2 GiB; heavy clients ran sequentially. Gzip declared Content-Length is 4,801,658; wire-only bytes and server-generation time are not claimed. The accepted value's complete mutation/export/import/cancellation/original-retry lifetime passes. The occupied excluded pair remains compact. This is a finite measurement, not a universal resource guarantee.

Instrumented httpx records **5,805 requests**, max concurrency50, p50 **0.018122488s**, p95 **0.261204394s**, max **2.843900266s**, no5xx. The load subset has **2,610 requests**, concurrency50, p50 **0.025237156s**, p95 **0.278982210s**, max **0.892654914s**, with atomic occupancy/state/receipt assertions. Raw sockets, browser traffic, standalone integrations, source injections and isolated-harness traffic are outside those instrumented totals; the complete HTTP count is unknown.

Application command durations sum to **296.881946s**, in a **300.655547s** window from **13:17:53.712733 to 13:22:54.368280 UTC**. All30 pinned frozen files match originals. No Verifier container or network remains; unrelated resources were untouched. Actual token usage and billing are unknown. Historical reports remain separate from these final-candidate results. Coordinator alone reconciles the next gate.
