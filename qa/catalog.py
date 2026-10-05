"""Consolidate case catalogs without treating collection as execution."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent


def main():
    rows = {}
    sources=list((ROOT/'reports/preparation').glob('*/catalog.jsonl'))
    for stage in range(1,5):
        sources.extend((ROOT/f'reports/stage-{stage}').glob('*/catalog.jsonl'))
    for source in sorted(sources):
        for line in source.read_text().splitlines():
            row = json.loads(line)
            key = row['id'].split('/qa/')[-1]
            if key.startswith('band-work/'):
                raise ValueError('Unrecognized source ID: '+key)
            if 'baseline-adjudicated' in key:
                continue
            if key not in rows:
                rows[key] = {'id': key, 'description': row['description'],
                             'source_sha256': row['source_sha256'], 'source_line': row['line'],
                             'stages': [], 'collection_evidence': [], 'application_outcome':'NOT_RUN'}
            item = rows[key]
            versions=item.setdefault('source_versions',[])
            version={'sha256':row['source_sha256'],'source_line':row['line'],
                     'catalog':str(source.relative_to(ROOT))}
            if version not in versions:versions.append(version)
            stage = row.get('stage')
            if key.startswith('official/'):
                stages = list(range(int(stage),5))
            elif '/numeric-original/' in '/'+key:
                stages = [int(stage)]
            elif key.startswith('derived/test_stage2_upgrade_browser.py'):
                stages = [2,3,4]
            elif key.startswith('derived/test_stage4'):
                stages = [4]
            elif key.startswith('derived/test_stage3'):
                stages = [3,4]
            elif key.startswith('derived/test_stage2'):
                stages = [2,3,4]
            elif key.startswith('derived/') or '/baseline-original/' in '/'+key:
                stages = [1,2,3,4]
            elif any(x in key for x in ('test_advanced.py','test_stage4_')):
                stages = [4]
            elif 'test_compact_pairs.py' in key:
                stages = [2,3,4]
            else:
                stages = [1,2,3,4]
            item['stages'] = sorted(set(item['stages']+stages))
            item['collection_evidence'].append(str(source.relative_to(ROOT)))
            if 'test_upgrade_contract.py' in key:
                item['edges'] = [[i,j] for i in range(1,5) for j in range(i,5)]
            elif key.startswith('derived/test_stage2_upgrade_browser.py'):
                item['edges'] = [[i,j] for j in range(2,5) for i in range(1,j+1)]
    frozen = [x for x in rows.values() if x['id'].startswith('frozen/')]
    derived = [x for x in rows.values() if x['id'].startswith('derived/')]
    official = [x for x in rows.values() if x['id'].startswith('official/')]
    assert len(frozen) == 216, len(frozen)
    report = {'kind':'COLLECTION_CATALOG', 'application_outcome':'NOT_RUN',
              'frozen_definitions':len(frozen), 'derived_definitions_currently_collected':len(derived),
              'official_shipped_definitions':len(official),
              'tooling_selfchecks_not_application':14,
              'tooling_selfcheck_counts':{'frozen_oracle':8,'independent_stage4_design':6},
              'adapter_definition_count':0,
              'adapter_note':'Opaque selector adaptations are aliases of original logical cases; see exact-revision report case matrices. They add no frozen or derived definitions.',
              'execution_evidence':'reports/stage-*/case-matrix-*.json; collection rows intentionally do not claim application outcomes',
              'cases':sorted(rows.values(),key=lambda x:x['id'])}
    (ROOT/'qa/catalog.json').write_text(json.dumps(report,indent=2,ensure_ascii=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}))


if __name__ == '__main__':
    main()
