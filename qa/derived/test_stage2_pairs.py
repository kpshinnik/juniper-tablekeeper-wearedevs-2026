"""Independent Stage2 pair/resource invariants; no product implementation imports."""
import copy
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import httpx
import pytest
from derived.test_stage1 import headers,snapshot,assert_error

DAY='2030-01-01'


def fixture():
    return {'users':[{'id':'u','email':'u@pairs.test','password':'synthetic-password','display_name':'Diner'}],
        'restaurants':[{'id':'r','name':'Pair garden','timezone':'UTC','slot_minutes':30,
            'reservation_duration_minutes':60,'cancellation_cutoff_minutes':0,
            'opening_hours':[{'weekday':d,'opens':'17:00','closes':'23:00'} for d in 'mon tue wed thu fri sat sun'.split()],
            'tables':[{'id':'a','label':'Window','capacity':2},{'id':'b','label':'Garden','capacity':3},
                      {'id':'c','label':'Courtyard','capacity':5}], 'combinable':[['b','a'],['b','c']]}], 'reservations':[]}


@pytest.fixture
def pairs():
    with httpx.Client(base_url='http://tablekeeper:8080',trust_env=False,timeout=5) as c:
        assert c.post('/_test/reset',json=fixture(),timeout=10).status_code==204
        login=c.post('/auth/login',json={'email':'u@pairs.test','password':'synthetic-password'})
        assert login.status_code==200
        yield c,login.json()['token']


def value(ids=('b','a'),party=5,start='18:00'):
    return {'restaurant_id':'r','table_ids':list(ids),'starts_at_local':DAY+'T'+start,'party_size':party}


def create(c,t,body,key):
    r=c.post('/reservations',json=body,headers=headers(t,key));assert r.status_code==201,r.text
    return r.json()


def available(c,party=1):
    r=c.get('/availability',params={'restaurant_id':'r','date':DAY,'party_size':party});assert r.status_code==200
    return {s['starts_at_local'][-5:]:s for s in r.json()['slots']}


def test_D201_pairs_order_membership_halfopen_and_release(pairs):
    """All eligible singles precede pairs in fixture/declaration order; a pair occupies every member and releases all on cancel, with half-open adjacent starts."""
    c,t=pairs
    s=available(c)['18:00'];assert s['available_table_ids']==['a','b','c']
    assert s['available_options']==[{'table_ids':['a'],'capacity':2},{'table_ids':['b'],'capacity':3},{'table_ids':['c'],'capacity':5},{'table_ids':['b','a'],'capacity':5},{'table_ids':['b','c'],'capacity':8}]
    original=create(c,t,value(),'pair');assert set(original['table_ids'])=={'a','b'} and 'table_id' not in original
    slots=available(c)
    for at in ['17:30','18:00','18:30']:
        assert slots[at]['available_table_ids']==['c']
        assert slots[at]['available_options']==[{'table_ids':['c'],'capacity':5}]
    assert slots['17:00']['available_table_ids']==slots['19:00']['available_table_ids']==['a','b','c']
    assert c.post('/reservations/'+original['reference']+'/cancel',json={},headers=headers(t)).status_code==200
    assert available(c)['18:00']==s
    retry=c.post('/reservations',json=value(),headers=headers(t,'pair'))
    assert retry.status_code==200 and retry.json()==original


@pytest.mark.parametrize('selection,code',[
    (['a','c'],'combination_not_allowed'),(['a','b','c'],'combination_not_allowed'),
    (['b','b'],'validation_failed'),([], 'validation_failed'),
],ids=['D202-nontransitive','D202-three-members','D202-duplicate','D202-empty'])
def test_D202_invalid_pair_retains_state_and_key(pairs,selection,code):
    """Undeclared/transitive/triple/duplicate/empty sets are refused without consuming the key or changing occupancy/state."""
    c,t=pairs;before=snapshot(c)
    assert_error(c.post('/reservations',json=value(selection,2),headers=headers(t,'selection')),422,code)
    assert snapshot(c)==before
    assert create(c,t,value(),'selection')['status']=='confirmed'


def test_D203_both_fields_and_summed_capacity_are_atomic(pairs):
    """Both selector fields are invalid; a party over exact summed capacity fails without consuming its key, then valid pair succeeds."""
    c,t=pairs;before=snapshot(c)
    assert_error(c.post('/reservations',json={**value(),'table_id':'a'},headers=headers(t,'both')),422,'validation_failed')
    assert_error(c.post('/reservations',json=value(party=6),headers=headers(t,'capacity')),422,'party_exceeds_capacity')
    assert snapshot(c)==before
    create(c,t,value(),'capacity')


