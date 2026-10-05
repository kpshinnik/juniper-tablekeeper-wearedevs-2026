"""Stage4 HTTP obligations derived before inspecting its implementation.

Only public HTTP contracts are used here. The large-objective case deliberately
keeps a huge common cost while two repairs differ by one; no power is expanded
by this client. Opaque snapshot corruptions are a separate, attributed adapter.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
import time
import uuid

import httpx
import pytest

from derived.test_stage1 import headers, assert_error, snapshot
from derived.test_stage3 import (fixture, policy, PASSWORD, booking, adopt,
                                series, current, history, publish, patch)

DAY = '2030-01-01'


class DeadlineClient(httpx.Client):
    """Measure complete receive/decompression, separately from later JSON parse."""
    def request(self, method, url, **kwargs):
        started=time.monotonic()
        response=super().request(method,url,**kwargs)
        elapsed=time.monotonic()-started
        bound=10 if str(url).startswith('/_test/') else 5
        assert elapsed<=bound, {'method':method,'path':str(url),'receive_s':elapsed,'bound_s':bound}
        return response


def require(r, status=201):
    assert r.status_code == status, (r.status_code, r.text[:1000])
    return json.loads(r.content, parse_float=Decimal) if r.content else None


def setup(c, fx=None, raw=None):
    require(c.post('/_test/reset', content=raw, headers={'Content-Type': 'application/json'}, timeout=10)
            if raw is not None else c.post('/_test/reset', json=fx or fixture(), timeout=10), 204)
    return {who: require(c.post('/auth/login', json={'email': who+'@stage3.test',
            'password': PASSWORD}), 200)['token'] for who in ('diner', 'manager', 'other')}


@pytest.fixture
def world4():
    with DeadlineClient(base_url='http://tablekeeper:8080', trust_env=False, timeout=5) as c:
        yield c, setup(c)


def closure(table='a', start=DAY+'T18:00:00+00:00', end=DAY+'T19:00:00+00:00'):
    return {'table_id': table, 'from': start, 'to': end}


def preview(c, tok, body=None, key=None, rid='r'):
    return require(c.post('/restaurants/'+rid+'/replans', json=body or closure(),
                   headers=headers(tok['manager'], key or uuid.uuid4().hex)))


def apply(c, tok, plan, key=None, rid='r'):
    return require(c.post('/restaurants/'+rid+'/replans/'+plan['plan_id']+'/apply', json={},
                   headers=headers(tok['manager'], key or uuid.uuid4().hex)))


def restaurant_revision(c, tok, rid='r', table='a'):
    # Public read-through witness: an empty, unapplied preview may store only a
    # plan and receipt. It cannot itself increment this counter.
    return preview(c, tok, closure(table, '2040-01-01T00:00:00Z', '2040-01-01T00:01:00Z'), rid=rid)['restaurant_revision']


def amend(c, tok, agreement, time='20:00', start=0, key=None, revision=None):
    return c.post('/series/'+agreement['series_id']+'/amend',
                  json={'expected_revision': agreement['revision'] if revision is None else revision,
                        'from_index': start, 'local_time': time},
                  headers=headers(tok['diner'], key or uuid.uuid4().hex))


@pytest.mark.parametrize('field,value', [('from','2030-01-01T18:00:00'), ('to','2030-01-01T19:00'),
    ('from','2030-02-30T18:00:00Z'), ('to',DAY+'T18:00:00Z'), ('to',DAY+'T17:00:00Z'),
    ('from',DAY+'T18:00:00+24:00'), ('from',''), ('to','garbage')], ids=[
    'offset-required-from','offset-required-to','invalid-date','empty-interval','reverse-interval',
    'invalid-offset','empty-instant','invalid-instant'])
def test_D401_invalid_closure_nonmutation(world4, field, value):
    """Malformed interval values reject422 and leave the key and complete state unclaimed."""
    c,tok=world4; body=closure(); body[field]=value; before=snapshot(c)
    assert_error(c.post('/restaurants/r/replans', json=body, headers=headers(tok['manager'],'retry')),422,'validation_failed')
    assert snapshot(c)==before
    preview(c,tok,key='retry')


@pytest.mark.parametrize('operation',['preview','apply'])
def test_D401_manager_boundary_and_missing_key(world4, operation):
    """Both planner writes require manager authorization and a nonempty idempotency key."""
    c,tok=world4; plan=preview(c,tok)
    path='/restaurants/r/replans'+('/'+plan['plan_id']+'/apply' if operation=='apply' else '')
    body={} if operation=='apply' else closure(); before=snapshot(c)
    for auth,status,code in [({},401,'unauthenticated'),(headers(tok['diner'],'x'),403,'forbidden'),
                            ({'Authorization':'Bearer '+tok['manager']},400,'missing_idempotency_key')]:
        assert_error(c.post(path,json=body,headers=auth),status,code)
    assert snapshot(c)==before


def test_D401_unknown_and_cross_restaurant_plan(world4):
    """Unknown table/restaurant/plan and a real plan under another restaurant are404 without mutation."""
    c,_=world4; fx=fixture(); other=copy.deepcopy(fx['restaurants'][0]); other['id']='other-r'
    fx['restaurants'].append(other); tok=setup(c,fx); plan=preview(c,tok); before=snapshot(c)
    for path,body in [('/restaurants/missing/replans',closure()),('/restaurants/r/replans',closure('missing')),
        ('/restaurants/r/replans/missing/apply',{}),('/restaurants/other-r/replans/'+plan['plan_id']+'/apply',{})]:
        assert_error(c.post(path,json=body,headers=headers(tok['manager'],'absent')),404,'not_found')
    assert snapshot(c)==before


def test_D401_six_tables_four_pairs_six_considered_supported(world4):
    """The inclusive required planning limits must support a feasible joint assignment."""
    c,_=world4; fx=fixture(); r=fx['restaurants'][0]
    r['tables']=[{'id':x,'label':x,'capacity':4} for x in 'abcdef']
    r['combinable']=[['a','b'],['b','c'],['c','d'],['d','e']]
    tok=setup(c,fx); refs=[]
    for i in range(6):
        _,b=booking(c,tok,key='b'+str(i),starts_at_local=DAY+f'T{10+i:02}:00')
        refs.append(b['reference'])
    p=preview(c,tok,closure('a',DAY+'T09:00:00Z',DAY+'T17:00:00Z'))
    assert len(p['assignments'])==6 and p['moved_count']==6
    assert [x['reference'] for x in p['assignments']]==sorted(refs)
    assert all(x['table_ids']==['b'] for x in p['assignments'])
    assert len(apply(c,tok,p)['reservations'])==6


def test_D402_full_interval_fixed_conflict_and_global_considered(world4):
    """A fixed booking outside the closure still blocks an assignment over the considered booking's full interval."""
    c,_=world4; fx=fixture(); fx['restaurants'][0]['slot_minutes']=30
    tok=setup(c,fx)
    _,moving=booking(c,tok,table='a')
    _,unchanged=booking(c,tok,key='overlapping-other-seat',table='c',starts_at_local=DAY+'T18:00')
    _,fixed=booking(c,tok,key='fixed-outside-window',table='b',starts_at_local=DAY+'T17:30')
    # To make c unavailable to moving too, the other considered booking occupies
    # the same interval. No whole-interval option is feasible, despite no fixed booking
    # overlapping this short closure window.
    body=closure('a',DAY+'T18:30:00Z',DAY+'T18:45:00Z'); before=snapshot(c)
    assert_error(c.post('/restaurants/r/replans',json=body,headers=headers(tok['manager'],'plan')),409,'no_feasible_plan')
    assert snapshot(c)==before
    require(c.post('/reservations/'+fixed['reference']+'/cancel',headers=headers(tok['diner'])),200)
    p=preview(c,tok,body,key='plan')
    assert set(x['reference'] for x in p['assignments'])=={moving['reference'],unchanged['reference']}
    assert {x['reference']:x['table_ids'] for x in p['assignments']}=={moving['reference']:['b'],unchanged['reference']:['c']}
    assert p['moved_count']==1


