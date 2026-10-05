"""Strict RFC3339 formatting cannot round or overflow valid IANA instants."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import pytest
from derived.test_stage1 import world,fixture,headers,snapshot,assert_error
from derived.test_historical_timestamps import RFC3339


def exact_instant(dt):
    """Independent integer coordinate; no UTC datetime conversion or timestamp()."""
    local=((dt.toordinal()-1)*86400+dt.hour*3600+dt.minute*60+dt.second)*1000000+dt.microsecond
    offset=dt.utcoffset()
    assert offset is not None
    return local-((offset.days*86400+offset.seconds)*1000000+offset.microseconds)


def check_stamp(stamp,expected):
    assert RFC3339.fullmatch(stamp),'Non-RFC3339 timestamp: '+stamp
    assert exact_instant(datetime.fromisoformat(stamp))==expected,'Timestamp changed the exact IANA instant: '+stamp


@pytest.mark.parametrize('zone,date,opens,closes,start,past',[
    ('Europe/Berlin','0001-01-01','00:00','01:00','00:00',True),
    ('America/New_York','0001-01-01','00:00','01:00','00:00',True),
    ('Europe/Berlin','9999-12-31','22:00','23:59','23:00',False),
    ('America/New_York','9999-12-31','22:00','23:59','23:00',False),
],ids=['D125-Berlin-min-second-offset','D125-NewYork-min-second-offset','D125-Berlin-max','D125-NewYork-max'])
def test_D125_historical_offsets_and_calendar_limits_keep_exact_rfc3339_lifetime(world,zone,date,opens,closes,start,past,record_property):
    """At both local calendar limits RFC3339 rendering retains exact IANA instants/local fields, occupancy, editable or cutoff behavior and immutable receipts after replacement; historical second offsets at year0001 cannot be rounded or overflowed."""
    c,_=world;fx=fixture();r=fx['restaurants'][0]
    r['timezone']=zone;r['reservation_duration_minutes']=30
    r['opening_hours']=[{'weekday':day,'opens':opens,'closes':closes} for day in 'mon tue wed thu fri sat sun'.split()]
    assert c.post('/_test/reset',json=fx,timeout=10).status_code==204
    login=c.post('/auth/login',json={'email':'u@derived.test','password':'synthetic-password'})
    assert login.status_code==200
    token=login.json()['token'];auth=headers(token,'cross-boundary')
    local=date+'T'+start
    expected=exact_instant(datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(zone),fold=0))
    value={'restaurant_id':'r','table_id':'a','starts_at_local':local,'party_size':2}
    availability=c.get('/availability',params={'restaurant_id':'r','date':date,'party_size':2})
    created=c.post('/reservations',json=value,headers=auth)
    record_property('observed',json.dumps({'zone':zone,'local':local,'exact_utc_microseconds_from_year1':expected,
        'availability_status':availability.status_code,'create_status':created.status_code,
        'create_body':created.json(),'health_status':c.get('/health').status_code}))
    assert availability.status_code==200,availability.text
    assert created.status_code==201,created.text
    receipt=created.json();ref=receipt['reference']
    slot=next(s for s in availability.json()['slots'] if s['starts_at_local']==local)
    check_stamp(slot['starts_at'],expected)
    check_stamp(receipt['starts_at'],expected)
    check_stamp(receipt['ends_at'],expected+30*60*1000000)
    assert receipt['starts_at_local']==local
    assert c.get('/restaurants/r').json()['timezone']==zone
    assert c.get('/reservations/'+ref,headers=auth).json()==receipt
    assert c.get('/reservations',headers=auth).json()=={'reservations':[receipt]}
    before=snapshot(c)
    assert_error(c.post('/reservations',json=value,headers=headers(token,'overlap')),409,'table_unavailable')
    assert snapshot(c)==before
    if past:
        assert_error(c.patch('/reservations/'+ref,json={'table_id':'b'},headers=auth),409,'cutoff_passed')
        assert_error(c.post('/reservations/'+ref+'/cancel',json={},headers=auth),409,'cutoff_passed')
        assert snapshot(c)==before
    else:
        amended=c.patch('/reservations/'+ref,json={'table_id':'b'},headers=auth)
        assert amended.status_code==200,amended.text
        assert amended.json()['starts_at_local']==local
        check_stamp(amended.json()['starts_at'],expected)
        check_stamp(amended.json()['ends_at'],expected+30*60*1000000)
        cancelled=c.post('/reservations/'+ref+'/cancel',json={},headers=auth)
        assert cancelled.status_code==200 and cancelled.json()['status']=='cancelled'
    current=c.get('/reservations/'+ref,headers=auth).json()
    exported=c.get('/_test/export',timeout=10)
    assert exported.status_code==200
    carrier=json.dumps(exported.json(),allow_nan=False)
    assert c.post('/_test/reset',json={'users':[],'restaurants':[],'reservations':[]},timeout=10).status_code==204
    restored=c.post('/_test/import',content=carrier,headers={'Content-Type':'application/json'},timeout=10)
    assert restored.status_code==204,restored.text
    assert c.get('/reservations/'+ref,headers=auth).json()==current
    before=snapshot(c)
    retried=c.post('/reservations',json=value,headers=auth)
    assert retried.status_code==200 and retried.json()==receipt
    assert snapshot(c)==before
    check_stamp(retried.json()['starts_at'],expected)
    check_stamp(retried.json()['ends_at'],expected+30*60*1000000)
    assert c.get('/health').json()=={'status':'ok'}
