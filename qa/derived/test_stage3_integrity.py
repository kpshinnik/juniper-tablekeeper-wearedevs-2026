"""Bind the pre-handoff D333/D334 obligations to schema3's opaque carrier.

HTTP only: no product modules, validation or oracle code are imported. Native
operation journal stays unchanged in every corruption; only the outer digest is
recomputed. Valid controls and exact destination nonmutation are mandatory.
"""
import copy
import hashlib
import json

import pytest

from derived.test_stage3 import (world3, fixture, reset, policy, publish, booking,
                                adopt, patch, series, current, history, PASSWORD)
from derived.test_stage1 import headers, assert_error, snapshot
from adapters.test_string_payload import payload, seal


def exported(c):
    r = c.get('/_test/export', timeout=10)
    assert r.status_code == 200
    envelope = r.json()
    decoded = payload(envelope)
    assert decoded['schema'] == 3, 'QA schema3 selector applicability'
    assert isinstance(decoded['restaurant_revisions'], dict)
    return envelope, decoded


def revision(c, rid='r'):
    return exported(c)[1]['restaurant_revisions'][rid]


def test_D333_atomic_operation_counter_sequence(world3, record_property):
    """Reset seeds count0; each actual operation increments once, noops/replays/rejects never do."""
    c, _ = world3
    fx = fixture()
    other = copy.deepcopy(fx['restaurants'][0]); other['id'] = 'other-r'
    other['tables'] = [{'id': 'x', 'label': 'X', 'capacity': 100}]
    other['combinable'] = []
    fx['restaurants'].append(other)
    fx['reservations'] = [{'id': 'seed', 'reference': 'SEED01', 'user_id': 'diner',
        'restaurant_id': 'r', 'table_id': 'c', 'starts_at_local': '2000-01-01T10:00', 'party_size': 2}]
    reset(c, fx)
    tok = {who: c.post('/auth/login', json={'email': who+'@stage3.test', 'password': PASSWORD}).json()['token']
           for who in ('diner', 'manager', 'other')}
    observations = []
    def check(name, expected):
        got = revision(c)
        observations.append({'operation': name, 'expected': expected, 'observed': got})
        assert got == expected, (name, expected, got)
    check('reset-seeds', 0)
    assert current(c, tok['diner'], 'SEED01')['revision'] == 1
    body, anchor = booking(c, tok, key='counter-create'); check('create', 1)
    p = policy('2040-01-01')
    old = current(c, tok['diner'], anchor['reference'])
    old_history = history(c, tok['diner'], anchor['reference'])
    receipt_policy = publish(c, tok, p, key='counter-policy'); check('policy', 2)
    assert current(c, tok['diner'], anchor['reference']) == old
    assert history(c, tok['diner'], anchor['reference']) == old_history
    sb, sr = adopt(c, tok, anchor['reference'], key='counter-series'); check('adoption', 3)
    assert current(c, tok['diner'], anchor['reference']) == old
    sid = sr['series_id']; refs = [x['reference'] for x in sr['occurrences']]
    assert patch(c, tok, refs[1], {'party_size': 3}).status_code == 200; check('patch', 4)
    assert series(c, tok, sid)['revision'] == 2
    assert c.post('/reservations/'+refs[2]+'/cancel', headers=headers(tok['diner'])).status_code == 200
    check('cancel', 5)
    mb = {'moves': [{'reference': refs[0], 'party_size': 4}, {'reference': refs[1], 'party_size': 5}]}
    mr = c.post('/reservation-moves', json=mb, headers=headers(tok['diner'], 'counter-moves'))
    assert mr.status_code == 201; check('batch-two-members', 6)
    actual = series(c, tok, sid)
    assert actual['revision'] == 4
    assert [o['exception'] for o in actual['occurrences']] == [True, True, False]
    unchanged = copy.deepcopy(actual)
    assert patch(c, tok, refs[0], {'party_size': 4}).status_code == 200; check('noop-patch', 6)
    noops = {'moves': [{'reference': refs[0]}, {'reference': refs[1]}]}
    assert c.post('/reservation-moves', json=noops, headers=headers(tok['diner'], 'noop-moves')).status_code == 201
    check('noop-batch', 6)
    assert c.post('/reservations/'+refs[2]+'/cancel', headers=headers(tok['diner'])).status_code == 200
    check('repeat-cancel', 6)
    for path, request, key, original in [('/reservations', body, 'counter-create', anchor),
            ('/restaurants/r/policies', p, 'counter-policy', receipt_policy),
            ('/series', sb, 'counter-series', sr), ('/reservation-moves', mb, 'counter-moves', mr.json())]:
        who = 'manager' if '/policies' in path else 'diner'
        replay = c.post(path, json=request, headers=headers(tok[who], key))
        assert replay.status_code == 200 and replay.json() == original
        check('original-replay-'+key, 6)
    assert series(c, tok, sid) == unchanged
    for name, request, ref, status, code in [('validation', {'party_size': 0}, refs[0], 422, 'validation_failed'),
            ('stale', {'expected_revision': 1, 'party_size': 0}, refs[0], 409, 'stale_revision'),
            ('cutoff', {'party_size': 3}, 'SEED01', 409, 'cutoff_passed')]:
        before = snapshot(c)
        assert_error(patch(c, tok, ref, request), status, code)
        assert snapshot(c) == before; check('reject-'+name, 6)
    _, b = booking(c, tok, key='blocked-anchor', table='b'); check('new-anchor', 7)
    booking(c, tok, key='blocker', table='b', date='2030-01-08'); check('future-blocker', 8)
    before = snapshot(c)
    rejected = c.post('/series', json={'anchor_reference': b['reference'], 'count': 3, 'interval_weeks': 1},
                      headers=headers(tok['diner'], 'failed-series'))
    assert_error(rejected, 409, 'table_unavailable'); assert snapshot(c) == before
    check('reject-adoption', 8)
    assert revision(c, 'other-r') == 0
    response = c.post('/reservations', json={'restaurant_id': 'other-r', 'table_id': 'x',
        'starts_at_local': '2030-01-01T18:00', 'party_size': 2}, headers=headers(tok['diner'], 'other-r'))
    assert response.status_code == 201 and revision(c, 'other-r') == 1
    check('other-restaurant-isolation', 8)
    reset(c, fx); check('replacement-reset', 0)
    record_property('observed', json.dumps(observations))


