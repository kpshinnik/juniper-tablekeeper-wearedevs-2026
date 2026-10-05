"""Unique, append-only command attempts with exact environment and hashes."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import signal
import subprocess
import time
import uuid


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reports', type=Path, required=True)
    p.add_argument('--label', required=True)
    p.add_argument('--kind', choices=['PREPARATION', 'TOOLING', 'APPLICATION'], required=True)
    p.add_argument('--product-sha')
    p.add_argument('--qa-sha')
    p.add_argument('--stage', type=int, choices=[1, 2, 3, 4])
    p.add_argument('--cwd', type=Path)
    p.add_argument('--timeout', type=float, default=1800)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command:
        p.error('Command is required')
    if a.kind == 'APPLICATION' and (not a.product_sha or len(a.product_sha) != 40):
        p.error('Application evidence requires the full product SHA')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = a.reports / f'{stamp}-{a.label}-{uuid.uuid4().hex[:8]}'
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(QA_EVIDENCE_DIR=str(out.resolve()), QA_PRODUCT_SHA=a.product_sha or '',
               QA_SOURCE_SHA=a.qa_sha or '', PYTHONDONTWRITEBYTECODE='1')
    if a.stage:
        env['STAGE_UNDER_TEST'] = str(a.stage)
    command = [x.replace('{OUT}', str(out.resolve())) for x in command]
    meta = {'kind': a.kind, 'application_outcome': 'NOT_RUN' if a.kind != 'APPLICATION' else 'RUNNING',
            'room': 'e04c2728-8535-41c8-be50-88eb8068fa09', 'product_sha': a.product_sha,
            'qa_sha': a.qa_sha, 'stage': a.stage, 'command': command,
            'cwd': str(a.cwd or Path.cwd()), 'started_at': datetime.now(timezone.utc).isoformat(),
            'python': platform.python_version(), 'platform': platform.platform(),
            'timeout_s': a.timeout, 'client_memory_cap_added': False}
    (out / 'attempt.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(str(out), flush=True)
    tick = time.monotonic()
    code = 125
    try:
        with (out / 'command.log').open('wb') as stream:
            process = subprocess.Popen(command, cwd=a.cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=a.timeout)
                meta['command_outcome'] = 'EXITED'
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                code = 124
                meta['command_outcome'] = 'TIMEOUT'
    except Exception as exc:
        meta.update(command_outcome='RUNNER_ERROR', error=repr(exc))
    meta.update(returncode=code, duration_s=time.monotonic()-tick,
                ended_at=datetime.now(timezone.utc).isoformat())
    if a.kind == 'APPLICATION':
        meta['application_outcome'] = 'REQUIRES_RECONCILIATION'  # exit zero alone is not acceptance
    (out / 'result.json').write_text(json.dumps(meta, indent=2) + '\n')
    hashes = {str(f.relative_to(out)): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in out.rglob('*') if f.is_file()}
    (out / 'manifest.sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps({'out': str(out), 'returncode': code, 'duration_s': meta['duration_s']}), flush=True)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
