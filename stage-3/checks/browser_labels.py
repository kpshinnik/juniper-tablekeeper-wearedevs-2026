"""Direct V-S2-001 reproduction and label-layout regression; local HTTP only."""
import datetime
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

os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers')
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server

OUT = ROOT / 'checks/evidence' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-label-layout')
OUT.mkdir(parents=True, exist_ok=False)
service = server.Server(('127.0.0.1', 0), server.Handler)
thread = threading.Thread(target=service.serve_forever, daemon=True)
thread.start()
BASE = 'http://127.0.0.1:' + str(service.server_address[1])
PAYLOAD = '<img src=x onerror="window.__qa_xss=1">'
rows = []


def check(browser, width):
    data = {'users': [{'id': 'u', 'email': 'u@browser.test', 'password': 'synthetic-password', 'display_name': 'Browser diner ' + PAYLOAD}],
            'restaurants': [{'id': 'r', 'name': 'Garden ' + PAYLOAD, 'timezone': 'UTC', 'slot_minutes': 30,
                'reservation_duration_minutes': 60, 'cancellation_cutoff_minutes': 0,
                'opening_hours': [{'weekday': d, 'opens': '17:00', 'closes': '23:00'} for d in 'mon tue wed thu fri sat'.split()],
                'tables': [{'id': 'a', 'label': 'Window ' + PAYLOAD, 'capacity': 4},
                           {'id': 'b', 'label': 'Garden nook', 'capacity': 4}, {'id': 'c', 'label': 'Courtyard', 'capacity': 4}], 'combinable': []}],
            'reservations': []}
    (OUT / 'fixture.json').write_text(json.dumps(data, indent=2) + '\n')
    req = urllib.request.Request(BASE + '/_test/reset', data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
    assert urllib.request.urlopen(req, timeout=10).status == 204
    context = browser.new_context(viewport={'width': width, 'height': 900})
    page = context.new_page()
    observed = []
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def measure(state):
        result = page.evaluate('''() => ({viewport:innerWidth, document:document.documentElement.scrollWidth,
          escaped: Array.from(document.querySelectorAll('body *')).map(e => {const r=e.getBoundingClientRect();return {
            tag:e.tagName, id:e.id, class:e.className, testid:e.dataset.testid, left:r.left, right:r.right,
            width:r.width, scroll:e.scrollWidth, client:e.clientWidth, text:e.textContent.slice(0,160)}})
            .filter(e=>e.right>innerWidth+.5 || e.left<-.5)})''')
        observed.append({'state': state, **result})
        return result

    try:
        for route in ['/', '/signup', '/login', '/lookup']:
            page.goto(BASE + route)
            measure('public:' + route)
        page.goto(BASE + '/login')
        page.get_by_test_id('login-email').fill('u@browser.test')
        page.get_by_test_id('login-password').fill('synthetic-password')
        page.get_by_test_id('login-submit').click()
        expect(page.get_by_test_id('current-user')).to_contain_text(PAYLOAD)
        page.get_by_test_id('restaurant-select').select_option('r')
        page.get_by_test_id('date-input').fill('2030-01-01')
        page.get_by_test_id('party-size-input').fill('2')
        page.get_by_test_id('search-button').click()
        page.get_by_test_id('slot-a-18:00').click()
        expect(page.get_by_test_id('booking-summary')).to_contain_text(PAYLOAD)
        assert not page.evaluate('Boolean(window.__qa_xss)')
        assert page.locator('img[src="x"]').count() == 0
        result = measure('signed-in booking form')
        page.screenshot(path=str(OUT / f'booking-{width}.png'), full_page=True)
        assert result['document'] <= width, result
        page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
        reference = page.get_by_test_id('confirmation-reference').inner_text()
        expect(page.get_by_test_id('confirmation-details')).to_contain_text(PAYLOAD)
        measure('confirmation')
        for route in ['/signup', '/login', '/lookup']:
            page.goto(BASE + route)
            expect(page.get_by_test_id('current-user')).to_contain_text(PAYLOAD)
            measure('signed-in:' + route)
        page.get_by_test_id('lookup-reference-input').fill(reference)
        page.get_by_test_id('lookup-submit').click()
        expect(page.get_by_test_id('reservation-tables')).to_contain_text(PAYLOAD)
        measure('lookup detail')
        page.screenshot(path=str(OUT / f'lookup-{width}.png'), full_page=True)
        assert all(item['document'] <= width for item in observed), observed
        assert not errors, errors
    finally:
        (OUT / f'layout-{width}.json').write_text(json.dumps({'measurements': observed, 'page_errors': errors}, indent=2) + '\n')
        context.close()


try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width in [375, 1360]:
            start = time.monotonic()
            row = {'id': f'V-S2-001-{width}', 'description': 'Direct reported literal labels; signed-in form and lifetime layout',
                   'expected': 'Safe literal labels, all measured widths <= viewport', 'environment': 'Local HTTP and Chromium, not constrained Docker'}
            try:
                check(browser, width)
                row.update(status='PASS', observed='All label/layout/lifetime assertions passed')
            except Exception:
                row.update(status='FAIL', observed=traceback.format_exc())
            row['duration_seconds'] = time.monotonic() - start
            rows.append(row)
            with (OUT / 'cases.jsonl').open('a') as log:
                log.write(json.dumps(row) + '\n')
            print(row['id'], row['status'], round(row['duration_seconds'], 3), flush=True)
        browser.close()
finally:
    service.shutdown()
    service.server_close()
    thread.join()
    sources = [ROOT / 'domain.py', ROOT / 'legacy.py', ROOT / 'server.py', ROOT / 'exactjson.py', *sorted((ROOT / 'web').glob('*')), Path(__file__)]
    (OUT / 'sources.json').write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2) + '\n')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (OUT / 'summary.json').write_text(json.dumps({'head_at_execution': head, 'product_identity': 'Exact source hashes accompany attempt; uncommitted files may differ from HEAD',
        'counts': {s: sum(r['status'] == s for r in rows) for s in ['PASS', 'FAIL']}, 'duration_seconds': sum(r['duration_seconds'] for r in rows)}, indent=2) + '\n')
print(OUT)
sys.exit(any(row['status'] != 'PASS' for row in rows))
