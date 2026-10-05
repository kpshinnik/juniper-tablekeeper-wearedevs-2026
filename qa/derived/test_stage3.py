"""Stage3 cases derived from its written contract, before product handoff.

No application modules are imported. Opaque representation corruption and
restaurant-counter adapters are separate from these public HTTP assertions.
"""
import copy
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from derived.test_stage1 import assert_error, headers, snapshot

DAY = '2030-01-01'
PASSWORD = 'synthetic-password'


def fixture(zone='UTC', capacity=100):
    return {'users': [{'id': who, 'email': who+'@stage3.test', 'password': PASSWORD,
                       'display_name': who} for who in ('diner', 'manager', 'other')],
            'restaurants': [{'id': 'r', 'name': 'Policy garden', 'timezone': zone,
                'manager_user_ids': ['manager'], 'slot_minutes': 30,
                'reservation_duration_minutes': 60, 'cancellation_cutoff_minutes': 0,
                'opening_hours': [{'weekday': d, 'opens': '00:00', 'closes': '23:59'}
                                  for d in 'mon tue wed thu fri sat sun'.split()],
                'tables': [{'id': t, 'label': t.upper(), 'capacity': capacity} for t in 'abc'],
                'combinable': [['b', 'a'], ['b', 'c']]}], 'reservations': []}


@pytest.fixture
def world3():
    with httpx.Client(base_url='http://tablekeeper:8080', timeout=5, trust_env=False) as c:
        reset(c, fixture())
        tokens = {who: c.post('/auth/login', json={'email': who+'@stage3.test',
                  'password': PASSWORD}).json()['token'] for who in ('diner', 'manager', 'other')}
        yield c, tokens


def reset(c, fx):
    r = c.post('/_test/reset', json=fx, timeout=10)
    assert r.status_code == 204, r.text


def policy(date=DAY, **changes):
    value = {'effective_from': date, 'slot_minutes': 30, 'reservation_duration_minutes': 90,
             'cancellation_cutoff_minutes': 0,
             'opening_hours': [{'weekday': d, 'opens': '00:00', 'closes': '23:59'}
                               for d in 'mon tue wed thu fri sat sun'.split()],
             'capacities': {'a': 100, 'b': 100, 'c': 100}}
    value.update(changes)
    return value


def terms(p, version):
    return {**{k: copy.deepcopy(v) for k, v in p.items() if k != 'effective_from'},
            'policy_version': version}


def publish(c, tokens, value=None, key='policy'):
    value = policy() if value is None else value
    r = c.post('/restaurants/r/policies', json=value, headers=headers(tokens['manager'], key))
    assert r.status_code == 201, r.text
    return r.json()


def booking(c, tokens, key='book', date=DAY, table='a', party=2, **fields):
    body = {'restaurant_id': 'r', 'table_id': table, 'starts_at_local': date+'T18:00', 'party_size': party}
    if 'table_ids' in fields:
        body.pop('table_id')
    body.update(fields)
    r = c.post('/reservations', json=body, headers=headers(tokens['diner'], key))
    assert r.status_code == 201, r.text
    return body, r.json()


def current(c, token, ref):
    r = c.get('/reservations/'+ref, headers=headers(token))
    assert r.status_code == 200, r.text
    return r.json()


