"""Local real-browser regressions. Heavy judged-container execution is separate."""
import datetime
import hashlib
import json
import os
import pathlib
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request

os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/Users/kirillpsinnik/Code/wearedevelopers-hackathon/tools/browsers')
from playwright.sync_api import sync_playwright, expect

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import server


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'checks/evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-browser')
OUT.mkdir(parents=True, exist_ok=False)
service = server.Server(('127.0.0.1', 0), server.Handler)
thread = threading.Thread(target=service.serve_forever, daemon=True)
thread.start()
BASE = 'http://127.0.0.1:'+str(service.server_address[1])
observations = []


def request(path, body=None, token=None, method=None, key=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer '+token
    if key: headers['Idempotency-Key'] = key
    req = urllib.request.Request(BASE+path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method or ('POST' if body is not None else 'GET'))
    try: response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as error: response = error
    raw = response.read()
    return response.status, json.loads(raw) if raw else None


def fixture(huge=False, xss=False):
    rest = {'id': 'r', 'name': 'Juniper Garden', 'timezone': 'Europe/Berlin', 'slot_minutes': 30,
            'reservation_duration_minutes': 90, 'cancellation_cutoff_minutes': 0,
            'opening_hours': [{'weekday': d, 'opens': '18:00', 'closes': '23:00'} for d in ['mon','tue','wed','thu','fri','sat','sun']],
            'tables': [{'id': 'a','label': 'Window','capacity': 9007199254740992 if huge else 4},
                       {'id': 'b','label': 'Garden','capacity': 1 if huge else 4},
                       {'id': 'c','label': 'Terrace','capacity': 2}], 'combinable': [['a','b']]}
    if xss: rest['name'] = '<img src=x onerror="window.BAD=1">'; rest['tables'][0]['label'] = '<script>window.BAD=2</script>'
    second = dict(rest, id='r2', name='Juniper Orchard', tables=[{'id':'z','label':'Orchard seat','capacity':4}], combinable=[])
    return {'users':[{'id':'u','email':'ada@example.test','password':'password123','display_name':'Ada'}], 'restaurants':[rest,second], 'reservations':[]}


def signin(context):
    code, auth = request('/auth/login', {'email':'ada@example.test','password':'password123'})
    assert code == 200
    context.add_init_script('localStorage.setItem("juniper.session", '+json.dumps(json.dumps(auth))+');')
    return auth['token']


def search(page, party='2', restaurant='r'):
    page.get_by_test_id('restaurant-select').select_option(restaurant)
    page.get_by_test_id('date-input').fill('2099-01-05')
    page.get_by_test_id('party-size-input').fill(party)
    page.get_by_test_id('search-button').click()
    expect(page.get_by_test_id('availability-grid')).to_be_visible()


def routes_signup_lookup(browser):
    request('/_test/reset', fixture())
    context = browser.new_context(); page = context.new_page()
    try:
        for path in ['/', '/signup', '/login', '/lookup']:
            response = page.goto(BASE+path); assert response.status == 200 and 'text/html' in response.headers['content-type']
        page.goto(BASE+'/signup')
        page.get_by_test_id('signup-display-name').fill('Mira')
        page.get_by_test_id('signup-email').fill('mira@example.test')
        page.get_by_test_id('signup-password').fill('password123')
        page.get_by_test_id('signup-submit').click()
        expect(page.get_by_test_id('current-user')).to_have_text('Mira')
        search(page); page.get_by_test_id('slot-a-19:00').click(); page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('confirmation-reference')).to_be_visible(); reference = page.get_by_test_id('confirmation-reference').inner_text()
        page.get_by_test_id('booking-submit').click(); expect(page.get_by_test_id('confirmation-reference')).to_have_text(reference)
        page.goto(BASE+'/lookup'); expect(page.get_by_test_id('current-user')).to_have_text('Mira')
        page.get_by_test_id('lookup-reference-input').fill(reference); page.get_by_test_id('lookup-submit').click()
        expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
        page.get_by_test_id('reservation-cancel-button').click(); expect(page.get_by_test_id('reservation-status')).to_have_text('cancelled')
        expect(page.get_by_test_id('reservation-cancel-button')).to_have_count(0)
        page.get_by_test_id('logout-button').click(); expect(page.get_by_test_id('current-user')).to_have_count(0)
        page.goto(BASE+'/login'); page.get_by_test_id('login-email').fill('mira@example.test'); page.get_by_test_id('login-password').fill('password123'); page.get_by_test_id('login-submit').click()
        expect(page.get_by_test_id('current-user')).to_have_text('Mira')
    finally: context.close()


