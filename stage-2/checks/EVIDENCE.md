# Builder Stage 2 checks

These are developer executions of the copied-and-extended Stage 2 context. They do not replace independent exact-SHA Docker, frozen, upgrade or official runs.

Current status: historical acceptance at `d8941d7e630c9f2787623d1222f647d49b40ae91` is reopened by independently confirmed V-S2-002. The older pending/accepted descriptions below record their original chronology. The new browser repair awaits renewed full independent qualification; Stage 3 carry-forward waits Coordinator's reconciled gate.

* `20261005T084445.300430Z-domain/`: 47 unittest methods passed in 8.772 seconds (8.844 seconds subprocess duration), with source/test/log hashes. This is 37 inherited regression methods plus 10 Stage 2 pair/numeric/compatibility methods. Repeating the inherited methods does not make new definitions.
* `20261005T084243.952044Z-browser/`: seven Chromium case definitions passed. JSONL records measured case durations and expected/observed outcomes; `sources.json` records exact product/test hashes. Two actual POST 201 responses were fetched and then aborted at the browser response boundary, including a pending-form replacement-import case. Both recovered the original reference and current pair-to-single assignment, preserving raw body/key and one reservation. These are local HTTP/browser executions, not constrained-container or real-source-removal claims.
* The browser run also covers signup/login/navigation/current user/logout, unchanged success replay, lookup/cancel, stale search across restaurant labels/grid/form, exact party `9007199254740993` through query/form/raw JSON/retry, a concurrent occupancy refusal with retained form and refreshed grid, inert XSS labels, visible focus, and no page overflow at 375 and 1280 pixels. `mobile-375.png` and `desktop-1280.png` are actual screenshots inspected by Builder.
* `20261005T083103.178782Z-pair-check-reproduction/` preserves a developer assertion error: the expected options omitted an independently available single table `c`. The initial identical failure remains in the native tool transcript; the unchanged reproduction stores the full test definition, source hashes and log. The expectation was corrected to include both available singles. No product code was changed for that assertion correction.
* Earlier evidence directories were copied with accepted Stage 1 for provenance. They remain historical Stage 1 attempts, not Stage 2 executions.

The small sparse sum check uses exponent 100000 and compares prepared plain/gzip bytes. It is not a substitute for unchanged extreme R2N002 exponent 100000000 with complete original-client receive/decompression and parse. The Verifier owns that heavy execution, the 2 CPU / 2 GiB service limits, full frozen applicability, authentic producer-removal integration and final acceptance.

Inherited Stage 1 product bytes were checked unchanged against accepted `fd843b83db16ec8585d66af7ac0d6fac89aae82c`. Stage 3 and Stage 4 are not implemented.

## Feedback-panel refinement

The design hook identified a thick side accent and an accent border on rounded panels in `web/style.css`. Both were removed in favor of consistent thin borders; state text and background colors remain distinct. No suppression was added and neither finding remains outstanding. A single scoped detector pass returned an empty finding list.

`20261005T085804.442428Z-browser/` preserves a fresh execution after this CSS-only product change: all seven existing browser cases passed, including real committed-response loss, replacement import, exact large integer input, stale search and occupancy refusal. Its new 375px and 1280px screenshots were visually inspected. Python and JavaScript product bytes are unchanged from the initial Stage 2 candidate; this repeat adds executions, not case definitions. Independent acceptance is still pending.

## Direction-independent refusal wording

Coordinator found that the refusal message described the availability grid as “below”, while the grid is beside the form on desktop and above it on mobile. Product `a96b13048d19a5d93d75bb6c51ee100e44a2d8fd` changes only that string in `web/app.js`: “Availability has been refreshed; choose another table or time.” Original captures and commits remain intact.

`20261005T090524.770632Z-browser/` records seven existing browser cases passing after this change (7.884 seconds for the command). B206 verifies the visible error, retained form input, refreshed unavailable cell and responsive layout. Both new screenshots were inspected and show the corrected wording. No test definition or behavior changed; this is a further execution of the same seven definitions. The source hashes match the committed product bytes.

## V-S2-001 — long literal labels on mobile