def history(c, token, ref):
    r = c.get('/reservations/'+ref+'/history', headers=headers(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['reference'] == ref
    entries = data['entries']
    assert [e['seq'] for e in entries] == list(range(1, len(entries)+1))
    at = [dt.datetime.fromisoformat(e['at']) for e in entries]
    assert all(x.utcoffset() is not None for x in at)
    assert at == sorted(at)
    return entries


def patch(c, tokens, ref, value):
    return c.patch('/reservations/'+ref, json=value, headers=headers(tokens['diner']))


def adopt(c, tokens, ref, key='series', **fields):
    body = {'anchor_reference': ref, 'count': 3, 'interval_weeks': 1, **fields}
    r = c.post('/series', json=body, headers=headers(tokens['diner'], key))
    assert r.status_code == 201, r.text
    return body, r.json()


def series(c, tokens, sid):
    r = c.get('/series/'+sid, headers=headers(tokens['diner']))
    assert r.status_code == 200, r.text
    return r.json()


def test_D301_explanations_independent_rules_and_absent_shape(world3):
    """Both rules are independently reported for every table, ordered, and absent without explain."""
    c, tok = world3
    publish(c, tok, policy(capacities={'a': 1, 'b': 4, 'c': 1}))
    booking(c, tok, party=1)
    params = {'restaurant_id': 'r', 'date': DAY, 'party_size': 2}
    ordinary = c.get('/availability', params=params).json()
    explained = c.get('/availability', params={**params, 'explain': 'true'}).json()
    for plain, slot in zip(ordinary['slots'], explained['slots'], strict=True):
        assert 'explain' not in plain
        assert {k: v for k, v in slot.items() if k != 'explain'} == plain
        assert [x['table_id'] for x in slot['explain']] == list('abc')
        for e in slot['explain']:
            assert e['policy_version'] == 1
            assert [r['rule'] for r in e['rules']] == ['capacity', 'no_overlap']
            assert all(type(r['holds']) is bool for r in e['rules'])
            assert e['available'] is all(r['holds'] for r in e['rules'])
        assert [x['table_id'] for x in slot['explain'] if x['available']] == slot['available_table_ids']
    slot = next(x for x in explained['slots'] if x['starts_at_local'] == DAY+'T18:00')
    assert [r['holds'] for r in slot['explain'][0]['rules']] == [False, False]
    assert [r['holds'] for r in slot['explain'][1]['rules']] == [True, True]
    assert [r['holds'] for r in slot['explain'][2]['rules']] == [False, True]


@pytest.mark.parametrize('value', ['false', '1', '', 'TRUE', ' true'], ids=['false', 'one', 'empty', 'uppercase', 'space'])
def test_D302_explain_value_contract(world3, value):
    """Only the exact optional query value true is accepted, with no mutation."""
    c, _ = world3; before = snapshot(c)
    assert_error(c.get('/availability', params={'restaurant_id': 'r', 'date': DAY,
                 'party_size': '2', 'explain': value}), 422, 'validation_failed')
    assert snapshot(c) == before


def test_D303_policy_permissions_and_private_history(world3):
    """Manager publication rights do not grant private diner history or decision access."""
    c, tok = world3; _, b = booking(c, tok); before = snapshot(c)
    for h, status, code in [({}, 401, 'unauthenticated'), (headers(tok['diner']), 403, 'forbidden')]:
        assert_error(c.post('/restaurants/r/policies', json=policy(), headers=h), status, code)
    assert_error(c.post('/restaurants/absent/policies', json=policy(), headers=headers(tok['manager'])), 404, 'not_found')
    for suffix in ('/history', '/decision'):
        for h in ({}, headers(tok['other']), headers(tok['manager']), {'Authorization': 'Bearer invalid'}):
            assert_error(c.get('/reservations/'+b['reference']+suffix, headers=h), 404, 'not_found')
    assert c.get('/restaurants/r/policies').json() == {'policies': []}
    assert snapshot(c) == before


POLICY_BAD = [
    ('effective_from', '2030-02-30'), ('effective_from', '2030-1-01'), ('effective_from', True),
    ('slot_minutes', 0), ('slot_minutes', 1441), ('slot_minutes', True), ('slot_minutes', '30'),
    ('reservation_duration_minutes', 0), ('reservation_duration_minutes', 1441),
    ('reservation_duration_minutes', False), ('cancellation_cutoff_minutes', -1),
    ('cancellation_cutoff_minutes', 10081), ('cancellation_cutoff_minutes', 0.5),
    ('opening_hours', [{'weekday': 'tue', 'opens': '18:00', 'closes': '23:00'}]*2),
    ('opening_hours', [{'weekday': 'tue', 'opens': '23:00', 'closes': '18:00'}]),
    ('capacities', {'a': 1, 'b': 2}), ('capacities', {'a': 1, 'b': 2, 'c': 3, 'd': 4}),
    ('capacities', {'a': 0, 'b': 2, 'c': 3}), ('capacities', {'a': 101, 'b': 2, 'c': 3}),
    ('capacities', {'a': True, 'b': 2, 'c': 3}), ('capacities', {'a': 1.5, 'b': 2, 'c': 3})]


@pytest.mark.parametrize('field,value', POLICY_BAD, ids=['bad'+str(i+1) for i in range(len(POLICY_BAD))])
def test_D304_invalid_complete_policy_rollback_and_key_reuse(world3, field, value):
    """Invalid complete policies return422 without consuming a version or key."""
    c, tok = world3; p = policy(); p[field] = value; before = snapshot(c)
    assert_error(c.post('/restaurants/r/policies', json=p, headers=headers(tok['manager'])), 422, 'validation_failed')
    assert snapshot(c) == before
    assert publish(c, tok, key='derived')['policy_version'] == 1


@pytest.mark.parametrize('field', list(policy()), ids=list(policy()))
def test_D305_policy_all_fields_required(world3, field):
    """Every policy field is required; omission cannot allocate a version or receipt."""
    c, tok = world3; p = policy(); del p[field]; before = snapshot(c)
    assert_error(c.post('/restaurants/r/policies', json=p, headers=headers(tok['manager'])), 422, 'validation_failed')
    assert snapshot(c) == before


def test_D306_publication_order_date_ties_original_detail_and_replay(world3):
    """Effective-date choice and tie-breaking are independent of publication order; existing booking is immutable."""
    c, tok = world3; original = c.get('/restaurants/r').json(); body, b = booking(c, tok)
    old_history = history(c, tok['diner'], b['reference'])
    policies = [policy('2030-01-15', reservation_duration_minutes=120), policy('2030-01-01'),
                policy('2030-01-15', reservation_duration_minutes=150)]
    receipts = [publish(c, tok, p, 'p'+str(i)) for i, p in enumerate(policies)]
    assert [p['policy_version'] for p in receipts] == [1, 2, 3]
    assert c.get('/restaurants/r/policies').json() == {'policies': receipts}
    assert c.get('/restaurants/r').json() == original
    for date, version, duration in [('2029-12-25', 0, 60), ('2030-01-08', 2, 90), ('2030-01-15', 3, 150)]:
        _, made = booking(c, tok, key=date, date=date)
        assert made['accepted_terms']['policy_version'] == version
        assert made['accepted_terms']['reservation_duration_minutes'] == duration
    assert current(c, tok['diner'], b['reference']) == b
    assert history(c, tok['diner'], b['reference']) == old_history
    r = c.post('/restaurants/r/policies', json=policies[0], headers=headers(tok['manager'], 'p0'))
    assert r.status_code == 200 and r.json() == receipts[0]
    assert c.post('/reservations', json=body, headers=headers(tok['diner'], 'book')).json() == b
    before = snapshot(c)
    assert_error(c.post('/restaurants/r/policies', json={}, headers=headers(tok['manager'], 'p0')), 409, 'idempotency_key_reuse')
    assert snapshot(c) == before


def test_D307_policy_zero_not_restricted_by_publication_capacity_bound(world3):
    """Large accepted fixture capacities remain exact through current terms, history, ordinary export/import and replay."""
    c, _ = world3; huge = 9007199254740993; reset(c, fixture(capacity=huge))
    tok = {x: c.post('/auth/login', json={'email': x+'@stage3.test', 'password': PASSWORD}).json()['token'] for x in ('diner', 'manager')}
    body, b = booking(c, tok, party=huge)
    assert b['party_size'] == huge and b['accepted_terms']['capacities']['a'] == huge
    assert b['accepted_terms']['policy_version'] == 0
    hist = history(c, tok['diner'], b['reference'])
    publish(c, tok)
    no_op = patch(c, tok, b['reference'], {'party_size': huge, 'expected_revision': 1})
    assert no_op.status_code == 200 and no_op.json() == b
    exported = c.get('/_test/export').json()
    assert c.post('/_test/import', json=exported, timeout=10).status_code == 204
    assert current(c, tok['diner'], b['reference']) == b
    assert history(c, tok['diner'], b['reference']) == hist
    replay = c.post('/reservations', json=body, headers=headers(tok['diner'], 'book'))
    assert replay.status_code == 200 and replay.json() == b


def test_D308_history_changes_terms_noops_cancel_and_original_receipt(world3):
    """Real changes add one ordered genuine event; no-ops/replays/repeated cancellation add none."""
    c, tok = world3; body, b = booking(c, tok); ref = b['reference']
    hist = history(c, tok['diner'], ref)
    assert len(hist) == 1 and hist[0]['event'] == 'created' and hist[0]['revision'] == 1
    assert hist[0]['changes'] == [{'field': k, 'from': None, 'to': body[k]} for k in ('table_id', 'starts_at_local', 'party_size')]
    assert hist[0]['accepted_terms'] == b['accepted_terms']
    p = policy(); publish(c, tok, p)
    assert patch(c, tok, ref, {'table_id': 'a', 'party_size': 2}).json() == b
    assert history(c, tok['diner'], ref) == hist
    changed = patch(c, tok, ref, {'table_id': 'b', 'starts_at_local': DAY+'T19:00', 'party_size': 3})
    assert changed.status_code == 200; now = changed.json()
    assert now['revision'] == 2 and now['accepted_terms'] == terms(p, 1)
    hist2 = history(c, tok['diner'], ref)
    assert hist2[:1] == hist and len(hist2) == 2
    assert hist2[1]['changes'] == [{'field': k, 'from': body[k], 'to': now[k]} for k in ('table_id', 'starts_at_local', 'party_size')]
    assert hist2[1]['event'] == 'changed' and hist2[1]['revision'] == 2 and hist2[1]['accepted_terms'] == now['accepted_terms']
    cancelled = c.post('/reservations/'+ref+'/cancel', headers=headers(tok['diner']))
    assert cancelled.status_code == 200 and cancelled.json()['revision'] == 3
    hist3 = history(c, tok['diner'], ref)
    assert hist3[:2] == hist2 and len(hist3) == 3
    assert hist3[-1]['event'] == 'cancelled' and hist3[-1]['changes'] == [] and hist3[-1]['revision'] == 3
    assert c.post('/reservations/'+ref+'/cancel', headers=headers(tok['diner'])).json() == cancelled.json()
    assert history(c, tok['diner'], ref) == hist3
    decision = c.get('/reservations/'+ref+'/decision', headers=headers(tok['diner']))
    assert decision.json() == {'reference': ref, 'revision': 3, 'accepted_terms': now['accepted_terms']}
    retry = c.post('/reservations', json=body, headers=headers(tok['diner'], 'book'))
    assert retry.status_code == 200 and retry.json() == b


@pytest.mark.parametrize('revision', [True, False, 0, -1, 1.5, '1', None], ids=['true', 'false', 'zero', 'negative', 'fraction', 'string', 'null'])
def test_D309_expected_revision_type_range(world3, revision):
    """Explicit invalid expected revisions produce422 without changing a booking or its history."""
    c, tok = world3; _, b = booking(c, tok); before = snapshot(c)
    assert_error(patch(c, tok, b['reference'], {'expected_revision': revision, 'party_size': 3}), 422, 'validation_failed')
    assert snapshot(c) == before


def test_D310_stale_revision_precedes_cutoff_and_change_validation(world3):
    """A positive stale revision wins over past cutoff and malformed proposed fields."""
    c, tok = world3; _, b = booking(c, tok, date='2000-01-01'); before = snapshot(c)
    assert_error(patch(c, tok, b['reference'], {'expected_revision': 2, 'party_size': False}), 409, 'stale_revision')
    assert_error(patch(c, tok, b['reference'], {'expected_revision': 1, 'party_size': False}), 409, 'cutoff_passed')
    assert snapshot(c) == before


def test_D311_concurrent_revision_compare_and_change(world3, record_property):
    """Fifty concurrent distinct real changes from revision1 have exactly one winner and one event."""
    c, tok = world3; _, b = booking(c, tok)
    with ThreadPoolExecutor(max_workers=50) as pool:
        replies = list(pool.map(lambda n: patch(c, tok, b['reference'], {'expected_revision': 1, 'party_size': n}), range(3, 53)))
    assert [r.status_code for r in replies].count(200) == 1
    for r in replies:
        if r.status_code != 200: assert_error(r, 409, 'stale_revision')
    now = current(c, tok['diner'], b['reference']); hist = history(c, tok['diner'], b['reference'])
    assert now['revision'] == 2 and len(hist) == 2 and hist[-1]['revision'] == 2
    record_property('observed', json.dumps({'concurrency': 50, 'requests': 50, 'successes': 1, 'stale': 49, 'history_entries': 2}))


def test_D312_combined_history_and_reversed_pair_noop(world3):
    """Pair history uses complete canonical sets; reversed input has no semantic change."""
    c, tok = world3; _, b = booking(c, tok, table_ids=['a', 'b']); ref = b['reference']
    assert b['table_ids'] == ['b', 'a'] and 'table_id' not in b
    hist = history(c, tok['diner'], ref)
    assert hist[0]['changes'][0] == {'field': 'table_ids', 'from': None, 'to': ['b', 'a']}
    assert patch(c, tok, ref, {'table_ids': ['a', 'b']}).json() == b
    assert history(c, tok['diner'], ref) == hist
    single = patch(c, tok, ref, {'table_id': 'c'})
    assert single.status_code == 200 and single.json()['revision'] == 2
    assert history(c, tok['diner'], ref)[-1]['changes'] == [{'field': 'table_ids', 'from': ['b', 'a'], 'to': ['c']}]
    pair = patch(c, tok, ref, {'table_ids': ['c', 'b']})
    assert pair.status_code == 200 and pair.json()['table_ids'] == ['b', 'c']
    assert history(c, tok['diner'], ref)[-1]['changes'] == [{'field': 'table_ids', 'from': ['c'], 'to': ['b', 'c']}]


def test_D313_real_change_revalidates_all_fields_new_policy_noop_keeps_terms(world3):
    """An unrelated party change must revalidate the retained time under its newly applicable grid."""
    c, tok = world3; _, b = booking(c, tok, starts_at_local=DAY+'T18:30'); ref = b['reference']
    publish(c, tok, policy(slot_minutes=60)); before = snapshot(c)
    assert patch(c, tok, ref, {'party_size': 2}).json() == b
    assert snapshot(c) == before
    assert_error(patch(c, tok, ref, {'party_size': 3}), 422, 'not_on_slot_grid')
    assert snapshot(c) == before
    changed = patch(c, tok, ref, {'starts_at_local': DAY+'T19:00', 'party_size': 3})
    assert changed.status_code == 200 and changed.json()['accepted_terms']['policy_version'] == 1


def test_D314_adoption_authentic_anchor_per_date_terms_and_replay(world3):
    """Adoption preserves the anchor exactly and independently chooses each generated occurrence's policy."""
    c, tok = world3; create_body, anchor = booking(c, tok); ref = anchor['reference']
    hist = history(c, tok['diner'], ref)
    publish(c, tok, policy('2030-01-08', reservation_duration_minutes=120), 'p1')
    publish(c, tok, policy('2030-01-15', reservation_duration_minutes=150), 'p2')
    request, receipt = adopt(c, tok, ref)
    assert receipt['revision'] == 1 and receipt['interval_weeks'] == 1
    occurrences = receipt['occurrences']
    assert [x['index'] for x in occurrences] == [0, 1, 2]
    assert len({x['reference'] for x in occurrences}) == 3
    assert all(x['exception'] is False for x in occurrences)
    assert occurrences[0]['reservation'] == anchor and occurrences[0]['reference'] == ref
    assert history(c, tok['diner'], ref) == hist
    for i, occ in enumerate(occurrences):
        b = occ['reservation']; assert b == current(c, tok['diner'], occ['reference'])
        assert b['starts_at_local'] == ['2030-01-01T18:00', '2030-01-08T18:00', '2030-01-15T18:00'][i]
        assert b['accepted_terms']['policy_version'] == i and b['revision'] == 1
        h = history(c, tok['diner'], occ['reference'])
        assert len(h) == 1 and h[0]['event'] == 'created' and h[0]['accepted_terms'] == b['accepted_terms']
    assert patch(c, tok, occurrences[1]['reference'], {'party_size': 3}).status_code == 200
    replay = c.post('/series', json=request, headers=headers(tok['diner'], 'series'))
    assert replay.status_code == 200 and replay.json() == receipt
    assert c.post('/reservations', json=create_body, headers=headers(tok['diner'], 'book')).json() == anchor
    assert len(c.get('/reservations', headers=headers(tok['diner'])).json()['reservations']) == 3


@pytest.mark.parametrize('field,value', [('count', 1), ('count', 13), ('count', True), ('count', '2'),
                                         ('interval_weeks', 0), ('interval_weeks', 5), ('interval_weeks', False), ('interval_weeks', 1.5)],
                         ids=['count-low', 'count-high', 'count-bool', 'count-string', 'interval-low', 'interval-high', 'interval-bool', 'interval-fraction'])
def test_D315_invalid_series_ranges_rollback(world3, field, value):
    """Invalid series count/interval is rejected422 without a partial agreement or idempotency claim."""
    c, tok = world3; _, anchor = booking(c, tok); before = snapshot(c)
    request = {'anchor_reference': anchor['reference'], 'count': 3, 'interval_weeks': 1, field: value}
    assert_error(c.post('/series', json=request, headers=headers(tok['diner'], 'series')), 422, 'validation_failed')
    assert snapshot(c) == before
    adopt(c, tok, anchor['reference'])


def test_D316_series_privacy_anchor_state_and_repeat_adoption(world3):
    """Series read privacy returns404 without authentication; adoption enforces owner, confirmed, editable and unused anchor."""
    c, tok = world3; _, b = booking(c, tok); ref = b['reference']
    request = {'anchor_reference': ref, 'count': 2, 'interval_weeks': 1}; before = snapshot(c)
    assert_error(c.post('/series', json=request), 401, 'unauthenticated')
    assert_error(c.post('/series', json=request, headers=headers(tok['other'])), 404, 'not_found')
    assert snapshot(c) == before
    _, agreement = adopt(c, tok, ref)
    for h in ({}, headers(tok['other']), headers(tok['manager'])):
        assert_error(c.get('/series/'+agreement['series_id'], headers=h), 404, 'not_found')
    before = snapshot(c)
    assert_error(c.post('/series', json=request, headers=headers(tok['diner'], 'new-adoption')), 409, 'already_in_series')
    assert snapshot(c) == before
    _, past = booking(c, tok, key='past', date='2000-01-01')
    assert_error(c.post('/series', json={**request, 'anchor_reference': past['reference']}, headers=headers(tok['diner'], 'past-series')), 409, 'cutoff_passed')
    _, cancelled = booking(c, tok, key='cancel', table='c')
    assert c.post('/reservations/'+cancelled['reference']+'/cancel', headers=headers(tok['diner'])).status_code == 200
    assert_error(c.post('/series', json={**request, 'anchor_reference': cancelled['reference']}, headers=headers(tok['diner'], 'cancel-series')), 409, 'reservation_cancelled')


def test_D317_failed_occurrence_first_index_rolls_back_and_reuses_key(world3):
    """First-index occupancy beats a later policy capacity failure; failed adoption leaves no generated booking or key."""
    c, tok = world3; _, anchor = booking(c, tok); _, blocker = booking(c, tok, key='block', date='2030-01-08')
    publish(c, tok, policy('2030-01-15', capacities={'a': 1, 'b': 100, 'c': 100}), 'bad-later')
    before = snapshot(c); request = {'anchor_reference': anchor['reference'], 'count': 3, 'interval_weeks': 1}
    assert_error(c.post('/series', json=request, headers=headers(tok['diner'], 'series')), 409, 'table_unavailable')
    assert snapshot(c) == before
    assert c.post('/reservations/'+blocker['reference']+'/cancel', headers=headers(tok['diner'])).status_code == 200
    before = snapshot(c)
    assert_error(c.post('/series', json=request, headers=headers(tok['diner'], 'series')), 422, 'party_exceeds_capacity')
    assert snapshot(c) == before
    publish(c, tok, policy('2030-01-15'), 'correct-later')
    adopt(c, tok, anchor['reference'])


def test_D318_series_dst_gap_atomicity_and_fold_first_occurrence(world3):
    """Recurring dates use local calendar weeks; skipped time rejects all and folded time uses its first occurrence."""
    c, _ = world3; reset(c, fixture('America/New_York'))
    token = c.post('/auth/login', json={'email': 'diner@stage3.test', 'password': PASSWORD}).json()['token']; tok = {'diner': token}
    _, anchor = booking(c, tok, starts_at_local='2030-03-03T02:30'); before = snapshot(c)
    assert_error(c.post('/series', json={'anchor_reference': anchor['reference'], 'count': 3, 'interval_weeks': 1}, headers=headers(token, 'gap')), 422, 'invalid_local_time')
    assert snapshot(c) == before
    _, fold = booking(c, tok, key='fold', starts_at_local='2030-10-27T01:30')
    _, adopted = adopt(c, tok, fold['reference'], key='fold-series', count=2)
    generated = adopted['occurrences'][1]['reservation']
    assert generated['starts_at_local'] == '2030-11-03T01:30'
    assert generated['starts_at'] == '2030-11-03T01:30:00-04:00'
    assert generated['ends_at'] == '2030-11-03T01:30:00-05:00'


def test_D319_permanent_exceptions_noops_cancel_and_anchor_independence(world3):
    """Real member changes permanently mark exceptions; cancelling retains flags and siblings, no-ops allocate nothing."""
    c, tok = world3; _, anchor = booking(c, tok); _, s = adopt(c, tok, anchor['reference']); sid = s['series_id']
    ref = s['occurrences'][1]['reference']
    assert patch(c, tok, ref, {'party_size': 2}).status_code == 200
    assert series(c, tok, sid) == s
    assert patch(c, tok, ref, {'party_size': 3}).status_code == 200
    assert patch(c, tok, ref, {'party_size': 2}).status_code == 200
    after = series(c, tok, sid)
    assert after['revision'] == 3 and after['occurrences'][1]['exception'] is True
    assert c.post('/reservations/'+ref+'/cancel', headers=headers(tok['diner'])).status_code == 200
    cancelled = series(c, tok, sid)
    assert cancelled['revision'] == 4 and cancelled['occurrences'][1]['exception'] is True
    assert c.post('/reservations/'+ref+'/cancel', headers=headers(tok['diner'])).status_code == 200
    assert series(c, tok, sid) == cancelled
    assert c.post('/reservations/'+anchor['reference']+'/cancel', headers=headers(tok['diner'])).status_code == 200
    final = series(c, tok, sid)
    assert final['revision'] == 5 and final['occurrences'][0]['exception'] is False
    assert final['occurrences'][2] == s['occurrences'][2]


def test_D320_collective_series_changes_count_once_rollback_and_original_receipt(world3):
    """Changing two members increments a series once; stale batch rolls back all; replay is immutable."""
    c, tok = world3; _, anchor = booking(c, tok); _, s = adopt(c, tok, anchor['reference']); sid = s['series_id']
    refs = [x['reference'] for x in s['occurrences']]
    moves = {'moves': [{'reference': r, 'party_size': 3, 'expected_revision': 1} for r in refs[:2]]}
    response = c.post('/reservation-moves', json=moves, headers=headers(tok['diner'], 'batch'))
    assert response.status_code == 201; receipt = response.json()
    assert [x['revision'] for x in receipt['reservations']] == [2, 2]
    updated = series(c, tok, sid)
    assert updated['revision'] == 2 and [x['exception'] for x in updated['occurrences']] == [True, True, False]
    for r in refs[:2]: assert len(history(c, tok['diner'], r)) == 2
    before = snapshot(c)
    bad = {'moves': [{'reference': refs[2], 'party_size': 4, 'expected_revision': 1},
                     {'reference': refs[0], 'party_size': 4, 'expected_revision': 1}]}
    assert_error(c.post('/reservation-moves', json=bad, headers=headers(tok['diner'], 'failed-batch')), 409, 'stale_revision')
    assert snapshot(c) == before
    noop = {'moves': [{'reference': r, 'party_size': 3, 'expected_revision': 2} for r in refs[:2]]}
    assert c.post('/reservation-moves', json=noop, headers=headers(tok['diner'], 'noop')).status_code == 201
    assert series(c, tok, sid) == updated
    assert patch(c, tok, refs[0], {'party_size': 4}).status_code == 200
    replay = c.post('/reservation-moves', json=moves, headers=headers(tok['diner'], 'batch'))
    assert replay.status_code == 200 and replay.json() == receipt


def test_D321_concurrent_policy_versions_and_series_identical_key(world3, record_property):
    """Concurrent publications allocate unique contiguous versions, identical adoption creates a single agreement."""
    c, tok = world3; _, anchor = booking(c, tok)
    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda n: c.post('/restaurants/r/policies', json=policy(),
                          headers=headers(tok['manager'], 'parallel-'+str(n))), range(20)))
    assert all(r.status_code == 201 for r in responses)
    assert sorted(r.json()['policy_version'] for r in responses) == list(range(1, 21))
    assert [p['policy_version'] for p in c.get('/restaurants/r/policies').json()['policies']] == list(range(1, 21))
    body = {'anchor_reference': anchor['reference'], 'count': 3, 'interval_weeks': 1}
    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda _: c.post('/series', json=body, headers=headers(tok['diner'], 'same-series')), range(20)))
    assert sorted(r.status_code for r in responses) == [200]*19+[201]
    assert all(r.json() == responses[0].json() for r in responses)
    assert len(c.get('/reservations', headers=headers(tok['diner'])).json()['reservations']) == 3
    assert series(c, tok, responses[0].json()['series_id'])['revision'] == 1
    record_property('observed', json.dumps({'concurrency': 20, 'policy_requests': 20, 'series_requests': 20, 'policy_versions': 20, 'adoptions': 1}))


