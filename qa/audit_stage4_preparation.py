"""Preparation integrity only; never imports or starts a product."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
FILES=['qa/derived/test_stage4.py','qa/derived/test_stage4_browser.py','qa/producer_stage4.py',
       'qa/selfcheck_stage4_design.py','qa/run_suite.py','qa/run_upgrade.py','qa/fault_publication.py',
       'qa/catalog.py','qa/reconcile_candidate.py','qa/STAGE4-INTEGRITY-CONTRACT.md','qa/COVERAGE.md',
       'qa/README.md','qa/catalog.json','reports/defects.json','qa/audit_stage4_preparation.py']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); a=p.parse_args()
    sources={name:sha(ROOT/name) for name in FILES}
    for name in FILES:
        if name.endswith('.py'): ast.parse((ROOT/name).read_text(),filename=name)
    frozen=json.loads((ROOT/'qa/frozen/manifest.json').read_text())
    assert sha(ROOT/'qa/frozen/manifest.json')=='91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036'
    assert all(sha(ROOT/'qa/frozen'/name)==item['sha256'] for name,item in frozen['files'].items())
    assert sha(ROOT/'qa/derived/test_stage2_native_range.py')=='94c5f02b0cb6eb01eeacb555ca013e52a28a4ce562ccd1a39ac44865a0ff1346'
    catalog=json.loads((ROOT/'qa/catalog.json').read_text())
    assert (catalog['frozen_definitions'],catalog['derived_definitions_currently_collected'],catalog['official_shipped_definitions'])==(216,268,158)
    new=[c for c in catalog['cases'] if c['id'].startswith('derived/test_stage4')]
    assert len(new)==64 and all(c['stages']==[4] for c in new)
    attempts=[]
    for folder in sorted((ROOT/'reports/preparation').glob('20261005T12*-stage4-*')):
        if '-preparation-audit-' in folder.name: continue
        if not (folder/'manifest.sha256.json').exists(): continue
        manifest=json.loads((folder/'manifest.sha256.json').read_text())
        assert all(sha(folder/name)==digest for name,digest in manifest.items())
        result=json.loads((folder/'result.json').read_text())
        assert result['kind']!='APPLICATION' and result['application_outcome']=='NOT_RUN'
        attempts.append({'path':str(folder.relative_to(ROOT)),'kind':result['kind'],
            'exit':result['returncode'],'duration_s':result['duration_s'],
            'manifest_sha256':sha(folder/'manifest.sha256.json'),'artifacts':len(manifest)})
    assert len(attempts)==5 and sum(x['exit']==2 for x in attempts)==1, attempts
    final=ROOT/'reports/preparation/20261005T120444.250315Z-stage4-final-source-collection-100d9cdb/catalog.jsonl'
    rows=[json.loads(line) for line in final.read_text().splitlines()]
    assert len(rows)==64
    assert all(sha(ROOT/'qa'/row['id'].split('::')[0])==row['source_sha256'] for row in rows)
    result={'kind':'STAGE4_PREPARATION_AUDIT','application_outcome':'NOT_RUN','application_executions':0,
        'created_at':datetime.now(timezone.utc).isoformat(),'coordinator_gate':'f2bfa8297f77353675c2942fb765b18113b35266',
        'accepted_source_product':'4ce583cca13a033dd2f548ca982deec7200f8ad6',
        'accepted_source_evidence':'4db2742eca07f941e6a03f92c97c3d93c380619f',
        'complete_coordinator_handoff_parts':[1,2,3,4,5,6,7],
        'builder_candidate':None,'frozen_definitions':216,'independent_collected_definitions':268,
        'new_independent_collected_definitions':64,'official_definitions':158,
        'tooling_selfchecks':{'frozen_oracle_pass':8,'derived_design_pass':6,'application_cases':0},
        'source_faults_defined':{'operations':18,'planned_injection_executions':50,'actual_stage4_injections':0},
        'pending_binding':'D415 semantic corruption plus cumulative opaque selector applicability after exact candidate handoff',
        'source_sha256':sources,'frozen_rehashed_files':len(frozen['files']),
        'unchanged_D219_sha256':sha(ROOT/'qa/derived/test_stage2_native_range.py'),
        'attempts':attempts,'preserved_preparation_error':{'attempt':attempts[0]['path'],
            'cause':'First host collection lacked qa on Python import path; two collection errors, no cases executed',
            'correction':'Run collection with cwd=qa; assertions unchanged. Later source adds explicit receive deadline measurement and is recollected.'},
        'no_stage4_implementation_inspection_or_application_execution':True}
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('kind','application_outcome','application_executions','frozen_definitions',
        'independent_collected_definitions','new_independent_collected_definitions','official_definitions','tooling_selfchecks','frozen_rehashed_files')}))


if __name__=='__main__': main()
