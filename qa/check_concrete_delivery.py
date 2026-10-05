"""Capture the unchanged offline checker and adjudicate its raw findings separately."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def env_strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'Env' and isinstance(child, list):
                yield from (x for x in child if isinstance(x, str))
            else:
                yield from env_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from env_strings(child)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkout-record', required=True, type=Path)
    p.add_argument('--product-checkout-record', required=True, type=Path)
    p.add_argument('--official', required=True, type=Path)
    p.add_argument('--python', required=True)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    delivery = json.loads(a.checkout_record.read_text())
    product = json.loads(a.product_checkout_record.read_text())
    root = Path(delivery['checkout'])
    sha = delivery['product_sha']
    assert git(root, 'rev-parse', 'HEAD') == sha
    assert git(root, 'status', '--porcelain=v1', '--untracked-files=all') == ''
    assert not (root/'.git/objects/info/alternates').exists()
    hashes = delivery['file_sha256']
    assert all(digest(root/name) == value for name, value in hashes.items())
    product_files = {name: value for name, value in product['file_sha256'].items()
                     if re.match(r'^stage-[1-4]/', name)}
    actual_product_files = {name: value for name, value in hashes.items()
                            if re.match(r'^stage-[1-4]/', name)}
    assert actual_product_files == product_files
    required = ['README.md', 'FACTORY.md'] + ['mandates/'+x+'.md' for x in
                ('coordinator', 'builder', 'verifier')] + [f'stage-{i}/{name}'
                for i in range(1, 5) for name in ('Dockerfile', 'RUN.md')]
    assert all((root/name).is_file() for name in required)
    official_hashes = {str(x.relative_to(a.official)): digest(x)
                       for x in (a.official/'harness').rglob('*.py')}
    official_hashes['harness/requirements.txt'] = digest(a.official/'harness/requirements.txt')
    dependency_versions = {name: importlib.metadata.version(name)
                           for name in ('httpx', 'playwright', 'pytest')}
    command = [a.python, '-m', 'harness', 'check', str(root), '--track', 'tablekeeper']
    start = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    with (a.out/'stdout.log').open('wb') as stdout, (a.out/'stderr.log').open('wb') as stderr:
        result = subprocess.run(command, cwd=a.official, stdout=stdout, stderr=stderr,
                                timeout=120)
    duration = time.monotonic()-tick
    # Classification is after the unchanged command. It never modifies checker,
    # delivery, originals, or the command's actual failure status.
    output = (a.out/'stdout.log').read_text()+(a.out/'stderr.log').read_text()
    findings = []
    env_pattern = re.compile(r'(?i)\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)\s*=\s*\S+')
    for line in output.splitlines():
        entry = {'raw_line': line, 'classification': 'UNCLASSIFIED'}
        if line.startswith('room.json is missing;'):
            entry['classification'] = 'MISSING_GENUINE_NATIVE_ROOM_EXPORT'
        else:
            match = re.match(r'^(.+) looks like it holds (?:a|an) ([a-z-]+)\.', line)
            if match:
                name, shape = match.groups()
                path = root/name
                assert path.resolve().is_relative_to(root.resolve()) and path.is_file()
                entry.update(path=name, shape=shape, file_sha256=digest(path))
                if shape == 'env-assignment':
                    text = path.read_text()
                    matches = list(env_pattern.finditer(text))
                    env = set(env_strings(json.loads(text)))
                    safe = {x for x in env if re.fullmatch(r'GPG_KEY=[0-9A-F]{40}', x)}
                    entry['match_locations'] = [dict(offset=m.start(),
                        match_sha256=hashlib.sha256(m.group().encode()).hexdigest()) for m in matches]
                    if matches and all(m.group().rstrip('\",') in safe for m in matches):
                        entry['classification'] = 'PUBLIC_DOCKER_GPG_FINGERPRINT_NOT_CREDENTIAL'
                        entry['public_fingerprints'] = sorted(x.split('=', 1)[1] for x in safe)
        findings.append(entry)
    assert all(digest(root/name) == value for name, value in hashes.items())
    assert git(root, 'status', '--porcelain=v1', '--untracked-files=all') == ''
    assert all(digest(a.official/name) == value for name, value in official_hashes.items())
    report = {'lane': 'PACKAGING', 'delivery_sha': sha, 'accepted_product_sha': product['product_sha'],
              'checkout': str(root), 'command': command, 'cwd': str(a.official),
              'started_at': start, 'ended_at': datetime.now(timezone.utc).isoformat(),
              'duration_s': duration, 'raw_exit': result.returncode,
              'stdout_sha256': digest(a.out/'stdout.log'), 'stderr_sha256': digest(a.out/'stderr.log'),
              'tracked_files_rehashed_before_and_after': len(hashes),
              'product_files_equal_accepted_candidate': len(product_files),
              'required_layout_files_sha256': {name: digest(root/name) for name in required},
              'host_installed_dependency_versions': dependency_versions,
              'official_pinned_requirements': (a.official/'harness/requirements.txt').read_text(),
              'official_source_sha256': official_hashes, 'findings': findings,
              'finding_count': len(findings), 'unclassified_findings': sum(x['classification']=='UNCLASSIFIED' for x in findings),
              'status': 'PASS' if result.returncode == 0 else 'RAW_FAIL_RETAINED',
              'native_room_export_exists': (root/'room.json').exists(),
              'raw_bytes_modified': False, 'history_rewritten': False,
              'official_checker_modified': False}
    (a.out/'packaging.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('delivery_sha','accepted_product_sha','raw_exit',
                    'duration_s','finding_count','unclassified_findings','status')}))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
