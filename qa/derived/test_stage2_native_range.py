"""D219: real browser entry of an API-valid integer beyond finite double range.

Both fill and ordinary sequential key input are observed. No DOM value setter,
type mutation, bypass of form validation or manufactured server response is used.
"""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from derived.test_stage1 import headers
from derived.test_stage2_browser import browser_world, fixture, login, search, DAY

PARTY = '1'+'0'*400


def exact(raw):
    return json.loads(raw, parse_int=Decimal, parse_float=Decimal)


def input_state(control):
    return control.evaluate('''e=>({tag:e.tagName,type:e.type,value:e.value,
        valueAsNumber:String(e.valueAsNumber),validationMessage:e.validationMessage,
        validity:{valid:e.validity.valid,badInput:e.validity.badInput,
        rangeOverflow:e.validity.rangeOverflow,rangeUnderflow:e.validity.rangeUnderflow,
        stepMismatch:e.validity.stepMismatch,valueMissing:e.validity.valueMissing},
        min:e.getAttribute('min'),max:e.getAttribute('max'),pattern:e.getAttribute('pattern'),
        inputmode:e.getAttribute('inputmode'),outerHTML:e.outerHTML})''')


def enter_and_observe(page, control, out, evidence):
    # A small-number control verifies the automation mechanism and active focus.
    control.fill('1'); evidence['small_fill_control'] = input_state(control)
    assert control.input_value() == '1'
    try:
        control.fill(PARTY)
        evidence['fill_exception'] = None
    except Exception as exc:
        evidence['fill_exception'] = {'type': type(exc).__name__, 'message': str(exc)}
    evidence['after_fill'] = input_state(control)
    page.screenshot(path=str(out/'after-fill.png'), full_page=True)
    control.click(); control.press('ControlOrMeta+A'); control.press('Backspace')
    control.press_sequentially('2')
    evidence['small_keyboard_control'] = input_state(control)
    assert control.input_value() == '2'
    control.press('ControlOrMeta+A'); control.press('Backspace')
    tick = time.monotonic()
    control.press_sequentially(PARTY)
    evidence['keyboard_entry_s'] = time.monotonic()-tick
    evidence['after_keyboard'] = input_state(control)
    page.screenshot(path=str(out/'after-keyboard.png'), full_page=True)


