# Juniper Tablekeeper delivery plan

Room: e04c2728-8535-41c8-be50-88eb8068fa09. Initial human dispatch: 39dff2fa-68d0-4bad-89a0-cd75dc8e282e.
Workspace: /Users/kirillpsinnik/Code/wearedevelopers-hackathon/band-work/final.
Coordinator first measured the run at2026-10-05T06:21:47Z. All four product stages are accepted as of2026-10-05T15:23:07Z. Final product `25ade1c7add9a5701a511e07f79a619a3cb21b51` has independent evidence `96329db1347c0e8b555282e22a35785643020d04`:216frozen/344independent/158official definitions reconciledPASS, all ten demonstrated defect families closed, and unchanged clean isolated --all with575applicablePASS. Original failures and tooling corrections remain preserved. The complete decision and six-part final continuation are delivered, including all four verbatim specs. Next: Builder finishes current English/Russian guides/demo; Coordinator finishes factory/provenance; Verifier checks a clean concrete final delivery and preserves raw outcome. Product folders stay unchanged. Native full-room export remains unverified after four attempts; the explicit operator fallback and packaging limitation remain. No recording or public submission is claimed.

## Ownership and acceptance

Coordinator owns this plan, architecture.json, FACTORY.md, acceptance.md, provenance/ and mandates/.
Builder owns stage-1/ through stage-4/, their RUN.md, README.md, FEATURES.md, FEATURES.html and demo/.
Verifier owns qa/, reports/, independent test catalogs and decisions.
All seats run Codex / gpt-6-astra, with no model override per the dispatch. Use each seat's own Git author and committer.
The shared repository lock is an OS flock on .git/factory-repository.lock, held through index/HEAD checks, owned-path staging, commit and path audit. Foreign staged paths are left untouched.

## Ordered work

1. Build Stage 1 from the complete official specification. Independently review the full commit SHA against every applicable official, frozen and derived case. Reconcile each result in acceptance.md before advancement.
2. After acceptance, copy Stage 1 into Stage 2 and extend with browser flows and combined tables. Verify prior contracts, upgrade edges and real response-loss recovery.
3. After acceptance, copy Stage 2 into Stage 3 and extend policies, histories and recurring agreements. Verify authentic migration and no fabricated history.
4. After acceptance, copy Stage 3 into Stage 4 and extend exact closure planning and series amendments. Verify independent optimization, original receipts and current UI assignment.
5. Qualify the immutable final product SHA from a standalone clean checkout using unchanged official --all --mode isolated. Complete all ten same/forward upgrade edges, producer-removal integration and final distinct security/load executions.
6. Finish truthful English/Russian docs, local submission materials and real-video storyboard. Obtain the unchanged native full room export where available; otherwise document the operator export step explicitly. Run the unchanged package checker on a clean final delivery copy. Report local-only outcome, exact revisions, measured elapsed time and available usage.

## Gates

AC01 provenance and role separation; AC02 independent stage build/runtime; AC03 complete API; AC04 truthful responsive UI; AC05 policies/history/series; AC06 optimizer/amendments; AC07 comprehensive reconciled execution; AC08 clean exact-revision qualification; AC09 complete local documentation and packaging; AC10 honest counts, costs and duration.
The detailed matrix in acceptance.md remains authoritative for case reconciliation. An expected overshoot failure is distinct from a product failure; four known original malformed-email assertions are preserved and adjudicated against Stage 1 section 6. No test collection or oracle selfcheck is an application PASS. Unknown organizer tests remain unknown.

## Inputs and boundaries

Official guide and complete four-stage specs are authoritative, read-only. The entire supplied webinar transcript has been read for factory context; current written requirements govern discrepancies.
Frozen input manifest SHA256: 91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036.
No prior implementation, archive or competing product is an input. No publication, external submission or real booking.
Verifier owns resource-sensitive service testing; huge clients run sequentially, service limited to 2 CPU / 2 GiB, client limits preserved.

## Architecture

