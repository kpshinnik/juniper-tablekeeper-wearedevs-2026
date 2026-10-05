# The Juniper factory

Juniper Tablekeeper was built from an empty repository by three real BAND coding seats, from one initial human dispatch, in room `e04c2728-8535-41c8-be50-88eb8068fa09`. All four product stages are independently accepted and reconciled. Final product `25ade1c7add9a5701a511e07f79a619a3cb21b51` passes the unchanged clean isolated qualification with **575 applicable official executions**.

The final documentation and concrete delivery check are being completed. A genuine native full-room export has not been verified. Product acceptance therefore does not yet establish complete submission packaging. Nothing has been publicly pushed, published or submitted, and no real table has been booked.

## Actual seats and runtime

| Seat | BAND identity | Owned work |
|---|---|---|
| Coordinator | `kirill.pshinnik/coordinator` — `2797b972-fd4a-4a7e-99ca-81416ac9d83e` | Requirements, plan, acceptance, architecture, FACTORY, provenance and mandates |
| Builder | `kirill.pshinnik/builder` — `31aabbf4-b16e-4715-9e10-76681e9af4b7` | Four product folders, RUN instructions, English/Russian guides and demo materials |
| Verifier | `kirill.pshinnik/verifier` — `5df6c6e4-9cf7-4ebb-8d93-d69f6c297ca5` | Independent QA, reports, catalogs, exact-revision ACCEPT/REJECT and reproduction |

All three used **Codex / gpt-6-astra**, with the configured model override remaining null. The operator established the default model and the effective Never ask / Full access profile, generation1/1, before dispatch. The run did not change models, permissions or provider configuration. Coordinator did not implement product code.

The three files in [mandates/](mandates/) are byte-identical copies of the frozen generic mandates and begin with the actual harness and model. They describe reusable role behavior; track-specific contracts live in the specifications and room handoffs.

## How to reproduce the factory on another problem

1. Create a fresh empty Git repository separate from read-only requirements. Define the complete written problem, ordered milestones, allowed inputs, resource limits, acceptance criteria and local deliverables before dispatch.
2. In BAND, use **Add participants → Coding sessions** to attach three distinct active coding sessions. Give them the matching Coordinator, Builder and Verifier mandates, the same absolute workspace and separate Git author/committer identities. A roster entry alone does not start a coding session. Select the intended harness/model and prepare execution permissions before the run.
3. Add every configured seat to a fresh room and verify addressed delivery. Coordinator reads the complete requirements and sends numbered handoffs containing the relevant full specification, constraints, absolute paths, ownership and acceptance criteria. Send all parts before requiring work; separately record actual recipient assembly. A message ID or file pointer is not the requirements.
4. Builder derives invariants, failure behavior and boundary conditions, implements only assigned paths, performs local checks, and commits a full SHA. Verifier receives that exact revision, independently rebuilds a standalone clean checkout and executes official, supplied and independently derived checks.
5. Verifier reports ACCEPT or REJECT with the exact SHA, primary evidence and reproduction. Coordinator reconciles every applicable case, including contrary evidence. Genuine defects return to Builder for a new commit and a fresh exact-SHA review. Only an accepted stage may be copied forward.
6. Preserve all failures and corrections. Finish truthful documentation, measured duration/available usage and concrete packaging checks. Report an essential external blocker honestly instead of waiting for human steering or inventing evidence.

For another problem, replace the domain specifications, checks and architecture component IDs. Retain the role separation, complete handoffs, clean revision binding, failure preservation and explicit ownership.

## Repository coordination and recovery

Every writer uses an operating-system exclusive `fcntl.flock` on `.git/factory-repository.lock`. The lock covers the actual HEAD/index recheck, explicitly owned staging, commit and committed-path audit. Waits are bounded. Foreign staged paths are left untouched; the writer releases the lock and reports the concrete conflict. A historical chat reservation is not a live lock. No seat resets, stashes, amends, rebases or squashes another seat's work.

Private runtime tasks track each seat's own work. The shared board coordinates Builder and Verifier assignments. The active room plan is an immutable Markdown snapshot containing Arch JSON, with a separate diagram snapshot. Local [plan.md](plan.md) and [architecture.json](architecture.json) are the editable sources; publishing a new snapshot explicitly refreshes the room.