def test_D322_accepted_cutoff_not_new_policy_cutoff(world3):
    """Publishing a permissive cutoff does not release an already accepted cutoff; a new strict cutoff does not retroactively refuse cancellation."""
    c, _ = world3
    now = dt.datetime.now(dt.timezone.utc)
    tomorrow = (now+dt.timedelta(days=1)).date().isoformat()
    fx = fixture(); fx['restaurants'][0]['cancellation_cutoff_minutes'] = 10080
    reset(c, fx)
    tok = {x: c.post('/auth/login', json={'email': x+'@stage3.test', 'password': PASSWORD}).json()['token'] for x in ('diner', 'manager')}
    _, locked = booking(c, tok, date=tomorrow)
    publish(c, tok, policy(tomorrow, cancellation_cutoff_minutes=0))
    before = snapshot(c)
    assert_error(patch(c, tok, locked['reference'], {'party_size': 3}), 409, 'cutoff_passed')
    assert_error(c.post('/reservations/'+locked['reference']+'/cancel', headers=headers(tok['diner'])), 409, 'cutoff_passed')
    assert snapshot(c) == before
    _, editable = booking(c, tok, key='editable', date=tomorrow, table='c')
    publish(c, tok, policy(tomorrow, cancellation_cutoff_minutes=10080), 'strict')
    assert c.post('/reservations/'+editable['reference']+'/cancel', headers=headers(tok['diner'])).status_code == 200


