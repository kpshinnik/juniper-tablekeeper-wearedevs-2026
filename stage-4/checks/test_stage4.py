"""Builder checks from written Stage4 invariants; no independent oracle imports."""
import concurrent.futures
import random
import unittest
from unittest.mock import patch

from test_invariants import domain, j, server
import stage3


class SeatingAndAmendments(unittest.TestCase):
    def setUp(self):
        self.fixture = {
            'users': [dict(id='u', email='u@example.test', password='synthetic-pass', display_name='Diner'),
                      dict(id='m', email='m@example.test', password='synthetic-pass', display_name='Manager')],
            'restaurants': [dict(id='r', name='Synthetic', timezone='UTC', slot_minutes=30,
                reservation_duration_minutes=60, cancellation_cutoff_minutes=0, manager_user_ids=['m'],
                opening_hours=[dict(weekday=d, opens='16:00', closes='23:00') for d in domain.WEEKDAYS],
                tables=[dict(id=t, label=t.upper(), capacity=c) for t, c in [('a', 4), ('b', 4), ('c', 6)]])],
            'reservations': []}
        self.reset()

    def reset(self):
        self.store = server.Store()
        self.store.state = domain.reset(self.fixture)
        self.store.state['tokens'].update(u='u', m='m')

    def req(self, path, body=None, key='key', user='u', method='POST', query=None):
        status, raw, _ = self.store.request(method, path, query or {},
            {'authorization': 'Bearer ' + user, 'idempotency-key': key}, body or {})
        if isinstance(raw, server.PreparedBody):
            raw = b''.join(raw.blocks())
        return status, j.loads(raw) if raw else None

    def book(self, table='a', time='18:00', day='2030-01-01', key='book', party=2):
        return self.req('/reservations', dict(restaurant_id='r', table_id=table,
            starts_at_local=day + 'T' + time, party_size=party), key=key)[1]

    def preview(self, table='a', begin='2030-01-01T18:00:00Z', end='2030-01-01T19:00:00Z', key='preview'):
        return self.req('/restaurants/r/replans', {'table_id': table, 'from': begin, 'to': end}, key, 'm')[1]

    def apply(self, plan, key='apply'):
        return self.req('/restaurants/r/replans/' + plan['plan_id'] + '/apply', {}, key, 'm')

    def expect_error(self, code, action):
        before = j.dumps(domain.export_state(self.store.state))
        with self.assertRaises(domain.Fault) as error:
            action()
        self.assertEqual(error.exception.code, code)
        self.assertEqual(before, j.dumps(domain.export_state(self.store.state)))

    def series(self, count=3):
        anchor = self.book()
        agreement = self.req('/series', dict(anchor_reference=anchor['reference'], count=count, interval_weeks=1), 'series')[1]
        return anchor, agreement

    def amend(self, agreement, time='20:00', revision=1, from_index=0, key='amend'):
        return self.req('/series/' + agreement['series_id'] + '/amend',
            dict(expected_revision=revision, from_index=from_index, local_time=time), key)

    def test_exact_integer_cost_properties_and_compact_borrow(self):
        rng = random.Random(74)
        for _ in range(3000):
            terms = [rng.randrange(-10**40, 10**40) * 10**rng.randrange(40) for _ in range(6)]
            total = sum(terms)
            if total < 0:
                terms, total = [-x for x in terms], -total
            result = j.IntegerTotal(terms)
            self.assertEqual(j.loads(j.dumps(result)), j.Number.parse(total))
            other = rng.randrange(10**80)
            self.assertEqual(result < other, total < other)
        high = j.Number.parse('1e100000000')
        a, b = j.IntegerTotal([high, -4]), j.IntegerTotal([high, -3])
        self.assertLess(a, b)
        self.assertEqual(a.plus(j.IntegerTotal([4])), high)
        self.assertLess(len(a.segments()), 5)

    def test_preview_all_bookings_apply_and_original_receipts(self):
        a = self.book(); b = self.book('b', key='second')
        before = j.clone(self.store.state)
        plan = self.preview()
        self.assertEqual(plan['moved_count'], 1)
        self.assertEqual(plan['unused_seats'], 6)
        self.assertEqual([a['reference'] for a in plan['assignments']], sorted([a['reference'], b['reference']]))
        for name in ('reservations', 'histories', 'closures', 'restaurant_revisions'):
            self.assertTrue(j.equal(self.store.state[name], before[name]))
        status, applied = self.apply(plan)
        self.assertEqual(status, 201)
        self.assertEqual(applied['restaurant_revision'], 3)
        changed = self.store.state['reservations'][a['reference']]
        self.assertEqual(changed['table_ids'], ['c'])
        self.assertEqual(changed['accepted_terms'], before['reservations'][a['reference']]['accepted_terms'])
        entry = self.store.state['histories'][a['reference']][-1]
        self.assertEqual((entry['event'], entry['changes'][0]['field'], entry['plan_id']), ('reassigned', 'table_ids', plan['plan_id']))
        self.assertTrue(j.equal(self.book(), a))
        self.assertTrue(j.equal(self.apply(plan)[1], applied))
        self.expect_error('plan_already_applied', lambda: self.apply(plan, 'different'))
        self.assertTrue(j.equal(domain.import_state(domain.export_state(self.store.state)), self.store.state))

    def test_full_interval_fixed_conflict_and_proposed_closure(self):
        self.book(time='17:30'); self.book('b', time='17:00', key='fixed')
        plan = self.preview(begin='2030-01-01T18:00:00Z', end='2030-01-01T18:15:00Z')
        self.assertEqual(plan['assignments'][0]['table_ids'], ['c'])

    def test_empty_closure_half_open_and_fractional_instants(self):
        a = self.book(time='19:00')
        plan = self.preview()
        self.assertEqual(plan['assignments'], [])
        self.assertEqual(plan['unused_seats'], 0)
        self.apply(plan)
        self.assertEqual(self.store.state['restaurant_revisions']['r'], 2)
        self.assertEqual(self.store.state['reservations'][a['reference']]['revision'], 1)
        result = self.req('/availability', method='GET', query=dict(restaurant_id='r', date='2030-01-01', party_size='2', explain='true'))[1]
        slot = next(s for s in result['slots'] if s['starts_at_local'].endswith('18:00'))
        self.assertNotIn('a', slot['available_table_ids'])
        self.assertFalse(slot['explain'][0]['rules'][1]['holds'])
        self.expect_error('table_unavailable', lambda: self.book(key='closed'))
        other = self.preview(begin='2030-01-02T18:00:00.0000000001Z', end='2030-01-02T18:00:00.0000000002Z', key='fraction')
        self.assertEqual(other['assignments'], [])

    def test_infeasible_rollback_and_planning_limit(self):
        self.book(); self.book('b', key='b'); self.book('c', key='c')
        self.expect_error('no_feasible_plan', self.preview)
        self.fixture['restaurants'][0]['tables'] += [dict(id=str(i), label=str(i), capacity=4) for i in range(4)]
        self.reset()
        self.expect_error('planning_limit', self.preview)

    def test_exact_unused_seat_difference_selects_lower_capacity(self):
        self.fixture['restaurants'][0]['tables'][1]['capacity'] = j.Number.parse('9007199254740993')
        self.fixture['restaurants'][0]['tables'][2]['capacity'] = j.Number.parse('9007199254740992')
        self.reset(); self.book()
        plan = self.preview()
        self.assertEqual(plan['assignments'][0]['table_ids'], ['c'])
        self.assertEqual(plan['unused_seats'], j.Number.parse('9007199254740990'))

    def test_small_objective_delta_beside_huge_exponent_survives_receipt_and_import(self):
        high = j.Number.parse('1e100000000')
        self.fixture['restaurants'][0]['tables'] = [dict(id=t, label=t, capacity=c)
            for t, c in [('a', 6), ('b', high), ('c', 4), ('d', 3)]]
        self.reset()
        first = self.book(party=5)
        second = self.book(time='19:00', key='second')
        body = dict(table_id='a', **{'from': '2030-01-01T18:00:00Z', 'to': '2030-01-01T20:00:00Z'})
        headers = {'authorization': 'Bearer m', 'idempotency-key': 'exact'}
        status, plan, work = domain.dispatch(self.store.state, 'POST', '/restaurants/r/replans', {}, headers, body)
        self.assertEqual(status, 201)
        assigned = {a['reference']: a['table_ids'] for a in plan['assignments']}
        self.assertEqual(assigned, {first['reference']: ['b'], second['reference']: ['d']})
        self.assertEqual(plan['unused_seats'], j.IntegerTotal([high, -4]))
        # The endpoint's JSON representation is necessarily enormous. This local
        # check verifies preparation/portability compactly; independent HTTP QA
        # owns actual large response and uncapped-client resource measurements.
        wire = self.store.prepare(work, plan, False)
        self.assertIsInstance(wire, server.PreparedBody)
        self.assertGreater(wire.length, 99_999_999)
        self.assertLess(len(wire.parts), 100)
        restored = domain.import_state(domain.export_state(work))
        self.assertTrue(j.equal(restored, work))
        status, replay, change = domain.dispatch(restored, 'POST', '/restaurants/r/replans', {}, headers, body)
        self.assertEqual(status, 200)
        self.assertIsNone(change)
        self.assertTrue(j.equal(plan, replay))

    def test_original_policy_capacity_and_pair_rank(self):
        self.fixture['restaurants'][0]['tables'] = [dict(id=t, label=t, capacity=c) for t, c in [('a', 8), ('b', 3), ('c', 3)]]
        self.fixture['restaurants'][0]['combinable'] = [['c', 'b']]
        self.reset(); self.book(party=6)
        policy = dict(effective_from='2029-01-01', slot_minutes=30, reservation_duration_minutes=60,
            cancellation_cutoff_minutes=0, opening_hours=[], capacities={'a': 1, 'b': 1, 'c': 1})
        self.req('/restaurants/r/policies', policy, 'policy', 'm')
        plan = self.preview()
        self.assertEqual(plan['assignments'][0]['table_ids'], ['c', 'b'])
        self.assertEqual(plan['unused_seats'], 0)
        self.apply(plan)

    def test_stale_plan_and_concurrent_application(self):
        self.book(); plan = self.preview(); self.book('c', day='2030-01-02', key='later')
        self.expect_error('stale_plan', lambda: self.apply(plan))
        plan = self.preview(key='new')
        def apply(key):
            try: return self.apply(plan, key)[0]
            except domain.Fault as e: return e.code
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(apply, ['first', 'second']))
        self.assertEqual(set(results), {201, 'plan_already_applied'})

    def test_series_repair_preserves_flags_once_then_amends_current_tables(self):
        anchor, agreement = self.series()
        plan = self.preview(end='2030-01-20T19:00:00Z')
        self.apply(plan)
        current = self.req('/series/' + agreement['series_id'], method='GET')[1]
        self.assertEqual(current['revision'], 2)
        self.assertTrue(all(not o['exception'] for o in current['occurrences']))
        _, amended = self.amend(agreement, revision=2)
        self.assertEqual(amended['revision'], 3)
        self.assertTrue(all(o['reservation']['table_ids'] == ['b'] for o in amended['occurrences']))
        self.assertEqual(self.store.state['restaurant_revisions']['r'], 4)
        self.assertTrue(j.equal(self.amend(agreement, revision=2)[1], amended))

    def test_series_skips_permanent_exceptions_and_cancelled_members(self):
        anchor, agreement = self.series(4)
        refs = [o['reference'] for o in agreement['occurrences']]
        self.req('/reservations/' + refs[1], {'starts_at_local': '2030-01-09T18:00'}, method='PATCH')
        self.req('/reservations/' + refs[2] + '/cancel')
        _, result = self.amend(agreement, revision=3)
        self.assertEqual([o['reservation']['starts_at_local'] for o in result['occurrences']],
            ['2030-01-01T20:00', '2030-01-09T18:00', '2030-01-15T18:00', '2030-01-22T20:00'])
        self.assertEqual([o['exception'] for o in result['occurrences']], [False, True, False, False])
        self.assertEqual(result['revision'], 4)

    def test_series_noop_after_policy_change_and_empty_eligible(self):
        _, agreement = self.series()
        policy = dict(effective_from='2029-01-01', slot_minutes=30, reservation_duration_minutes=120,
            cancellation_cutoff_minutes=0, opening_hours=[], capacities={'a': 1, 'b': 1, 'c': 1})
        self.req('/restaurants/r/policies', policy, 'policy', 'm')
        before = self.store.state['restaurant_revisions']['r']
        _, result = self.amend(agreement, time='18:00')
        self.assertEqual(result['revision'], 1)
        self.assertEqual(self.store.state['restaurant_revisions']['r'], before)
        self.expect_error('outside_opening_hours', lambda: self.amend(agreement, key='real'))

    def test_series_collective_rollback_nonoccupancy_precedence_and_revision(self):
        _, agreement = self.series()
        self.book(time='20:00', key='conflict')
        self.expect_error('table_unavailable', lambda: self.amend(agreement))
        self.expect_error('stale_revision', lambda: self.amend(agreement, revision=2, time='23:00'))
        self.expect_error('outside_opening_hours', lambda: self.amend(agreement, time='23:00'))
        self.assertEqual(self.amend(agreement, time='21:00')[0], 201)

    def test_series_concurrent_expected_revision_and_empty_eligible(self):
        _, agreement = self.series()
        def amend(time):
            try: return self.amend(agreement, time=time, key=time)[0]
            except domain.Fault as error: return error.code
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(amend, ['20:00', '21:00']))
        self.assertEqual(set(results), {201, 'stale_revision'})
        for occurrence in agreement['occurrences']:
            self.req('/reservations/' + occurrence['reference'] + '/cancel')
        revision = self.store.state['series'][agreement['series_id']]['revision']
        counter = self.store.state['restaurant_revisions']['r']
        _, result = self.amend(agreement, revision=revision, key='empty')
        self.assertEqual(result['revision'], revision)
        self.assertEqual(self.store.state['restaurant_revisions']['r'], counter)

    def test_series_nonoccupancy_error_precedes_earlier_conflict(self):
        _, agreement = self.series()
        self.book(time='20:00', key='conflict')
        policy = dict(effective_from='2030-01-08', slot_minutes=30, reservation_duration_minutes=60,
            cancellation_cutoff_minutes=0, opening_hours=[], capacities={'a': 4, 'b': 4, 'c': 6})
        self.req('/restaurants/r/policies', policy, 'policy', 'm')
        self.expect_error('outside_opening_hours', lambda: self.amend(agreement))

    def test_series_from_index_validation_permissions_and_true_dst_gap(self):
        _, agreement = self.series()
        path = '/series/' + agreement['series_id'] + '/amend'
        valid = dict(expected_revision=1, from_index=0, local_time='20:00')
        for field, value in [('expected_revision', True), ('from_index', -1), ('from_index', 3),
                             ('from_index', True), ('local_time', '2:00'), ('local_time', '24:00')]:
            self.expect_error('validation_failed', lambda: self.req(path, dict(valid, **{field: value})))
        self.expect_error('not_found', lambda: self.req(path, valid, user='m'))
        rest = self.fixture['restaurants'][0]
        rest.update(timezone='Europe/Berlin', opening_hours=[dict(weekday=d, opens='00:00', closes='08:00') for d in domain.WEEKDAYS])
        self.reset()
        with patch.object(domain, 'now', return_value='2026-01-01T00:00:00+00:00'):
            anchor = self.book(time='01:00', day='2026-03-22')
            agreement = self.req('/series', dict(anchor_reference=anchor['reference'], count=2, interval_weeks=1), 'adopt')[1]
            self.expect_error('invalid_local_time', lambda: self.amend(agreement, time='02:30'))

    def test_previous_stage_migration_keeps_series_and_ignored_receipt_fields(self):
        base = stage3.reset(self.fixture); base['tokens'].update(u='u', m='m')
        body = dict(restaurant_id='r', table_id='a', starts_at_local='2030-01-01T18:00', party_size=2, from_index=False)
        headers = {'authorization': 'Bearer u', 'idempotency-key': 'old'}
        _, original, base = stage3.dispatch(base, 'POST', '/reservations', {}, headers, body)
        _, agreement, base = stage3.dispatch(base, 'POST', '/series', {}, headers,
            dict(anchor_reference=original['reference'], count=3, interval_weeks=1))
        self.store.state = domain.import_state(stage3.snapshot(base))
        self.assertTrue(j.equal(self.req('/reservations', body, 'old')[1], original))
        self.amend(agreement)
        self.assertTrue(j.equal(domain.import_state(domain.export_state(self.store.state)), self.store.state))

    def test_snapshot_semantic_plan_closure_and_history_corruption(self):
        a = self.book(); plan = self.preview(); self.apply(plan)
        original = self.store.state
        self.assertTrue(j.equal(domain.import_state(domain.export_state(original)), original))
        mutators = [lambda s: s['closures'].clear(),
                    lambda s: s['plans'][plan['plan_id']].update(applied=False),
                    lambda s: s['plans'][plan['plan_id']]['response'].update(unused_seats=123),
                    lambda s: s['histories'][a['reference']][-1].update(plan_id='invented')]
        for mutate in mutators:
            altered = j.clone(original); mutate(altered)
            self.expect_error('validation_failed', lambda: self.req('/_test/import', domain.export_state(altered)))

    def test_preparation_failures_on_three_new_paths_leave_no_publication(self):
        _, agreement = self.series()
        plan = self.preview()
        operations = [lambda: self.preview(key='fault-preview'), lambda: self.apply(plan), lambda: self.amend(agreement)]
        for operation in operations:
            before = j.dumps(domain.export_state(self.store.state))
            with patch.object(self.store, 'prepare', side_effect=ValueError('synthetic publication fault')):
                with self.assertRaises(ValueError): operation()
            self.assertEqual(before, j.dumps(domain.export_state(self.store.state)))


if __name__ == '__main__':
    unittest.main()
