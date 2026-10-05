"""D411: Stage4 operations after actual old/final producer removal by run_upgrade.

Private snapshot, tokens and receipt payloads stay in the runner's disposable
directory. Public evidence contains hashes and assertion outcomes only. This
script itself does not claim to remove a producer; the host runner proves it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import httpx

from derived.test_stage1 import headers
from derived.test_stage3 import fixture, policy, PASSWORD


def healthy(c):
    deadline = time.monotonic()+55
    while time.monotonic()<deadline:
        try:
            r = c.get('/health')
            if r.status_code == 200 and r.json() == {'status': 'ok'}: return
        except httpx.HTTPError:
            pass
        time.sleep(.1)
    raise AssertionError('health deadline')


def require(r, status):
    assert r.status_code == status, (r.status_code, r.text[:1000])
    return r.json() if r.content else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['produce', 'consume'], required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args()
    stage = int(os.environ['QA_SOURCE_STAGE'])
    target = int(os.environ['STAGE_UNDER_TEST'])
    assert target==4 and stage<=target
    root = args.state_dir; tick = time.monotonic()
    host = 'source' if args.phase=='produce' else 'destination'
    assertions = []
    with httpx.Client(base_url='http://'+host+':8080', timeout=10, trust_env=False) as c:
        healthy(c)
        if args.phase=='produce':
            fx = fixture()
            if stage==1: fx['restaurants'][0].pop('combinable')
            if stage<3: fx['restaurants'][0].pop('manager_user_ids')
            require(c.post('/_test/reset', json=fx), 204)
            tokens = {who: require(c.post('/auth/login', json={'email': who+'@stage3.test',
                      'password': PASSWORD}), 200)['token'] for who in ('diner', 'manager')}
            tokens['second'] = require(c.post('/auth/login', json={'email': 'diner@stage3.test',
                                       'password': PASSWORD}), 200)['token']
            originals = []
            def write(path, body, key, who='diner'):
                receipt = require(c.post(path, json=body, headers=headers(tokens[who], key)), 201)
                originals.append({'path': path, 'body': body, 'key': key, 'who': who, 'receipt': receipt})
                return receipt
            if stage>=3:
                write('/restaurants/r/policies', policy('2030-01-08'), 'source-policy', 'manager')
            body = {'restaurant_id': 'r', 'table_id': 'a', 'starts_at_local': '2030-01-01T18:00',
                    'party_size': 2, 'accepted_terms': {'untrusted': 'ignored'},
                    'revision': -900, 'expected_revision': False, 'unknown': ['雪', {'n': 123456789012345678901}]}
            if stage==1:
                # A future-recognized selector must remain ignored in a legacy receipt.
                body['table_ids'] = ['b', 'c']
            first = write('/reservations', body, 'source-create')
            second = write('/reservations', {'restaurant_id': 'r', 'table_id': 'c',
                           'starts_at_local': '2030-01-01T22:00', 'party_size': 2}, 'source-second')
            ref = first['reference']
            require(c.patch('/reservations/'+ref, json={'party_size': 3, 'starts_at_local': '2030-01-01T19:00'},
                            headers=headers(tokens['diner'])), 200)
            moves = {'moves': [{'reference': ref, 'table_id': 'b'},
                               {'reference': second['reference'], 'table_id': 'a'}]}
            if stage<3:
                # Later-stage optimistic concurrency is not retroactive identity validation.
                for move in moves['moves']: move['expected_revision'] = False
            write('/reservation-moves', moves, 'source-moves')
            require(c.patch('/reservations/'+ref, json={'party_size': 4}, headers=headers(tokens['diner'])), 200)
            state = {'tokens': tokens, 'originals': originals, 'anchor_reference': ref, 'source_stage': stage}
            if stage>=3:
                agreement = write('/series', {'anchor_reference': ref, 'count': 3, 'interval_weeks': 1}, 'source-series')
                sid = agreement['series_id']; member = agreement['occurrences'][1]['reference']
                require(c.patch('/reservations/'+member, json={'party_size': 5}, headers=headers(tokens['diner'])), 200)
                require(c.patch('/reservations/'+member, json={'party_size': 4}, headers=headers(tokens['diner'])), 200)
                require(c.post('/reservations/'+agreement['occurrences'][2]['reference']+'/cancel', headers=headers(tokens['diner'])), 200)
                if stage>=4:
                    # Repair the eligible anchor and the reverted permanent
                    # exception together; operator seating must not erase flags.
                    plan=write('/restaurants/r/replans',{'table_id':'b','from':'2030-01-01T00:00:00Z',
                               'to':'2030-01-16T00:00:00Z'},'source-plan','manager')
                    write('/restaurants/r/replans/'+plan['plan_id']+'/apply',{},'source-apply','manager')
                    before=require(c.get('/series/'+sid,headers=headers(tokens['diner'])),200)
                    write('/series/'+sid+'/amend',{'expected_revision':before['revision'],
                          'from_index':0,'local_time':'20:00'},'source-amend')
                    state['pending_plan']=write('/restaurants/r/replans',{'table_id':'c',
                        'from':'2035-01-01T18:00:00Z','to':'2035-01-01T19:00:00Z'},'pending-plan','manager')
                state['series'] = require(c.get('/series/'+sid, headers=headers(tokens['diner'])), 200)
                state['policies'] = require(c.get('/restaurants/r/policies'), 200)
            current = require(c.get('/reservations', headers=headers(tokens['diner'])), 200)['reservations']
            state['records'] = {b['reference']: b for b in current}
            if stage>=3:
                state['histories'] = {ref: require(c.get('/reservations/'+ref+'/history', headers=headers(tokens['diner'])), 200) for ref in state['records']}
                state['decisions'] = {ref: require(c.get('/reservations/'+ref+'/decision', headers=headers(tokens['diner'])), 200) for ref in state['records']}
            export = c.get('/_test/export'); require(export, 200)
            # Ordinary JSON carrier serialization, never copying internal objects.
            raw = json.dumps(export.json(), ensure_ascii=True, allow_nan=False).encode()
            (root/'snapshot.json').write_bytes(raw)
            (root/'client.json').write_text(json.dumps(state, ensure_ascii=True))
            assertions += ['populated source accounts, multiple tokens, amended records, immutable create and batch receipts',
                           'source>=3 also published policy, authentic adoption, permanent reverted exception, cancelled member']
        else:
            raw = (root/'snapshot.json').read_bytes(); state = json.loads((root/'client.json').read_text())
            tokens = state['tokens']; ref = state['anchor_reference']
            # Fresh destination has its own data and token; replacement must erase both.
            require(c.post('/_test/reset', json=fixture()), 204)
            revoked = require(c.post('/auth/login', json={'email': 'other@stage3.test', 'password': PASSWORD}), 200)['token']
            for token in tokens.values():
                assert c.get('/reservations', headers=headers(token)).status_code == 401
            require(c.post('/_test/import', content=raw, headers={'Content-Type': 'application/json'}), 204)
            assert c.get('/reservations', headers=headers(revoked)).status_code == 401
            got = require(c.get('/reservations', headers=headers(tokens['diner'])), 200)['reservations']
            assert set(x['reference'] for x in got) == set(state['records'])
            for record in got:
                old = state['records'][record['reference']]
                for key, value in old.items(): assert record[key] == value, (record['reference'], key)
                assert 'revision' in record and 'accepted_terms' in record and 'table_ids' in record
            for request in state['originals']:
                retry = c.post(request['path'], json=request['body'], headers=headers(tokens[request['who']], request['key']))
                assert require(retry, 200) == request['receipt']
            assert require(c.post('/auth/login', json={'email': 'diner@stage3.test', 'password': PASSWORD}), 200)['user_id'] == 'diner'
            assert len(require(c.get('/reservations', headers=headers(tokens['second'])), 200)['reservations']) == len(got)
            assertions += ['old login and multiple tokens valid, destination token revoked',
                           'old identities/current values and every original receipt exactly retained']
            before_anchor = require(c.get('/reservations/'+ref, headers=headers(tokens['diner'])), 200)
            before_history = require(c.get('/reservations/'+ref+'/history', headers=headers(tokens['diner'])), 200)
            if stage<3:
                # These producers never recorded history: importing their current
                # state cannot invent historical creation/change/cancellation events.
                for old_ref in state['records']:
                    h = require(c.get('/reservations/'+old_ref+'/history', headers=headers(tokens['diner'])), 200)
                    assert h['entries'] == [], h
                # This legacy fixture had no manager declaration. Migration
                # cannot invent a manager grant from the user's display name.
                assert c.post('/restaurants/r/policies', json=policy('2030-01-08'),
                              headers=headers(tokens['manager'], 'target-policy')).status_code == 403
                agreement = require(c.post('/series', json={'anchor_reference': ref, 'count': 3, 'interval_weeks': 1},
                                           headers=headers(tokens['diner'], 'target-series')), 201)
                assert agreement['occurrences'][0]['reservation'] == before_anchor
                assert require(c.get('/reservations/'+ref+'/history', headers=headers(tokens['diner'])), 200) == before_history
                for occurrence in agreement['occurrences'][1:]:
                    history = require(c.get('/reservations/'+occurrence['reference']+'/history', headers=headers(tokens['diner'])), 200)
                    assert len(history['entries']) == 1 and history['entries'][0]['event'] == 'created'
                    assert occurrence['reservation']['accepted_terms']['policy_version'] == 0
                assertions.append('legacy history absent, adopted anchor unchanged, generated history authentic under policy0; no invented manager grant')
            else:
                assert require(c.get('/restaurants/r/policies'), 200) == state['policies']
                assert require(c.get('/series/'+state['series']['series_id'], headers=headers(tokens['diner'])), 200) == state['series']
                assert state['series']['revision'] == (6 if stage>=4 else 4)
                assert [o['exception'] for o in state['series']['occurrences']] == [False, True, False]
                for old_ref in state['records']:
                    for suffix, key in [('history', 'histories'), ('decision', 'decisions')]:
                        assert require(c.get('/reservations/'+old_ref+'/'+suffix, headers=headers(tokens['diner'])), 200) == state[key][old_ref]
                assertions.append('final policies, authentic histories/decisions, revision4 series, permanent exception and cancellation preserved')
                agreement=state['series']
            if stage>=4:
                pending=state['pending_plan']
                applied=require(c.post('/restaurants/r/replans/'+pending['plan_id']+'/apply',json={},
                                headers=headers(tokens['manager'],'target-pending-apply')),201)
                assert applied['restaurant_revision']==pending['restaurant_revision']+1
                # Source repair is an actual closure, not merely retained plans.
                refused=c.post('/reservations',json={'restaurant_id':'r','table_id':'b',
                    'starts_at_local':'2030-01-02T19:00','party_size':2},headers=headers(tokens['diner'],'source-closed'))
                assert refused.status_code==409 and refused.json()['error']['code']=='table_unavailable'
                assertions.append('source plan/apply/amend receipts and pending plan retained; imported closure authoritative')
            # Every source edge supports a genuine new Stage4 series amendment.
            old_agreement=require(c.get('/series/'+agreement['series_id'],headers=headers(tokens['diner'])),200)
            amended=require(c.post('/series/'+agreement['series_id']+'/amend',json={
                'expected_revision':old_agreement['revision'],'from_index':0,'local_time':'21:00'},
                headers=headers(tokens['diner'],'target-amend')),201)
            assert amended['revision']==old_agreement['revision']+1
            for old,new in zip(old_agreement['occurrences'],amended['occurrences'],strict=True):
                assert new['reference']==old['reference'] and new['exception']==old['exception']
                if old['exception'] or old['reservation']['status']=='cancelled':
                    assert new==old
                else:
                    assert new['reservation']['starts_at_local']==old['reservation']['starts_at_local'][:11]+'21:00'
                    assert new['reservation']['table_ids']==old['reservation']['table_ids']
            assertions.append('new Stage4 amendment preserves imported seating, authentic original dates, exceptions and cancellations')
            # A Stage1 fixture had no pairs; migration must not invent them.
            selection = ['a'] if stage==1 else ['a', 'b']
            fresh = require(c.post('/reservations', json={'restaurant_id': 'r', 'table_ids': selection,
                        'starts_at_local': '2031-01-01T18:00', 'party_size': 2 if stage==1 else 150}, headers=headers(tokens['diner'], 'target-new-selection')), 201)
            assert fresh['table_ids'] == (['a'] if stage==1 else ['b', 'a']) and fresh['revision'] == 1
            # Replacement again removes every post-import write and session.
            require(c.post('/_test/import', content=raw, headers={'Content-Type': 'application/json'}), 204)
            assert len(require(c.get('/reservations', headers=headers(tokens['diner'])), 200)['reservations']) == len(state['records'])
            assertions.append('new target selection accepted and repeated replacement restores original source state')
    print(json.dumps({'id': 'D411-stage4-producer-authenticity', 'kind': 'PRODUCER_REMOVAL_INTEGRATION',
          'phase': args.phase, 'source_stage': stage, 'destination_stage': target,
          'snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'snapshot_bytes': len(raw),
          'expected': 'Authentic state and exact immutable receipts survive detached ordinary JSON replacement',
          'observed': assertions, 'outcome': 'PASS', 'duration_s': time.monotonic()-tick}))


if __name__=='__main__': main()
