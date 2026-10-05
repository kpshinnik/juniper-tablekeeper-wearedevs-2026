"""Stage3 developer contract checks. Independent room verification is separate."""
import concurrent.futures
import unittest
from unittest.mock import patch

from test_invariants import domain, fixture, j, server
import legacy


class PoliciesAndSeries(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture()
        self.fixture['users'].append(dict(id='other', email='other@example.test', password='password123', display_name='Other'))
        rest = self.fixture['restaurants'][0]
        rest['manager_user_ids'] = ['u']
        rest['combinable'] = [['b', 'a']]
        self.store = server.Store()
        self.store.state = domain.reset(self.fixture)
        self.store.state['tokens'].update(session='u', other='other')
        self.body = dict(restaurant_id='r', table_id='a', starts_at_local='2099-01-05T19:00', party_size=2)

    def request(self, path='/reservations', body=None, method='POST', key='one', token='session', query=None):
        headers = {'idempotency-key': key}
        if token:
            headers['authorization'] = 'Bearer ' + token
        status, raw, _ = self.store.request(method, path, query or {}, headers, self.body if body is None else body)
        return status, j.loads(raw) if raw else None

    def fail(self, code, path, body, **kwargs):
        before = j.dumps(self.store.state)
        with self.assertRaises(domain.Fault) as caught:
            self.request(path, body, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(j.dumps(self.store.state), before)
        return caught.exception.status

    def policy(self, date='2099-01-01', duration=120, capacity=4):
        return dict(effective_from=date, slot_minutes=30, reservation_duration_minutes=duration,
                    cancellation_cutoff_minutes=60, opening_hours=self.fixture['restaurants'][0]['opening_hours'],
                    capacities={'a': capacity, 'b': capacity})

    def publish(self, **kwargs):
        return self.request('/restaurants/r/policies', self.policy(**kwargs), key=str(kwargs))

    def lookup(self, reference):
        return self.request('/reservations/' + reference, method='GET')[1]

    def history(self, reference):
        return self.request('/reservations/' + reference + '/history', method='GET')[1]['entries']

    def adopt(self, reference, count=3):
        return self.request('/series', dict(anchor_reference=reference, count=count, interval_weeks=1), key='adopt')

    def test_policy_publication_order_ties_and_accepted_terms(self):
        _, original = self.request()
        self.publish(date='2099-01-04', duration=120)
        self.publish(date='2099-01-01', duration=60)
        self.publish(date='2099-01-04', duration=30)
        self.assertTrue(j.equal(original, self.lookup(original['reference'])))
        policies = self.request('/restaurants/r/policies', method='GET', token=None)[1]['policies']
        self.assertEqual([p['policy_version'] for p in policies], [1, 2, 3])
        _, amended = self.request('/reservations/' + original['reference'], {'party_size': 3}, method='PATCH')
        self.assertEqual(amended['accepted_terms']['policy_version'], 3)
        self.assertEqual(amended['ends_at'], '2099-01-05T19:30:00+01:00')
        self.assertEqual(amended['revision'], 2)
        self.assertEqual([e['accepted_terms']['policy_version'] for e in self.history(original['reference'])], [0, 3])
        self.assertTrue(j.equal(self.request()[1], original))

    def test_noop_retains_terms_after_closed_policy(self):
        _, original = self.request()
        policy = self.policy(); policy['opening_hours'] = []
        self.request('/restaurants/r/policies', policy, key='close')
        before = j.dumps(self.store.state)
        _, same = self.request('/reservations/' + original['reference'], {'party_size': 2}, method='PATCH')
        self.assertTrue(j.equal(original, same))
        self.assertEqual(j.dumps(self.store.state), before)
        self.fail('outside_opening_hours', '/reservations/' + original['reference'], {'party_size': 3}, method='PATCH')

    def test_policy_invalid_types_and_permissions_nonmutation(self):
        for field, invalid in [('slot_minutes', True), ('reservation_duration_minutes', 1441),
                                ('cancellation_cutoff_minutes', -1), ('effective_from', '2099-02-30'),
                                ('opening_hours', {}), ('capacities', {'a': 4}), ('capacities', {'a': 101, 'b': 4})]:
            with self.subTest(field=field, invalid=invalid):
                policy = self.policy(); policy[field] = invalid
                self.assertEqual(self.fail('validation_failed', '/restaurants/r/policies', policy), 422)
        self.assertEqual(self.fail('forbidden', '/restaurants/r/policies', self.policy(), token='other'), 403)
        self.assertEqual(self.fail('unauthenticated', '/restaurants/r/policies', self.policy(), token=None), 401)
        self.assertEqual(self.publish()[1]['policy_version'], 1)
        self.assertEqual(self.publish()[0], 200)

    def test_explanations_both_false_and_no_explain_shape(self):
        self.request()
        query = dict(restaurant_id='r', date='2099-01-05', party_size='5', explain='true')
        result = self.request('/availability', method='GET', token=None, query=query)[1]
        slot = next(s for s in result['slots'] if s['starts_at_local'].endswith('19:00'))
        self.assertEqual([r['holds'] for r in slot['explain'][0]['rules']], [False, False])
        self.assertEqual([r['holds'] for r in slot['explain'][1]['rules']], [False, True])
        del query['explain']
        result = self.request('/availability', method='GET', query=query)[1]
        self.assertTrue(all('explain' not in s and 'available_options' in s for s in result['slots']))
        for value in ('false', '1', ''):
            self.fail('validation_failed', '/availability', {}, method='GET', query=dict(query, explain=value))

    def test_policy_zero_capacity_remains_uncapped_and_exact(self):
        self.fixture['restaurants'][0]['tables'][0]['capacity'] = j.Number.parse('1e100000000')
        self.store.state = domain.reset(self.fixture); self.store.state['tokens']['session'] = 'u'
        self.body['party_size'] = j.Number.parse('1e100000000')
        _, original = self.request()
        self.publish(capacity=1)
        _, same = self.request('/reservations/' + original['reference'], {}, method='PATCH')
        self.assertTrue(j.equal(same, original))
        self.fail('party_exceeds_capacity', '/reservations/' + original['reference'], {'starts_at_local': '2099-01-05T20:00'}, method='PATCH')

    def test_stale_revision_precedes_cutoff_validation_and_concurrency(self):
        _, original = self.request()
        ref = original['reference']
        self.fail('stale_revision', '/reservations/' + ref, {'expected_revision': 2, 'party_size': False}, method='PATCH')
        def edit(size):
            try:
                return self.request('/reservations/' + ref, {'expected_revision': 1, 'party_size': size}, method='PATCH')[0]
            except domain.Fault as error:
                return error.code
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(edit, [3, 4]))
        self.assertEqual(results.count(200), 1)
        self.assertEqual(results.count('stale_revision'), 1)
        self.assertEqual(len(self.history(ref)), 2)
        self.assertEqual(self.store.state['restaurant_revisions']['r'], 2)

    def test_owner_only_history_decision_series_including_signed_out(self):
        _, original = self.request()
        _, series = self.adopt(original['reference'])
        for path in ['/reservations/' + original['reference'] + '/history',
                     '/reservations/' + original['reference'] + '/decision', '/series/' + series['series_id']]:
            for token in (None, 'other'):
                self.assertEqual(self.fail('not_found', path, {}, method='GET', token=token), 404)

    def test_adoption_authentic_anchor_and_independent_policies(self):
        _, original = self.request()
        history = self.history(original['reference'])
        self.publish(date='2099-01-12', duration=60)
        _, series = self.adopt(original['reference'])
        self.assertTrue(j.equal(series['occurrences'][0]['reservation'], original))
        self.assertTrue(j.equal(self.history(original['reference']), history))
        self.assertEqual([o['reservation']['accepted_terms']['policy_version'] for o in series['occurrences']], [0, 1, 1])
        self.assertEqual(self.store.state['restaurant_revisions']['r'], 3)
        self.assertTrue(j.equal(self.request()[1], original))
        self.assertEqual(self.adopt(original['reference'])[0], 200)

    def test_series_failure_rolls_back_generated_members_and_receipt(self):
        _, original = self.request()
        self.request(body=dict(self.body, starts_at_local='2099-01-19T19:00'), key='conflict')
        self.fail('table_unavailable', '/series', dict(anchor_reference=original['reference'], count=3, interval_weeks=1), key='adopt')
        self.assertEqual(self.adopt(original['reference'], count=2)[0], 201)

    def test_batch_once_per_series_permanent_exception_and_cancel(self):
        _, original = self.request()
        _, series = self.adopt(original['reference'])
        refs = [o['reference'] for o in series['occurrences']]
        moves = {'moves': [{'reference': ref, 'party_size': 3} for ref in refs[:2]]}
        self.request('/reservation-moves', moves, key='moves')
        current = self.request('/series/' + series['series_id'], method='GET')[1]
        self.assertEqual(current['revision'], 2)
        self.assertEqual([o['exception'] for o in current['occurrences']], [True, True, False])
        self.request('/reservations/' + refs[0] + '/cancel', {})
        current = self.request('/series/' + series['series_id'], method='GET')[1]
        self.assertEqual(current['revision'], 3)
        self.assertTrue(current['occurrences'][0]['exception'])
        before = j.dumps(self.store.state)
        self.request('/reservations/' + refs[0] + '/cancel', {})
        self.assertEqual(j.dumps(self.store.state), before)
        self.assertTrue(j.equal(self.adopt(original['reference'])[1], series))

    def test_pair_history_and_reversed_pair_noop(self):
        self.body.pop('table_id'); self.body['table_ids'] = ['a', 'b']
        _, original = self.request()
        ref = original['reference']
        self.assertEqual(self.history(ref)[0]['changes'][0]['field'], 'table_ids')
        _, same = self.request('/reservations/' + ref, {'table_ids': ['b', 'a']}, method='PATCH')
        self.assertTrue(j.equal(same, original))
        self.request('/reservations/' + ref, {'table_id': 'b'}, method='PATCH')
        self.assertEqual(self.history(ref)[1]['changes'][0], {'field': 'table_ids', 'from': ['b', 'a'], 'to': ['b']})

    def test_valid_roundtrip_and_semantically_corrupt_journal_state(self):
        _, original = self.request()
        self.publish()
        _, series = self.adopt(original['reference'])
        ref = series['occurrences'][1]['reference']
        self.request('/reservations/' + ref, {'party_size': 3}, method='PATCH')
        snapshot = domain.snapshot(self.store.state)
        restored = domain.import_state(j.loads(j.dumps(snapshot)))
        self.assertTrue(j.equal(restored, self.store.state))
        mutators = [lambda s: s['reservations'][ref].update(revision=99),
                    lambda s: s['series'][series['series_id']].update(revision=1),
                    lambda s: s['series'][series['series_id']]['occurrences'][1].update(exception=False),
                    lambda s: s['series'][series['series_id']]['occurrences'][1].update(scheduled_date='2099-01-20'),
                    lambda s: s['histories'][ref][0]['accepted_terms'].update(policy_version=0),
                    lambda s: s['receipts'][0]['response'].update(party_size=3),
                    lambda s: s['receipts'][0]['body'].update(party_size=3),
                    lambda s: s['restaurant_revisions'].update(r=0)]
        for mutate in mutators:
            altered = j.clone(restored); mutate(altered)
            self.fail('validation_failed', '/_test/import', domain.snapshot(altered), token=None)

    def test_legacy_producer_import_preserves_old_receipts_without_fabricated_events(self):
        old = legacy.reset(self.fixture); old['tokens']['session'] = 'u'
        body = dict(self.body, expected_revision=False, ignored=j.loads('1.00000000000000000001'))
        status, original, old = legacy.dispatch(old, 'POST', '/reservations', {},
                                               {'authorization': 'Bearer session', 'idempotency-key': 'one'}, body)
        self.assertEqual(status, 201)
        ref = original['reference']
        _, _, old = legacy.dispatch(old, 'PATCH', '/reservations/' + ref, {},
                                   {'authorization': 'Bearer session'}, {'party_size': 3})
        self.store.state = domain.import_state(legacy.snapshot(old))
        self.assertEqual(self.history(ref), [])
        self.assertTrue(j.equal(self.request(body=body)[1], original))
        self.assertNotIn('revision', original)
        _, series = self.adopt(ref)
        self.assertEqual(self.history(ref), [])
        self.assertEqual(series['occurrences'][0]['reservation']['party_size'], 3)
        self.store.state = domain.import_state(domain.snapshot(self.store.state))
        self.assertTrue(j.equal(self.request(body=body)[1], original))

    def test_preparation_failure_rolls_back_policy_series_and_every_counter(self):
        _, original = self.request()
        for path, body in [('/restaurants/r/policies', self.policy()),
                           ('/series', dict(anchor_reference=original['reference'], count=3, interval_weeks=1))]:
            before = j.dumps(self.store.state)
            with patch.object(self.store, 'prepare', side_effect=ValueError('synthetic preparation failure')):
                with self.assertRaises(ValueError):
                    self.request(path, body, key='fault')
            self.assertEqual(j.dumps(self.store.state), before)
            self.assertEqual(self.request(path, body, key='fault')[0], 201)

    def test_series_dst_gap_rollback_and_first_occurrence_policy_error(self):
        value = fixture()
        value['restaurants'][0].update(cancellation_cutoff_minutes=0, reservation_duration_minutes=30)
        self.store.state = domain.reset(value); self.store.state['tokens']['session'] = 'u'
        # Future Berlin spring transition: generated occurrence 1 has no 02:30.
        self.body['starts_at_local'] = '2030-03-24T02:30'
        _, anchor = self.request()
        self.fail('invalid_local_time', '/series', dict(anchor_reference=anchor['reference'], count=3, interval_weeks=1))
        self.assertEqual(len(self.store.state['reservations']), 1)
        self.assertEqual(self.store.state['restaurant_revisions']['r'], 1)

    def test_noop_batch_and_failed_multi_series_move_have_exact_counters(self):
        _, anchor = self.request()
        _, series = self.adopt(anchor['reference'])
        refs = [o['reference'] for o in series['occurrences']]
        moves = {'moves': [{'reference': ref, 'expected_revision': 1} for ref in refs]}
        _, receipt = self.request('/reservation-moves', moves, key='noop')
        self.assertEqual(self.store.state['restaurant_revisions']['r'], 2)
        self.assertEqual(self.store.state['series'][series['series_id']]['revision'], 1)
        self.assertTrue(j.equal(self.request('/reservation-moves', moves, key='noop')[1], receipt))
        invalid = {'moves': [{'reference': refs[0], 'party_size': 3}, {'reference': refs[1], 'expected_revision': 9}]}
        self.fail('stale_revision', '/reservation-moves', invalid, key='failed')
        self.assertEqual(self.lookup(refs[0])['party_size'], 2)

    def test_legacy_fixture_adapters_preserve_original_timestamp_and_unknown_selector(self):
        # Two inherited developer methods edited the *current* native state to
        # resemble a legacy producer. Stage3's journal correctly rejects such
        # edits. These cases construct the documented schema1 producer instead.
        for historical in (False, True):
            value = fixture()
            if historical:
                value['restaurants'][0].update(reservation_duration_minutes=60,
                    opening_hours=[{'weekday': d, 'opens': '17:00', 'closes': '23:00'} for d in domain.WEEKDAYS])
            old = legacy.reset(value); old['tokens']['session'] = 'u'
            body = dict(self.body)
            if historical:
                body['starts_at_local'] = '1800-01-01T18:00'
            _, original, old = legacy.dispatch(old, 'POST', '/reservations', {},
                {'authorization': 'Bearer session', 'idempotency-key': 'one'}, body)
            record, receipt = old['reservations'][original['reference']], old['receipts'][0]
            if historical:
                for target in (record, receipt['response']):
                    target.update(starts_at='1800-01-01T18:00:00+00:53:28', ends_at='1800-01-01T19:00:00+00:53:28')
            else:
                record.pop('table_ids'); receipt['response'].pop('table_ids'); receipt.pop('producer_stage')
                receipt['body']['table_ids'] = {'previously': 'unknown'}
            saved = j.clone(receipt['response'])
            self.store.state = domain.import_state(legacy.snapshot(old))
            self.assertTrue(j.equal(self.request(body=receipt['body'])[1], saved))
            current = self.lookup(original['reference'])
            self.assertEqual(current['table_ids'], ['a'])
            self.assertEqual(self.history(original['reference']), [])
            if historical:
                self.assertEqual(current['starts_at'], '1800-01-01T17:06:32+00:00')
            self.store.state = domain.import_state(domain.snapshot(self.store.state))
            self.assertTrue(j.equal(self.request(body=receipt['body'])[1], saved))


if __name__ == '__main__':
    unittest.main()