def rich_state(c, tok):
    """Two independent series share original dates, but use disjoint seating."""
    publish(c, tok, policy('2030-01-08'), key='policy-one')
    publish(c, tok, policy('2030-01-08', reservation_duration_minutes=120), key='policy-two')
    _, a = booking(c, tok, key='pair-anchor', table_ids=['a', 'b'])
    _, b = booking(c, tok, key='single-anchor', table='c')
    _, sa = adopt(c, tok, a['reference'], key='series-a')
    _, sb = adopt(c, tok, b['reference'], key='series-b')
    refs = [o['reference'] for o in sa['occurrences']]
    assert patch(c, tok, refs[1], {'party_size': 3}).status_code == 200
    assert patch(c, tok, refs[1], {'party_size': 2}).status_code == 200
    assert c.post('/reservations/'+refs[2]+'/cancel', headers=headers(tok['diner'])).status_code == 200
    moves = {'moves': [{'reference': refs[0], 'party_size': 4},
                       {'reference': sb['occurrences'][0]['reference'], 'party_size': 3}]}
    assert c.post('/reservation-moves', json=moves, headers=headers(tok['diner'], 'batch')).status_code == 201
    assert c.post('/reservations/'+refs[0]+'/cancel', headers=headers(tok['diner'])).status_code == 200
    return {'a': sa['series_id'], 'b': sb['series_id'], 'refs': refs,
            'other_ref': sb['occurrences'][0]['reference']}


CORRUPTIONS = ['policy-version', 'policy-capacity', 'policy-date', 'policy-zero',
    'current-terms', 'current-end', 'history-seq', 'history-time', 'history-terminal',
    'history-revision-low', 'history-revision-high', 'history-terms', 'history-field-order',
    'history-linkage', 'series-owner', 'series-duplicate-reference', 'series-index',
    'series-missing-member', 'series-anchor', 'original-date', 'series-interval',
    'series-revision-low', 'series-revision-high', 'permanent-exception',
    'cancel-erases-exception', 'cancel-invents-exception', 'policy-receipt',
    'series-receipt', 'batch-receipt', 'receipt-owner', 'receipt-body',
    'restaurant-revision-low', 'restaurant-revision-high']