def loss_repair(browser, replacement=False):
    request('/_test/reset', fixture()); context = browser.new_context(); token = signin(context); page = context.new_page(); captured = []
    def lose(route):
        if route.request.method != 'POST': return route.continue_()
        captured.append({'body': route.request.post_data, 'key': route.request.headers['idempotency-key']})
        response = route.fetch()
        if len(captured) == 1:
            assert response.status == 201; captured[0]['receipt'] = response.json(); route.abort('failed')
        else: route.fulfill(response=response)
    page.route('**/reservations', lose)
    try:
        page.goto(BASE); search(page, '6'); page.get_by_test_id('slot-a+b-19:00').click(); page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('booking-uncertain')).to_be_visible(); expect(page.get_by_test_id('booking-error')).to_have_count(0); expect(page.get_by_test_id('confirmation')).to_have_count(0)
        expect(page.get_by_test_id('booking-party-size')).to_have_value('6')
        original = captured[0]['receipt']; ref = original['reference']
        if replacement:
            _, exported = request('/_test/export'); assert request('/_test/reset', fixture())[0] == 204; assert request('/_test/import', exported)[0] == 204
        assert request('/reservations/'+ref, {'table_id':'c','party_size':2}, token, method='PATCH')[0] == 200
        page.get_by_test_id('booking-submit').click(); expect(page.get_by_test_id('confirmation-reference')).to_have_text(ref)
        expect(page.get_by_test_id('confirmation-tables')).to_have_text('Terrace'); expect(page.get_by_test_id('booking-uncertain')).to_have_count(0); expect(page.get_by_test_id('booking-error')).to_have_count(0)
        assert captured[0]['body'] == captured[1]['body'] and captured[0]['key'] == captured[1]['key']
        assert len(request('/reservations', token=token)[1]['reservations']) == 1
        code, replay = request('/reservations', json.loads(captured[0]['body']), token, key=captured[0]['key']); assert code == 200 and replay == original
        expect(page.get_by_test_id('slot-a+b-19:00')).to_have_attribute('data-available','true')
        page.goto(BASE+'/lookup'); page.get_by_test_id('lookup-reference-input').fill(ref); page.get_by_test_id('lookup-submit').click(); expect(page.get_by_test_id('reservation-tables')).to_have_text('Terrace')
        (OUT/('replacement-loss.json' if replacement else 'repair-loss.json')).write_text(json.dumps(captured,indent=2)+'\n')
    finally: context.close()


def stale_search(browser):
    request('/_test/reset', fixture()); context = browser.new_context(); signin(context); page = context.new_page(); held=[]
    def delay(route):
        if 'restaurant_id=r&' in route.request.url:
            held.append((route,route.fetch()))
        else: route.continue_()
    page.route('**/availability?*',delay)
    try:
        page.goto(BASE); page.get_by_test_id('restaurant-select').select_option('r'); page.get_by_test_id('date-input').fill('2099-01-05'); page.get_by_test_id('search-button').click()
        page.wait_for_timeout(100); assert held
        page.get_by_test_id('restaurant-select').select_option('r2'); page.get_by_test_id('search-button').click(); expect(page.get_by_test_id('slot-z-19:00')).to_be_visible()
        page.get_by_test_id('slot-z-19:00').click(); expect(page.get_by_test_id('booking-summary')).to_contain_text('Orchard seat')
        route,response = held.pop(); route.fulfill(response=response); page.wait_for_timeout(100)
        expect(page.get_by_test_id('slot-z-19:00')).to_be_visible(); expect(page.get_by_test_id('slot-a-19:00')).to_have_count(0); expect(page.get_by_test_id('booking-summary')).to_contain_text('Orchard seat')
    finally:
        for route,response in held: route.fulfill(response=response)
        context.close()


