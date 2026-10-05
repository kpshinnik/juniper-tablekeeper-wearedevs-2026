"""New assertions derived from audit30, for a disposable 2CPU/2GiB service.

Original eight reproduction scripts and their historical targets are unchanged.
R001–R004 use a six-second absolute read deadline as an additional robustness
criterion, rather than claiming the spec assigns its ordinary-request SLA to
an unfinished malicious request. They send at most a few hundred bytes.
"""
import concurrent.futures
from datetime import datetime, timezone
import json
import selectors
import socket
import threading
import time
from zoneinfo import ZoneInfo

import httpx
import pytest


WEEK = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')


def fixture(zone='UTC', close='23:59'):
    return {'users': [{'id': 'audit-guest', 'email': 'guest@audit30.test',
                      'password': 'synthetic-audit-password', 'display_name': 'Guest'}],
            'reservations': [],
            'restaurants': [{'id': 'audit-dining', 'name': 'Audit Dining',
                             'timezone': zone, 'slot_minutes': 30,
                             'reservation_duration_minutes': 60,
                             'cancellation_cutoff_minutes': 0,
                             'opening_hours': [{'weekday': w, 'opens': '00:00', 'closes': close} for w in WEEK],
                             'tables': [{'id': 'one', 'label': 'One', 'capacity': 4},
                                        {'id': 'two', 'label': 'Two', 'capacity': 4}]}]}


@pytest.fixture
def api():
    with httpx.Client(base_url='http://tablekeeper:8080', timeout=11, trust_env=False) as c:
        assert c.post('/_test/reset', json=fixture()).status_code == 204
        response = c.post('/auth/login', json={'email': 'guest@audit30.test',
                                              'password': 'synthetic-audit-password'})
        assert response.status_code == 200
        yield c, response.json()['token']


def observed(record_property, **values):
    record_property('observed', json.dumps(values, ensure_ascii=True))


def payload(table='one', starts='2030-01-01T18:00'):
    return {'restaurant_id': 'audit-dining', 'table_id': table,
            'starts_at_local': starts, 'party_size': 2}


def create(c, token, key, body):
    started = time.monotonic()
    response = c.post('/reservations', content=json.dumps(body, ensure_ascii=True),
                      headers={'Authorization': 'Bearer ' + token, 'Idempotency-Key': key,
                               'Content-Type': 'application/json'}, timeout=6)
    assert time.monotonic() - started <= 5
    return response


def ordinary(c, method, path, timings, **kwargs):
    started = time.monotonic()
    response = c.request(method, path, timeout=6, **kwargs)
    elapsed = time.monotonic() - started
    timings.append({'method': method, 'path': path, 'status': response.status_code, 'elapsed_s': elapsed})
    assert elapsed <= 5
    return response


def snapshot(c):
    r = c.get('/_test/export')
    assert r.status_code == 200
    return r.json()


def raw_probe(c, prefix, drip, record_property):
    """Measure closure without allocating the advertised body on either side."""
    before = snapshot(c)
    stop = threading.Event()
    started = time.monotonic()
    received = bytearray()
    sent = len(prefix)
    closed = False
    with socket.create_connection(('tablekeeper', 8080), timeout=2) as sock:
        sock.settimeout(.25)
        sock.sendall(prefix)

        def sender():
            nonlocal sent
            while not stop.wait(.25):
                try:
                    sock.sendall(drip)
                    sent += len(drip)
                except OSError:
                    break

        thread = threading.Thread(target=sender, daemon=True)
        if drip:
            thread.start()
        health_start = time.monotonic()
        health = c.get('/health', timeout=6)
        health_elapsed = time.monotonic() - health_start
        try:
            while time.monotonic() - started < 8:
                try:
                    block = sock.recv(4096)
                    if not block:
                        closed = True
                        break
                    received.extend(block)
                except socket.timeout:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    closed = True
                    break
        finally:
            stop.set()
            if drip:
                thread.join(timeout=1)
        elapsed = time.monotonic() - started
    same = snapshot(c) == before
    observed(record_property, bytes_sent=sent, elapsed_s=elapsed, closed=closed,
             response_prefix=received[:80].decode('ascii', 'replace'),
             health_status=health.status_code, health_elapsed_s=health_elapsed,
             state_unchanged=same, criterion='additional absolute read deadline <=6s')
    assert sent < 1000 and closed and elapsed <= 6
    assert health.status_code == 200 and health_elapsed <= 5 and same


