"""D220: independent exact401-digit layout lifetime, separate from unchanged D219.

The search summary must display its actual value without document overflow or
clipping. Inputs may scroll internally for editing; their complete value remains
exact. All observations target a committed product through real HTTP/Chromium.
"""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from derived.test_stage1 import headers
from derived.test_stage2_browser import browser_world, fixture, login, DAY, BASE
from derived.test_stage2_native_range import PARTY, exact


def geometry(page, require_party):
    """Read real text fragments, including clipping ancestors; never alter DOM."""
    result = page.evaluate('''({party}) => {
      const fragments=[], walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
      let node;
      while(node=walker.nextNode()) {
        const at=node.textContent.indexOf(party); if(at<0) continue;
        if(['SCRIPT','STYLE'].includes(node.parentElement.tagName)) continue;
        const range=document.createRange(); range.setStart(node,at); range.setEnd(node,at+party.length);
        const rects=Array.from(range.getClientRects(),r=>({left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}));
        const ancestors=[];
        for(let e=node.parentElement;e;e=e.parentElement) {
          const s=getComputedStyle(e),r=e.getBoundingClientRect();
          ancestors.push({tag:e.tagName,display:s.display,visibility:s.visibility,opacity:s.opacity,
            overflowX:s.overflowX,overflowY:s.overflowY,textOverflow:s.textOverflow,
            left:r.left,right:r.right,top:r.top,bottom:r.bottom});
        }
        fragments.push({text:node.textContent,rects,ancestors});
      }
      return {viewport:innerWidth,document:document.documentElement.scrollWidth,
        body:document.body.scrollWidth,fragments};
    }''', {'party': PARTY})
    assert result['document'] <= result['viewport'], result
    if require_party:
        assert result['fragments'], 'Full actual401-digit search summary must be rendered'
    for fragment in result['fragments']:
        assert fragment['rects'], 'Actual party text must be rendered, not hidden'
        for rect in fragment['rects']:
            assert rect['width'] > 0 and rect['height'] > 0
            assert rect['left'] >= -1 and rect['right'] <= result['viewport']+1, rect
            for ancestor in fragment['ancestors']:
                assert ancestor['display'] != 'none' and ancestor['visibility'] == 'visible'
                assert float(ancestor['opacity']) > 0
                if ancestor['overflowX'] in ('hidden', 'clip'):
                    assert rect['left'] >= ancestor['left']-1 and rect['right'] <= ancestor['right']+1
                if ancestor['overflowY'] in ('hidden', 'clip'):
                    assert rect['top'] >= ancestor['top']-1 and rect['bottom'] <= ancestor['bottom']+1
    return result


