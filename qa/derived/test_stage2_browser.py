"""Independent real-browser Stage2 checks, written before Stage2 product review."""
import copy
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import parse_qs,urlsplit
import httpx
import pytest
from playwright.sync_api import sync_playwright,expect
from derived.test_stage1 import headers

BASE=os.environ.get('QA_BROWSER_BASE','http://127.0.0.1:8080')
DAY='2030-01-01'
PASSWORD='synthetic-password'


def wait_healthy(client):
    deadline=time.monotonic()+55
    while time.monotonic()<deadline:
        try:
            response=client.get('/health',timeout=2)
            if response.status_code==200 and response.json()=={'status':'ok'}:return
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise AssertionError('Service did not become healthy within55 seconds')


def fixture(pair=False,large=None):
    return {'users':[{'id':'u','email':'u@browser.test','password':PASSWORD,'display_name':'Browser diner'}],
        'restaurants':[{'id':'r','name':'Juniper garden','timezone':'UTC','slot_minutes':30,
          'reservation_duration_minutes':60,'cancellation_cutoff_minutes':0,
          'opening_hours':[{'weekday':d,'opens':'17:00','closes':'23:00'} for d in 'mon tue wed thu fri sat sun'.split()],
          'tables':[{'id':'a','label':'Bay window','capacity':large or (2 if pair else 4)},
                    {'id':'b','label':'Garden nook','capacity':2 if pair else 4},
                    {'id':'c','label':'Courtyard','capacity':4}], 'combinable':[['b','a']] if pair else []}], 'reservations':[]}


@pytest.fixture
def browser_world(request):
    out=Path(os.environ.get('QA_EVIDENCE_DIR','/evidence'))/'browser'/re.sub(r'[^A-Za-z0-9_.-]','_',request.node.name)
    out.mkdir(parents=True,exist_ok=True)
    with httpx.Client(base_url=BASE,trust_env=False,timeout=5) as c,sync_playwright() as pw:
        wait_healthy(c)
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1360,'height':900})
        context.set_default_timeout(8000);context.tracing.start(screenshots=True,snapshots=True,sources=True)
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:errors.append('External runtime URL: '+r.url) if urlsplit(r.url).scheme in ('http','https') and urlsplit(r.url).netloc!=urlsplit(BASE).netloc else None)
        try:yield c,page,errors,out
        finally:
            if not page.is_closed():page.screenshot(path=str(out/'final.png'),full_page=True)
            (out/'page-errors.json').write_text(json.dumps(errors))
            context.tracing.stop(path=str(out/'trace.zip'));context.close();browser.close()


def seed(c,data):
    assert c.post('/_test/reset',json=data,timeout=10).status_code==204
    r=c.post('/auth/login',json={'email':'u@browser.test','password':PASSWORD});assert r.status_code==200
    return r.json()['token']


def login(page):
    page.goto(BASE+'/login');page.get_by_test_id('login-email').fill('u@browser.test')
    page.get_by_test_id('login-password').fill(PASSWORD);page.get_by_test_id('login-submit').click()
    expect(page.get_by_test_id('current-user')).to_contain_text('Browser diner')
    # Authentication sets the header before its automatic navigation commits.
    # Wait for that real redirect instead of racing it with a second goto.
    page.wait_for_url(BASE+'/');expect(page.get_by_test_id('current-user')).to_contain_text('Browser diner')


def search(page,party='4',restaurant='r',day=DAY):
    page.get_by_test_id('restaurant-select').select_option(restaurant)
    page.get_by_test_id('date-input').fill(day);page.get_by_test_id('party-size-input').fill(str(party))
    page.get_by_test_id('search-button').click()


def no_overflow(page):
    result=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
    assert result['document']<=result['viewport'],result
    return result


def interception(page,lose=True):
    calls=[];receipts=[];statuses=[]
    def handle(route):
        request=route.request
        if request.method!='POST':route.fallback();return
        calls.append({'key':request.headers.get('idempotency-key'),'raw_body':request.post_data})
        response=route.fetch();statuses.append(response.status);receipts.append(response.json())
        if lose and len(calls)==1:
            assert response.status==201,'Must lose an actual committed success, not fabricate a failure'
            route.abort('failed')
        else:route.fulfill(response=response)
    page.route('**/reservations',handle)
    return calls,receipts,statuses