def test_R001_declared_two_gigabyte_body_is_bounded(api, record_property):
    """A tiny incomplete body with a two-billion-byte declaration closes promptly without changing state."""
    c, _ = api
    raw_probe(c, b'POST /auth/login HTTP/1.1\r\nHost: tablekeeper\r\nContent-Length: 2000000000\r\n\r\n{',
              b'', record_property)


def test_R002_continuous_body_drip_has_absolute_deadline(api, record_property):
    """Small recurring body bytes cannot renew an incomplete request forever."""
    c, _ = api
    raw_probe(c, b'POST /auth/login HTTP/1.1\r\nHost: tablekeeper\r\nContent-Length: 1000\r\n\r\n{',
              b' ', record_property)


def test_R003_continuous_header_drip_has_absolute_deadline(api, record_property):
    """A header delivered one byte at a time has a total deadline and no side effects."""
    c, _ = api
    raw_probe(c, b'POST /auth/login HTTP/1.1\r\nHost: tablekeeper\r\nX-Slow: ',
              b'x', record_property)


def test_R004_49_incomplete_bodies_leave_health_responsive(api, record_property):
    """Within the 50-connection budget, held bodies leave health responsive and are retired."""
    c, _ = api
    before = snapshot(c)
    peers = []
    closed_after = []
    opened = {}
    selector = selectors.DefaultSelector()
    try:
        for _ in range(49):
            peer = socket.create_connection(('tablekeeper', 8080), timeout=2)
            peer.setblocking(False)
            peer.sendall(b'POST /auth/login HTTP/1.1\r\nHost: tablekeeper\r\nContent-Length: 100\r\n\r\n{')
            peers.append(peer)
            opened[peer] = time.monotonic()
            selector.register(peer, selectors.EVENT_READ)
        tick = time.monotonic()
        response = c.get('/health', timeout=6)
        health_elapsed = time.monotonic() - tick
        deadline = min(opened.values()) + 6
        while selector.get_map() and time.monotonic() < deadline:
            for key, _ in selector.select(min(.1, max(0, deadline-time.monotonic()))):
                peer = key.fileobj
                try:
                    block = peer.recv(4096)
                except (ConnectionResetError, BrokenPipeError):
                    block = b''
                except BlockingIOError:
                    continue
                if not block:
                    closed_after.append(time.monotonic() - opened[peer])
                    selector.unregister(peer)
    finally:
        selector.close()
        for peer in peers:
            peer.close()
    same = snapshot(c) == before
    observed(record_property, held_connections=len(peers), closed=len(closed_after),
             connection_closure_elapsed_s=closed_after,
             health_status=response.status_code, health_elapsed_s=health_elapsed,
             state_unchanged=same, bytes_per_body=1)
    assert len(peers) == len(closed_after) == 49 and same
    assert all(elapsed <= 6 for elapsed in closed_after)
    assert response.status_code == 200 and health_elapsed <= 5


def test_R005_concurrent_logins_keep_all_requests_within_sla(api, record_property):
    """49 valid logins and one health request complete within the 50-in-flight ordinary SLA."""
    c, _ = api
    barrier = threading.Barrier(50)

    def call(index):
        with httpx.Client(base_url=c.base_url, timeout=6, trust_env=False) as client:
            barrier.wait(timeout=10)
            started = time.monotonic()
            response = (client.get('/health') if index == 49 else
                        client.post('/auth/login', json={'email': 'guest@audit30.test',
                                                       'password': 'synthetic-audit-password'}))
            return index, response.status_code, time.monotonic() - started

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
        results = list(pool.map(call, range(50)))
    ordered = sorted(x[2] for x in results)
    observed(record_property, concurrency=50, requests=results,
             p50_s=ordered[24], p95_s=ordered[47], max_s=ordered[-1])
    assert all(status == 200 and duration <= 5 for _, status, duration in results)


