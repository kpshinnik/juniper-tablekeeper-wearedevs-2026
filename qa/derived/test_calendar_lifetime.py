"""Offset calendar boundaries across occupancy, mutation and replacement lifetime."""
import json
import pytest
from derived.test_stage1 import world, fixture, headers, snapshot, assert_error


@pytest.mark.parametrize('date,zone,opens,closes,start,end,adjacent,offset,past', [
    ('0001-01-01','Etc/GMT-1','00:00','01:00','00:00','00:30','00:30','+01:00',True),
    ('9999-12-31','Etc/GMT+1','22:00','23:59','23:00','23:30','22:30','-01:00',False),
], ids=['D123-min-plus01-lifetime','D123-max-minus01-lifetime'])
def test_D123_offset_extrema_full_booking_lifetime(world,date,zone,opens,closes,start,end,adjacent,offset,past,record_property):
    """Valid offset calendar extrema preserve exact timestamps, UTC half-open occupancy, list order, real-clock cutoff, editable amendments/batches/cancellation and original receipts after ordinary JSON replacement import."""
    c,_=world
    fx=fixture();r=fx['restaurants'][0]
    r['timezone']=zone;r['reservation_duration_minutes']=30
    r['opening_hours']=[{'weekday':d,'opens':opens,'closes':closes} for d in 'mon tue wed thu fri sat sun'.split()]
    assert c.post('/_test/reset',json=fx,timeout=10).status_code==204
    login=c.post('/auth/login',json={'email':'u@derived.test','password':'synthetic-password'})
    assert login.status_code==200
    token=login.json()['token'];auth=headers(token)
    value={'restaurant_id':'r','table_id':'a','starts_at_local':date+'T'+start,'party_size':2}
    created=c.post('/reservations',json=value,headers=headers(token,'edge-original'))
    assert created.status_code==201,created.text
    original=created.json();ref=original['reference']
    assert original['starts_at']==date+'T'+start+':00'+offset
    assert original['ends_at']==date+'T'+end+':00'+offset
    assert c.get('/reservations/'+ref,headers=auth).json()==original

    available=c.get('/availability',params={'restaurant_id':'r','date':date,'party_size':2})
    assert available.status_code==200,available.text
    chosen=next(s for s in available.json()['slots'] if s['starts_at_local']==value['starts_at_local'])
    assert 'a' not in chosen['available_table_ids'] and 'b' in chosen['available_table_ids']
    before=snapshot(c)
    assert_error(c.post('/reservations',json=value,headers=headers(token,'edge-conflict')),409,'table_unavailable')
    assert snapshot(c)==before
    other_value=dict(value,starts_at_local=date+'T'+adjacent)
    other=c.post('/reservations',json=other_value,headers=headers(token,'edge-adjacent'))
    assert other.status_code==201,other.text
    other_original=other.json();other_ref=other_original['reference']
    listed=c.get('/reservations',headers=auth)
    assert listed.status_code==200
    assert [x['reference'] for x in listed.json()['reservations']]==([other_ref,ref] if past else [ref,other_ref])
    replay=c.post('/reservations',json=value,headers=headers(token,'edge-original'))
    assert replay.status_code==200 and replay.json()==original

    move_body={'moves':[{'reference':ref,'table_id':'a'},{'reference':other_ref,'table_id':'b'}]}
    move_receipt=None
    if past:
        before=snapshot(c)
        assert_error(c.patch('/reservations/'+ref,json={'party_size':1},headers=auth),409,'cutoff_passed')
        assert snapshot(c)==before
        assert_error(c.post('/reservations/'+ref+'/cancel',json={},headers=auth),409,'cutoff_passed')
        assert snapshot(c)==before
        assert_error(c.post('/reservation-moves',json=move_body,headers=headers(token,'edge-moves')),409,'cutoff_passed')
        assert snapshot(c)==before
    else:
        amended=c.patch('/reservations/'+ref,json={'table_id':'b','party_size':3},headers=auth)
        assert amended.status_code==200,amended.text
        assert amended.json()['reservation_id']==original['reservation_id']
        assert amended.json()['starts_at']==original['starts_at']
        assert amended.json()['ends_at']==original['ends_at']
        moved=c.post('/reservation-moves',json=move_body,headers=headers(token,'edge-moves'))
        assert moved.status_code==201,moved.text
        move_receipt=moved.json()
        assert [x['reference'] for x in move_receipt['reservations']]==[ref,other_ref]
        cancelled=c.post('/reservations/'+ref+'/cancel',json={},headers=auth)
        assert cancelled.status_code==200 and cancelled.json()['status']=='cancelled'
        again=c.post('/reservations/'+ref+'/cancel',json={},headers=auth)
        assert again.status_code==200 and again.json()==cancelled.json()

    current=c.get('/reservations',headers=auth).json()
    exported=c.get('/_test/export',timeout=10)
    assert exported.status_code==200
    carrier=json.dumps(exported.json())
    assert c.post('/_test/reset',json={'users':[],'restaurants':[],'reservations':[]},timeout=10).status_code==204
    imported=c.post('/_test/import',content=carrier,headers={'Content-Type':'application/json'},timeout=10)
    assert imported.status_code==204,imported.text
    assert c.get('/reservations',headers=auth).json()==current
    for key,body,receipt in [('edge-original',value,original),('edge-adjacent',other_value,other_original)]:
        before=snapshot(c)
        retry=c.post('/reservations',json=body,headers=headers(token,key))
        assert retry.status_code==200 and retry.json()==receipt
        assert snapshot(c)==before
    if move_receipt is not None:
        before=snapshot(c)
        retry=c.post('/reservation-moves',json=move_body,headers=headers(token,'edge-moves'))
        assert retry.status_code==200 and retry.json()==move_receipt
        assert snapshot(c)==before
    assert c.get('/reservations/'+ref,headers=auth).json()['status']==('confirmed' if past else 'cancelled')
    assert c.post('/_test/import',content=carrier,headers={'Content-Type':'application/json'},timeout=10).status_code==204
    assert c.get('/reservations',headers=auth).json()==current
    assert c.post('/auth/login',json={'email':'u@derived.test','password':'synthetic-password'}).status_code==200
    assert c.get('/health').json()=={'status':'ok'}
    record_property('observed',json.dumps({'zone':zone,'date':date,'starts_at':original['starts_at'],
        'ends_at':original['ends_at'],'ordinary_json_import_status':imported.status_code,
        'original_receipts_replayed':3 if move_receipt else 2,'current_status':'confirmed' if past else 'cancelled',
        'adjacent_booking_created':True,'past_cutoff_rejections':3 if past else 0}))
