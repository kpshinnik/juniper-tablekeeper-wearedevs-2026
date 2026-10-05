"""A huge pair need not be expanded when occupancy excludes it from the output."""
from decimal import Decimal
import json
import time

import httpx


def test_C001_blocked_pair_requires_only_compact_availability(record_property):
    """An occupied small member excludes its declared huge-capacity pair; eleven available large singles have compact exact capacities and finish within5s."""
    fixture = {
        'users': [{'id': 'guest', 'email': 'guest@pair.test',
                   'password': 'synthetic-pair-password', 'display_name': 'Guest'}],
        'restaurants': [{'id': 'pair', 'name': 'Pair Garden', 'timezone': 'UTC',
            'slot_minutes': 30, 'reservation_duration_minutes': 60,
            'cancellation_cutoff_minutes': 0,
            'opening_hours': [{'weekday': day, 'opens': '17:00', 'closes': '23:00'}
                              for day in 'mon tue wed thu fri sat sun'.split()],
            'tables': [{'id': 'a', 'label': 'Large single', 'capacity': '__HUGE__'},
                       {'id': 'b', 'label': 'Occupied single', 'capacity': 4}],
            'combinable': [['b', 'a']], 'manager_user_ids': ['guest']}],
        'reservations': [{'id': 'seed-'+str(i), 'reference': 'SEED'+str(i).zfill(6),
            'user_id': 'guest', 'restaurant_id': 'pair', 'table_id': 'b',
            'party_size': 1, 'starts_at_local': '2030-01-01T'+str(17+i)+':00'}
            for i in range(6)],
    }
    raw = json.dumps(fixture, separators=(',', ':')).replace('"__HUGE__"', '1e100000000')
    observed = {'reset_bytes': len(raw), 'exponent': 100000000,
                'expected_pair_output': 'none: b occupied for every opening interval'}
    with httpx.Client(base_url='http://tablekeeper:8080', trust_env=False, timeout=6) as client:
        restored = client.post('/_test/reset', content=raw,
                               headers={'Content-Type': 'application/json'}, timeout=10)
        assert restored.status_code == 204, restored.text[:500]
        before = client.get('/_test/export', timeout=10).content
        started = time.monotonic()
        response = None
        try:
            response = client.get('/availability', params={
                'restaurant_id': 'pair', 'date': '2030-01-01', 'party_size': '1'})
            observed.update(status=response.status_code, response_bytes=len(response.content))
        except httpx.HTTPError as error:
            observed['request_error'] = type(error).__name__
        observed['elapsed_s'] = time.monotonic()-started
        try:
            tick = time.monotonic()
            health = client.get('/health')
            observed.update(health_status=health.status_code, health_elapsed_s=time.monotonic()-tick)
        except httpx.HTTPError as error:
            observed['health_error'] = type(error).__name__
        record_property('observed', json.dumps(observed))
        assert response is not None, observed
        assert response.status_code == 200 and observed['elapsed_s'] <= 5, observed
        value = json.loads(response.content, parse_float=Decimal, parse_int=Decimal)
        slots = value['slots']
        assert len(slots) == 11
        for slot in slots:
            assert slot['available_table_ids'] == ['a']
            assert slot['available_options'] == [{'table_ids': ['a'], 'capacity': Decimal('1e100000000')}]
        assert len(response.content) < 10000, 'Only compact exact numbers belong in this response'
        assert observed['health_status'] == 200 and observed['health_elapsed_s'] <= 5
        assert client.get('/_test/export', timeout=10).content == before
