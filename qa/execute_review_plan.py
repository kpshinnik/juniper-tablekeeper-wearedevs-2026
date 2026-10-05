"""Run a bound review plan sequentially, preserving every command attempt."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--assembly', type=Path, required=True)
    parser.add_argument('--product-sha', required=True)
    parser.add_argument('--qa-sha', required=True)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    assembly = json.loads(args.assembly.read_text())
    assert assembly['all_seven_full_native_parts_read']
    assert assembly['product_sha'] == plan['product_sha'] == args.product_sha
    assert len(args.product_sha) == len(args.qa_sha) == 40
    assert not args.record.exists(), 'Never overwrite an execution ledger'
    root = Path(__file__).resolve().parent.parent
    checkout = plan['candidate_checkout']
    assert subprocess.check_output(['git', '-C', checkout, 'rev-parse', 'HEAD'], text=True).strip() == args.product_sha
    assert not subprocess.check_output(['git', '-C', checkout, 'status', '--porcelain=v1', '--untracked-files=all'], text=True).strip()
    ledger = {'product_sha': args.product_sha, 'qa_sha': args.qa_sha,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'sequential': True, 'fail_fast': False, 'commands': []}
    args.record.write_text(json.dumps(ledger, indent=2) + '\n')
    for index, lane in enumerate(plan['lanes'], 1):
        command = [sys.executable, str(root / 'qa/attempt.py'),
                   '--reports', str(args.reports.resolve()),
                   '--label', lane['label'] + '-' + args.product_sha[:7],
                   '--kind', 'APPLICATION', '--product-sha', args.product_sha,
                   '--qa-sha', args.qa_sha, '--stage', str(plan['stage']),
                   '--cwd', lane['cwd'], '--', *lane['command_template']]
        print(json.dumps({'start': index, 'total': len(plan['lanes']), 'label': lane['label']}), flush=True)
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        item = {'index': index, 'label': lane['label'], 'command': command,
                'returncode': result.returncode, 'stdout': result.stdout,
                'stderr': result.stderr, 'ended_at': datetime.now(timezone.utc).isoformat()}
        ledger['commands'].append(item)
        args.record.write_text(json.dumps(ledger, indent=2) + '\n')
        print(json.dumps({'complete': index, 'label': lane['label'],
                          'returncode': result.returncode, 'stdout': result.stdout.strip(),
                          'stderr': result.stderr.strip()}), flush=True)
    ledger['ended_at'] = datetime.now(timezone.utc).isoformat()
    ledger['all_commands_attempted'] = len(ledger['commands']) == len(plan['lanes'])
    ledger['outcome'] = 'REQUIRES_RECONCILIATION'
    args.record.write_text(json.dumps(ledger, indent=2) + '\n')


if __name__ == '__main__':
    main()
