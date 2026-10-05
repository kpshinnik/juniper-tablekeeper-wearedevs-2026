"""Source-level publication experiment, explicitly separate from HTTP tests.

Imports only the exact clean revision passed on the command line. No product
file is changed. Every operation/control and injected fault is individually
logged; a list of controls is never reported as an executed injection count.
"""
from pathlib import Path
import argparse
import importlib
import json
import sys
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage-path', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--stage', type=int, choices=[1,2,3,4], default=1)
    args = parser.parse_args()
    sys.path.insert(0, str(args.stage_path))
    server, domain, j = [importlib.import_module(name) for name in ('server','domain','exactjson')]
    fx = {'users':[{'id':'u','email':'u@fault.test','password':'synthetic-password','display_name':'Diner'}],
          'restaurants':[{'id':'r','name':'Fault garden','timezone':'UTC','slot_minutes':30,
            'reservation_duration_minutes':60,'cancellation_cutoff_minutes':0,
            'opening_hours':[{'weekday':d,'opens':'17:00','closes':'23:00'} for d in 'mon tue wed thu fri sat sun'.split()],
            'tables':[{'id':'a','label':'A','capacity':4},{'id':'b','label':'B','capacity':4}]}],'reservations':[]}
    base = {'restaurant_id':'r','table_id':'a','starts_at_local':'2030-01-01T18:00','party_size':2}
    if args.stage>=3:
        fx['restaurants'][0]['manager_user_ids']=['u']
    policy = {'effective_from':'2030-01-01','slot_minutes':30,'reservation_duration_minutes':90,
              'cancellation_cutoff_minutes':0,'opening_hours':fx['restaurants'][0]['opening_hours'],
              'capacities':{'a':4,'b':4}}
    def world():
        store = server.Store()
        store.request('POST','/_test/reset',{}, {},fx)
        _, encoded, _ = store.request('POST','/auth/login',{}, {},{'email':'u@fault.test','password':'synthetic-password'})
        token = j.loads(encoded)['token']
        auth = {'authorization':'Bearer '+token,'idempotency-key':'one','accept-encoding':'gzip'}
        if args.stage>=3:
            setup = {'authorization':'Bearer '+token,'idempotency-key':'setup-book'}
            _, raw, _ = store.request('POST','/reservations',{},setup,
                {**base,'table_id':'b','starts_at_local':'2030-02-01T18:00'})
            ref = j.loads(raw)['reference']
            setup['idempotency-key']='setup-series'
            status, _, _ = store.request('POST','/series',{},setup,
                {'anchor_reference':ref,'count':2,'interval_weeks':1})
            assert status==201
            setup['idempotency-key']='setup-policy'
            status, _, _ = store.request('POST','/restaurants/r/policies',{},setup,
                {**policy,'effective_from':'2040-01-01'})
            assert status==201
        return store,auth
    def prepare(operation):
        store,auth = world()
        path, body, method = '/reservations',base,'POST'
        if operation in ('patch','cancel','moves','series','series_patch','series_cancel','series_moves','series_amend'):
            plain = dict(auth); plain.pop('accept-encoding')
            _, raw, _ = store.request('POST','/reservations',{},plain,base)
            ref = j.loads(raw)['reference']
            if operation.startswith('series_'):
                status, raw, _ = store.request('POST','/series',{},plain,
                    {'anchor_reference':ref,'count':3,'interval_weeks':1})
                assert status==201
                agreement=j.loads(raw)
                refs=[x['reference'] for x in agreement['occurrences']]
            path = '/reservations/'+ref
            if operation in ('patch','series_patch'): method,body='PATCH',{'party_size':1}
            elif operation in ('cancel','series_cancel'): path,body=path+'/cancel',{}
            elif operation=='moves': path,body='/reservation-moves',{'moves':[{'reference':ref,'table_id':'b'}]}
            elif operation=='series_moves': path,body='/reservation-moves',{'moves':[{'reference':r,'party_size':1} for r in refs[:2]]}
            elif operation=='series_amend': path,body='/series/'+agreement['series_id']+'/amend',{'expected_revision':1,'from_index':0,'local_time':'20:00'}
            else: path,body='/series',{'anchor_reference':ref,'count':3,'interval_weeks':1}
        elif operation in ('replan_preview','replan_apply','series_replan_apply','empty_replan_apply'):
            plain=dict(auth); plain.pop('accept-encoding')
            if operation!='empty_replan_apply':
                status,raw,_=store.request('POST','/reservations',{},plain,base)
                assert status==201
                if operation=='series_replan_apply':
                    ref=j.loads(raw)['reference']
                    status,_,_=store.request('POST','/series',{},plain,{'anchor_reference':ref,'count':3,'interval_weeks':1})
                    assert status==201
            path='/restaurants/r/replans'
            body={'table_id':'a','from':'2030-01-01T00:00:00Z','to':'2030-01-16T00:00:00Z'}
            if operation!='replan_preview':
                status,raw,_=store.request('POST',path,{},plain,body)
                assert status==201
                plan=j.loads(b''.join(raw.blocks()) if isinstance(raw,server.PreparedBody) else raw)
                path,body=path+'/'+plan['plan_id']+'/apply',{}
        elif operation=='policy':
            path,body='/restaurants/r/policies',policy
        elif operation == 'signup':
            path,body='/auth/signup',{'email':'new@fault.test','password':'synthetic-password','display_name':'New'}
        elif operation == 'login':
            path,body='/auth/login',{'email':'u@fault.test','password':'synthetic-password'}
        elif operation == 'reset':
            path,body='/_test/reset',{'users':[],'restaurants':[],'reservations':[]}
        elif operation == 'import':
            path,body='/_test/import',domain.snapshot(domain.empty_state())
        return store, (method,path,{},auth,body)
    operations=['signup','login','create','patch','cancel','moves','reset','import']
    if args.stage>=3:
        operations+=['policy','series','series_patch','series_cancel','series_moves']
    if args.stage>=4:
        operations+=['replan_preview','replan_apply','series_replan_apply','empty_replan_apply','series_amend']
    faults=['response_encode','candidate_encode','compression']
    rows=[]
    controls=[]
    for operation in operations:
        store,request = prepare(operation)
        tick=time.monotonic()
        status,_,_=store.request(*request)
        controls.append({'id':'CONTROL-'+operation,'operation':operation,'status':status,
                         'duration_s':time.monotonic()-tick,'outcome':'PASS' if status in (200,201,204) else 'FAIL'})
        with args.out.with_name('source-controls.jsonl').open('a') as stream:
            stream.write(json.dumps(controls[-1])+'\n')
        for fault in faults:
            # 204 reset/import have no response encoding or compression; they
            # still require and exercise candidate validation/preparation.
            if operation in ('reset','import') and fault!='candidate_encode':
                continue
            store,request=prepare(operation)
            before=j.dumps(store.state,True)
            original_prepare=store.prepare
            triggered=[]
            def injected(candidate,response,compressed):
                def boom(*unused,**kw):
                    triggered.append(fault)
                    raise ValueError('Verifier synthetic '+fault)
                if fault=='response_encode':
                    original_chunks=j.chunks
                    def response_chunks(value,*a,**kw):
                        if value is response:
                            boom()
                        yield from original_chunks(value,*a,**kw)
                    with patch.object(j,'dumps',side_effect=boom), patch.object(j,'chunks',side_effect=response_chunks):
                        return original_prepare(candidate,response,compressed)
                if fault=='compression':
                    with patch.object(server.gzip,'compress',side_effect=boom), patch.object(server.PreparedBody,'compressed',side_effect=boom):
                        return original_prepare(candidate,response,compressed)
                original_chunks=j.chunks
                def chunks(value,*a,**kw):
                    if value is candidate:
                        boom()
                    yield from original_chunks(value,*a,**kw)
                with patch.object(j,'chunks',side_effect=chunks):
                    return original_prepare(candidate,response,compressed)
            tick=time.monotonic()
            error=None
            with patch.object(store,'prepare',side_effect=injected):
                try: store.request(*request)
                except Exception as exc: error=type(exc).__name__
            unchanged=j.dumps(store.state,True)==before
            status,_,_=store.request(*request)
            passed=triggered==[fault] and error=='ValueError' and unchanged and status in (200,201,204)
            row={'id':'FAULT-'+operation+'-'+fault,'kind':'SOURCE_INJECTION_NOT_HTTP',
                 'operation':operation,'fault':fault,'actually_triggered':triggered,
                 'expected':'Injected failure before publication leaves exact state unchanged; retry succeeds',
                 'observed':{'exception':error,'state_unchanged':unchanged,'retry_status':status},
                 'outcome':'PASS' if passed else 'FAIL','duration_s':time.monotonic()-tick}
            rows.append(row)
            with args.out.open('a') as stream: stream.write(json.dumps(row)+'\n')
    result={'kind':'SOURCE_INJECTION_NOT_HTTP','control_operations_defined':operations,
            'control_operations_executed':controls,'actual_injected_case_count':len(rows),
            'defined_operation_count':len(operations),
            'executed_control_operation_names':sorted({x['operation'] for x in controls}),
            'executed_control_operation_count':len({x['operation'] for x in controls}),
            'actually_injected_operation_names':sorted({x['operation'] for x in rows if x['actually_triggered']}),
            'actually_injected_operation_count':len({x['operation'] for x in rows if x['actually_triggered']}),
            'actually_triggered_fault_point_types':sorted({x['fault'] for x in rows if x['actually_triggered']}),
            'actually_triggered_fault_point_type_count':len({x['fault'] for x in rows if x['actually_triggered']}),
            'actual_distinct_fault_names':sorted({x['fault'] for x in rows if x['actually_triggered']}),
            'legacy_fault_names_field_meaning':'Fault-point types, never operation names; retained for existing report readers.',
            'http_requests':0,'passed':sum(x['outcome']=='PASS' for x in rows),'failed':sum(x['outcome']=='FAIL' for x in rows)}
    print(json.dumps(result))
    if result['failed'] or any(x['outcome']!='PASS' for x in controls): raise SystemExit(1)


if __name__=='__main__':main()
