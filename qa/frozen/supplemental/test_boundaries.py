"""Independent regression probes for the audit findings over real HTTP.

Tests use only synthetic local containers. Product source is not imported.
Snapshot-corruption checks explicitly apply to this project's transparent receipt format.
"""
import copy
import json
import socket
import httpx
import pytest


@pytest.fixture
def api():
    with httpx.Client(base_url='http://tablekeeper:8080',timeout=8,trust_env=False) as client:
        data={'users':[{'id':x,'email':x+'@example.test','password':'synthetic-password','display_name':x.title()} for x in ('alice','bob')],
              'reservations':[],
              'restaurants':[{'id':'r_main','name':'Audit dining','timezone':'UTC','slot_minutes':30,
               'reservation_duration_minutes':60,'cancellation_cutoff_minutes':0,
               'opening_hours':[{'weekday':x,'opens':'00:00','closes':'23:59'} for x in ('mon','tue','wed','thu','fri','sat','sun')],
               'tables':[{'id':'t_1','label':'One','capacity':4},{'id':'t_2','label':'Two','capacity':4}]}]}
        assert client.post('/_test/reset',json=data).status_code==204
        tokens={}
        for u in data['users']:
            r=client.post('/auth/login',json={'email':u['email'],'password':u['password']})
            assert r.status_code==200
            tokens[u['id']]=r.json()['token']
        yield client,tokens,data


def body(**kwargs):
    return dict(restaurant_id='r_main',table_id='t_1',starts_at_local='2030-01-01T18:00',party_size=2,**kwargs)


def book(client,token,key,payload):
    return client.post('/reservations',content=json.dumps(payload,ensure_ascii=True),headers={'Authorization':'Bearer '+token,'Idempotency-Key':key,'Content-Type':'application/json'})


def observe(record_property,**values):
    record_property('observed',json.dumps(values,ensure_ascii=True))


def bookings(client,token):
    r=client.get('/reservations',headers={'Authorization':'Bearer '+token})
    assert r.status_code==200
    return r.json()['reservations']


def test_B001_deep_receipt_atomic_retry(api,record_property):
    """Accepted deep unknown JSON must not create a booking without a replay receipt."""
    c,t,_=api
    nested='leaf'
    for _ in range(600): nested={'x':nested}
    payload=body(ignored=nested)
    first=book(c,t['alice'],'deep',payload)
    retry=book(c,t['alice'],'deep',payload)
    records=bookings(c,t['alice'])
    observe(record_property,first=first.status_code,retry=retry.status_code,bookings=len(records),same_response=first.json()==retry.json())
    assert first.status_code==201 and retry.status_code==200 and first.json()==retry.json() and len(records)==1


def test_B002_large_accumulated_snapshot_roundtrip(api,record_property):
    """Two accepted large receipts must survive an unchanged snapshot round-trip."""
    c,t,_=api
    payloads=[]
    for i in range(2):
        payload=body(ignored='x'*1100000);payload['table_id']='t_'+str(i+1);payloads.append(payload)
        assert book(c,t['alice'],'big-'+str(i),payload).status_code==201
    snapshot=c.get('/_test/export')
    assert snapshot.status_code==200
    restored=c.post('/_test/import',content=snapshot.content,headers={'Content-Type':'application/json'})
    retries=[book(c,t['alice'],'big-'+str(i),p).status_code for i,p in enumerate(payloads)]
    observe(record_property,snapshot_bytes=len(snapshot.content),import_status=restored.status_code,retries=retries)
    assert restored.status_code==204 and retries==[200,200]


def test_B003_cross_owner_receipt_rejected(api,record_property):
    """Transparent receipt state cannot bind Alice's key to Bob's confirmation."""
    c,t,_=api
    a=book(c,t['alice'],'alice-key',body());bbody=body();bbody['table_id']='t_2'
    b=book(c,t['bob'],'bob-key',bbody)
    assert a.status_code==b.status_code==201
    original=c.get('/_test/export').json(); altered=copy.deepcopy(original)
    stack=[altered]; found=0
    while stack:
        item=stack.pop()
        if isinstance(item,dict):
            receipt_body=item.get('body')
            # Later BAND snapshots preserve exact request numbers in JSON text.
            # Decode only the fixture selector; the cross-owner rejection assertion stays unchanged.
            if 'body_json' in item and isinstance(item['body_json'],str):
                receipt_body=json.loads(item['body_json'])
            if item.get('response')==a.json() and receipt_body==body(): item['response']=b.json();found+=1
            else: stack.extend(item.values())
        elif isinstance(item,list): stack.extend(item)
    assert found==1,'Receipt format changed; adapt the white-box corruption fixture, do not count this as a product failure.'
    result=c.post('/_test/import',json=altered)
    unchanged=c.get('/_test/export').json()==original
    observe(record_property,import_status=result.status_code,destination_unchanged=unchanged)
    assert result.status_code==422 and unchanged