@pytest.mark.parametrize('pair',[False,True],ids=['D211-single-two-booking-swap','D211-pair-to-single-mobile'])
def test_D211_actual_lost_201_then_atomic_repair_shows_current_assignment(browser_world,pair,record_property):
    """Lose actual committed201, retain pending form/body/key, repair pair-to-single or swap two bookings, then recover original reference with CURRENT confirmation/lookup/grid and exactly one UI-created reservation."""
    c,page,errors,out=browser_world;t=seed(c,fixture(pair));auth=headers(t)
    other=None
    if not pair:
        r=c.post('/reservations',json={'restaurant_id':'r','table_id':'b','starts_at_local':DAY+'T18:00','party_size':2},headers=headers(t,'other'))
        assert r.status_code==201;other=r.json()
    else:page.set_viewport_size({'width':375,'height':812})
    calls,receipts,statuses=interception(page)
    login(page);search(page);slot='b+a' if pair else 'a'
    cell=page.get_by_test_id('slot-'+slot+'-18:00');expect(cell).to_have_attribute('data-available','true');cell.click()
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
    summary=page.get_by_test_id('booking-summary').inner_text()
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('booking-uncertain')).to_be_visible();assert page.get_by_test_id('booking-uncertain').inner_text().strip()
    expect(page.get_by_test_id('booking-error')).to_have_count(0);expect(page.get_by_test_id('confirmation-reference')).to_have_count(0)
    expect(page.get_by_test_id('booking-summary')).to_have_text(summary)
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
    assert len(calls)==1 and statuses==[201] and calls[0]['key'];original=receipts[0];ref=original['reference']
    page.screenshot(path=str(out/'uncertain.png'),full_page=True)
    changes={'moves':[{'reference':ref,'table_ids':['c' if pair else 'b']}]}
    if other:changes['moves'].append({'reference':other['reference'],'table_ids':['a']})
    repair=c.post('/reservation-moves',json=changes,headers=headers(t,'repair'));assert repair.status_code==201,repair.text
    page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_have_text(ref)
    label='Courtyard' if pair else 'Garden nook'
    expect(page.get_by_test_id('confirmation-tables')).to_contain_text(label)
    expect(page.get_by_test_id('confirmation-details')).to_contain_text(label)
    expect(page.get_by_test_id('booking-uncertain')).to_have_count(0);expect(page.get_by_test_id('booking-error')).to_have_count(0)
    expect(page.get_by_test_id('booking-form')).to_be_visible();expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
    assert len(calls)==2 and calls[0]==calls[1] and statuses==[201,200] and receipts==[original,original]
    current=c.get('/reservations/'+ref,headers=auth);assert current.status_code==200
    assert current.json()['table_ids']==['c' if pair else 'b']
    expect(page.get_by_test_id('slot-'+('c' if pair else 'b')+'-18:00')).to_have_attribute('data-available','false')
    page.screenshot(path=str(out/'current-confirmation.png'),full_page=True);no_overflow(page)
    page.goto(BASE+'/lookup');page.get_by_test_id('lookup-reference-input').fill(ref);page.get_by_test_id('lookup-submit').click()
    expect(page.get_by_test_id('reservation-tables')).to_contain_text(label);expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
    listed=c.get('/reservations',headers=auth).json()['reservations'];assert len(listed)==(1 if pair else 2)
    assert sum(x['reference']==ref for x in listed)==1
    assert not errors;no_overflow(page)
    record_property('observed',json.dumps({'post_statuses':statuses,'unchanged_raw_retry':calls[0]==calls[1],
        'immutable_receipt':receipts[0]==receipts[1],'current_table_ids':current.json()['table_ids'],
        'ui_created_reservations':1,'viewport':page.viewport_size}))