@pytest.mark.parametrize('entry', ['search', 'booking'], ids=['D219-search', 'D219-booking'])
def test_D219_exact_401_digit_party_native_input_and_retry(browser_world, entry, record_property):
    """API-valid1e400 must remain a401-digit decimal in real search/booking controls, query and numeric POST, then survive real201-loss retry exactly once."""
    c, page, errors, out = browser_world
    tick = time.monotonic()
    observation = {'id': 'D219-'+entry, 'product_sha': os.environ.get('QA_PRODUCT_SHA'),
        'test_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'intended_decimal': PARTY, 'decimal_digits': len(PARTY), 'entry_field': entry,
        'expected': 'Exact input/query/POST and unchanged real201-loss retry for finite API-valid party',
        'mechanism': 'fill plus sequential ordinary keyboard input; DOM inspected read-only',
        'browser_version': page.context.browser.version, 'api_control': {}, 'input': {},
        'browser_requests': [], 'post_attempts': [], 'status': 'RUNNING'}
    def write_evidence():
        observation['duration_s'] = time.monotonic()-tick
        observation['page_errors'] = errors
        observation['visible_text'] = page.locator('body').inner_text()
        (out/'observed.json').write_text(json.dumps(observation, indent=2, ensure_ascii=True))
        record_property('observed', json.dumps(observation, ensure_ascii=True))
    try:
        fx = fixture(); r = fx['restaurants'][0]
        r['tables'] = [{'id': 'a', 'label': 'Window seat', 'capacity': 'EXACT_CAPACITY'}]
        r['combinable'] = []; r['opening_hours'] = [{'weekday': 'tue', 'opens': '18:00', 'closes': '19:00'}]
        raw_fixture = json.dumps(fx).replace('"EXACT_CAPACITY"', '1e400')
        (out/'synthetic-fixture.json').write_text(raw_fixture)
        assert c.post('/_test/reset', content=raw_fixture, headers={'Content-Type': 'application/json'}, timeout=10).status_code == 204
        auth = c.post('/auth/login', json={'email': 'u@browser.test', 'password': 'synthetic-password'})
        assert auth.status_code == 200; token = auth.json()['token']
        at = time.monotonic()
        availability = c.get('/availability', params={'restaurant_id': 'r', 'date': DAY, 'party_size': PARTY})
        observation['api_control']['availability_s'] = time.monotonic()-at
        observation['api_control']['availability_status'] = availability.status_code
        observation['api_control']['availability_bytes'] = len(availability.content)
        assert availability.status_code == 200
        slots = exact(availability.content)['slots']; assert len(slots) == 1
        assert slots[0]['available_table_ids'] == ['a']
        assert slots[0]['available_options'][0]['capacity'] == Decimal(PARTY)
        raw_body = '{"restaurant_id":"r","table_id":"a","starts_at_local":"'+DAY+'T18:00","party_size":'+PARTY+'}'
        at = time.monotonic()
        created = c.post('/reservations', content=raw_body, headers=headers(token, 'api-control'))
        observation['api_control'].update(create_status=created.status_code, create_s=time.monotonic()-at,
                                         raw_body=raw_body, response_text=created.text)
        assert created.status_code == 201 and exact(created.content)['party_size'] == Decimal(PARTY)
        replay = c.post('/reservations', content=raw_body, headers=headers(token, 'api-control'))
        assert replay.status_code == 200 and exact(replay.content) == exact(created.content)
        observation['api_control'].update(replay_status=200, exact_party=True, original_retry=True)
        # Reset the successful control so the actual diner can book this one slot.
        assert c.post('/_test/reset', content=raw_fixture, headers={'Content-Type': 'application/json'}, timeout=10).status_code == 204
        auth = c.post('/auth/login', json={'email': 'u@browser.test', 'password': 'synthetic-password'})
        assert auth.status_code == 200; token = auth.json()['token']
        page.set_viewport_size({'width': 375, 'height': 900})
        def capture(request):
            path = urlsplit(request.url).path
            if path in ('/availability', '/reservations'):
                observation['browser_requests'].append({'method': request.method, 'url': request.url,
                    'raw_body': request.post_data, 'key': request.headers.get('idempotency-key')})
        page.on('request', capture)
        def lose_real_response(route):
            if route.request.method != 'POST': route.fallback(); return
            response = route.fetch()
            attempt = {'raw_body': route.request.post_data, 'key': route.request.headers.get('idempotency-key'),
                       'status': response.status, 'response_text': response.text()}
            observation['post_attempts'].append(attempt)
            if len(observation['post_attempts']) == 1 and response.status == 201:
                attempt['deliberately_lost'] = True
                route.abort('failed')
            else:
                route.fulfill(response=response)
        page.route('**/reservations', lose_real_response)
        login(page)
        if entry == 'search':
            page.get_by_test_id('restaurant-select').select_option('r')
            page.get_by_test_id('date-input').fill(DAY)
            control = page.get_by_test_id('party-size-input')
        else:
            search(page, '2')
            cell = page.get_by_test_id('slot-a-18:00'); expect(cell).to_have_attribute('data-available', 'true'); cell.click()
            control = page.get_by_test_id('booking-party-size')
        enter_and_observe(page, control, out, observation['input'])
        before_submit = len(observation['browser_requests'])
        page.get_by_test_id('search-button' if entry == 'search' else 'booking-submit').click()
        page.wait_for_timeout(250)
        observation['after_submit_input'] = input_state(control)
        observation['requests_after_submit'] = observation['browser_requests'][before_submit:]
        page.screenshot(path=str(out/'after-submit.png'), full_page=True)
        assert observation['input']['after_keyboard']['value'] == PARTY, (
            'Manual-like keyboard entry did not retain exact API-valid integer', observation['input']['after_keyboard'])
        if entry == 'search':
            queries = [parse_qs(urlsplit(x['url']).query) for x in observation['requests_after_submit'] if urlsplit(x['url']).path == '/availability']
            assert queries and queries[0]['party_size'] == [PARTY]
            cell = page.get_by_test_id('slot-a-18:00'); expect(cell).to_have_attribute('data-available', 'true'); cell.click()
            expect(page.get_by_test_id('booking-party-size')).to_have_value(PARTY)
            observation['booking_prefill'] = input_state(page.get_by_test_id('booking-party-size'))
            page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
        expect(page.get_by_test_id('booking-error')).to_have_count(0)
        expect(page.get_by_test_id('confirmation-reference')).to_have_count(0)
        calls = observation['post_attempts']; assert len(calls) == 1 and calls[0]['status'] == 201
        assert exact(calls[0]['raw_body'])['party_size'] == Decimal(PARTY)
        original = exact(calls[0]['response_text'])
        expect(page.get_by_test_id('booking-party-size')).to_have_value(PARTY)
        page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('confirmation-reference')).to_have_text(original['reference'])
        expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
        assert len(calls) == 2 and [x['status'] for x in calls] == [201, 200]
        assert calls[0]['key'] and calls[0]['key'] == calls[1]['key'] and calls[0]['raw_body'] == calls[1]['raw_body']
        assert exact(calls[1]['response_text']) == original
        records = exact(c.get('/reservations', headers=headers(token)).content)['reservations']
        assert len(records) == 1 and records[0]['party_size'] == Decimal(PARTY)
        assert not errors
        observation['status'] = 'PASS'
    except BaseException as exc:
        observation['status'] = 'FAIL' if isinstance(exc, AssertionError) else 'ERROR'
        observation['exception'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        write_evidence()