def test_D323_unknown_fields_identity_new_paths_scope_and_conflict_precedence(world3):
    """Unknown fields are ignored for semantics but retained in new policy/series request identity and path/user key scopes."""
    c, tok = world3; p = {**policy(), 'unknown': {'nested': [True, None, '\u0000雪']}}
    result = publish(c, tok, p, 'shared-key')
    assert result['policy_version'] == 1
    before = snapshot(c)
    assert_error(c.post('/restaurants/r/policies', json={**p, 'unknown': 0}, headers=headers(tok['manager'], 'shared-key')), 409, 'idempotency_key_reuse')
    assert snapshot(c) == before
    # Same user/key on a different idempotent path is a fresh request.
    r = c.post('/reservations', json={'restaurant_id': 'r', 'table_id': 'c', 'starts_at_local': DAY+'T18:00', 'party_size': 2}, headers=headers(tok['manager'], 'shared-key'))
    assert r.status_code == 201
    _, anchor = booking(c, tok, key='shared-key')
    body, receipt = adopt(c, tok, anchor['reference'], key='shared-key', unknown={'nested': 1})
    before = snapshot(c)
    assert_error(c.post('/series', json={**body, 'count': False}, headers=headers(tok['diner'], 'shared-key')), 409, 'idempotency_key_reuse')
    assert snapshot(c) == before
    replay = c.post('/series', json=body, headers=headers(tok['diner'], 'shared-key'))
    assert replay.status_code == 200 and replay.json() == receipt