def test_D212_exact_integer_search_form_create_and_retry(browser_world,record_property):
    """Accepted9007199254740993 remains exact through query text, form value, raw JSON number, committed response-loss retry and server lookup; no JS-safe-integer cap or rounding."""
    c,page,errors,out=browser_world;party='9007199254740993';t=seed(c,fixture(large=int(party)))
    page.set_viewport_size({'width':375,'height':812});queries=[]
    page.on('request',lambda r:queries.append(parse_qs(urlsplit(r.url).query)) if urlsplit(r.url).path=='/availability' else None)
    calls,receipts,statuses=interception(page);login(page);search(page,party)
    cell=page.get_by_test_id('slot-a-18:00');expect(cell).to_have_attribute('data-available','true');cell.click()
    expect(page.get_by_test_id('booking-party-size')).to_have_value(party)
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
    assert queries and queries[0]['party_size']==[party]
    raw=calls[0]['raw_body'];decoded=json.loads(raw,parse_int=Decimal,parse_float=Decimal)
    assert isinstance(decoded['party_size'],Decimal) and decoded['party_size']==Decimal(party)
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
    assert calls[0]==calls[1] and statuses==[201,200] and receipts[0]==receipts[1]
    listed=c.get('/reservations',headers=headers(t));assert listed.status_code==200
    rows=json.loads(listed.content,parse_int=Decimal,parse_float=Decimal)['reservations']
    assert len(rows)==1 and rows[0]['party_size']==Decimal(party)
    no_overflow(page);assert not errors
    record_property('observed',json.dumps({'party_text':party,'raw_numeric_party_preserved':True,'unchanged_retry':True,'post_statuses':statuses}))


@pytest.mark.parametrize('pair',[False,True],ids=['D213-single-refused','D213-pair-refused'])
def test_D213_confirmed_refusal_preserves_form_refreshes_grid_and_can_change_choice(browser_world,pair):
    """Another client wins after form opening: confirmed409 shows only booking-error, retains form/inputs, refreshes occupancy and permits a distinct corrected request."""
    c,page,errors,out=browser_world;t=seed(c,fixture(pair));calls,_,statuses=interception(page,lose=False)
    login(page);search(page);slot='b+a' if pair else 'a'
    cell=page.get_by_test_id('slot-'+slot+'-18:00');expect(cell).to_have_attribute('data-available','true');cell.click()
    summary=page.get_by_test_id('booking-summary').inner_text()
    taken=c.post('/reservations',json={'restaurant_id':'r','table_id':'a','starts_at_local':DAY+'T18:00','party_size':2},headers=headers(t,'other'))
    assert taken.status_code==201
    page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('booking-error')).to_be_visible()
    expect(page.get_by_test_id('confirmation-reference')).to_have_count(0);expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
    expect(page.get_by_test_id('booking-form')).to_be_visible();expect(page.get_by_test_id('booking-summary')).to_have_text(summary)
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4')
    page.screenshot(path=str(out/'refused-preserved-form.png'),full_page=True)
    expect(page.get_by_test_id('slot-a-18:00')).to_have_attribute('data-available','false')
    if pair:
        old=page.get_by_test_id('slot-b+a-18:00')
        assert old.count()==0 or old.get_attribute('data-available')=='false'
    page.get_by_test_id('slot-c-18:00').click();page.get_by_test_id('booking-submit').click()
    expect(page.get_by_test_id('confirmation-reference')).to_be_visible();expect(page.get_by_test_id('booking-error')).to_have_count(0)
    assert statuses==[409,201] and calls[0]['key']!=calls[1]['key'];assert not errors


def test_D214_late_search_cannot_replace_grid_labels_or_booking_selection(browser_world):
    """Hold actual search A response until after B opens its form; late A must not change B's grid, labels, party or booking selection."""
    c,page,errors,out=browser_world;fx=fixture();second=copy.deepcopy(fx['restaurants'][0]);second.update(id='second',name='Second dining room')
    second['tables']=[{'id':'z','label':'Second room booth','capacity':6}];fx['restaurants'].append(second);seed(c,fx)
    held=[]
    def delay_a(route):
        params=parse_qs(urlsplit(route.request.url).query)
        response=route.fetch()
        if params.get('restaurant_id')==['r']:held.append((route,response))
        else:route.fulfill(response=response)
    page.route('**/availability?**',delay_a);login(page);search(page,'2','r')
    deadline=time.monotonic()+5
    while not held and time.monotonic()<deadline:page.wait_for_timeout(20)
    assert held,'Search A must actually be pending'
    page.screenshot(path=str(out/'loading-search-a.png'),full_page=True)
    search(page,'4','second');cell=page.get_by_test_id('slot-z-18:00');expect(cell).to_have_attribute('data-available','true');cell.click()
    expect(page.get_by_test_id('booking-summary')).to_contain_text('Second room booth')
    for route,response in held:route.fulfill(response=response)
    page.wait_for_timeout(150)
    expect(page.get_by_test_id('slot-z-18:00')).to_have_attribute('data-available','true')
    expect(page.get_by_test_id('slot-a-18:00')).to_have_count(0)
    expect(page.get_by_test_id('booking-summary')).to_contain_text('Second room booth')
    expect(page.get_by_test_id('booking-party-size')).to_have_value('4');assert not errors


