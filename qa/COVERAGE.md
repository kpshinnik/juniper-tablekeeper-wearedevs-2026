# Independent acceptance coverage

> Current product decision: Stage4 `25ade1c7add9a5701a511e07f79a619a3cb21b51` independently ACCEPTED; Coordinator reconciliation and final packaging are pending. Earlier status paragraphs below are retained historical snapshots. See `reports/stage-4/REVIEW-25ade1c.md`.


Room: `e04c2728-8535-41c8-be50-88eb8068fa09`. Owner: Verifier.
Latest disposition: **renewed Stage3 pair repair ACCEPT** at
`301caf55085280f12197e393ab6b4735ef4046c3`: fresh179 frozen,214 independent,
152 official definitions reconcile PASS. All ten defect families directly pass,
including unchanged D222 and eight D223–D225 pair-cell/retry checks.
See `reports/stage-3/REVIEW-301caf5.md` and its exact-revision case matrix.
Coordinator alone reconciles renewed advancement. Stage4 `e538cd1` remains
REJECTED for V-S2-003; its full review and codec/D404 addenda remain preserved.
Stage1 `fd843b8` and renewed accepted Stage2 `4b2236f` remain byte-identical.
Earlier Stage2/3 acceptances and later reopenings remain historical evidence.
Derived from the complete seven-part assignment and all four specifications before
examining any product implementation. All application rows initially **NOT_RUN**.
Collection, source inspection, QA selfchecks and input hashes cannot change that status.
Acceptance requires execution evidence at the exact final product revision and closure
of every demonstrated contradiction, including earlier failed attempts.

## Counting and applicability

| Frozen input | Distinct definitions | Stages / required executions |
|---|---:|---|
| baseline-original/test_security.py | 84 | 1,2,3,4, unchanged; S064–S067 original oracle results retained |
| baseline-original/test_load.py | 20 | 1,2,3,4; request count, concurrency, p50/p95/max and atomic assertions |
| baseline-adjudicated/test_security.py + test_load.py | 0 additional | Same 104 definitions; all stages separately; four email expectations corrected to 422 plus nonmutation |
| supplemental/test_boundaries.py | 14 | Every stage; B003 receipt selector applicability explicitly audited |
| supplemental/test_auth_contract.py | 8 | Every stage; independently establishes email oracle conflict |
| supplemental/test_json_responses.py | 3 | Every stage; full accepted nested receipt export lifetime |
| supplemental/test_protocol_resources.py | 8 | Every stage; huge exponent sequentially, judged service 2 CPU / 2 GiB |
| supplemental/test_audit30.py | 11 | Every stage; framing, equality, DST and seed checks |
| supplemental/test_compact_pairs.py | 1 | Stages 2–4; occupied small pair member excludes huge output |
| supplemental/test_advanced.py | 28 | Stage 4; 24 deterministic optimizer seeds + four series cases |
| supplemental/test_stage4_ui.py | 2 | Stage 4; real browser, desktop/mobile and current assignments |
| supplemental/test_stage4_ui_lost.py | 2 | Stage 4; fetch real 201, abort response, repair, original retry |
| supplemental/test_stage4_load.py | 3 | Stage 4; once-only application and atomic reads |
| supplemental/test_stage4_numeric.py | 2 | Stage 4; exact unused capacity and pair reassignment |
| supplemental/test_upgrade_contract.py | 6 | All ten edges: 1→1/2/3/4, 2→2/3/4, 3→3/4, 4→4 |
| numeric-original/test_numeric_lifetime.py | 24 total | Stage 1:12; Stage 2:14; Stage 3:24; Stage 4:24; original assertions unchanged |
| supplemental/selfcheck_oracle.py | 8 tooling only | Hand-derived QA oracle selfchecks; excluded from application totals |
| Official shipped suites | Separately catalogued | Stage N runs suites 1..N and expected next-stage probe; final --all --mode isolated |

Operator definitions total **216** (192 + 24). Repeated stages, corrected oracles,
HTTP requests, injected faults and repeated attempts never increase this total.
Every parametrized definition has a stable node ID and source SHA in collected catalogs.
Numeric collection respects the frozen module's STAGE_UNDER_TEST gating. No deselected
or skipped case is a pass. Source selectors may be adapted in separate QA files only;
retain unchanged execution, exact selector failure, source hash and adapted execution.

## Requirement matrix

Evidence bindings below are required test families, not claims that shipped tests alone
fully cover the requirement. `Dxxx` identifiers name independently derived obligations.
Each row requires exact-revision outcomes before ACCEPT. Lower-stage requirements apply
to every later stage unless explicitly refined by that stage's specification.