def test_D324_final_roundtrip_history_series_original_receipts_replacement(world3):
    """An ordinary JSON roundtrip preserves policy/series/history/current values and immutable originals, and replaces later mutations."""
    c, tok = world3; p = policy(); original_policy = publish(c, tok, p)
    body, anchor = booking(c, tok); adoption_body, original_series = adopt(c, tok, anchor['reference'])
    member = original_series['occurrences'][1]['reference']
    assert patch(c, tok, member, {'party_size': 3}).status_code == 200
    refs = [x['reference'] for x in original_series['occurrences']]
    expected = {r: [current(c, tok['diner'], r), history(c, tok['diner'], r)] for r in refs}
    expected_series = series(c, tok, original_series['series_id'])
    export = c.get('/_test/export').json()
    assert c.post('/reservations/'+refs[-1]+'/cancel', headers=headers(tok['diner'])).status_code == 200
    assert c.post('/_test/import', content=json.dumps(export), headers={'Content-Type': 'application/json'}, timeout=10).status_code == 204
    assert {r: [current(c, tok['diner'], r), history(c, tok['diner'], r)] for r in refs} == expected
    assert series(c, tok, original_series['series_id']) == expected_series
    for path, value, token, key, original in [('/reservations', body, tok['diner'], 'book', anchor),
            ('/series', adoption_body, tok['diner'], 'series', original_series),
            ('/restaurants/r/policies', p, tok['manager'], 'policy', original_policy)]:
        r = c.post(path, json=value, headers=headers(token, key))
        assert r.status_code == 200 and r.json() == original