def test_D402_prior_closure_and_half_open_boundaries(world4):
    """Applied closures block a whole candidate interval; touching closure endpoints do not overlap."""
    c,tok=world4
    apply(c,tok,preview(c,tok,closure('b',DAY+'T17:30:00Z',DAY+'T18:30:00Z')))
    _,b=booking(c,tok)
    p=preview(c,tok,closure('a',DAY+'T18:30:00Z',DAY+'T19:00:00Z'))
    assert p['assignments']==[{'reference':b['reference'],'table_ids':['c'],'changed':True}]
    apply(c,tok,p)
    booking(c,tok,key='touches-b-end',table='b',starts_at_local=DAY+'T18:30')
    booking(c,tok,key='touches-a-end',table='a',starts_at_local=DAY+'T19:00')
    booking(c,tok,key='touches-b-start',table='b',starts_at_local=DAY+'T16:30')


@pytest.mark.parametrize('exponent',[16,40,400,100000000],ids=['beyond-binary-safe','decimal-context','beyond-float','compact-extreme'])
def test_D403_exact_objective_small_difference_beside_huge_common_cost(world4, exponent, record_property):
    """Exact waste distinguishes H from H+1 beside an unchanged H-seat table; the lower-waste higher-rank option wins through retry/apply/import."""
    c,_=world4; fx=fixture(); r=fx['restaurants'][0]
    r['tables']=[{'id':t,'label':t,'capacity':cap} for t,cap in [('a',2),('b',4),('c',3),('huge','HUGE_MARKER')]]
    r['combinable']=[]
    raw=json.dumps(fx).replace('"HUGE_MARKER"','1e'+str(exponent)).encode()
    tok=setup(c,raw=raw)
    _,large=booking(c,tok,key='huge-common',table='huge',party=1)
    _,moving=booking(c,tok,key='move',table='a',party=2)
    body=closure(); h=headers(tok['manager'],'exact-plan')
    response=c.post('/restaurants/r/replans',json=body,headers=h); p=require(response)
    assert p['unused_seats']==Decimal('1e'+str(exponent))
    assert p['moved_count']==1
    assert {x['reference']:x['table_ids'] for x in p['assignments']}=={large['reference']:['huge'],moving['reference']:['c']}
    assert require(c.post('/restaurants/r/replans',json=body,headers=h),200)==p
    result=apply(c,tok,p,key='exact-apply')
    assert next(x for x in result['reservations'] if x['reference']==moving['reference'])['table_ids']==['c']
    exported=c.get('/_test/export',timeout=10); require(exported,200)
    require(c.post('/_test/reset',json={'users':[],'restaurants':[],'reservations':[]},timeout=10),204)
    require(c.post('/_test/import',content=exported.content,headers={'Content-Type':'application/json'},timeout=10),204)
    assert require(c.post('/restaurants/r/replans',json=body,headers=h),200)==p
    assert require(c.post('/restaurants/r/replans/'+p['plan_id']+'/apply',json={},headers=headers(tok['manager'],'exact-apply')),200)==result
    record_property('observed',json.dumps({'exponent':exponent,'winning_unused_seats':'1e'+str(exponent),
        'rejected_alternative_unused_seats':'1e'+str(exponent)+'+1','lower_waste_beats_lower_rank':True,
        'complete_preview_receive_bytes':len(response.content),'original_receipts_after_import':True}))


