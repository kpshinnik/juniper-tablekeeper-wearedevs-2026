"""Independent Stage4 real201 loss plus planner repair at both required widths."""
import json

import pytest
from playwright.sync_api import expect

from derived.test_stage1 import headers
from derived.test_stage2_browser import (BASE, DAY, PASSWORD, browser_world, fixture,
    seed, login, search, no_overflow, interception)


@pytest.mark.parametrize('width',[375,1360],ids=['mobile','desktop'])
@pytest.mark.parametrize('pair',[False,True],ids=['single','pair'])
def test_D410_real_lost_201_then_plan_current_assignment(browser_world,width,pair,record_property):
    """Real201 response is aborted, manager plan is applied, and exact original retry recovers current literal labels/lookup/grid without duplication."""
    c,page,errors,out=browser_world
    fx=fixture(pair); fx['restaurants'][0]['manager_user_ids']=['u']
    label='<svg onload=alert(1)> '+('Courtyard-'*25)+' 雪 & garden'
    fx['restaurants'][0]['tables'][2]['label']=label
    fx['users'].append({'id':'other','email':'other@browser.test','password':PASSWORD,'display_name':'Other'})
    token=seed(c,fx); page.set_viewport_size({'width':width,'height':900})
    if not pair:
        r=c.post('/auth/login',json={'email':'other@browser.test','password':PASSWORD}); assert r.status_code==200
        other=r.json()['token']
        r=c.post('/reservations',json={'restaurant_id':'r','table_id':'b','starts_at_local':DAY+'T18:00','party_size':2},headers=headers(other,'other'))
        assert r.status_code==201
    calls,receipts,statuses=interception(page)
    login(page); search(page); cell=page.get_by_test_id('slot-'+('b+a' if pair else 'a')+'-18:00')
    expect(cell).to_have_attribute('data-available','true'); cell.click()
    summary=page.get_by_test_id('booking-summary').inner_text(); page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
    assert page.get_by_test_id('booking-uncertain').inner_text().strip()
    expect(page.get_by_test_id('booking-error')).to_have_count(0); expect(page.get_by_test_id('confirmation-reference')).to_have_count(0)
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4'); no_overflow(page)
    assert statuses==[201] and len(calls)==1 and calls[0]['key']
    original=receipts[0]; ref=original['reference']
    p=c.post('/restaurants/r/replans',json={'table_id':'a','from':DAY+'T18:00:00Z','to':DAY+'T19:00:00Z'},headers=headers(token,'plan'))
    assert p.status_code==201,p.text
    applied=c.post('/restaurants/r/replans/'+p.json()['plan_id']+'/apply',json={},headers=headers(token,'apply'))
    assert applied.status_code==201,applied.text
    assert next(r for r in applied.json()['reservations'] if r['reference']==ref)['table_ids']==['c']
    expect(page.get_by_test_id('booking-summary')).to_have_text(summary)
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
    page.screenshot(path=str(out/'uncertain-after-plan.png'),full_page=True)
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_have_text(ref)
    expect(page.get_by_test_id('confirmation-tables')).to_contain_text(label)
    expect(page.get_by_test_id('confirmation-details')).to_contain_text(label)
    expect(page.get_by_test_id('booking-error')).to_have_count(0); expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
    assert calls[0]==calls[1] and statuses==[201,200] and receipts==[original,original]
    assert len(c.get('/reservations',headers=headers(token)).json()['reservations'])==1
    no_overflow(page); page.screenshot(path=str(out/'current-confirmation.png'),full_page=True)
    page.goto(BASE+'/lookup'); page.get_by_test_id('lookup-reference-input').fill(ref); page.get_by_test_id('lookup-submit').click()
    expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
    expect(page.get_by_test_id('reservation-tables')).to_contain_text(label); no_overflow(page)
    assert page.get_by_test_id('reservation-tables').locator('svg').count()==0
    page.goto(BASE+'/'); search(page)
    expect(page.get_by_test_id('slot-a-18:00')).to_have_attribute('data-available','false')
    expect(page.get_by_test_id('slot-c-18:00')).to_have_attribute('data-available','false')
    no_overflow(page); assert errors==[]
    record_property('observed',json.dumps({'width':width,'pair':pair,'post_statuses':statuses,
        'same_request_identity':calls[0]==calls[1],'original_receipt_immutable':True,
        'current_table':'c','actual_plan_apply':p.json()['plan_id'],'single_diner_booking':True,
        'literal_full_label':label,'horizontal_overflow':False}))
