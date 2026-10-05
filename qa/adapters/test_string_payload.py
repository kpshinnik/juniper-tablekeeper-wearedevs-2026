"""Explicit representation adaptation for a string-valued exact-JSON payload.

Original frozen B003 and derived snapshot tests remain unchanged and execute
separately. This only decodes/re-encodes the opaque state selector; expected422
and exact destination nonmutation remain required. Checksum controls and actual
semantic mutations are measured. No product source or numeric oracle is imported.
"""
import copy
import hashlib
import json
import pytest

from derived.test_stage1 import world,body,headers,snapshot,assert_error
from frozen.supplemental.test_boundaries import api,body as frozen_body,book,observe


def payload(envelope):
    raw=envelope['state']['payload']
    return json.loads(raw) if isinstance(raw,str) else raw


def seal(envelope,decoded):
    encoded=json.dumps(decoded,sort_keys=True,separators=(',',':'),ensure_ascii=True)
    state=envelope['state']
    state['payload']=encoded if isinstance(state['payload'],str) else decoded
    state['sha256']=hashlib.sha256(encoded.encode('ascii')).hexdigest()


@pytest.mark.parametrize('corruption',['receipt-party','receipt-start','receipt-end','receipt-body','receipt-move-order'],
                         ids=['D116-receipt-party','D116-receipt-start','D116-receipt-end','D116-receipt-body','D116-batch-order'])
def test_D116_checksum_valid_semantic_corruption_is_rejected(world,corruption,record_property):
    """Adapted selector: matching checksum cannot authorize inconsistent receipt fields or batch ordering;422 exact nonmutation."""
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
    control=copy.deepcopy(exported)
    raw=control['state']['payload']
    encoded=raw.encode('utf-8') if isinstance(raw,str) else json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    assert hashlib.sha256(encoded).hexdigest()==control['state']['sha256'],'QA checksum adapter mismatch'
    assert c.post('/_test/import',json=control).status_code==204
    before=snapshot(c)
    broken=copy.deepcopy(control);decoded=payload(broken)
    receipt=next(x for x in decoded['receipts'] if x['key']==('moves' if corruption=='receipt-move-order' else 'original'))
    if corruption=='receipt-party':receipt['response']['party_size']=3
    elif corruption=='receipt-start':receipt['response']['starts_at']='2030-01-01T19:00:00+00:00'
    elif corruption=='receipt-end':receipt['response']['ends_at']='2030-01-01T18:00:00+00:00'
    elif corruption=='receipt-body':receipt['body']['party_size']=3
    else:receipt['response']['reservations'].reverse()
    seal(broken,decoded)
    response=c.post('/_test/import',json=broken,timeout=10)
    unchanged=snapshot(c)==before
    record_property('adaptation_of','derived/test_snapshot_semantics.py::'+corruption)
    record_property('observed',json.dumps({'import_status':response.status_code,'destination_unchanged':unchanged,
                                         'checksum_recomputed':True,'valid_control_import':204,
                                         'payload_representation':type(broken['state']['payload']).__name__}))
    assert_error(response,422,'validation_failed')
    assert unchanged


def test_B003_cross_owner_receipt_rejected(api,record_property):
    """Adapted frozen B003 selector: Alice's key cannot point to Bob's confirmation;422 exact nonmutation."""
    c,t,_=api
    a=book(c,t['alice'],'alice-key',frozen_body());bbody=frozen_body();bbody['table_id']='t_2'
    b=book(c,t['bob'],'bob-key',bbody)
    assert a.status_code==b.status_code==201
    original=c.get('/_test/export').json();altered=copy.deepcopy(original)
    decoded=payload(altered);stack=[decoded];found=0
    while stack:
        item=stack.pop()
        if isinstance(item,dict):
            receipt_body=item.get('body')
            if 'body_json' in item and isinstance(item['body_json'],str):receipt_body=json.loads(item['body_json'])
            if item.get('response')==a.json() and receipt_body==frozen_body():item['response']=b.json();found+=1
            else:stack.extend(item.values())
        elif isinstance(item,list):stack.extend(item)
    assert found==1,'QA selector not applicable; do not infer product failure'
    seal(altered,decoded)
    result=c.post('/_test/import',json=altered)
    unchanged=c.get('/_test/export').json()==original
    record_property('adaptation_of','frozen/supplemental/test_boundaries.py::test_B003_cross_owner_receipt_rejected')
    observe(record_property,import_status=result.status_code,destination_unchanged=unchanged,checksum_recomputed=True)
    assert result.status_code==422 and unchanged
