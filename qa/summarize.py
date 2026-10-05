"""Derive a new summary artifact; never rewrite an original attempt."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import math


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def metrics(rows):
    values = sorted(r['send_receive_decompression_s'] for r in rows)
    def percentile(p):
        return values[max(0, math.ceil(len(values)*p)-1)] if values else None
    return {'requests':len(values),'p50_s':percentile(.5),'p95_s':percentile(.95),
            'max_s':max(values) if values else None,
            'max_observed_inflight':max((r['inflight_at_start'] for r in rows),default=0),
            'statuses':dict(Counter(str(r.get('status',r.get('exception'))) for r in rows)),
            'received_decompressed_bytes':sum(r.get('received_decompressed_bytes') or 0 for r in rows)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--attempt',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    source = a.attempt.resolve()
    if a.out.resolve().is_relative_to(source):
        p.error('New summaries must be outside immutable attempt directory')
    records = read_rows(source/'cases.jsonl')
    by_id = defaultdict(list)
    for row in records:
        by_id[row['id']].append(row)
    priority = {'PASS':0,'SKIP':1,'FAIL':2,'ERROR':3}
    outcomes = {key:max((r['outcome'] for r in rows),key=priority.get) for key,rows in by_id.items()}
    requests = read_rows(source/'http-requests.jsonl')
    grouped = defaultdict(list)
    for row in requests:
        grouped[row.get('case')].append(row)
    hashes = json.loads((source/'manifest.sha256.json').read_text())
    mismatches = [name for name,expected in hashes.items()
                  if not (source/name).is_file() or hashlib.sha256((source/name).read_bytes()).hexdigest()!=expected]
    result = {'attempt':str(source),'integrity_mismatches':mismatches,
              'case_outcomes':outcomes,'totals':dict(Counter(outcomes.values())),
              'httpx':metrics(requests),'httpx_by_case':{str(key):metrics(rows) for key,rows in grouped.items()},
              'raw_wire_requests':len(read_rows(source/'wire-requests.jsonl')),
              'fault_injections_counted_as_http':0,
              'acceptance':'REQUIRES_CONTRACT_RECONCILIATION'}
    with a.out.open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'summary':str(a.out),'totals':result['totals'],'httpx':result['httpx'],
                      'integrity_mismatches':mismatches}))


if __name__ == '__main__':
    main()
