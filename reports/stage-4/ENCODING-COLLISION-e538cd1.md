# Stage4 exact JSON carrier investigation

Product **e538cd16bbd96d4206d89f17a67791e759c00823**. **19/19 D417 cases PASS; no collision demonstrated within this bounded scope.** Stage4 remains **REJECT** for V-S2-003. The original full review and its evidence are unchanged.

Six carrier-shape cases exercise all four writes (booking, preview, apply, series amend), including wrapper-like objects, number/cost-like dictionaries, arrays, serialized strings with Unicode/control characters, 128 nested containers, and exact compact numbers ±100,000,000 in exponent magnitude. Equivalent numerical spellings preserve original receipts before and after ordinary outer-envelope JSON roundtrip, replacement import and real booking changes. Four direct type-identity cases preserve boolean/number/object distinctions. Nine checksum-valid forged-carrier cases reject 422 with exact destination nonmutation, while equivalent signed-cost controls and valid original roundtrips succeed.

Each lifetime case checks 4 initial equivalent replays, 8 post-import original/equivalent replays and 24 distinct-value conflicts. Current repaired assignment/time remains distinct from immutable original receipts. Internal attacks cover duplicated or missing paths, a path into a user null, boolean/negative array indices, object/boolean terms, negative cost and journal-inconsistent cost. Old receipts remain replayable and new plan application succeeds after restoring valid state.

Two attempts executed the same 19 definitions: **38 executions, 19 PASS, 19 raw FAIL, 0 ERROR, 0 SKIP**. The first attempt failed inside the QA standard-JSON encoder because an inherited helper returned Decimal for outer format_version. Its original source commit, logs, JUnit, JSONL and hashes remain preserved; the separate correction uses ordinary JSON parsing for the outer envelope and keeps the payload opaque. Corrected QA source SHA256: `25668245400041709caf8afe859515534b9a7ccf427498ed89f19b81686b9201`. It was executed as an explicitly hash-bound working correction while Builder-owned staged paths were untouched, then included unchanged in the evidence commit.

Corrected run: **11.196909 s**, **855 measured HTTP requests**, **0 HTTP 5xx**, max complete receive/decompression **0.060352 s**. Both attempts total **29.153638 s** and **1080 measured HTTP requests**. Service verified at 2 CPU/2 GiB, read-only root, internal network, with uncapped client. No source injection or source-only application definition is counted. Two immutable manifests verify **48 artifact files**.

- Initial raw attempt: `reports/stage-4/20261005T130056.421844Z-encoding-collision-e538cd1-3cf2c2d8`.
- Corrected attempt: `reports/stage-4/20261005T130426.567489Z-encoding-collision-codec-corrected-e538cd1-b0724a54`.
- Complete case outcomes, durations, expected/observed assertions, source/runtime hashes and metrics: `ENCODING-COLLISION-e538cd1.json`.
- Source binding and independent coverage: `ENCODING-COLLISION-PREPARATION-e538cd1.json`; QA-only correction: `ENCODING-COLLISION-QA-CORRECTION-e538cd1.json`.

The collected derived union grows from 317 to 336 by these 19 actual definitions; repeated attempts and codec correction add no definitions. Frozen 216 and official 158 counts are unchanged. This investigation does not establish universal collision freedom or reopen the already completed full-suite execution.
