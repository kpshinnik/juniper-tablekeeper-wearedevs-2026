"""Developer regressions derived from the contract, independent of shipped tests."""
import concurrent.futures
import pathlib
import socket
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import domain
import exactjson as j
import server


def fixture():
    return j.loads('''{"users":[{"id":"u","email":"u@example.test","password":"password123","display_name":"Ada"}],
    "restaurants":[{"id":"r","name":"Juniper","timezone":"Europe/Berlin","slot_minutes":30,
    "reservation_duration_minutes":90,"cancellation_cutoff_minutes":0,
    "opening_hours":[{"weekday":"mon","opens":"00:00","closes":"23:59"},{"weekday":"sun","opens":"00:00","closes":"05:00"}],
    "tables":[{"id":"a","label":"Window","capacity":4},{"id":"b","label":"Garden","capacity":4}]}],"reservations":[]}''')


class Invariants(unittest.TestCase):
    def setUp(self):
        self.store = server.Store()
        self.store.state = domain.reset(fixture())
        self.store.state['tokens']['test-token'] = 'u'
        self.headers = {'authorization': 'Bearer test-token', 'idempotency-key': 'one'}
        self.body = j.loads('{"restaurant_id":"r","table_id":"a","starts_at_local":"2099-01-05T19:00","party_size":2}')

    def request(self, method='POST', path='/reservations', body=None, headers=None):
        code, raw, _ = self.store.request(method, path, {}, headers or self.headers, self.body if body is None else body)
        return code, j.loads(raw) if raw else None

    def test_original_receipt_survives_cancel_and_replacement(self):
        code, original = self.request()
        self.assertEqual(code, 201)
        ref = original['reference']
        self.request('POST', '/reservations/' + ref + '/cancel', {})
        snapshot = domain.snapshot(self.store.state)
        self.store.state = domain.import_state(j.loads(j.dumps(snapshot)))
        self.assertEqual(self.request()[0], 200)
        self.assertTrue(j.equal(self.request()[1], original))
        self.assertEqual(self.request('GET', '/reservations/' + ref)[1]['status'], 'cancelled')

    def test_failed_response_preparation_does_not_publish(self):
        before = j.dumps(self.store.state, True)
        with patch.object(self.store, 'prepare', side_effect=ValueError('injected preparation failure')):
            with self.assertRaises(ValueError):
                self.request()
        self.assertEqual(j.dumps(self.store.state, True), before)
        self.assertEqual(self.request()[0], 201)

    def test_concurrent_identical_requests_exactly_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(lambda _: self.request(), range(20)))
        self.assertEqual([r[0] for r in results].count(201), 1)
        self.assertEqual(len(self.store.state['reservations']), 1)
        self.assertTrue(all(j.equal(r[1], results[0][1]) for r in results))

    def test_deep_exact_unknown_value_lifetime(self):
        deep = '[' * 2200 + '1.000e100000000' + ']' * 2200
        self.body['unknown'] = j.loads(deep)
        self.request()
        self.body['unknown'] = j.loads(deep.replace('1.000e100000000', '10e99999999'))
        self.assertEqual(self.request()[0], 200)
        self.store.state = domain.import_state(j.loads(j.dumps(domain.snapshot(self.store.state))))
        self.assertEqual(self.request()[0], 200)

    def test_boolean_is_not_equivalent_number(self):
        self.body['unknown'] = True
        self.request()
        self.body['unknown'] = j.Number.parse('1')
        with self.assertRaises(domain.Fault) as caught:
            self.request()
        self.assertEqual(caught.exception.code, 'idempotency_key_reuse')

    def test_receipt_precedes_invalid_changed_body(self):
        self.request()
        with self.assertRaises(domain.Fault) as caught:
            self.request(body={'party_size': False})
        self.assertEqual(caught.exception.code, 'idempotency_key_reuse')

    def test_atomic_swap_and_conflict_rollback(self):
        _, one = self.request()
        second_body = dict(self.body, table_id='b')
        _, two = self.request(body=second_body, headers=dict(self.headers, **{'idempotency-key': 'two'}))
        moves = {'moves': [{'reference': one['reference'], 'table_id': 'b'}, {'reference': two['reference'], 'table_id': 'a'}]}
        code, result = self.request(path='/reservation-moves', body=moves)
        self.assertEqual(code, 201)
        self.assertEqual([r['table_id'] for r in result['reservations']], ['b', 'a'])
        before = j.dumps(self.store.state, True)
        moves['moves'][1]['table_id'] = 'b'
        with self.assertRaises(domain.Fault):
            self.request(path='/reservation-moves', body=moves, headers=dict(self.headers, **{'idempotency-key': 'bad'}))
        self.assertEqual(j.dumps(self.store.state, True), before)

    def test_corrupt_import_preserves_destination(self):
        self.request()
        before = j.dumps(self.store.state, True)
        exported = domain.snapshot(self.store.state)
        payload = exported['state']['payload']
        decoded = j.loads(payload) if isinstance(payload, str) else payload
        decoded['tokens'].clear()
        exported['state']['payload'] = j.dumps(decoded).decode('ascii') if isinstance(payload, str) else decoded
        with self.assertRaises(domain.Fault):
            self.request(path='/_test/import', body=exported)
        self.assertEqual(j.dumps(self.store.state, True), before)

    def test_dst_fold_duration_and_gap(self):
        r = self.store.state['restaurants']['r']
        start, end = domain.interval(r, '2026-10-25T01:30')
        self.assertEqual(start.isoformat(), '2026-10-25T01:30:00+02:00')
        self.assertEqual(end.isoformat(), '2026-10-25T02:00:00+01:00')
        with self.assertRaises(domain.Fault) as caught:
            domain.interval(r, '2026-03-29T02:30')
        self.assertEqual(caught.exception.code, 'invalid_local_time')

    def test_half_open_adjacency(self):
        self.request()
        second = dict(self.body, starts_at_local='2099-01-05T20:30')
        self.assertEqual(self.request(body=second, headers=dict(self.headers, **{'idempotency-key': 'adjacent'}))[0], 201)

    def test_huge_compact_party_rejected_without_expansion(self):
        self.body['party_size'] = j.Number.parse('1e100000000')
        with self.assertRaises(domain.Fault) as caught:
            self.request()
        self.assertEqual(caught.exception.code, 'party_exceeds_capacity')
        self.assertEqual(self.store.state['receipts'], [])

    def test_numerically_equivalent_body_retry(self):
        self.request()
        self.body['party_size'] = j.Number.parse('2.000e0')
        self.assertEqual(self.request()[0], 200)