@pytest.mark.parametrize('route',['/auth/signup','/_test/reset'],ids=['signup','fixture'])
def test_B004_surrogate_input_no_server_error(api,record_property,route):
    """Unpaired Unicode is rejected atomically or supported with working login and snapshots."""
    c,t,data=api;before=c.get('/_test/export').json()
    if route=='/auth/signup': payload={'email':'unicode@example.test','display_name':'Unicode','password':'12345678\ud800'}
    else: payload=copy.deepcopy(data);payload['users'][0]['password']='12345678\ud800'
    result=c.post(route,content=json.dumps(payload,ensure_ascii=True),headers={'Content-Type':'application/json'})
    unchanged=c.get('/_test/export').json()==before
    if result.status_code in (400,422):
        observe(record_property,status=result.status_code,destination_unchanged=unchanged,handling='rejected')
        assert unchanged
    else:
        # The contract forbids 5xx but does not require rejecting this JSON string.
        # A consistent implementation can preserve it instead of rejecting it.
        assert result.status_code==(201 if route=='/auth/signup' else 204)
        account=payload if route=='/auth/signup' else payload['users'][0]
        credentials={'email':account['email'],'password':account['password']}
        login=c.post('/auth/login',content=json.dumps(credentials,ensure_ascii=True))
        snapshot=c.get('/_test/export')
        restored=c.post('/_test/import',content=snapshot.content)
        again=c.post('/auth/login',content=json.dumps(credentials,ensure_ascii=True))
        observe(record_property,status=result.status_code,handling='supported',login=login.status_code,snapshot=snapshot.status_code,restore=restored.status_code,login_after_import=again.status_code)
        assert (login.status_code,snapshot.status_code,restored.status_code,again.status_code)==(200,200,204,200)


def test_B005_max_calendar_day(api,record_property):
    """Availability on the maximum supported ISO date must skip out-of-day candidates."""
    c,t,_=api
    availability=c.get('/availability',params={'restaurant_id':'r_main','date':'9999-12-31','party_size':2})
    payload=body();payload['starts_at_local']='9999-12-31T18:00'
    create=book(c,t['alice'],'last-day',payload)
    observe(record_property,availability=availability.status_code,create=create.status_code)
    assert availability.status_code==200 and create.status_code==201


@pytest.mark.parametrize('rid,encoded',[('r/annex','r%2Fannex'),('r%2Fannex','r%252Fannex'),('r?x','r%3Fx'),('r#x','r%23x')],ids=['slash','literal-percent','question','fragment'])
def test_B006_opaque_id_roundtrip(api,record_property,rid,encoded):
    """Accepted opaque IDs remain available via segment-encoded public detail."""
    c,t,data=api;data['restaurants'][0]['id']=rid
    assert c.post('/_test/reset',json=data).status_code==204
    r=c.get('/restaurants/'+encoded)
    observe(record_property,id=rid,status=r.status_code)
    assert r.status_code==200 and r.json()['id']==rid


@pytest.mark.parametrize('headers',[b'Transfer-Encoding: chunked\r\n',b'Content-Length: 4\r\nContent-Length: 5\r\n',b'Content-Length: -1\r\n',b'Content-Length: abc\r\n'],ids=['transfer-encoding','duplicate-length','negative-length','invalid-length'])
def test_B007_rejected_framing_cannot_execute_body(api,record_property,headers):
    """Rejected framing closes the connection without executing unread embedded reset bytes."""
    c,t,_=api;before=c.get('/restaurants').json()
    embedded=b'POST /_test/reset HTTP/1.1\r\nHost: tablekeeper\r\nContent-Type: application/json\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}'
    raw=b'POST /auth/signup HTTP/1.1\r\nHost: tablekeeper\r\n'+headers+b'\r\n'+embedded
    chunks=[];timed_out=False
    with socket.create_connection(('tablekeeper',8080),timeout=3) as sock:
        sock.sendall(raw)
        try:
            while True:
                block=sock.recv(65536)
                if not block: break
                chunks.append(block)
        except socket.timeout: timed_out=True
    response=b''.join(chunks);after=c.get('/restaurants').json()
    statuses=[part[:3].decode('ascii','replace') for part in response.split(b'HTTP/1.1 ')[1:]]
    observe(record_property,statuses=statuses,read_timeout=timed_out,restaurants_unchanged=before==after)
    assert before==after and len(statuses)==1 and statuses[0].startswith('4') and not timed_out
