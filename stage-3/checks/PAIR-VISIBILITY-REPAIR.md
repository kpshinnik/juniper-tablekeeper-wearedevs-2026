# Stage 3 carry-forward of V-S2-003

The renewed Stage 2 gate `b0e69e22fa1fd30e89516e09b0fecac45b74a2eb`
accepts product `4b2236fb6576b636d168b2cacf1a5d91921cf582`, independently
reviewed in evidence `92dc4c42b8f562d1548f4e36a53437a28f151a3f`.
All six Coordinator continuation sections were assembled before this repair;
the accompanying assembly JSON identifies the authored mirror and native delivery
receipts separately. That mirror is not a native room export.

## Invariants and failure behavior, recorded before editing

- Copy only the accepted Stage 2 per-slot pair-button omission into the existing
  Stage 3 browser. Preserve the server, numeric codec, CSS, HTML, policies,
  histories, adoption, series and accepted terms.
- A pair appears only when that slot's `available_options` includes it. Preserve
  declared order and literal labels. A pair excluded for the whole day has no row.
- Every single-table cell remains present, including unavailable false cells.
- Rendering availability must not reset the selected form, exact party text,
  original request body/key or pending/uncertain outcome. Refusal is distinct
  from lost response; unchanged retries retain the original receipt while
  confirmation and lookup read the current assignment.
- Partial-day occupancy, all-day occupancy, insufficient capacity, available
  keyboard selection, 375/1360 layouts, long labels, exact 401-digit values,
  stale search and refresh during a pending request are required boundaries.
- The API transaction and receipt publication points do not change. The repair
  only changes which pair buttons are rendered; no server mutation is added.
- Stage 1, accepted Stage 2 and rejected Stage 4 remain byte-identical. Existing
  failed Stage 3 D222 evidence and historical acceptances remain intact.

## Verification plan

Run unchanged D222 against the original Stage 3 browser, preserve its failure,
then copy the accepted browser and run unchanged D219–D225, the existing browser
flow and Stage 3 developer adapter. Use an ephemeral local HTTP service and local
Chromium only. These are Builder checks, not independent resource-constrained
container qualification. The Verifier must rebuild the new committed SHA and
execute the complete cumulative Stage 3 gate.

## Executed Builder checks

All five attempts below use a real ephemeral local HTTP service and local Chromium
where applicable. They do not establish Docker resource/offline qualification.
Every original log, JUnit failure and artifact remains unchanged.

| Attempt under checks/evidence | Observed result |
| --- | --- |
| 20261005T134537.910692Z-unchanged-browser-review | Original reopened Stage 3 runtime: unchanged D222 at 375/1360, 0 PASS / 2 FAIL / 0 ERROR / 0 SKIP. |
| 20261005T134611.888872Z-unchanged-browser-review | Corrected browser: unchanged D219–D225, 16 PASS / 0 FAIL / 0 ERROR / 0 SKIP. Exact 401-digit entry/loss/retry, geometry and invalid input, partial/all-day pair exclusion, capacity/order/keyboard, refusal and pending-response refresh. |
| 20261005T134627.110492Z-stage3-developer | Existing explicit developer adapter: 62 methods PASS, including policies/history/adoption, authentic imports, counters, atomicity, numeric and historical-calendar regressions. The two original incompatible fixture methods and their old errors are preserved; the documented adapter is explicit. |
| 20261005T134627.191379Z-browser | Existing B201–B207: seven PASS, including stale search, literal XSS, current assignment after pair-to-single repair, original retry and replacement import. |
| 20261005T134704.794207Z-label-layout | Existing literal-label/layout lifetime: two PASS at 375/1360. |

These attempts contain 25 corrected browser passes and 62 developer passes,
separate from two preserved original browser failures: 87 PASS / 2 FAIL across
89 local executions. No new test definitions are claimed. Tests precede the
product commit and bind exact source hashes; they are not claimed as execution
on a future commit. The committed candidate requires independent full review.
The optional wrapper later gained an external evidence-root setting, with no
assertion or runtime change, so postcommit checks can leave stage folders clean.
