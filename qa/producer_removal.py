"""Two-phase HTTP portability check; the host removes producer between phases."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time

import httpx


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--phase',choices=['produce','consume'],required=True)
    p.add_argument('--state-dir',type=Path,required=True)
    a=p.parse_args()
    root=a.state_dir
    legacy_selector=os.environ.get('QA_LEGACY_SELECTOR')=='1'
    case_id='D217' if legacy_selector else 'D115'
    host='source' if a.phase=='produce' else 'destination'
    started=time.monotonic()
    with httpx.Client(base_url='http://'+host+':8080',timeout=6,trust_env=False) as c:
        deadline=time.monotonic()+55
        while True:
            try:
                if c.get('/health').status_code==200:break
            except httpx.HTTPError:pass
            assert time.monotonic()<deadline
            time.sleep(.1)
        if a.phase=='produce':
            hours=[{'weekday':d,'opens':'17:00','closes':'23:00'} for d in 'mon tue wed thu fri sat sun'.split()]
            fixture={'users':[{'id':'u','email':'u@portability.test','password':'synthetic-password','display_name':'Diner'}],
              'restaurants':[{'id':'r','name':'Portable garden','timezone':'UTC','slot_minutes':30,
               'reservation_duration_minutes':60,'cancellation_cutoff_minutes':0,'opening_hours':hours,
               'tables':[{'id':'a','label':'A','capacity':4},{'id':'b','label':'B','capacity':4}]}],'reservations':[]}
            source_stage=int(os.environ.get('QA_SOURCE_STAGE','1'))
            if legacy_selector:assert source_stage==1 and int(os.environ['STAGE_UNDER_TEST'])>=2
            if source_stage>=2:fixture['restaurants'][0]['combinable']=[['a','b']]
            assert c.post('/_test/reset',json=fixture,timeout=10).status_code==204
            tokens=[]
            for _ in range(2):
                r=c.post('/auth/login',json={'email':'u@portability.test','password':'synthetic-password'})
                assert r.status_code==200; tokens.append(r.json()['token'])
            auth={'Authorization':'Bearer '+tokens[0],'Idempotency-Key':'create'}
            body={'restaurant_id':'r','table_id':'a','starts_at_local':'2030-01-01T18:00','party_size':2,'unknown':{'雪':[True,1]}}
            if source_stage>=2:
                body.pop('table_id');body['table_ids']=['a','b']
            if legacy_selector:body['table_ids']=['b','a']  # Unknown and ignored by the actual Stage1 producer.
            first=c.post('/reservations',json=body,headers=auth)
            assert first.status_code==201
            original=first.json(); ref=original['reference']
            moves={'moves':[{'reference':ref,'table_id':'b'}]}
            if legacy_selector:moves['moves'][0]['table_ids']=['a']
            batch=c.post('/reservation-moves',json=moves,headers={**auth,'Idempotency-Key':'moves'})
            assert batch.status_code==201
            assert c.post('/reservations/'+ref+'/cancel',json={},headers=auth).status_code==200
            snap=c.get('/_test/export',timeout=10)
            assert snap.status_code==200
            root.mkdir(exist_ok=True)
            (root/'snapshot.json').write_bytes(snap.content)
            (root/'client.json').write_text(json.dumps({'tokens':tokens,'original':original,'body':body,'moves':moves,'batch':batch.json()}))
            print(json.dumps({'id':case_id+'-producer-populated-export','outcome':'PASS','duration_s':time.monotonic()-started,
                              'snapshot_sha256':hashlib.sha256(snap.content).hexdigest(),'snapshot_bytes':len(snap.content)}))
        else:
            saved=(root/'snapshot.json').read_bytes(); x=json.loads((root/'client.json').read_text())
            # The fresh destination cannot know either retained token before import.
            for token in x['tokens']:
                assert c.get('/reservations',headers={'Authorization':'Bearer '+token}).status_code==401
            assert c.post('/_test/import',content=saved,headers={'Content-Type':'application/json'},timeout=10).status_code==204
            for token in x['tokens']:
                auth={'Authorization':'Bearer '+token}
                r=c.get('/reservations/'+x['original']['reference'],headers=auth)
                assert r.status_code==200 and r.json()['status']=='cancelled' and r.json()['table_id']=='b'
                replay=c.post('/reservations',json=x['body'],headers={**auth,'Idempotency-Key':'create'})
                assert replay.status_code==200 and replay.json()==x['original']
                replay=c.post('/reservation-moves',json=x['moves'],headers={**auth,'Idempotency-Key':'moves'})
                assert replay.status_code==200 and replay.json()==x['batch']
            if legacy_selector:
                before=c.get('/_test/export',timeout=10).content
                altered={**x['body'],'table_ids':['a']}
                conflict=c.post('/reservations',json=altered,headers={**auth,'Idempotency-Key':'create'})
                assert conflict.status_code==409 and conflict.json()['error']['code']=='idempotency_key_reuse'
                rejected=c.post('/reservations',json=x['body'],headers={**auth,'Idempotency-Key':'fresh-both-fields'})
                assert rejected.status_code==422 and rejected.json()['error']['code']=='validation_failed'
                assert c.get('/_test/export',timeout=10).content==before
            auth={'Authorization':'Bearer '+x['tokens'][0],'Idempotency-Key':'new'}
            new_body={**x['body'],'starts_at_local':'2030-01-01T20:00'}
            target_stage=int(os.environ.get('STAGE_UNDER_TEST','1'))
            if target_stage>=2 and 'table_id' in new_body:new_body['table_ids']=[new_body.pop('table_id')]
            new=c.post('/reservations',json=new_body,headers=auth);assert new.status_code==201
            if target_stage>=2:assert new.json()['table_ids']==new_body['table_ids']
            assert c.post('/_test/import',content=saved,headers={'Content-Type':'application/json'},timeout=10).status_code==204
            assert len(c.get('/reservations',headers=auth).json()['reservations'])==1
            assert c.post('/auth/login',json={'email':'u@portability.test','password':'synthetic-password'}).status_code==200
            print(json.dumps({'id':case_id+'-source-removed-fresh-destination-lifetime','outcome':'PASS',
                              'duration_s':time.monotonic()-started,'retained_tokens':2,'immutable_receipts':2,
                              'current_reference_retained':True,'new_write':True,'new_target_table_ids_operation':target_stage>=2,
                              'original_selection':[x['body']['table_id']] if legacy_selector else x['body'].get('table_ids',[x['body'].get('table_id')]),
                              'legacy_ignored_selector_original_identity_preserved':legacy_selector,
                              'repeat_replacement':True,'password_login':True}))


if __name__=='__main__':main()
