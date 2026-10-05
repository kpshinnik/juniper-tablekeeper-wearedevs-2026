"""Run applicable local methods, keeping inherited fixture adaptations explicit."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADAPTED = {
    'test_historical_lifetime.HistoricalLifetime.test_legacy_offset_seconds_receipt_remains_original',
    'test_pairs.Pairs.test_old_receipt_unknown_table_ids_remains_ignored_on_import',
}


def leaves(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from leaves(item)
        else:
            yield item


if '--execute' in sys.argv:
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'checks'), pattern='test_stage4.py' if '--stage4-only' in sys.argv else 'test*.py')
    # Original methods remain unchanged on disk and their first raw ERRORs are
    # preserved. Both edited native snapshots to mimic schema1; the explicit
    # Stage3 adapter constructs schema1 instead and exercises both lifetimes.
    selected = unittest.TestSuite(t for t in leaves(suite) if t.id() not in ADAPTED)
    result = unittest.TextTestRunner(verbosity=2).run(selected)
    raise SystemExit(0 if result.wasSuccessful() else 1)

folder = ROOT / 'checks/evidence' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-stage4-developer')
folder.mkdir()
command = [sys.executable, str(pathlib.Path(__file__).resolve()), '--execute']
if '--stage4-only' in sys.argv:
    command.append('--stage4-only')
start = time.monotonic()
process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
(folder / 'tests.log').write_text(process.stdout + process.stderr)
(folder / 'result.json').write_text(json.dumps({
    'command': command, 'exit_code': process.returncode, 'seconds': time.monotonic() - start,
    'adapted_original_methods': sorted(ADAPTED),
    'replacement': 'test_stage3.PoliciesAndSeries.test_legacy_fixture_adapters_preserve_original_timestamp_and_unknown_selector (two subcases)',
    'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [*ROOT.glob('*.py'), *ROOT.glob('checks/*.py')]},
}, indent=2))
print(folder)
print(process.stdout + process.stderr)
raise SystemExit(process.returncode)