def test_D326_closed_and_fully_unavailable_explained_slots(world3):
    """Closed policy days have no slots; capacity-excluded open slots retain complete explanations."""
    c, tok = world3
    publish(c, tok, policy(opening_hours=[{'weekday': 'tue', 'opens': '18:00', 'closes': '19:30'}],
                           capacities={'a': 1, 'b': 1, 'c': 1}))
    opened = c.get('/availability', params={'restaurant_id': 'r', 'date': DAY, 'party_size': 3, 'explain': 'true'})
    assert opened.status_code == 200
    slots = opened.json()['slots']; assert len(slots) == 1
    assert slots[0]['available_table_ids'] == [] and slots[0]['available_options'] == []
    assert len(slots[0]['explain']) == 3 and all(x['available'] is False for x in slots[0]['explain'])
    closed = c.get('/availability', params={'restaurant_id': 'r', 'date': '2030-01-02', 'party_size': 3, 'explain': 'true'})
    assert closed.status_code == 200 and closed.json()['slots'] == []


def test_D327_pair_selected_policy_capacity_and_real_change_terms(world3):
    """Pair capacity uses selected-policy members, and later publication leaves original pair terms intact."""
    c, tok = world3; p = policy(capacities={'a': 2, 'b': 3, 'c': 1}); publish(c, tok, p)
    _, b = booking(c, tok, party=5, table_ids=['a', 'b'])
    assert b['accepted_terms'] == terms(p, 1)
    publish(c, tok, policy(capacities={'a': 1, 'b': 1, 'c': 1}), 'small')
    assert patch(c, tok, b['reference'], {'table_ids': ['a', 'b']}).json() == b
    before = snapshot(c)
    assert_error(patch(c, tok, b['reference'], {'starts_at_local': DAY+'T20:00'}), 422, 'party_exceeds_capacity')
    assert snapshot(c) == before
    changed = patch(c, tok, b['reference'], {'starts_at_local': DAY+'T20:00', 'party_size': 2})
    assert changed.status_code == 200 and changed.json()['accepted_terms']['policy_version'] == 2


