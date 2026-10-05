"""Complementary pair-cell repair obligations derived from Stage2 UI rules.

D222 stays unchanged. These cases additionally bind absence of all-day rows,
retained single false cells, accessible declared-order choices, preserved refused
forms, and a real refresh completing during a later booking response loss.
"""
import json
import re
import time

import pytest
from playwright.sync_api import expect
from derived.test_stage1 import headers
from derived.test_stage2_browser import (DAY, browser_world, fixture, seed, login,
                                        search, no_overflow, interception)


def occupy(c, token):
    r=c.post('/reservations',json={'restaurant_id':'r','table_id':'a',
        'starts_at_local':DAY+'T18:00','party_size':2},headers=headers(token,'external'))
    assert r.status_code==201
    return r.json()


def open_pair(page):
    cell=page.get_by_test_id('slot-b+a-18:00')
    expect(cell).to_have_attribute('data-available','true')
    expect(cell).to_have_accessible_name(re.compile(r'Garden nook.*Bay window.*18:00'))
    cell.focus(); expect(cell).to_be_focused(); page.keyboard.press('Enter')
    summary=page.get_by_test_id('booking-summary').inner_text()
    assert summary.index('Garden nook')<summary.index('Bay window')
    return summary


def preserved(page, summary):
    expect(page.get_by_test_id('booking-form')).to_be_visible()
    expect(page.get_by_test_id('booking-summary')).to_have_text(summary)
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4')


@pytest.mark.parametrize('width',[375,1360],ids=['mobile','desktop'])
@pytest.mark.parametrize('excluded',['occupied-all-day','insufficient-capacity'])
def test_D223_excluded_pair_row_and_single_cells(browser_world,width,excluded,record_property):
    """All-day excluded pairs have no row or choices; every single cell retains exact API availability, while available pairs remain literal, ordered and keyboard accessible."""
    c,page,errors,out=browser_world;fx=fixture(pair=True)
    for h in fx['restaurants'][0]['opening_hours']: h.update(opens='18:00',closes='19:00')
    token=seed(c,fx);page.set_viewport_size({'width':width,'height':900})
    login(page);search(page);open_pair(page)
    if excluded=='occupied-all-day': occupy(c,token)
    party=4 if excluded=='occupied-all-day' else 5
    slots=c.get('/availability',params={'restaurant_id':'r','date':DAY,'party_size':party}).json()['slots']
    assert len(slots)==1 and all(o['table_ids']!=['b','a'] for o in slots[0]['available_options'])
    search(page,party)
    expect(page.get_by_test_id('slot-c-18:00')).to_have_attribute('data-available',str('c' in slots[0]['available_table_ids']).lower())
    expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
    expect(page.get_by_role('heading',name='Garden nook + Bay window',exact=True)).to_have_count(0)
    for table in 'abc':
        expect(page.get_by_test_id('slot-'+table+'-18:00')).to_have_attribute('data-available',str(table in slots[0]['available_table_ids']).lower())
    page.screenshot(path=str(out/'excluded-pair-row.png'),full_page=True)
    geometry=no_overflow(page);assert not errors
    record_property('observed',json.dumps({'width':width,'excluded':excluded,'pair_row_and_choices_absent':True,
        'single_cells_match_api':True,'available_control_keyboard_and_declared_labels':True,'geometry':geometry}))


