"""Reconcile immutable first-review evidence without changing any raw attempt."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path

from summarize import metrics, read_rows

ROOT=Path(__file__).resolve().parent.parent
SHA='89582510069e984f446060d797e138f4a3bf08f9'
OUT=ROOT/'reports/stage-1'


def main():
    attempts=[];cases=defaultdict(list);all_http=[];load=[]
    for path in sorted(OUT.glob('*8958251*')):
        if not path.is_dir() or not (path/'result.json').exists():continue
        result=json.loads((path/'result.json').read_text())
        if result['kind']!='APPLICATION':continue
        assert result['product_sha']==SHA
        manifest=json.loads((path/'manifest.sha256.json').read_text())
        mismatches=[name for name,digest in manifest.items()
                    if hashlib.sha256((path/name).read_bytes()).hexdigest()!=digest]
        assert not mismatches,(path,mismatches)
        rows=read_rows(path/'cases.jsonl')
        http=read_rows(path/'http-requests.jsonl');all_http+=http
        load_http=[r for r in http if 'test_load.py' in (r.get('case') or '')]
        load+=load_http
        relative=str(path.relative_to(ROOT))
        entry={'path':relative,'manifest_sha256':hashlib.sha256((path/'manifest.sha256.json').read_bytes()).hexdigest(),
               'duration_s':result['duration_s'],'started_at':result['started_at'],'ended_at':result['ended_at'],
               'qa_sha':result['qa_sha'],'returncode':result['returncode'],'command_outcome':result['command_outcome'],
               'case_totals':dict(Counter(r['outcome'] for r in rows)),'case_executions':len(rows),
               'httpx':metrics(http),'load_httpx':metrics(load_http),'integrity_mismatches':mismatches}
        if (path/'official/report.json').exists():
            entry['official_report']=json.loads((path/'official/report.json').read_text())
            entry['next_stage_probe']=json.loads((path/'official/stage-2.counts.json').read_text())
        for row in rows:
            key=row['id'].replace('baseline-adjudicated/','baseline-original/')
            cases[key].append({'attempt':relative,'variant':row['id'],'outcome':row['outcome'],
                               'duration_s':row['duration_s'],'test_sha256':row['test_sha256'],
                               'metrics':row['metrics']})
        attempts.append(entry)
    # Every completed collection has its own source hash; retain changed test
    # versions and the original versus adjudicated run as separate observations.
    matrix=json.loads((ROOT/'qa/catalog.json').read_text())
    catalog={r['id']:r for r in matrix['cases']}
    for attempt in attempts:
        for row in read_rows(ROOT/attempt['path']/'catalog.jsonl'):
            key=row['id'].replace('baseline-adjudicated/','baseline-original/')
            if key not in catalog:
                catalog[key]={'id':key,'description':row['description'],'stages':[1,2,3,4],
                              'source_sha256':row['source_sha256'],'source_line':row['line']}
    for key,row in catalog.items():
        row['observations_at_product_sha']=cases.get(key,[])
        row['latest_observed_outcome']=cases[key][-1]['outcome'] if key in cases else 'NOT_EXECUTED_IN_THIS_REVIEW'
    latest={k:v[-1]['outcome'] for k,v in cases.items()}
    frozen={k:v for k,v in latest.items() if k.startswith('frozen/')}
    derived={k:v for k,v in latest.items() if k.startswith('derived/')}
    assert len(frozen)==166 and len(derived)==45,(len(frozen),len(derived))
    def find(label):
        return next(a['path'] for a in attempts if label in a['path'])
    common=find('-common-');upgrade=find('-upgrade-1to1-');confirmation=find('-derived-confirmations-')
    semantics=find('-snapshot-semantics-')
    defects=[
      {'id':'V-S1-001','title':'Continuous header/body bytes renew an inactivity timeout',
       'criterion':'AC03.7; bounded incomplete HTTP handling and ordinary request deadline',
       'cases':['R002','R003','D117[header]','D117[body]'],
       'reproduction':'Send an incomplete login header or Content-Length1000 body, then one byte every0.2s for6.5s. Read actual peer response and EOF using select/recv.',
       'expected':'Controlled response/closure within6s of request start; health and exact state unchanged.',
       'observed':'Frozen continuous8s probes saw no closure. Independent probes recorded first400/EOF only at9.3634s(header) and9.3560s(body), about3s after drips stopped. Health200 and exact state unchanged.',
       'evidence':[common,confirmation]},
      {'id':'V-S1-002','title':'Skipped closing wall-clock invalidates otherwise valid early slots',
       'criterion':'AC03.4; Stage1 sections8 and9 local starts, opening hours and absolute duration',
       'cases':['R008[America/New_York]','R008[Europe/Berlin]'],
       'reproduction':'Reset spring-transition date2030-03-10 NewYork or2030-03-31 Berlin, open00:00/close02:30, grid30/duration60; GET availability.',
       'expected':'200 with early slots00:00 and00:30; early valid booking remains possible, late booking ending beyond local close refused.',
       'observed':'422 for entire transition day; ordinary-date control200. Original test stops before early/late booking assertions.',
       'evidence':[common]},
      {'id':'V-S1-003','title':'Wrong-type reset reservations can replace state',
       'criterion':'AC03.1,AC03.6; Stage1 section5 wrong JSON type400 and atomic reset',
       'cases':['D116-reset-null','D116-reset-bool','D116-reset-number','D116-reset-empty-string','D116-reset-object'],
       'reproduction':'Seed/login, export destination; reset same fixture with reservations:null,true,42,"",{} instead of array; export and use old token.',
       'expected':'400 malformed_request and unchanged destination/old token.',
       'observed':'null,true,42 return422, preserve state/token200. Empty string/object return204, change exact export and revoke old token401. Nonempty string control returns400 unchanged.',
       'evidence':[find('-derived-8958251-'),confirmation]},
      {'id':'V-S1-004','title':'Opaque numeric snapshots lose exact receipt values through ordinary JSON clients',
       'criterion':'AC03.6,AC03.8; Stage1 section10 portable exact original receipts; frozen U003-U005',
       'cases':['U003','U004','U005'],
       'reproduction':'Create receipt with ignored numeric field1e400,1e-400 or1.0000000000000000000000000000001; export via ordinary response.json(); serialize and import unchanged object into fresh destination.',
       'expected':'Portable opaque JSON state preserves exact original request and imports204; original retry remains200.',
       'observed':'U003 cannot serialize float infinity before import (ValueError, counted frozen FAIL). U004/U005 round on client and destination returns422 checksum mismatch. Exact raw-byte numeric lifetimes separately pass.',
       'evidence':[upgrade]},
      {'id':'V-S1-005','title':'Checksum-valid inconsistent receipt semantics import successfully',
       'criterion':'AC03.6; Stage1 sections7,10,11 invalid state, original request/response correspondence and ordered batch receipt',
       'cases':['D116-receipt-party','D116-receipt-start','D116-receipt-end','D116-receipt-body','D116-batch-order'],
       'reproduction':'After valid control export/import, alter receipt responseparty2->3, start offset instant18->19 while local stays18, end19->18, bodyparty2->3, or reverse batch responses. Recompute sha256 of compact sorted ASCII payload; import.',
       'expected':'422 validation_failed and exact destination nonmutation for each semantic inconsistency.',
       'observed':'All five return204 and change destination. Independent adapter control checksum equals exported checksum and unchanged control imports204; this is not a selector mismatch.',
       'evidence':[semantics]}
    ]
    for defect in defects:defect.update(status='OPEN',product_sha=SHA,owner='Builder')
    ledger={'room':'e04c2728-8535-41c8-be50-88eb8068fa09','status':'REJECT','product_revision':SHA,
            'application_command_attempts':len(attempts),'defects':defects,
            'oracle_notes':[{'id':'ORACLE-EMAIL-001','cases':['S064','S065','S066','S067'],
              'criterion':'Stage1 section6 explicitly requires422 validation_failed for malformed email, including login.',
              'original_outcome':'4FAIL: unchanged original expects401','adjudicated_outcome':'4PASS:422 plus exact nonmutation',
              'counting':'Same four definitions; original raw failures remain unchanged.',
              'evidence':[find('-original-'),find('-adjudicated-')]},
              {'id':'ADAPTER-RECEIPT-001','cases':['B003'],'status':'ORIGINAL_SELECTOR_APPLICABLE_PASS',
               'additional_adapter':'qa/derived/test_snapshot_semantics.py recomputes checksum for five stronger semantic checks; no frozen source changed.'}]}
    (ROOT/'reports/defects.json').write_text(json.dumps(ledger,indent=2)+'\n')
    starts=[datetime.fromisoformat(a['started_at']) for a in attempts]
    ends=[datetime.fromisoformat(a['ended_at']) for a in attempts]
    review={'decision':'REJECT','product_sha':SHA,'stage':1,'room':ledger['room'],
      'evidence_revision':'Full Git commit SHA containing this report is delivered separately after commit; avoids self-reference.',
      'attempts':attempts,'frozen_applicable_distinct_definitions':len(frozen),
      'frozen_latest_adjudicated_outcomes':dict(Counter(frozen.values())),
      'derived_distinct_definitions':len(derived),'derived_latest_outcomes':dict(Counter(derived.values())),
      'pytest_case_executions_with_repeats':sum(a['case_executions'] for a in attempts),
      'pytest_raw_execution_outcomes':dict(Counter(o['outcome'] for values in cases.values() for o in values)),
      'official_stage1':{'definitions':120,'executed':120,'pass':120,'fail':0,'error':0,'skip':0},
      'official_stage2_probe':{'collected':25,'executed':1,'fail':1,'not_executed_after_failfast':24,'applicable_to_stage1':False},
      'developer_tests_separately_executed':{'definitions':14,'pass':14},
      'source_faults':{'control_operations':8,'control_operations_pass':8,'actual_injections':20,'pass':20,
                       'distinct_injected_names':['response_encode','candidate_encode','compression'],'http_requests':0},
      'producer_removal_integration':{'outcome':'PASS','edges_completed':[[1,1]],'remaining_edges':[[1,2],[1,3],[1,4],[2,2],[2,3],[2,4],[3,3],[3,4],[4,4]],
        'actual_removal_before_destination_start':True,'old_tokens_checked':2,'original_receipts_checked':2,'http_request_count':None,
        'limitations':'Standalone producer script did not instrument per-request count. Evidence proves ordinary-value case only, not failed numeric upgrades.'},
      'instrumented_httpx':metrics(all_http),'instrumented_load_httpx':metrics(load),
      'request_count_limitations':'HTTP metrics count instrumented pytest httpx only, including setup and repeated attempts. Official requests, health clients, source fault controls, standalone producer integration and raw sockets are not silently included.',
      'attempt_command_duration_sum_s':sum(a['duration_s'] for a in attempts),
      'execution_window_elapsed_s':(max(ends)-min(starts)).total_seconds(),
      'execution_window_start':min(starts).isoformat(),'execution_window_end':max(ends).isoformat(),
      'actual_model_usage_tokens':None,'actual_billing_usd':None,'usage_note':'Actual runtime billing/token meter not supplied to this verifier; unknown, not estimated invoice.',
      'defects':defects,'all_attempt_manifests_verified':True,
      'limits':'REJECT is supported by counterexamples. This is not an assertion of exhaustive Stage1 correctness or later-stage readiness; remaining broader matrix items need execution before ACCEPT.'}
    (OUT/'REVIEW-8958251.json').write_text(json.dumps(review,indent=2)+'\n')
    (OUT/'case-matrix-8958251.json').write_text(json.dumps({'product_sha':SHA,'decision':'REJECT','cases':list(catalog.values())},indent=2)+'\n')
    lines=['# Stage 1 independent decision: REJECT','',f'Product revision: `{SHA}`. Room: `{ledger["room"]}`.',
      '','Five observed contract defects prevent acceptance and advancement. The exact committed product was rebuilt independently from a clean standalone clone; no product edits were made by Verifier.',
      '','The full evidence commit SHA is sent in the native room decision after this report is committed. QA source revisions and source hashes appear in every attempt; the product revision above remains the review target.',
      '','## Executed evidence','',
      '| Suite | PASS | FAIL | Notes |','|---|---:|---:|---|',
      '| Official Stage1 isolated |120|0|Unchanged harness; clean exact-SHA checkout|',
      '| Original frozen baseline |100|4|S064-S067 oracle conflict, raw results retained|',
      '| Adjudicated same baseline |104|0|No additional definitions; only four expectations corrected plus nonmutation|',
      '| Common frozen |40|4|R002/R003 slow streams; two R008 DST closing cases|',
      '| Numeric original Stage1 |12|0|Unchanged assertions including R2N002 full receive/decompression/parse lifetime|',
      '| Upgrade1 to1 |3|3|U003 overflow serialization; U004 underflow and U005 precision import|',
      '| Derived initial |33|5|Reset type cases|',
      '| Derived confirmation rerun |33|7|Same38 plus two raw actual-EOF probes; repeat requests are not new definitions|',
      '| Derived snapshot semantics |0|5|Checksum adapter control204, corrupt semantic state accepted204|',
      '| Developer checks, independently rerun unchanged |14|0|Separate from independent definitions|',
      '| Source publication injections |20|0|8 control operations, 3 actual injected names; zero HTTP requests|',
      '| Actual source removal integration |1|0|Producer removed before fresh destination start; ordinary data only|',
      '',f'Frozen Stage1 has **166 applicable distinct definitions**: latest corrected-oracle outcomes159PASS/7FAIL. Independent derived tests add45 distinct definitions:33PASS/12FAIL. There are{review["pytest_case_executions_with_repeats"]} recorded pytest case executions across repeated original/adjudicated/derived attempts, with raw{review["pytest_raw_execution_outcomes"]}. No ERROR or SKIP was converted to PASS.',
      '','The official next-stage probe collected25 definitions, executed one failing check, then stopped; the other24 were not executed. This is outside Stage1 applicability and does not establish any Stage2 implementation.',
      '','## Open defects','']
    for d in defects:
        lines += [f'### {d["id"]}: {d["title"]}','',f'Criterion: {d["criterion"]}.',
                  '',f'Reproduce: {d["reproduction"]}',f'Expected: {d["expected"]}',f'Observed: {d["observed"]}',
                  '', 'Evidence: '+', '.join(f'[{Path(p).name}](../../{p})' for p in d['evidence'])+'.','']
    lines += ['## Environment, timing and counts','',
      'All supplemental Docker services used2CPU/2GiB, read-only root, tmpfs and an internal network. Clients had no added memory cap; heavy runs were sequential. Every owned container and network was removed with captured logs. Image/container/network inspections, health measurements and exact commands are in each attempt. Service images remain labelled verifier-owned for reproducibility.',
      '',f'Instrumented pytest HTTP requests: **{len(all_http)}**. Measured load subset: **{len(load)}**, p50={metrics(load)["p50_s"]:.6f}s, p95={metrics(load)["p95_s"]:.6f}s, max={metrics(load)["max_s"]:.6f}s; maximum measured concurrency={metrics(load)["max_observed_inflight"]}. These include repeats and setup; they do not increase test definitions. All suites retain their own request percentiles and atomicity assertions.',
      '',f'Application command attempts:{len(attempts)}; sum of command durations={review["attempt_command_duration_sum_s"]:.3f}s. Elapsed execution window={review["execution_window_elapsed_s"]:.3f}s ({review["execution_window_start"]} to {review["execution_window_end"]}), including analysis gaps. Local source fault/developer checks overlapped; Docker suites did not.',
      '','Actual token usage and billing are unknown. No price estimate is presented as an invoice.',
      '','The raw-byte numeric lifetime passed on Stage1. The huge pair sum1e100000000+4 becomes applicable in Stage2; no claim is made for it yet. U003-U005 failures use ordinary JSON object portability, a different boundary. Raw-wire probes and standalone producer-removal calls are reported separately because the HTTP instrumentation does not cover them.',
      '','## Evidence inventory and next gate','',
      'All original attempt manifests were rehashed with zero mismatches. `REVIEW-8958251.json` holds counts, timings, manifest hashes and QA revisions. `case-matrix-8958251.json` preserves each definition and every raw execution outcome, including unchanged oracle failures and repeated tests. `../defects.json` tracks all five open families. `../../qa/COVERAGE.md` retains the complete specification matrix.',
      '','Builder must repair Stage1 and supply a new full-SHA review handoff. Rebuild that exact revision and rerun every applicable frozen test and every previous counterexample, adapting opaque selectors explicitly if representation changes. Later-stage gates, remaining upgrade edges, final all-stage clean delivery, final docs and genuine room export remain pending. Coordinator alone reconciles advancement.']
    (OUT/'REVIEW-8958251.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:review[k] for k in ['decision','product_sha','frozen_applicable_distinct_definitions','frozen_latest_adjudicated_outcomes','derived_distinct_definitions','derived_latest_outcomes','pytest_case_executions_with_repeats','pytest_raw_execution_outcomes','instrumented_httpx','instrumented_load_httpx','attempt_command_duration_sum_s','execution_window_elapsed_s']},indent=2))


if __name__=='__main__':main()