def test_D403_rank_tie_and_per_booking_accepted_capacities(world4):
    """Equal waste chooses fixture rank, while a later policy cannot rewrite a booking's accepted capacities."""
    c,_=world4; fx=fixture(); fx['restaurants'][0]['tables']=[{'id':x,'label':x,'capacity':4} for x in 'abc']
    tok=setup(c,fx); _,b=booking(c,tok,party=4)
    publish(c,tok,policy(capacities={'a':1,'b':1,'c':100}))
    p=preview(c,tok)
    assert p['unused_seats']==0 and p['assignments']==[{'reference':b['reference'],'table_ids':['b'],'changed':True}]
    got=apply(c,tok,p)['reservations'][0]
    assert got['accepted_terms']==b['accepted_terms'] and got['ends_at']==b['ends_at']


@pytest.mark.parametrize('change',['create','patch','cancel','policy','adopt','moves','other-apply'])
def test_D404_every_restaurant_mutation_stales_plan(world4, change):
    """Each intervening successful restaurant mutation invalidates an old plan, with atomic refusal."""
    c,tok=world4; _,b=booking(c,tok,table='c'); p=preview(c,tok)
    if change=='create': booking(c,tok,key='later',table='b')
    elif change=='patch': require(patch(c,tok,b['reference'],{'party_size':3}),200)
    elif change=='cancel': require(c.post('/reservations/'+b['reference']+'/cancel',headers=headers(tok['diner'])),200)
    elif change=='policy': publish(c,tok)
    elif change=='adopt': adopt(c,tok,b['reference'])
    elif change=='moves': require(c.post('/reservation-moves',json={'moves':[{'reference':b['reference'],'party_size':3}]},headers=headers(tok['diner'],'moves')))
    else: apply(c,tok,preview(c,tok,closure('b','2040-01-01T10:00:00Z','2040-01-01T11:00:00Z')))
    before=snapshot(c)
    assert_error(c.post('/restaurants/r/replans/'+p['plan_id']+'/apply',json={},headers=headers(tok['manager'],'apply')),409,'stale_plan')
    assert snapshot(c)==before