| ID | Stage | Authoritative requirement / independently checked invariant | Required evidence |
|---|---|---|---|
| AC01 | all | Fresh room/code; read-only official/frozen inputs; three real seats, reciprocal full handoffs; distinct author and committer; no prior product/archive reuse | Frozen hashes, Git path/identity audit, genuine native room export |
| AC02 | all | Independent Dockerfile+RUN.md per stage; accepted prior copied forward only; no later backfill; single image, PORT/default8080,0.0.0.0,health≤60s,2CPU/2GiB,≤50inflight,5s ordinary/10s controls,offline runtime,ephemeral disk | Exact clean checkout, isolated official runs, container inspect, RUN reproduction |
| AC03 | all | All applicable API, typing/errors/auth/occupancy/DST/atomicity/original receipts/replacement portability | S1/S2/S3/S4 rows below; no counterexample left open |
| AC04 | 2+ | Warm coherent responsive product, route/testid fidelity, labels/focus/contrast,375px no overflow, distinct loading/empty/refused/uncertain states | Actual desktop/mobile browser walkthrough, screenshots, browser tests |
| AC04.5 | 2+ | Exact positive integer party through search/form/raw numeric JSON/unchanged retry above JS safe range, no invented UI cap where fixture capacity permits | D2129007199254740993; D219-search/booking401-digit1e400, D220 geometry,D221 invalid-entry recovery; V-S2-002 resolved Stage2 at63cf798 and Stage3 at4ce583c |
| AC05 | 3+ | Policies, histories, adoption, series and counters; authentic imported histories | S3 rows, upgrades and representation audit |
| AC06 | 4 | Exact deterministic optimizer; atomic closures/series amendments | S4 rows and independent planning oracle |
| AC07 | all | Every applicable frozen/official/derived case executed; source errors/skips distinct; all historical failures reconciled | Catalog, case JSONL/JUnit, defect ledger, repair regressions |
| AC08 | final | Standalone immutable clean Git checkout at exact productSHA; unchanged official --all --mode isolated; clean delivery harness check | Checkout status/hashes, full harness logs/reports and delivery revision |
| AC09 | final | Truthful English README/Russian FEATURES.md+self-contained HTML,RUN/API/roles/data/retry/persistence/demo/claims/revisions/limits; presentation/storyboard≤5min/300MB; generic mandates/FACTORY/native full room export; local-only | Document and provenance audit; explicit unavailable external artifacts |
| AC10 | all | Product vs evidence SHA; definitions vs executions/requests/injections; retained failures/skips/errors; measured duration and actual available usage; unknown billing remains unknown | Attempt metadata/hashes, request metrics, fault records and final counts |
| S1-01 | 1+ | Confirmed occupancy half-open UTC intervals; no overlaps at every read, serializable concurrent writes; rejected/retried requests never duplicate/partially book | Official1, baseline load, D101,D112 |
| S1-02 | 1+ | GET health exact200/status; reset unauth204 replaces everything and permits repeat; seeded users immediately login | Official1, baseline, D101,D115 |
| S1-03 | 1+ | JSON charset; RFC3339 offsets; unknown request/query fields ignored; accepted opaque IDs≤64 across fixture/routes | Boundaries B006, baseline typing, D103,D108 |
| S1-04 | 1+ | Fixture timezone/grid/duration/cutoff/hours/tables, no overnight hours; seeded reservations preserved; arbitrary calendar dates including past create allowed | Official1, audit30, B005, D110 |
| S1-05 | 1+ | Every4xx/5xx structured error; no5xx even concurrency; wrong type400, missing/invalid-format/range422; endpoint-specific party/local-time422 precedence | Security84,auth8,D102,D106 |
| S1-06 | 1+ | Query integer plain digits only, signs/exponents/decimal forms422; no invented magnitude cap | Baseline,audit30,numeric,D107 |
| S1-07 | 1+ | Signup201/login200 IDs/display/token; email duplicate409; format/password<8→422; unknown valid email/wrong password401 | Original/adjudicated/auth8; D104 |
| S1-08 | 1+ | Password hashing, no plaintext; nonexpiring multiple tokens; public health/reset/export/import/auth/restaurants/availability; private endpoints bearer validation | Security84; source snapshot credential audit; upgrades |
| S1-09 | 1+ | Key required400 absent/empty;1..255 else422; user+method+path scope, exact whole parsed JSON equality including unknown fields/key order/whitespace | Security84, audit30,numeric,D105,D108 |
| S1-10 | 1+ | Parse JSON object/auth then idempotency before endpoint checks; different body409 even invalid/current-resource missing; failed key reusable | Security84,numeric,D105 |
| S1-11 | 1+ | First201/replay200 identical original JSON; concurrent unused key exactly one201; never mutate on replay after amend/cancel/import | Load20,upgrades,numeric,D112 |
| S1-12 | 1+ | Public restaurant list fixture order/detail original fields/unknown404 | Official1,D103 |
| S1-13 | 1+ | Availability required3params; local-date grid opening anchored; fits true duration; every slot including empty; singles fixture order/capacity/unoccupied; closed day[] | Official1,audit30,D109,D110 |
| S1-14 | 1+ | Create immutable identity/reference6..12 A-Z0-9 unique,correct response timestamps/party/status/end; body table/restaurant ownership404 | Official1,security,load,D111 |
| S1-15 | 1+ | Create overlap409;off-grid422;outside/end-after-close422;capacity422;party positive integer422;local gap422;past accepted | Official1,audit30,numeric,D109 |
| S1-16 | 1+ | Own list descending starts_at both statuses and empty[]; others' reference404 without existence leak | Official1,security,D104 |
| S1-17 | 1+ | Cancel frees instantly; repeat200 current state; real-clock cutoff currentstart409,others404 | Official1,load,D110 |
| S1-18 | 1+ | PATCH subset retains omitted fields; validation same as create;old current-start cutoff first;cancelled409;atomic release+reserve;stable identity | Official1,load,numeric,D112 |
| S1-19 | 1+ | Berlin/NY spring gaps absent/reject;fold first occurrence once;absolute duration through both transitions;IANA offsets | Official1,audit30,D109 |
| S1-20 | 1+ | Export JSON envelope track/version1/state;atomic read-only detached snapshot;import unchanged204 replacement repeat;reset clears all | Official1,upgrades,D115 |
| S1-21 | 1+ | Export preserves hashed accounts,tokens,config,identities,status/timestamps,whole request bodies and original receipts;no source dependency | Upgrades all10edges plus actual producer removal D115 |
| S1-22 | 1+ | Invalid JSON errors;missing/wrong envelope/state422 exactdest nonmutation;revokes olddest users/tokens;failed keys reusable | Baseline,boundaries B003,upgrades,D116 |
| S1-23 | 1+ | Moves auth+key,1..8objects distinctstringrefs;shape/duplicate422;owner404/same restaurant422;unknown ignored,omitted retained | Official1,security,D113 |
| S1-24 | 1+ | Moves inputorder nonoccupancy errors;each old cutoff before changes;cancelled409;result overlap409 incl unchanged/unlisted;all-or-nothing records+keys | Official1,load,numeric,D113,D114 |
| S1-25 | 1+ | Moves ordered201 identity/owner/creation stable;noopallvalues stable;original replay200 after edits/cancel/import | Official1,upgrades,numeric,D113 |
| S2-01 | 2+ | HTML routes /,/signup,/login,/lookup;consistent navigation,all required testids;auth/current-user/logout every screen | Official2,D215,D216 |
| S2-02 | 2+ | Search selects restaurant/date/party;single cells every slot/table;data-available exactAPI;unavailable inert;available signedout autherror/login;closed no-slots | Official2,D213–D215 |
| S2-03 | 2+ | Summary label/time;party prefills;form stays aftersuccess;unchanged submit same key/body/reference;changedfield newrequest | Official2,D211–D213 |
| S2-04 | 2+ | Confirmation exactreference,current labels/restaurant/localtime;lookup exactstatus,alltables,cancel absent aftercancel,error when refused/notfound | Official2,D211,D215,D216 |
| S2-05 | 2+ | SearchA late cannot replace B grid/labels/form;409 preserves forminputs,error+refresh,no confirmation | Official2,D213,D214 |
| S2-06 | 2+ | Lostresponse incl committed:nonemptyuncertain,noerror/newconfirmation;unchanged form retries samekey/body;success clears flags+originalref;confirmed rejection error | Official2,D211,D212 |
| S2-07 | 2+ | Stage1snapshot accepted whilebrowser retains sign-in/ref/pending key/form;lost-beforeexport retry original,no reload required | D216 live browser; separate actual source removal D115,D217 |
| S2-08 | 2+ | Declared unordered pairs only,no transitivity,no≥3;capacity exactsum;seed table_id or table_ids/statuscancelled | Official2,compactpairs,numeric,D201–D203,D208 |
| S2-09 | 2+ | Available_options every allowed singles thenpairs;fixture/declarationorder/memberorder;allmembers free fullinterval;singleids stay singles | Official2,compactpairs,numeric,D201,D207 |
| S2-10 | 2+ | Legacy single request;bothfields422;duplicate422;unallowed or>2→combination_not_allowed;anyoverlap409;sumcapacity422 | Official2,D202,D203 |
| S2-11 | 2+ | All responses table_ids and singleton table_id only;PATCH/moves/cancel supportpairs atomically;reversed set noop | Official2,D201,D204–D208 |
| S2-12 | 2+ | Pair cells shown only for available declared pairs at each slot; excluded all-day row absent; single false cells retained; declarationorder/testids/labels; all retry/concurrency rules preserved | Official2,D211,D213,D215,D222–D225 |
| S3-01 | 3+ | explain optional trueonly else422;absent noexplanation;everytable fixtureorder,bothrules independently capacity/no_overlap,available conjunction,policyversion | Official3,D301,D302×5,D326 |
| S3-02 | 3+ | History/decision owner404 even unauth;cancelledhistory accessible;oldestseq1increments1,atnondecreasing | Official3,D303,D308 |
| S3-03 | 3+ | Created3fields/null;changedonly actual orderedfields;noop/replaynoevent;cancelledemptyterminal;eachresultrevision+completeacceptedtermsimmutable | Official3,D308,D312,D314,D329 |
| S3-04 | 3+ | Fixture managersdefault[];policy auth401/nonmanager403/unknown404;manager no private-owner privileges | Official3,D303,D332 |
| S3-05 | 3+ | Complete policy allfields,actualdate,grid/duration1..1440,cutoff0..10080,nobooleans,hoursuniqueweekday,capacities exactlytableids ints1..100;invalid422atomic | Official3,numeric,D304×21,D305×6,D332 |
| S3-06 | 3+ | Policy keyscope/replay;versions perrestaurant increasing onlysuccess;effective greatestdate thenversion;past/outoforder allowed;immutable;publicpublicationorder,detail original | Official3,D306,D321,D323 |
| S3-07 | 3+ | Creation/seedrevision1 under selected/policy0;whole selected acceptedterms excludeseffectivefrom;publication no retroactiveend/history/terms;oldreceipt unchanged | Official3,D306,D307,D308,D327,D328 |
| S3-08 | 3+ | Cancel oldacceptedcutoff;real amend oldcutoff then allresultfields under resultingdatepolicy,replaces terms/end,revision+1;noopretainall butconfirmed/editable;failnone | Official3,D308,D310,D313,D322,D327 |
| S3-09 | 3+ | expected_revision positiveinteger no arbitrary upper bound;invalid422,stale409 before cutoff/resultvalidation;concurrentatmostone realchange | Official3,numeric,D309×7,D310,D311,D320 |
| S3-10 | 3+ | POSTseries ownerauth+key;anchorconfirmed/editable/unadopted;owner404,cancelled409,already409;count2..12 interval1..4 booleaninvalid | Official3,numeric,D315×8,D316,D329 |
| S3-11 | 3+ | Adoptanchor unchanged identity/revision/history/terms/timestamps/receipt;generatedoriginalcalendar dates+weekinterval sameclock;independentdatepolicy/DST/capacity/occupancy | Official3,D314,D318,D329,D331 |
| S3-12 | 3+ | Firstfailedoccurrence determines error;failure removes allrecords/history/counters/key;distinctrefs/stableindices/list/history/occupancy | Official3,D317,D318,D331; D333 operation accounting/D334 corruption bounds/D335 valid original schedules; exact4ce583c PASS |
| S3-13 | 3+ | SeriesGET currentstates owner/noauth404;individualrealPATCH permanentexception andseries+1;noop/failnone;cancelseries+1 notexception/repeatnone;anchorcancel independent | Official3,D316,D319,D320,D330 |
| S3-14 | 3+ | Adoption restaurantrevision+1 entireoperation;replay originalseries/countersunchanged;stages1/2imports adoption authentic oldhistory | Official3,upgrades,D314,D321,D324; D325 actual producer removal; D333 operation accounting/D334 corruption bounds/D335 valid original schedules; exact4ce583c PASS |
| S3-15 | 3+ | Pairhistory table_ids fullsets in canonicalorder when either side pair;single-to-single table_id;paircreation replacesfield;reversedinputnoop | Official3,D308,D312,D327 |
| S3-16 | 3+ | Collective moves allPATCH semantics/revisionchecks,changedbook+1/history1,restaurant+1total,affectedseries+1each,permanentexceptions;failure/replaynone | Official3,D320,D330; source member fault injections; D333 operation accounting/D334 corruption bounds/D335 valid original schedules; exact4ce583c PASS |
| S4-01 | 4 | Replan manager+key;offsetinstants from<to422,unknowntable404;halfopenclosure;≤6tables/4pairs/6considered fully supported,beyondmay422planning_limit | Official4,D401 |
| S4-02 | 4 | Everyconfirmed overlappingclosure considered;fixed outside assignments;perbookingacceptedcapacity,temporal conflicts,prior/proposedclosures;retainidentity/owner/party/time/end/terms;cutoffno impediment | advanced24,D402 |
| S4-03 | 4 | Exactlexicographic moved_count,unused_seats,rankvector bysortedrefs;singlyfixturethenpairdecl ranks;no feasible409 unchanged | advanced24,oracle8tooling,stage4numeric,D402,D403 |
| S4-04 | 4 | Preview201 plan/revision/closure/orderedassignments;preview maystoreplan only,nooccupancy/closure/history/revisions | Official4,advanced24,D403 |
| S4-05 | 4 | Restaurantrevision reset0;newbooking/realamend/cancel/policy/application +1;batch/adoptionwhole+1;noop/failure/replay/previewnone;otherrestaurantisolated | Official4,D404 |
| S4-06 | 4 | Apply manager+key+{};unknown/crossrestaurantplan404;stale409 nochange;differentkeyalreadyapplied409;successfulreplayoriginal200;concurrentatomic | Official4,stage4load,D404 |
| S4-07 | 4 | Applyclosure+allassignments atomic;orderedallconsidered;onlymovedbookrevision+1 and reassigned/table_ids/plan_idhistory;terms/timesstable;restaurant+1whole | Official4,stage4load,D405 |
| S4-08 | 4 | Appliedclosures exclude singles/pairs/create/amend409 andexplainno_overlapfalse;halfopenedges;currentUIlabels/truthfuloriginalretry | Official4,stage4UI,stage4lost,D405 |
| S4-09 | 4 | Seriesamend own/noauth401/others404+key;required positiveexpectedrevision,index0..count-1,exactHH:MM,nobooleans;invalid422/stale409 beforeallcutoffs | Official4,D406 |
| S4-10 | 4 | Eligible indices exclude cancelled/permanentexceptions;originalschedule dates,currentselection/party/identity retained;identicalnoopretainterms;real oldcutoff then newdatepolicy | advanced4,D406,D407 |
| S4-11 | 4 | Collective occupancy vs unchangedmembers/otherbookings/closures;nonoccupancy errors firstbyindex;failure records/history/key/allrevisionsnone | advanced4,D407 |
| S4-12 | 4 | Eachchangedbookingrevision/history+1;series/restaurant+1whole iffchanged;noexceptionmark;empty/noop success no revisions;originalreplay immutable | advanced4,D407 |
| S4-13 | 4 | Repairs preserve seriesexceptions/originaldates/identities/terms;eachaffectedseries+1once;concurrent sameexpectedrevision cannotbothrealchange | advanced4,stage4load,D408 |
| S4-14 | 4 | Acceptexports ownstages1–3 andfinal;importedmoved/cancelledseries works;oldreceipts/history/retries retained | all10upgradeedges,D409 |