Native send acceptance and recipient assembly are different observations. This run encountered delayed visibility of long handoffs. Complete authored mirrors and actual native delivery IDs made already-sent parts inspectable; they were never presented as a native room export. Each reviewer recorded assembly before application execution. The final [six-part delivery continuation](provenance/final-delivery-handoff.md) includes all four verbatim specifications; its [receipts](provenance/final-delivery-handoff.json) record all accepted parts. Verifier's seven-part final decision contains the complete review, reproduction and cumulative criteria.

Only Verifier runs resource-sensitive qualification. Huge clients run sequentially to avoid confusing shared VM memory pressure with isolated service behavior. Builder uses lightweight local checks and leaves that qualification lane free. Owned containers and networks are uniquely labeled and cleaned; existing demos on8787/18082 and unrelated resources remain outside scope.

## Accepted revisions

| Stage | Product SHA | Independent evidence SHA | Coordinator gate SHA |
|---|---|---|---|
| 1 | `fd843b83db16ec8585d66af7ac0d6fac89aae82c` | `b5578cdd018398bde579322a78a161add719de4c` | `0fde6cc725d472cd0c9db36fa2969a6ecb747654` |
| 2 | `4b2236fb6576b636d168b2cacf1a5d91921cf582` | `92dc4c42b8f562d1548f4e36a53437a28f151a3f` | `b0e69e22fa1fd30e89516e09b0fecac45b74a2eb` |
| 3 | `301caf55085280f12197e393ab6b4735ef4046c3` | `f31cf3ab27938453c42b4d495ec54953c990153a` | `63617e70f29f564ddb490f48fa83e49d737bb4ee` |
| 4 | `25ade1c7add9a5701a511e07f79a619a3cb21b51` | `96329db1347c0e8b555282e22a35785643020d04` | `693f9ec5d4c2df6353a15f002ffb601bf765d13a` |

The final product SHA contains all four independently buildable folders. Stages1–3 remain byte-identical to the accepted earlier contexts. The separate Stage4 load-metrics addendum is `117db1a1e0e5d13510845961aaf348416e07e842`; it derives metrics from existing raw logs and adds no application execution.

A **product** SHA fixes the tested stage bytes. An **evidence** SHA adds reports. A **delivery** SHA adds final documents and packaging inputs. Later commits do not retroactively become the revision tested by an earlier report. Each report names the actual checkout and hashes. The concrete final delivery and its checker outcome will be bound separately.

## Architecture and implementation choices

The service is a fresh Python standard-library implementation with bundled local assets and timezone data. Each stage is a standalone Docker context. The transport accepts one unambiguous framed request, applies an absolute input deadline and closes the connection after the response.

Domain writes prepare a private candidate under a lock, including validation, immutable receipts and encoding, before publishing the state reference. Failure before publication leaves the destination unchanged. Response loss after publication preserves one committed operation and its original receipt. Whole-state preparation costs copying and encoding time; measured load results define the verified scope.

Exact decimal representation and iterative JSON operations retain finite numeric and deep unknown values without binary rounding. Snapshots carry opaque exact JSON inside the required object envelope, allowing ordinary JSON roundtrip without losing nested precision. Exact integer instants support calendar boundaries and historical IANA offsets.

Stage3 records successful operations with their original times and identities in a transaction journal. Import replay validates authentic policies, accepted terms, histories and recurring agreements without inventing earlier events. Stage4 adds exact lexicographic closure planning and atomic series amendments. The browser keeps a pending request's exact body/key and truthful uncertainty; after original receipt recovery it reads the current assignment.

State is in memory. Explicit export/import is required across process replacement; restart alone does not persist it. The challenge's unauthenticated test controls are not a production deployment claim. No real restaurant, payment or customer-data integration exists.

## Genuine failures and repairs

A green official suite never overrode a demonstrated defect.

| Observed problem | Real recovery |
|---|---|
| Initial Stage1 passed120 official checks but failed independent transport, DST closing, reset types, exact snapshot lifetime and semantic import cases | Five reviewed revisions closed seven defect families, including later calendar extrema and historical second-offset timestamp findings |
| Valid long literal labels overflowed the375px browser | Builder repaired intrinsic grid sizing and wrapping; independent current-flow and full-label regressions passed |
| Browser number inputs discarded a valid401-digit party value | Text-based exact decimal entry and serialization were repaired; genuine committed-response loss, retry and geometry were checked |
| Unavailable pairs remained visible as disabled booking cells | Stage2, Stage3 and Stage4 gates were reopened; the accepted two-line browser condition was copied and fully requalified in that order |
| Developer checks polluted an earlier isolated checkout | Original logs and chronology correction were preserved; the qualifying harness was repeated cleanly, and later developer checks used a separate checkout |
| Wrong email oracle, snapshot selectors, a QA restaurant URL and a QA Decimal encoder | Original FAIL/ERROR and source bytes remained; separately corrected expectations/adapters/tooling were executed without adding definitions |

