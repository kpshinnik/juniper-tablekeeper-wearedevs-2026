"""V-S2-002: actual keyboard entry, exact transport and lost-response lifetime."""
import datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers')
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server

PARTY = '1' + '0' * 400
OUT = ROOT / 'checks/evidence' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-numeric-entry')
OUT.mkdir(parents=True, exist_ok=False)
service = server.Server(('127.0.0.1', 0), server.Handler)
thread = threading.Thread(target=service.serve_forever, daemon=True)
thread.start()
BASE = 'http://127.0.0.1:' + str(service.server_address[1])
rows = []


def exact(raw):
    return json.loads(raw, parse_int=Decimal, parse_float=Decimal)


def http(path, body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read()
        return response.status, exact(raw) if raw else None


def check(browser, entry):
    folder = OUT / entry
    folder.mkdir()
    fixture = {'users': [{'id': 'u', 'email': 'u@browser.test', 'password': 'synthetic-password', 'display_name': 'Numeric diner'}],
        'restaurants': [{'id': 'r', 'name': 'Numeric garden', 'timezone': 'UTC', 'slot_minutes': 30,
            'reservation_duration_minutes': 60, 'cancellation_cutoff_minutes': 0,
            'opening_hours': [{'weekday': 'tue', 'opens': '18:00', 'closes': '19:00'}],
            'tables': [{'id': 'a', 'label': 'Window seat', 'capacity': int(PARTY)}], 'combinable': []}], 'reservations': []}
    assert http('/_test/reset', fixture)[0] == 204
    token = http('/auth/login', {'email': 'u@browser.test', 'password': 'synthetic-password'})[1]['token']
    context = browser.new_context(viewport={'width': 375, 'height': 900})
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    observation = {'entry': entry, 'requests': [], 'posts': [], 'inputs': [], 'geometry': [], 'page_errors': []}
    page.on('pageerror', lambda error: observation['page_errors'].append(str(error)))
    page.on('request', lambda req: observation['requests'].append({'method': req.method, 'url': req.url, 'body': req.post_data}) if urlsplit(req.url).path in ['/availability', '/reservations'] else None)

    def intercept(route):
        if route.request.method != 'POST':
            route.continue_()
            return
        response = route.fetch()
        observation['posts'].append({'status': response.status, 'body': route.request.post_data,
            'key': route.request.headers.get('idempotency-key'), 'response': response.text()})
        if len(observation['posts']) == 1 and response.status == 201:
            route.abort('failed')
        else:
            route.fulfill(response=response)

    def geometry(state):
        observed = page.evaluate('() => ({viewport:innerWidth, document:document.documentElement.scrollWidth})')
        observation['geometry'].append({'state': state, **observed})
        page.screenshot(path=str(folder / (state + '.png')), full_page=True)
        assert observed['document'] <= observed['viewport'], observed

    def capture(control, state):
        value = control.evaluate('e => ({value:e.value,type:e.type,badInput:e.validity.badInput,number:String(e.valueAsNumber),label:e.labels[0]?.textContent,inputmode:e.inputMode})')
        observation['inputs'].append({'state': state, **value})
        return value

    try:
        page.route('**/reservations', intercept)
        page.goto(BASE + '/login')
        page.get_by_test_id('login-email').fill('u@browser.test')
        page.get_by_test_id('login-password').fill('synthetic-password')
        page.get_by_test_id('login-submit').click()
        expect(page.get_by_test_id('current-user')).to_have_text('Numeric diner')
        page.get_by_test_id('restaurant-select').select_option('r')
        page.get_by_test_id('date-input').fill('2030-01-01')
        if entry == 'booking':
            page.get_by_test_id('party-size-input').fill('2')
            page.get_by_test_id('search-button').click()
            page.get_by_test_id('slot-a-18:00').click()
        control = page.get_by_test_id('party-size-input' if entry == 'search' else 'booking-party-size')
        submit = page.get_by_test_id('search-button' if entry == 'search' else 'booking-submit')
        control.fill('1')
        expect(control).to_have_value('1')
        control.fill(PARTY)
        capture(control, 'filled-401-digits')
        control.press('ControlOrMeta+A')
        control.press('Backspace')
        control.press_sequentially('2')
        expect(control).to_have_value('2')
        control.press('ControlOrMeta+A')
        control.press('Backspace')
        control.press_sequentially(PARTY)
        observed = capture(control, 'typed-401-digits')
        before = len(observation['requests'])
        submit.click()
        page.wait_for_timeout(150)
        observation['requests_after_submit'] = observation['requests'][before:]
        page.screenshot(path=str(folder / 'after-submit.png'), full_page=True)
        assert observed['value'] == PARTY, observed
        assert observation['inputs'][0]['value'] == PARTY
        if entry == 'search':
            expect(page.get_by_test_id('slot-a-18:00')).to_have_attribute('data-available', 'true')
            queries = [parse_qs(urlsplit(req['url']).query) for req in observation['requests_after_submit'] if urlsplit(req['url']).path == '/availability']
            assert queries[0]['party_size'] == [PARTY]
            geometry('search')
            page.get_by_test_id('slot-a-18:00').click()
            expect(page.get_by_test_id('booking-party-size')).to_have_value(PARTY)
            page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
        expect(page.get_by_test_id('booking-error')).to_have_count(0)
        expect(page.get_by_test_id('confirmation')).to_have_count(0)
        expect(page.get_by_test_id('booking-party-size')).to_have_value(PARTY)
        geometry('uncertain')
        posts = observation['posts']
        assert len(posts) == 1 and posts[0]['status'] == 201
        assert exact(posts[0]['body'])['party_size'] == Decimal(PARTY)
        receipt = exact(posts[0]['response'])
        page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('confirmation-reference')).to_have_text(receipt['reference'])
        expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
        expect(page.get_by_test_id('booking-error')).to_have_count(0)
        assert [p['status'] for p in posts] == [201, 200]
        assert posts[0]['key'] == posts[1]['key'] and posts[0]['body'] == posts[1]['body']
        assert exact(posts[1]['response']) == receipt
        geometry('confirmed')
        records = http('/reservations', token=token)[1]['reservations']
        assert len(records) == 1 and records[0]['party_size'] == Decimal(PARTY)
        page.goto(BASE + '/lookup?reference=' + receipt['reference'])
        expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
        geometry('lookup')
        page.get_by_test_id('reservation-cancel-button').click()
        expect(page.get_by_test_id('reservation-status')).to_have_text('cancelled')
        geometry('cancelled')
        page.goto(BASE + '/')
        page.get_by_test_id('restaurant-select').select_option('r')
        page.get_by_test_id('date-input').fill('2030-01-01')
        # Retain small-number validity and reject invalid integer text without requests.
        for invalid in ['', '0', '-1', '1.5', '1e400', '+2', 'two']:
            before = len(observation['requests'])
            page.get_by_test_id('party-size-input').fill(invalid)
            page.get_by_test_id('search-button').click()
            expect(page.get_by_test_id('search-error')).to_contain_text('whole number')
            assert len(observation['requests']) == before
        page.get_by_test_id('party-size-input').fill('0002')
        page.get_by_test_id('search-button').click()
        page.get_by_test_id('slot-a-18:00').click()
        expect(page.get_by_test_id('booking-party-size')).to_have_value('2')
        for invalid in ['', '0', '-1', '1.5', '1e400', '+2', 'two']:
            before = len(posts)
            page.get_by_test_id('booking-party-size').fill(invalid)
            page.get_by_test_id('booking-submit').click()
            expect(page.get_by_test_id('booking-error')).to_contain_text('whole number')
            assert len(posts) == before
        assert not observation['page_errors'], observation['page_errors']
    finally:
        (folder / 'observed.json').write_text(json.dumps(observation, indent=2) + '\n')
        context.tracing.stop(path=str(folder / 'trace.zip'))
        context.close()


