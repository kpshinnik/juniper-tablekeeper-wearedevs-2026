"""D417: bounded schema4 carrier collision investigation on actual HTTP.

No product modules are imported. Public inputs include carrier-shaped ignored
values; corruption cases edit the observed opaque wrapper independently and
recompute its checksum. Standard JSON touches only the ordinary outer envelope.
The compact huge values below never require client or service power expansion.
"""
import copy
import hashlib
import json

import pytest

from derived.test_stage4 import world4, require, setup, closure, current, series
from derived.test_stage1 import headers, assert_error


SHAPES = ['wrapper-object', 'number-objects', 'carrier-array', 'carrier-string',
          'nested-128', 'exact-compact-numbers']


def snapshot(c):
    # Unlike the general exact-number assertion helper, use an ordinary JSON
    # parser here. All private numbers remain inside the opaque payload string;
    # the outer format_version is the ordinary integer 1.
    response = c.get('/_test/export', timeout=10)
    assert response.status_code == 200
    value = json.loads(response.content)
    assert type(value['state']['payload']) is str
    return value


def metadata(shape, equivalent=False):
    carrier = {'storage_version': 4, 'value': {'cost': None},
               'wide_values': [{'path': ['cost'], 'terms': [100, -4]}]}
    objects = {'Number': {'sign': 1, 'digits': '100', 'exponent': 0},
               'IntegerSum': {'high': '1', 'gap': 9, 'low': '4', 'exponent': 0},
               'IntegerTotal': {'terms': [100, -4]}, '$number': [1, '1', 4],
               'path': ['receipts', 0, 'body', 'probe'], 'terms': [1, -1]}
    if shape == 'wrapper-object': value = carrier
    elif shape == 'number-objects': value = objects
    elif shape == 'carrier-array': value = [carrier, objects, None, True, False, 0, '0', [], {}]
    elif shape == 'carrier-string': value = json.dumps([carrier, objects]) + '\x00\n雪𝄞'
    elif shape == 'nested-128':
        value = [carrier, objects]
        for i in range(128): value = {'path': [i, value], 'terms': [None, 'IntegerTotal']}
    elif shape == 'exact-compact-numbers':
        return ('{"n":10e99999999,"tiny":100e-100000002,"adjacent":90071992547409930e-1,'
                '"zero":0,"carrier":{"terms":[10e99999999,-40e-1],"path":["value",0]}}'
                if equivalent else
                '{"n":1e100000000,"tiny":1e-100000000,"adjacent":9007199254740993,'
                '"zero":-0,"carrier":{"terms":[1e100000000,-4],"path":["value",0]}}')
    else: raise AssertionError(shape)
    return json.dumps(value, ensure_ascii=not equivalent, sort_keys=equivalent,
                      separators=(',', ':') if equivalent else None)


def raw_body(body, probe):
    return json.dumps(body, ensure_ascii=True)[:-1] + (',' if body else '') + '"probe":' + probe + '}'


def post(c, path, token, key, body, probe):
    return c.post(path, content=raw_body(body, probe).encode('utf-8'),
                  headers={**headers(token, key), 'Content-Type': 'application/json'})


def ordinary_transport(envelope):
    """The payload string stays opaque through ordinary JSON codec operations."""
    return json.loads(json.dumps(json.loads(json.dumps(envelope)), ensure_ascii=False))


def observations(record_property, value):
    record_property('observed', json.dumps(value, sort_keys=True))


