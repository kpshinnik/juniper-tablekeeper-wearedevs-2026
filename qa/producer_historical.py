"""D126: actual old HTTP producer, removed before a fresh repaired consumer starts.

The host owns process removal. This client verifies immutable legacy receipts and
strict current projections without constructing or modifying an opaque snapshot.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import os
import time
import httpx
from derived.test_timestamp_boundaries import exact_instant,check_stamp
from derived.test_historical_timestamps import RFC3339


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--phase',choices=['produce','consume'],required=True)
    p.add_argument('--state-dir',type=Path,required=True)
    a=p.parse_args(); root=a.state_dir; started=time.monotonic()
    host='source' if a.phase=='produce' else 'destination'
    with httpx.Client(base_url='http://'+host+':8080',timeout=5,trust_env=False) as c:
        deadline=time.monotonic()+55
        while True:
            try:
                if c.get('/health').status_code==200:break
            except httpx.HTTPError:pass
            assert time.monotonic()<deadline
            time.sleep(.1)
        credentials={'email':'legacy@portability.test','password':'synthetic-password'}
        if a.phase=='produce':
            hours=[{'weekday':d,'opens':'00:00','closes':'23:30'} for d in 'mon tue wed thu fri sat sun'.split()]
            fixture={'users':[{'id':'u',**credentials,'display_name':'Historical diner'}],'restaurants':[], 'reservations':[]}
            for ident,zone in [('berlin','Europe/Berlin'),('ny','America/New_York')]:
                fixture['restaurants'].append({'id':ident,'name':ident,'timezone':zone,'slot_minutes':30,
                    'reservation_duration_minutes':30,'cancellation_cutoff_minutes':0,'opening_hours':hours,
                    'tables':[{'id':ident+'a','label':'A','capacity':4},{'id':ident+'b','label':'B','capacity':4}]})
            assert c.post('/_test/reset',json=fixture,timeout=10).status_code==204
            tokens=[]
            for _ in range(2):
                login=c.post('/auth/login',json=credentials);assert login.status_code==200
                tokens.append(login.json()['token'])
            records=[]
            for i,(ident,zone,local) in enumerate([
                ('berlin','Europe/Berlin','1800-01-01T18:00'),
                ('ny','America/New_York','1800-01-01T18:00'),
                ('berlin','Europe/Berlin','0001-01-01T00:00'),
                ('ny','America/New_York','0001-01-01T00:00')]):
                body={'restaurant_id':ident,'table_id':ident+'a','starts_at_local':local,'party_size':2}
                key='historical-'+str(i)
                r=c.post('/reservations',json=body,headers={'Authorization':'Bearer '+tokens[0],'Idempotency-Key':key})
                assert r.status_code==201,r.text
                receipt=r.json()
                assert not RFC3339.fullmatch(receipt['starts_at']),'Source must actually exhibit legacy historical spelling'
                expected=exact_instant(datetime.fromisoformat(local).replace(tzinfo=ZoneInfo(zone)))
                assert exact_instant(datetime.fromisoformat(receipt['starts_at']))==expected
                records.append({'body':body,'key':key,'receipt':receipt,'zone':zone,'expected':expected})
            snap=c.get('/_test/export',timeout=10);assert snap.status_code==200
            root.mkdir(exist_ok=True)
            (root/'snapshot.json').write_bytes(snap.content)
            (root/'client.json').write_text(json.dumps({'tokens':tokens,'records':records}))
            print(json.dumps({'id':'D126-old-historical-producer-export','outcome':'PASS','records':4,
                'legacy_non_rfc3339_receipts':4,'duration_s':time.monotonic()-started,
                'snapshot_sha256':hashlib.sha256(snap.content).hexdigest(),'snapshot_bytes':len(snap.content)}))
        else:
            saved=(root/'snapshot.json').read_bytes(); x=json.loads((root/'client.json').read_text())
            for token in x['tokens']:
                assert c.get('/reservations',headers={'Authorization':'Bearer '+token}).status_code==401
            imported=c.post('/_test/import',content=saved,headers={'Content-Type':'application/json'},timeout=10)
            assert imported.status_code==204,imported.text
            before=c.get('/_test/export',timeout=10).content
            for token in x['tokens']:
                auth={'Authorization':'Bearer '+token}
                listed=c.get('/reservations',headers=auth);assert listed.status_code==200
                assert len(listed.json()['reservations'])==4
                byref={r['reference']:r for r in listed.json()['reservations']}
                for item in x['records']:
                    old=item['receipt'];ref=old['reference'];expected=item['expected']
                    result=c.get('/reservations/'+ref,headers=auth);assert result.status_code==200
                    current=result.json();assert current==byref[ref]
                    expected_fields={k:v for k,v in old.items() if k not in ('starts_at','ends_at')}
                    if int(os.environ.get('STAGE_UNDER_TEST','1'))>=2:expected_fields['table_ids']=[old['table_id']]
                    projection_extra=()
                    if int(os.environ.get('STAGE_UNDER_TEST','1'))>=3:
                        # Stage3 adds current revision/terms, while the authentic
                        # old receipt remains byte-semantic original below.
                        rest=c.get('/restaurants/'+old['restaurant_id']).json()
                        expected_terms={k:rest[k] for k in ('slot_minutes','reservation_duration_minutes',
                                                           'cancellation_cutoff_minutes','opening_hours')}
                        expected_terms.update(policy_version=0,capacities={t['id']:t['capacity'] for t in rest['tables']})
                        assert current['revision']==1 and current['accepted_terms']==expected_terms
                        history=c.get('/reservations/'+ref+'/history',headers=auth)
                        assert history.status_code==200 and history.json()=={'reference':ref,'entries':[]}
                        projection_extra=('revision','accepted_terms')
                    assert {k:v for k,v in current.items() if k not in ('starts_at','ends_at',*projection_extra)}==expected_fields
                    check_stamp(current['starts_at'],expected);check_stamp(current['ends_at'],expected+1800000000)
                    assert c.get('/restaurants/'+old['restaurant_id']).json()['timezone']==item['zone']
                    availability=c.get('/availability',params={'restaurant_id':old['restaurant_id'],'date':old['starts_at_local'][:10],'party_size':2})
                    assert availability.status_code==200
                    slot=next(s for s in availability.json()['slots'] if s['starts_at_local']==old['starts_at_local'])
                    check_stamp(slot['starts_at'],expected)
                    assert old['table_id'] not in slot['available_table_ids']
                    retry=c.post('/reservations',json=item['body'],headers={**auth,'Idempotency-Key':item['key']})
                    assert retry.status_code==200 and retry.json()==old,'Legacy original JSON receipt was rewritten'
                    conflict=c.post('/reservations',json=item['body'],headers={**auth,'Idempotency-Key':item['key']+'-new'})
                    assert conflict.status_code==409 and conflict.json()['error']['code']=='table_unavailable'
            assert c.get('/_test/export',timeout=10).content==before,'Reads/retries altered imported state'
            auth={'Authorization':'Bearer '+x['tokens'][0],'Idempotency-Key':'new-target'}
            item=x['records'][0]
            fresh=c.post('/reservations',json={**item['body'],'table_id':'berlinb'},headers=auth)
            assert fresh.status_code==201,fresh.text
            check_stamp(fresh.json()['starts_at'],item['expected'])
            assert c.post('/_test/import',content=saved,headers={'Content-Type':'application/json'},timeout=10).status_code==204
            assert len(c.get('/reservations',headers=auth).json()['reservations'])==4
            assert c.post('/auth/login',json=credentials).status_code==200
            assert c.get('/health').json()=={'status':'ok'}
            print(json.dumps({'id':'D126-old-historical-source-removed-fresh-current-lifetime','outcome':'PASS',
                'duration_s':time.monotonic()-started,'retained_tokens':2,'immutable_receipts':4,
                'strict_current_historical_projections':4,'exact_calendar_boundary_records':2,
                'current_reference_retained':True,'new_write':True,'repeat_replacement':True,'password_login':True}))


if __name__=='__main__':main()
