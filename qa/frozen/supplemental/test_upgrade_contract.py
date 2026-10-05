"""Portable populated state between separately running immutable stage images."""
import copy
import json
import time

import httpx
import pytest
from test_boundaries import body, observe


@pytest.fixture
def peers():
    hours=[{'weekday':d,'opens':'00:00','closes':'23:59'} for d in ('mon','tue','wed','thu','fri','sat','sun')]
    fixture={'users':[{'id':'alice','email':'alice@upgrade.test','password':'synthetic-upgrade-only','display_name':'Alice'}],
             'restaurants':[{'id':'r_main','name':'Upgrade dining','timezone':'UTC','slot_minutes':30,'reservation_duration_minutes':60,
                             'cancellation_cutoff_minutes':0,'opening_hours':hours,'tables':[{'id':'t_1','label':'One','capacity':4},{'id':'t_2','label':'Two','capacity':4}],
                             'combinable':[['t_1','t_2']],'manager_user_ids':['alice']}], 'reservations':[]}
    clients=[httpx.Client(base_url=f'http://{host}:8080',timeout=10,trust_env=False) for host in ('source','destination')]
    try:
        tokens=[]
        for client in clients:
            deadline=time.monotonic()+60
            while True:
                try:
                    r=client.get('/health',timeout=2)
                    if r.status_code==200:break
                except httpx.HTTPError:pass
                assert time.monotonic()<deadline,'Stage failed to become ready'
                time.sleep(.1)
            assert client.post('/_test/reset',json=fixture).status_code==204
            r=client.post('/auth/login',json={'email':'alice@upgrade.test','password':'synthetic-upgrade-only'})
            assert r.status_code==200
            tokens.append(r.json()['token'])
        yield clients[0],clients[1],tokens
    finally:
        for client in clients:client.close()


def headers(token,key=None):
    h={'Authorization':'Bearer '+token}
    if key is not None:h['Idempotency-Key']=key
    return h


def create(client,token,key,payload=None):
    r=client.post('/reservations',json=body() if payload is None else payload,headers=headers(token,key))
    assert r.status_code==201,r.text
    return r.json()


def transfer(source,destination):
    exported=source.get('/_test/export');assert exported.status_code==200,exported.text
    # Ordinary clients decode and re-encode the opaque JSON envelope.
    snapshot=exported.json()
    imported=destination.post('/_test/import',content=json.dumps(snapshot,allow_nan=False),headers={'Content-Type':'application/json'})
    assert imported.status_code==204,imported.text
    return snapshot


def test_U001_original_receipt_sessions_and_replacement(peers,record_property):
    """Old session tokens and original cancelled-booking receipts survive; destination tokens are revoked."""
    source,dest,t=peers
    first=create(source,t[0],'before-upgrade')
    cancelled=source.post('/reservations/'+first['reference']+'/cancel',json={},headers=headers(t[0]))
    assert cancelled.status_code==200
    second=source.post('/auth/login',json={'email':'alice@upgrade.test','password':'synthetic-upgrade-only'}).json()['token']
    transfer(source,dest)
    assert dest.get('/reservations',headers=headers(t[1])).status_code==401
    for token in (t[0],second):
        r=dest.get('/reservations/'+first['reference'],headers=headers(token));assert r.status_code==200 and r.json()['status']=='cancelled'
    replay=dest.post('/reservations',json=body(),headers=headers(t[0],'before-upgrade'))
    assert replay.status_code==200 and replay.json()==first
    login=dest.post('/auth/login',json={'email':'alice@upgrade.test','password':'synthetic-upgrade-only'});assert login.status_code==200
    observe(record_property,sessions_preserved=2,destination_token_revoked=True,original_replay=True,password_login=200)


def test_U002_old_batch_receipt_after_later_amendment(peers,record_property):
    """An atomic swap's original ordered response survives a later amendment and stage transfer."""
    source,dest,t=peers
    a=create(source,t[0],'a');bbody=body();bbody['table_id']='t_2';b=create(source,t[0],'b',bbody)
    changes={'moves':[{'reference':a['reference'],'table_id':'t_2'},{'reference':b['reference'],'table_id':'t_1'}]}
    response=source.post('/reservation-moves',json=changes,headers=headers(t[0],'swap'));assert response.status_code==201,response.text
    original=response.json()
    r=source.patch('/reservations/'+a['reference'],json={'starts_at_local':'2030-01-01T20:00'},headers=headers(t[0]));assert r.status_code==200
    transfer(source,dest)
    replay=dest.post('/reservation-moves',json=changes,headers=headers(t[0],'swap'))
    assert replay.status_code==200 and replay.json()==original
    current=dest.get('/reservations/'+a['reference'],headers=headers(t[0])).json()
    assert current['starts_at_local']=='2030-01-01T20:00' and current['table_id']=='t_2'
    observe(record_property,original_ordered_batch_replay=True,current_amendment_retained=True)


@pytest.mark.parametrize('number',['1e400','1e-400','1.00000000000000000000000000000000000001'],ids=['U003-overflow','U004-underflow','U005-precision'])
def test_exact_unknown_number_survives_ordinary_json_transfer(peers,record_property,number):
    """Opaque state survives ordinary JSON client roundtrip without rounding unknown request numbers."""
    source,dest,t=peers
    raw=(json.dumps(body())[:-1]+',"ignored":'+number+'}').encode()
    first=source.post('/reservations',content=raw,headers=headers(t[0],'numeric'));assert first.status_code==201,first.text
    transfer(source,dest)
    replay=dest.post('/reservations',content=raw,headers=headers(t[0],'numeric'))
    assert replay.status_code==200 and replay.json()==first.json()
    changed=(json.dumps(body())[:-1]+',"ignored":0}').encode()
    conflict=dest.post('/reservations',content=changed,headers=headers(t[0],'numeric'))
    assert conflict.status_code==409 and conflict.json()['error']['code']=='idempotency_key_reuse'
    observe(record_property,number=number,original_replay=True,distinct_zero_conflict=True)


def test_U006_invalid_import_is_atomic_and_source_snapshot_detached(peers,record_property):
    """An exported snapshot is detached from later source writes; failed import leaves destination intact."""
    source,dest,t=peers
    original=create(source,t[0],'detach');snapshot=source.get('/_test/export').json()
    assert source.post('/reservations/'+original['reference']+'/cancel',json={},headers=headers(t[0])).status_code==200
    assert dest.post('/_test/import',json=snapshot).status_code==204
    found=dest.get('/reservations/'+original['reference'],headers=headers(t[0]));assert found.status_code==200 and found.json()['status']=='confirmed'
    before=dest.get('/_test/export').json();bad=copy.deepcopy(snapshot);bad['format_version']=999
    r=dest.post('/_test/import',json=bad);assert r.status_code==422
    assert dest.get('/_test/export').json()==before
    observe(record_property,detached_snapshot=True,invalid_import=422,destination_unchanged=True)