def test_R006_deep_unknown_batch_keeps_atomic_receipt(api, record_property):
    """A deep unknown batch value preserves both moves and its replay before and after import."""
    c, token = api
    a = create(c, token, 'first', payload())
    b = create(c, token, 'second', payload('two', '2030-01-01T19:00'))
    assert a.status_code == b.status_code == 201
    deep = 'leaf'
    for _ in range(600):
        deep = {'x': deep}
    body = {'moves': [{'reference': a.json()['reference'], 'table_id': 'two'},
                      {'reference': b.json()['reference'], 'table_id': 'one'}], 'ignored': deep}
    headers = {'Authorization': 'Bearer ' + token, 'Idempotency-Key': 'deep-batch',
               'Content-Type': 'application/json'}
    timings = []
    first = ordinary(c, 'POST', '/reservation-moves', timings, content=json.dumps(body), headers=headers)
    retry = ordinary(c, 'POST', '/reservation-moves', timings, content=json.dumps(body), headers=headers)
    current_before = [ordinary(c, 'GET', '/reservations/'+r.json()['reference'], timings,
                               headers={'Authorization': 'Bearer '+token}).json() for r in (a, b)]
    exported = c.get('/_test/export')
    restore_start = time.monotonic()
    restored = c.post('/_test/import', content=exported.content)
    restore_elapsed = time.monotonic() - restore_start
    replay = ordinary(c, 'POST', '/reservation-moves', timings, content=json.dumps(body), headers=headers)
    current_after = [ordinary(c, 'GET', '/reservations/'+r.json()['reference'], timings,
                              headers={'Authorization': 'Bearer '+token}).json() for r in (a, b)]
    availability = ordinary(c, 'GET', '/availability', timings,
                            params={'restaurant_id': 'audit-dining', 'date': '2030-01-01', 'party_size': 2})
    assert availability.status_code == 200
    available = {s['starts_at_local']: s['available_table_ids'] for s in availability.json()['slots']}
    observed(record_property, first=first.status_code, retry=retry.status_code,
             import_status=restored.status_code, replay=replay.status_code,
             same_response=first.json() == retry.json() == replay.json(),
             current_records=current_after, readbacks_equal_before_after=current_before == current_after,
             availability_18=available.get('2030-01-01T18:00'), availability_19=available.get('2030-01-01T19:00'),
             request_timings=timings, restore_elapsed_s=restore_elapsed)
    assert (first.status_code, retry.status_code, restored.status_code, replay.status_code) == (201, 200, 204, 200)
    assert first.json() == retry.json() == replay.json()
    assert [r['table_id'] for r in first.json()['reservations']] == ['two', 'one']
    assert current_before == current_after == first.json()['reservations']
    assert available['2030-01-01T18:00'] == ['one'] and available['2030-01-01T19:00'] == ['two']
    assert restore_elapsed <= 10


def test_R007_truncated_deep_json_does_not_consume_retry_key(api, record_property):
    """Malformed deep input leaves state and the retry key available for a later valid request."""
    c, token = api
    before = snapshot(c)
    bad = c.post('/reservations', content='{"ignored":' + '[' * 600,
                 headers={'Authorization': 'Bearer ' + token, 'Idempotency-Key': 'bad-then-good'})
    same = snapshot(c) == before
    good = create(c, token, 'bad-then-good', payload())
    observed(record_property, malformed=bad.status_code, error_code=bad.json().get('error', {}).get('code'),
             state_unchanged=same, subsequent=good.status_code)
    assert bad.status_code == 400 and bad.json()['error']['code'] == 'malformed_request' and same and good.status_code == 201


SPRING = [('America/New_York', '2030-03-10', '2030-03-17'),
          ('Europe/Berlin', '2030-03-31', '2030-04-07')]


