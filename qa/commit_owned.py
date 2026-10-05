"""Commit only Verifier paths while holding the shared OS repository lock."""
from pathlib import Path
import argparse
import fcntl
import json
import os
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent


def git(*args, check=True):
    return subprocess.run(['git', '-C', str(ROOT), *args], text=True, capture_output=True, check=check)


def owned(path):
    return path.startswith('qa/') or path.startswith('reports/')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--message', required=True)
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args()
    for path in args.paths:
        relative = str((ROOT / path).resolve().relative_to(ROOT))
        if relative not in ('qa', 'reports') and not owned(relative):
            raise SystemExit('Foreign path refused: ' + relative)
    with (ROOT / '.git/factory-repository.lock').open('a') as lock:
        deadline = time.monotonic() + 15
        while True:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise SystemExit('Repository lock remained busy for 15 seconds; no staging performed')
                time.sleep(.1)
        before = git('rev-parse', '--verify', 'HEAD', check=False).stdout.strip() or None
        staged = git('diff', '--cached', '--name-only', '-z').stdout.split('\0')
        foreign = [p for p in staged if p and not owned(p)]
        if foreign:
            raise SystemExit('Foreign staged paths untouched: ' + json.dumps(foreign))
        git('add', '--', *args.paths)
        actual = [p for p in git('diff', '--cached', '--name-only', '-z').stdout.split('\0') if p]
        if not actual:
            raise SystemExit('Nothing staged')
        assert all(owned(p) for p in actual), actual
        env = os.environ.copy()
        env.update(GIT_AUTHOR_NAME='Verifier', GIT_AUTHOR_EMAIL='verifier@juniper.factory.invalid',
                   GIT_COMMITTER_NAME='Verifier', GIT_COMMITTER_EMAIL='verifier@juniper.factory.invalid')
        result = subprocess.run(['git', '-C', str(ROOT), 'commit', '-m', args.message],
                                env=env, text=True, capture_output=True)
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)
        after = git('rev-parse', 'HEAD').stdout.strip()
        changed = git('diff-tree', '--root', '--no-commit-id', '--name-only', '-r', after).stdout.splitlines()
        assert all(owned(p) for p in changed), changed
        assert git('diff', '--cached', '--name-only').stdout == ''
        print(json.dumps({'parent': before, 'commit': after, 'committed_paths': changed,
                          'identity': git('show', '-s', '--format=%an <%ae> / %cn <%ce>', after).stdout.strip(),
                          'lock': str(ROOT / '.git/factory-repository.lock'), 'path_audit': 'PASS'}))


if __name__ == '__main__':
    main()
