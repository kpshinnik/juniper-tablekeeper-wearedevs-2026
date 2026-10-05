"""Keep one live browser/form through old backend export and target import.

Stage1 has no HTML contract. The target's real Stage2 HTML is therefore loaded
once while an explicit transport adapter routes API calls to the old producer;
after import the same origin/form calls the destination. No DOM/storage/session
injection and no invented receipt are used. Actual process removal is a separate
host-run integration, not claimed by this browser case.
"""
import hashlib
import json
import os
from urllib.parse import urlsplit
import httpx
from playwright.sync_api import expect
from derived.test_stage1 import headers
from derived.test_stage2_browser import browser_world,fixture,seed,login,search,BASE,DAY,no_overflow,wait_healthy

SOURCE_STAGE=int(os.environ.get('QA_SOURCE_STAGE','1'))
DESTINATION_STAGE=int(os.environ.get('STAGE_UNDER_TEST','2'))


def test_D216_live_browser_pending_identity_and_old_reference_survive_import(browser_world,record_property):
    """A live browser signed in against the source retains its pending exact body/key and old reference across an actual export/import boundary, recovering original receipt and using a new target table_ids operation."""
    destination,page,errors,out=browser_world;pair=SOURCE_STAGE>=2
    with httpx.Client(base_url='http://source:8080',trust_env=False,timeout=5) as source:
        wait_healthy(source)
        token=seed(source,fixture(pair=pair));seed(destination,fixture(pair=pair))
        old=source.post('/reservations',json={'restaurant_id':'r','table_id':'c','starts_at_local':DAY+'T20:00','party_size':2},headers=headers(token,'existing'))
        assert old.status_code==201;oldref=old.json()['reference']
        target_login=destination.post('/auth/login',json={'email':'u@browser.test','password':'synthetic-password'})
        assert target_login.status_code==200;revoked=target_login.json()['token']
        state={'target':'http://source:8080'};calls=[];receipts=[];statuses=[]
        def transport(route):
            request=route.request;url=urlsplit(request.url)
            api=url.path.startswith(('/auth/','/restaurants','/availability','/reservations','/reservation-moves','/_test/'))
            if not api:route.fallback();return
            response=route.fetch(url=state['target']+url.path+('?' + url.query if url.query else ''))
            if request.method=='POST' and url.path=='/reservations':
                calls.append({'key':request.headers.get('idempotency-key'),'raw_body':request.post_data})
                statuses.append(response.status);receipts.append(response.json())
                if len(calls)==1:
                    assert response.status==201
                    route.abort('failed');return
            route.fulfill(response=response)
        page.route('**/*',transport);login(page)
        page.goto(BASE+'/lookup');page.get_by_test_id('lookup-reference-input').fill(oldref);page.get_by_test_id('lookup-submit').click()
        expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
        page.goto(BASE+'/');search(page,'4');slot='b+a' if pair else 'a'
        cell=page.get_by_test_id('slot-'+slot+'-18:00');expect(cell).to_have_attribute('data-available','true');cell.click()
        form_before=page.get_by_test_id('booking-summary').inner_text()
        page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
        expect(page.get_by_test_id('confirmation-reference')).to_have_count(0)
        assert statuses==[201] and calls[0]['key'];original=receipts[0]
        exported=source.get('/_test/export',timeout=10);assert exported.status_code==200
        imported=destination.post('/_test/import',content=json.dumps(exported.json(),allow_nan=False),headers={'Content-Type':'application/json'},timeout=10)
        assert imported.status_code==204,imported.text
        state['target']=BASE
        expect(page.get_by_test_id('current-user')).to_contain_text('Browser diner')
        expect(page.get_by_test_id('booking-summary')).to_have_text(form_before);expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
        assert destination.get('/reservations',headers=headers(revoked)).status_code==401
        page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_have_text(original['reference'])
        expect(page.get_by_test_id('booking-uncertain')).to_have_count(0);expect(page.get_by_test_id('booking-error')).to_have_count(0)
        assert statuses==[201,200] and calls[0]==calls[1] and receipts==[original,original]
        current=destination.get('/reservations/'+original['reference'],headers=headers(token));assert current.status_code==200
        assert set(current.json()['table_ids'])==({'a','b'} if pair else {'a'})
        expect(page.get_by_test_id('confirmation-tables')).to_contain_text('Bay window')
        if pair:expect(page.get_by_test_id('confirmation-tables')).to_contain_text('Garden nook')
        listed=destination.get('/reservations',headers=headers(token));assert listed.status_code==200 and len(listed.json()['reservations'])==2
        page.goto(BASE+'/lookup');page.get_by_test_id('lookup-reference-input').fill(oldref);page.get_by_test_id('lookup-submit').click()
        expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed');expect(page.get_by_test_id('reservation-tables')).to_contain_text('Courtyard')
        new=destination.post('/reservations',json={'restaurant_id':'r','table_ids':['c'],'starts_at_local':DAY+'T21:00','party_size':2},headers=headers(token,'new-stage2'))
        assert new.status_code==201 and new.json()['table_ids']==['c']
        assert not errors;no_overflow(page)
        page.screenshot(path=str(out/'old-reference-after-transfer.png'),full_page=True)
        record_property('observed',json.dumps({'source_stage':SOURCE_STAGE,'destination_stage':DESTINATION_STAGE,'same_live_browser':True,
            'actual_committed_response_loss':True,'post_statuses':statuses,'original_body_key_receipt':True,
            'old_reference_lookup':True,'retained_token':True,'new_target_table_ids_write':True,
            'snapshot_sha256':hashlib.sha256(exported.content).hexdigest(),
            'transport_adapter':'Target HTML; API producer switches to destination only after import; no DOM/storage injection',
            'producer_removal_in_this_browser_case':False}))