def test_D404_noops_replays_preview_and_other_restaurant_do_not_stale(world4, record_property):
    """No-op and replay writes plus another restaurant's changes leave the plan valid."""
    c,_=world4; fx=fixture(); r2=copy.deepcopy(fx['restaurants'][0]); r2['id']='other-r'; fx['restaurants'].append(r2)
    tok=setup(c,fx); body,b=booking(c,tok,table='c'); p=preview(c,tok)
    original_history=history(c,tok['diner'],b['reference'])
    assert p['restaurant_revision']==1 and p['moved_count']==0
    require(patch(c,tok,b['reference'],{'party_size':2}),200)
    require(c.post('/reservations',json=body,headers=headers(tok['diner'],'book')),200)
    require(c.post('/reservation-moves',json={'moves':[{'reference':b['reference']}]},headers=headers(tok['diner'],'noops')))
    preview(c,tok)
    other_plan=preview(c,tok,rid='other-r')
    assert other_plan['restaurant_revision']==0
    other_applied=apply(c,tok,other_plan,rid='other-r',key='other-apply')
    assert other_applied['restaurant_revision']==1 and other_applied['reservations']==[]
    # The applied closure belongs only to other-r. It cannot alter r's
    # booking, its history or its current seating availability.
    for rid,available in [('r',True),('other-r',False)]:
        slots=require(c.get('/availability',params={'restaurant_id':rid,'date':DAY,'party_size':2}),200)['slots']
        slot=next(x for x in slots if x['starts_at_local']==DAY+'T18:00')
        assert ('a' in slot['available_table_ids']) is available
    assert current(c,tok['diner'],b['reference'])==b
    assert history(c,tok['diner'],b['reference'])==original_history
    applied=apply(c,tok,p,key='original-apply')
    assert applied['restaurant_revision']==p['restaurant_revision']+1
    assert applied['reservations']==[b]
    assert current(c,tok['diner'],b['reference'])==b
    assert history(c,tok['diner'],b['reference'])==original_history
    before=snapshot(c)
    for rid,plan,receipt,key in [('r',p,applied,'original-apply'),('other-r',other_plan,other_applied,'other-apply')]:
        assert require(c.post('/restaurants/'+rid+'/replans/'+plan['plan_id']+'/apply',json={},headers=headers(tok['manager'],key)),200)==receipt
        assert snapshot(c)==before
    record_property('observed',json.dumps({'other_restaurant_apply':201,'other_revision':1,
        'original_restaurant_apply':201,'original_revision':2,'noops_replays_preview_not_stale':True,
        'unmoved_booking_and_history_unchanged':True,'closures_independent':True,
        'two_application_replays':200,'exact_replay_nonmutation':True}))