def test_D328_seeded_bookings_revision_one_original_policy(world3):
    """A seeded pair gets revision1 and original whole-fixture accepted terms; cancelled seeds occupy nothing."""
    c, _ = world3; fx = fixture(capacity=150)
    fx['reservations'] = [
        {'id': 'seed1', 'reference': 'SEED001', 'user_id': 'diner', 'restaurant_id': 'r',
         'table_ids': ['a', 'b'], 'starts_at_local': DAY+'T18:00', 'party_size': 151},
        {'id': 'seed2', 'reference': 'SEED002', 'user_id': 'diner', 'restaurant_id': 'r',
         'table_id': 'c', 'starts_at_local': DAY+'T18:00', 'party_size': 1, 'status': 'cancelled'}]
    reset(c, fx)
    token = c.post('/auth/login', json={'email': 'diner@stage3.test', 'password': PASSWORD}).json()['token']
    first = current(c, token, 'SEED001'); second = current(c, token, 'SEED002')
    assert first['revision'] == second['revision'] == 1
    assert first['accepted_terms']['policy_version'] == 0 and first['accepted_terms']['capacities'] == dict.fromkeys('abc', 150)
    available = c.get('/availability', params={'restaurant_id': 'r', 'date': DAY, 'party_size': 1}).json()
    slot = next(x for x in available['slots'] if x['starts_at_local'] == DAY+'T18:00')
    assert slot['available_table_ids'] == ['c']