## Derived cases and prior counterexamples carried forward

| Family | Additional obligations before accepting applicable stage |
|---|---|
| D101 | Raw conflicting/duplicate/comma/zero/negative/invalid Content-Length, Transfer-Encoding combinations, malformed request line/header/method; controlled structured rejection and connection closure; no injected unread reset executes; health and exact snapshot unchanged |
| D102 | Truncated and slowly delivered header/body, missing length with unread body, unsupported method body, valid request after rejected input on same connection, rejected trailing bytes/pipeline; complete valid pipelined requests remain correctly delimited |
| D103 | Unknown nested fields through every write, unknown queries, opaque IDs path-encoded once; long/Unicode/control labels; correct JSON and response Content-Type including framework errors |
| D104 | Cross-owner auth/list/lookup/cancel/moves/importedtokens, malformed auth, concurrent sessions, signup races, hashing evidence |
| D105 | Exact equality distinguishes true/1, false/0, null/absence, strings/numbers, tinydecimals/zero, adjacentlargevalues; equal decimal/exponent forms and signedzero; wholebody unknownfields retained; wrongpathkey isolated |
| D106 | Depth600/2000/5000, large payloads, unpairedUnicode and escapedcontrols through validate/copy/equality/commit/encode/export/import/retry; accepted values cannot fail later stages of lifetime |
| D107 | Huge compact party rejects quickly without power materialization; accepted unbounded capacities and exactsum1e100000000+4 over actualHTTP ≤5s receive+decompression; complete client JSON parse separately timed, no new client memory cap, sequential clients |
| D108 | Idempotency user/method/path scope and error precedence after parsedobject+auth, fieldorder/whitespace/unknownnestedvalues; retries after failure/currentresource removal/replacement |
| D109 | True-duration DST opening/closing and both folds/gaps, firstoccurrence, halfopen boundaries, slot inclusion via absolute duration, max/min calendar bounds |
| D110 | Real-clock cutoff before/equal/after threshold; past bookingcreate allowed; sameclock policy dates and acceptedcutoff used; noop editability |
| D111 | Stable IDs/reference uniqueness/cross-table affiliations, output types/offsets, list order and identity immutability through entire life |
| D112 | Concurrent overlapping bookings/distinctkeys/samekeys/noops/cancels/moves andatomic reads;failures preservestate andkeys;requestcount/concurrency/p50/p95/max |
| D113 | Batch swap/cycle,unchangedlistedoccupancy,unlistedcollision,inputorder errorprecedence,1/8/9items,duplicate refs,reusablefailedkeys,originalorderedreceipt |
| D114 | Source fault injection at every fallible preparation/publication/encoding boundary for reset,signup/login,writes,import; separate controlsdefined vsactuallyinjected; precommitfailure no mutation,postcommitloss originalretry exactlyonce |
| D115 | Populate/export then stop AND remove source; freshdestination imports retainedbytes; old tokens/references/passwordlogin/originalreceipts work, repeatreplacement restores; all ten edges |
| D116 | Corrupt envelope/accounts/tokenlinks/receiptowner/identity/history/revisions/policies/series/closures/plans; malformedstate422 exactdestnonmutation; valid exported original succeeds; adapters retained separately |
| D117 | Measure actual peer EOF under continuous header/body drip; bounded handling, health and exact state nonmutation; planned drip window is distinct from observed closure time |
| D118 | Discard a real committed POST response, then amend/cancel/export/import before retry; original response immutable, current reservation truthful, exactly one creation |
| D119 | Same caller/key/body across create and moves paths; ordered original receipts after collective swaps, subsequent changes and replacement |
| D120 | Two valid pipelined messages remain delimited; controlled close after first or two ordered responses; fresh retries prove exactly-once effects |
| D121 | Checksum-valid corruptions of password storage, token links, duplicate identity, overlap, instants, receipt method/body and timezone reject without destination mutation |
| D122 | Local year 0001/9999 dates with fixed IANA offsets whose intermediate UTC value crosses a library calendar bound; valid local starts/ends, availability/create/export/import/retry and UTC controls |
| D123 | Full offset-extrema lifetime: explicit start/end values, lookup/list order, half-open adjacent occupancy, overlap nonmutation, past cutoff rejections or future PATCH/moves/cancel, ordinary JSON export/import replacement, immutable creation/batch replay and repeat import |
| D124 | Valid historical IANA dates with offset seconds must still return strict RFC3339 timestamps representing the exact instant, through availability/create/lookup/retry/export/import |
| D125 | Historical IANA second offsets at year0001 and both-zone year9999 controls retain exact integer instants and local fields under strict RFC3339 serialization, occupancy, cutoff/amend/cancel and replacement/original replay; do not demand impossible seconds-bearing offsets or round instants |
| D126 | Actual old historical producer removed before fresh consumer: two retained tokens, four immutable original receipts, exact strict current projections, year0001 instants, occupied slots, new target write and repeated replacement; standalone integration separate from pytest counts |
| D127 | Four independent source formatter experiments combine both calendar extrema and both signs of a synthetic second offset; strict syntax and exact independently computed integer instant; no HTTP or claim about future IANA offsets |
| D201–D208 | Eleven independent pair/resource definitions: declared ordering/member occupancy/half-open release; four invalid pair variants; both-selector and summed capacity errors; atomic pair/single swaps and original receipts; collective rollback; unlisted member conflicts;20-request pair/member concurrency; cancelled pair seeds |
| D211–D215 | Eight browser definitions: actual committed201 loss then swap/pair-to-single repair and truthful current assignment; exact9007199254740993; two refusal/form/refresh cases; late search;375px/desktop routes/labels/keyboard/XSS/layout. D215-mobile failed at a96b130; V-S2-001 resolves at d8941d7 with the unchanged direct check |
| D216 | One live-browser transfer definition repeated on1→2/2→2: same session/form/body/key/reference across replacement; disclosed actual Stage2HTML/Stage1API transport adapter. Actual producer removal remains a separate lane |
| D217 | Standalone producer-removal integration: real Stage1 formerly-unknown table_ids stays part of immutable body identity while current Stage2 rejects both selectors on fresh keys; original receipts/tokens/references and new target writes survive |
| D218 | Two added full literal-label browser lifetimes: public/signed grid, form, confirmation, unchanged receipt retry, confirmed and cancelled lookup; exact geometry375/375 and1360/1360, fulltext/XSSsafe/onebooking. Separate from unchanged D215 |
| D219 | Two exact401-digit party browser cases, search and booking entry; ordinary fill and keyboard controls, exact API controls, real201-loss/originalretry. FAIL atd8941d7 and0c0a386 before browser creation, continuation NOT_REACHED there; unchanged source fully PASS at63cf798 |
| D220 | Two geometry definitions375/1360: full401-digit rendered summary and actual text fragments without page overflow/clipping, form/uncertainty/retry-confirmation/current lookup, exact wire query/body/key/original201→200 receipt and onebooking. PASS at63cf798; Builder intermediate3407px remains source-hash-attributed evidence, not an independent rejection ofd894/0c0 |
| D221 | Two decimal-text validation definitions for search/booking: eight invalid positive-integer inputs each reject visibly without requests/state mutation; accessible label/numeric keyboard hint/focus/mobile layout remain; ordinary corrected keyboard input books exactly once |
| D301–D332 |73 Stage3 public HTTP definitions covering policies/history/adoption/series, permissions, bounds, independent explanations, unknown-field identity, immutable receipts, accepted cutoff/terms, revision concurrency, per-date policies/DST/first-index rollback, permanent exceptions and batches |
| D325 | Actual source removal1→3/2→3/3→3; authentic original receipts, old empty histories and unchanged adopted anchors, genuine generated histories, final policies/series/counters and new target operations. Standalone integration separate from pytest counts |
| D333 | One counter sequence independently checks reset seeds0,create/policy/adoption/patch/cancel/batch increments, once-per-series, noops/replays/rejections0 and restaurant isolation |
| D334 |33 separately executed checksum-valid native snapshot corruptions; authentic journal unchanged, valid controls, exact destination nonmutation, post-rejection valid roundtrip and new write |
| D335 | Valid overlapping original series schedules, disjoint actual seating, permanent exceptions/cancel flags and repeat exact roundtrip |
| D401–D409,D412–D414 |60 new public HTTP definitions: exact objective including compact1e100000000 common cost with one-seat difference, full intervals/prior closures, inclusive limits, stale/noop/receipt precedence, counters/history, ownership/schema, collective amendments, DST and replacement lifetime. PREPARED/NOT_RUN |
| D410 |4 browser definitions: single/pair actual201loss then planner repair at375/1360; exact original retry/current full-label confirmation, lookup/grid, geometry and one diner booking. PREPARED/NOT_RUN |
| D411 |Standalone removed-producer integration for1→4/2→4/3→4/4→4; authentic old/final state, new target amendment, final plan/apply/amend receipts and pending plan. Not pytest count. PREPARED/NOT_RUN |
| D415 |Stage4 semantic corruption obligations in STAGE4-INTEGRITY-CONTRACT.md. Representation binding awaits exact candidate; not yet collected definitions or application outcomes |

