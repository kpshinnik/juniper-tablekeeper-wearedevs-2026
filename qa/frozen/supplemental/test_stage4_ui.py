"""Stage4 UI must display applied assignments while immutable retries survive.

Two additional browser cases, not a claim of a required new manager screen.
The runner uses the disposable service's network namespace so a real localhost
origin provides Web Crypto without weakening a user's browser security.
"""
import json
from pathlib import Path
import time

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright


BASE = 'http://127.0.0.1:8080'
DAY = '2030-01-01'


@pytest.fixture
def api():
    with httpx.Client(base_url=BASE, trust_env=False, timeout=6) as c:
        yield c


@pytest.fixture
def browser_page(request):
    out = Path('/reports/stage4-ui') / request.node.name
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1360, 'height': 900}, record_video_dir=str(out/'video'))
        context.set_default_timeout(8000)
        page = context.new_page()
        errors, creates = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def record_create(route):
            r = route.request
            if r.method == 'POST':
                creates.append({'method': r.method, 'key': r.headers.get('idempotency-key'), 'body': r.post_data})
            route.continue_()

        page.route('**/reservations', record_create)
        yield page, creates, errors, out
        context.close()
        browser.close()


def request(c, timings, method, path, **kwargs):
    start = time.monotonic()
    r = c.request(method, path, **kwargs)
    elapsed = time.monotonic()-start
    timings.append({'method': method, 'path': path, 'status': r.status_code, 'elapsed_s': elapsed})
    assert elapsed <= (10 if path == '/_test/reset' else 5)
    return r


def seed(c, timings, pair=False):
    fx = {'users': [{'id': name, 'email': name+'@ui4.test', 'password': 'synthetic-ui-password',
                     'display_name': name.title()} for name in ('guest', 'other', 'manager')],
          'reservations': [],
          'restaurants': [{'id': 'dining', 'name': 'Juniper UI Audit', 'timezone': 'UTC',
             'manager_user_ids': ['manager'], 'slot_minutes': 60, 'reservation_duration_minutes': 60,
             'cancellation_cutoff_minutes': 0,
             'opening_hours': [{'weekday': w, 'opens': '18:00', 'closes': '22:00'}
                               for w in ('mon','tue','wed','thu','fri','sat','sun')],
             'tables': [{'id': 'x', 'label': 'Bay window', 'capacity': 2 if pair else 4},
                        {'id': 'y', 'label': 'Garden nook', 'capacity': 2 if pair else 4},
                        {'id': 'z', 'label': 'Courtyard table', 'capacity': 4 if pair else 2}],
             'combinable': [['y','x']] if pair else []}]}
    assert request(c, timings, 'POST', '/_test/reset', json=fx).status_code == 204
    tokens = {}
    for name in ('guest','other','manager'):
        r = request(c, timings, 'POST', '/auth/login', json={'email': name+'@ui4.test', 'password':'synthetic-ui-password'})
        assert r.status_code == 200
        tokens[name] = r.json()['token']
    return tokens


def auth(token, key=None):
    return {'Authorization': 'Bearer '+token, **({'Idempotency-Key': key} if key else {})}


def login_and_book(page, slot, creates, out):
    page.goto(BASE+'/login')
    page.get_by_test_id('login-email').fill('guest@ui4.test')
    page.get_by_test_id('login-password').fill('synthetic-ui-password')
    page.get_by_test_id('login-submit').click()
    expect(page.get_by_test_id('current-user')).to_contain_text('Guest')
    page.get_by_test_id('date-input').fill(DAY)
    page.get_by_test_id('party-size-input').fill('4')
    page.get_by_test_id('search-button').click()
    expect(page.get_by_test_id('slot-'+slot+'-18:00')).to_have_attribute('data-available','true')
    page.get_by_test_id('slot-'+slot+'-18:00').click()
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
    reference = page.get_by_test_id('confirmation-reference').inner_text()
    assert len(creates) == 1 and creates[0]['key'] and creates[0]['body']
    page.screenshot(path=str(out/'before-plan.png'),full_page=True)
    return reference


