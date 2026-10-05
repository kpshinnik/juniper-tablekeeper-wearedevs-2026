"""Build a new immutable exact-SHA evidence inventory with explicit aliases.

This aggregates executed evidence; the supplied decision remains a human-readable
Verifier judgment, never an automatic inference from an aggregate pass count.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from summarize import metrics, read_rows

ROOT=Path(__file__).resolve().parent.parent
FREEZE=ROOT.parent.parent/'factory/final-inputs/20261005T061628Z'
MANIFEST='91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(node):
    node=node.replace('baseline-adjudicated/','baseline-original/')
    if node.startswith('adapters/test_stage4_payload.py'):
        target=('frozen/supplemental/test_boundaries.py' if '::test_B003' in node else
                'derived/test_snapshot_semantics.py' if '::test_D116' in node else
                'derived/test_additional_stage1.py' if '::test_D121' in node else
                'derived/test_stage3_integrity.py')
        return node.replace('adapters/test_stage4_payload.py',target)
    if node.startswith('adapters/test_string_payload.py::test_B003'):
        node=node.replace('adapters/test_string_payload.py','frozen/supplemental/test_boundaries.py')
    elif node.startswith('adapters/test_string_payload.py::test_D116'):
        node=node.replace('adapters/test_string_payload.py','derived/test_snapshot_semantics.py')
    return node


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--product-sha',required=True)
    p.add_argument('--checkout',type=Path,required=True)
    p.add_argument('--decision',choices=['ACCEPT','REJECT'],required=True)
    p.add_argument('--derived-definitions',type=int,required=True)
    p.add_argument('--stage',type=int,choices=[1,2,3,4],default=1)
    p.add_argument('--open-defect',action='append',default=[])
    a=p.parse_args();out=ROOT/f'reports/stage-{a.stage}';short=a.product_sha[:7]
    attempts=[];observations=defaultdict(list);http=[];load=[];raw=[];source=[];deployment=[];producers=[];developer=[];formatter=[];parses=[]
    for folder in sorted(out.glob('*'+short+'*')):
        if not folder.is_dir() or not (folder/'attempt.json').exists():continue
        initial=json.loads((folder/'attempt.json').read_text())
        if initial['kind']!='APPLICATION':continue
        assert (folder/'result.json').exists(),('Unfinished attempt',folder)
        result=json.loads((folder/'result.json').read_text())
        assert result['product_sha']==a.product_sha
        manifest=json.loads((folder/'manifest.sha256.json').read_text())
        assert all(digest(folder/name)==value for name,value in manifest.items()),folder
        rows=read_rows(folder/'cases.jsonl');requests=read_rows(folder/'http-requests.jsonl')
        parses.extend(dict(r,attempt=str(folder.relative_to(ROOT))) for r in read_rows(folder/'json-parse.jsonl'))
        http+=requests;load+=[r for r in requests if 'test_load.py' in (r.get('case') or '')]
        rel=str(folder.relative_to(ROOT))
        entry={'path':rel,'manifest_sha256':digest(folder/'manifest.sha256.json'),
               'duration_s':result['duration_s'],'started_at':result['started_at'],'ended_at':result['ended_at'],
               'qa_sha':result['qa_sha'],'returncode':result['returncode'],'command_outcome':result['command_outcome'],
               'raw_case_outcomes':dict(Counter(r['outcome'] for r in rows)),'httpx':metrics(requests),
               'manifest_verified':True}
        qa_files={x for x in result['command'] if x.startswith('qa/') and x.endswith('.py')}
        if 'qa/run_upgrade.py' in qa_files:
            qa_files.add('qa/producer_stage4.py' if 'stage4-authenticity' in result['command'] else
                         'qa/producer_stage3.py' if 'stage3-authenticity' in result['command'] else
                         'qa/producer_historical.py' if 'historical' in result['command'] else 'qa/producer_removal.py')
        if 'qa/run_stage3_integrity.py' in qa_files:
            qa_files.add('qa/run_suite.py')
        entry['qa_source_sha256_at_recorded_revision']={name:hashlib.sha256(subprocess.check_output(
            ['git','-C',str(ROOT),'show',result['qa_sha']+':'+name])).hexdigest() for name in sorted(qa_files)}
        tests_log=(folder/'tests.log').read_text() if (folder/'tests.log').exists() else ''
        if 'import file mismatch:' in tests_log and result['returncode']==2:
            entry['adjudication']='PRESERVED_QA_MODULE_NAME_COLLISION_BEFORE_CASE_EXECUTION'
        if 'upgrade checks require the preceding stage:' in tests_log:
            entry['adjudication']='PRESERVED_QA_PREVIOUS_SERVICE_SETUP_ERROR'
        for row in rows:
            item=dict(row,attempt=rel,definition=canonical(row['id']),reconciliation='APPLICATION_RESULT')
            if not item.get('description'):item['description']=row['id'].split('::')[-1].replace('_',' ')
            if row['outcome']=='FAIL':
                if 'baseline-original/test_security.py' in row['id'] and re.search(r'\[S06[4-7]-',row['id']):
                    item['reconciliation']='ORACLE_CONFLICT_RETAINED'
                elif row['id'].startswith('derived/test_snapshot_semantics.py') or row['id']=='frozen/supplemental/test_boundaries.py::test_B003_cross_owner_receipt_rejected':
                    item['reconciliation']='OPAQUE_SELECTOR_MISMATCH_RETAINED'
                elif (a.stage == 3 and short == '0c0a386' and
                      folder.name == '20261005T103104.209999Z-stage2-browser-0c0a386-d4f15256' and
                      'test_D215_routes_labels_keyboard_layout_and_untrusted_text' in row['id'] and
                      'is interrupted by another navigation' in tests_log):
                    item['reconciliation']='QA_LOGIN_NAVIGATION_RACE_RETAINED'
                    item['correction']='a534f9c: wait for the product login redirect instead of issuing a competing goto; product and case assertions unchanged. Fresh synchronized attempt separately recorded.'
                else:item['reconciliation']='OPEN_PRODUCT_DEFECT'
            if row['id'].startswith('adapters/') and row['outcome']=='PASS':
                item['reconciliation']='SEPARATE_REPRESENTATION_ADAPTER'
            if (a.product_sha=='25ade1c7add9a5701a511e07f79a619a3cb21b51'
                    and row['outcome']=='FAIL'):
                # Bound to this run's inspected original traces. The matching
                # adapter observations must still exist and pass below.
                schema3_selector = (
                    folder.name=='20261005T145600.257473Z-stage3-integrity-25ade1c-74b0e78c'
                    and row['id'].startswith('derived/test_stage3_integrity.py::')
                    and row['test_sha256']=='43b1fb2256b8e383c9e1f90383c2fd9327fe610794bee31c1a43b2c542e8b7ee'
                    and "KeyError: 'schema'" in row['observed'])
                state_selector = (
                    folder.name=='20261005T145814.406048Z-additional-stage1-25ade1c-13a9b072'
                    and row['id'].startswith('derived/test_additional_stage1.py::test_D121')
                    and row['test_sha256']=='b5026a9d100d4581258482360a1b549a985ec3c81050247225b8769d1eb86699'
                    and "KeyError: 'reservations'" in row['observed'])
                if schema3_selector or state_selector:
                    item['reconciliation']='OPAQUE_SELECTOR_MISMATCH_RETAINED'
                    item['correction']='Inspected original selector fails before semantic mutation on schema4 carrier. Separate unchanged assertions through adapters/test_stage4_payload.py passed in 20261005T145755.475202Z-stage4-snapshot-adapted-25ade1c-9414a638; zero new definitions.'
            if (a.product_sha=='e538cd16bbd96d4206d89f17a67791e759c00823' and row['outcome']=='FAIL'):
                if ((folder.name=='20261005T122452.950405Z-snapshot-adapted-e538cd1-0dd7a74b'
                     and row['id'].startswith('adapters/test_string_payload.py::test_D116') and "KeyError: 'receipts'" in tests_log)
                    or (folder.name=='20261005T122455.983995Z-stage3-integrity-e538cd1-fab33904'
                        and row['id'].startswith('derived/test_stage3_integrity.py') and "KeyError: 'schema'" in tests_log)
                    or (folder.name=='20261005T123600.277176Z-additional-stage1-e538cd1-f7acbbd4'
                        and row['id'].startswith('derived/test_additional_stage1.py::test_D121') and "KeyError: 'reservations'" in tests_log)):
                    item['reconciliation']='OPAQUE_SELECTOR_MISMATCH_RETAINED'
                    item['correction']='Separate explicit schema4 value/wide_values carrier adapter; original assertions and raw failures retained.'
                if (folder.name=='20261005T122505.057246Z-stage4-domain-e538cd1-9dba16a4' and
                    row['id']=='derived/test_stage4.py::test_D404_noops_replays_preview_and_other_restaurant_do_not_stale'):
                    item['reconciliation']='QA_WRONG_RESTAURANT_URL_RETAINED'
                    item['correction']='Original helper applies the other-r plan to /restaurants/r, correctly receiving404; corrected call explicitly supplies rid=other-r. Assertions unchanged.'
            if (row['outcome']=='ERROR' and row['id'].endswith('::test_preceding_stage_accounts_survive_import')
                    and 'upgrade checks require the preceding stage:' in tests_log):
                item['reconciliation']='QA_SETUP_ERROR_RETAINED'
            observations[item['definition']].append(item);raw.append(item)
        entry['official_harness_counts']={str(f.relative_to(folder/'official')):json.loads(f.read_text()) for f in sorted((folder/'official').rglob('stage-*.counts.json'))}
        if (folder/'source-faults.jsonl').exists():
            injected=read_rows(folder/'source-faults.jsonl')
            try:
                summary=json.loads((folder/'command.log').read_text().splitlines()[-1])
            except json.JSONDecodeError:
                assert folder.name=='20261005T124236.523737Z-source-faults-e538cd1-928cbdd7'
                assert "TypeError: object of type 'PreparedBody' has no len()" in (folder/'command.log').read_text()
                summary={'control_operations_defined':None,'control_operations_executed':[]}
                entry['adjudication']='PRESERVED_SOURCE_QA_PREPARED_BODY_DECODE_ERROR_AFTER_38_REAL_INJECTIONS'
                entry['correction']='Read small prepared response blocks before decoding the plan in QA setup; separate complete50 injection attempt required.'
            assert all(r['actually_triggered']==[r['fault']] for r in injected)
            source.append({'attempt':rel,'defined_operation_names':summary['control_operations_defined'],
                'executed_control_operation_names':[r['operation'] for r in summary['control_operations_executed']],
                'actually_injected_operation_names':sorted({r['operation'] for r in injected}),
                'fault_point_types':sorted({r['fault'] for r in injected}),
                'injection_executions':len(injected),'outcomes':dict(Counter(r['outcome'] for r in injected)),
                'reset_actual_injection':[r for r in injected if r['operation']=='reset'],'http_requests':0})
        if '-unchanged-developer-' in folder.name:
            log=(folder/'command.log').read_text()
            count=int(re.search(r'Ran (\d+) tests',log)[1])
            developer.append({'attempt':rel,'executed_methods':count,'outcome':'PASS' if result['returncode']==0 else 'FAIL'})
        if result['returncode']==2 and 'deployment_probe.py: error: unrecognized arguments: --stage 1' in (folder/'command.log').read_text():
            entry['adjudication']='PRESERVED_QA_INVOCATION_ERROR_BEFORE_APPLICATION_EXECUTION'
            entry['application_requests_executed']=0
            entry['correction']='New deployment-corrected attempt; original error/log/hash retained.'
        if (folder/'deployment.jsonl').exists():
            deployment.extend(dict(r,attempt=rel) for r in read_rows(folder/'deployment.jsonl'))
        if (folder/'formatter-boundaries.jsonl').exists():
            formatter.extend(dict(r,attempt=rel) for r in read_rows(folder/'formatter-boundaries.jsonl'))
        if (folder/'producer-removal-proof.json').exists():
            env=json.loads((folder/'environment.json').read_text())
            proof=json.loads((folder/'producer-removal-proof.json').read_text())
            consumer=json.loads((folder/'consumer.log').read_text().splitlines()[-1])
            assert proof['removed'] and proof['destination_not_started_yet'] and proof['post_removal_inspect_returncode']!=0
            producers.append({'attempt':rel,'source_sha':env['source_sha'],'destination_sha':env['destination_sha'],
                              'proof':proof,'consumer':consumer,'http_request_count':None})
        attempts.append(entry)
    definitions=[]
    for key,items in sorted(observations.items()):
        effective=[r for r in items if r['reconciliation'] not in ('ORACLE_CONFLICT_RETAINED','OPAQUE_SELECTOR_MISMATCH_RETAINED','QA_SETUP_ERROR_RETAINED','QA_LOGIN_NAVIGATION_RACE_RETAINED','QA_WRONG_RESTAURANT_URL_RETAINED')]
        assert effective,('Unreconciled oracle/selector',key)
        # Never let a later pass silently erase a real failure within one review.
        priority={'PASS':0,'SKIP':1,'FAIL':2,'ERROR':3}
        outcome=max((r['outcome'] for r in effective),key=priority.get)
        definitions.append({'id':key,'effective_outcome':outcome,'observations':items})
    groups={name:[r for r in definitions if r['id'].startswith(prefix)] for name,prefix in
            [('frozen','frozen/'),('derived','derived/'),('official','official/')]}
    expected_frozen={1:166,2:169,3:179,4:216}[a.stage]
    expected_official={1:120,2:145,3:152,4:158}[a.stage]
    assert len(groups['frozen'])==expected_frozen,(len(groups['frozen']),expected_frozen)
    assert len(groups['derived'])==a.derived_definitions,len(groups['derived'])
    assert len(groups['official'])==expected_official,(len(groups['official']),expected_official)
    if a.decision=='ACCEPT':
        assert not a.open_defect and all(r['effective_outcome']=='PASS' for r in definitions)
        assert all(x['command_outcome']=='EXITED' for x in attempts)
    frozen=json.loads((ROOT/'qa/frozen/manifest.json').read_text())
    assert digest(ROOT/'qa/frozen/manifest.json')==digest(FREEZE/'manifest.json')==MANIFEST
    checks=[]
    for path,info in frozen['files'].items():
        assert digest(ROOT/'qa/frozen'/path)==digest(FREEZE/path)==info['sha256'],path
        checks.append({'path':path,'sha256':info['sha256'],'original_and_copy_match':True})
    status=subprocess.check_output(['git','-C',str(a.checkout),'status','--porcelain'],text=True)
    assert not status
    assert subprocess.check_output(['git','-C',str(a.checkout),'rev-parse','HEAD'],text=True).strip()==a.product_sha
    starts=[datetime.fromisoformat(r['started_at']) for r in attempts];ends=[datetime.fromisoformat(r['ended_at']) for r in attempts]
    review={'product_sha':a.product_sha,'decision':a.decision,'open_defects':a.open_defect,'stage':a.stage,
        'room':'e04c2728-8535-41c8-be50-88eb8068fa09','checkout':str(a.checkout),'clean_checkout_status':status,
        'evidence_revision':'Delivered after committing this report; avoids self-reference.',
        'attempts':attempts,'application_command_attempts':len(attempts),
        'raw_pytest_executions':len(raw),'raw_pytest_outcomes':dict(Counter(r['outcome'] for r in raw)),
        'raw_fail_classification':dict(Counter(r['reconciliation'] for r in raw if r['outcome']=='FAIL')),
        'raw_nonpass_classification':dict(Counter(r['reconciliation'] for r in raw if r['outcome']!='PASS')),
        'reconciled_definitions':{k:{'count':len(v),'outcomes':dict(Counter(r['effective_outcome'] for r in v))} for k,v in groups.items()},
        'source_fault_experiments':source,'source_formatter_experiments':formatter,'developer_checks':developer,'deployment_configurations':deployment,
        'actual_producer_removal_executions':producers,'producer_removal_distinct_integration_definitions':len({x['consumer']['id'] for x in producers}),
        'instrumented_httpx':metrics(http),'instrumented_load_httpx':metrics(load),
        'complete_json_parse_observations':parses,
        'json_parse_limits':'Original full json.loads decoder and assertions are retained. Observations are supplemental; absence after an earlier assertion/timeout/OOM is not a parse PASS. Received/decompressed bytes and HTTP timing are separate. No client memory cap was added.',
        'frozen_manifest_sha256':MANIFEST,'frozen_rehashed_files':checks,'all_attempt_manifests_verified':True,
        'command_duration_sum_s':sum(r['duration_s'] for r in attempts),
        'execution_window_start':min(starts).isoformat(),'execution_window_end':max(ends).isoformat(),
        'execution_window_elapsed_s':(max(ends)-min(starts)).total_seconds(),'actual_tokens':None,'actual_billing_usd':None,
        'count_limits':'HTTP metrics count instrumented pytest httpx including setup and repeats; exclude raw sockets, standalone producer/deployment clients, source injections and unchanged official harness. Uninstrumented HTTP totals are unknown.',
        'format_correction':'D117 stopped_dripping_after_s is the planned upper limit; actual EOF/send-stop observations are in recorded events. Source operation names and fault-point types are separate fields.'}
    for path,value in [(out/('REVIEW-'+short+'.json'),review),
                       (out/('case-matrix-'+short+'.json'),{'product_sha':a.product_sha,'decision':a.decision,'definitions':definitions})]:
        with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({k:review[k] for k in ['product_sha','decision','application_command_attempts','raw_pytest_executions','raw_pytest_outcomes','raw_fail_classification','reconciled_definitions','instrumented_httpx','instrumented_load_httpx','command_duration_sum_s','execution_window_elapsed_s']},indent=2))


if __name__=='__main__':main()