## Evidence contract

Every attempt gets a unique directory, untouched logs, start/end/duration, exact command,
minimal environment, product/QA revisions and SHA256 file manifest. Every case records ID,
description, expected, observed, PASS/FAIL/ERROR/SKIP and duration. Raw request counts are
separate from test definitions and exclude source-level injections. Load percentiles are
computed from individual measured calls; concurrent request overlap is measured. Huge
responses preserve original client receive/decompression assertions; a stream hash or
server-only duration is supplemental evidence. Only synthetic test credentials enter
private snapshots; no environment dump or real personal data.

## Current Stage3 execution binding

Exact `4ce583cca13a033dd2f548ca982deec7200f8ad6` is **ACCEPT** after all six
Builder handoff parts.179 frozen/204 independent/152 official definitions PASS.
35 application attempts retain659 raw pytest executions:649PASS/10FAIL, with
four original email-oracle and six opaque-selector mismatches separately
reconciled; zero pytest ERROR/SKIP. Unchanged developer64methods retain62PASS/2ERROR;
separate explicit adapter runner62PASS. Six actual removed-producer executions
over three definitions include accepted1/2/current3 and historical object/offset/
ignored-selector compatibility. Live browser transfer passes each1→3/2→3/3→3.
35 actual source faults across13operations/3faulttypes, four formatters and two
deployment checks PASS, separately counted. All24 numeric cases PASS, including
1,100,002,780bytes received/decompressed2.589222691s and complete Decimal parse
4.885175492s with uncapped client. All nine prior defect families directly PASS.
The generated developer logs remain preserved outside the clean checkout, with
an additive chronology correction. The first isolated harness is not used for
clean-checkout qualification; a fresh clean exact-SHA harness passes120+25+7.
36 attempt manifests/923files verify. See REVIEW-4ce583c.md, JSON/case-matrix/
provenance for complete sources, observations, measurements and limitations.
Coordinator gate `f2bfa8297f77353675c2942fb765b18113b35266` reconciles this
Stage3 acceptance. Stage4 QA preparation now adds64 collected definitions to
the cumulative204, for268 independently collected definitions. Additional D415
opaque obligations need candidate-specific binding. All Stage4 application
outcomes and final-delivery checks remain NOT_RUN; see STAGE4-INTEGRITY-CONTRACT.md.

