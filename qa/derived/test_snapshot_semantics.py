"""Explicit adapter for the reviewed Stage1 payload+sha256 state representation.

This independently recomputes the ordinary JSON checksum after a semantic
corruption, so rejection cannot be attributed only to an unchanged digest.
The frozen transparent B003 selector is retained and runs separately.
"""
import copy
import hashlib
import json

import pytest
from test_stage1 import world, body, headers, snapshot, assert_error


def seal(envelope):
    state=envelope['state']
    assert set(state)=={'payload','sha256'}, 'QA adapter requires review for changed opaque representation'
    raw=json.dumps(state['payload'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    state['sha256']=hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('corruption',['receipt-party','receipt-start','receipt-end','receipt-body','receipt-move-order'],
                         ids=['D116-receipt-party','D116-receipt-start','D116-receipt-end','D116-receipt-body','D116-batch-order'])
def test_D116_checksum_valid_semantic_corruption_is_rejected(world,corruption,record_property):
    """A matching checksum cannot authorize inconsistent original response/body/times or batch input ordering; import422 preserves destination exactly."""
    c,token=world
    first=c.post('/reservations',json=body(),headers=headers(token,'original'))
    assert first.status_code==201
    if corruption=='receipt-move-order':
        second=c.post('/reservations',json={**body(),'table_id':'b'},headers=headers(token,'second'))
        assert second.status_code==201
        moves={'moves':[{'reference':first.json()['reference'],'table_id':'b'},
                        {'reference':second.json()['reference'],'table_id':'a'}]}
        assert c.post('/reservation-moves',json=moves,headers=headers(token,'moves')).status_code==201
    exported=c.get('/_test/export').json()
    # Control: this independently serialized ordinary state is already canonical
    # for the small integer fixture. A selector/checksum mismatch is QA applicability.
    control=copy.deepcopy(exported);seal(control)
    assert control['state']['sha256']==exported['state']['sha256'],'QA checksum adapter mismatch'
    assert c.post('/_test/import',json=control).status_code==204
    before=snapshot(c)
    broken=copy.deepcopy(control)
    receipts=broken['state']['payload']['receipts']
    receipt=next(x for x in receipts if x['key']==('moves' if corruption=='receipt-move-order' else 'original'))
    if corruption=='receipt-party':receipt['response']['party_size']=3
    elif corruption=='receipt-start':receipt['response']['starts_at']='2030-01-01T19:00:00+00:00'
    elif corruption=='receipt-end':receipt['response']['ends_at']='2030-01-01T18:00:00+00:00'
    elif corruption=='receipt-body':receipt['body']['party_size']=3
    else:receipt['response']['reservations'].reverse()
    seal(broken)
    response=c.post('/_test/import',json=broken,timeout=10)
    unchanged=snapshot(c)==before
    record_property('observed',json.dumps({'import_status':response.status_code,'destination_unchanged':unchanged,
                                         'checksum_recomputed':True,'valid_control_import':204}))
    assert_error(response,422,'validation_failed')
    assert unchanged
