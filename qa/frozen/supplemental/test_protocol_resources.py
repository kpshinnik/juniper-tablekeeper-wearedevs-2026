"""Bounded HTTP robustness checks; only run in this runner's disposable service.

The large-exponent case runs last because a broken implementation may monopolize
its service process. The runner must constrain that service to 2 CPU / 2 GiB and
remove it afterward. No public target and no product imports are used.
"""
import json
import time

import httpx
import pytest


@pytest.fixture
def api():
    with httpx.Client(base_url='http://tablekeeper:8080', timeout=8, trust_env=False) as c:
        fixture = {
            'reservations': [],
            'users': [{'id': 'resource-guest', 'email': 'guest@resource.test',
                       'password': 'synthetic-resource-password', 'display_name': 'Guest'}],
            'restaurants': [{'id': 'resource-restaurant', 'name': 'Resource test',
                             'timezone': 'UTC', 'slot_minutes': 30,
                             'reservation_duration_minutes': 60,
                             'cancellation_cutoff_minutes': 0,
                             'opening_hours': [{'weekday': day, 'opens': '00:00', 'closes': '23:59'}
                                               for day in ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')],
                             'tables': [{'id': 'one', 'label': 'One', 'capacity': 4}]}],
        }
        assert c.post('/_test/reset', json=fixture).status_code == 204
        login = c.post('/auth/login', json={'email': 'guest@resource.test',
                                          'password': 'synthetic-resource-password'})
        assert login.status_code == 200
        yield c, login.json()['token']


@pytest.mark.parametrize('method', ['TRACE', 'CONNECT', 'PROPFIND', 'REPORT', 'SEARCH', 'LINK', 'UNLINK'])
def test_H001_unknown_http_method_is_bounded_and_nonmutating(api, record_property, method):
    """An unexpected HTTP method cannot produce 5xx or mutate application state."""
    c, _ = api
    before = c.get('/_test/export')
    assert before.status_code == 200
    started = time.monotonic()
    response = c.request(method, '/health')
    duration = time.monotonic() - started
    after = c.get('/_test/export')
    same = after.status_code == 200 and after.json() == before.json()
    record_property('observed', json.dumps({'method': method, 'status': response.status_code,
                                          'elapsed_s': duration, 'state_unchanged': same}))
    assert response.status_code < 500 and duration <= 5 and same


def test_H002_large_exponent_cannot_monopolize_service(api, record_property):
    """A tiny valid integer payload above table capacity is rejected promptly without blocking health."""
    c, token = api
    before = c.get('/_test/export')
    assert before.status_code == 200
    # A compact, valid JSON integer value. Materializing 100 million decimal
    # digits is unnecessary to compare it with a four-seat table's capacity.
    payload = ('{"restaurant_id":"resource-restaurant","table_id":"one",'
               '"starts_at_local":"2030-01-01T18:00","party_size":1e100000000}')
    started = time.monotonic()
    observed = {'payload_bytes': len(payload), 'exponent': 100000000,
                'status': None, 'health_status': None, 'state_unchanged': None}
    try:
        response = c.post('/reservations', content=payload,
                          headers={'Authorization': 'Bearer ' + token,
                                   'Idempotency-Key': 'bounded-integer',
                                   'Content-Type': 'application/json'}, timeout=6)
        observed['status'] = response.status_code
        observed['error_code'] = response.json().get('error', {}).get('code')
    except httpx.HTTPError as exc:
        observed['request_error_type'] = type(exc).__name__
    finally:
        observed['elapsed_s'] = time.monotonic() - started
    try:
        health_started = time.monotonic()
        health = c.get('/health', timeout=6)
        observed['health_status'] = health.status_code
        observed['health_elapsed_s'] = time.monotonic() - health_started
        after = c.get('/_test/export', timeout=11)
        observed['state_unchanged'] = after.status_code == 200 and after.json() == before.json()
    except httpx.HTTPError as exc:
        observed['probe_error_type'] = type(exc).__name__
    record_property('observed', json.dumps(observed))
    assert observed['status'] == 422 and observed['elapsed_s'] <= 5
    assert observed['health_status'] == 200 and observed['health_elapsed_s'] <= 5
    assert observed['state_unchanged']
