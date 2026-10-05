# Stage 1 repair decision: REJECT, superseded

Product: `e5e6305a96b92057324ff8ac5a62afce84651669`.
New acceptance target requested by Builder: `7d7643857eeac6396467a791d93b0fa7c43b8fa2`.
Room: `e04c2728-8535-41c8-be50-88eb8068fa09`.

V-S1-005 still reproduces in all five semantic receipt cases. Decode the opaque
payload string, change original party/body/start/end or reverse batch response order,
serialize it and recompute its checksum. The import returns204 and changes the
destination; expected422 validation_failed and exact nonmutation. The unchanged
control imports204 and its original string checksum is independently verified.

Primary evidence: [adapted snapshot attempt](20261005T071057.364580Z-snapshot-adapted-e5e6305-89546443/).
QA adapter revision: `379d59671984f50833cf4f8f50dc68b459c90f4c`.
The five outcomes are genuine product failures; cross-owner receipt rejection in
the same adapted suite passes.

| Executed checks | PASS | FAIL | Reconciliation |
|---|---:|---:|---|
| Official Stage1 isolated |120|0|Exact clean standalone revision; unchanged harness|
| Original baseline |100|4|S064–S067 original401 oracle conflicts with explicit422 requirement|
| Adjudicated same baseline |104|0|Same definitions, original raw failures preserved|
| Common frozen |43|1|B003 cannot descend into new opaque string payload; selector mismatch, not product defect|
| Numeric original Stage1 |12|0|Unchanged full-client assertions and accepted-value lifetime|
| Derived original semantics |0|5|Old object-payload checksum selector is inapplicable; raw failures retained|
| Explicit adapted semantics + B003 |1|5|B003PASS; five genuine V-S1-005 failures|
| Independent derived HTTP |40|0|Includes all reset types, actual slow-stream EOF, exact JSON lifetime and atomicity|
| Unchanged developer checks |21|0|Separate from independent checks|
| Source publication fault injections |20|0|Eight executed controls, three actually injected fault names, zero HTTP count|

V-S1-001 slow-stream deadlines, V-S1-002 both DST gap-closing cases, and V-S1-003
invalid-reset nonmutation pass their independent reproductions on this revision.
They require reverification on the final candidate. V-S1-004's unchanged numeric
upgrade tests and actual producer-removal integration were not executed on this
superseded candidate; no repair claim is inferred from developer tests.

There are315 raw pytest execution outcomes:300PASS/15FAIL. The failures consist
of four retained email-oracle conflicts, six representation-selector mismatches,
and five product counterexamples. An adapter adds no new underlying definition.
The JSON report preserves every attempt, source hash, raw case outcome, command
duration and measured HTTP request metrics. All attempt manifests rehash cleanly.
Nothing in this report rewrites the original failed evidence.

Builder requested the newer candidate while this review was active. Completed
work is retained; remaining upgrade checks move to the new exact-revision review.
No later stage is authorized by this rejection. Actual billing and token usage
remain unknown.
