"""Valid local calendar limits must remain usable with explicit-offset zones."""
import json
import pytest
from derived.test_stage1 import world,fixture,headers


@pytest.mark.parametrize('date,zone,opening,closing,start',[
    ('0001-01-01','UTC','00:00','01:00','00:00'),
    ('0001-01-01','Etc/GMT-1','00:00','01:00','00:00'),
    ('9999-12-31','UTC','22:00','23:59','23:00'),
    ('9999-12-31','Etc/GMT+1','22:00','23:59','23:00'),
],ids=['D122-min-utc','D122-min-plus01','D122-max-utc','D122-max-minus01'])
def test_D122_local_calendar_limits_keep_valid_offset_bookings(world,date,zone,opening,closing,start,record_property):
    """A valid local date and IANA fixed-offset zone yield200 availability and201 booking when its whole real duration fits local opening hours, including local calendar extrema."""
    c,_=world;fx=fixture();rest=fx['restaurants'][0]
    rest['timezone']=zone;rest['reservation_duration_minutes']=30
    rest['opening_hours']=[{'weekday':d,'opens':opening,'closes':closing} for d in 'mon tue wed thu fri sat sun'.split()]
    reset=c.post('/_test/reset',json=fx);assert reset.status_code==204
    login=c.post('/auth/login',json={'email':'u@derived.test','password':'synthetic-password'});assert login.status_code==200
    token=login.json()['token']
    available=c.get('/availability',params={'restaurant_id':'r','date':date,'party_size':2})
    value={'restaurant_id':'r','table_id':'a','starts_at_local':date+'T'+start,'party_size':2}
    created=c.post('/reservations',json=value,headers=headers(token,'calendar-edge'))
    record_property('observed',json.dumps({'date':date,'zone':zone,'reset_status':reset.status_code,
        'availability_status':available.status_code,'create_status':created.status_code,
        'availability_body':available.json(),'create_body':created.json(),'health':c.get('/health').status_code}))
    assert available.status_code==200,available.text
    assert value['starts_at_local'] in [s['starts_at_local'] for s in available.json()['slots']]
    assert created.status_code==201,created.text
    assert created.json()['starts_at_local']==value['starts_at_local']
    saved=c.get('/_test/export');assert saved.status_code==200
    assert c.post('/_test/import',content=saved.content,headers={'Content-Type':'application/json'},timeout=10).status_code==204
    replay=c.post('/reservations',json=value,headers=headers(token,'calendar-edge'))
    assert replay.status_code==200 and replay.json()==created.json()
