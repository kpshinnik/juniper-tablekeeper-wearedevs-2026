# Stage3 independent review — REJECT

Product: **`0c0a3867fc38fff0824ec2f887a135a2965bb60f`**. Room:
`e04c2728-8535-41c8-be50-88eb8068fa09`. Verifier owns this decision.
**V-S2-002 remains OPEN and is directly reproduced on Stage3.** No other product
failure was established by this review. Coordinator alone reconciles advancement;
the renewed Stage2 gate precedes carrying its repair into Stage3. Stage4 is gated.

Primary machine-readable evidence is [REVIEW-0c0a386.json](REVIEW-0c0a386.json),
[case-matrix-0c0a386.json](case-matrix-0c0a386.json), and
[provenance-0c0a386.json](provenance-0c0a386.json). These preserve every executed
case, source hash, exact revision, command, duration, observed result and manifest.
Evidence commit is supplied in the native review handoff to avoid self-reference.

## Blocking reproduction

Use the synthetic fixture in
`20261005T102752.835588Z-native-range-0c0a386-ef7ff328/browser/`:
one UTC restaurant, one table capacity `1e400`, Tuesday18:00–19:00,
duration60/grid30/cutoff0, no pairs. Sign in as `u@browser.test`, password
`synthetic-password`. Date2030-01-01. Enter the exact decimal integer consisting
of `1` followed by400 zeros in search; independently search2, open18:00, and enter
the same integer in the booking field. Click the real submit button.

Expected: retain the exact positive integer and submit it unchanged through query
and numeric JSON; after a real committed201 response is lost, preserve its body/key
and retry one booking. This is cumulative Stage1 valid positive integers,
Stage2 search/form/create/retry and explicitly delivered AC04.5, without an invented
browser party cap.

Observed: **D219-search and D219-booking FAIL**. Both direct API controls return
availability200, create201, original replay200 with the exact value. Browser fill
does not throw. Small-value fill and keyboard controls succeed. After ordinary
sequential401-key entry, both native number controls expose `value=""`,
`valueAsNumber=NaN`, `badInput=true`; submit sends no corresponding request and
shows “Enter a whole number of guests, at least 1.” This is an actual supported
input failure, not a Playwright fill exception. No DOM value injection or validation
bypass was used. Real-browser huge-value creation/loss/retry is **NOT_REACHED**.
Raw requests, DOM properties, validation text, timings, screenshots and traces are
preserved. Search/booking after-submit screenshots were visually inspected.

The unchanged test source SHA256 is
`94c5f02b0cb6eb01eeacb555ca013e52a28a4ce562ccd1a39ac44865a0ff1346`.
Its earlier Stage2 failure and additive rejection remain in
`../stage-2/ADDENDUM-d8941d7-V-S2-002.md`, evidence
`6f449325c4ced6a2c0ff6e7563a4b2ddb338fca2`. This Stage3 finding is empirical,
not inferred from inherited source. Repair requires a fresh exact-SHA cumulative
review; current green suites do not close it.

## Executed results and preserved nonpasses

| Lane | Exact-revision result |
|---|---|
| Frozen applicable definitions | **179 PASS**:104 baseline,44 common,1 compact pair,24 numeric,6 upgrade. Original/adjudicated baseline count once |
| Official Stage1–3 definitions | **152 PASS** in detailed run; unchanged isolated harness also reports120+25+7 PASS and claimed stage3 |
| Independent HTTP/browser definitions | **200 total:198 PASS,2 FAIL** (D219). Includes73 public Stage3 cases and35 counter/integrity cases |
| Raw pytest executions | **663:649 PASS,14 FAIL,0 ERROR,0 SKIP**; repeats add no definitions |
| Frozen upgrade executions | Six definitions repeated on1→3,2→3,3→3:18 PASS; D216 live browser transfer PASS on each edge |
| Actual removed-producer integration | Five PASS executions over3 standalone definitions: D325 on all3edges, D126 historical, D217 formerly-ignored selector |
| Source publication experiments | 13 defined and executed operation controls;35 actual injections PASS over all13 operations and3 fault types; separate from HTTP counts |
| Source formatter experiments | Four PASS; separate from HTTP and synthetic-offset expectations distinguished from IANA rules |
| Deployment | Default8080 and configured18087 PASS on an internal network,2CPU/2GiB/read-only root/required noexec64MiB tmpfs; health0.5201s/0.5916s |
| Unchanged developer methods |64 executed:62 PASS,2 ERROR; explicit supplied adapter runner separately62 PASS. These are not extra HTTP definitions |

Four original malformed-email401 expectations conflict with Stage1§6 requiring422;
their raw FAILs and original bytes remain. The separately adjudicated104-case run
and eight authentication contract cases establish the required behavior. Six
opaque-selector mismatches (B003 and five D116 variants) remain, with separate
decode/reseal adapters passing the original422 and exact-nonmutation assertions.

Two D215 failures in `20261005T103104.209999Z-stage2-browser-0c0a386-d4f15256`
occurred when the QA login helper issued `goto('/')` while the product was already
redirecting there. The real response had updated the signed-in header before the
navigation committed. QA commit`a534f9c095d6fd75df21c313265f44bc3e3e363c` waits for
that redirect; product and case assertions are unchanged. The fresh synchronized
eight-case run passes. Both original failures, traces and hashes remain; they are
classified as QA navigation races, not erased product failures or new definitions.

