"""Run unchanged independent browser definitions against a lightweight local service.

This is Builder reproduction evidence, not independent constrained-container review.
QA source files are read from the sibling qa directory and never modified/imported
by the product. No persistent demo port or Docker resource is used.
"""
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
import server

targets = sys.argv[1:] or ['test_stage2_pair_visibility.py']
test_paths = [(REPO/'qa'/t if '/' in t else REPO/'qa/derived'/t).resolve() for t in targets]
assert all(p.is_relative_to(REPO/'qa') and p.is_file() and p.name.startswith('test_') for p in test_paths)
evidence_root = Path(os.environ.get('BUILDER_EVIDENCE_ROOT', str(ROOT / 'checks/evidence')))
out = evidence_root / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-unchanged-browser-review')
out.mkdir(parents=True)
sources = [*sorted(ROOT.glob('*.py')), *sorted((ROOT/'web').glob('*')),
           Path(__file__), REPO/'qa/derived/test_stage1.py', REPO/'qa/derived/test_stage2_browser.py',
           *test_paths]
manifest = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=os.pathsep.join([str(out), str(REPO/'qa'), str(REPO/'qa/frozen/supplemental')]),
           PLAYWRIGHT_BROWSERS_PATH='/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers',
           QA_EVIDENCE_DIR=str(out), STAGE_UNDER_TEST='4')
start = time.monotonic()
with (out/'service.log').open('w') as service_log, contextlib.redirect_stderr(service_log):
    service = server.Server(('127.0.0.1', 0), server.Handler)
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    env['QA_BROWSER_BASE'] = 'http://127.0.0.1:' + str(service.server_address[1])
    plugin = out/'local_frozen_adapter.py'
    plugin.write_text("import os, pathlib, sys\ndef pytest_collection_modifyitems(session, config, items):\n    for name, module in list(sys.modules.items()):\n        if name.endswith(('test_stage4_ui', 'test_stage4_ui_lost')):\n            module.BASE = os.environ['QA_BROWSER_BASE']\n            if name.endswith('test_stage4_ui'):\n                module.Path = lambda value: pathlib.Path(os.environ['QA_EVIDENCE_DIR'])/'stage4-ui' if str(value)=='/reports/stage4-ui' else pathlib.Path(value)\n")
    command = [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider', '-p', 'local_frozen_adapter', '-q',
               '--junitxml=' + str(out/'junit.xml'), *[str(p) for p in test_paths]]
    try:
        with (out/'tests.log').open('w') as log:
            result = subprocess.run(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
    finally:
        service.shutdown(); service.server_close(); thread.join()
rows = []
if (out/'junit.xml').exists():
    for case in ET.parse(out/'junit.xml').iter('testcase'):
        status = 'FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS'
        rows.append({'id': case.get('classname')+'::'+case.get('name'), 'status':status, 'duration_seconds':float(case.get('time',0)),
                     'observed': ''.join(case.find('failure').itertext()) if status=='FAIL' else 'See original JUnit and captured observations'})
(out/'cases.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
(out/'result.json').write_text(json.dumps({'command':command, 'cwd':str(REPO), 'exit_code':result.returncode,
    'duration_seconds':time.monotonic()-start,'repository_head':head,'source_sha256':manifest,
    'product_source_binding':'Exact hashes above; repository may include non-runtime Builder check changes.',
    'adapter':'FrozenUI origin/artifact output only; test source/assertions unchanged. Plugin retained in attempt.',
    'environment':'Builder local HTTP on ephemeral loopback port and Chromium; no Docker or service resource-limit qualification',
    'counts':{s:sum(r['status']==s for r in rows) for s in ['PASS','FAIL','ERROR','SKIP']}},indent=2)+'\n')
print(out)
print(json.dumps({s:sum(r['status']==s for r in rows) for s in ['PASS','FAIL','ERROR','SKIP']}))
sys.exit(result.returncode)