class Transport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = server.Server(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def exchange(self, raw):
        with socket.create_connection(self.server.server_address, timeout=5) as s:
            s.sendall(raw); s.shutdown(socket.SHUT_WR)
            received = b''
            while True:
                part = s.recv(65536)
                if not part:
                    return received
                received += part

    def test_rejected_framing_cannot_dispatch_unread_payload(self):
        server.STORE.state = domain.reset(fixture())
        before = j.dumps(server.STORE.state, True)
        reset = b'POST /_test/reset HTTP/1.1\r\nContent-Length: 45\r\n\r\n{"users":[],"restaurants":[],"reservations":[]}'
        for headers in [b'Content-Length: 0\r\nContent-Length: 1', b'Transfer-Encoding: chunked', b'Content-Length: +2', b'Bad Header: x']:
            response = self.exchange(b'POST /wrong HTTP/1.1\r\n' + headers + b'\r\n\r\n' + reset)
            self.assertIn(b'400 Bad Request', response)
            self.assertEqual(response.count(b'HTTP/1.1'), 1)
            self.assertEqual(j.dumps(server.STORE.state, True), before)

    def test_truncated_and_malformed_json_do_not_mutate(self):
        server.STORE.state = domain.reset(fixture())
        before = j.dumps(server.STORE.state, True)
        for raw in [b'{}', b'{"users": [}']:
            response = self.exchange(b'POST /_test/reset HTTP/1.1\r\nContent-Length: 90\r\n\r\n' + raw)
            self.assertIn(b'400 Bad Request', response)
            self.assertEqual(j.dumps(server.STORE.state, True), before)


if __name__ == '__main__':
    unittest.main()
