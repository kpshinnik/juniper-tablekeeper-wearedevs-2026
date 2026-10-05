"""Independent continuation of the repaired literal-label browser lifetime.

D215's original assertion remains unchanged. These additional definitions cover
the successful receipt, repeated submit, lookup and cancelled detail with the same
valid labels, which its original form-only fixture does not reach.
"""
import json

import pytest
from playwright.sync_api import expect

from derived.test_stage1 import headers
from derived.test_stage2_browser import (
    BASE, browser_world, fixture, interception, login, no_overflow, search, seed,
)


@pytest.mark.parametrize('width', [375, 1360], ids=['D218-mobile', 'D218-desktop'])
def test_D218_full_literal_labels_through_confirmation_retry_lookup_cancel(
        browser_world, width, record_property):
    """Full valid literal labels fit every booking lifecycle screen without executing markup; unchanged retry retains one booking and cancellation remains usable."""
    client, page, errors, out = browser_world
    payload = '<img src=x onerror="window.__qa_xss=1">'
    data = fixture()
    restaurant = data['restaurants'][0]
    restaurant['name'] = 'Garden ' + payload
    restaurant['tables'][0]['label'] = 'Window ' + payload
    data['users'][0]['display_name'] = 'Browser diner ' + payload
    token = seed(client, data)
    page.set_viewport_size({'width': width, 'height': 900})
    measurements = []

    def measure(state):
        result = no_overflow(page)
        assert not page.evaluate('Boolean(window.__qa_xss)')
        assert page.locator('img[src="x"]').count() == 0
        assert not errors
        measurements.append({'state': state, **result})
        (out / 'geometry.json').write_text(json.dumps(measurements, indent=2))
        page.screenshot(path=str(out / (state + '.png')), full_page=True)

    page.goto(BASE + '/')
    search(page, '2')
    expect(page.get_by_test_id('slot-a-18:00')).to_have_attribute('data-available', 'true')
    measure('public-grid')
    login(page)
    search(page, '2')
    cell = page.get_by_test_id('slot-a-18:00')
    expect(cell).to_have_attribute('data-available', 'true')
    expect(page.get_by_test_id('current-user')).to_contain_text(payload)
    measure('signed-grid')
    cell.click()
    expect(page.get_by_test_id('booking-summary')).to_contain_text(payload)
    measure('form')
    calls, receipts, statuses = interception(page, lose=False)
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
    reference = page.get_by_test_id('confirmation-reference').inner_text()
    expect(page.get_by_test_id('confirmation-details')).to_contain_text(restaurant['name'])
    expect(page.get_by_test_id('confirmation-tables')).to_contain_text(restaurant['tables'][0]['label'])
    expect(page.get_by_test_id('booking-form')).to_be_visible()
    measure('confirmation')
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_have_text(reference)
    expect(page.get_by_test_id('booking-submit')).to_be_enabled()
    assert statuses == [201, 200]
    assert calls[0] == calls[1] and receipts[0] == receipts[1]
    response = client.get('/reservations', headers=headers(token))
    assert response.status_code == 200 and len(response.json()['reservations']) == 1
    measure('unchanged-retry')
    page.goto(BASE + '/lookup')
    page.get_by_test_id('lookup-reference-input').fill(reference)
    page.get_by_test_id('lookup-submit').click()
    expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
    expect(page.get_by_test_id('reservation-detail')).to_contain_text(restaurant['name'])
    expect(page.get_by_test_id('reservation-tables')).to_contain_text(restaurant['tables'][0]['label'])
    measure('confirmed-lookup')
    page.get_by_test_id('reservation-cancel-button').click()
    expect(page.get_by_test_id('reservation-status')).to_have_text('cancelled')
    expect(page.get_by_test_id('reservation-cancel-button')).to_have_count(0)
    expect(page.get_by_test_id('reservation-detail')).to_contain_text(restaurant['name'])
    expect(page.get_by_test_id('reservation-tables')).to_contain_text(restaurant['tables'][0]['label'])
    measure('cancelled-lookup')
    record_property('observed', json.dumps({'viewport': width, 'measurements': measurements,
        'full_literal_labels': True, 'markup_executed': False, 'bookings': 1,
        'original_receipt_retry_statuses': statuses}))
