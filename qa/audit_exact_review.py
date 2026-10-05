"""Hash-audit executed review artifacts and their exact source revisions."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkout-record', type=Path, required=True)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--product-sha', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    checkout_record = json.loads(args.checkout_record.read_text())
    checkout = Path(checkout_record['checkout'])
    assert checkout_record['product_sha'] == args.product_sha
    assert not subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain=v1', '--untracked-files=all'], text=True).strip()
    assert subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip() == args.product_sha
    assert not (checkout / '.git/objects/info/alternates').exists()
    for name, expected in checkout_record['file_sha256'].items():
        assert digest(checkout / name) == expected, name
    matrix = json.loads((args.reports / ('case-matrix-' + args.product_sha[:7] + '.json')).read_text())
    assert matrix['product_sha'] == args.product_sha
    annotated = {(item['attempt'], item['id']): item
                 for definition in matrix['definitions'] for item in definition['observations']}
    manifests, sources, cases, description_supplements = [], {}, [], []
    for folder in sorted(args.reports.resolve().glob('*' + args.product_sha[:7] + '*')):
        if not folder.is_dir() or not (folder / 'attempt.json').exists():
            continue
        meta = json.loads((folder / 'attempt.json').read_text())
        assert (folder / 'result.json').exists(), folder
        manifest = json.loads((folder / 'manifest.sha256.json').read_text())
        for name, expected in manifest.items():
            assert digest(folder / name) == expected, (folder, name)
        manifests.append({'path': str(folder.relative_to(root)), 'artifact_files': len(manifest),
                          'manifest_sha256': digest(folder / 'manifest.sha256.json'),
                          'all_files_verified': True, 'kind': meta['kind']})
        case_path = folder / 'cases.jsonl'
        if not case_path.exists():
            continue
        for line in case_path.read_text().splitlines():
            row = json.loads(line)
            assert row['product_revision'] == args.product_sha
            assert row['expected'] and row['observed']
            if not row['description']:
                supplement = annotated[(str(folder.relative_to(root)), row['id'])]
                assert supplement['description'] and supplement['test_sha256'] == row['test_sha256']
                assert supplement['outcome'] == row['outcome']
                description_supplements.append({'attempt': str(folder.relative_to(root)), 'id': row['id'],
                    'description': supplement['description'],
                    'source': 'Separate case matrix derives missing docstring description from original descriptive test name; raw row unchanged.'})
            name = row['id'].split('::')[0]
            key = (meta['qa_sha'], name)
            if key not in sources:
                if name.startswith('official/'):
                    expected = digest(root.parent.parent / name)
                else:
                    blob = subprocess.check_output(['git', '-C', str(root), 'show', meta['qa_sha'] + ':qa/' + name])
                    expected = hashlib.sha256(blob).hexdigest()
                    assert digest(root / 'qa' / name) == expected, name
                sources[key] = expected
            assert row['test_sha256'] == sources[key], name
            cases.append(row)
    result = {'at': datetime.now(timezone.utc).isoformat(), 'product_sha': args.product_sha,
              'clean_checkout': True, 'standalone_no_alternates': True,
              'complete_tracked_files_rehashed': len(checkout_record['file_sha256']),
              'manifest_count': len(manifests), 'artifact_file_count': sum(x['artifact_files'] for x in manifests),
              'manifests': manifests, 'case_rows_verified': len(cases),
              'raw_case_outcomes': dict(Counter(x['outcome'] for x in cases)),
              'raw_missing_docstring_descriptions': len(description_supplements),
              'separate_description_supplements': description_supplements,
              'test_sources': [{'qa_sha': key[0], 'path': key[1], 'sha256': value} for key, value in sorted(sources.items())],
              'outcome': 'PASS', 'scope': 'Integrity and provenance audit; no new application tests, requests or definitions.'}
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ['product_sha','complete_tracked_files_rehashed','manifest_count','artifact_file_count','case_rows_verified','raw_case_outcomes','outcome']}))


if __name__ == '__main__':
    main()