@pytest.mark.parametrize('shape', SHAPES, ids=['D417-'+x for x in SHAPES])
def test_D417_user_carriers_full_write_lifetime(world4, shape, record_property):
    """Ignored carrier-shaped values retain exact retry identity across real repair, series amendment and ordinary envelope roundtrip."""
    c, tok = world4
    original, equivalent = metadata(shape), metadata(shape, True)
    receipts = []

    def write(path, who, key, body):
        response = require(post(c, path, tok[who], key, body, original))
        before = snapshot(c)
        assert require(post(c, path, tok[who], key, body, equivalent), 200) == response
        assert snapshot(c) == before
        receipts.append((path, who, key, body, response))
        return response

    b = write('/reservations', 'diner', 'booking-carrier',
              {'restaurant_id': 'r', 'table_id': 'a', 'starts_at_local': '2030-01-01T18:00', 'party_size': 2})
    agreement = require(c.post('/series', headers=headers(tok['diner'], 'adoption-control'),
                              json={'anchor_reference': b['reference'], 'count': 2, 'interval_weeks': 1}))
    p = write('/restaurants/r/replans', 'manager', 'preview-carrier', closure())
    assert p['unused_seats'] == 98 and p['moved_count'] == 1
    applied = write('/restaurants/r/replans/'+p['plan_id']+'/apply', 'manager', 'apply-carrier', {})
    assert applied['reservations'][0]['table_ids'] == ['b']
    now = series(c, tok, agreement['series_id'])
    amended = write('/series/'+agreement['series_id']+'/amend', 'diner', 'amend-carrier',
                    {'expected_revision': now['revision'], 'from_index': 0, 'local_time': '20:00'})
    assert all(o['reservation']['starts_at_local'].endswith('T20:00') for o in amended['occurrences'])

    exported = snapshot(c)
    transported = ordinary_transport(exported)
    assert transported == exported
    destination = setup(c)
    require(c.post('/_test/import', json=transported, timeout=10), 204)
    assert snapshot(c) == exported
    assert c.get('/reservations', headers=headers(destination['diner'])).status_code == 401
    conflicts = 0
    for path, who, key, body, receipt in receipts:
        before = snapshot(c)
        for raw in (original, equivalent):
            assert require(post(c, path, tok[who], key, body, raw), 200) == receipt
            assert snapshot(c) == before
        # Distinct boolean/numeric/object/array/string/null JSON values cannot
        # alias a successful object's, array's, or string's exact identity.
        for different in ('true', '1', '{"terms":[1]}', '[1]', '"1"', 'null'):
            assert_error(post(c, path, tok[who], key, body, different), 409, 'idempotency_key_reuse')
            assert snapshot(c) == before
            conflicts += 1
    actual = current(c, tok['diner'], b['reference'])
    assert actual['table_ids'] == ['b'] and actual['starts_at_local'] == '2030-01-01T20:00'
    assert receipts[0][-1]['table_ids'] == ['a'] and receipts[0][-1]['starts_at_local'].endswith('T18:00')
    assert len(c.get('/reservations', headers=headers(tok['diner'])).json()['reservations']) == 2
    observations(record_property, {'shape': shape, 'idempotent_paths': 4, 'first_uses': 4,
        'equivalent_initial_replays': 4, 'original_and_equivalent_post_import_replays': 8,
        'distinct_value_conflicts': conflicts, 'outer_ordinary_json_roundtrip': True,
        'immutable_original_receipts': True, 'current_assignment_and_time_preserved': True,
        'exact_snapshot_nonmutation': True, 'import': 204})


@pytest.mark.parametrize('original,different', [('true','1'), ('1','{"terms":[1]}'),
    ('{"terms":[1]}','1'), ('false','0')], ids=['D417-bool-number', 'D417-number-object',
    'D417-object-number', 'D417-false-zero'])
def test_D417_type_identity_survives_carrier_roundtrip(world4, original, different, record_property):
    """Boolean, numeric and cost-shaped object identities remain distinct after import and conflict without mutation."""
    c, tok = world4
    body = {'restaurant_id':'r','table_id':'a','starts_at_local':'2030-01-01T18:00','party_size':2}
    receipt = require(post(c, '/reservations', tok['diner'], 'type', body, original))
    before = snapshot(c)
    require(c.post('/_test/import', json=ordinary_transport(before), timeout=10), 204)
    assert snapshot(c) == before
    assert_error(post(c, '/reservations', tok['diner'], 'type', body, different), 409, 'idempotency_key_reuse')
    assert snapshot(c) == before
    equivalent = '1.0' if original == '1' else original
    assert require(post(c, '/reservations', tok['diner'], 'type', body, equivalent), 200) == receipt
    assert snapshot(c) == before
    observations(record_property, {'original_json': original, 'distinct_json': different,
        'import':204, 'conflict':409, 'original_replay':200, 'exact_nonmutation':True})


ATTACKS = ['duplicate-path', 'null-user-receipt-path', 'boolean-array-index',
           'negative-array-index', 'object-terms', 'boolean-terms', 'negative-total',
           'journal-inconsistent-cost', 'missing-cost-path']


