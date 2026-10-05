"""Pin the renewed review matrix without importing or executing product code."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL = ROOT.parent.parent / 'official'
OUT = ROOT / 'reports/preparation/stage4-pair-renewal'
GATE = '63617e70f29f564ddb490f48fa83e49d737bb4ee'
STAGES = {1: 'fd843b83db16ec8585d66af7ac0d6fac89aae82c',
          2: '4b2236fb6576b636d168b2cacf1a5d91921cf582',
          3: '301caf55085280f12197e393ab6b4735ef4046c3'}
PARTS = ['9e2a9db8-b818-4cac-8dfe-60fee01fe88c', 'a686289b-4204-4165-b20b-9935c9341c80',
         '886bad0d-efb2-46df-91c4-75e71f5a436f', '5d9943c4-8d6a-41b5-b17e-7f3bb4dec109',
         '027a6348-fada-47c2-9340-2ede20f724d5', '4a91c609-8c69-4a3b-beb5-45111a96f15b',
         '56fa3dc9-5943-4608-9f11-8fa55ea6caf5']
PINS = {
    'qa/derived/test_stage4.py': 'be299b0e7d12dc8d25b4c7f1dba031ce2c36543886218ba46e508cb3e86c3065',
    'qa/derived/test_stage4_encoding_collision.py': '25668245400041709caf8afe859515534b9a7ccf427498ed89f19b81686b9201',
    'qa/derived/test_stage2_pair_visibility.py': '254a3e674d0c00a6b61e2ff6df4e5d5e96241e46d6e6288ae3c41a41dcf18d93',
    'qa/derived/test_stage2_native_range.py': '94c5f02b0cb6eb01eeacb555ca013e52a28a4ce562ccd1a39ac44865a0ff1346',
}


def read(name):
    return json.loads((ROOT / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    path = OUT / name
    assert not path.exists(), ('Preparation is append-only', path)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n')


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    stamp = datetime.now(timezone.utc).isoformat()
    catalog = read('qa/catalog.json')
    cases = []
    for row in catalog['cases']:
        if 4 not in row['stages']:
            continue
        category = row['id'].split('/')[0]
        if category not in ('frozen', 'derived', 'official', 'adapters'):
            continue
        source = (OFFICIAL.parent / row['id'].split('::')[0] if category == 'official'
                  else ROOT / 'qa' / row['id'].split('::')[0])
        cases.append({'id': row['id'], 'category': category,
                      'description': row['description'] or row['id'].split('::')[-1],
                      'source': str(source), 'source_sha256': sha(source),
                      'catalog_source_sha256': row['source_sha256'],
                      'source_line': row['source_line'], 'definition_weight': int(category != 'adapters'),
                      'application_outcome': 'NOT_RUN', 'actual_revision': None})
    counts = Counter(c['category'] for c in cases if c['definition_weight'])
    assert counts == {'frozen': 216, 'derived': 344, 'official': 158}, counts
    for name, expected in PINS.items():
        assert sha(ROOT / name) == expected, name
    frozen = read('qa/frozen/manifest.json')
    frozen_root = ROOT.parent.parent / 'factory/final-inputs/20261005T061628Z'
    assert sha(ROOT / 'qa/frozen/manifest.json') == sha(frozen_root / 'manifest.json') == '91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036'
    for name, info in frozen['files'].items():
        assert sha(ROOT / 'qa/frozen' / name) == sha(frozen_root / name) == info['sha256'], name
    write('case-matrix.json', {'kind': 'CASE_MATRIX_PREPARATION_ONLY', 'prepared_at': stamp,
          'stage': 4, 'product_sha': None, 'counts': dict(counts), 'definition_count': sum(counts.values()),
          'adapter_definitions': 0, 'application_executions': 0, 'cases': cases})

    plan = deepcopy(read('reports/preparation/stage3-pair-renewal/run-plan.json'))
    plan.update(stage=4, product_sha=None,
                application_execution_authorization_dependency='New Builder full SHA and complete seven-part review assembled; standalone immutable checkout and source binding required.')
    lanes = []
    for lane in plan['lanes']:
        lane = deepcopy(lane)
        label = lane['label']
        command = lane['command_template']
        if '--stage' in command:
            command[command.index('--stage') + 1] = '4'
        command[:] = [x.replace('/stage-3', '/stage-4') for x in command]
        if label == 'snapshot-adapted':
            lane['label'] = 'stage4-snapshot-adapted'
            command[command.index('--suite') + 1] = 'stage4-snapshot-adapted'
        if label == 'official-stage3-detail':
            lane['label'] = 'official-stage4-detail'
            command[command.index('--suite') + 1] = 'official-stage4-detail'
        if label.startswith('upgrade-'):
            lane['label'] = label[:-1] + '4'
            command[command.index('--producer-scenario') + 1] = 'stage4-authenticity'
            if label == 'upgrade-3-to-3':
                command[command.index('--source-checkout') + 1] = '{ACCEPTED_STAGE3_CHECKOUT}'
        if label == 'removed-old-object':
            command[command.index('--producer-scenario') + 1] = 'stage4-authenticity'
        if label == 'developer-explicit-adapter':
            command.append('--execute')
        if label == 'official-isolated-clean':
            lane['label'] = 'official-all-isolated-clean'
            index = command.index('--stage')
            command[index:index+2] = ['--all']
        lanes.append(lane)
    py = lanes[0]['command_template'][0]
    def add(label, command, cwd=ROOT, phase='APPLICATION'):
        lanes.append({'label': label, 'command_template': command, 'cwd': str(cwd),
                      'outcome': 'NOT_RUN', 'preserve_all_attempts': True, 'phase': phase})
    for suite in ['advanced', 'stage4-load', 'stage4-numeric', 'stage4-ui', 'stage4-domain',
                  'stage4-browser-derived', 'stage4-integrity', 'stage4-encoding-collision']:
        add(suite, [py, 'qa/run_suite.py', '--checkout', '{CANDIDATE_CHECKOUT}', '--stage', '4',
                    '--suite', suite, '--out', '{OUT}'])
    add('upgrade-4-to-4', [py, 'qa/run_upgrade.py', '--checkout', '{CANDIDATE_CHECKOUT}',
        '--source-checkout', '{CANDIDATE_CHECKOUT}', '--stage', '4', '--source-stage', '4',
        '--browser-transfer', '--producer-scenario', 'stage4-authenticity', '--out', '{OUT}'])
    # Repair controls and frozen U402/U404 go first; final isolation goes last.
    priority = {'stage2-pair-visibility': 0, 'stage2-pair-repair': 1, 'stage4-ui': 2,
                'stage4-browser-derived': 3, 'official-all-isolated-clean': 100}
    lanes.sort(key=lambda x: priority.get(x['label'], 10))
    plan['lanes'] = lanes
    plan['packaging_after_gate'] = {'label': 'final-concrete-delivery-check', 'cwd': str(OFFICIAL),
        'command_template': [py, '-m', 'harness', 'check', '{FINAL_CLEAN_DELIVERY}', '--track', 'tablekeeper'],
        'outcome': 'NOT_RUN', 'preserve_missing_export_and_all_scanner_findings': True}
    plan['source_faults'] = {'defined_operations': 18, 'planned_actual_injections': 50,
                            'actual_injections': 0, 'not_http_definitions': True}
    plan['D404'] = 'Corrected explicit other-r URL is included in stage4-domain once; previous wrong-route FAIL remains historical. No redundant focused run or new definition.'
    assert len({x['label'] for x in lanes}) == len(lanes) == 45
    write('run-plan.json', plan)

    old = read('reports/preparation/stage3-pair-renewal/assembly.json')
    requirements = deepcopy(old['requirement_matrix'])
    for row in requirements:
        row['outcome'] = 'NOT_RUN'
    for line in (ROOT / 'qa/COVERAGE.md').read_text().splitlines():
        if line.startswith('| S4-'):
            cols = [x.strip() for x in line.split('|')[1:-1]]
            requirements.append(dict(zip(['criterion','applicability','requirement','planned_evidence'], cols), outcome='NOT_RUN'))
    requirements.extend([
        {'criterion': 'AC03.8-D417', 'requirement': 'User carrier-shaped JSON identity, equivalent and distinct exact numeric/bool/object values across four writes, ordinary envelope roundtrip/import/replay; genuine internal corruption rejects atomically.', 'planned_evidence': 'All19 unchanged corrected D417 definitions; prior19 QAencoder failures retained; no universal collision-freedom claim.', 'outcome': 'NOT_RUN'},
        {'criterion': 'V-S2-003', 'requirement': 'Unavailable pairs absent, false singles retained; selected form/body/key/uncertainty survive refusal, real201loss and concurrent refresh; current repaired assignments separate from originalreceipt.', 'planned_evidence': 'Unchanged U402/U404,D222,D223-D225 at375/1360, stage4 planner response-loss browser.', 'outcome': 'NOT_RUN'},
        {'criterion': 'FINAL-TRANSFERS', 'requirement': 'Ten current accepted source/destination edges with six frozen definitions, actual producer removal and retained browser/receipts/newoperations.', 'planned_evidence': 'Six earlier edges exact accepted evidence below; four fresh Stage4 edges plus historical old-format producers.', 'outcome': 'NOT_RUN'},
    ])
    defects = deepcopy(old['prior_defect_regressions'])
    for row in defects:
        row.pop('new_stage3_outcome', None)
        row['new_stage4_outcome'] = 'NOT_RUN'
    earlier = []
    for stage, revision in STAGES.items():
        report = ROOT / f'reports/stage-{stage}/REVIEW-{revision[:7]}.json'
        data = json.loads(report.read_text())
        earlier.append({'destination_stage': stage, 'destination_sha': revision,
                        'review': str(report.relative_to(ROOT)), 'review_sha256': sha(report),
                        'incoming_current_edges': [[i, stage] for i in range(1, stage+1)],
                        'provenance_note': 'Earlier exact accepted stage evidence; never a new Stage4 result.'})
    sources = sorted({c['source'] for c in cases})
    sources += [str(ROOT/name) for name in ['qa/fault_publication.py','qa/run_suite.py','qa/run_upgrade.py',
        'qa/producer_stage4.py','qa/attempt.py','qa/reconcile_candidate.py','qa/prepare_stage4_renewal.py','provenance/stage-4-pair-continuation.md',
        'provenance/stage-4-pair-continuation.json']]
    sources += [str(OFFICIAL / f'tablekeeper/spec/stage-{n}.md') for n in range(1,5)]
    sources += [str(OFFICIAL / 'docs/participant-guide.md'), str(ROOT.parent.parent / 'kickoff/dark-factory-kickoff_transcript.md')]
    assembly = {'kind': 'RECIPIENT_ASSEMBLY_AND_PREPARATION', 'recorded_at': stamp,
        'actual_complete_native_assembly_utc': '2026-10-05T14:24:14Z',
        'room': 'e04c2728-8535-41c8-be50-88eb8068fa09', 'recipient': 'kirill.pshinnik/verifier',
        'coordinator_parts_actually_received': [{'part': i+1, 'message_id': value} for i,value in enumerate(PARTS)],
        'full_seven_part_contract_assembled': True, 'coordinator_gate': GATE,
        'coordinator_mirror_commit': subprocess.check_output(['git','log','-1','--format=%H','--','provenance/stage-4-pair-continuation.json'],cwd=ROOT,text=True).strip(),
        'accepted_prior_stages': STAGES, 'rejected_stage4_source': 'e538cd16bbd96d4206d89f17a67791e759c00823',
        'new_builder_candidate_sha': None, 'new_builder_full_review_assembled': False,
        'application_executions': 0, 'frozen_definitions': 216, 'independent_definitions': 344,
        'official_definitions': 158, 'adapter_definitions': 0, 'source_fault_operations': 18,
        'source_fault_planned_injections': 50, 'source_fault_actual_injections': 0,
        'earlier_current_transfer_evidence': earlier,
        'fresh_transfers': [{'source_stage': n,'source_sha':STAGES.get(n),'destination_stage':4,
            'frozen_definitions':6,'live_browser':True,'producer_removed_before_fresh_destination':True,
            'outcome':'NOT_RUN'} for n in range(1,5)],
        'prior_defect_regressions': defects, 'requirement_matrix': requirements,
        'source_hashes': {p:sha(Path(p)) for p in sources}, 'frozen_rehashed_files':len(frozen['files']),
        'limitations': ['Preparation and collection prove no application PASS.',
            'Native room browser readable; four full export attempts yielded no verified file. Final clean unchanged checker must retain honest failure if unresolved.',
            'Original e538 and all earlier failures stay preserved; adapters add zero definitions.',
            'No final product candidate or complete Builder review received at preparation time.']}
    write('assembly.json', assembly)
    write('inspection-error.json', {'kind':'PREPARATION_READ_COMMAND_ERROR', 'application_executions':0,
        'original_command':'python3 -c list comprehension using x in conditional before walrus assignment',
        'original_stdout':'', 'original_stderr':'Traceback (most recent call last):\n  File "<string>", line 1, in <module>\n  File "<string>", line 1, in <listcomp>\nNameError: name \'x\' is not defined\n',
        'returncode':1, 'duration_s':0.162937125,
        'correction':'Separate explicit for-loop read succeeded; no product request, source alteration or acceptance case.'})
    print(json.dumps({'kind':'PREPARATION','application_executions':0,'counts':dict(counts),
                      'command_templates':len(lanes),'separate_final_packaging_template':1,
                      'source_hashes':len(assembly['source_hashes']),'frozen_files':len(frozen['files'])}))


if __name__ == '__main__':
    main()
