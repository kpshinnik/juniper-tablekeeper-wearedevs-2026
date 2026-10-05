"""Independent black-box tests; destructive calls restricted to synthetic local targets."""
import copy
import json
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlsplit
import httpx
import pytest


def pytest_addoption(parser):
    parser.addoption('--target', default='http://127.0.0.1:8080')
    parser.addoption('--case-log', default=None)


def pytest_configure(config):
    for mark in ['security: security or adversarial validation', 'load: concurrent or sustained traffic', 'stage(n): minimum stage']:
        config.addinivalue_line('markers', mark)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    target = item.config.getoption('--case-log')
    if target and (report.when == 'call' or report.failed or report.skipped):
        row = {'id': item.nodeid, 'phase': report.when, 'outcome': report.outcome,
               'duration_s': report.duration, 'timestamp': datetime.now(timezone.utc).isoformat(),
               'description': item.function.__doc__ or '', 'metrics': dict(report.user_properties)}
        if report.failed:
            row['failure'] = str(report.longrepr)
        with open(target, 'a', encoding='utf8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')


@pytest.fixture
def api(request):
    target = request.config.getoption('--target')
    if urlsplit(target).hostname not in {'localhost', '127.0.0.1', '::1', 'service', 'tablekeeper', 'tablekeeper-rehearsal-s1'}:
        pytest.fail('Destructive synthetic tests are restricted to local/container targets.')
    with httpx.Client(base_url=target, timeout=5, trust_env=False,
                      limits=httpx.Limits(max_connections=100, max_keepalive_connections=60)) as c:
        yield c


def fixture_data():
    date = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    hours = [{'weekday': day, 'opens': '00:00', 'closes': '23:59'}
             for day in ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')]
    restaurant = {'id': 'r_main', 'name': 'Juniper Dining', 'timezone': 'Europe/Berlin',
                  'slot_minutes': 30, 'reservation_duration_minutes': 60,
                  'cancellation_cutoff_minutes': 120, 'opening_hours': hours,
                  'tables': [{'id': f't_{i}', 'label': f'Table {i}', 'capacity': i * 2} for i in range(1, 7)],
                  'combinable': [['t_1', 't_2'], ['t_3', 't_4']], 'manager_user_ids': ['alice']}
    second = copy.deepcopy(restaurant)
    second.update(id='r_other', name='Juniper Garden')
    data = {'users': [{'id': name, 'email': f'{name}@example.test',
                       'password': f'{name}-correct-horse', 'display_name': name.title()}
                      for name in ('alice', 'bob')], 'restaurants': [restaurant, second], 'reservations': []}
    return data, date


@pytest.fixture
def world(api):
    data, date = fixture_data()
    assert api.post('/_test/reset', json=data, timeout=10).status_code == 204
    tokens = {}
    for user in data['users']:
        r = api.post('/auth/login', json={'email': user['email'], 'password': user['password']})
        assert r.status_code == 200, r.text
        tokens[user['id']] = r.json()['token']
    return SimpleNamespace(data=data, date=date, tokens=tokens,
                           body={'restaurant_id': 'r_main', 'table_id': 't_2',
                                 'starts_at_local': date + 'T18:00', 'party_size': 3})


def headers(world, user='alice', key=None):
    result = {'Authorization': 'Bearer ' + world.tokens[user]}
    if key is not None:
        result['Idempotency-Key'] = key
    return result


def book(api, world, *, body=None, key=None, user='alice'):
    return api.post('/reservations', json=world.body if body is None else body,
                    headers=headers(world, user, key or uuid.uuid4().hex))


def error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()['error']['code'] == code, response.text
    assert isinstance(response.json()['error']['message'], str)
    return response


def reservations(api, world, user='alice'):
    r = api.get('/reservations', headers=headers(world, user))
    assert r.status_code == 200, r.text
    return r.json()['reservations']
