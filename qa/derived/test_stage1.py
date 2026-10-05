"""Independent contract probes authored before reviewing this run's product.

Only the disposable service alias is targeted. These supplement, never replace,
the frozen assertions. Raw-wire probes are counted separately from httpx calls.
"""
import copy
import json
import os
from pathlib import Path
import re
import socket
import time
from decimal import Decimal

import httpx
import pytest


def fixture():
    return {'users': [{'id': 'u', 'email': 'u@derived.test', 'password': 'synthetic-password', 'display_name': 'Diner'}],
            'restaurants': [{'id': 'r', 'name': 'Synthetic garden', 'timezone': 'UTC',
               'slot_minutes': 30, 'reservation_duration_minutes': 60, 'cancellation_cutoff_minutes': 0,
               'opening_hours': [{'weekday': d, 'opens': '17:00', 'closes': '23:00'} for d in 'mon tue wed thu fri sat sun'.split()],
               'tables': [{'id': 'a', 'label': 'Window', 'capacity': 4}, {'id': 'b', 'label': 'Garden', 'capacity': 4}]}],
            'reservations': []}


@pytest.fixture
def world():
    with httpx.Client(base_url='http://tablekeeper:8080', timeout=6, trust_env=False) as c:
        assert c.post('/_test/reset', json=fixture(), timeout=10).status_code == 204
        r = c.post('/auth/login', json={'email': 'u@derived.test', 'password': 'synthetic-password'})
        assert r.status_code == 200
        yield c, r.json()['token']


def body():
    return {'restaurant_id': 'r', 'table_id': 'a', 'starts_at_local': '2030-01-01T18:00', 'party_size': 2}


def headers(token, key='derived'):
    return {'Authorization': 'Bearer ' + token, 'Idempotency-Key': key, 'Content-Type': 'application/json'}


def snapshot(c):
    r = c.get('/_test/export', timeout=10)
    assert r.status_code == 200
    return json.loads(r.content, parse_float=Decimal, parse_int=Decimal)


def assert_error(response, status, code):
    assert response.status_code == status, response.text[:500]
    assert response.headers.get('Content-Type', '').lower().startswith('application/json')
    assert response.json()['error']['code'] == code
    assert isinstance(response.json()['error']['message'], str) and response.json()['error']['message']


EMBEDDED = b'POST /_test/reset HTTP/1.1\r\nHost: tablekeeper\r\nContent-Type: application/json\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}'
BAD_HEADERS = [
    ('conflicting-length', b'Content-Length: 2\r\nContent-Length: 9\r\n'),
    ('identical-duplicate', b'Content-Length: 2\r\nContent-Length: 2\r\n'),
    ('comma-length', b'Content-Length: 2, 9\r\n'),
    ('negative-length', b'Content-Length: -1\r\n'),
    ('signed-length', b'Content-Length: +2\r\n'),
    ('hex-length', b'Content-Length: 0x2\r\n'),
    ('decimal-length', b'Content-Length: 2.0\r\n'),
    ('missing-length', b''),
    ('zero-unread', b'Content-Length: 0\r\n'),
    ('chunked', b'Transfer-Encoding: chunked\r\n'),
    ('te-and-length', b'Transfer-Encoding: chunked\r\nContent-Length: 2\r\n'),
    ('te-identity', b'Transfer-Encoding: identity\r\n'),
]


def wire_request(payload, shutdown=False):
    tick = time.monotonic()
    chunks = []
    timed_out = False
    with socket.create_connection(('tablekeeper', 8080), timeout=5) as sock:
        sock.settimeout(5)
        sock.sendall(payload)
        if shutdown:
            sock.shutdown(socket.SHUT_WR)
        try:
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        except (ConnectionResetError, BrokenPipeError):
            pass  # controlled close is checked together with the response below
        except socket.timeout:
            timed_out = True
    elapsed = time.monotonic()-tick
    response = b''.join(chunks)
    if directory := os.environ.get('QA_EVIDENCE_DIR'):
        with (Path(directory)/'wire-requests.jsonl').open('a') as stream:
            stream.write(json.dumps({'request_bytes': len(payload), 'response_bytes': len(response),
                                    'elapsed_s': elapsed, 'timed_out': timed_out,
                                    'raw_response': response.decode('ascii', 'backslashreplace')})+'\n')
    return response, elapsed, timed_out


