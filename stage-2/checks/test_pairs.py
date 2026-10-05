"""Stage2 contract regressions; no external product or planning oracle."""
import gzip
import random
import unittest

from test_invariants import fixture, domain, j, server


class Pairs(unittest.TestCase):
    def setUp(self):
        value = fixture()
        rest = value['restaurants'][0]
        rest['tables'].append({'id': 'c', 'label': 'Terrace', 'capacity': 2})
        rest['combinable'] = [['b', 'a'], ['b', 'c']]
        self.store = server.Store()
        self.store.state = domain.reset(value)
        self.store.state['tokens']['session'] = 'u'
        self.headers = {'authorization': 'Bearer session'}
        self.body = {'restaurant_id': 'r', 'table_ids': ['a', 'b'], 'party_size': 6,
                     'starts_at_local': '2099-01-05T19:00'}

    def request(self, method='POST', path='/reservations', body=None, key='pair'):
        code, raw, _ = self.store.request(method, path, {}, dict(self.headers, **{'idempotency-key': key}), self.body if body is None else body)
        return code, j.loads(raw) if raw else None

    def fault(self, body, status, code, key='bad', path='/reservations'):
        before = j.dumps(self.store.state, True)
        with self.assertRaises(domain.Fault) as caught:
            self.request(path=path, body=body, key=key)
        self.assertEqual((caught.exception.status, caught.exception.code), (status, code))
        self.assertEqual(j.dumps(self.store.state, True), before)

    def test_pair_order_and_immutable_receipt_after_pair_to_single(self):
        code, original = self.request()
        self.assertEqual(code, 201)
        self.assertEqual(original['table_ids'], ['b', 'a'])
        self.assertNotIn('table_id', original)
        self.assertEqual(self.request()[0], 200)
        self.fault(dict(self.body, table_ids=['b', 'a']), 409, 'idempotency_key_reuse', key='pair')
        code, current = self.request('PATCH', '/reservations/'+original['reference'], {'table_id': 'c', 'party_size': 2})
        self.assertEqual((code, current['table_ids'], current['table_id']), (200, ['c'], 'c'))
        self.store.state = domain.import_state(domain.snapshot(self.store.state))
        self.assertTrue(j.equal(self.request()[1], original))

    def test_declared_pairs_only_not_transitive(self):
        self.fault(dict(self.body, table_ids=['a', 'c']), 422, 'combination_not_allowed')
        self.fault(dict(self.body, table_ids=['a', 'b', 'c']), 422, 'combination_not_allowed')
        self.fault(dict(self.body, table_ids=['a', 'a']), 422, 'validation_failed')
        self.fault(dict(self.body, table_id='a'), 422, 'validation_failed')
        self.fault(dict(self.body, table_ids='a'), 400, 'malformed_request')
        self.fault(dict(self.body, table_ids=['a', 'missing']), 404, 'not_found')

    def test_pair_occupies_each_member_and_half_open_adjacency(self):
        self.request()
        for table in ['a', 'b']:
            body = dict(self.body, table_ids=[table], party_size=2)
            self.fault(body, 409, 'table_unavailable', key=table)
            self.assertEqual(self.request(body=dict(body, starts_at_local='2099-01-05T20:30'), key=table)[0], 201)

    def test_atomic_pair_swap_with_single(self):
        _, pair = self.request()
        _, single = self.request(body=dict(self.body, table_ids=['c'], party_size=2), key='single')
        moves = {'moves': [{'reference': pair['reference'], 'table_id': 'c', 'party_size': 2},
                           {'reference': single['reference'], 'table_ids': ['a', 'b'], 'party_size': 6}]}
        code, receipt = self.request(path='/reservation-moves', body=moves, key='swap')
        self.assertEqual(code, 201)
        self.assertEqual([r['table_ids'] for r in receipt['reservations']], [['c'], ['b', 'a']])
        self.store.state = domain.import_state(domain.snapshot(self.store.state))
        self.assertTrue(j.equal(self.request(path='/reservation-moves', body=moves, key='swap')[1], receipt))

    def test_failed_pair_batch_preserves_every_record(self):
        _, pair = self.request()
        _, single = self.request(body=dict(self.body, table_ids=['c'], party_size=2), key='single')
        self.fault({'moves': [{'reference': pair['reference'], 'table_ids': ['b', 'c'], 'party_size': 2},
                              {'reference': single['reference']}]}, 409, 'table_unavailable', path='/reservation-moves')

    def test_cancelled_seed_does_not_occupy_either_member(self):
        value = fixture()
        value['restaurants'][0]['combinable'] = [['a', 'b']]
        value['reservations'] = [dict(self.body, id='seed', reference='ABCDEF', user_id='u', status='cancelled')]
        state = domain.reset(value)
        proposed = domain.candidate(state, self.body)
        self.assertTrue(domain.free(state, proposed))
        self.assertEqual(state['reservations']['ABCDEF']['status'], 'cancelled')

    def test_old_receipt_unknown_table_ids_remains_ignored_on_import(self):
        body = {'restaurant_id': 'r', 'table_id': 'a', 'party_size': 2, 'starts_at_local': '2099-01-05T19:00'}
        _, original = self.request(body=body)
        # Construct the old documented representation, without asserting an
        # actual old-source process run (independent verification owns that).
        record = self.store.state['reservations'][original['reference']]
        record.pop('table_ids')
        receipt = self.store.state['receipts'][0]
        receipt.pop('producer_stage')
        receipt['response'].pop('table_ids')
        receipt['body']['table_ids'] = {'previously': 'unknown'}
        saved = j.clone(receipt['response'])
        self.store.state = domain.import_state(domain.snapshot(self.store.state))
        code, replay = self.request(body=receipt['body'])
        self.assertEqual(code, 200)
        self.assertTrue(j.equal(replay, saved))
        self.assertEqual(domain.public(record)['table_ids'], ['a'])

    def test_huge_excluded_pair_stays_compact(self):
        rest = self.store.state['restaurants']['r']
        rest['tables'][0]['capacity'] = j.Number.parse('1e100000000')
        rest['opening_hours'] = [{'weekday': 'mon', 'opens': '18:00', 'closes': '20:00'}]
        rest['reservation_duration_minutes'] = j.Number.parse(120)
        self.request(body=dict(self.body, table_ids=['b'], party_size=2, starts_at_local='2099-01-05T18:00'))
        result = domain.availability(self.store.state, {'restaurant_id': 'r', 'date': '2099-01-05', 'party_size': '2'})
        self.assertEqual(result['slots'][0]['available_options'], [
            {'table_ids': ['a'], 'capacity': rest['tables'][0]['capacity']},
            {'table_ids': ['c'], 'capacity': rest['tables'][2]['capacity']}])
        self.assertLess(len(j.dumps(result)), 500)

    def test_sparse_sum_comparison_and_bounded_wire_preparation(self):
        rest = self.store.state['restaurants']['r']
        rest['tables'][0]['capacity'] = j.Number.parse('1e100000')
        value = domain.capacity(rest, ['a', 'b'])
        self.assertGreater(value, j.Number.parse('1e100000'))
        self.assertLess(value, j.Number.parse('2e100000'))
        for tail, comparison in [('3', 1), ('4', 0), ('5', -1)]:
            self.assertEqual(value.compare(j.Number.parse('1'+'0'*99999+tail)), comparison)
        prepared = server.PreparedBody(j.chunks({'capacity': value}, sparse=True))
        plain = b''.join(prepared.blocks())
        self.assertEqual(prepared.length, len(plain))
        self.assertEqual(gzip.decompress(prepared.compressed()), plain)
        self.assertTrue(j.equal(j.loads(plain)['capacity'], j.Number.parse('1'+'0'*99999+'4')))

    def test_exact_addition_and_comparison_small_independent_integers(self):
        rng = random.Random(62026)
        for _ in range(250):
            a, b = (rng.randint(1, 999999999999)*10**rng.randint(0, 120) for _ in range(2))
            total = j.add_integers(j.Number.parse(a), j.Number.parse(b))
            self.assertEqual(j.loads(j.dumps(total)), j.Number.parse(a+b))
            self.assertGreater(total, j.Number.parse(a+b-1))
            self.assertLess(total, j.Number.parse(a+b+1))


if __name__ == '__main__':
    unittest.main()
