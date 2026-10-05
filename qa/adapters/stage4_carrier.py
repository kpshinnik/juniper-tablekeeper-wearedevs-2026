"""Independent schema4 carrier selector, limited to small corruption fixtures.

No product import. Native wide paths are restored as exact Python integers and
repacked at those same paths. This does not act as a planner or JSON oracle.
Unchanged raw exports and this representation's roundtrip are separate controls.
"""
import copy
import hashlib
import json


def parent(value, path):
    for key in path[:-1]:
        value = value[key]
    return value, path[-1]


def payload(envelope):
    wrapper = json.loads(envelope['state']['payload'])
    assert wrapper['storage_version'] == 4
    value = copy.deepcopy(wrapper['value'])
    for row in wrapper['wide_values']:
        assert all(type(n) is int for n in row['terms']), 'Small fixture adapter only'
        target, key = parent(value, row['path'])
        assert target[key] is None
        target[key] = sum(row['terms'])
    assert value['schema'] == 4
    return value


def seal(envelope, decoded):
    wrapper = json.loads(envelope['state']['payload'])
    value = copy.deepcopy(decoded)
    wide = []
    for row in wrapper['wide_values']:
        try:
            target, key = parent(value, row['path'])
            number = target[key]
        except (KeyError, IndexError):
            continue
        assert type(number) is int, 'Small fixture adapter only'
        wide.append({'path': row['path'], 'terms': [number]})
        target[key] = None
    wrapper = {'storage_version': 4, 'value': value, 'wide_values': wide}
    encoded = json.dumps(wrapper, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    envelope['state'] = {'payload': encoded, 'sha256': hashlib.sha256(encoded.encode('ascii')).hexdigest()}


def exported(c):
    result = c.get('/_test/export', timeout=10)
    assert result.status_code == 200
    envelope = result.json()
    return envelope, payload(envelope)