## Historical initial Stage3 rejection and repair preparation

Exact`0c0a3867fc38fff0824ec2f887a135a2965bb60f` is **REJECT**, V-S2-002 OPEN.
All179frozen and152official definitions pass;200independent definitions yield198PASS
and2FAIL. The original browser failure is repeated directly; no source inference.
32application attempts retain663raw pytest executions649PASS/14FAIL:2product,
4original email-oracle,6opaque-selector,2QA login-navigation races. Corrected setup
reruns separately pass the original D215 assertions; source/results remain preserved.
Unchanged developer64methods include2ERROR; explicit schema1adapter runner62PASS.
All24numeric definitions including original extreme full receive/parse pass.
Source35actual injections/13operations/3faulttypes,5removed-producer executions over
3definitions,4source formatter cases and2deployment configurations are separate lanes.
Six frozen upgrades plus live-browser transfer pass on each1→3/2→3/3→3 edge.
See`reports/stage-3/REVIEW-0c0a386.md`,JSON/case-matrix/provenance for exact sources,
timings, resources, controls and full unresolved-case disposition. No prior pass
qualifies a repair. Renewed Stage2 gate89d24c47 authorizes correction carry-forward;
fresh complete Stage3 review awaits Builder's new committedSHA/fullhandoff.
Prepared current catalogue:179 frozen,204 independent,152 official definitions,
including D219/D220/D221. `reports/preparation/STAGE3-CORRECTION-89d24c47.json`
binds exact sources and required lanes; new-candidate application outcome NOT_RUN.

