"""Complementary V-S2-003 browser checks using real local HTTP and Chromium."""
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
import urllib.error
import urllib.request

os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers')
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server

OUT = ROOT/'checks/evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-pair-visibility')
OUT.mkdir(parents=True)
service = server.Server(('127.0.0.1', 0), server.Handler)
thread = threading.Thread(target=service.serve_forever, daemon=True)
thread.start()
BASE = 'http://127.0.0.1:' + str(service.server_address[1])
DAY = '2030-01-01'
rows = []


def http(path, body=None, token=None, key=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    if key: headers['Idempotency-Key'] = key
    request = urllib.request.Request(BASE+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try: response = urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as error: response = error
    raw = response.read()
    return response.status, json.loads(raw) if raw else None


def reset():
    fixture = {'users': [{'id':'u','email':'pair@example.test','password':'synthetic-pair','display_name':'Pair diner'}],
        'restaurants':[{'id':'r','name':'Synthetic pair garden','timezone':'UTC','slot_minutes':60,
            'reservation_duration_minutes':60,'cancellation_cutoff_minutes':0,
            'opening_hours':[{'weekday':'tue','opens':'18:00','closes':'20:00'}],
            'tables':[{'id':'a','label':'Window','capacity':2},{'id':'b','label':'Garden','capacity':2},{'id':'c','label':'Terrace','capacity':4}],
            'combinable':[['b','a']]}], 'reservations':[]}
    assert http('/_test/reset',fixture)[0] == 204
    code,auth=http('/auth/login',{'email':'pair@example.test','password':'synthetic-pair'})
    assert code == 200
    return auth


def occupy(token, clock):
    code, booking = http('/reservations',{'restaurant_id':'r','table_id':'a','starts_at_local':DAY+'T'+clock,'party_size':2},token,'occupy-'+clock)
    assert code == 201
    return booking


def search(page, party='4'):
    page.get_by_test_id('restaurant-select').select_option('r')
    page.get_by_test_id('date-input').fill(DAY)
    page.get_by_test_id('party-size-input').fill(party)
    page.get_by_test_id('search-button').click()
    expect(page.get_by_test_id('availability-grid')).to_be_visible()


def single_cells(page, party='4'):
    code, data = http('/availability?restaurant_id=r&date='+DAY+'&party_size='+party)
    assert code == 200
    for slot in data['slots']:
        for table in ['a','b','c']:
            cell = page.get_by_test_id('slot-'+table+'-'+slot['starts_at_local'][-5:])
            expect(cell).to_have_count(1)
            expect(cell).to_have_attribute('data-available',str(table in slot['available_table_ids']).lower())


def partial(page, token, observation):
    occupy(token,'18:00');search(page)
    expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
    pair = page.get_by_test_id('slot-b+a-19:00')
    expect(pair).to_be_enabled();expect(pair).to_have_attribute('data-available','true')
    assert 'Garden and Window' in pair.get_attribute('aria-label')
    assert page.locator('.table-title h3').all_text_contents() == ['Window','Garden','Terrace','Garden + Window']
    single_cells(page)
    pair.focus();assert pair.evaluate('e=>document.activeElement===e')
    pair.press('Enter');expect(page.get_by_test_id('booking-summary')).to_contain_text('Garden + Window')
    search(page,'5')
    assert page.locator('.table-title h3').all_text_contents() == ['Window','Garden','Terrace']
    assert page.locator('button.slot').count() == 6
    single_cells(page,'5')
    observation['covered']=['occupied member','touching free slot','declared label/rank','keyboard','capacity-excluded whole row','all single cells']


def all_day(page, token, observation):
    occupy(token,'18:00');occupy(token,'19:00');search(page)
    assert page.locator('.table-title h3').all_text_contents() == ['Window','Garden','Terrace']
    assert page.locator('button.slot').count() == 6
    expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
    expect(page.get_by_test_id('slot-b+a-19:00')).to_have_count(0)
    single_cells(page)
    observation['covered']=['all-day occupied member','no pair row','single unavailable cells retained']


def refusal(page, token, observation):
    posts=[]
    def observe(route):
        if route.request.method!='POST':return route.continue_()
        response=route.fetch();posts.append({'body':route.request.post_data,'key':route.request.headers['idempotency-key'],'status':response.status,'response':response.json()});route.fulfill(response=response)
    page.route('**/reservations',observe)
    search(page);page.get_by_test_id('slot-b+a-18:00').click()
    competitor=occupy(token,'18:00')
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('booking-error')).to_be_visible()
    expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
    expect(page.get_by_test_id('slot-b+a-19:00')).to_be_visible()
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
    expect(page.get_by_test_id('booking-summary')).to_contain_text('Garden + Window')
    expect(page.get_by_test_id('confirmation')).to_have_count(0)
    single_cells(page)
    assert http('/reservations/'+competitor['reference']+'/cancel',{},token)[0]==200
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
    reference=page.get_by_test_id('confirmation-reference').inner_text()
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_have_text(reference)
    assert [p['status'] for p in posts]==[409,201,200]
    assert len({p['key'] for p in posts})==1 and len({p['body'] for p in posts})==1
    assert posts[1]['response']==posts[2]['response']
    expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
    expect(page.get_by_test_id('booking-form')).to_be_visible()
    observation['posts']=posts


def pending_refresh(page, token, observation):
    posts=[];held_post=[];held_av=[];availability_calls=[]
    def post(route):
        if route.request.method!='POST':return route.continue_()
        response=route.fetch();posts.append({'body':route.request.post_data,'key':route.request.headers['idempotency-key'],'status':response.status,'response':response.json()})
        if len(posts)==1:
            assert response.status==201;route.abort('failed')
        elif len(posts)==3:held_post.append((route,response))
        else:route.fulfill(response=response)
    def availability(route):
        availability_calls.append(route.request.url)
        if len(availability_calls)==2:held_av.append((route,route.fetch()))
        else:route.continue_()
    def until(predicate):
        end=time.monotonic()+5
        while not predicate():
            assert time.monotonic()<end,'Expected intercepted real request did not arrive'
            page.wait_for_timeout(20)
    page.route('**/reservations',post);page.route('**/availability?*',availability)
    try:
        search(page);page.get_by_test_id('slot-b+a-18:00').click();page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('booking-uncertain')).to_be_visible();expect(page.get_by_test_id('booking-error')).to_have_count(0);expect(page.get_by_test_id('confirmation')).to_have_count(0)
        page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_be_visible();until(lambda:held_av)
        page.get_by_test_id('booking-submit').click();until(lambda:held_post)
        expect(page.get_by_test_id('booking-submit')).to_be_disabled()
        route,response=held_av.pop();route.fulfill(response=response)
        expect(page.get_by_test_id('slot-b+a-18:00')).to_have_count(0)
        expect(page.get_by_test_id('slot-b+a-19:00')).to_be_visible()
        expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
        expect(page.get_by_test_id('booking-summary')).to_contain_text('Garden + Window')
        expect(page.get_by_test_id('confirmation')).to_have_count(0)
        expect(page.get_by_test_id('booking-error')).to_have_count(0)
        assert page.get_by_test_id('booking-submit').is_disabled()
        single_cells(page)
        route,response=held_post.pop();route.fulfill(response=response)
        expect(page.get_by_test_id('confirmation-reference')).to_have_text(posts[0]['response']['reference'])
        expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
        expect(page.get_by_test_id('confirmation-tables')).to_have_text('Garden + Window')
        assert [p['status'] for p in posts]==[201,200,200]
        assert len({p['body'] for p in posts})==1 and len({p['key'] for p in posts})==1
        assert posts[0]['response']==posts[1]['response']==posts[2]['response']
        assert len(http('/reservations',token=token)[1]['reservations'])==1
        observation['posts']=posts;observation['refresh_completed_while_retry_pending']=True
    finally:
        for route,response in held_av+held_post:route.fulfill(response=response)


