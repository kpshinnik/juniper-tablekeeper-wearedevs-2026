"""Read-only fresh-room evidence accounting; never executes product or tests.

One primary case JSONL per attempt is counted. JUnit, frozen logs and harness
copies are linked separately, not added to that count. Every refresh is new.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from reconcile_candidate import canonical
from summarize import metrics

ROOT = Path(__file__).resolve().parent.parent
ROOM = 'e04c2728-8535-41c8-be50-88eb8068fa09'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def read(path):
    return json.loads(path.read_text())


def rows(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def ref(path):
    return {'path': relative(path), 'sha256': digest(path), 'bytes': path.stat().st_size}


def walk(root, excluded):
    for parent, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('source', 'archive', '__pycache__')
                   and not any((Path(parent)/d).resolve().is_relative_to(x) for x in excluded)]
        yield Path(parent), files


def lane(meta):
    text = ' '.join(meta.get('command', []))
    if '--collect-only' in text:
        return 'COLLECTION_NOT_APPLICATION'
    if 'selfcheck' in text:
        return 'ORACLE_SELFCHECK_NOT_APPLICATION'
    if 'harness check' in text or 'check_concrete_delivery.py' in text:
        return 'PACKAGING'
    if 'harness run' in text:
        return 'OFFICIAL_ISOLATED'
    if 'fault_publication.py' in text:
        return 'SOURCE_INJECTION_NOT_HTTP'
    if 'formatter_boundary_probe.py' in text:
        return 'SOURCE_FORMATTER_NOT_HTTP'
    if 'unittest' in text or 'run_developer.py' in text:
        return 'DEVELOPER_CHECKS'
    if 'deployment_probe.py' in text:
        return 'DEPLOYMENT'
    if 'run_upgrade.py' in text:
        return 'TRANSFER_HTTP_BROWSER_PRODUCER_REMOVAL'
    if meta.get('kind') == 'APPLICATION':
        return 'APPLICATION_HTTP_BROWSER'
    return meta.get('kind', 'UNKNOWN') + '_NOT_APPLICATION'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--final-product-sha')
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(ROOT/'reports') and not out.exists()
    out.mkdir(parents=True)
    own_attempt = Path(os.environ.get('QA_EVIDENCE_DIR', str(out))).resolve()
    excluded = [out, own_attempt]
    started = datetime.now(timezone.utc).isoformat()
    notes = []
    dispositions = defaultdict(list)
    review_records = []
    for stage in range(1, 5):
        base = ROOT/f'reports/stage-{stage}'
        for path in sorted(base.glob('case-matrix-*.json')):
            data = read(path)
            for definition in data.get('definitions', []):
                for item in definition.get('observations', []):
                    key = (item.get('attempt'), item.get('id'))
                    dispositions[key].append({'classification': item.get('reconciliation'),
                        'raw_outcome': item.get('outcome'), 'evidence': relative(path),
                        'definition': definition['id']})
            # The first review used an earlier ledger shape. Its explicit
            # REJECT and malformed-email oracle adjudication stay historical.
            if data.get('product_sha', '').startswith('8958251'):
                for definition in data.get('cases', []):
                    for item in definition.get('observations_at_product_sha', []):
                        node = item['variant']
                        oracle = 'baseline-original/test_security.py' in node and re.search(r'\[S06[4-7]-',node)
                        classification = ('ORACLE_CONFLICT_RETAINED' if oracle else
                            'HISTORICAL_PRODUCT_FAILURE_RETAINED' if item['outcome'] != 'PASS' else 'APPLICATION_RESULT')
                        dispositions[(item['attempt'],node)].append({'classification':classification,
                            'raw_outcome':item['outcome'],'evidence':relative(path),'definition':canonical(node)})
        for path in sorted(base.glob('REVIEW-*.json')):
            data = read(path)
            review_records.append({**ref(path), 'stage': stage, 'product_sha': data.get('product_sha'),
                'recorded_decision': data.get('decision'),
                'recorded_raw_pytest_executions': data.get('raw_pytest_executions',data.get('raw_pytest_case_executions',data.get('pytest_case_executions_with_repeats'))),
                'recorded_raw_pytest_outcomes': data.get('raw_pytest_outcomes',data.get('raw_outcomes',data.get('pytest_raw_execution_outcomes'))),
                'recorded_reconciled_definitions': data.get('reconciled_definitions'),
                'recorded_application_attempts': data.get('application_command_attempts'),
                'note': 'Original report scope; later addenda are separately indexed. Historical acceptance may have been reopened.'})
            if data.get('product_sha', '').startswith('e5e6305'):
                for item in data.get('cases', []):
                    node = item['id']
                    oracle = 'baseline-original/test_security.py' in node and re.search(r'\[S06[4-7]-',node)
                    selector = (node.startswith('derived/test_snapshot_semantics.py') or
                        node == 'frozen/supplemental/test_boundaries.py::test_B003_cross_owner_receipt_rejected')
                    classification = ('APPLICATION_RESULT' if item['outcome'] == 'PASS' else
                        'ORACLE_CONFLICT_RETAINED' if oracle else 'OPAQUE_SELECTOR_MISMATCH_RETAINED' if selector else
                        'HISTORICAL_PRODUCT_FAILURE_RETAINED')
                    dispositions[(item['attempt'],node)].append({'classification':classification,
                        'raw_outcome':item['outcome'],'evidence':relative(path),'definition':canonical(node)})
        for path in sorted(base.glob('ADDENDUM-*.json')):
            data = read(path)
            attempt = data.get('primary_attempt') or data.get('new_evidence',{}).get('attempt')
            if attempt and data.get('defect') in ('V-S2-002','V-S2-003'):
                for item in rows(ROOT/attempt/'cases.jsonl'):
                    if item['outcome'] != 'PASS':
                        dispositions[(attempt,item['id'])].append({'classification':'HISTORICAL_PRODUCT_FAILURE_RETAINED',
                            'raw_outcome':item['outcome'],'evidence':relative(path),'definition':canonical(item['id']),
                            'defect':data['defect']})
    collision_path = ROOT/'reports/stage-4/ENCODING-COLLISION-e538cd1.json'
    if collision_path.exists():
        data = read(collision_path)
        for attempt in data.get('attempts', []):
            if attempt.get('classification') == 'QA_CODEC_FAILURE':
                for item in rows(ROOT/attempt['path']/'cases.jsonl'):
                    dispositions[(attempt['path'], item['id'])].append({
                        'classification': 'QA_CODEC_FAILURE_RETAINED', 'raw_outcome': item['outcome'],
                        'evidence': relative(collision_path), 'definition': canonical(item['id'])})

    folders = []
    for parent, files in walk(ROOT/'reports', excluded):
        if 'attempt.json' in files:
            folders.append(parent)
    folders.sort()
    seen_execution = {}
    attempts, case_rows, fault_rows, independent_lanes = [], [], [], []
    aggregate = defaultdict(lambda: {'attempts': 0, 'raw': Counter(), 'definitions': set(),
        'invocations': 0, 'invocation_outcomes': Counter(), 'source_versions': defaultdict(set),
        'requests': [], 'load_requests': [], 'security_load_definitions': set(), 'nonpass': Counter()})
    kind_counts, lane_counts = Counter(), Counter()
    reference_mismatches = []
    priority = {'PASS': 0, 'SKIP': 1, 'FAIL': 2, 'ERROR': 3}
    for folder in folders:
        initial = read(folder/'attempt.json')
        result = read(folder/'result.json') if (folder/'result.json').exists() else None
        meta = result or initial
        if meta.get('room') != ROOM:
            notes.append({'path': relative(folder), 'issue': 'Room identity is missing or different; excluded from aggregate'})
            continue
        execution_key = hashlib.sha256(json.dumps({k:initial.get(k) for k in
            ('room','product_sha','qa_sha','started_at','command','cwd')},sort_keys=True).encode()).hexdigest()
        duplicate_of = seen_execution.get(execution_key)
        seen_execution.setdefault(execution_key, relative(folder))
        manifest = read(folder/'manifest.sha256.json') if (folder/'manifest.sha256.json').exists() else {}
        refs = {}
        names = ['attempt.json','result.json','manifest.sha256.json','catalog.jsonl','cases.jsonl','junit.xml',
                 'session.jsonl','environment.json','command.log','tests.log','frozen-case-log.jsonl',
                 'http-requests.jsonl','wire-requests.jsonl','source-faults.jsonl','formatter-boundaries.jsonl',
                 'deployment.jsonl','producer-removal-proof.json','consumer.log','client-after.json',
                 'service-before.json','service-after.json','json-parse.jsonl']
        for name in names:
            path = folder/name
            if path.exists():
                refs[name] = ref(path)
                expected = manifest.get(name)
                if expected and expected != refs[name]['sha256']:
                    reference_mismatches.append({'path':relative(path),'manifest':expected,'actual':refs[name]['sha256']})
        env = read(folder/'environment.json') if (folder/'environment.json').exists() else {}
        sessions = rows(folder/'session.jsonl')
        catalog = rows(folder/'catalog.jsonl')
        raw = rows(folder/'cases.jsonl')
        kind = meta.get('kind', 'UNKNOWN')
        category = lane(meta)
        row = {'path': relative(folder), 'execution_identity': execution_key, 'duplicate_of': duplicate_of,
            'kind': kind, 'lane': category, 'product_sha': meta.get('product_sha'), 'test_revision': meta.get('qa_sha'),
            'stage': meta.get('stage'), 'started_at': meta.get('started_at'), 'ended_at': meta.get('ended_at'),
            'duration_s': meta.get('duration_s'), 'command_outcome': meta.get('command_outcome', 'INCOMPLETE'),
            'returncode': meta.get('returncode'), 'command': meta.get('command'), 'cwd': meta.get('cwd'),
            'environment': {'python': meta.get('python'), 'platform': meta.get('platform'),
                'service_limits': env.get('service_limits'), 'client_memory_cap': env.get('client_memory_cap'),
                'client_memory_cap_added': meta.get('client_memory_cap_added'), 'session_records': sessions},
            'artifacts': refs, 'manifest_declared_artifacts': len(manifest),
            'manifest_audit_scope': 'Primary referenced files rehashed. Other artifacts retain their original manifest and review audits; no new full-history byte audit claimed.',
            'case_result_rows': len(raw), 'raw_outcomes': dict(Counter(r['outcome'] for r in raw)),
            'catalog_count_not_execution': len(catalog), 'case_source_hashes': {},
            'result_complete': result is not None, 'oom_observations': [],
            'prior_adjudications': [], 'fresh_acceptance_inferred': False}
        product_short = (meta.get('product_sha') or '')[:7]
        row['product_source_bindings'] = [ref(path) for pattern in
            (f'provenance-{product_short}.json',f'SOURCE-BINDING-{product_short}.json',f'INDEX-{product_short}.json')
            for path in (ROOT/f"reports/stage-{meta.get('stage')}").glob(pattern)] if product_short else []
        for item in catalog:
            row['case_source_hashes'].setdefault(item['id'].split('::')[0], set()).add(item['source_sha256'])
        for item in raw:
            row['case_source_hashes'].setdefault(item['id'].split('::')[0], set()).add(item.get('test_sha256'))
        row['case_source_hashes'] = {k:sorted(v for v in values if v) for k,values in row['case_source_hashes'].items()}
        for name in ('client-after.json','service-after.json'):
            if (folder/name).exists():
                objects = read(folder/name)
                if isinstance(objects, list):
                    row['oom_observations'] += [{'artifact':name,'oom_killed':obj.get('State',{}).get('OOMKilled'),
                        'exit_code':obj.get('State',{}).get('ExitCode')} for obj in objects if isinstance(obj,dict)]
        applied = kind == 'APPLICATION' and not duplicate_of
        key = (str(meta.get('stage')), meta.get('product_sha') or 'UNRECORDED')
        group = aggregate[key] if applied else None
        if applied:
            group['attempts'] += 1
        native_invocations = defaultdict(list)
        for index, item in enumerate(raw, 1):
            definition = canonical(item['id'])
            mapped = dispositions.get((relative(folder), item['id']), [])
            classified = [r['classification'] for r in mapped if r.get('classification')]
            if not classified and item['outcome'] != 'PASS':
                classified = ['RAW_UNCLASSIFIED_RETAINED']
            case_rows.append({'attempt': relative(folder), 'execution_identity': execution_key,
                'duplicate_of': duplicate_of, 'kind':kind, 'lane':category, 'stage':meta.get('stage'),
                'product_revision': item.get('product_revision', meta.get('product_sha')),
                'test_revision': meta.get('qa_sha'), 'test_sha256': item.get('test_sha256'),
                'stable_id':item['id'], 'canonical_definition':definition, 'phase':item.get('phase'),
                'outcome':item['outcome'], 'duration_s':item.get('duration_s'),
                'description': item.get('description') or item['id'],
                'expected':item.get('expected'), 'observed':item.get('observed'),
                'original_record':{**refs['cases.jsonl'],'line':index},
                'classification':classified, 'classification_evidence':mapped,
                'counted_as_application_result':applied})
            native_invocations[item['id']].append(item['outcome'])
            if applied:
                group['raw'][item['outcome']] += 1
                group['definitions'].add(definition)
                if item.get('test_sha256'):
                    group['source_versions'][definition].add(item['test_sha256'])
                if item['outcome'] != 'PASS':
                    group['nonpass'].update(classified)
                if '/baseline-' in item['id'] and any(x in item['id'] for x in ('test_security.py','test_load.py')):
                    group['security_load_definitions'].add(definition)
        row['case_invocations'] = len(native_invocations)
        row['invocation_outcomes'] = dict(Counter(max(v,key=lambda x:priority.get(x,4)) for v in native_invocations.values()))
        if applied:
            group['invocations'] += len(native_invocations)
            group['invocation_outcomes'].update(row['invocation_outcomes'])
        http = rows(folder/'http-requests.jsonl')
        row['instrumented_httpx'] = metrics(http)
        row['instrumented_raw_wire_rows'] = len(rows(folder/'wire-requests.jsonl'))
        if applied:
            group['requests'].extend(http)
            group['load_requests'].extend(r for r in http if 'test_load.py' in (r.get('case') or ''))
        injections = rows(folder/'source-faults.jsonl')
        assert all(item.get('actually_triggered') == [item.get('fault')] for item in injections), relative(folder)
        for index, item in enumerate(injections, 1):
            fault_rows.append({'attempt':relative(folder),'product_sha':meta.get('product_sha'),
                'qa_revision':meta.get('qa_sha'),'duplicate_of':duplicate_of,
                'original_record':{**refs['source-faults.jsonl'],'line':index}, **item})
        extra = {'attempt':relative(folder),'product_sha':meta.get('product_sha'),'test_revision':meta.get('qa_sha'),
                 'lane':category,'duplicate_of':duplicate_of,'source_injections':len(injections),
                 'actually_injected_operation_names':sorted({r['operation'] for r in injections if r.get('actually_triggered')}),
                 'fault_types':sorted({r['fault'] for r in injections if r.get('actually_triggered')}),
                 'source_outcomes':dict(Counter(r['outcome'] for r in injections)),
                 'control_summary':None,'developer_summary':None,'official_count_files':[]}
        log = (folder/'command.log').read_text(errors='replace') if (folder/'command.log').exists() else ''
        if injections:
            for line in reversed(log.splitlines()):
                try:
                    value = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(value,dict) and 'control_operations_defined' in value:
                    extra['control_summary'] = value
                    break
        if category == 'DEVELOPER_CHECKS':
            match = re.search(r'Ran (\d+) tests? in ([\d.]+)s',log)
            extra['developer_summary'] = {'methods':int(match[1]) if match else None,
                'duration_s':float(match[2]) if match else None,
                'result_line':next((line for line in reversed(log.splitlines()) if line.startswith(('FAILED (','OK','ERROR:','FAIL:'))),None),
                'raw_log':refs.get('command.log')}
        for subdir, files in walk(folder, []):
            for name in files:
                if name.endswith('.counts.json'):
                    path = subdir/name
                    extra['official_count_files'].append({**ref(path),'counts':read(path)})
        if category not in ('APPLICATION_HTTP_BROWSER','TRANSFER_HTTP_BROWSER_PRODUCER_REMOVAL') or injections or extra['official_count_files']:
            independent_lanes.append(extra)
        if applied and not raw:
            row['no_primary_case_rows_explanation'] = 'Use separate lane artifacts; command exit alone is never an application case PASS.'
        attempts.append(row)
        kind_counts[kind] += 1
        lane_counts[category] += 1

    per_review = []
    for (stage, product), group in sorted(aggregate.items()):
        per_review.append({'stage':stage,'product_sha':product,'historical_attempts_indexed':group['attempts'],
            'raw_primary_case_rows':sum(group['raw'].values()),'raw_primary_outcomes':dict(group['raw']),
            'case_invocations_within_attempts':group['invocations'],'invocation_outcomes':dict(group['invocation_outcomes']),
            'unique_canonical_definitions_observed':len(group['definitions']),
            'definition_categories':dict(Counter(x.split('/')[0] for x in group['definitions'])),
            'executed_security_load_unique_definitions':len(group['security_load_definitions']),
            'nonpass_classification_occurrences':dict(group['nonpass']),
            'instrumented_httpx_only':metrics(group['requests']),
            'instrumented_load_httpx_only':metrics(group['load_requests']),
            'source_versions':{k:sorted(v) for k,v in sorted(group['source_versions'].items())},
            'acceptance_inferred':False,
            'scope':'All retained attempts for this product/stage, including later addenda; distinct from the original report scope.'})
    final_review = None
    if args.final_product_sha:
        path = ROOT/f'reports/stage-4/REVIEW-{args.final_product_sha[:7]}.json'
        final_review = {**ref(path), 'report':read(path)} if path.exists() else {'product_sha':args.final_product_sha,'status':'NO_REVIEW_REPORT'}
    all_cases = [r for r in case_rows if r['counted_as_application_result']]
    union = sorted({r['canonical_definition'] for r in all_cases})
    raw_totals = Counter(r['outcome'] for r in all_cases)
    all_faults = [r for r in fault_rows if not r['duplicate_of']]
    limits = [
        'Only this fresh room qa/reports records are inspected; source and archive directories are pruned before traversal.',
        'Primary cases.jsonl rows are a reproducible historical subtotal. They exclude isolated official internal runs, raw developer methods, source-only controls, standalone producer consumers, and document geometry; no grand total joins incompatible lanes.',
        'Within an attempt, native test IDs collapse setup/call/teardown outcomes to one invocation, using the worst raw outcome. Multiple phases remain in the raw-row ledger. Repeated attempts remain separate executions.',
        'Canonical definitions collapse baseline original/adjudicated and known representation adapters. Repeated stages/edges/requests/source versions add zero definitions.',
        'A raw historical PASS is not current acceptance. Reconciliations are linked to immutable original review matrices and codec addendum; unclassified historical nonpasses remain visible.',
        'HTTP metrics cover only captured httpx metadata; raw sockets, browser requests and standalone/official consumers are not fully instrumented. Complete all-history request totals cannot be reconstructed reliably.',
        'The ledger hashes primary referenced artifacts and preserves original full manifests. It is not a new byte-for-byte audit of every large historical screenshot/export artifact.',
        'Developer and isolated official totals remain per-attempt references; do not add their JUnit/frozen logs to the same primary-case totals.',
        'Builder-owned document geometry and product-local checks are outside this qa/reports-only inventory. Their published reports remain separately owned; no counts are invented.',
        'Recorded missing QA revisions or session/environment fields remain null. Source hashes from actual case records are retained even when a working QA source differed from the base commit.',
        'The current inventory command is excluded from its own input snapshot. Each refresh creates a new output; previous inventory artifacts never become new application attempts.',
        'Final native export and unchanged clean delivery checker are separate packaging obligations. Missing export or scanner failures do not become application PASS.',
    ]
    summary = {'kind':'FRESH_ROOM_HISTORICAL_EVIDENCE_INVENTORY','room':ROOM,'snapshot_started_at':started,
        'snapshot_finished_at':datetime.now(timezone.utc).isoformat(),
        'repository_head_at_finish':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'script_sha256':digest(Path(__file__)), 'application_requests_added_by_inventory':0,
        'final_new_stage4_review':final_review,'final_review_status':'PENDING_NEW_BUILDER_HANDOFF' if final_review is None else 'SEPARATE_REPORT_REFERENCE',
        'attempt_records':len(attempts),'kinds':dict(kind_counts),'lanes':dict(lane_counts),
        'duplicate_attempt_records':sum(bool(r['duplicate_of']) for r in attempts),
        'historical_primary_case_rows':len(all_cases),'historical_primary_raw_outcomes':dict(raw_totals),
        'historical_observed_canonical_definition_union':len(union),
        'historical_definition_categories':dict(Counter(x.split('/')[0] for x in union)),
        'historical_source_injection_executions':len(all_faults),
        'historical_source_injection_outcomes':dict(Counter(r['outcome'] for r in all_faults)),
        'historical_actual_injected_operation_names':sorted({r['operation'] for r in all_faults if r.get('actually_triggered')}),
        'historical_fault_types':sorted({r['fault'] for r in all_faults if r.get('actually_triggered')}),
        'reference_hash_mismatches':reference_mismatches,'unindexed_or_ambiguous_records':notes,'limitations':limits}
    summary['historical_nonpass_without_recorded_disposition'] = sum(
        r['classification'] == ['RAW_UNCLASSIFIED_RETAINED'] for r in all_cases)
    for name, value in [('summary.json',summary),('per-review.json',per_review),('review-references.json',review_records),
                        ('separate-lanes.json',independent_lanes),('definition-union.json',union)]:
        (out/name).write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n')
    for name, records in [('attempts.jsonl',attempts),('cases.jsonl',case_rows),('source-injections.jsonl',fault_rows)]:
        with (out/name).open('w') as stream:
            for record in records:
                stream.write(json.dumps(record,ensure_ascii=True)+'\n')
    lines = ['# Fresh-room evidence inventory','',f'Snapshot: {started}. This read-only accounting added no application requests.',
        '',f'Indexed **{len(attempts)} attempt records**. Primary historical case JSONL subtotal: **{len(all_cases)} raw rows**, '+str(dict(raw_totals))+'.',
        f'Observed canonical definition union: **{len(union)}**. This is historical coverage, not a fresh Stage4 qualification.',
        '', 'The new Stage4 exact-revision review is pending.' if final_review is None else 'The new Stage4 review is linked separately in summary.json.',
        '', '| Stage | Product | Attempts | Raw PASS | FAIL | ERROR | SKIP | Observed definitions |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for group in per_review:
        counts=group['raw_primary_outcomes']
        lines.append(f"| {group['stage']} | {group['product_sha']} | {group['historical_attempts_indexed']} | {counts.get('PASS',0)} | {counts.get('FAIL',0)} | {counts.get('ERROR',0)} | {counts.get('SKIP',0)} | {group['unique_canonical_definitions_observed']} |")
    lines += ['', 'Files: `attempts.jsonl` binds original metadata, logs, catalogs, JUnit and environment; `cases.jsonl` retains stable IDs, expected/observed results, source hashes and original line references; `per-review.json` separates exact revision subtotals. `review-references.json` preserves original report scopes. `source-injections.jsonl` and `separate-lanes.json` keep source faults, controls, developer methods, collection, tooling, isolated official runs and packaging apart.', '', 'Limits:', '']
    lines += ['- '+limit for limit in limits]
    (out/'README.md').write_text('\n'.join(lines)+'\n')
    (out/'inventory-manifest.json').write_text(json.dumps({f.name:digest(f) for f in sorted(out.iterdir()) if f.is_file()},indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['kind','attempt_records','historical_primary_case_rows',
        'historical_primary_raw_outcomes','historical_observed_canonical_definition_union',
        'historical_source_injection_executions','reference_hash_mismatches','application_requests_added_by_inventory']}))


if __name__ == '__main__':
    main()