@pytest.mark.parametrize('width',[375,1360],ids=['D215-mobile','D215-desktop'])
def test_D215_routes_labels_keyboard_layout_and_untrusted_text(browser_world,width,record_property):
    """Required routes render HTML and coherent labelled keyboard controls without horizontal scrolling; untrusted restaurant/table/display text never executes markup."""
    c,page,errors,out=browser_world;fx=fixture();payload='<img src=x onerror="window.__qa_xss=1">'
    fx['restaurants'][0]['name']='Garden '+payload;fx['restaurants'][0]['tables'][0]['label']='Window '+payload
    fx['users'][0]['display_name']='Browser diner '+payload
    fx['restaurants'][0]['opening_hours']=[h for h in fx['restaurants'][0]['opening_hours'] if h['weekday']!='sun']
    t=seed(c,fx);page.set_viewport_size({'width':width,'height':900})
    for route in ['/','/signup','/login','/lookup']:
        response=page.goto(BASE+route);assert response.status==200 and 'text/html' in response.headers.get('content-type','')
        no_overflow(page)
        controls=page.locator('input:visible,select:visible')
        for i in range(controls.count()):
            control=controls.nth(i)
            label=control.evaluate('(e)=>e.getAttribute("aria-label")||e.getAttribute("aria-labelledby")||(e.labels&&Array.from(e.labels).map(x=>x.textContent).join(" "))')
            assert label and label.strip(),'Visible input lacks associated label on '+route
        page.keyboard.press('Tab')
        focus=page.evaluate('(()=>{let e=document.activeElement;function css(){let s=getComputedStyle(e);return [s.outlineStyle,s.outlineWidth,s.outlineColor,s.boxShadow,s.borderColor,s.backgroundColor,s.color,s.fontWeight]};let before=css();e.blur();let after=css();e.focus();return {tag:e.tagName,focused:before,unfocused:after}})()')
        assert focus['tag'] not in ('BODY','HTML')
        # A valid focus ring may be painted on an ancestor or pseudo-element.
        # Preserve control styles and screenshots for required visual review;
        # do not invent an outline-only oracle.
        (out/('focus-'+(route.strip('/') or 'home')+'.json')).write_text(json.dumps(focus,indent=2))
        page.screenshot(path=str(out/('route-'+(route.strip('/') or 'home')+'.png')),full_page=True)
    page.goto(BASE+'/');search(page,'2',day='2030-01-06')
    expect(page.get_by_test_id('no-slots')).to_be_visible();expect(page.get_by_test_id('availability-grid')).to_have_count(0)
    page.screenshot(path=str(out/'closed-empty.png'),full_page=True)
    login(page);search(page,'2');cell=page.get_by_test_id('slot-a-18:00');expect(cell).to_have_attribute('data-available','true');cell.click()
    expect(page.get_by_test_id('booking-summary')).to_contain_text(payload)
    expect(page.get_by_test_id('current-user')).to_contain_text(payload)
    assert not page.evaluate('Boolean(window.__qa_xss)') and page.locator('img[src="x"]').count()==0
    no_overflow(page);assert not errors
    styles=page.locator('body,h1,h2,label,button,input,select,[data-testid="booking-summary"]').evaluate_all('(elements)=>elements.filter(e=>e.getClientRects().length).map(e=>{let s=getComputedStyle(e);return {tag:e.tagName,testid:e.dataset.testid,text:e.textContent.slice(0,120),color:s.color,background:s.backgroundColor,fontSize:s.fontSize,fontWeight:s.fontWeight,outline:s.outline}})')
    (out/'visual-style-evidence.json').write_text(json.dumps(styles,indent=2))
    record_property('observed',json.dumps({'viewport':width,'routes':4,'labelled_controls':True,'keyboard_reachable':True,'focus_and_contrast_visual_review':'required separately','untrusted_text_executed':False}))
