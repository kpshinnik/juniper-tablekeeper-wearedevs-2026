"""RFC3339 must preserve exact historical IANA instants and receipt lifetime."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import test_calendar_lifetime as transport
from test_invariants import fixture, domain, j, server


class HistoricalLifetime(unittest.TestCase):
    setUpClass = classmethod(transport.CalendarLifetime.setUpClass.__func__)
    tearDownClass = classmethod(transport.CalendarLifetime.tearDownClass.__func__)
    request = transport.CalendarLifetime.request

    def lifetime(self, zone, day, start, opening='17:00', closing='23:00'):
        value = fixture()
        rest = value['restaurants'][0]
        rest['timezone'] = zone
        rest['reservation_duration_minutes'] = 60
        rest['opening_hours'] = [{'weekday': d, 'opens': opening, 'closes': closing} for d in domain.WEEKDAYS]
        self.assertEqual(self.request('POST', '/_test/reset', value)[0], 204)
        code, auth = self.request('POST', '/auth/login', {'email': 'u@example.test', 'password': 'password123'})
        self.assertEqual(code, 200)
        token = auth['token']
        code, grid = self.request('GET', '/availability?restaurant_id=r&date='+day+'&party_size=2')
        self.assertEqual(code, 200, grid)
        body = {'restaurant_id': 'r', 'table_id': 'a', 'starts_at_local': day+'T'+start, 'party_size': 2}
        code, original = self.request('POST', '/reservations', body, token, 'historical')
        self.assertEqual(code, 201, original)
        print('historical timestamps', zone, day, original['starts_at'], original['ends_at'], flush=True)
        for slot in grid['slots']:
            self.timestamp(slot['starts_at'], slot['starts_at_local'], zone)
        self.timestamp(original['starts_at'], body['starts_at_local'], zone)
        self.assertRegex(original['ends_at'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$')
        self.assertEqual(domain.utc(original['ends_at']) - domain.utc(original['starts_at']), 3600_000_000)
        self.assertEqual(original['starts_at_local'], body['starts_at_local'])
        code, conflict = self.request('POST', '/reservations', body, token, 'conflict')
        self.assertEqual((code, conflict['error']['code']), (409, 'table_unavailable'))
        code, grid = self.request('GET', '/availability?restaurant_id=r&date='+day+'&party_size=2')
        slot = next(s for s in grid['slots'] if s['starts_at_local'] == body['starts_at_local'])
        self.assertNotIn('a', slot['available_table_ids'])
        path = '/reservations/'+original['reference']
        for method, suffix, change in [('POST', '/cancel', {}), ('PATCH', '', {'party_size': 3})]:
            code, refused = self.request(method, path+suffix, change, token)
            self.assertEqual((code, refused['error']['code']), (409, 'cutoff_passed'))
        code, exported = self.request('GET', '/_test/export')
        self.assertEqual(code, 200)
        ordinary_carrier = json.loads(json.dumps(json.loads(j.dumps(exported)), allow_nan=False))
        self.assertEqual(self.request('POST', '/_test/reset', value)[0], 204)
        self.assertEqual(self.request('POST', '/_test/import', ordinary_carrier)[0], 204)
        code, replay = self.request('POST', '/reservations', body, token, 'historical')
        self.assertEqual(code, 200, replay)
        self.assertTrue(j.equal(replay, original))
        code, current = self.request('GET', path, token=token)
        self.assertEqual(code, 200, current)
        self.assertTrue(j.equal(current, original))
        code, listed = self.request('GET', '/reservations', token=token)
        self.assertEqual(code, 200)
        self.assertTrue(j.equal(listed['reservations'], [original]))
        self.assertEqual(self.request('GET', '/health')[0], 200)

    def timestamp(self, value, local, zone):
        self.assertRegex(value, r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$')
        expected = datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(zone), fold=0)
        self.assertEqual(domain.utc(value), domain.instant(expected))

    def test_berlin_1800_http_lifetime(self):
        self.lifetime('Europe/Berlin', '1800-01-01', '18:00')

    def test_new_york_1800_http_lifetime(self):
        self.lifetime('America/New_York', '1800-01-01', '18:00')

    def test_minimum_berlin_second_offset_lifetime(self):
        self.lifetime('Europe/Berlin', '0001-01-01', '00:00', '00:00', '02:00')

    def test_minimum_new_york_second_offset_lifetime(self):
        self.lifetime('America/New_York', '0001-01-01', '00:00', '00:00', '02:00')

    def test_formatter_second_offsets_at_both_calendar_extrema(self):
        # Formatter boundaries include a fixed second offset at the maximum
        # year; this is a unit check, not a claim about future IANA zone rules.
        for day, seconds in [('0001-01-01T00:00:00', 3208), ('9999-12-31T23:59:59', -3208)]:
            with self.subTest(day=day, seconds=seconds):
                original = datetime.fromisoformat(day).replace(tzinfo=timezone(timedelta(seconds=seconds)))
                encoded = domain.timestamp(original)
                self.assertRegex(encoded, r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$')
                self.assertEqual(domain.utc(encoded), domain.instant(original))

    def test_legacy_offset_seconds_receipt_remains_original(self):
        value = fixture()
        rest = value['restaurants'][0]
        rest.update(timezone='Europe/Berlin', reservation_duration_minutes=60,
                    opening_hours=[{'weekday': d, 'opens': '17:00', 'closes': '23:00'} for d in domain.WEEKDAYS])
        source = server.Store()
        source.state = domain.reset(value)
        source.state['tokens']['legacy-session'] = 'u'
        headers = {'authorization': 'Bearer legacy-session', 'idempotency-key': 'legacy'}
        body = {'restaurant_id': 'r', 'table_id': 'a', 'party_size': 2, 'starts_at_local': '1800-01-01T18:00'}
        code, raw, _ = source.request('POST', '/reservations', {}, headers, body)
        self.assertEqual(code, 201)
        current = j.loads(raw)
        # Exact timestamp representation emitted by the previous product; this is
        # a format-compatibility fixture, not a claimed old-producer execution.
        legacy = dict(current, starts_at='1800-01-01T18:00:00+00:53:28', ends_at='1800-01-01T19:00:00+00:53:28')
        source.state['reservations'][legacy['reference']].update(legacy)
        source.state['receipts'][0]['response'] = j.clone(legacy)
        destination = server.Store()
        destination.state = domain.import_state(domain.snapshot(source.state))
        self.assertTrue(j.equal(source.state, destination.state))
        code, raw, _ = destination.request('POST', '/reservations', {}, headers, body)
        self.assertEqual(code, 200)
        self.assertTrue(j.equal(j.loads(raw), legacy))
        code, raw, _ = destination.request('GET', '/reservations/'+legacy['reference'], {}, headers, None)
        self.assertEqual(code, 200)
        self.timestamp(j.loads(raw)['starts_at'], body['starts_at_local'], 'Europe/Berlin')


if __name__ == '__main__':
    unittest.main()
