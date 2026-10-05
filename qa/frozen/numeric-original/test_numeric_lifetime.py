"""Verifier-owned exact-number lifetime checks derived from AC-R306 N001–N008.

The oracle uses Decimal parsing only, never the product codec, floats, enormous
powers or a new contract limit. Stage-dependent cases are collected explicitly.
"""
from decimal import Decimal
import json
import os
import sys
import time
import uuid

import httpx
import pytest

STAGE = int(os.environ.get('STAGE_UNDER_TEST', '3'))
sys.setrecursionlimit(max(20000, sys.getrecursionlimit()))  # Independent QA decoder only.


class Number(str):
    """An explicitly supplied JSON number token, not a string value."""


def wire(value):
    if isinstance(value, (Number, Decimal)):
        return str(value)
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k, ensure_ascii=True)+':'+wire(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(wire(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def decoded(response):
    return json.loads(response.content, parse_float=Decimal, parse_int=Decimal)


def fixture(capacity=4, second=4):
    r = {'id': 'numeric', 'name': 'Exact Garden', 'timezone': 'UTC', 'slot_minutes': 30,
         'reservation_duration_minutes': 60, 'cancellation_cutoff_minutes': 0,
         'opening_hours': [{'weekday': d, 'opens': '17:00', 'closes': '23:00'} for d in 'mon tue wed thu fri sat sun'.split()],
         'tables': [{'id': 'a', 'label': 'Window', 'capacity': capacity},
                    {'id': 'b', 'label': 'Garden', 'capacity': second}]}
    if STAGE >= 2:
        r['combinable'] = [['b', 'a']]
    if STAGE >= 3:
        r['manager_user_ids'] = ['guest']
    return {'users': [{'id': 'guest', 'email': 'guest@numeric.test', 'password': 'synthetic-numeric-password', 'display_name': 'Guest'}],
            'restaurants': [r], 'reservations': []}


def headers(token=None, key=None):
    h = {'Content-Type': 'application/json'}
    if token:
        h['Authorization'] = 'Bearer ' + token
    if key is not None:
        h['Idempotency-Key'] = key
    return h


def request(c, method, path, token=None, key=None, body=None, raw=None, limit=5):
    tick = time.monotonic()
    r = c.request(method, path, content=raw if raw is not None else (wire(body) if body is not None else None),
                  headers=headers(token, key), timeout=limit+1)
    assert time.monotonic()-tick <= limit, (method, path, 'contract duration exceeded')
    return r


def reset(c, data):
    r = request(c, 'POST', '/_test/reset', body=data, limit=10)
    assert r.status_code == 204, r.text[:1000]
    r = request(c, 'POST', '/auth/login', body={'email': 'guest@numeric.test', 'password': 'synthetic-numeric-password'})
    assert r.status_code == 200, r.text[:1000]
    return decoded(r)['token']


@pytest.fixture
def world():
    with httpx.Client(base_url='http://tablekeeper:8080', trust_env=False, timeout=6) as c:
        yield c, reset(c, fixture())


def export(c):
    r = request(c, 'GET', '/_test/export', limit=10)
    assert r.status_code == 200, r.text[:1000]
    return r


def same(c, before):
    assert decoded(export(c)) == decoded(before)


def error(r, code, status=422):
    assert r.status_code == status, r.text[:1000]
    assert decoded(r)['error']['code'] == code


def body(party=2, table='a', **kw):
    value = {'restaurant_id': 'numeric', 'table_id': table, 'starts_at_local': '2030-01-01T18:00', 'party_size': party}
    if 'table_ids' in kw:
        value.pop('table_id')
    value.update(kw)
    return value


def create(c, token, value=None, key=None):
    r = request(c, 'POST', '/reservations', token, key or str(uuid.uuid4()), body=value or body())
    assert r.status_code == 201, r.text[:1000]
    return r


def replace(c, saved):
    assert request(c, 'POST', '/_test/reset', body={'users': [], 'restaurants': [], 'reservations': []}, limit=10).status_code == 204
    assert request(c, 'POST', '/_test/import', raw=saved.content, limit=10).status_code == 204
    same(c, saved)


@pytest.mark.parametrize('operation', ['create', 'patch', 'moves'], ids=['R2N001-create', 'R2N001-patch', 'R2N001-moves'])
def test_huge_positive_refusal_health_atomicity_and_reusable_key(world, record_property, operation):
    """1e100000000 exceeds a four-seat capacity, returns exact 422 within 5s, preserves state/health and leaves failed keys reusable."""
    c, token = world
    a = decoded(create(c, token)) if operation != 'create' else None
    before = export(c)
    if operation == 'create':
        path, method, value = '/reservations', 'POST', body(Number('1e100000000'))
    elif operation == 'patch':
        path, method, value = '/reservations/'+a['reference'], 'PATCH', {'party_size': Number('1e100000000')}
    else:
        path, method, value = '/reservation-moves', 'POST', {'moves': [{'reference': a['reference'], 'party_size': Number('1e100000000')}]}
    start = time.monotonic()
    refused = request(c, method, path, token, 'huge-refusal', body=value)
    record_property('huge_request_s', time.monotonic()-start)
    error(refused, 'party_exceeds_capacity')
    health = request(c, 'GET', '/health')
    assert health.status_code == 200 and decoded(health) == {'status': 'ok'}
    same(c, before)
    good = body() if operation == 'create' else ({'party_size': 1} if operation == 'patch' else {'moves': [{'reference': a['reference'], 'party_size': 1}]})
    r = request(c, method, path, token, 'huge-refusal', body=good)
    assert r.status_code == (200 if operation == 'patch' else 201), r.text[:1000]


@pytest.mark.parametrize('exponent', [400, 5000, 100000000], ids=['R2N002-e400', 'R2N002-e5000', 'R2N002-e100000000'])
def test_valid_large_capacity_entire_http_lifetime(world, record_property, exponent):
    """Valid arbitrary positive capacity and party values remain exact through output, selection, no-op, real amendments, list, replacement import, cancellation and original retry."""
    c, _ = world
    value = Number('1e'+str(exponent)); equivalent = Number('10e'+str(exponent-1))
    token = reset(c, fixture(value))
    detail = request(c, 'GET', '/restaurants/numeric')
    assert detail.status_code == 200 and decoded(detail)['tables'][0]['capacity'] == Decimal(value)
    party_query = '1' + '0'*exponent if exponent <= 5000 else '1'
    available = request(c, 'GET', '/availability?restaurant_id=numeric&date=2030-01-01&party_size='+party_query)
    assert available.status_code == 200
    slot = next(s for s in decoded(available)['slots'] if s['starts_at_local'].endswith('18:00'))
    assert 'a' in slot['available_table_ids']
    first = create(c, token, body(value), 'large-lifetime'); original = decoded(first); ref = original['reference']
    assert original['party_size'] == Decimal(value)
    if STAGE >= 3:
        assert original['accepted_terms']['capacities']['a'] == Decimal(value)
    no_op_before = export(c)
    no_op = request(c, 'PATCH', '/reservations/'+ref, token, body={'party_size': equivalent})
    assert no_op.status_code == 200 and decoded(no_op) == original
    same(c, no_op_before)
    for count in (1, value):
        r = request(c, 'PATCH', '/reservations/'+ref, token, body={'party_size': count})
        assert r.status_code == 200 and decoded(r)['party_size'] == Decimal(str(count))
    before = export(c)
    too_large = request(c, 'POST', '/reservations', token, 'capacity-edge', body=body(Number('2e'+str(exponent)), table='a', starts_at_local='2030-01-01T20:00'))
    error(too_large, 'party_exceeds_capacity'); same(c, before)
    saved = export(c); replace(c, saved)
    current = request(c, 'GET', '/reservations/'+ref, token)
    listed = request(c, 'GET', '/reservations', token)
    assert current.status_code == listed.status_code == 200
    assert decoded(listed)['reservations'] == [decoded(current)]
    cancel = request(c, 'POST', '/reservations/'+ref+'/cancel', token, body={})
    assert cancel.status_code == 200 and decoded(cancel)['status'] == 'cancelled'
    final = export(c)
    replay = request(c, 'POST', '/reservations', token, 'large-lifetime', body=body(equivalent))
    assert replay.status_code == 200 and decoded(replay) == original
    same(c, final)
    record_property('value_exponent', exponent)
    record_property('response_bytes', len(first.content))
    record_property('export_bytes', len(saved.content))


NUMBERS = [('1e100000000', '10e99999999', '2e100000000'),
           ('1e-100000000', '10e-100000001', '2e-100000000'),
           ('-1e100000000', '-10e99999999', '1e100000000'),
           ('0e100000000', '-0e-100000000', '1e-100000000')]


@pytest.mark.parametrize('left,equal,different', NUMBERS, ids=['R2N005-huge','R2N005-tiny','R2N005-negative','R2N005-zero'])
def test_exact_unknown_numeric_identity_deep_receipt(world, left, equal, different):
    """Deep unknown huge/tiny/negative/zero JSON numbers compare mathematically, retain distinct alternatives, and preserve original receipts across mutations/import."""
    c, token = world
    base = wire(body())[:-1]
    def payload(number):
        return base + ',"ignored":' + '[{"雪":'*600 + number + '}]'*600 + '}'
    first = request(c, 'POST', '/reservations', token, 'unknown-number', raw=payload(left))
    assert first.status_code == 201; original = decoded(first); ref = original['reference']
    same_before = export(c)
    equal_reply = request(c, 'POST', '/reservations', token, 'unknown-number', raw=payload(equal))
    assert equal_reply.status_code == 200 and decoded(equal_reply) == original
    same(c, same_before)
    error(request(c, 'POST', '/reservations', token, 'unknown-number', raw=payload(different)), 'idempotency_key_reuse', 409)
    same(c, same_before)
    assert request(c, 'PATCH', '/reservations/'+ref, token, body={'party_size': 1}).status_code == 200
    saved = export(c); replace(c, saved)
    assert request(c, 'POST', '/reservations/'+ref+'/cancel', token, body={}).status_code == 200
    cancelled = export(c)
    replay = request(c, 'POST', '/reservations', token, 'unknown-number', raw=payload(equal))
    assert replay.status_code == 200 and decoded(replay) == original
    same(c, cancelled)


@pytest.mark.parametrize('other', [1, 10**399], ids=['R2N007-wide-gap','R2N007-adjacent-exponents'])
def test_exact_pair_sum_and_adjacent_capacity_boundary(world, other):
    """Pair capacity equals exact 1e400+1 or 1e400+1e399; sum+1 fails without mutation and sum succeeds through receipt/import/cancel."""
    c, _ = world
    token = reset(c, fixture(Number('1e400'), other))
    capacity = 10**400 + other
    reply = request(c, 'GET', '/availability?restaurant_id=numeric&date=2030-01-01&party_size='+str(capacity))
    assert reply.status_code == 200
    slot = next(s for s in decoded(reply)['slots'] if s['starts_at_local'].endswith('18:00'))
    assert slot['available_table_ids'] == []
    assert slot['available_options'] == [{'table_ids': ['b','a'], 'capacity': Decimal(capacity)}]
    before = export(c)
    error(request(c, 'POST', '/reservations', token, 'sum-edge', body=body(capacity+1, table_ids=['a','b'])), 'party_exceeds_capacity')
    same(c, before)
    first = create(c, token, body(capacity, table_ids=['a','b']), 'sum-edge')
    original = decoded(first)
    assert original['party_size'] == capacity and original['table_ids'] == ['b','a']
    saved = export(c); replace(c, saved)
    assert request(c, 'POST', '/reservations/'+original['reference']+'/cancel', token, body={}).status_code == 200
    cancelled = export(c)
    replay = request(c, 'POST', '/reservations', token, 'sum-edge', body=body(capacity, table_ids=['a','b']))
    assert replay.status_code == 200 and decoded(replay) == original
    same(c, cancelled)


def policy(**updates):
    r = fixture()['restaurants'][0]
    p = {k:r[k] for k in ('slot_minutes','reservation_duration_minutes','cancellation_cutoff_minutes','opening_hours')}
    p.update(effective_from='2030-01-01', capacities={'a':4,'b':4})
    p.update(updates)
    return p


FINITE = [('policy', field) for field in ['slot_minutes','reservation_duration_minutes','cancellation_cutoff_minutes','capacities']]
FINITE += [('series', field) for field in ['count','interval_weeks']]


@pytest.mark.parametrize('endpoint,field', FINITE, ids=['R2N003-'+a+'-'+b for a,b in FINITE])
def test_finite_fields_reject_huge_before_expansion(world, endpoint, field):
    """Explicitly finite policy and series fields reject huge exact integers promptly, without version/allocation/receipt mutation; key stays reusable."""
    c, token = world
    if endpoint == 'policy':
        path = '/restaurants/numeric/policies'; good = policy(); value = dict(good)
        value[field] = {'a':Number('1e100000000'),'b':4} if field == 'capacities' else Number('1e100000000')
    else:
        anchor = decoded(create(c, token))
        path = '/series'; good = {'anchor_reference':anchor['reference'],'count':2,'interval_weeks':1}; value = dict(good)
        value[field] = Number('1e100000000')
    before = export(c)
    error(request(c, 'POST', path, token, 'finite-field', body=value), 'validation_failed'); same(c, before)
    r = request(c, 'POST', path, token, 'finite-field', body=good)
    assert r.status_code == 201


@pytest.mark.parametrize('past', [False, True], ids=['R2N004-future','R2N004-cutoff'])
def test_unbounded_revision_precedes_cutoff_and_result_validation(world, past):
    """Valid huge expected_revision is stale409 before cutoff/invalid resulting fields; no arbitrary maximum or mutation is allowed."""
    c, token = world
    first = decoded(create(c, token, body(starts_at_local='2000-01-01T18:00' if past else '2030-01-01T18:00')))
    before = export(c)
    request_body = {'expected_revision':Number('1e100000000'),'party_size':False}
    error(request(c, 'PATCH', '/reservations/'+first['reference'], token, body=request_body), 'stale_revision', 409)
    same(c, before)
    for invalid in (True, Number('1e-100000000'), Number('-1e100000000'), 0):
        error(request(c, 'PATCH', '/reservations/'+first['reference'], token, body={'expected_revision':invalid}), 'validation_failed')
        same(c, before)
    if not past:
        r = request(c, 'PATCH', '/reservations/'+first['reference'], token, body={'expected_revision':Number('1.00'), 'party_size':2})
        assert r.status_code == 200 and decoded(r) == first
        same(c, before)


@pytest.mark.parametrize('operation', ['moves'] + (['policy','series'] if STAGE >= 3 else []), ids=lambda s:'R2N006-'+s)
def test_additional_write_receipts_retain_huge_unknown_equality(world, operation):
    """Batch/policy/series unknown huge numbers survive copy, original response, replacement import and exact replay without repeated mutation."""
    c, token = world
    anchor = decoded(create(c, token))
    if operation == 'moves':
        path = '/reservation-moves'; value = {'moves':[{'reference':anchor['reference'],'party_size':1}]}
    elif operation == 'policy':
        path = '/restaurants/numeric/policies'; value = policy()
    else:
        path = '/series'; value = {'anchor_reference':anchor['reference'],'count':2,'interval_weeks':1}
    value['ignored'] = Number('1e100000000')
    first = request(c, 'POST', path, token, 'all-receipts', body=value)
    assert first.status_code == 201, first.text[:1000]
    original = decoded(first); saved = export(c); replace(c, saved)
    assert request(c, 'POST', '/reservations/'+anchor['reference']+'/cancel', token, body={}).status_code == 200
    now = export(c); value['ignored'] = Number('10e99999999')
    replay = request(c, 'POST', path, token, 'all-receipts', body=value)
    assert replay.status_code == 200 and decoded(replay) == original
    same(c, now)
    value['ignored'] = Number('2e100000000')
    error(request(c, 'POST', path, token, 'all-receipts', body=value), 'idempotency_key_reuse', 409)
    same(c, now)


def test_R2N008_deep_preparation_and_batch_commit_boundary(world):
    """A deep Unicode/numeric batch prepares original receipts atomically; later invalid item rolls back every booking and leaves the key reusable."""
    c, token = world
    a = decoded(create(c, token, body(table='a')))
    b = decoded(create(c, token, body(table='b')))
    unknown = '[{"雪":'*2000 + '1e100000000' + '}]'*2000
    before = export(c)
    value = {'moves':[{'reference':a['reference'],'table_id':'b'},
                      {'reference':b['reference'],'table_id':'a','party_size':Number('1e100000000')}]}
    raw = wire(value)[:-1] + ',"ignored":' + unknown + ',"text":"\\ud800"}'
    refused = request(c, 'POST', '/reservation-moves', token, 'deep-atomic', raw=raw)
    error(refused, 'party_exceeds_capacity'); same(c, before)
    value['moves'][1]['party_size'] = 2
    raw = wire(value)[:-1] + ',"ignored":' + unknown + ',"text":"\\ud800"}'
    first = request(c, 'POST', '/reservation-moves', token, 'deep-atomic', raw=raw)
    assert first.status_code == 201, first.text[:1000]
    original = decoded(first)
    for r in original['reservations']:
        readback = request(c, 'GET', '/reservations/'+r['reference'], token)
        assert readback.status_code == 200 and decoded(readback) == r
    assert [r['table_id'] for r in original['reservations']] == ['b','a']
    saved = export(c); replace(c, saved)
    replay = request(c, 'POST', '/reservation-moves', token, 'deep-atomic', raw=raw.replace('1e100000000','10e99999999'))
    assert replay.status_code == 200 and decoded(replay) == original
    same(c, saved)


# Applicability is explicit collection, not reported as skipped or passed.
if STAGE < 2:
    del test_exact_pair_sum_and_adjacent_capacity_boundary
if STAGE < 3:
    del test_finite_fields_reject_huge_before_expansion
    del test_unbounded_revision_precedes_cutoff_and_result_validation