```arch
{
  "kind": "layered",
  "title": "Juniper Tablekeeper: stage progression and independent acceptance",
  "layers": [
    {
      "id": "factory",
      "title": "Factory seats",
      "items": [
        {
          "id": "coordinator",
          "label": "Coordinator",
          "detail": "Requirements, ownership, gates and provenance"
        },
        {
          "id": "builder",
          "label": "Builder",
          "detail": "Product implementation and commit"
        },
        {
          "id": "verifier",
          "label": "Verifier",
          "detail": "Independent exact-revision execution and decision"
        }
      ]
    },
    {
      "id": "product",
      "title": "Independent service image per stage",
      "items": [
        {
          "id": "browser",
          "label": "Local diner browser",
          "detail": "Stage 2 onward; stale search and response-loss recovery"
        },
        {
          "id": "service",
          "label": "HTTP service",
          "detail": "Strict framing, exact JSON and authenticated atomic operations"
        },
        {
          "id": "policies",
          "label": "Policies and histories",
          "detail": "Stage 3 immutable accepted terms and events"
        },
        {
          "id": "series",
          "label": "Recurring agreements",
          "detail": "Stage 3 adoption; Stage 4 collective amendments"
        },
        {
          "id": "planner",
          "label": "Closure planner",
          "detail": "Stage 4 exact moved-count, unused-seat and rank ordering; compact arithmetic, preview and atomic apply"
        }
      ]
    },
    {
      "id": "state",
      "title": "State and portability",
      "items": [
        {
          "id": "transactions",
          "label": "Atomic publication",
          "detail": "Prepare validation, resulting state and receipt before commit"
        },
        {
          "id": "snapshots",
          "label": "Portable snapshots",
          "detail": "Replacement import, old tokens and immutable original receipts"
        },
        {
          "id": "journal",
          "label": "Operation journal",
          "detail": "Stages 3–4 recorded times and identities; replay validates each prior-stage baseline and later operations"
        },
        {
          "id": "closures",
          "label": "Applied closures",
          "detail": "Stage 4 half-open intervals published atomically with seating assignments"
        }
      ]
    },
    {
      "id": "qualification",
      "title": "Independent qualification",
      "items": [
        {
          "id": "qa",
          "label": "Frozen and derived cases",
          "detail": "216 distinct supplemental definitions plus full-contract checks"
        },
        {
          "id": "official",
          "label": "Unchanged official harness",
          "detail": "Isolated clean-checkout exact-SHA stage and final runs"
        },
        {
          "id": "evidence",
          "label": "Immutable attempt evidence",
          "detail": "Raw failures, hashes, metrics, revisions and native room export"
        }
      ]
    }
  ],
  "flows": [
    {
      "from": "coordinator",
      "to": "builder",
      "label": "Complete numbered task and spec"
    },
    {
      "from": "builder",
      "to": "verifier",
      "label": "Committed full SHA and setup"
    },
    {
      "from": "verifier",
      "to": "coordinator",
      "label": "ACCEPT or REJECT with evidence"
    },
    {
      "from": "browser",
      "to": "service",
      "label": "HTTP and truthful retries"
    },
    {
      "from": "service",
      "to": "transactions",
      "label": "Validate and prepare"
    },
    {
      "from": "policies",
      "to": "transactions",
      "label": "Accepted terms and history"
    },
    {
      "from": "series",
      "to": "transactions",
      "label": "Collective changes"
    },
    {
      "from": "planner",
      "to": "transactions",
      "label": "Atomic plan apply"
    },
    {
      "from": "transactions",
      "to": "snapshots",
      "label": "State with original receipts"
    },
    {
      "from": "snapshots",
      "to": "journal",
      "label": "Validate recorded operation provenance"
    },
    {
      "from": "journal",
      "to": "transactions",
      "label": "Reconstruct histories, terms and counters"
    },
    {
      "from": "qa",
      "to": "service",
      "label": "Adversarial and browser checks"
    },
    {
      "from": "official",
      "to": "service",
      "label": "Offline 2 CPU / 2 GiB"
    },
    {
      "from": "qa",
      "to": "evidence",
      "label": "Case outcomes and hashes"
    },
    {
      "from": "official",
      "to": "evidence",
      "label": "Unchanged reports"
    },
    {
      "from": "transactions",
      "to": "closures",
      "label": "Publish closure with assignments"
    },
    {
      "from": "closures",
      "to": "service",
      "label": "Availability and write conflicts"
    },
    {
      "from": "closures",
      "to": "snapshots",
      "label": "Portable closure state"
    }
  ]
}
```