## Historical Stage2 acceptance binding (reopened above)

Stage 2 product `d8941d7e630c9f2787623d1222f647d49b40ae91` is **ACCEPTED by Verifier**.
The complete exact-SHA gate passes frozen169/169, official145/145 and independent90/90.
V-S2-001 passes unchanged D215-mobile; two additional D218 definitions cover full
literal labels through confirmation, unchanged retry, lookup and cancellation.
Every one of seven measured states fits375/375 or1360/1360. Original D215 source
and all rejected evidence remain unchanged. All seven Stage1 repaired families pass
again. See `reports/stage-2/REVIEW-d8941d7.md`, its JSON inventory and
`case-matrix-d8941d7.json` for exact sources, attempts and observed outcomes.

Twenty-seven application attempts preserve521 raw pytest executions:
511PASS/10FAIL, zeroERROR/SKIP. Four original email-oracle failures and six opaque
selector mismatches are retained and explicitly reconciled through separate checks.
Source injections20 across8actualoperations/3faulttypes, formatter4, developer47,
two deployment configurations and five actual-removal executions over three standalone
integration definitions are separate lanes. Six frozen transfer definitions and D216
live-browser transfer pass on both1→2/2→2 without definition inflation.

All14 unchanged numeric definitions pass. Current R2N002-e100000000 availability
is1,100,002,780bytes, received/decompressed in3.790672238s; original complete Decimal
JSON parse in4.882439196s separately; uncapped client peak2,843,532KiB,service2CPU/2GiB.
This finite-case success does not establish a universal numeric bound.