@pytest.mark.parametrize('width',[375,1360],ids=['mobile','desktop'])
def test_D224_refused_pair_disappears_but_retry_identity_survives(browser_world,width,record_property):
    """A confirmed refusal removes the unavailable pair choice while preserving its form, body and key for successful unchanged retry after the competing booking is cancelled."""
    c,page,errors,out=browser_world;token=seed(c,fixture(pair=True));page.set_viewport_size({'width':width,'height':900})
    calls,receipts,statuses=interception(page,lose=False)
    login(page);search(page);summary=open_pair(page);other=occupy(c,token)
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('booking-error')).to_be_visible()
    expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
    expect(page.get_by_test_id('slot-b+a-19:00')).to_have_attribute('data-available','true')
    expect(page.get_by_test_id('slot-a-18:00')).to_have_attribute('data-available','false')
    preserved(page,summary);expect(page.get_by_test_id('confirmation')).to_have_count(0)
    assert c.post('/reservations/'+other['reference']+'/cancel',headers=headers(token)).status_code==200
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
    ref=page.get_by_test_id('confirmation-reference').inner_text();preserved(page,summary)
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_have_text(ref)
    expect(page.get_by_test_id('booking-error')).to_have_count(0);expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
    assert statuses==[409,201,200] and calls[0]==calls[1]==calls[2] and receipts[1]==receipts[2]
    rows=c.get('/reservations',headers=headers(token)).json()['reservations']
    assert len(rows)==2 and sum(r['status']=='confirmed' for r in rows)==1
    page.screenshot(path=str(out/'restored-pair-confirmation.png'),full_page=True);no_overflow(page);assert not errors
    record_property('observed',json.dumps({'width':width,'statuses':statuses,'unchanged_form_body_key':True,
        'refused_pair_choice_removed':True,'later_pair_available':True,'confirmed_bookings':1}))


@pytest.mark.parametrize('width',[375,1360],ids=['mobile','desktop'])
def test_D225_refresh_finishes_during_committed_response_loss(browser_world,width,record_property):
    """A real refusal refresh completing while the unchanged next POST201 is held cannot discard its form/key; aborting that committed response stays uncertain and retry200 recovers exactly one booking."""
    c,page,errors,out=browser_world;token=seed(c,fixture(pair=True));page.set_viewport_size({'width':width,'height':900})
    calls=[];receipts=[];statuses=[];held_availability=[];held_post=[];availability_count=[]
    def availability(route):
        response=route.fetch();availability_count.append(response.status)
        if len(availability_count)==2:held_availability.append((route,response))
        else:route.fulfill(response=response)
    def submission(route):
        if route.request.method!='POST':route.fallback();return
        calls.append({'key':route.request.headers.get('idempotency-key'),'body':route.request.post_data})
        response=route.fetch();statuses.append(response.status);receipts.append(response.json())
        if len(calls)==2:
            assert response.status==201;held_post.append((route,response))
        else:route.fulfill(response=response)
    def wait_for(items):
        end=time.monotonic()+5
        while not items and time.monotonic()<end:page.wait_for_timeout(20)
        assert items
    page.route('**/availability?**',availability);page.route('**/reservations',submission)
    login(page);search(page);summary=open_pair(page);other=occupy(c,token)
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('booking-error')).to_be_visible();wait_for(held_availability)
    assert c.post('/reservations/'+other['reference']+'/cancel',headers=headers(token)).status_code==200
    page.get_by_test_id('booking-submit').click();wait_for(held_post)
    route,response=held_availability.pop();route.fulfill(response=response)
    expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
    expect(page.get_by_test_id('slot-b+a-19:00')).to_have_attribute('data-available','true')
    preserved(page,summary);expect(page.get_by_test_id('booking-submit')).to_be_disabled()
    expect(page.get_by_test_id('confirmation')).to_have_count(0);expect(page.get_by_test_id('booking-error')).to_have_count(0)
    route,response=held_post.pop();route.abort('failed')
    expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
    assert page.get_by_test_id('booking-uncertain').inner_text().strip()
    preserved(page,summary);expect(page.get_by_test_id('confirmation')).to_have_count(0)
    expect(page.get_by_test_id('booking-error')).to_have_count(0)
    page.screenshot(path=str(out/'refresh-complete-uncertain.png'),full_page=True)
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_have_text(receipts[1]['reference'])
    expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
    assert statuses==[409,201,200] and calls[0]==calls[1]==calls[2] and receipts[1]==receipts[2]
    rows=c.get('/reservations',headers=headers(token)).json()['reservations']
    assert len(rows)==2 and sum(r['status']=='confirmed' for r in rows)==1
    no_overflow(page);assert not errors
    record_property('observed',json.dumps({'width':width,'statuses':statuses,'real201_response_aborted':True,
        'refresh_completed_while_post_pending':True,'unchanged_body_key_form':True,'confirmed_bookings':1}))