try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for entry in ['search', 'booking']:
            started = time.monotonic()
            row = {'id': 'V-S2-002-' + entry, 'description': '401-digit fill/ordinary keys, exact HTTP, real201 abort, unchanged retry, lookup/cancel and invalid/small inputs',
                'expected': 'Exact integer retained end to end, one booking, original body/key/receipt on retry, no horizontal page overflow',
                'environment': 'Local HTTP and Chromium ' + browser.version + ', not constrained Docker'}
            try:
                check(browser, entry)
                row.update(status='PASS', observed='All entry, transport, lifetime, validation and layout assertions passed')
            except Exception:
                row.update(status='FAIL', observed=traceback.format_exc())
            row['duration_seconds'] = time.monotonic() - started
            rows.append(row)
            with (OUT / 'cases.jsonl').open('a') as log:
                log.write(json.dumps(row) + '\n')
            print(row['id'], row['status'], round(row['duration_seconds'], 3), flush=True)
        browser.close()
finally:
    service.shutdown()
    service.server_close()
    thread.join()
    sources = [ROOT / 'domain.py', ROOT / 'server.py', ROOT / 'exactjson.py', *sorted((ROOT / 'web').glob('*')), Path(__file__)]
    (OUT / 'sources.json').write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2) + '\n')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (OUT / 'summary.json').write_text(json.dumps({'head_at_execution': head, 'product_identity': 'Exact source hashes bind these working-tree bytes; HEAD may differ',
        'counts': {status: sum(row['status'] == status for row in rows) for status in ['PASS', 'FAIL']}, 'duration_seconds': sum(row['duration_seconds'] for row in rows)}, indent=2) + '\n')
print(OUT)
sys.exit(any(row['status'] != 'PASS' for row in rows))