@pytest.mark.parametrize('zone,day,normal', SPRING, ids=['NewYork', 'Berlin'])
def test_R008_nonexistent_closing_time_does_not_reject_valid_early_bookings(api, record_property, zone, day, normal):
    """A nonexistent 02:30 closing boundary permits early bookings while respecting real duration."""
    c, _ = api
    assert c.post('/_test/reset', json=fixture(zone, '02:30')).status_code == 204
    login = c.post('/auth/login', json={'email': 'guest@audit30.test', 'password': 'synthetic-audit-password'})
    assert login.status_code == 200
    token = login.json()['token']
    r = c.get('/availability', params={'restaurant_id': 'audit-dining', 'date': day, 'party_size': 2})
    control = c.get('/availability', params={'restaurant_id': 'audit-dining', 'date': normal, 'party_size': 2})
    assert r.status_code == control.status_code == 200
    starts = [s['starts_at_local'] for s in r.json()['slots']]
    early = create(c, token, 'spring-early', payload(starts=day+'T00:30'))
    before_late = snapshot(c)
    late = create(c, token, 'spring-late', payload('two', day+'T01:30'))
    late_unchanged = snapshot(c) == before_late
    retry = create(c, token, 'spring-early', payload(starts=day+'T00:30'))
    exported = c.get('/_test/export')
    restore = c.post('/_test/import', content=exported.content)
    replay = create(c, token, 'spring-early', payload(starts=day+'T00:30'))
    observed(record_property, zone=zone, starts=starts, normal_slots=len(control.json()['slots']),
             early=early.status_code, early_end=early.json().get('ends_at'), late=late.status_code,
             late_error=late.json().get('error', {}).get('code'), late_state_unchanged=late_unchanged,
             retry=retry.status_code, restore=restore.status_code, replay=replay.status_code,
             oracle='00:30 +60 real minutes =01:30;01:30 +60 real minutes =03:30')
    assert starts == [day+'T00:00', day+'T00:30']
    assert len(control.json()['slots']) == 4
    assert (early.status_code, late.status_code, retry.status_code, restore.status_code, replay.status_code) == (201, 422, 200, 204, 200)
    assert late.json()['error']['code'] == 'outside_opening_hours' and late_unchanged
    assert early.json() == retry.json() == replay.json()
    start = datetime.fromisoformat(early.json()['starts_at'])
    end = datetime.fromisoformat(early.json()['ends_at'])
    assert end.astimezone(ZoneInfo(zone)).strftime('%Y-%m-%dT%H:%M') == day+'T01:30'
    assert (end.astimezone(timezone.utc)-start.astimezone(timezone.utc)).total_seconds() == 3600


@pytest.mark.parametrize('zone,day,normal', SPRING, ids=['NewYork', 'Berlin'])
def test_R009_nonexistent_start_is_atomic_validation_failure(api, record_property, zone, day, normal):
    """Spring gap starts are absent from availability and rejected without occupancy or retry mutation."""
    c, _ = api
    assert c.post('/_test/reset', json=fixture(zone, '04:00')).status_code == 204
    login = c.post('/auth/login', json={'email': 'guest@audit30.test', 'password': 'synthetic-audit-password'})
    assert login.status_code == 200
    before = snapshot(c)
    bad = create(c, login.json()['token'], 'gap-start', payload(starts=day+'T02:00'))
    same = snapshot(c) == before
    available = c.get('/availability', params={'restaurant_id': 'audit-dining', 'date': day, 'party_size': 2})
    assert available.status_code == 200
    starts = [s['starts_at_local'] for s in available.json()['slots']]
    observed(record_property, zone=zone, rejected=bad.status_code,
             error_code=bad.json().get('error', {}).get('code'), state_unchanged=same, starts=starts)
    assert bad.status_code == 422 and bad.json()['error']['code'] == 'invalid_local_time' and same
    assert not any(s.endswith(('T02:00', 'T02:30')) for s in starts)
