"""Imported receipts must be internally valid historical operation results."""
import hashlib
import unittest

from test_invariants import fixture, domain, j, server


class ReceiptSemantics(unittest.TestCase):
    def source(self):
        store = server.Store()
        store.state = domain.reset(fixture())
        store.state['tokens']['source-session'] = 'u'
        headers = {'authorization': 'Bearer source-session'}
        references = []
        for index, table in enumerate(['a', 'b']):
            body = {'restaurant_id': 'r', 'table_id': table, 'party_size': j.Number.parse('2'),
                    'starts_at_local': '2099-01-05T19:00'}
            result = store.request('POST', '/reservations', {}, dict(headers, **{'idempotency-key': 'create'+str(index)}), body)
            references.append(j.loads(result[1])['reference'])
        moves = {'moves': [{'reference': references[0], 'table_id': 'b'}, {'reference': references[1], 'table_id': 'a'}]}
        store.request('POST', '/reservation-moves', {}, dict(headers, **{'idempotency-key': 'swap'}), moves)
        return store, references, headers

    def reject_corruption(self, kind):
        source, _, _ = self.source()
        exported = domain.snapshot(source.state)
        control = domain.import_state(exported)
        self.assertTrue(j.equal(control, source.state))
        payload = j.loads(exported['state']['payload'])
        receipt = next(r for r in payload['receipts'] if r['key'] == ('swap' if kind == 'order' else 'create0'))
        if kind == 'response-party':
            receipt['response']['party_size'] = j.Number.parse('3')
        elif kind == 'request-party':
            receipt['body']['party_size'] = j.Number.parse('3')
        elif kind == 'start':
            receipt['response']['starts_at'] = '2099-01-05T20:00:00+01:00'
        elif kind == 'end':
            receipt['response']['ends_at'] = receipt['response']['starts_at']
        else:
            receipt['response']['reservations'].reverse()
        encoded = j.dumps(payload)
        exported['state'] = {'payload': encoded.decode('ascii'), 'sha256': hashlib.sha256(encoded).hexdigest()}
        destination = server.Store()
        destination.state = domain.reset(fixture())
        destination.state['tokens']['destination-session'] = 'u'
        before = j.dumps(destination.state, True)
        with self.assertRaises(domain.Fault) as caught:
            destination.request('POST', '/_test/import', {}, {}, exported)
        self.assertEqual((caught.exception.status, caught.exception.code), (422, 'validation_failed'))
        self.assertEqual(j.dumps(destination.state, True), before)

    def test_receipt_response_party_corruption(self):
        self.reject_corruption('response-party')

    def test_receipt_request_party_corruption(self):
        self.reject_corruption('request-party')

    def test_receipt_start_inconsistent_with_local(self):
        self.reject_corruption('start')

    def test_receipt_zero_elapsed_duration(self):
        self.reject_corruption('end')

    def test_batch_receipt_order_matches_request(self):
        self.reject_corruption('order')

    def test_valid_historical_receipts_survive_later_changes(self):
        source, references, headers = self.source()
        source.request('PATCH', '/reservations/'+references[0], {}, headers, {'party_size': j.Number.parse('3')})
        source.request('POST', '/reservations/'+references[1]+'/cancel', {}, headers, {})
        # A no-op move is itself a valid immutable receipt.
        source.request('POST', '/reservation-moves', {}, dict(headers, **{'idempotency-key': 'noop'}),
                       {'moves': [{'reference': references[0]}]})
        exported = domain.snapshot(source.state)
        destination = server.Store()
        destination.state = domain.import_state(exported)
        for receipt in source.state['receipts']:
            replay = destination.request('POST', receipt['path'], {},
                dict(headers, **{'idempotency-key': receipt['key']}), receipt['body'])
            self.assertEqual(replay[0], 200)
            self.assertTrue(j.equal(j.loads(replay[1]), receipt['response']))


if __name__ == '__main__':
    unittest.main()
