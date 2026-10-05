"""Verify and preserve the authorized freeze. Never reads product implementations."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
FROZEN = Path('/Users/kirillpsinnik/Code/wearedevelopers-hackathon/factory/final-inputs/20261005T061628Z')
EXPECTED = '91fadde5b105ab3bab5c7a93779f6d91eca710e5cca85c6306d5adc1cdc61036'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def put_once(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f'Refusing to overwrite different frozen evidence: {path}')
    else:
        with path.open('xb') as stream:
            stream.write(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    raw = (FROZEN / 'manifest.json').read_bytes()
    assert digest(raw) == EXPECTED, 'Frozen manifest hash mismatch'
    manifest = json.loads(raw)
    rows = []
    for name, meta in manifest['files'].items():
        source = FROZEN / name
        data = source.read_bytes()
        actual = digest(data)
        row = {'path': name, 'expected_sha256': meta['sha256'], 'actual_sha256': actual,
               'expected_bytes': meta['bytes'], 'actual_bytes': len(data),
               'matches': actual == meta['sha256'] and len(data) == meta['bytes']}
        rows.append(row)
        if not row['matches']:
            raise RuntimeError(f'Frozen source mismatch: {name}')
        put_once(ROOT / 'qa' / 'frozen' / name, data)
    put_once(ROOT / 'qa' / 'frozen' / 'manifest.json', raw)
    original = (FROZEN / 'baseline-original/test_security.py').read_text()
    corrected = (FROZEN / 'baseline-adjudicated/test_security.py').read_text()
    diff = ''.join(difflib.unified_diff(original.splitlines(True), corrected.splitlines(True),
                                     'baseline-original/test_security.py', 'baseline-adjudicated/test_security.py'))
    (args.out / 'baseline-oracle.diff').write_text(diff)
    result = {'kind': 'INPUT_INTEGRITY_ONLY', 'application_outcome': 'NOT_RUN',
              'room': 'e04c2728-8535-41c8-be50-88eb8068fa09',
              'at': datetime.now(timezone.utc).isoformat(), 'manifest_sha256': EXPECTED,
              'source_root': str(FROZEN), 'verified_files': len(rows), 'files': rows}
    (args.out / 'input-integrity.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'verified_files': len(rows), 'manifest_sha256': EXPECTED,
                      'application_outcome': 'NOT_RUN', 'out': str(args.out)}))


if __name__ == '__main__':
    main()
