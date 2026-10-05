"""Additional independently derived protocol and semantic-state boundaries."""
import copy
import json
import re
import pytest

from derived.test_stage1 import world,body,headers,snapshot,assert_error,wire_request
from adapters.test_string_payload import payload,seal


def test_D120_valid_pipeline_has_controlled_boundary_and_retry(world,record_property):
    """Two complete pipelined writes either complete in order or close explicitly after the first; fresh retry of the second creates no duplicate."""
    c,token=world
    def request(value,key):
        raw=json.dumps(value).encode()
        return (b'POST /reservations HTTP/1.1\r\nHost: tablekeeper\r\nAuthorization: Bearer '+token.encode()+
                b'\r\nIdempotency-Key: '+key.encode()+b'\r\nContent-Type: application/json\r\nContent-Length: '+
                str(len(raw)).encode()+b'\r\n\r\n'+raw)
    first=body();second={**body(),'table_id':'b'}
    response,elapsed,timeout=wire_request(request(first,'pipeline-a')+request(second,'pipeline-b'))
    statuses=re.findall(rb'HTTP/1\.[01] ([0-9]{3}) ',response)
    assert not timeout and elapsed<=5 and statuses in ([b'201'],[b'201',b'201'])
    if len(statuses)==1:assert b'connection: close' in response.lower()
    before=c.get('/reservations',headers=headers(token)).json()['reservations']
    assert len(before)==len(statuses)
    replay=c.post('/reservations',json=second,headers=headers(token,'pipeline-b'))
    assert replay.status_code==(201 if len(statuses)==1 else 200)
    again=c.post('/reservations',json=second,headers=headers(token,'pipeline-b'))
    assert again.status_code==200 and again.json()==replay.json()
    assert len(c.get('/reservations',headers=headers(token)).json()['reservations'])==2
    assert c.get('/health').status_code==200
    record_property('observed',json.dumps({'pipeline_responses':len(statuses),'first_statuses':[s.decode() for s in statuses],
                                         'fresh_second_status':replay.status_code,'final_bookings':2}))


@pytest.mark.parametrize('corruption',['plaintext-password','unknown-token-owner','duplicate-reservation-id',
    'overlapping-confirmed','inconsistent-instant','wrong-receipt-method','missing-receipt-body','invalid-zone'])
def test_D121_corrupt_semantic_state_rejects_without_replacement(world,corruption,record_property):
    """Corrupt account/token/identity/occupancy/time/receipt/configuration state with a valid checksum returns422 and preserves destination exactly."""
    c,token=world
    first=c.post('/reservations',json=body(),headers=headers(token,'first'));assert first.status_code==201
    second=c.post('/reservations',json={**body(),'table_id':'b'},headers=headers(token,'second'));assert second.status_code==201
    saved=c.get('/_test/export').json()
    assert c.post('/_test/import',json=saved).status_code==204
    before=snapshot(c);broken=copy.deepcopy(saved);data=payload(broken)
    a=data['reservations'][first.json()['reference']];b=data['reservations'][second.json()['reference']]
    if corruption=='plaintext-password':data['users']['u']['password_hash']='synthetic-password'
    elif corruption=='unknown-token-owner':data['tokens'][token]='absent-user'
    elif corruption=='duplicate-reservation-id':b['reservation_id']=a['reservation_id']
    elif corruption=='overlapping-confirmed':b['table_id']='a'
    elif corruption=='inconsistent-instant':a['starts_at']='2030-01-01T19:00:00+00:00'
    elif corruption=='wrong-receipt-method':data['receipts'][0]['method']='GET'
    elif corruption=='missing-receipt-body':del data['receipts'][0]['body']
    else:data['restaurants']['r']['timezone']='Invalid/Synthetic_Zone'
    seal(broken,data)
    result=c.post('/_test/import',json=broken,timeout=10)
    unchanged=snapshot(c)==before
    record_property('observed',json.dumps({'corruption':corruption,'import_status':result.status_code,
                                         'destination_unchanged':unchanged,'checksum_recomputed':True,'control_import':204}))
    assert_error(result,422,'validation_failed')
    assert unchanged and c.get('/reservations',headers=headers(token)).status_code==200