def corrupt(s, ids, name):
    a = s['series'][ids['a']]; refs = ids['refs']
    r = s['reservations'][refs[1]]; h = s['histories'][refs[1]]
    receipt = lambda key: next(x for x in s['receipts'] if x['key'] == key)
    if name == 'policy-version': s['policies']['r'][1]['policy_version'] = 1
    elif name == 'policy-capacity': del s['policies']['r'][0]['capacities']['a']
    elif name == 'policy-date': s['policies']['r'][0]['effective_from'] = '2030-02-30'
    elif name == 'policy-zero': s['reservations'][refs[0]]['accepted_terms']['capacities']['a'] = 99
    elif name == 'current-terms': r['accepted_terms']['policy_version'] = 1
    elif name == 'current-end': r['ends_at'] = '2030-01-08T20:30:00+00:00'
    elif name == 'history-seq': h[1]['seq'] = 3
    elif name == 'history-time': h[1]['at'] = '2000-01-01T00:00:00+00:00'
    elif name == 'history-terminal': s['histories'][refs[0]].append(copy.deepcopy(s['histories'][refs[0]][0]))
    elif name == 'history-revision-low': h[-1]['revision'] = 1
    elif name == 'history-revision-high': h[-1]['revision'] = 99
    elif name == 'history-terms': h[0]['accepted_terms']['policy_version'] = 0
    elif name == 'history-field-order': h[0]['changes'].reverse()
    elif name == 'history-linkage': h[1]['changes'][0]['from'] = 77
    elif name == 'series-owner': a['user_id'] = 'other'
    elif name == 'series-duplicate-reference': a['occurrences'][1]['reference'] = refs[0]
    elif name == 'series-index': a['occurrences'][1]['index'] = 0
    elif name == 'series-missing-member': a['occurrences'].pop()
    elif name == 'series-anchor': a['occurrences'][0]['reference'] = ids['other_ref']
    elif name == 'original-date': a['occurrences'][1]['scheduled_date'] = '2030-01-09'
    elif name == 'series-interval': a['interval_weeks'] = 2
    elif name == 'series-revision-low': a['revision'] = 1
    elif name == 'series-revision-high': a['revision'] += 1
    elif name == 'permanent-exception': a['occurrences'][1]['exception'] = False
    elif name == 'cancel-erases-exception': a['occurrences'][0]['exception'] = False
    elif name == 'cancel-invents-exception': a['occurrences'][2]['exception'] = True
    elif name == 'policy-receipt': receipt('policy-one')['response']['policy_version'] = 2
    elif name == 'series-receipt': receipt('series-a')['response']['occurrences'].reverse()
    elif name == 'batch-receipt': receipt('batch')['response']['reservations'].reverse()
    elif name == 'receipt-owner': receipt('series-a')['user_id'] = 'other'
    elif name == 'receipt-body': receipt('series-a')['body']['count'] = 4
    elif name == 'restaurant-revision-low': s['restaurant_revisions']['r'] -= 1
    elif name == 'restaurant-revision-high': s['restaurant_revisions']['r'] += 1
    else: raise AssertionError(name)


@pytest.mark.parametrize('mutation', CORRUPTIONS, ids=['D334-'+x for x in CORRUPTIONS])
def test_D334_checksum_valid_semantic_integrity(world3, mutation, record_property):
    """Authentic journal and valid controls prove corrupted native histories/series/counters cannot be imported."""
    c, tok = world3; ids = rich_state(c, tok)
    original, decoded = exported(c)
    assert c.post('/_test/import', json=original, timeout=10).status_code == 204
    assert c.get('/_test/export').json() == original
    broken = copy.deepcopy(original); altered = copy.deepcopy(decoded)
    corrupt(altered, ids, mutation)
    assert altered != decoded, 'QA mutation must change its selected value'
    assert altered['audit'] == decoded['audit'], 'Authentic journal must remain untouched'
    seal(broken, altered)
    # Distinct destination has its own account/token and data; exact whole-state
    # nonmutation includes credentials, receipts, occupancy and every counter.
    reset(c, fixture())
    destination_token = c.post('/auth/login', json={'email': 'other@stage3.test', 'password': PASSWORD}).json()['token']
    before = snapshot(c)
    result = c.post('/_test/import', json=broken, timeout=10)
    unchanged = snapshot(c) == before
    record_property('observed', json.dumps({'mutation': mutation, 'import_status': result.status_code,
        'destination_unchanged': unchanged, 'unchanged_control': 204, 'checksum_recomputed': True,
        'authentic_journal_unchanged': True, 'source_payload_sha256': original['state']['sha256']}))
    assert_error(result, 422, 'validation_failed'); assert unchanged
    assert c.post('/_test/import', json=original, timeout=10).status_code == 204
    assert c.get('/_test/export').json() == original
    assert c.get('/reservations', headers=headers(destination_token)).status_code == 401
    assert c.get('/reservations', headers=headers(tok['diner'])).status_code == 200
    assert patch(c, tok, ids['other_ref'], {'party_size': 4}).status_code == 200


def test_D335_overlapping_original_dates_valid_roundtrip(world3, record_property):
    """Overlapping original schedules are valid with disjoint seating and permanent exceptions/cancellations."""
    c, tok = world3; ids = rich_state(c, tok)
    original, s = exported(c)
    a, b = s['series'][ids['a']], s['series'][ids['b']]
    assert [o['scheduled_date'] for o in a['occurrences']] == [o['scheduled_date'] for o in b['occurrences']]
    assert [o['exception'] for o in a['occurrences']] == [True, True, False]
    assert s['reservations'][ids['refs'][0]]['status'] == 'cancelled'
    assert s['reservations'][ids['refs'][2]]['status'] == 'cancelled'
    before = {sid: series(c, tok, sid) for sid in (ids['a'], ids['b'])}
    for _ in range(2):
        assert c.post('/_test/import', json=original, timeout=10).status_code == 204
        assert c.get('/_test/export').json() == original
        assert {sid: series(c, tok, sid) for sid in before} == before
    record_property('observed', json.dumps({'overlapping_original_dates': True, 'repeat_imports': 2,
        'series_revisions': [a['revision'], b['revision']], 'exact_roundtrip': True}))