try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for width in [375,1360]:
            for number,name,operation in [('B223','partial-day-and-capacity',partial),('B224','all-day-occupancy',all_day),('B225','refusal-retains-selected-form',refusal),('B226','loss-and-refresh-during-retry',pending_refresh)]:
                case_id=number+'-'+str(width);folder=OUT/case_id;folder.mkdir();start=time.monotonic();observation={'width':width,'page_errors':[]}
                row={'id':case_id,'description':name,'expected':'All assertions pass','environment':'Local ephemeral HTTP and Chromium, not Docker qualification'}
                auth=reset();context=browser.new_context(viewport={'width':width,'height':900});context.set_default_timeout(5000)
                context.add_init_script('localStorage.setItem("juniper.session",'+json.dumps(json.dumps(auth))+');')
                context.tracing.start(screenshots=True,snapshots=True,sources=True);page=context.new_page();page.on('pageerror',lambda error:observation['page_errors'].append(str(error)))
                try:
                    page.goto(BASE);operation(page,auth['token'],observation)
                    observation['geometry']=page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
                    assert observation['geometry']['width']==observation['geometry']['scroll']
                    assert not observation['page_errors']
                    row.update(status='PASS',observed='All assertions passed')
                except Exception:row.update(status='FAIL',observed=traceback.format_exc())
                finally:
                    page.screenshot(path=str(folder/'final.png'),full_page=True);context.tracing.stop(path=str(folder/'trace.zip'));context.close()
                    (folder/'observed.json').write_text(json.dumps(observation,indent=2)+'\n')
                row['duration_seconds']=time.monotonic()-start;rows.append(row)
                with (OUT/'cases.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
                print(case_id,row['status'],flush=True)
                if row['status']!='PASS':print(row['observed'],flush=True)
        browser.close()
finally:
    service.shutdown();service.server_close();thread.join()
    sources=[ROOT/'server.py',ROOT/'domain.py',ROOT/'exactjson.py',*sorted((ROOT/'web').glob('*')),Path(__file__)]
    (OUT/'source-sha256.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
    (OUT/'result.json').write_text(json.dumps({'repository_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'runtime_binding':'Working tree, exact hashes accompany this attempt','counts':{s:sum(r['status']==s for r in rows) for s in ['PASS','FAIL']},'duration_seconds':sum(r['duration_seconds'] for r in rows)},indent=2)+'\n')
print(OUT)
sys.exit(any(row['status']!='PASS' for row in rows))