def exact_party(browser):
    request('/_test/reset',fixture(huge=True)); context=browser.new_context();token=signin(context);page=context.new_page();seen=[]
    page.on('request',lambda req: seen.append((req.url,req.post_data)) if req.url.endswith('/reservations') or '/availability?' in req.url else None)
    try:
        page.goto(BASE);search(page,'9007199254740993');page.get_by_test_id('slot-a+b-19:00').click()
        expect(page.get_by_test_id('booking-party-size')).to_have_value('9007199254740993')
        page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_be_visible()
        ref=page.get_by_test_id('confirmation-reference').inner_text();page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('confirmation-reference')).to_have_text(ref)
        posts=[json.loads(body) for url,body in seen if body];assert len(posts)==2 and all(p['party_size']==9007199254740993 for p in posts)
        assert any('party_size=9007199254740993' in url for url,_ in seen)
        assert request('/reservations/'+ref,token=token)[1]['party_size']==9007199254740993
    finally:context.close()


def refusal_and_layout(browser):
    request('/_test/reset',fixture());context=browser.new_context(viewport={'width':375,'height':900});token=signin(context);page=context.new_page()
    try:
        page.goto(BASE);search(page);page.get_by_test_id('slot-a-19:00').click()
        assert request('/reservations',{'restaurant_id':'r','table_id':'a','starts_at_local':'2099-01-05T19:00','party_size':2},token,key='competitor')[0]==201
        page.get_by_test_id('booking-submit').click();expect(page.get_by_test_id('booking-error')).to_be_visible();expect(page.get_by_test_id('confirmation')).to_have_count(0)
        expect(page.get_by_test_id('booking-party-size')).to_have_value('2');expect(page.get_by_test_id('slot-a-19:00')).to_have_attribute('data-available','false')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(OUT/'mobile-375.png'),full_page=True)
        page.set_viewport_size({'width':1280,'height':900});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth');page.screenshot(path=str(OUT/'desktop-1280.png'),full_page=True)
        for path in ['/signup','/login','/lookup']:
            page.set_viewport_size({'width':375,'height':900});page.goto(BASE+path);assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.get_by_test_id('lookup-reference-input').focus();assert page.evaluate('getComputedStyle(document.activeElement).outlineStyle') != 'none'
    finally:context.close()


def xss(browser):
    request('/_test/reset',fixture(xss=True));context=browser.new_context();signin(context);page=context.new_page()
    try:
        page.goto(BASE);search(page);page.get_by_test_id('slot-a-19:00').click();assert page.evaluate('window.BAD === undefined')
        expect(page.get_by_test_id('booking-summary')).to_contain_text('<script>window.BAD=2</script>');assert page.locator('#page img').count()==0
    finally:context.close()


try:
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        cases=[('B201','Routes/signup/login/single retry/lookup/cancel',routes_signup_lookup),('B202','Real committed response loss plus pair-to-single repair',loss_repair),('B203','Pending form/token/retry survives replacement import',lambda b:loss_repair(b,True)),('B204','Late search cannot replace newer labels/grid/form',stale_search),('B205','Exact party above JavaScript safe integer through query/body/retry',exact_party),('B206','Competing booking refusal/form/grid/mobile/desktop/focus',refusal_and_layout),('B207','Untrusted restaurant/table labels are inert text',xss)]
        for case_id,description,operation in cases:
            start=time.monotonic();row={'id':case_id,'description':description,'expected':'All assertions pass','environment':'Local HTTP service and Chromium, not resource-limited Docker'}
            try:operation(browser);row.update(status='PASS',observed='All assertions passed')
            except Exception:row.update(status='FAIL',observed=traceback.format_exc())
            row['duration_seconds']=time.monotonic()-start;observations.append(row)
            with (OUT/'cases.jsonl').open('a') as log:log.write(json.dumps(row)+'\n')
            print(case_id,row['status'],round(row['duration_seconds'],3),flush=True)
            if row['status']!='PASS':print(row['observed'],flush=True)
        browser.close()
finally:
    service.shutdown();service.server_close();thread.join()
    sources=[ROOT/'domain.py',ROOT/'legacy.py',ROOT/'server.py',ROOT/'exactjson.py',*sorted((ROOT/'web').glob('*')),pathlib.Path(__file__)]
    (OUT/'sources.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
    (OUT/'summary.json').write_text(json.dumps({'counts':{s:sum(r['status']==s for r in observations) for s in ['PASS','FAIL']},'duration_seconds':sum(r['duration_seconds'] for r in observations),'source_revision':'Stage3 working tree; exact source hashes accompany this attempt'},indent=2)+'\n')
print(OUT)
sys.exit(any(row['status']!='PASS' for row in observations))