Rejected `a96b13048d19a5d93d75bb6c51ee100e44a2d8fd` retains its full report/evidence
`06653fae61e2c505ac3a9eb863e24982a675dcee`, including original392px mobile overflow,
all oracle/selector observations and both detailed-official tooling failures. Its
independent total was88; only the two new D218 flow definitions raise the current
total to90. Prior `PREPARATION.md` stays a historical NOT_RUN preparation artifact;
`PARTIAL-705e187.md` retains the earlier11PASS partial attempt. These prior passes do
not qualify this repair. Coordinator alone reconciles advancement; Stage3/4 and final
packaging are still pending.

Stage 1 product `fd843b83db16ec8585d66af7ac0d6fac89aae82c` is **ACCEPTED by Verifier**.
V-S1-001 through V-S1-007 pass direct independent regressions, including exact
historical/calendar lifetimes and actual old historical producer removal.
See `reports/stage-1/REVIEW-fd843b8.md`, its JSON execution inventory and
`reports/stage-1/case-matrix-fd843b8.json` for exact sources, attempts and outcomes.
Reconciled results are frozen166/166, official120/120 and derived68/68. Four
original oracle failures and six selector mismatches are retained and reconciled.
Publication faults, formatter experiments, deployment and actual producer removal
are separate lanes. All earlier rejections remain unchanged. Coordinator alone
reconciles copy-forward. Stage2 is independently accepted; Stage3–4 and final delivery gates remain pending;
definition collection is not execution.