def test_D204_pair_single_atomic_swap_and_original_receipts(pairs):
    """A listed pair and listed single swap collectively; later amendment/cancel/import leave original creation and ordered move receipts unchanged."""
    c,t=pairs;a=create(c,t,value(),'pair');b=create(c,t,value(['c'],2),'single')
    assert b['table_id']=='c' and b['table_ids']==['c']
    moves={'moves':[{'reference':a['reference'],'table_ids':['c']},{'reference':b['reference'],'table_ids':['a','b']}]}
    moved=c.post('/reservation-moves',json=moves,headers=headers(t,'swap'));assert moved.status_code==201,moved.text
    original=moved.json();assert [r['reference'] for r in original['reservations']]==[a['reference'],b['reference']]
    assert original['reservations'][0]['table_ids']==['c'] and original['reservations'][0]['table_id']=='c'
    assert set(original['reservations'][1]['table_ids'])=={'a','b'} and 'table_id' not in original['reservations'][1]
    assert c.patch('/reservations/'+a['reference'],json={'starts_at_local':DAY+'T20:00'},headers=headers(t)).status_code==200
    assert c.post('/reservations/'+b['reference']+'/cancel',json={},headers=headers(t)).status_code==200
    exported=c.get('/_test/export',timeout=10);assert exported.status_code==200
    assert c.post('/_test/reset',json={'users':[],'restaurants':[],'reservations':[]},timeout=10).status_code==204
    assert c.post('/_test/import',content=json.dumps(exported.json(),allow_nan=False),headers={'Content-Type':'application/json'},timeout=10).status_code==204
    before=snapshot(c)
    replay=c.post('/reservation-moves',json=moves,headers=headers(t,'swap'));assert replay.status_code==200 and replay.json()==original
    for key,body,receipt in [('pair',value(),a),('single',value(['c'],2),b)]:
        replay=c.post('/reservations',json=body,headers=headers(t,key));assert replay.status_code==200 and replay.json()==receipt
    assert snapshot(c)==before


def test_D205_resulting_pair_overlap_rolls_back_all_and_key(pairs):
    """Overlapping final sets reject the whole move, including records/occupancy/receipt key; a corrected collective swap reuses that key."""
    c,t=pairs;a=create(c,t,value(),'pair');b=create(c,t,value(['c'],2),'single')
    before=snapshot(c)
    bad={'moves':[{'reference':a['reference'],'table_ids':['b','c']},{'reference':b['reference'],'table_ids':['c']}]}
    assert_error(c.post('/reservation-moves',json=bad,headers=headers(t,'batch')),409,'table_unavailable')
    assert snapshot(c)==before
    good={'moves':[{'reference':a['reference'],'table_ids':['c']},{'reference':b['reference'],'table_ids':['b','a']}]}
    assert c.post('/reservation-moves',json=good,headers=headers(t,'batch')).status_code==201


def test_D206_unlisted_member_conflict_preserves_original_pair(pairs):
    """A failed pair amendment colliding with an unlisted reservation retains the original complete pair occupancy and identity."""
    c,t=pairs;a=create(c,t,value(),'pair');create(c,t,value(['c'],2),'blocker');before=snapshot(c)
    assert_error(c.patch('/reservations/'+a['reference'],json={'table_ids':['b','c']},headers=headers(t)),409,'table_unavailable')
    assert snapshot(c)==before and c.get('/reservations/'+a['reference'],headers=headers(t)).json()==a


def test_D207_pair_and_member_concurrent_requests_linearize(pairs,record_property):
    """Twenty simultaneous pair/member attempts publish exactly one confirmed reservation with no partial occupancy or duplicate successes."""
    c,t=pairs;gate=threading.Barrier(20)
    def attempt(i):
        with httpx.Client(base_url='http://tablekeeper:8080',trust_env=False,timeout=5) as client:
            body=value() if i%2==0 else value(['b'],2)
            gate.wait();r=client.post('/reservations',json=body,headers=headers(t,'race-'+str(i)))
            return r.status_code,r.json()
    with ThreadPoolExecutor(max_workers=20) as pool:results=list(pool.map(attempt,range(20)))
    assert sum(status==201 for status,_ in results)==1
    assert all(status==201 or (status==409 and data['error']['code']=='table_unavailable') for status,data in results)
    listed=c.get('/reservations',headers=headers(t));assert listed.status_code==200 and len(listed.json()['reservations'])==1
    assert 'b' not in available(c)['18:00']['available_table_ids']
    record_property('observed',json.dumps({'attempts':20,'concurrency':20,'created':1,'refused':19,'committed_reservations':1}))


def test_D208_seeded_cancelled_pair_never_occupies(pairs):
    """A seeded cancelled pair remains visible to its owner while every constituent table and declared option stays available."""
    c,_=pairs;fx=fixture();fx['reservations']=[{**value(),'id':'seed','reference':'SEED01','user_id':'u','status':'cancelled'}]
    assert c.post('/_test/reset',json=fx,timeout=10).status_code==204
    login=c.post('/auth/login',json={'email':'u@pairs.test','password':'synthetic-password'});assert login.status_code==200;t=login.json()['token']
    r=c.get('/reservations/SEED01',headers=headers(t));assert r.status_code==200 and r.json()['status']=='cancelled'
    assert set(r.json()['table_ids'])=={'a','b'} and 'table_id' not in r.json()
    assert available(c)['18:00']['available_table_ids']==['a','b','c']
