"""Stage 4 HTTP checks: global planning optimality and recurring atomic changes.

These are supplemental inputs. No pass is claimed until executed on a real Stage 4
commit. Every randomized input has a fixed seed and its own isolated reset.
"""
import copy
import json
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from test_boundaries import api, observe
from planning_oracle import solve, overlaps, interval


def checked(response, status):
    assert response.status_code == status, (response.status_code, response.text)
    return None if status == 204 else response.json()


class World:
    def __init__(self, api, capacities=(2, 4, 4, 6), pairs=((0, 1), (2, 3))):
        self.c, _, data = api
        data = copy.deepcopy(data)
        r = data['restaurants'][0]
        r['manager_user_ids'] = ['alice']
        r['tables'] = [{'id': f't_{i+1}', 'label': f'Table {i+1}', 'capacity': n} for i, n in enumerate(capacities)]
        r['combinable'] = [[f't_{a+1}', f't_{b+1}'] for a, b in pairs]
        checked(self.c.post('/_test/reset', json=data), 204)
        self.r = r
        self.tokens = {u['id']: checked(self.c.post('/auth/login', json={'email':u['email'], 'password':u['password']}), 200)['token'] for u in data['users']}
        self.rev = 0
        self.seq = 0

    def headers(self, user='alice', key=None):
        result = {'Authorization': 'Bearer '+self.tokens[user]}
        if key is not None: result['Idempotency-Key'] = key
        return result

    def post(self, path, body, key=None, status=201, user='alice'):
        self.seq += 1
        return checked(self.c.post(path, json=body, headers=self.headers(user, key or f'advanced-{self.seq}')), status)

    def get(self, path, user='alice'):
        return checked(self.c.get(path, headers=self.headers(user)), 200)

    def book(self, tables=('t_1',), time='18:00', date='2030-01-01', party=2, user='alice'):
        body = {'restaurant_id': 'r_main', 'table_ids': list(tables), 'starts_at_local': date+'T'+time, 'party_size': party}
        result = self.post('/reservations', body, user=user)
        self.rev += 1
        return result

    def policy(self, capacities, date='2030-01-01', duration=60):
        body = {k: self.r[k] for k in ('slot_minutes', 'cancellation_cutoff_minutes', 'opening_hours')}
        body.update(effective_from=date, reservation_duration_minutes=duration, capacities=capacities)
        result = self.post('/restaurants/r_main/policies', body)
        self.rev += 1
        return result

    def history(self, reference):
        return self.get('/reservations/'+reference+'/history')

    def series(self):
        anchor = self.book()
        result = self.post('/series', {'anchor_reference':anchor['reference'], 'count':4, 'interval_weeks':1}, key='adopt')
        self.rev += 1
        return result


