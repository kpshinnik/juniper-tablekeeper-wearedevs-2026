# Stage 4 load metrics addendum

Exact product: `25ade1c7add9a5701a511e07f79a619a3cb21b51`. Primary ACCEPT evidence: `96329db1347c0e8b555282e22a35785643020d04`. This adds metrics derived from existing raw bytes, with zero new application definitions, executions or requests. The original decision, raw logs and hashes remain unchanged.

The Stage 4 load attempt records **325 instrumented HTTP requests**, including setup, assertions and the 225 mixed concurrent calls. Nearest-rank **p50 is 0.016398293009842746 s**, **p95 is 0.05168993299594149 s**, and **maximum is 0.06720915099140257 s**. These timings include send, receive and decompression. The observed peak is **37 requests in flight**. Each scenario requested a pool of **50 workers**, with 50 writes and 25 shuffled reads; this requested worker count is distinct from observed concurrency.

| Frozen scenario | Instrumented requests including setup/assertions | Observed peak in flight | p50 (s) | p95 (s) | Maximum (s) | Concurrent write results |
|---|---:|---:|---:|---:|---:|---|
| L401 same key | 92 | 32 | 0.018480660000932403 | 0.047047569998539984 | 0.059033209006884135 | One 201; 49 identical original-receipt 200 replays |
| L402 different keys | 92 | 37 | 0.016157951002242044 | 0.04080980901198927 | 0.05822401600016747 | One 201; 49 `plan_already_applied` 409 conflicts |
| L403 competing plans | 141 | 31 | 0.011849910995806567 | 0.05760745098814368 | 0.06720915099140257 | One 201; 49 `stale_plan` 409 conflicts |

All 25 reads per scenario returned 200 and showed either the complete original assignment or complete applied assignment. The unchanged assertions also verify one reservation revision increment per moved booking, one restaurant revision increment for the whole plan, unchanged identities/times/party sizes/accepted terms, intact older history plus one reassigned entry with the winning plan ID, and the immutable original apply receipt after later cancellation. Each of the three definitions passed. The recorded mixed-call elapsed timings also include JSON parsing; their separate statistics are retained in the JSON addendum.

This Stage 4 subset is reported separately from the **2,610 baseline load requests** (observed peak 50; p50 0.036946310006896965 s, p95 0.41163614600372966 s, max 1.144046971006901 s). Both are subsets of the already reported 13,838 instrumented HTTPX requests and are not added again to that count.

Reproduction: parse `send_receive_decompression_s` from every row of the source JSONL, sort ascending, and select index `ceil(N*p)-1` for each percentile. Observed peak is `max(inflight_at_start)`. Group by `case` for the rows above. The complete original attempt manifest was rehashed successfully before deriving this addendum.

- [Structured metrics and raw/source hashes](LOAD-METRICS-25ade1c.json)
- [Original request log](20261005T150145.533926Z-stage4-load-25ade1c-2ec04fd2/http-requests.jsonl), SHA256 `bdbea464e6ca227dd06b5168f98db7f9483ed0b9675440256ff8cba9fc37d507`
- [Original case results](20261005T150145.533926Z-stage4-load-25ade1c-2ec04fd2/cases.jsonl), SHA256 `9e3cdb80366c7bf0087fa362def04586535301512196441fa65da56b6fa7d703`
- [Original ACCEPT review](REVIEW-25ade1c.md)

AC07.4 reporting is complete with this supplement. The exact-product ACCEPT decision and final packaging boundary remain unchanged.