The two unchanged developer errors forge native schema3 snapshots to resemble old
formats while leaving their journal inconsistent. Their errors/source remain.
The supplied explicit schema1 adapter passes, and independent D325/D126/D217 use
actual old processes, stop/remove them, then import into fresh destinations. The
historical current-response adapter only adds checks for Stage3 revision1/policy0
terms/empty old histories; immutable original receipts remain exact.

The unchanged official harness also records its automatic next-stage probe failure
in `official/stage-4.log`/`report.json.overshoot`. Stage4 is outside this gate and
has no claimed PASS. Its failure is retained. No unavailable check or hidden test
has been represented as passing.

## Cumulative criterion matrix

| Criterion | Evidence and disposition |
|---|---|
| AC01 provenance/ownership | Complete six-part Builder handoff preceded execution. Standalone clean detached checkout, no alternates; exact product/test hashes; QA/report-only own commits |
| AC02 deployment/earlier folders | Each judged service independently rebuilt from stage3 Dockerfile;2CPU/2GiB/read-only/internal network. Default/custom ports pass. Stage1 matches acceptedfd843b8 across28files; Stage2 matchesd8941d7 across89files, with its newly reopened D219 issue explicitly retained |
| AC03 API/errors/auth/exact JSON/time/atomicity | Official1–3,104security/load baseline, common44, pair1,numeric24, independent inherited HTTP and exact lifetime cases pass after stated oracle/selector reconciliation. All seven earlier Stage1 defect families directly regress PASS |
| AC04/AC04.5 browser | Stale search, refusal/form preservation, real201-loss with current assignment, exact9007199254740993, lookup/cancel/auth, XSS/focus/routes,375px/desktop and full literal-label lifetimes pass. **D219 two cases FAIL**; V-S2-002 open. V-S2-001 original mobile check passes with synchronized setup |
| AC05 explanations/policies/history | D301–D313,D326–D328,D332 and officialStage3 pass: independent rules, public ordered policies/date+version selection, manager privacy, policy0 uncapped, old accepted cutoff, noops, authentic ordered histories, stale precedence and50-request revision concurrency |
| AC05 adoption/series/batches | D314–D324,D329–D331 pass: unchanged anchor, per-date policy/DST/first-failure rollback, permanent exceptions, cancelled retention, once-per-series/batch accounting, idempotent original receipts |
| AC05 counters/import authenticity | D333 complete operation sequence PASS;33 D334 checksum-valid native semantic corruptions reject422 with exact destination nonmutation and valid controls; D335 overlapping original schedules valid roundtrip PASS. Authentic journal is unchanged in each corruption |
| AC03/AC05 cross-version portability | Six unchanged transfers on1→3/2→3/3→3; actual removal before fresh destination, retained tokens/login/identities/original receipts, no fabricated old events, authentic adoption/new target operations; current histories/policies/series preserved. D126/D217 older producers also PASS |
| AC03 publication | Source audit confirms private candidate and full response/candidate preparation before sole state assignment.35 actual injected failures prove exact rollback and successful retry, including policy,adoption,series member writes,reset/import; realHTTP browser loss covers post-commit uncertainty |
| AC06 | Stage4 optimizer/closures/series amendments NOT_APPLICABLE; still gated |
| AC07 coverage | All179frozen/152official/200independent applicable definitions executed; case matrix preserves all nonpasses. D219 prevents acceptance |
| AC08 | Exact clean candidate checkout and unchanged isolated per-stage harness complete. Final four-stage immutable delivery/all-stage check is a later gate |
| AC09 | Stage3 RUN/English/Russian guide contents reviewed for setup/roles/endpoints/retry/persistence. The claim of unrestricted exact browser party entry is contradicted by D219 and must be corrected with repair. Final submission/presentation/video/native FULL room export remain later deliverables; no publication or real booking performed |
| AC10 | Exact revisions, source hashes, JSONL/JUnit/raw logs/traces, durations and resource measurements retained; unknown total tokens/billing remain unknown |

## Resources and evidence limits

The original R2N002-e100000000 case passes. Availability contains
**1,100,002,780 received/decompressed bytes**, transferred/decompressed in
**4.327149341s** (the unchanged five-second assertion). The separately measured
complete original Decimal JSON parse takes **5.813241558s**. Gzip declared wire
length is4,801,658bytes. Uncapped client peak is **2,845,628KiB**; the service is
limited to2CPU/2GiB. The case's `response_bytes:889` is a later response, not the
availability size. This is successful finite-case evidence, not a universal bound.

Instrumented pytest HTTPX observed7,815 calls, no5xx, up to50inflight. The load
subset has2,610 calls, p50=0.035770914s,p95=0.360155127s,max=1.239344362s, peak50.
Those counts include setup and repeated attempts; raw sockets, browser requests,
standalone producers, source injections and unchanged isolated-harness requests
are separate or uncounted. Distinct definitions are not request counts.

There are32 application command attempts,382.797737s summed command duration,
622.338225s first-to-last execution window. The clean-checkout tooling attempt is
separate. All886 files in33 complete attempt manifests were rehashed. Product
inventory binds all120Stage3 tracked files and the earlier folders. Owned services,
clients and networks were cleaned; unrelated demos were untouched.

Required next action: Builder repairs Stage2 first and sends its complete exact-SHA
package. After renewed independent Stage2 acceptance and Coordinator reconciliation,
carry that accepted correction into Stage3 and rerun the entire Stage3 gate at the
new revision. Preserve this REJECT and all earlier evidence.