@pytest.mark.parametrize('width', [375, 1360], ids=['D220-mobile', 'D220-desktop'])
def test_D220_exact_party_geometry_through_loss_retry_and_lookup(browser_world, width, record_property):
    """401-digit search summary remains fully rendered and page fits viewport through real201 loss/retry, original receipt, current lookup and one exact booking."""
    c, page, errors, out = browser_world
    started = time.monotonic()
    observed = {'id': 'D220-'+str(width), 'product_sha': os.environ.get('QA_PRODUCT_SHA'),
        'test_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'viewport': width, 'exact_decimal': PARTY, 'browser_version': page.context.browser.version,
        'geometry': [], 'requests': [], 'posts': [], 'outcome': 'RUNNING'}
    def measure(name, require_party=True):
        text = page.locator('body').inner_text()
        assert 'Infinity' not in text and 'NaN' not in text, 'Finite exact values must not be presented as nonfinite'
        entry = {'state': name, **geometry(page, require_party)}
        observed['geometry'].append(entry)
        page.screenshot(path=str(out/(name+'.png')), full_page=True)
        (out/'geometry.json').write_text(json.dumps(observed['geometry'], indent=2))
        assert not errors
    def capture(request):
        if urlsplit(request.url).path in ('/availability', '/reservations'):
            observed['requests'].append({'method': request.method, 'url': request.url,
                'raw_body': request.post_data, 'key': request.headers.get('idempotency-key')})
    def intercept(route):
        if route.request.method != 'POST': route.fallback(); return
        tick = time.monotonic(); response = route.fetch()
        observed['posts'].append({'status': response.status, 'raw_body': route.request.post_data,
            'key': route.request.headers.get('idempotency-key'), 'response_text': response.text(),
            'fetch_s': time.monotonic()-tick})
        if len(observed['posts']) == 1:
            assert response.status == 201, 'Lose an actual committed success only'
            route.abort('failed')
        else: route.fulfill(response=response)
    try:
        fx = fixture(); rest = fx['restaurants'][0]
        rest['name'] = 'Exact party garden'
        rest['tables'] = [{'id': 'a', 'label': 'Window seat', 'capacity': 'EXACT_CAPACITY'}]
        rest['combinable'] = []
        rest['opening_hours'] = [{'weekday': 'tue', 'opens': '18:00', 'closes': '19:00'}]
        raw_fixture = json.dumps(fx).replace('"EXACT_CAPACITY"', '1e400')
        (out/'synthetic-fixture.json').write_text(raw_fixture)
        assert c.post('/_test/reset', content=raw_fixture, headers={'Content-Type': 'application/json'}, timeout=10).status_code == 204
        auth = c.post('/auth/login', json={'email': 'u@browser.test', 'password': 'synthetic-password'})
        assert auth.status_code == 200; token = auth.json()['token']
        page.set_viewport_size({'width': width, 'height': 900})
        page.on('request', capture); page.route('**/reservations', intercept)
        login(page)
        page.get_by_test_id('restaurant-select').select_option('r')
        page.get_by_test_id('date-input').fill(DAY)
        control = page.get_by_test_id('party-size-input')
        control.fill(''); control.press_sequentially(PARTY)
        expect(control).to_have_value(PARTY)
        page.get_by_test_id('search-button').click()
        cell = page.get_by_test_id('slot-a-18:00')
        expect(cell).to_have_attribute('data-available', 'true')
        queries = [parse_qs(urlsplit(x['url']).query) for x in observed['requests']
                   if urlsplit(x['url']).path == '/availability']
        assert queries and queries[-1]['party_size'] == [PARTY]
        measure('search-summary')
        cell.click()
        expect(page.get_by_test_id('booking-summary')).to_contain_text('Window seat')
        expect(page.get_by_test_id('booking-summary')).to_contain_text('18:00')
        expect(page.get_by_test_id('booking-party-size')).to_have_value(PARTY)
        measure('booking-form')
        page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('booking-uncertain')).to_be_visible()
        expect(page.get_by_test_id('booking-error')).to_have_count(0)
        expect(page.get_by_test_id('confirmation')).to_have_count(0)
        expect(page.get_by_test_id('booking-party-size')).to_have_value(PARTY)
        calls = observed['posts']; assert len(calls) == 1 and calls[0]['status'] == 201
        assert exact(calls[0]['raw_body'])['party_size'] == Decimal(PARTY)
        original = exact(calls[0]['response_text'])
        assert original['party_size'] == Decimal(PARTY)
        measure('booking-uncertain')
        page.get_by_test_id('booking-submit').click()
        expect(page.get_by_test_id('confirmation-reference')).to_have_text(original['reference'])
        expect(page.get_by_test_id('booking-uncertain')).to_have_count(0)
        expect(page.get_by_test_id('booking-error')).to_have_count(0)
        expect(page.get_by_test_id('booking-submit')).to_be_enabled()
        assert [x['status'] for x in calls] == [201, 200]
        assert calls[0]['key'] and calls[0]['key'] == calls[1]['key']
        assert calls[0]['raw_body'] == calls[1]['raw_body']
        assert exact(calls[1]['response_text']) == original
        expect(page.get_by_test_id('confirmation-details')).to_contain_text(rest['name'])
        expect(page.get_by_test_id('confirmation-tables')).to_contain_text('Window seat')
        measure('retry-confirmation')
        records = exact(c.get('/reservations', headers=headers(token)).content)['reservations']
        assert len(records) == 1 and records[0]['party_size'] == Decimal(PARTY)
        assert records[0]['reference'] == original['reference']
        page.goto(BASE+'/lookup')
        page.get_by_test_id('lookup-reference-input').fill(original['reference'])
        page.get_by_test_id('lookup-submit').click()
        expect(page.get_by_test_id('reservation-status')).to_have_text('confirmed')
        expect(page.get_by_test_id('reservation-tables')).to_contain_text('Window seat')
        expect(page.get_by_test_id('reservation-detail')).to_contain_text(rest['name'])
        assert exact(c.get('/reservations/'+original['reference'], headers=headers(token)).content) == records[0]
        measure('current-lookup', require_party=False)
        observed.update(outcome='PASS', actual_201_loss=True, original_retry=True, booking_count=1)
    except BaseException as exc:
        observed.update(outcome='FAIL' if isinstance(exc, AssertionError) else 'ERROR',
                        exception={'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        observed.update(duration_s=time.monotonic()-started, page_errors=errors)
        (out/'observed.json').write_text(json.dumps(observed, indent=2))
        record_property('observed', json.dumps(observed))
