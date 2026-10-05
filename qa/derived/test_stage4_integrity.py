"""D415: independent semantic corruption, bound after observing schema4.

All fixtures are created over HTTP. Native journal is retained unchanged and
only the outer checksum is recalculated. The small-value carrier adapter is
independent of the product and must pass its own valid roundtrip control.
"""
import copy
import json
import pytest

from adapters.stage4_carrier import exported, seal
from derived.test_stage4 import (world4, preview, apply, closure, require, amend,
                                setup, booking, adopt, patch, series, publish, policy)
from derived.test_stage1 import headers, assert_error, snapshot


MUTATIONS = ['plan-restaurant', 'plan-unknown-table', 'plan-reversed-interval',
    'plan-altered-closure', 'plan-revision-low', 'plan-revision-high',
    'plan-missing-unmoved', 'plan-duplicate-reference', 'plan-foreign-reference',
    'plan-invalid-pair', 'plan-closed-seat', 'plan-collision', 'plan-nonoptimal-rank',
    'plan-wrong-moved', 'plan-wrong-unused', 'plan-applied-flag', 'pending-applied-flag',
    'reassigned-missing', 'reassigned-extra', 'reassigned-plan-id', 'reassigned-before',
    'reassigned-terms', 'reassigned-time', 'unmoved-revision', 'unmoved-history',
    'closure-removed', 'closure-changed', 'closure-foreign',
    'restaurant-revision-low', 'restaurant-revision-high',
    'series-application-low', 'series-application-high', 'operator-invents-exception',
    'operator-erases-exception', 'scheduled-date', 'amend-missing-event',
    'amend-wrong-terms', 'amend-excluded-member', 'amend-extra-revision',
    'preview-receipt-owner', 'preview-receipt-body', 'preview-receipt-response',
    'apply-receipt-plan', 'apply-receipt-current', 'amend-receipt-body',
    'amend-receipt-response', 'noop-amend-receipt-revision']


def rich(c, tok):
    publish(c, tok, policy('2030-01-15'), key='new-policy')
    _, anchor = booking(c, tok, key='anchor')
    _, agreement = adopt(c, tok, anchor['reference'], key='adopt', count=4)
    refs = [o['reference'] for o in agreement['occurrences']]
    require(patch(c, tok, refs[1], {'party_size':3}), 200)
    require(patch(c, tok, refs[1], {'party_size':2}), 200)
    require(c.post('/reservations/'+refs[3]+'/cancel', headers=headers(tok['diner'])), 200)
    _, other = booking(c, tok, key='unmoved', table='c')
    plan = preview(c, tok, closure('a','2030-01-01T00:00:00Z','2030-01-23T00:00:00Z'), key='preview')
    assert len(plan['assignments']) == 4 and plan['moved_count'] == 3
    apply(c, tok, plan, key='apply')
    now = series(c, tok, agreement['series_id'])
    require(amend(c, tok, now, key='amend'))
    now = series(c, tok, agreement['series_id'])
    require(amend(c, tok, now, key='noop-amend'))
    empty = preview(c, tok, closure('c','2040-01-01T00:00:00Z','2040-01-01T01:00:00Z'), key='empty-preview')
    assert empty['moved_count'] == 0
    apply(c, tok, empty, key='empty-apply')
    pending = preview(c, tok, closure('a','2041-01-01T00:00:00Z','2041-01-01T01:00:00Z'), key='pending')
    return {'refs':refs, 'sid':agreement['series_id'], 'pid':plan['plan_id'],
            'pending':pending['plan_id'], 'other':other['reference']}