The final review directly passes all ten demonstrated product defect families. The [acceptance ledger](acceptance.md), [final review](reports/stage-4/REVIEW-25ade1c.md) and [Builder history](demo/HISTORY.md) contain exact reproductions and revisions. The earlier full [factory chronology](provenance/factory-history-693f9ec.md) is preserved as the exact FACTORY text at gate693f9ec; its relative references were written for the repository root.

## Verification and evidence scope

| Final lane | Actual result |
|---|---|
| Frozen / independent / official definitions | **216 / 344 / 158 reconciled PASS**;718 primary canonical definitions |
| Distinct baseline security/load inputs | **84 security +20 load**, actually executed |
| Primary raw pytest executions | **892:839 PASS /53 FAIL /0 ERROR /0 SKIP** |
| Original failures | Four malformed-email oracle conflicts;49 earlier-layout selectors; separate104 adjudicated and49 semantic-adapter passes |
| Original developer / explicit adapter |81 PASS /2 fixture ERROR retained; separate81 adapter PASS |
| Unchanged isolated official all-stage run |**575 applicable PASS** (120+145+152+158),158 distinct definitions |
| Separate automatic future-stage probes |4 PASS /3 FAIL;31 unexecuted after expected failures, outside the proper earlier-stage contracts |
| Publication fault injection |50 actual PASS combinations;18 defined controls,18 executed controls,18 actually injected names,3 fault types, including reset; zero HTTP requests |
| Detached producer integrations |All10 current same/forward edges; four fresh incoming Stage4 edges;7 final standalone removal executions across3 integration definitions |
| Separate formatter / deployment checks |4 /2 PASS |

Every original failure, runner error and correction remains. Missing raw docstring descriptions in178 rows caused a provenance-audit tooling failure; separate descriptions from the original test names repaired the annotation audit without rewriting raw results. Collection and the eight planner-oracle selfchecks are QA tooling, not application PASS.

Verifier rehashed all11,031 tracked checkout files,45 attempt manifests,1,296 artifacts and50 executed test sources. Coordinator independently verified the1,296 artifacts,1,028 stage files and50 source hashes, and audited22 commits after the Stage3 gate without ownership violations. All30 frozen inputs and the official package remain unchanged. Frozen manifest SHA256 is `91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036`.

The [15:12:38 historical inventory](reports/history/20261005T151238.210978Z-final-history-25ade1c-ed3fc0df/inventory/README.md) separately indexes457 attempt records and8,208 primary case rows:7,914 PASS,293 FAIL and1 ERROR. It includes423 historical source injections in a separate lane. Repeats, aliases, corrected104, stage copies and transfer edges add no definitions. Developer, isolated harness, source, tooling, browser-document and packaging lanes are not combined into a misleading grand total.

### Load and extreme numeric observations

Services ran with2 CPU/2 GiB, read-only roots, required tmpfs and internal Docker networking. The client for the extreme original numeric test remained uncapped.

| Measured request scope | Requests | Observed peak | p50 | p95 | Maximum |
|---|---:|---:|---:|---:|---:|
| Instrumented HTTPX |13,838|50|0.005119834s|0.101003214s|3.563072849s|
| Baseline load subset |2,610|50|0.036946310s|0.411636146s|1.144046971s|
| Stage4 load subset, including setup/assertions |325|37|0.016398293s|0.051689933s|0.067209151s|

The Stage4 scenarios each requested50 workers for50 writes and25 shuffled reads. Observed concurrency is distinct from that requested pool size. Assertions check atomic assignments, exactly-once revisions/history and immutable original application receipts. Both subsets are already included in the HTTPX total. Uninstrumented browser, raw-socket, standalone and official-harness request totals are unknown. The [load addendum](reports/stage-4/LOAD-METRICS-25ade1c.md) binds raw hashes and nearest-rank percentile calculations.

The unchanged `1e100000000 +4` case receives and decompresses **1,100,002,780 bytes in3.563072849s**, passing the original five-second assertion. Complete original Decimal JSON parsing separately takes **6.614927763s**; uncapped client peak RSS is **2,845,436KiB**. The entire accepted-value lifetime passes. Server-generation and wire-only timings were not measured separately. A finite extreme PASS is not a universal bound on arbitrary output size or client memory, and hidden organizer tests remain unknown.

