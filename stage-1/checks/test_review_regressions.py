"""Permanent regressions for independent review counterexamples."""
import socket
import json
import threading
import time
import unittest

from test_invariants import fixture, domain, j, server


class GapBoundaries(unittest.TestCase):
    def state(self, zone, opens='00:00', closes='02:30'):
        value = fixture()
        rest = value['restaurants'][0]
        rest['timezone'] = zone
        rest['reservation_duration_minutes'] = j.Number.parse('60')
        rest['opening_hours'] = [{'weekday': 'sun', 'opens': opens, 'closes': closes}]
        return domain.reset(value)

    def assert_gap_closing(self, zone, day):
        state = self.state(zone)
        result = domain.availability(state, {'restaurant_id': 'r', 'date': day, 'party_size': '2'})
        self.assertEqual([s['starts_at_local'] for s in result['slots']], [day+'T00:00', day+'T00:30'])
        body = {'restaurant_id': 'r', 'table_id': 'a', 'party_size': j.Number.parse('2'), 'starts_at_local': day+'T00:30'}
        self.assertEqual(domain.candidate(state, body)['starts_at_local'], day+'T00:30')
        body['starts_at_local'] = day+'T01:30'
        before = j.dumps(state, True)
        with self.assertRaises(domain.Fault) as caught:
            domain.candidate(state, body)
        self.assertEqual(caught.exception.code, 'outside_opening_hours')
        self.assertEqual(j.dumps(state, True), before)

    def test_new_york_gap_closing(self):
        self.assert_gap_closing('America/New_York', '2030-03-10')

    def test_berlin_gap_closing(self):
        self.assert_gap_closing('Europe/Berlin', '2030-03-31')

    def test_gap_opening_retains_later_grid_slots(self):
        for zone, day in [('America/New_York', '2030-03-10'), ('Europe/Berlin', '2030-03-31')]:
            state = self.state(zone, '02:30', '05:00')
            result = domain.availability(state, {'restaurant_id': 'r', 'date': day, 'party_size': '2'})
            self.assertEqual([s['starts_at_local'] for s in result['slots']], [day+'T03:00', day+'T03:30', day+'T04:00'])


class AbsoluteInputDeadline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = server.Server(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def drip(self, initial, byte):
        before = j.dumps(server.STORE.state, True)
        stop = threading.Event()
        with socket.create_connection(self.server.server_address, timeout=6.2) as connection:
            connection.sendall(initial)
            started = time.monotonic()
            def sender():
                while not stop.wait(.1):
                    try:
                        connection.sendall(byte)
                    except OSError:
                        break
            thread = threading.Thread(target=sender, daemon=True)
            thread.start()
            observed = None
            try:
                observed = connection.recv(65536)
            except socket.timeout:
                pass
            finally:
                elapsed = time.monotonic() - started
                stop.set(); thread.join(timeout=1)
        self.assertIsNotNone(observed, 'Continuous bytes kept incomplete input alive beyond 6.2 seconds')
        self.assertLessEqual(elapsed, 6)
        self.assertTrue(not observed or b'400 Bad Request' in observed, observed)
        self.assertEqual(j.dumps(server.STORE.state, True), before)
        self.assertEqual(server.STORE.request('GET', '/health', {}, {}, {})[0], 200)

    def test_body_drip_absolute_deadline(self):
        self.drip(b'POST /auth/login HTTP/1.1\r\nContent-Length: 1000\r\n\r\n{', b' ')

    def test_header_drip_absolute_deadline(self):
        self.drip(b'POST /auth/login HTTP/1.1\r\nX-Slow: ', b'x')


class StateBoundaryRegressions(unittest.TestCase):
    def test_reset_reservations_wrong_types_are_malformed_and_atomic(self):
        for wrong in [None, True, j.Number.parse('42'), '', {}, 'bad']:
            with self.subTest(value=wrong):
                store = server.Store()
                store.state = domain.reset(fixture())
                before = j.dumps(store.state, True)
                body = fixture()
                body['reservations'] = wrong
                with self.assertRaises(domain.Fault) as caught:
                    store.request('POST', '/_test/reset', {}, {}, body)
                self.assertEqual((caught.exception.status, caught.exception.code), (400, 'malformed_request'))
                self.assertEqual(j.dumps(store.state, True), before)

    def test_exact_snapshot_survives_ordinary_client_json_roundtrip(self):
        for numeric in ['1e400', '1e-400', '1.00000000000000000000000000000000000001']:
            with self.subTest(number=numeric):
                store = server.Store()
                store.state = domain.reset(fixture())
                store.state['tokens']['test-token'] = 'u'
                headers = {'authorization': 'Bearer test-token', 'idempotency-key': 'portable'}
                body = {'restaurant_id': 'r', 'table_id': 'a', 'starts_at_local': '2099-01-05T19:00',
                        'party_size': j.Number.parse('2'), 'unknown': j.Number.parse(numeric)}
                first = store.request('POST', '/reservations', {}, headers, body)
                exported = store.request('GET', '/_test/export', {}, {}, {})[1]
                # An ordinary opaque-state carrier need not implement exact decimals.
                carried = json.dumps(json.loads(exported), allow_nan=False)
                imported = domain.import_state(j.loads(carried))
                fresh = server.Store(); fresh.state = imported
                replay = fresh.request('POST', '/reservations', {}, headers, body)
                self.assertEqual(replay[0], 200)
                self.assertTrue(j.equal(j.loads(first[1]), j.loads(replay[1])))
                changed = dict(body, unknown=j.Number.parse('0'))
                with self.assertRaises(domain.Fault) as caught:
                    fresh.request('POST', '/reservations', {}, headers, changed)
                self.assertEqual(caught.exception.code, 'idempotency_key_reuse')


if __name__ == '__main__':
    unittest.main()