@pytest.mark.parametrize('seed', range(24), ids=[f'P{i+1:03d}-seed-{i}' for i in range(24)])
def test_global_plan_matches_independent_exhaustive_oracle(api, record_property, seed):
    """Compare the exact three-part global optimum, then verify preview/apply/replay effects."""
    rng = random.Random(seed)
    capacities = [rng.choice([2, 3, 4, 5, 6]) for _ in range(4+seed%3)]
    pairs = [(0, 1), (1, 2), (2, 3), (0, len(capacities)-1)][:2+seed%3]
    w = World(api, capacities, pairs)
    current_cap = dict(zip((t['id'] for t in w.r['tables']), capacities))
    options = [(t['id'],) for t in w.r['tables']] + [tuple(p) for p in w.r['combinable']]
    records = [w.book(options[seed%len(options)], party=1+seed%2)]
    candidates = ['17:00', '17:30', '18:00', '18:30', '19:00', '19:30', '20:00']
    for _ in range(100):
        if len(records) >= 3+seed%4: break
        option = rng.choice(options); time = rng.choice(candidates)
        start = datetime.fromisoformat('2030-01-01T'+time).replace(tzinfo=timezone.utc)
        proposal = (start.isoformat(), (start+timedelta(hours=1)).isoformat())
        if any(set(option).intersection(r['table_ids']) and overlaps(proposal, interval(r)) for r in records): continue
        party = rng.randint(1, sum(current_cap[t] for t in option))
        records.append(w.book(option, time=time, party=party))
        if len(records) == 2 and seed%2 == 0:
            current_cap = {t['id']:rng.choice([1,2,4,7]) for t in w.r['tables']}
            w.policy(current_cap)
    # Publishing another policy cannot rewrite the capacities accepted by old bookings.
    if seed%3 == 0:
        w.policy({t['id']:1 for t in w.r['tables']})
    closure = {'table_id':records[0]['table_ids'][0], 'from':'2030-01-01T18:45:00+00:00', 'to':'2030-01-01T19:15:00+00:00'}
    expected = solve(w.r['tables'], w.r['combinable'], records, closure)
    record_property('scenario',json.dumps({'seed':seed,'tables':w.r['tables'],'pairs':w.r['combinable'],'reservations':records,'closure':closure},ensure_ascii=True))
    before = {r['reference']:w.history(r['reference']) for r in records}
    snapshot_before = w.get('/_test/export')
    response = w.c.post('/restaurants/r_main/replans', json=closure, headers=w.headers(key='preview'))
    if expected is None:
        rejected = checked(response, 409)
        assert rejected['error']['code'] == 'no_feasible_plan'
        assert w.get('/_test/export') == snapshot_before
        observe(record_property,seed=seed,bookings=len(records),expected='no_feasible_plan',observed='atomic 409')
        return
    plan = checked(response, 201)
    for field in ('assignments','moved_count','unused_seats'): assert plan[field] == expected[field], (field,plan,expected)
    assert plan['restaurant_revision'] == w.rev
    for r in records:
        assert w.get('/reservations/'+r['reference']) == r
        assert w.history(r['reference']) == before[r['reference']]
    assert w.post('/restaurants/r_main/replans', closure, key='preview', status=200) == plan
    path = '/restaurants/r_main/replans/'+plan['plan_id']+'/apply'
    result = w.post(path, {}, key='apply')
    assert result['restaurant_revision'] == w.rev+1
    wanted = {a['reference']:a for a in expected['assignments']}
    assert [r['reference'] for r in result['reservations']] == list(wanted)
    for old in records:
        new = w.get('/reservations/'+old['reference']); history = w.history(old['reference'])
        assignment = wanted.get(old['reference']); changed = assignment is not None and assignment['changed']
        for field in ('reference','reservation_id','restaurant_id','party_size','starts_at','ends_at','starts_at_local','accepted_terms','created_at','status'):
            assert new[field] == old[field], field
        assert new['revision'] == old['revision']+int(changed)
        assert len(history['entries']) == len(before[old['reference']]['entries'])+int(changed)
        if assignment is not None: assert new['table_ids'] == assignment['table_ids']
        if changed:
            entry = history['entries'][-1]
            assert entry['event'] == 'reassigned' and entry['plan_id'] == plan['plan_id']
            assert entry['changes'] == [{'field':'table_ids','from':old['table_ids'],'to':new['table_ids']}]
        else: assert history == before[old['reference']]
    assert w.post(path, {}, key='apply', status=200) == result
    assert w.post(path, {}, key='another-apply', status=409)['error']['code'] == 'plan_already_applied'
    # A subsequent real mutation must not change the stored successful apply response.
    w.post('/reservations/'+records[0]['reference']+'/cancel', {}, status=200)
    assert w.post(path, {}, key='apply', status=200) == result
    observe(record_property,seed=seed,bookings=len(records),expected=expected,observed={'moved_count':plan['moved_count'],'unused_seats':plan['unused_seats'],'revision':result['restaurant_revision']})


