"""A manager repairs seating while the diner has an actually lost booking response."""
import json

import pytest
from playwright.sync_api import expect

from test_stage4_ui import (BASE, DAY, api, browser_page, seed, request, auth,
                            apply, check_retry_lookup_grid)


@pytest.mark.parametrize('pair', [False, True], ids=['U403-global-lost', 'U404-pair-lost'])
def test_committed_lost_response_then_repair_retains_original_retry(
        api, browser_page, record_property, pair):
    """Abort the actual committed POST response, apply a plan, then recover with the exact same body/key and current assignment."""
    c = api
    page, creates, errors, out = browser_page
    timings = []
    tokens = seed(c, timings, pair=pair)
    if not pair:
        other = request(c, timings, 'POST', '/reservations',
                        headers=auth(tokens['other'], 'other'),
                        json={'restaurant_id': 'dining', 'table_id': 'y',
                              'starts_at_local': DAY+'T18:00', 'party_size': 2})
        assert other.status_code == 201
    receipts, statuses = [], []

    def lose_only_first_committed_response(route):
        r = route.request
        if r.method != 'POST':
            route.fallback()
            return
        creates.append({'method': r.method, 'key': r.headers.get('idempotency-key'),
                        'body': r.post_data})
        response = route.fetch()
        statuses.append(response.status)
        receipts.append(response.json())
        if len(receipts) == 1:
            assert response.status == 201
            route.abort('failed')
        else:
            route.fulfill(response=response)

    # The later route handles POST itself; the fixture's earlier route is retained.
    page.route('**/reservations', lose_only_first_committed_response)
    if pair:
        page.set_viewport_size({'width': 375, 'height': 812})
    page.goto(BASE+'/login')
    page.get_by_test_id('login-email').fill('guest@ui4.test')
    page.get_by_test_id('login-password').fill('synthetic-ui-password')
    page.get_by_test_id('login-submit').click()
    expect(page.get_by_test_id('current-user')).to_contain_text('Guest')
    page.get_by_test_id('date-input').fill(DAY)
    page.get_by_test_id('party-size-input').fill('4')
    page.get_by_test_id('search-button').click()
    slot = 'y+x' if pair else 'x'
    expect(page.get_by_test_id('slot-'+slot+'-18:00')).to_have_attribute('data-available', 'true')
    page.get_by_test_id('slot-'+slot+'-18:00').click()
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
    assert page.get_by_test_id('booking-uncertain').inner_text().strip()
    expect(page.get_by_test_id('booking-error')).to_have_count(0)
    expect(page.get_by_test_id('confirmation-reference')).to_have_count(0)
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
    assert len(receipts) == len(creates) == 1
    original = receipts[0]
    ref = original['reference']
    page.screenshot(path=str(out/'actually-lost-committed-response.png'), full_page=True)

    plan, result = apply(c, timings, tokens['manager'])
    assert plan['moved_count'] == (1 if pair else 2) and plan['unused_seats'] == 0
    table, label = ('z', 'Courtyard table') if pair else ('y', 'Garden nook')
    assignments = {r['reference']: r['table_ids'] for r in result['reservations']}
    assert assignments[ref] == [table]
    values = check_retry_lookup_grid(c, timings, page, creates, errors, out,
                                    tokens['guest'], ref, label, table, pair=pair)
    assert statuses == [201, 200]
    assert receipts == [original, original]
    listed = request(c, timings, 'GET', '/reservations', headers=auth(tokens['guest']))
    assert listed.status_code == 200
    assert len(listed.json()['reservations']) == 1
    record_property('description', test_committed_lost_response_then_repair_retains_original_retry.__doc__)
    record_property('observed', json.dumps({'actual_response_loss_after_commit': True,
                                         'browser_post_statuses': statuses,
                                         'immutable_original_receipt': receipts[0] == receipts[1],
                                         'no_duplicate_booking': True, 'plan': plan, **values}))
