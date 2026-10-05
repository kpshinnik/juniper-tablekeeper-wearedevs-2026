"""Concurrency checks use independent HTTP requests and state invariants, max 50 in flight."""
import copy
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
import pytest
from conftest import book,error,headers,reservations
pytestmark=pytest.mark.load


def burst(fn,count=50,workers=50,record=None):
    barrier=threading.Barrier(min(count,workers))
    def run(i):
        if i<workers: barrier.wait(timeout=20)
        start=time.monotonic(); result=fn(i); elapsed=time.monotonic()-start
        assert result.status_code<500, result.text
        assert elapsed<5, f'request latency {elapsed:.3f}s exceeds contract'
        return result,elapsed
    start=time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results=list(pool.map(run,range(count)))
    times=sorted(x[1] for x in results)
    if record:
        for key,value in {'requests':count,'concurrency':workers,'elapsed_s':time.monotonic()-start,
                          'p50_s':statistics.median(times),'p95_s':times[max(0,int(len(times)*.95)-1)],'max_s':max(times)}.items(): record(key,value)
    return [x[0] for x in results]


def codes(responses): return [x.status_code for x in responses]


def test_L001_hot_slot_race(api,world,record_property):
    """50 distinct keys compete for one slot: exactly one create; all others conflict."""
    rs=burst(lambda i:book(api,world),record=record_property)
    assert codes(rs).count(201)==1 and codes(rs).count(409)==49
    assert len(reservations(api,world))==1


def test_L002_identical_retry_storm(api,world,record_property):
    """50 simultaneous identical first-use keys produce one create and 49 identical receipts."""
    rs=burst(lambda i:book(api,world,key='storm'),record=record_property)
    assert codes(rs).count(201)==1 and codes(rs).count(200)==49
    assert all(r.json()==rs[0].json() for r in rs) and len(reservations(api,world))==1


def test_L003_conflicting_key_payloads(api,world,record_property):
    """Concurrent different payloads sharing a key elect one body without two writes."""
    rs=burst(lambda i:book(api,world,key='one-key',body=dict(world.body,party_size=1+i%4)),record=record_property)
    assert codes(rs).count(201)==1
    winner=next(r.json() for r in rs if r.status_code==201)
    for r in rs:
        if r.status_code==409: assert r.json()['error']['code']=='idempotency_key_reuse'
        else: assert r.json()==winner
    assert len(reservations(api,world))==1