@pytest.mark.parametrize('name,extra', BAD_HEADERS, ids=[x[0] for x in BAD_HEADERS])
def test_D101_rejected_framing_never_executes_unread_reset(world, record_property, name, extra):
    """Ambiguous or bodyless signup framing yields one controlled JSON4xx/close, never executes embedded reset, and preserves health/state."""
    c, _ = world
    before = snapshot(c)
    response, elapsed, timeout = wire_request(b'POST /auth/signup HTTP/1.1\r\nHost: tablekeeper\r\n' + extra + b'\r\n' + EMBEDDED)
    statuses = re.findall(rb'HTTP/1\.[01] ([0-9]{3}) ', response)
    record_property('observed', json.dumps({'statuses': [x.decode() for x in statuses], 'elapsed_s': elapsed, 'timeout': timeout}))
    assert snapshot(c) == before
    assert c.get('/health').json() == {'status': 'ok'}
    assert not timeout and elapsed <= 5
    assert len(statuses) == 1 and statuses[0].startswith(b'4'), response[:500]
    header, _, raw = response.partition(b'\r\n\r\n')
    assert b'application/json' in header.lower(), header
    error = json.loads(raw)['error']
    assert isinstance(error['code'], str) and isinstance(error['message'], str)


@pytest.mark.parametrize('raw', [
    b'POST /auth/signup HTTP/1.1\r\nHost: tablekeeper\r\nContent-Length: 100\r\n\r\n{"email":',
    b'POST /auth/signup HTTP/1.1\r\nHost: tablekeeper\r\nContent-Length:',
    b'POST /auth/signup HTTP/1.1\r\nHost: tablekeeper\r\nContent-Length: 100\r\n\r\n',
], ids=['D102-truncated-body', 'D102-truncated-header', 'D102-empty-body'])
def test_D102_incomplete_stream_closes_without_mutation(world, raw, record_property):
    """EOF before complete headers/body cannot publish partial state, keep the socket stuck, or prevent later health."""
    c, _ = world
    before = snapshot(c)
    response, elapsed, timeout = wire_request(raw, shutdown=True)
    assert not timeout and elapsed <= 5
    assert not re.search(rb'HTTP/1\.[01] [25][0-9]{2} ', response)
    assert snapshot(c) == before and c.get('/health').status_code == 200
    record_property('response_bytes', len(response))


@pytest.mark.parametrize('left,equal,different', [
    ('true', 'true', '1'), ('false', 'false', '0'), ('null', 'null', '0'),
    ('1.00', '10e-1', '1.00000000000000000000000000000001'),
    ('-0e900', '0.0', '1e-900'),
    ('9007199254740993', '90071992547409930e-1', '9007199254740992'),
    ('"1"', '"\\u0031"', '1'),
], ids=['D105-bool-true','D105-bool-false','D105-null','D105-decimal','D105-zero','D105-int53','D105-string'])
def test_D105_json_identity_distinctions_lifetime(world, left, equal, different):
    """JSON-type distinctions and exact numeric equivalence persist through response, amendment, import and original replay."""
    c, token = world
    def value(number):
        return json.dumps(body())[:-1] + ',"unknown":{"雪":['+number+']}}'
    first = c.post('/reservations', content=value(left).encode(), headers=headers(token))
    assert first.status_code == 201, first.text
    original = first.json()
    same = c.post('/reservations', content=value(equal).encode(), headers=headers(token))
    assert same.status_code == 200 and same.json() == original
    before = snapshot(c)
    conflict = c.post('/reservations', content=value(different).encode(), headers=headers(token))
    assert_error(conflict, 409, 'idempotency_key_reuse')
    assert snapshot(c) == before
    assert c.patch('/reservations/'+original['reference'], json={'party_size':1}, headers=headers(token)).status_code == 200
    exported = c.get('/_test/export').content
    assert c.post('/_test/reset', json={'users':[],'restaurants':[],'reservations':[]}).status_code == 204
    assert c.post('/_test/import', content=exported, headers={'Content-Type':'application/json'}, timeout=10).status_code == 204
    restored = snapshot(c)
    replay = c.post('/reservations', content=value(equal).encode(), headers=headers(token))
    assert replay.status_code == 200 and replay.json() == original
    assert snapshot(c) == restored


@pytest.mark.parametrize('depth',[1000,3000,5000],ids=['D106-depth1000','D106-depth3000','D106-depth5000'])
def test_D106_deep_unknown_receipt_full_lifetime(world, depth, record_property):
    """Deep ignored JSON is accepted and retains a working immutable receipt through equality, export/import and retry."""
    c, token = world
    raw = json.dumps(body())[:-1]+',"unknown":'+('[{"x":'*depth)+'"\\ud800雪"'+('}]'*depth)+'}'
    raw = raw.encode()
    first = c.post('/reservations', content=raw, headers=headers(token))
    assert first.status_code == 201, first.text[:500]
    same = c.post('/reservations', content=raw, headers=headers(token))
    assert same.status_code == 200 and same.json() == first.json()
    saved = c.get('/_test/export', timeout=10)
    assert saved.status_code == 200
    assert c.post('/_test/import', content=saved.content, headers={'Content-Type':'application/json'}, timeout=10).status_code == 204
    retry = c.post('/reservations', content=raw, headers=headers(token))
    assert retry.status_code == 200 and retry.json() == first.json()
    record_property('request_bytes', len(raw))
    record_property('export_bytes', len(saved.content))