def test_R001_series_skips_exceptions_and_cancelled(api, record_property):
    """Collective time change skips permanent diner exceptions and cancelled siblings."""
    w=World(api);series=w.series();sid=series['series_id'];occ=series['occurrences']
    ref1=occ[1]['reference'];ref2=occ[2]['reference']
    checked(w.c.patch('/reservations/'+ref1,json={'starts_at_local':'2030-01-08T20:00'},headers=w.headers()),200)
    w.post('/reservations/'+ref2+'/cancel',{},status=200)
    before=w.get('/series/'+sid);hist={o['reference']:w.history(o['reference']) for o in before['occurrences']}
    body={'expected_revision':before['revision'],'from_index':0,'local_time':'19:00'}
    after=w.post('/series/'+sid+'/amend',body,key='amend')
    assert after['revision']==before['revision']+1
    for i,(old,new) in enumerate(zip(before['occurrences'],after['occurrences'])):
        if i in (1,2): assert old==new and w.history(old['reference'])==hist[old['reference']]
        else:
            assert new['reservation']['starts_at_local']==old['reservation']['starts_at_local'][:11]+'19:00'
            assert new['reservation']['revision']==old['reservation']['revision']+1 and not new['exception']
    w.post('/reservations/'+occ[0]['reference']+'/cancel',{},status=200)
    assert w.post('/series/'+sid+'/amend',body,key='amend',status=200)==after
    observe(record_property,series_revision=after['revision'],skipped=[1,2],changed=[0,3],original_replay=True)


def test_R002_series_noop_retains_terms(api,record_property):
    """A no-op series amend keeps old policy, histories and revisions after publication."""
    w=World(api);series=w.series();sid=series['series_id']
    w.policy({t['id']:8 for t in w.r['tables']},duration=90)
    hist={o['reference']:w.history(o['reference']) for o in series['occurrences']}
    after=w.post('/series/'+sid+'/amend',{'expected_revision':1,'from_index':0,'local_time':'18:00'})
    assert after==series
    assert all(w.history(ref)==h for ref,h in hist.items())
    observe(record_property,unchanged_series=True,unchanged_histories=True)


def test_R003_series_conflict_rolls_back_all(api,record_property):
    """A late occurrence conflict cannot partially move earlier series members or consume its key."""
    w=World(api);series=w.series();sid=series['series_id'];block=w.book(time='20:00',date='2030-01-22',user='bob')
    before=w.get('/_test/export');body={'expected_revision':1,'from_index':0,'local_time':'20:00'}
    failed=w.post('/series/'+sid+'/amend',body,key='conflict',status=409)
    assert failed['error']['code']=='table_unavailable' and w.get('/_test/export')==before
    w.post('/reservations/'+block['reference']+'/cancel',{},status=200,user='bob')
    result=w.post('/series/'+sid+'/amend',body,key='conflict')
    assert result['revision']==2 and all(o['reservation']['starts_at_local'].endswith('T20:00') for o in result['occurrences'])
    observe(record_property,atomic_failure=True,reused_failed_key=True)


def test_R004_concurrent_series_revision(api,record_property):
    """Twenty competing amendments from one expected revision yield exactly one real change."""
    w=World(api);series=w.series();path='/series/'+series['series_id']+'/amend'
    def send(i):
        return w.c.post(path,json={'expected_revision':1,'from_index':0,'local_time':'19:00' if i%2 else '20:00'},headers=w.headers(key=f'race-{i}'))
    with ThreadPoolExecutor(max_workers=20) as pool: responses=list(pool.map(send,range(20)))
    statuses=[r.status_code for r in responses]
    assert statuses.count(201)==1 and statuses.count(409)==19
    assert all(r.json()['error']['code']=='stale_revision' for r in responses if r.status_code==409)
    current=w.get('/series/'+series['series_id'])
    assert current['revision']==2 and all(o['reservation']['revision']==2 for o in current['occurrences'])
    assert len({o['reservation']['starts_at_local'][11:] for o in current['occurrences']})==1
    observe(record_property,concurrency=20,created=statuses.count(201),stale=statuses.count(409),series_revision=current['revision'])
