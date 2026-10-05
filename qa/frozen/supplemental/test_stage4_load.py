"""Independent Stage4 concurrency checks, using only public synthetic HTTP.

Collection is preparation only. Run on an immutable Stage4 in its own service.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import random
import time

import httpx
import pytest

from test_advanced import World
from test_boundaries import api, observe


@pytest.mark.parametrize('mode', ['same-key', 'different-keys', 'competing-plans'],
                         ids=['L401-same-key', 'L402-different-keys', 'L403-competing-plans'])
def test_plan_application_load_and_atomic_reads(api, record_property, mode):
    """Fifty concurrent plan writes plus25 shuffled reads retain one commit, atomic assignments and immutable replay within5s per request."""
    w = World(api, capacities=(4, 4, 2), pairs=())
    big = w.book(('t_1',), party=4)
    small = w.book(('t_2',), party=2)
    old = {r['reference']: r for r in (big, small)}
    histories = {ref: w.history(ref) for ref in old}
    closure = {'table_id': 't_1', 'from': '2030-01-01T18:00:00Z',
               'to': '2030-01-01T19:00:00Z'}
    plans = [w.post('/restaurants/r_main/replans', closure, key='load-preview-0')]
    if mode == 'competing-plans':
        plans += [w.post('/restaurants/r_main/replans', closure, key=f'load-preview-{i}')
                  for i in range(1, 50)]
    assert all(p['restaurant_revision'] == 2 for p in plans)
    before = {big['reference']: ['t_1'], small['reference']: ['t_2']}
    after = {big['reference']: ['t_2'], small['reference']: ['t_3']}
    jobs = [('write', i) for i in range(50)]+[('read', i) for i in range(25)]
    random.Random(401).shuffle(jobs)

    def call(job):
        kind, i = job
        plan = plans[i] if mode == 'competing-plans' and kind == 'write' else plans[0]
        key = 'load-apply' if mode == 'same-key' else f'load-apply-{i}'
        path = '/restaurants/r_main/replans/'+plan['plan_id']+'/apply'
        tick = time.monotonic()
        result = {'kind': kind, 'index': i, 'key': key, 'plan_id': plan['plan_id']}
        try:
            if kind == 'write':
                response = w.c.post(path, json={}, headers=w.headers(key=key), timeout=6)
            else:
                response = w.c.get('/reservations', headers=w.headers(), timeout=6)
            result.update(status=response.status_code, body=response.json())
        except (httpx.HTTPError, ValueError) as error:
            result['error'] = type(error).__name__
        result['elapsed_s'] = time.monotonic()-tick
        return result

    with ThreadPoolExecutor(max_workers=50) as pool:
        results = list(pool.map(call, jobs))
    writes = [r for r in results if r['kind'] == 'write']
    reads = [r for r in results if r['kind'] == 'read']
    counts = dict(Counter(str(r.get('status', r.get('error'))) for r in writes))
    record_property('scenario', json.dumps({'mode': mode, 'closure': closure,
                                            'old': old, 'expected_assignments': after}))
    observe(record_property, mode=mode, request_count=len(results), max_workers=50,
            write_statuses=counts, requests=results)
    assert all('error' not in r and r['elapsed_s'] <= 5 for r in results), counts
    successes = [r for r in writes if r['status'] == 201]
    assert len(successes) == 1, counts
    winner = successes[0]
    receipt = winner['body']
    assert receipt['restaurant_revision'] == 3
    for r in writes:
        if r is winner:
            continue
        if mode == 'same-key':
            assert r['status'] == 200 and r['body'] == receipt
        else:
            assert r['status'] == 409
            expected = 'stale_plan' if mode == 'competing-plans' else 'plan_already_applied'
            assert r['body']['error']['code'] == expected
    for r in reads:
        assert r['status'] == 200
        assignments = {b['reference']: b['table_ids'] for b in r['body']['reservations']}
        assert assignments == before or assignments == after, assignments
    for ref, original in old.items():
        current = w.get('/reservations/'+ref)
        assert current['table_ids'] == after[ref]
        assert current['revision'] == original['revision']+1
        for field in ('reference', 'reservation_id', 'party_size', 'starts_at', 'ends_at',
                      'starts_at_local', 'accepted_terms', 'created_at', 'status'):
            assert current[field] == original[field], field
        history = w.history(ref)
        assert history['entries'][:-1] == histories[ref]['entries']
        assert history['entries'][-1]['event'] == 'reassigned'
        assert history['entries'][-1]['plan_id'] == winner['plan_id']
    w.post('/reservations/'+big['reference']+'/cancel', {}, status=200)
    path = '/restaurants/r_main/replans/'+winner['plan_id']+'/apply'
    assert w.post(path, {}, key=winner['key'], status=200) == receipt
