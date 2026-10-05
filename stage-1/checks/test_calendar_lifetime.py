"""Valid local calendar extrema must survive the complete HTTP lifetime."""
import http.client
import threading
import unittest

from test_invariants import fixture, domain, j, server


class CalendarLifetime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = server.Server(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def request(self, method, path, body=None, token=None, key=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if key:
            headers['Idempotency-Key'] = key
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, path, body=j.dumps(body) if body is not None else None, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            return response.status, j.loads(raw) if raw else None
        finally:
            connection.close()

    def lifetime(self, day, zone, opening, closing, start, end, offset):
        value = fixture()
        rest = value['restaurants'][0]
        rest['timezone'] = zone
        rest['reservation_duration_minutes'] = j.Number.parse('30')
        rest['opening_hours'] = [{'weekday': d, 'opens': opening, 'closes': closing} for d in domain.WEEKDAYS]
        self.assertEqual(self.request('POST', '/_test/reset', value)[0], 204)
        code, auth = self.request('POST', '/auth/login', {'email': 'u@example.test', 'password': 'password123'})
        self.assertEqual(code, 200)
        token = auth['token']
        code, grid = self.request('GET', '/availability?restaurant_id=r&date='+day+'&party_size=2')
        self.assertEqual(code, 200, grid)
        self.assertIn(day+'T'+start, [s['starts_at_local'] for s in grid['slots']])
        body = {'restaurant_id': 'r', 'table_id': 'a', 'starts_at_local': day+'T'+start, 'party_size': 2}
        code, original = self.request('POST', '/reservations', body, token, 'edge')
        self.assertEqual(code, 201, original)
        self.assertEqual(original['ends_at'], day+'T'+end+':00'+offset)
        code, collision = self.request('POST', '/reservations', body, token, 'conflict')
        self.assertEqual((code, collision['error']['code']), (409, 'table_unavailable'))
        code, listed = self.request('GET', '/reservations', token=token)
        self.assertEqual(code, 200, listed)
        self.assertEqual(listed['reservations'][0]['reference'], original['reference'])
        path = '/reservations/'+original['reference']
        expected_status = 'confirmed'
        if day.startswith('0001'):
            code, refused = self.request('POST', path+'/cancel', {}, token)
            self.assertEqual((code, refused['error']['code']), (409, 'cutoff_passed'))
        else:
            code, amended = self.request('PATCH', path, {'party_size': 3}, token)
            self.assertEqual(code, 200, amended)
            code, cancelled = self.request('POST', path+'/cancel', {}, token)
            self.assertEqual(code, 200, cancelled)
            expected_status = 'cancelled'
        code, exported = self.request('GET', '/_test/export')
        self.assertEqual(code, 200)
        self.assertEqual(self.request('POST', '/_test/reset', value)[0], 204)
        self.assertEqual(self.request('POST', '/_test/import', exported)[0], 204)
        code, replay = self.request('POST', '/reservations', body, token, 'edge')
        self.assertEqual(code, 200, replay)
        self.assertTrue(j.equal(replay, original))
        code, current = self.request('GET', path, token=token)
        self.assertEqual(code, 200, current)
        self.assertEqual(current['status'], expected_status)

    def test_minimum_local_date_plus_one(self):
        self.lifetime('0001-01-01', 'Etc/GMT-1', '00:00', '01:00', '00:00', '00:30', '+01:00')

    def test_maximum_local_date_minus_one(self):
        self.lifetime('9999-12-31', 'Etc/GMT+1', '22:00', '23:59', '23:00', '23:30', '-01:00')

    def test_minimum_utc_control(self):
        self.lifetime('0001-01-01', 'UTC', '00:00', '01:00', '00:00', '00:30', '+00:00')

    def test_maximum_utc_control(self):
        self.lifetime('9999-12-31', 'UTC', '22:00', '23:59', '23:00', '23:30', '+00:00')


if __name__ == '__main__':
    unittest.main()