def test_L004_distinct_slots_parallel(api,world,record_property):
    """50 independent nonoverlapping writes all commit with unique identities."""
    def request(i):
        date=(datetime.fromisoformat(world.date)+timedelta(days=i//6)).date().isoformat()
        return book(api,world,body=dict(world.body,table_id=f't_{i%6+1}',party_size=1,starts_at_local=date+'T18:00'))
    rs=burst(request,record=record_property)
    assert codes(rs)==[201]*50 and len({r.json()['reference'] for r in rs})==50
    assert len(reservations(api,world))==50


def test_L005_duplicate_signup_race(api,world,record_property):
    """Concurrent signup for one email creates exactly one account."""
    rs=burst(lambda i:api.post('/auth/signup',json={'email':'same@example.test','password':'correct-horse','display_name':'Same'}),record=record_property)
    assert codes(rs).count(201)==1 and codes(rs).count(409)==49
    assert all(r.status_code==201 or r.json()['error']['code']=='email_taken' for r in rs)


def test_L006_login_storm(api,world,record_property):
    """50 password-verifying logins finish within timeout and issue valid independent sessions."""
    rs=burst(lambda i:api.post('/auth/login',json={'email':'alice@example.test','password':'alice-correct-horse'}),record=record_property)
    assert codes(rs)==[200]*50
    assert len({r.json()['token'] for r in rs})==50
    assert all(api.get('/reservations',headers={'Authorization':'Bearer '+r.json()['token']}).status_code==200 for r in rs)


def test_L007_cancel_storm(api,world,record_property):
    """Repeated simultaneous cancellation has one stable outcome and releases the slot."""
    ref=book(api,world).json()['reference']
    rs=burst(lambda i:api.post(f'/reservations/{ref}/cancel',json={},headers=headers(world)),record=record_property)
    assert codes(rs)==[200]*50 and all(r.json()['status']=='cancelled' for r in rs)
    assert book(api,world,user='bob').status_code==201


def test_L008_amend_competes_for_target(api,world,record_property):
    """Two bookings race to move into one target: one winner and unchanged losing occupancy."""
    a=book(api,world).json(); b=book(api,world,body=dict(world.body,table_id='t_3')).json()
    rs=burst(lambda i:api.patch('/reservations/'+[a,b][i]['reference'],json={'table_id':'t_4'},headers=headers(world)),count=2,workers=2,record=record_property)
    assert sorted(codes(rs))==[200,409]
    current=reservations(api,world)
    assert sum(x['table_id']=='t_4' for x in current)==1 and len(current)==2


def test_L009_batch_retry_storm(api,world,record_property):
    """An atomic swap replayed concurrently returns one immutable batch receipt."""
    a=book(api,world).json(); b=book(api,world,body=dict(world.body,table_id='t_3')).json()
    body={'moves':[{'reference':a['reference'],'table_id':'t_3'},{'reference':b['reference'],'table_id':'t_2'}]}
    rs=burst(lambda i:api.post('/reservation-moves',json=body,headers=headers(world,key='swap')),record=record_property)
    assert codes(rs).count(201)==1 and codes(rs).count(200)==49
    assert all(r.json()==rs[0].json() for r in rs)


def test_L010_availability_storm(api,world,record_property):
    """200 availability reads at concurrency 50 retain complete deterministic slot results."""
    params={'restaurant_id':'r_main','date':world.date,'party_size':3}
    expected=api.get('/availability',params=params).json()
    rs=burst(lambda i:api.get('/availability',params=params),count=200,record=record_property)
    assert codes(rs)==[200]*200 and all(r.json()==expected for r in rs)


def test_L011_invalid_write_storm(api,world,record_property):
    """50 invalid writes neither crash the service nor allocate records."""
    rs=burst(lambda i:book(api,world,body=dict(world.body,party_size=-i-1)),record=record_property)
    assert codes(rs)==[422]*50 and reservations(api,world)==[]


def test_L012_unauthorized_storm(api,world,record_property):
    """Forged bearer traffic remains isolated from authenticated sessions under load."""
    rs=burst(lambda i:api.get('/reservations',headers={'Authorization':f'Bearer forged-{i}'}),record=record_property)
    assert codes(rs)==[401]*50 and api.get('/reservations',headers=headers(world)).status_code==200


def test_L013_export_during_bookings(api,world,record_property):
    """Concurrent snapshots and writes are consistent enough to restore and replay all included data."""
    def request(i):
        if i%2: return api.get('/_test/export')
        date=(datetime.fromisoformat(world.date)+timedelta(days=i)).date().isoformat()
        return book(api,world,key=f'export-{i}',body=dict(world.body,starts_at_local=date+'T18:00'))
    rs=burst(request,record=record_property)
    assert all(r.status_code==(200 if i%2 else 201) for i,r in enumerate(rs))
    for snapshot in [rs[i].json() for i in range(1,50,2)]:
        assert api.post('/_test/import',json=snapshot).status_code==204
        assert api.get('/reservations',headers=headers(world)).status_code==200


def test_L014_parallel_import_same_snapshot(api,world,record_property):
    """Parallel replacement with one snapshot never duplicates bookings or loses retained credentials."""
    a=book(api,world,key='saved').json(); snapshot=api.get('/_test/export').json()
    rs=burst(lambda i:api.post('/_test/import',json=snapshot),record=record_property)
    assert codes(rs)==[204]*50 and reservations(api,world)==[a]
    assert book(api,world,key='saved').json()==a


def test_L015_snapshot_reads_do_not_mutate(api,world,record_property):
    """100 concurrent exports are read-only and return the same complete state."""
    book(api,world); original=api.get('/_test/export').json()
    rs=burst(lambda i:api.get('/_test/export'),count=100,record=record_property)
    assert codes(rs)==[200]*100 and all(r.json()==original for r in rs)


def test_L016_health_with_write_load(api,world,record_property):
    """Health remains responsive while authenticated requests contend for storage."""
    rs=burst(lambda i:api.get('/health') if i%2 else book(api,world),record=record_property)
    assert all(rs[i].status_code==200 and rs[i].json()=={'status':'ok'} for i in range(1,50,2))
    assert codes(rs).count(201)==1


def test_L017_two_users_same_key(api,world,record_property):
    """Concurrent callers may independently use the same key without receipt leakage."""
    rs=burst(lambda i:book(api,world,user='alice' if i%2==0 else 'bob',key='shared',body=dict(world.body,table_id='t_2' if i%2==0 else 't_3')),record=record_property)
    assert codes(rs).count(201)==2 and codes(rs).count(200)==48
    assert len({r.json()['reference'] for r in rs})==2
    assert all(rs[i].json()==rs[i%2].json() for i in range(50))


def test_L018_overlap_different_starts(api,world,record_property):
    """Distinct starts in the same occupied interval cannot evade the concurrency lock."""
    rs=burst(lambda i:book(api,world,body=dict(world.body,starts_at_local=world.date+('T18:00' if i%2 else 'T18:30'))),record=record_property)
    assert codes(rs).count(201)==1 and codes(rs).count(409)==49


def test_L019_adjacent_intervals(api,world,record_property):
    """Adjacent half-open intervals may be booked simultaneously without false conflicts."""
    rs=burst(lambda i:book(api,world,body=dict(world.body,starts_at_local=world.date+f'T{i:02}:00')),count=20,workers=20,record=record_property)
    assert codes(rs)==[201]*20 and len(reservations(api,world))==20


def test_L020_cancel_amend_race(api,world,record_property):
    """Racing cancellation and amendment produces a serializable cancelled final record."""
    a=book(api,world).json(); ref=a['reference']
    def request(i):
        return api.post(f'/reservations/{ref}/cancel',json={},headers=headers(world)) if i%2 else api.patch(f'/reservations/{ref}',json={'party_size':1},headers=headers(world))
    rs=burst(request,record=record_property)
    assert all(rs[i].status_code==200 for i in range(1,50,2))
    assert all(rs[i].status_code in (200,409) for i in range(0,50,2))
    assert reservations(api,world)[0]['status']=='cancelled'
