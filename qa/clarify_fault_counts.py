"""Read preserved source-injection evidence; add labels without rerunning it."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    attempts = []
    for raw in sorted((ROOT / 'reports/stage-1').glob('*-source-faults-*/source-faults.jsonl')):
        folder = raw.parent
        manifest = json.loads((folder / 'manifest.sha256.json').read_text())
        assert all(sha(folder / name) == value for name, value in manifest.items())
        rows = [json.loads(line) for line in raw.read_text().splitlines()]
        summary = json.loads((folder / 'command.log').read_text().splitlines()[-1])
        metadata = json.loads((folder / 'attempt.json').read_text())
        triggered = [r for r in rows if r['actually_triggered'] == [r['fault']]]
        operations = sorted({r['operation'] for r in triggered})
        points = sorted({r['fault'] for r in triggered})
        reset = [r for r in triggered if r['operation'] == 'reset']
        assert len(rows) == len(triggered) == 20
        assert len(operations) == 8 and len(points) == 3
        assert len(reset) == 1 and reset[0]['fault'] == 'candidate_encode'
        assert reset[0]['observed'] == {'exception': 'ValueError', 'state_unchanged': True, 'retry_status': 204}
        attempts.append({
            'product_sha': metadata['product_sha'],
            'raw_path': str(raw.relative_to(ROOT)), 'raw_sha256': sha(raw),
            'original_manifest_sha256': sha(folder / 'manifest.sha256.json'),
            'original_manifest_verified': True,
            'defined_operation_names': summary['control_operations_defined'],
            'defined_operation_count': len(summary['control_operations_defined']),
            'executed_control_operation_names': sorted({r['operation'] for r in summary['control_operations_executed']}),
            'executed_control_operation_count': len(summary['control_operations_executed']),
            'actually_injected_operation_names': operations,
            'actually_injected_operation_count': len(operations),
            'actually_triggered_fault_point_types': points,
            'actually_triggered_fault_point_type_count': len(points),
            'actual_injection_executions': len(triggered),
            'injection_outcomes': dict(Counter(r['outcome'] for r in triggered)),
            'injections_by_operation': dict(Counter(r['operation'] for r in triggered)),
            'reset_actual_injection': reset[0], 'http_requests': 0,
        })
    assert len(attempts) == 3
    historical = sorted((ROOT / 'reports/stage-1').glob('REVIEW-*'))
    report = {
        'kind': 'EVIDENCE_LABEL_CLARIFICATION_NOT_APPLICATION_RERUN',
        'attributed_to': 'Verifier, following Coordinator evidence audit',
        'source_room_message': 'e19882ff-9fd2-4faa-b4a4-5260a65c87ac',
        'room': 'e04c2728-8535-41c8-be50-88eb8068fa09',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'clarification': 'Eight operations were actually injected, with twenty operation/fault-point executions per reviewed revision. Three is the number of fault-point types, not operation names.',
        'attempts': attempts,
        'historical_reports_preserved_sha256': {str(p.relative_to(ROOT)): sha(p) for p in historical},
        'application_executions_added': 0, 'new_logical_definitions_added': 0,
    }
    target = ROOT / 'reports/stage-1/CLARIFICATION-source-fault-counts-20261005.json'
    with target.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'artifact': str(target), 'attempts_audited': len(attempts),
                      'per_attempt_operations': 8, 'per_attempt_injections': 20,
                      'fault_point_types': 3, 'application_executions_added': 0}))


if __name__ == '__main__':
    main()