def seal(envelope, wrapper):
    result = copy.deepcopy(envelope)
    payload = json.dumps(wrapper, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    result['state'] = {'payload': payload, 'sha256': hashlib.sha256(payload.encode('ascii')).hexdigest()}
    return result


@pytest.mark.parametrize('attack', ATTACKS, ids=['D417-'+x for x in ATTACKS])
def test_D417_forged_carrier_rejected_atomically(world4, attack, record_property):
    """Checksum-valid forged carrier paths or inconsistent cost terms reject422 and leave a distinct destination unchanged."""
    c, tok = world4
    body = {'restaurant_id':'r','table_id':'a','starts_at_local':'2030-01-01T18:00','party_size':2}
    raw = '{"storage_version":4,"value":null,"wide_values":[{"path":["value"],"terms":[98]}]}'
    receipt = require(post(c, '/reservations', tok['diner'], 'carrier-book', body, raw))
    p = require(c.post('/restaurants/r/replans', json=closure(), headers=headers(tok['manager'],'carrier-plan')))
    assert p['unused_seats'] == 98
    original = snapshot(c)
    wrapper = json.loads(original['state']['payload'])
    cost = next(row for row in wrapper['wide_values'] if row['path'] == ['plans',p['plan_id'],'response','unused_seats'])
    # Valid signed-term representation proves the adapter accepts equivalent
    # arithmetic before attempting to reject an actually inconsistent value.
    control = copy.deepcopy(wrapper)
    for row in control['wide_values']: row['terms'] = [100,-2]
    require(c.post('/_test/import',json=ordinary_transport(seal(original,control)),timeout=10),204)
    assert snapshot(c) == original

    broken = copy.deepcopy(wrapper)
    row = next(x for x in broken['wide_values'] if x['path'] == cost['path'])
    receipts = broken['value']['receipts']
    index = next(i for i,r in enumerate(receipts) if r['key']=='carrier-book')
    if attack == 'duplicate-path': broken['wide_values'].append(copy.deepcopy(row))
    elif attack == 'null-user-receipt-path': broken['wide_values'].append({'path':['receipts',index,'body','probe','value'],'terms':[98]})
    elif attack == 'boolean-array-index': broken['wide_values'].append({'path':['receipts',False,'body','probe','value'],'terms':[98]})
    elif attack == 'negative-array-index': broken['wide_values'].append({'path':['receipts',-1,'body','probe','value'],'terms':[98]})
    elif attack == 'object-terms': row['terms'] = [{'sign':1,'digits':'98','exponent':0}]
    elif attack == 'boolean-terms': row['terms'] = [True,97]
    elif attack == 'negative-total': row['terms'] = [-1]
    elif attack == 'journal-inconsistent-cost': row['terms'] = [100,-1]
    elif attack == 'missing-cost-path': broken['wide_values'].remove(row)
    else: raise AssertionError(attack)
    assert broken != wrapper and broken['value']['audit'] == wrapper['value']['audit']
    destination = setup(c)
    before = snapshot(c)
    refused = c.post('/_test/import', json=ordinary_transport(seal(original,broken)), timeout=10)
    assert_error(refused,422,'validation_failed')
    assert snapshot(c) == before
    require(c.post('/_test/import',json=ordinary_transport(original),timeout=10),204)
    assert snapshot(c) == original
    assert c.get('/reservations',headers=headers(destination['diner'])).status_code == 401
    assert require(post(c,'/reservations',tok['diner'],'carrier-book',body,raw),200) == receipt
    assert require(c.post('/restaurants/r/replans',json=closure(),headers=headers(tok['manager'],'carrier-plan')),200) == p
    require(c.post('/restaurants/r/replans/'+p['plan_id']+'/apply',json={},headers=headers(tok['manager'],'after-control')))
    assert current(c,tok['diner'],receipt['reference'])['table_ids'] == ['b']
    observations(record_property, {'attack':attack, 'equivalent_signed_cost_control':204,
        'corrupt_import':422, 'destination_nonmutation':True, 'original_roundtrip':204,
        'original_receipt_replays':2, 'new_plan_application':201, 'journal_unchanged':True})