def apply(c, timings, token):
    preview = request(c,timings,'POST','/restaurants/dining/replans',
                      headers=auth(token,'preview'),json={'table_id':'x','from':DAY+'T18:00:00Z','to':DAY+'T19:00:00Z'})
    assert preview.status_code == 201
    plan = preview.json()
    applied = request(c,timings,'POST','/restaurants/dining/replans/'+plan['plan_id']+'/apply',
                      headers=auth(token,'apply'),json={})
    assert applied.status_code == 201
    return plan, applied.json()


def check_retry_lookup_grid(c, timings, page, creates, errors, out, token, ref, label, table, pair=False):
    # Replay retains the exact first POST/key, but the current UI must reflect
    # the manager's already-applied assignment rather than a stale receipt.
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_have_text(ref)
    expect(page.get_by_test_id('confirmation-tables')).to_have_text(label)
    assert len(creates) == 2 and creates[0] == creates[1]
    current = request(c,timings,'GET','/reservations/'+ref,headers=auth(token))
    assert current.status_code == 200 and current.json()['table_ids'] == [table]
    replay = request(c,timings,'POST','/reservations',headers={**auth(token,creates[0]['key']),
                      'Content-Type':'application/json'},content=creates[0]['body'])
    assert replay.status_code == 200 and replay.json()['reference'] == ref
    assert replay.json()['table_ids'] == (['y','x'] if pair else ['x'])
    page.screenshot(path=str(out/'confirmation-after-plan.png'),full_page=True)
    page.goto(BASE+'/lookup?reference='+ref)
    page.get_by_test_id('lookup-submit').click()
    expect(page.get_by_test_id('reservation-tables')).to_have_text(label)
    expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
    width = page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
    assert width['document'] <= width['viewport']
    page.screenshot(path=str(out/'lookup-after-plan.png'),full_page=True)
    page.goto(BASE)
    page.get_by_test_id('date-input').fill(DAY)
    page.get_by_test_id('party-size-input').fill('2')
    page.get_by_test_id('search-button').click()
    expect(page.get_by_test_id('slot-x-18:00')).to_have_attribute('data-available','false')
    expect(page.get_by_test_id('slot-x-19:00')).to_have_attribute('data-available','true')
    if pair:
        expect(page.get_by_test_id('slot-y+x-18:00')).to_have_count(0)
    assert not errors
    return {'reference':ref,'current_table_ids':current.json()['table_ids'],
            'original_replay_table_ids':replay.json()['table_ids'],'unchanged_retry':creates[0]==creates[1],
            'viewport':width,'browser_errors':errors,'request_timings':timings}


def test_U401_global_repair_updates_confirmation_lookup_and_availability(api,browser_page,record_property):
    """The global two-move repair updates actual desktop UI and preserves the original retry key/body/response."""
    c=api;page,creates,errors,out=browser_page;timings=[];tokens=seed(c,timings)
    other=request(c,timings,'POST','/reservations',headers=auth(tokens['other'],'other'),
                  json={'restaurant_id':'dining','table_id':'y','starts_at_local':DAY+'T18:00','party_size':2})
    assert other.status_code == 201
    ref=login_and_book(page,'x',creates,out)
    plan,result=apply(c,timings,tokens['manager'])
    assert plan['moved_count'] == 2 and plan['unused_seats'] == 0
    assert {r['reference']:r['table_ids'] for r in result['reservations']} == {ref:['y'],other.json()['reference']:['z']}
    values=check_retry_lookup_grid(c,timings,page,creates,errors,out,tokens['guest'],ref,'Garden nook','y')
    record_property('observed',json.dumps({'plan':plan,**values}))


def test_U402_pair_reassignment_is_current_on_375px_with_immutable_retry(api,browser_page,record_property):
    """A declared pair moves to a single table; 375px UI shows it while the pair's original receipt remains replayable."""
    c=api;page,creates,errors,out=browser_page;timings=[];tokens=seed(c,timings,pair=True)
    page.set_viewport_size({'width':375,'height':812})
    ref=login_and_book(page,'y+x',creates,out)
    plan,result=apply(c,timings,tokens['manager'])
    assert plan['moved_count'] == 1 and plan['unused_seats'] == 0
    assert result['reservations'][0]['table_ids'] == ['z']
    values=check_retry_lookup_grid(c,timings,page,creates,errors,out,tokens['guest'],ref,'Courtyard table','z',pair=True)
    assert values['viewport']['viewport'] == 375
    record_property('observed',json.dumps({'plan':plan,**values}))
