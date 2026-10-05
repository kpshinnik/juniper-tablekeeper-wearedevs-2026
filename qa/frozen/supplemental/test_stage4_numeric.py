"""Exact planning cancellations can have compact input AND output."""
from decimal import Decimal
import json
import time

import httpx
import pytest


@pytest.mark.parametrize('paired', [False, True], ids=['N401-unused-zero', 'N402-pair-to-single'])
def test_plan_compact_huge_integer_cancellation(record_property, paired):
    """Capacity and party1e100000000 cancel exactly to zero unused seats; preview/apply/replay stay compact and responsive."""
    fixture = {'users': [{'id': 'guest', 'email': 'guest@exact.test',
                         'password': 'synthetic-password', 'display_name': 'Guest'}],
               'reservations': [],
               'restaurants': [{'id': 'exact', 'name': 'Exact Garden', 'timezone': 'UTC',
                   'manager_user_ids': ['guest'], 'slot_minutes': 60,
                   'reservation_duration_minutes': 60, 'cancellation_cutoff_minutes': 0,
                   'opening_hours': [{'weekday': d, 'opens': '18:00', 'closes': '22:00'}
                                     for d in 'mon tue wed thu fri sat sun'.split()],
                   'tables': [{'id': 'a', 'label': 'Large', 'capacity': '__NUMBER__'},
                              {'id': 'b', 'label': 'Small', 'capacity': 4}],
                   'combinable': [['a', 'b']]}]}
    observed = {'paired': paired, 'exponent': 100000000, 'requests': []}

    def decode(response):
        return json.loads(response.content, parse_int=Decimal, parse_float=Decimal)

    with httpx.Client(base_url='http://tablekeeper:8080', timeout=6, trust_env=False) as c:
        reset = json.dumps(fixture).replace('"__NUMBER__"', '1e100000000')
        assert c.post('/_test/reset', content=reset, headers={'Content-Type': 'application/json'}, timeout=10).status_code == 204
        login = c.post('/auth/login', json={'email': 'guest@exact.test', 'password': 'synthetic-password'})
        assert login.status_code == 200
        token = login.json()['token']

        def call(method, path, status, key=None, raw=None):
            tick = time.monotonic()
            response = None
            entry = {'method': method, 'path': path, 'expected': status}
            try:
                response = c.request(method, path, content=raw,
                    headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json',
                             **({'Idempotency-Key': key} if key else {})})
                entry.update(status=response.status_code, bytes=len(response.content))
            except httpx.HTTPError as error:
                entry['error'] = type(error).__name__
            entry['elapsed_s'] = time.monotonic()-tick
            observed['requests'].append(entry)
            record_property('observed', json.dumps(observed))
            assert response is not None, entry
            assert response.status_code == status and entry['elapsed_s'] <= 5, entry
            assert len(response.content) < 10000, 'This exact synthetic result needs no expanded decimal gap'
            return response

        body = {'restaurant_id': 'exact', 'table_ids': ['a', 'b'] if paired else ['a'],
                'starts_at_local': '2030-01-01T18:00', 'party_size': '__NUMBER__'}
        raw = json.dumps(body).replace('"__NUMBER__"', '1e100000000')
        original = decode(call('POST', '/reservations', 201, key='original', raw=raw))
        reference = original['reference']
        history = decode(call('GET', '/reservations/'+reference+'/history', 200))
        closure = json.dumps({'table_id': 'b', 'from': '2030-01-01T18:00:00Z',
                              'to': '2030-01-01T19:00:00Z'})
        plan = decode(call('POST', '/restaurants/exact/replans', 201, key='preview', raw=closure))
        assert plan['restaurant_revision'] == 1 and plan['unused_seats'] == 0
        assert plan['moved_count'] == int(paired)
        assert plan['assignments'] == [{'reference': reference, 'table_ids': ['a'], 'changed': paired}]
        assert decode(call('GET', '/reservations/'+reference, 200)) == original
        assert decode(call('GET', '/reservations/'+reference+'/history', 200)) == history
        path = '/restaurants/exact/replans/'+plan['plan_id']+'/apply'
        applied = decode(call('POST', path, 201, key='apply', raw='{}'))
        assert applied['restaurant_revision'] == 2
        current = decode(call('GET', '/reservations/'+reference, 200))
        assert current['table_ids'] == ['a'] and current['revision'] == original['revision']+int(paired)
        for field in ('party_size', 'starts_at', 'ends_at', 'accepted_terms', 'created_at', 'reference', 'reservation_id'):
            assert current[field] == original[field], field
        later = decode(call('GET', '/reservations/'+reference+'/history', 200))
        if paired:
            assert later['entries'][:-1] == history['entries']
            assert later['entries'][-1]['event'] == 'reassigned'
        else:
            assert later == history
        assert decode(call('POST', '/reservations', 200, key='original', raw=raw)) == original
        assert decode(call('POST', path, 200, key='apply', raw='{}')) == applied
        assert decode(call('GET', '/health', 200))['status'] == 'ok'