def test_D404_empty_closure_counter_and_idempotency_precedence(world4):
    """Empty plans still apply one closure/counter; different keys see already-applied, original key remains immutable even after later writes."""
    c,tok=world4; p=preview(c,tok,key='preview'); assert p['restaurant_revision']==0 and p['assignments']==[]
    assert restaurant_revision(c,tok)==0
    r=apply(c,tok,p,key='apply'); assert r['restaurant_revision']==1 and r['reservations']==[]
    booking(c,tok,table='b')
    path='/restaurants/r/replans/'+p['plan_id']+'/apply'; before=snapshot(c)
    assert_error(c.post(path,json={},headers=headers(tok['manager'],'new')),409,'plan_already_applied')
    assert require(c.post(path,json={},headers=headers(tok['manager'],'apply')),200)==r
    assert_error(c.post(path,json={'changed':True},headers=headers(tok['manager'],'apply')),409,'idempotency_key_reuse')
    assert snapshot(c)==before and restaurant_revision(c,tok)==2


def test_D405_cutoff_bypass_and_closure_explanations(world4):
    """Operator repair can move a past booking; closure rejects create/amend and independently explains no_overlap false."""
    c,tok=world4; body,b=booking(c,tok,date='2000-01-01'); oldh=history(c,tok['diner'],b['reference'])
    assert_error(patch(c,tok,b['reference'],{'table_id':'b'}),409,'cutoff_passed')
    p=preview(c,tok,closure('a','2000-01-01T18:00:00Z','2000-01-01T19:00:00Z'))
    moved=apply(c,tok,p)['reservations'][0]
    assert moved['revision']==b['revision']+1
    for key in ('reservation_id','reference','party_size','starts_at','ends_at','starts_at_local','created_at','accepted_terms'):
        assert moved[key]==b[key]
    h=history(c,tok['diner'],b['reference']); assert h[:-1]==oldh and h[-1]['event']=='reassigned'
    assert h[-1]['plan_id']==p['plan_id'] and h[-1]['changes']==[{'field':'table_ids','from':['a'],'to':['b']}]
    assert_error(c.post('/reservations',json=body,headers=headers(tok['diner'],'closed-create')),409,'table_unavailable')
    slots=require(c.get('/availability',params={'restaurant_id':'r','date':'2000-01-01','party_size':101,'explain':'true'}),200)['slots']
    s=next(x for x in slots if x['starts_at_local']=='2000-01-01T18:00')
    assert [x['holds'] for x in s['explain'][0]['rules']]==[False,False]