`reports/defects.json` tracks open violations and exact-SHA repair evidence. Original
oracle failures remain historical outcomes even when adjudicated. A representation
selector mismatch is a QA adaptation need, not automatically a product violation.
Official expected next-stage overshoot failures are recorded separately from required-suite
failures. Final ACCEPT requires all required rows executed, all application failures
reconciled and documented essential external blockers resolved or explicitly excluded
from the claimed outcome. No hidden-test claim is possible.

## Renewed Stage2 pair-cell gate at 4b2236f

All five Builder parts were visible before execution; recipient assembly and the immutable
clean checkout bind the exact product. Frozen169/independent106/official145 all reconcile
PASS. Raw537pytest executions preserve527PASS/10FAIL: four email-oracle and six opaque
selector failures, each separately reconciled without rewriting its original. Sourcefault20,
developer47,formatter4,deployment2 and five actual producer removals are separate counts.
Both1→2/2→2 execute all six frozen transfer definitions plus live browser continuation.

D222 is unchanged and passes mobile/desktop. D223 adds four all-day occupied/capacity
exclusion cases with available keyboard/label/order controls; D224 two real409 removal
and unchanged-form retries; D225 two realPOST201-loss cases with a preceding refresh
completing while retry is pending. Eight new definitions raise the global collected derived
union from336 to344, without duplicating D222 across revisions or widths already defined.
Exact401-digit D219, full-value375/1360D220, invalid-entry/keyboardD221 and literal-label
D215/D218 remain passing. The Stage2 repair does not close V-S2-003 in Stage3/4.

Originalnumeric14 includes1.1GB receive/decompression2.843900266s and complete uncapped
client Decimal parse5.749942583s separately; service2CPU/2GiB. Fresh unchanged isolated
harness passes120+25 and retains its expected next-stage policy404 probe. All8,494 clean
checkout filehashes and33attempt manifests/901artifact files verify. See the complete
`reports/stage-2/REVIEW-4b2236f.md` and JSON/case-matrix/provenance/final-audit artifacts.

## Final candidate qualification at 25ade1c

All216 frozen/344 independent/158 official definitions reconcilePASS at exactSHA. Raw892pytest rows preserve839PASS/53FAIL (4 email oracle +49 opaque-selector failures); all49 unchanged semantic assertions pass through the explicit schema4 selector. All10 prior defect families directly pass, including frozenU402/U404, unchangedD219/D222 andD220–D225. D404 uses the corrected other-r route;19D417 corrected cases pass without erasing their original QA encoding failures.

45 application commands ran sequentially. Source50 actual injections/18 names/3 types,83 unchanged developer methods (81PASS/2ERROR) plus81 explicit adapterPASS,4 formatter and2 deployment experiments remain separate. Four final incoming edges each execute6 frozen definitions, live browser and actual source removal; all10 edges bind currentaccepted producers. Unchanged official --all isolated has575 applicablePASS plus retained expected next-stage probes. Exact raw counts, descriptions, sourcehashes, timings, manifests and exceptions are in the review, case matrix and fresh-room inventory. Final concrete delivery check follows Coordinator gate and final docs; no fabricated native export or recording.