## Reproduce the local qualification

Actual environment: Python3.12 venv `/Users/kirillpsinnik/Code/wearedevelopers-hackathon/.venv/bin/python`; Docker CLI `/opt/homebrew/bin/docker`; context `colima-tablekeeper`; VM4 CPU/6 GiB. Cached runners are `df-harness-runner` and `tablekeeper-test-runner`. The latter defaults to pytest; standalone scripts require `--entrypoint python`. Browser binaries are in the project's `tools/browsers`.

Each judged service uses2 CPU/2 GiB, a read-only root, required tmpfs and an internal network with no outbound runtime access. Another container on that network reaches the service; host-published ports do not establish offline behavior. Use only uniquely owned resources and run large clients sequentially.

The actual qualifying command, from the read-only official directory, was:

```sh
DOCKER_CONTEXT=colima-tablekeeper /Users/kirillpsinnik/Code/wearedevelopers-hackathon/.venv/bin/python -m harness run --track tablekeeper --repo /Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final-checkouts/25ade1c7add9a5701a511e07f79a619a3cb21b51-43adda3f --all --mode isolated --out /Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final/reports/stage-4/20261005T150257.076527Z-official-all-isolated-clean-25ade1c-31c1b500/official
```

For reproduction, create another standalone checkout at that exact product SHA, verify empty Git status and no alternates, and use a new report directory outside it. Keep official dependencies and assertions unchanged. The actual independent commands are in [RUN-PLAN-25ade1c.json](reports/stage-4/RUN-PLAN-25ade1c.json) and per-attempt metadata. Product run instructions are in the root guides and each stage's RUN.md.

The final concrete delivery check uses the unchanged command from the same official directory:

```sh
/Users/kirillpsinnik/Code/wearedevelopers-hackathon/.venv/bin/python -m harness check "$JUNIPER_DELIVERY_CHECKOUT" --track tablekeeper
```

Set that variable to the concrete clean delivery copy named in the final report. Verify its exact revision, matching stage bytes, mandates and FACTORY; retain stdout, stderr, exit status, source hashes and every finding. The product qualification command and packaging checker serve different purposes.

## Measured duration and available usage

The first Coordinator clock was **2026-10-05T06:21:47Z**, not a claimed provider-session creation or exact dispatch time.

| Gate | UTC on2026-10-05 | Elapsed from first clock |
|---|---|---|
| Stage1 |08:18:24|6,997s —1h56m37s|
| Initial Stage2, later reopened |09:46:58|12,311s —3h25m11s|
| Exact-number Stage2 repair, later reopened |11:08:13.831|17,186.831s|
| Initial corrected Stage3, later reopened |11:41:30|19,183s|
| Current Stage2 pair repair |13:34:43|25,976s —7h12m56s|
| Current Stage3 pair repair |14:20:21|28,714s —7h58m34s|
| Final Stage4 product gate |15:23:07|32,480s —9h1m20s|

The final45 application commands total **675.231466s** across **680.465478s**, from14:54:20.965722 to15:05:41.431200UTC. That test window differs from the cumulative factory duration. Final delivery completion time is recorded separately at closeout.

The latest [native room usage observation](provenance/usage-final-observation.json), at **15:16:24.353044UTC**, reports **316,529,051 aggregate tokens** and **$464.81803 catalog-equivalent** across three sessions. It is unchanged from13:42 despite subsequent work. Token categories and active-run completeness are unspecified; this is observed, potentially lagging attribution, not a verified complete token total. The per-seat equivalents are Coordinator$156.929914, Builder$121.247236 and Verifier$186.64088. Actual provider billing is **unknown**, not zero, and the estimate is **not an invoice**. Earlier observations remain in provenance/.

## Delivery boundary

All artifacts remain local to this project and its BAND room. The requested video artifact is a4:40 real-video storyboard with an encoding estimate below300MB; no actual recording, measured video file or event submission is claimed.

The full native room export must remain genuine and unchanged except its filename. Four supported download attempts returned no verified event or file path. Room observation works; this does not prove that BAND was unavailable or that Chrome saved nothing. [Export observations and the allowed operator step](provenance/export-readiness.md) explain how a later full native export would form a new delivery revision, not retroactively change this run's result.

A raw packaging failure remains a failure. Public Docker GPG fingerprint findings are adjudicated against the exact retained bytes and hashes; the checker is never altered and actual credentials are never hidden. Final local delivery will report the concrete check outcome and any remaining export dependency explicitly.