def test_D329_adopt_previously_amended_anchor_preserves_authentic_history(world3):
    """An anchor with real prior changes keeps its revision/history/identity and accepts the largest series bounds."""
    c, tok = world3; body, b = booking(c, tok)
    changed = patch(c, tok, b['reference'], {'party_size': 3, 'starts_at_local': '2030-01-02T18:00'})
    assert changed.status_code == 200; now = changed.json(); hist = history(c, tok['diner'], b['reference'])
    _, adopted = adopt(c, tok, b['reference'], count=12, interval_weeks=4)
    assert adopted['occurrences'][0]['reservation'] == now
    assert history(c, tok['diner'], b['reference']) == hist
    assert len(adopted['occurrences']) == 12
    for index, occurrence in enumerate(adopted['occurrences']):
        assert occurrence['index'] == index
        expected_date = dt.date(2030, 1, 2)+dt.timedelta(days=index*28)
        assert occurrence['reservation']['starts_at_local'] == expected_date.isoformat()+'T18:00'
    r = c.post('/reservations', json=body, headers=headers(tok['diner'], 'book'))
    assert r.status_code == 200 and r.json() == b


def test_D330_collective_two_series_each_increments_once(world3):
    """One batch affecting multiple members of two agreements increments each agreement once and leaves untouched members exact."""
    c, tok = world3; _, a = booking(c, tok); _, b = booking(c, tok, key='b', table='c')
    _, first = adopt(c, tok, a['reference'], key='series-a')
    _, second = adopt(c, tok, b['reference'], key='series-b')
    refs = [x['reference'] for s in (first, second) for x in s['occurrences'][:2]]
    request = {'moves': [{'reference': r, 'party_size': 3} for r in refs]}
    r = c.post('/reservation-moves', json=request, headers=headers(tok['diner'], 'two-series'))
    assert r.status_code == 201 and [x['reference'] for x in r.json()['reservations']] == refs
    for before in (first, second):
        after = series(c, tok, before['series_id'])
        assert after['revision'] == 2 and [x['exception'] for x in after['occurrences']] == [True, True, False]
        assert after['occurrences'][2] == before['occurrences'][2]
        assert [x['reservation']['revision'] for x in after['occurrences']] == [2, 2, 1]


def test_D331_series_combined_member_occupancy_prevents_partial_adoption(world3):
    """A single member occupied on a generated date rejects an entire declared-pair agreement and preserves its anchor."""
    c, tok = world3; _, anchor = booking(c, tok, table_ids=['a', 'b'])
    _, blocker = booking(c, tok, key='block', table='a', date='2030-01-08')
    request = {'anchor_reference': anchor['reference'], 'count': 3, 'interval_weeks': 1}; before = snapshot(c)
    assert_error(c.post('/series', json=request, headers=headers(tok['diner'], 'pair-series')), 409, 'table_unavailable')
    assert snapshot(c) == before
    assert c.post('/reservations/'+blocker['reference']+'/cancel', headers=headers(tok['diner'])).status_code == 200
    _, agreement = adopt(c, tok, anchor['reference'], key='pair-series')
    assert all(x['reservation']['table_ids'] == ['b', 'a'] for x in agreement['occurrences'])


def test_D332_policy_valid_numeric_boundaries_and_default_manager_denial(world3):
    """Publication accepts inclusive numerical bounds; absent manager list grants no publication permission."""
    c, tok = world3
    for i, p in enumerate([policy(slot_minutes=1, reservation_duration_minutes=1, cancellation_cutoff_minutes=0,
                                  capacities={'a': 1, 'b': 100, 'c': 1}),
                           policy(slot_minutes=1440, reservation_duration_minutes=1440, cancellation_cutoff_minutes=10080)]):
        assert publish(c, tok, p, 'bound-'+str(i))['policy_version'] == i+1
    fx = fixture(); fx['restaurants'][0].pop('manager_user_ids'); reset(c, fx)
    token = c.post('/auth/login', json={'email': 'manager@stage3.test', 'password': PASSWORD}).json()['token']; before = snapshot(c)
    assert_error(c.post('/restaurants/r/policies', json=policy(), headers=headers(token)), 403, 'forbidden')
    assert snapshot(c) == before