@pytest.mark.parametrize('wrong',[True, False, '2', 0, -1, 1.5, None],ids=['true','false','string','zero','negative','fraction','null'])
def test_D113_batch_last_invalid_rolls_back_prior_valid_move(world, wrong):
    """A later invalid party-size item rolls back a valid prior swap move and leaves its idempotency key reusable."""
    c, token = world
    a = c.post('/reservations', json=body(), headers=headers(token,'a')).json()
    b = body(); b['table_id']='b'
    b = c.post('/reservations', json=b, headers=headers(token,'b')).json()
    changes = {'moves':[{'reference':a['reference'],'table_id':'b'},
                        {'reference':b['reference'],'table_id':'a','party_size':wrong}]}
    before = snapshot(c)
    r = c.post('/reservation-moves', json=changes, headers=headers(token,'batch'))
    assert_error(r,422,'validation_failed')
    assert snapshot(c) == before
    changes['moves'][1]['party_size']=2
    success = c.post('/reservation-moves', json=changes, headers=headers(token,'batch'))
    assert success.status_code == 201, success.text
    assert [x['table_id'] for x in success.json()['reservations']] == ['b','a']


@pytest.mark.parametrize('wrong',[None,True,42,'',{},'bad'],ids=['null','bool','number','empty-string','object','string'])
def test_D116_reset_reservations_wrong_type_is_400_and_nonmutating(world,wrong,record_property):
    """A fixture's reservations field has array type; other JSON types return400 malformed_request and preserve the destination."""
    c,_=world
    before=snapshot(c)
    value=fixture();value['reservations']=wrong
    response=c.post('/_test/reset',json=value,timeout=10)
    unchanged=snapshot(c)==before
    token_valid=c.get('/reservations',headers=headers(world[1])).status_code
    record_property('observed',json.dumps({'reset_status':response.status_code,
                                         'destination_unchanged':unchanged,'old_token_status':token_valid}))
    assert_error(response,400,'malformed_request')
    assert unchanged


@pytest.mark.parametrize('mode',['header','body'],ids=['header','body'])
def test_D117_slow_drip_records_actual_peer_eof(world,mode,record_property):
    """Continuous bytes cannot extend request lifetime past6s; raw receive distinguishes actual peer EOF from observer timeout, with nonmutation and health."""
    import select
    c,_=world
    before=snapshot(c)
    prefix=(b'POST /auth/login HTTP/1.1\r\nHost: tablekeeper\r\nX-Slow: ' if mode=='header'
            else b'POST /auth/login HTTP/1.1\r\nHost: tablekeeper\r\nContent-Length: 1000\r\n\r\n{')
    drip=b'x' if mode=='header' else b' '
    events=[];received=bytearray();eof=None;first_response=None
    with socket.create_connection(('tablekeeper',8080),timeout=2) as peer:
        peer.setblocking(False)
        tick=time.monotonic();peer.sendall(prefix);next_send=tick+.2
        while time.monotonic()-tick<11:
            now=time.monotonic()
            if now-tick<6.5 and now>=next_send:
                try:
                    peer.sendall(drip);events.append({'event':'sent_drip','at_s':now-tick,'bytes':1})
                except OSError as exc:
                    events.append({'event':'send_error','at_s':now-tick,'error':type(exc).__name__})
                next_send=now+.2
            ready,_,_=select.select([peer],[],[],.04)
            if not ready:continue
            try:chunk=peer.recv(4096)
            except BlockingIOError:continue
            except ConnectionResetError:
                eof=time.monotonic()-tick;events.append({'event':'peer_reset','at_s':eof});break
            now=time.monotonic()-tick
            if not chunk:
                eof=now;events.append({'event':'peer_eof','at_s':now});break
            if first_response is None:first_response=now
            received.extend(chunk);events.append({'event':'response','at_s':now,'bytes':len(chunk)})
        elapsed=time.monotonic()-tick
    unchanged=snapshot(c)==before
    health=c.get('/health').status_code
    detail={'mode':mode,'eof_s':eof,'first_response_s':first_response,'elapsed_s':elapsed,
            'stopped_dripping_after_s':6.5,'destination_unchanged':unchanged,'health':health,
            'raw_response':bytes(received).decode('ascii','backslashreplace'),'events':events}
    record_property('observed',json.dumps(detail))
    if directory:=os.environ.get('QA_EVIDENCE_DIR'):
        with (Path(directory)/'slow-wire-requests.jsonl').open('a') as stream:
            stream.write(json.dumps(detail)+'\n')
    assert eof is not None and eof<=6,detail
    assert unchanged and health==200