The independent Verifier found 392px document width at a 375px viewport with a valid restaurant name, table label and display name containing the literal `<img src=x onerror="window.__qa_xss=1">`. Builder's direct reproduction in `20261005T091245.034986Z-label-layout/` preserves the same fixture, source hashes, screenshots and element geometry: the local Chromium/font environment measured 439px at 375px (FAIL), while the 1360px lifetime passed. Safe text rendering passed; this was intrinsic layout sizing, not HTML execution. The mobile grid's automatic minimum width was set by the unbreakable portion of the restaurant heading.

The repair lets the mobile grid track and its children shrink and wraps restaurant headings in both availability and lookup. It does not hide overflow or truncate displayed headings. `20261005T091323.356852Z-label-layout/` repeats the unchanged `browser_labels.py` reproduction: both widths PASS, including all public routes, signed-in booking, confirmation, signed-in routes and lookup detail (ten measurements per width, each exactly viewport width). Mobile booking and lookup screenshots were visually inspected. The two width variants are direct regressions of the reported D215 family, not additions to the frozen definition count.

`20261005T091329.293943Z-browser/` additionally repeats the existing seven browser cases; all PASS. Original failing inputs, captures and history remain intact. Independent verification of the committed repair is pending; the full repair handoff waits for the Verifier's remaining findings on the prior candidate.

## V-S2-002 — native numeric range and complete exact-value lifetime

Verifier D219-search and D219-booking independently show that native number inputs erase a valid 401-digit decimal party size while API controls accept it. The primary original attempt is `reports/stage-2/20261005T101600.241391Z-stage2-native-range-d8941d7-00c885b0/`; original Stage 3 candidate `0c0a3867fc38fff0824ec2f887a135a2965bb60f` independently reproduces both failures too. Original evidence remains untouched.

Builder's new `browser_numeric_entry.py` supplies two direct regression definitions, not new frozen definitions. Each attempt binds the exact product and test source hashes and records raw browser requests, DOM values, received original responses, screenshots, trace, duration, environment and status.

* `20261005T103442.119779Z-numeric-entry/`: both cases FAIL on the historical product bytes. Fill and 401 ordinary key events both leave the control empty with `badInput=true`; submit sends no availability or booking request. Loss/retry assertions are not reached.
* `20261005T103516.073561Z-numeric-entry/`: after replacing native number inputs, booking lifetime PASS; search FAIL because the now-preserved 401-digit summary expands document width to 3407px at a 375px viewport. This genuine intermediate failure is retained and repaired with full-text wrapping.
* `20261005T103545.885891Z-numeric-entry/`: both unchanged cases PASS, 8.763 seconds summed case duration. Fill and key input preserve all digits; search query and raw booking JSON are exact. A real successful POST 201 is fetched and its response aborted; the same form/body/key retries with 200 and the identical receipt. Each case leaves exactly one reservation with the exact party size, then looks up and cancels it. All measured search/uncertain/confirmation/lookup/cancel page widths equal 375px. Empty, zero, signed, fractional, exponent and alphabetic text fail locally without requests; ordinary values and leading-zero normalization remain valid.
* `20261005T103730.843425Z-browser/`: all seven existing B201–B207 cases PASS, retaining stale-search exclusion, exact `9007199254740993`, real committed-response loss/current-assignment repair, replacement import, refusal, navigation, labels and desktop/mobile behavior.
* `20261005T103747.056475Z-label-layout/`: both unchanged V-S2-001 width/lifetime variants PASS at 375px and 1360px. The final numeric confirmation screenshot was visually inspected; the complete count wraps without horizontal page scroll.

This repair changes only browser controls and summary wrapping in the product runtime. Python/API/Docker bytes and every Stage 1/Stage 3 file remain unchanged. No Docker, enormous-client or independent acceptance result is claimed by these local executions. The original and intermediate failures are additional executions of the same two new local definitions; they are not silently rewritten as passes.

## V-S2-003: unavailable pair cells

The later committed independent finding `850a16367801adefe0fbcde9fc7d0edf098bc7a9` reopened Stage 2 source `63cf798cf60baf3134a64e4db599c92d81561e3e` and the inherited Stage 3/4 browsers. [PAIR-VISIBILITY-REPAIR.md](PAIR-VISIBILITY-REPAIR.md) records the scoped Stage 2-only repair, two reproduced unchanged D222 failures and 25 successful corrected-runtime browser executions. Historical acceptance and all raw evidence above remain unchanged. A new exact-SHA independent review, not these local checks, decides renewed acceptance.
