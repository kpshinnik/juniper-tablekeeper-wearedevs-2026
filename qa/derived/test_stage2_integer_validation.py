"""D221: decimal-text controls preserve positive-whole-number validation."""
import json
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

from derived.test_stage1 import headers
from derived.test_stage2_browser import browser_world, fixture, seed, login, search, DAY, no_overflow


@pytest.mark.parametrize('entry', ['search', 'booking'], ids=['D221-search', 'D221-booking'])
def test_D221_invalid_decimal_text_no_request_then_valid_keyboard_recovery(browser_world, entry, record_property):
    """Reject eight non-positive/noninteger inputs without requests or mutation; labelled keyboard control stays usable and corrected input creates exactly once."""
    c, page, errors, out = browser_world
    token = seed(c, fixture()); login(page)
    page.set_viewport_size({'width': 375, 'height': 900})
    page.get_by_test_id('restaurant-select').select_option('r')
    page.get_by_test_id('date-input').fill(DAY)
    if entry == 'booking':
        search(page, '2'); page.get_by_test_id('slot-a-18:00').click()
    control = page.get_by_test_id('party-size-input' if entry == 'search' else 'booking-party-size')
    submit = page.get_by_test_id('search-button' if entry == 'search' else 'booking-submit')
    expect(page.get_by_label('Guests' if entry == 'search' else 'Guests at your table', exact=True)).to_have_count(1)
    expect(control).to_have_attribute('inputmode', 'numeric')
    calls = []
    page.on('request', lambda r: calls.append({'method':r.method,'url':r.url,'raw_body':r.post_data})
            if urlsplit(r.url).path in ('/availability','/reservations') else None)
    before = c.get('/_test/export').json(); observations = []
    for value in ['', '0', '-1', '1.5', '1e3', 'Infinity', 'NaN', 'abc']:
        control.fill(''); control.press_sequentially(value); control.focus()
        expect(control).to_be_focused(); expect(control).to_have_value(value)
        count = len(calls); submit.click()
        feedback = page.get_by_test_id('search-error' if entry == 'search' else 'booking-error')
        expect(feedback).to_be_visible(); assert feedback.inner_text().strip()
        expect(page.get_by_test_id('confirmation')).to_have_count(0)
        assert len(calls) == count, calls
        assert c.get('/_test/export').json() == before
        observations.append({'input':value,'error':feedback.inner_text(),'request_count':len(calls),**no_overflow(page)})
    control.fill(''); control.press_sequentially('2'); submit.click()
    if entry == 'search':
        cell = page.get_by_test_id('slot-a-18:00'); expect(cell).to_have_attribute('data-available','true')
        cell.click(); page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
    rows = c.get('/reservations', headers=headers(token)).json()['reservations']
    assert len(rows) == 1 and rows[0]['party_size'] == 2
    assert sum(x['method']=='POST' for x in calls) == 1
    assert not errors
    result = {'entry':entry,'invalid_inputs':observations,'requests':calls,'booking_count':1,'geometry':no_overflow(page)}
    (out/'validation.json').write_text(json.dumps(result,indent=2))
    record_property('observed',json.dumps(result))
