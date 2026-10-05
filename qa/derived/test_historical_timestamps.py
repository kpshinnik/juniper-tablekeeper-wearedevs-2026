"""RFC3339 response timestamps remain valid for accepted historical IANA dates."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import re
import pytest
from derived.test_stage1 import world, fixture, headers

RFC3339=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$')


@pytest.mark.parametrize('zone',['Europe/Berlin','America/New_York'],ids=['D124-Berlin-historical','D124-NewYork-historical'])
def test_D124_historical_offsets_return_rfc3339_exact_instants(world,zone,record_property):
    """An accepted1800 local date returns RFC3339 timestamps and exact IANA instants in availability/create/lookup/retry/import, even when historical local mean time has offset seconds."""
    c,_=world;fx=fixture();fx['restaurants'][0]['timezone']=zone
    assert c.post('/_test/reset',json=fx,timeout=10).status_code==204
    login=c.post('/auth/login',json={'email':'u@derived.test','password':'synthetic-password'})
    assert login.status_code==200
    token=login.json()['token'];auth=headers(token,'historical')
    local='1800-01-01T18:00'
    value={'restaurant_id':'r','table_id':'a','starts_at_local':local,'party_size':2}
    availability=c.get('/availability',params={'restaurant_id':'r','date':'1800-01-01','party_size':2})
    created=c.post('/reservations',json=value,headers=auth)
    assert availability.status_code==200 and created.status_code==201
    slot=next(s for s in availability.json()['slots'] if s['starts_at_local']==local)
    receipt=created.json()
    record_property('observed',json.dumps({'zone':zone,'availability_start':slot['starts_at'],
        'created_start':receipt['starts_at'],'created_end':receipt['ends_at'],
        'health_status':c.get('/health').status_code}))
    for stamp in [slot['starts_at'],receipt['starts_at'],receipt['ends_at'],receipt['created_at']]:
        assert RFC3339.fullmatch(stamp),'Not an RFC3339 timestamp: '+stamp
    expected=datetime(1800,1,1,18,tzinfo=ZoneInfo(zone)).astimezone(timezone.utc)
    actual=datetime.fromisoformat(receipt['starts_at']).astimezone(timezone.utc)
    assert actual==expected
    assert (datetime.fromisoformat(receipt['ends_at'])-datetime.fromisoformat(receipt['starts_at'])).total_seconds()==3600
    assert c.get('/reservations/'+receipt['reference'],headers=auth).json()==receipt
    exported=c.get('/_test/export',timeout=10)
    assert exported.status_code==200
    assert c.post('/_test/import',json=exported.json(),timeout=10).status_code==204
    retry=c.post('/reservations',json=value,headers=auth)
    assert retry.status_code==200 and retry.json()==receipt