def test_D405_apply_two_members_once_and_no_exception(world4):
    """A wide plan moves several members, increments the series once, retains scheduled dates/flags, then amend retains repaired tables."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference']); refs=[o['reference'] for o in s['occurrences']]
    oldh={r:history(c,tok['diner'],r) for r in refs}
    p=preview(c,tok,closure('a','2030-01-01T00:00:00Z','2030-01-16T00:00:00Z'))
    assert p['moved_count']==3
    applied=apply(c,tok,p); now=series(c,tok,s['series_id']); assert now['revision']==2
    assert applied['restaurant_revision']==p['restaurant_revision']+1
    for o in now['occurrences']:
        assert not o['exception'] and o['reservation']['table_ids']==['b']
        assert o['reservation']['revision']==2
        h=history(c,tok['diner'],o['reference']); assert h[:-1]==oldh[o['reference']] and h[-1]['event']=='reassigned'
    changed=require(amend(c,tok,now))
    assert changed['revision']==3
    for old,new in zip(now['occurrences'],changed['occurrences'],strict=True):
        assert new['reservation']['table_ids']==['b'] and not new['exception']
        assert new['reservation']['starts_at_local']==old['reservation']['starts_at_local'][:11]+'20:00'
    assert restaurant_revision(c,tok)==p['restaurant_revision']+2


AMEND_BAD=[('expected_revision',0),('expected_revision',True),('expected_revision','1'),('expected_revision',1.5),
    ('from_index',-1),('from_index',3),('from_index',True),('from_index','0'),('from_index',0.5),
    ('local_time','24:00'),('local_time','9:00'),('local_time','20:00:00'),('local_time','20:00Z'),('local_time',''),
    ('local_time',None)]


@pytest.mark.parametrize('field,value',AMEND_BAD,ids=['invalid-'+str(i+1) for i in range(len(AMEND_BAD))])
def test_D406_invalid_amendment_shape(world4,field,value):
    """Amendment schema rejects wrong formats/ranges/types before publishing any state or key."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference'])
    body={'expected_revision':1,'from_index':0,'local_time':'20:00'}; body[field]=value; before=snapshot(c)
    assert_error(c.post('/series/'+s['series_id']+'/amend',json=body,headers=headers(tok['diner'],'retry')),422,'validation_failed')
    assert snapshot(c)==before
    require(amend(c,tok,s,key='retry'))


@pytest.mark.parametrize('field',['expected_revision','from_index','local_time'])
def test_D406_amendment_required_fields(world4,field):
    """Each amendment field is required; omission returns422 with exact state unchanged."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference'])
    body={'expected_revision':1,'from_index':0,'local_time':'20:00'}; del body[field]; before=snapshot(c)
    assert_error(c.post('/series/'+s['series_id']+'/amend',json=body,headers=headers(tok['diner'])),422,'validation_failed')
    assert snapshot(c)==before


def test_D406_owner_permissions_and_stale_precedence(world4):
    """Amend is owner-only; stale revision wins over a resulting off-grid local time."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference']); path='/series/'+s['series_id']+'/amend'
    body={'expected_revision':1,'from_index':0,'local_time':'20:00'}; before=snapshot(c)
    for auth,status,code in [({},401,'unauthenticated'),(headers(tok['other']),404,'not_found'),
        (headers(tok['manager']),404,'not_found'),({'Authorization':'Bearer '+tok['diner']},400,'missing_idempotency_key')]:
        assert_error(c.post(path,json=body,headers=auth),status,code)
    assert_error(amend(c,tok,s,time='20:01',revision=99),409,'stale_revision')
    assert snapshot(c)==before


def test_D407_empty_eligible_noop_terms_original_receipts(world4):
    """Permanent reverted exceptions and cancelled members are excluded; an empty eligible set succeeds without mutation."""
    c,tok=world4; body,b=booking(c,tok); sb,s=adopt(c,tok,b['reference']); refs=[o['reference'] for o in s['occurrences']]
    require(patch(c,tok,refs[0],{'party_size':3}),200); require(patch(c,tok,refs[0],{'party_size':2}),200)
    for r in refs[1:]: require(c.post('/reservations/'+r+'/cancel',headers=headers(tok['diner'])),200)
    s=series(c,tok,s['series_id']); assert s['occurrences'][0]['exception']
    before_rev=restaurant_revision(c,tok); before_records=copy.deepcopy(s)
    result=require(amend(c,tok,s,key='empty')); assert result==before_records
    assert restaurant_revision(c,tok)==before_rev
    assert require(amend(c,tok,s,key='empty'),200)==result
    assert require(c.post('/reservations',json=body,headers=headers(tok['diner'],'book')),200)==b
    assert require(c.post('/series',json=sb,headers=headers(tok['diner'],'series')),200)['revision']==1