def corrupt(s, ids, name):
    p = s['plans'][ids['pid']]; response = p['response']; refs=ids['refs']
    assignment = lambda ref: next(x for x in response['assignments'] if x['reference']==ref)
    a = s['series'][ids['sid']]
    h = s['histories'][refs[0]]
    reassigned = next(x for x in h if x['event']=='reassigned')
    receipt = lambda key: next(x for x in s['receipts'] if x['key']==key)
    if name=='plan-restaurant': p['restaurant_id']='foreign'
    elif name=='plan-unknown-table': response['closure']['table_id']='unknown'
    elif name=='plan-reversed-interval': response['closure']['to']=response['closure']['from']
    elif name=='plan-altered-closure': response['closure']['to']='2030-01-24T00:00:00Z'
    elif name=='plan-revision-low': response['restaurant_revision']-=1
    elif name=='plan-revision-high': response['restaurant_revision']+=1
    elif name=='plan-missing-unmoved': response['assignments'].remove(assignment(ids['other']))
    elif name=='plan-duplicate-reference': response['assignments'].append(copy.deepcopy(response['assignments'][0]))
    elif name=='plan-foreign-reference': response['assignments'][0]['reference']='ABSENT01'
    elif name=='plan-invalid-pair': assignment(refs[0])['table_ids']=['a','c']
    elif name=='plan-closed-seat': assignment(refs[0])['table_ids']=['a']
    elif name=='plan-collision': assignment(refs[0])['table_ids']=['c']
    elif name=='plan-nonoptimal-rank': assignment(refs[2])['table_ids']=['c']
    elif name=='plan-wrong-moved': response['moved_count']+=1
    elif name=='plan-wrong-unused': response['unused_seats']+=1
    elif name=='plan-applied-flag': p['applied']=False
    elif name=='pending-applied-flag': s['plans'][ids['pending']]['applied']=True
    elif name=='reassigned-missing': h.remove(reassigned)
    elif name=='reassigned-extra': h.append(copy.deepcopy(reassigned))
    elif name=='reassigned-plan-id': reassigned['plan_id']=ids['pending']
    elif name=='reassigned-before': reassigned['changes'][0]['from']=['c']
    elif name=='reassigned-terms': reassigned['accepted_terms']['capacities']['b']=99
    elif name=='reassigned-time': s['reservations'][refs[1]]['starts_at_local']='2030-01-08T19:00'
    elif name=='unmoved-revision': s['reservations'][ids['other']]['revision']+=1
    elif name=='unmoved-history': s['histories'][ids['other']].append(copy.deepcopy(reassigned))
    elif name=='closure-removed': s['closures'].pop(0)
    elif name=='closure-changed': s['closures'][0]['to']='2030-01-24T00:00:00Z'
    elif name=='closure-foreign': s['closures'][0]['restaurant_id']='foreign'
    elif name=='restaurant-revision-low': s['restaurant_revisions']['r']-=1
    elif name=='restaurant-revision-high': s['restaurant_revisions']['r']+=1
    elif name=='series-application-low': a['revision']-=1
    elif name=='series-application-high': a['revision']+=2
    elif name=='operator-invents-exception': a['occurrences'][0]['exception']=True
    elif name=='operator-erases-exception': a['occurrences'][1]['exception']=False
    elif name=='scheduled-date': a['occurrences'][0]['scheduled_date']='2030-01-02'
    elif name=='amend-missing-event': h.pop()
    elif name=='amend-wrong-terms': s['histories'][refs[2]][-1]['accepted_terms']['policy_version']=0
    elif name=='amend-excluded-member': s['reservations'][refs[1]]['starts_at_local']='2030-01-08T20:00'
    elif name=='amend-extra-revision': s['reservations'][refs[2]]['revision']+=1
    elif name=='preview-receipt-owner': receipt('preview')['user_id']='diner'
    elif name=='preview-receipt-body': receipt('preview')['body']['table_id']='b'
    elif name=='preview-receipt-response': receipt('preview')['response']['assignments'].reverse()
    elif name=='apply-receipt-plan': receipt('apply')['response']['plan_id']=ids['pending']
    elif name=='apply-receipt-current': receipt('apply')['response']['reservations'][0]['starts_at_local']='2030-01-01T20:00'
    elif name=='amend-receipt-body': receipt('amend')['body']['local_time']='21:00'
    elif name=='amend-receipt-response': receipt('amend')['response']['revision']+=1
    elif name=='noop-amend-receipt-revision': receipt('noop-amend')['response']['revision']+=1
    else: raise AssertionError(name)


@pytest.mark.parametrize('mutation', MUTATIONS, ids=['D415-'+x for x in MUTATIONS])
def test_D415_authentic_stage4_snapshot_integrity(world4, mutation, record_property):
    """Checksum-valid inconsistent plans, receipts, closures or histories reject422 without mutating destination."""
    c,tok=world4; ids=rich(c,tok); original,state=exported(c)
    require(c.post('/_test/import',json=original,timeout=10),204)
    repacked=copy.deepcopy(original); seal(repacked,state)
    require(c.post('/_test/import',json=repacked,timeout=10),204)
    assert c.get('/_test/export').json()==original, 'Independent carrier must preserve valid semantics'
    altered=copy.deepcopy(state); corrupt(altered,ids,mutation)
    assert altered!=state and altered['audit']==state['audit']
    broken=copy.deepcopy(original); seal(broken,altered)
    dest=setup(c); before=snapshot(c)
    refused=c.post('/_test/import',json=broken,timeout=10)
    assert_error(refused,422,'validation_failed'); assert snapshot(c)==before
    require(c.post('/_test/import',json=original,timeout=10),204)
    assert c.get('/reservations',headers=headers(dest['diner'])).status_code==401
    assert c.get('/reservations',headers=headers(tok['diner'])).status_code==200
    for old in state['receipts']:
        r=c.request(old['method'],old['path'],json=old['body'],headers=headers(tok[old['user_id']],old['key']))
        assert r.status_code==200 and r.json()==old['response']
    require(amend(c,tok,series(c,tok,ids['sid']),time='21:00'))
    record_property('observed',json.dumps({'mutation':mutation,'raw_control':204,'repacked_control':204,
        'invalid_import':422,'exact_destination_nonmutation':True,'authentic_journal_unchanged':True,
        'original_receipts_replayed':len(state['receipts']),'new_amendment':201}))