def test_D118_real_201_response_discarded_original_retry_after_mutation(world,record_property):
    """Receive actual201 then discard the response; exactly one booking and immutable retry survive amendment, cancellation and replacement import."""
    c,token=world
    raw=json.dumps(body()).encode()
    request=(b'POST /reservations HTTP/1.1\r\nHost: tablekeeper\r\nAuthorization: Bearer '+token.encode()+
             b'\r\nIdempotency-Key: lost-response\r\nContent-Type: application/json\r\nContent-Length: '+
             str(len(raw)).encode()+b'\r\nConnection: close\r\n\r\n'+raw)
    with socket.create_connection(('tablekeeper',8080),timeout=5) as peer:
        peer.sendall(request);status=bytearray()
        while not status.endswith(b'\r\n'):
            chunk=peer.recv(1);assert chunk
            status.extend(chunk);assert len(status)<100
        assert bytes(status).startswith(b'HTTP/1.1 201 ')
        # Headers/body are deliberately not read; close discards the response.
    rows=c.get('/reservations',headers=headers(token)).json()['reservations']
    assert len(rows)==1
    original=rows[0];reference=original['reference']
    assert c.patch('/reservations/'+reference,json={'table_id':'b'},headers=headers(token)).status_code==200
    assert c.post('/reservations/'+reference+'/cancel',json={},headers=headers(token)).status_code==200
    saved=c.get('/_test/export').content
    assert c.post('/_test/reset',json={'users':[],'restaurants':[],'reservations':[]}).status_code==204
    assert c.post('/_test/import',content=saved,headers={'Content-Type':'application/json'},timeout=10).status_code==204
    before=snapshot(c)
    replay=c.post('/reservations',content=raw,headers=headers(token,'lost-response'))
    assert replay.status_code==200 and replay.json()==original
    current=c.get('/reservations/'+reference,headers=headers(token)).json()
    assert current['table_id']=='b' and current['status']=='cancelled'
    assert len(c.get('/reservations',headers=headers(token)).json()['reservations'])==1
    assert snapshot(c)==before
    record_property('observed',json.dumps({'actual_status_line':bytes(status).decode().strip(),
        'response_body_discarded':True,'raw_http_requests':1,'original_replay':200,'bookings':1,
        'current_table':'b','current_status':'cancelled','exact_nonmutation_on_replay':True}))


def test_D119_same_key_same_body_different_path_historical_receipts(world,record_property):
    """One user/key/body is independently valid on create and moves; no-op and changed batch receipts stay original through later mutations and import."""
    c,token=world
    bbody={**body(),'table_id':'b'}
    b=c.post('/reservations',json=bbody,headers=headers(token,'second'));assert b.status_code==201
    b=b.json()
    common={**body(),'moves':[{'reference':b['reference'],'party_size':2,'restaurant_id':'ignored'}]}
    a=c.post('/reservations',json=common,headers=headers(token,'shared'));assert a.status_code==201
    a=a.json()
    noop=c.post('/reservation-moves',json=common,headers=headers(token,'shared'));assert noop.status_code==201
    swaps={'moves':[{'reference':a['reference'],'table_id':'b'}, {'reference':b['reference'],'table_id':'a'}]}
    swapped=c.post('/reservation-moves',json=swaps,headers=headers(token,'swap'));assert swapped.status_code==201
    assert c.patch('/reservations/'+a['reference'],json={'party_size':1,'starts_at_local':'2030-01-01T20:00'},headers=headers(token)).status_code==200
    assert c.post('/reservations/'+b['reference']+'/cancel',json={},headers=headers(token)).status_code==200
    saved=c.get('/_test/export').json()
    assert c.post('/_test/import',json=saved,timeout=10).status_code==204
    before=snapshot(c)
    for path,key,value,expected in [('/reservations','shared',common,a),
                                  ('/reservation-moves','shared',common,noop.json()),
                                  ('/reservation-moves','swap',swaps,swapped.json()),
                                  ('/reservations','second',bbody,b)]:
        replay=c.post(path,json=value,headers=headers(token,key))
        assert replay.status_code==200 and replay.json()==expected
    assert snapshot(c)==before
    record_property('observed',json.dumps({'original_receipts':4,'same_user_key_body_distinct_paths':2,
                                         'valid_historical_import':204,'replays_nonmutating':True}))