def test_D407_nonoccupancy_precedes_earlier_occupancy_and_rolls_back(world4):
    """A later occurrence's off-grid policy error outranks an earlier occupancy conflict, with no partial mutation."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference'])
    booking(c,tok,key='block',starts_at_local=DAY+'T20:30')
    publish(c,tok,policy('2030-01-08',slot_minutes=60))
    before=snapshot(c)
    assert_error(amend(c,tok,s,time='20:30',key='refused'),422,'not_on_slot_grid')
    assert snapshot(c)==before
    # Same failed key is free for a valid request; no phantom receipt survived.
    require(amend(c,tok,s,time='22:00',key='refused'))


def test_D407_original_dates_after_individual_move_remain_excluded(world4):
    """Moving an occurrence to another date permanently excludes it; eligible members keep their own original dates and current seating."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference']); middle=s['occurrences'][1]['reference']
    require(patch(c,tok,middle,{'starts_at_local':'2030-02-02T18:00','table_id':'c'}),200)
    now=series(c,tok,s['series_id']); changed=require(amend(c,tok,now,start=1))
    assert changed['occurrences'][0]==now['occurrences'][0] and changed['occurrences'][1]==now['occurrences'][1]
    assert changed['occurrences'][2]['reservation']['starts_at_local']=='2030-01-15T20:00'
    assert not changed['occurrences'][2]['exception']


def test_D408_competing_plans_one_atomic_application(world4):
    """Different plans of the same restaurant revision cannot both publish closures and assignments."""
    c,tok=world4; _,b=booking(c,tok); p=preview(c,tok); q=preview(c,tok)
    def send(item):
        return c.post('/restaurants/r/replans/'+item['plan_id']+'/apply',json={},headers=headers(tok['manager'],item['plan_id']))
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(send,[p,q]))
    assert sorted(r.status_code for r in results)==[201,409]
    assert next(r for r in results if r.status_code==409).json()['error']['code']=='stale_plan'
    assert current(c,tok['diner'],b['reference'])['revision']==2
    assert len(history(c,tok['diner'],b['reference']))==2
    assert restaurant_revision(c,tok)==2


def test_D409_snapshot_retains_unapplied_plan_and_all_original_receipts(world4):
    """A valid replacement snapshot retains pending plan validity, later applied plan/amend receipts, current series and immutable originals."""
    c,tok=world4; body,b=booking(c,tok); sb,s=adopt(c,tok,b['reference'])
    p=preview(c,tok,key='saved-plan'); exported=c.get('/_test/export',timeout=10); require(exported,200)
    booking(c,tok,key='discard',table='c',date='2031-01-01')
    require(c.post('/_test/import',content=exported.content,headers={'Content-Type':'application/json'},timeout=10),204)
    applied=apply(c,tok,p,key='saved-apply'); now=series(c,tok,s['series_id'])
    amended=require(amend(c,tok,now,key='saved-amend'))
    raw=c.get('/_test/export',timeout=10); require(raw,200)
    require(c.post('/_test/reset',json={'users':[],'restaurants':[],'reservations':[]},timeout=10),204)
    require(c.post('/_test/import',content=raw.content,headers={'Content-Type':'application/json'},timeout=10),204)
    assert series(c,tok,s['series_id'])==amended
    assert require(c.post('/reservations',json=body,headers=headers(tok['diner'],'book')),200)==b
    assert require(c.post('/series',json=sb,headers=headers(tok['diner'],'series')),200)==s
    assert require(c.post('/restaurants/r/replans',json=closure(),headers=headers(tok['manager'],'saved-plan')),200)==p
    assert require(c.post('/restaurants/r/replans/'+p['plan_id']+'/apply',json={},headers=headers(tok['manager'],'saved-apply')),200)==applied
    assert require(amend(c,tok,now,key='saved-amend'),200)==amended


