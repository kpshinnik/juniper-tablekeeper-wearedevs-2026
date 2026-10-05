# V-S2-003 scoped Stage 2 repair

Before editing, the required invariants are: render a pair cell only when that
slot's `available_options` contains the declared pair; retain every single-table
cell and its true/false status; retain declared pair order and literal labels;
omit a pair row if no slot offers it. Capacity and occupancy remain API decisions.

The current failure comes from including a pair row when any slot offers it,
then appending a disabled pair button at all other slots. The repair must remove
the actual unavailable button, not merely rename its test ID. The board update
must not clear the separate selected form, exact request body/key or uncertainty.
No mutation, API, numeric parsing, receipt or server state change is needed.

Boundaries to verify include one occupied member, touching free intervals,
part-day and all-day exclusion, insufficient pair capacity, available pair
ordering, unavailable singles, preserved input/selection after a confirmed
refusal, a retry in flight while availability refresh completes, and actual
committed-response loss followed by unchanged original retry/current reads.
Both 375px and 1360px layouts must remain usable. Prior exact 401-digit entry,
invalid-text recovery, stale search and literal-label regressions still apply.

Compatibility constraints: only Stage 2 and owned root/demo documentation may
change in this repair. Stage 1 remains accepted; Stage 3 and Stage 4 keep their
reviewed bytes until their respective preceding gates are renewed. Historical
acceptances, all raw failures and independent evidence remain untouched.

Builder's local HTTP/Chromium runs are reproductions and development checks,
not the independent fresh exact-SHA qualification. Verifier retains heavy
Docker/resource testing and the full cumulative gate. The actual attempts below retain their exact source hashes; preparation alone is never PASS.

## Executed local attempts

All paths below are under `checks/evidence/` and use a real ephemeral loopback HTTP service and Chromium. No Docker/service resource qualification or independent ACCEPT is claimed.

| Attempt | Result |
| --- | --- |
| `20261005T125315.201008Z-unchanged-browser-review` | Original Stage 2 runtime: unchanged D222 mobile/desktop both FAIL, 0 PASS / 2 FAIL / 0 ERROR / 0 SKIP. Raw JUnit, logs, observations, screenshots, traces and hashes preserved. |
| `20261005T125606.471992Z-pair-visibility` | Corrected runtime: eight complementary browser definitions PASS (four behaviors × two widths). Partial-day/capacity and all-day exclusion, declared labels/order/keyboard, all single cells, confirmed-refusal form/body/key preservation, and genuine POST 201 loss followed by a board refresh while an unchanged retry remains in flight. |
| `20261005T125639.102164Z-unchanged-browser-review` | Unchanged D219/D220/D221/D222: eight executions PASS, no FAIL/ERROR/SKIP. Exact 401-digit keyboard entry, actual POST 201 loss/original retry, five-state geometry, invalid text/recovery and pair-cell absence. |
| `20261005T125711.918066Z-browser` | Existing B201–B207: seven PASS, including stale search, literal XSS, pair-to-single repair before original retry, replacement import and exactly one booking. |
| `20261005T125859.319587Z-label-layout` | Existing full literal-label regression: two PASS at 375/1360px. |

There are 25 successful browser executions across the four repaired-runtime lanes above, plus the two preserved baseline D222 failures. The eight new local definitions are B223–B226 at two widths; reused independent and earlier local definitions are not new. This count is separate from Verifier's frozen/derived catalogues. The UI runtime change is one conditional plus its explanatory comment. All server, JSON, CSS and HTML behavior stays unchanged; Stage 1, Stage 3 and Stage 4 remain at their reviewed bytes. The full renewed Stage 2 gate must be independently executed on the committed candidate.

## Preserved staging check outcome

The first staging attempt stopped before commit because the full cached `git diff --check` returned exit 2 for trailing spaces in four lines of the original D222 failure text: baseline `junit.xml` lines 29/64 and `tests.log` lines 33/71 (`E       Actual value: 1 `). Those raw bytes remain unchanged. The subsequent commit audit scopes whitespace validation to product/check-source/documentation files and explicitly retains the raw-log nonpass. An additional unchanged D222 execution began before a commit existed; its recorded repository HEAD and exact source hashes, not an intended postcommit label, determine its provenance. It is a repeated execution, not new definitions or committed-candidate qualification.
