"""Create a standalone detached committed checkout, independent of the live index."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import uuid


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--destination-root', type=Path, required=True)
    p.add_argument('--record', type=Path, required=True)
    a = p.parse_args()
    sha = run('git', '-C', str(a.repo), 'rev-parse', '--verify', a.revision + '^{commit}')
    if a.revision != sha:
        p.error('Use a full 40-character committed SHA')
    destination = a.destination_root / (sha + '-' + uuid.uuid4().hex[:8])
    destination.parent.mkdir(parents=True, exist_ok=True)
    run('git', 'clone', '--no-local', '--no-checkout', str(a.repo), str(destination))
    run('git', '-C', str(destination), 'checkout', '--detach', sha)
    status = run('git', '-C', str(destination), 'status', '--porcelain=v1', '--untracked-files=all')
    assert not status, status
    assert not (destination / '.git/objects/info/alternates').exists()
    files = run('git', '-C', str(destination), 'ls-files', '-z').split('\0')
    hashes = {}
    for path in files:
        source = destination / path
        if source.is_symlink():
            raise RuntimeError('Delivery symlink: ' + path)
        if source.is_file():
            hashes[path] = hashlib.sha256(source.read_bytes()).hexdigest()
    record = {'product_sha': sha, 'checkout': str(destination), 'clean_status': status,
              'standalone_no_alternates': True, 'file_sha256': hashes}
    a.record.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'product_sha': sha, 'checkout': str(destination), 'files': len(hashes)}))


if __name__ == '__main__':
    main()