@pytest.mark.parametrize('operation',['preview','apply','amend'])
def test_D412_new_write_unknown_exact_identity_and_replay_precedence(world4,operation):
    """Unknown fields do not change semantics, but their exact parsed values remain in each new write's immutable identity."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference'])
    if operation=='preview': path='/restaurants/r/replans'; body=closure(); who='manager'
    elif operation=='apply':
        p=preview(c,tok); path='/restaurants/r/replans/'+p['plan_id']+'/apply'; body={}; who='manager'
    else:
        path='/series/'+s['series_id']+'/amend'; body={'expected_revision':1,'from_index':0,'local_time':'20:00'}; who='diner'
    body['unknown']={'unicode':'雪\u0000\ud800','exact':'EXACT_NUMBER','boolean':True,'nested':[[[]]]}
    raw=json.dumps(body).replace('"EXACT_NUMBER"','1e400').encode()
    original=require(c.post(path,content=raw,headers=headers(tok[who],'exact-identity')))
    equivalent=json.dumps(body,sort_keys=True,indent=1).replace('"EXACT_NUMBER"','10e399').encode()
    before=snapshot(c)
    assert require(c.post(path,content=equivalent,headers=headers(tok[who],'exact-identity')),200)==original
    changed=copy.deepcopy(body); changed['unknown']['boolean']=1
    different=json.dumps(changed).replace('"EXACT_NUMBER"','1e400').encode()
    assert_error(c.post(path,content=different,headers=headers(tok[who],'exact-identity')),409,'idempotency_key_reuse')
    assert snapshot(c)==before


@pytest.mark.parametrize('transition',['spring-gap','fall-first-fold'])
def test_D413_series_amendment_real_dst_dates(world4,transition):
    """Amendments use each original local date: a generated gap rolls everything back, and a fold uses its first absolute occurrence."""
    c,_=world4; tok=setup(c,fixture(zone='America/New_York'))
    if transition=='spring-gap':
        _,b=booking(c,tok,date='2030-03-03',starts_at_local='2030-03-03T01:30')
        _,s=adopt(c,tok,b['reference']); before=snapshot(c)
        assert_error(amend(c,tok,s,time='02:30',key='dst'),422,'invalid_local_time')
        assert snapshot(c)==before
        require(amend(c,tok,s,time='03:30',key='dst'))
    else:
        _,b=booking(c,tok,date='2030-10-27',starts_at_local='2030-10-27T00:30')
        _,s=adopt(c,tok,b['reference']); changed=require(amend(c,tok,s,time='01:30'))
        fold=changed['occurrences'][1]['reservation']
        assert fold['starts_at']=='2030-11-03T01:30:00-04:00'
        assert fold['ends_at']=='2030-11-03T01:30:00-05:00'


def test_D414_late_closure_conflict_whole_series_rollback(world4):
    """A closure at the last eligible member prevents every amendment; the failed key remains reusable at its half-open end."""
    c,tok=world4; _,b=booking(c,tok); _,s=adopt(c,tok,b['reference'])
    p=preview(c,tok,closure('a','2030-01-15T20:00:00Z','2030-01-15T21:00:00Z'))
    assert p['assignments']==[]; apply(c,tok,p); before=snapshot(c)
    assert_error(amend(c,tok,s,key='closure-amend'),409,'table_unavailable')
    assert snapshot(c)==before
    result=require(amend(c,tok,s,time='21:00',key='closure-amend'))
    assert result['revision']==2
    assert all(not o['exception'] and o['reservation']['starts_at_local'].endswith('T21:00') for o in result['occurrences'])
