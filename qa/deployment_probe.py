"""Real isolated-container default/custom PORT and readiness checks."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import time
import uuid

D=['/opt/homebrew/bin/docker','--context','colima-tablekeeper']


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',type=Path,required=True)
    p.add_argument('--stage',type=int,choices=[1,2,3,4],default=1)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out
    sha=subprocess.check_output(['git','-C',str(a.checkout),'rev-parse','HEAD'],text=True).strip()
    assert sha==os.environ['QA_PRODUCT_SHA']
    assert not subprocess.check_output(['git','-C',str(a.checkout),'status','--porcelain'],text=True)
    name='juniper-v-port-'+uuid.uuid4().hex[:10];net=name+'-net';image=name+':s'+str(a.stage)
    labels=['--label','juniper.owner=verifier','--label','juniper.room=e04c2728-8535-41c8-be50-88eb8068fa09']
    active=[];network=False
    def run(argv,file,check=True):
        tick=time.monotonic();r=subprocess.run(argv,capture_output=True,timeout=60)
        (out/file).write_bytes(r.stdout+r.stderr)
        with (out/'commands.jsonl').open('a') as f:f.write(json.dumps({'argv':argv,'returncode':r.returncode,'duration_s':time.monotonic()-tick})+'\n')
        if check:assert r.returncode==0,(file,r.returncode)
        return r
    try:
        run(D+['build',*labels,'-t',image,str(a.checkout/f'stage-{a.stage}')],'build.log')
        run(D+['network','create','--internal',*labels,net],'network-create.log');network=True
        for port,configured in [(8080,False),(18087,True)]:
            service=name+'-'+str(port);start=time.monotonic()
            run(D+['run','-d','--name',service,*labels,'--network',net,'--network-alias','tablekeeper',
                   '--cpus','2','--memory','2g','--memory-swap','2g','--read-only',
                   '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=64m',
                   *(['-e','PORT='+str(port)] if configured else []),image],str(port)+'-start.log')
            active.append(service)
            code="import httpx,json,time;tick=time.monotonic();requests=0\nwhile time.monotonic()-tick<55:\n try:\n  requests+=1;r=httpx.get('http://tablekeeper:"+str(port)+"/health',timeout=2,trust_env=False)\n  if r.status_code==200 and r.json()=={'status':'ok'}:print(json.dumps({'status':200,'body':r.json(),'requests':requests,'client_elapsed_s':time.monotonic()-tick}));break\n except httpx.HTTPError:pass\n time.sleep(.1)\nelse:raise SystemExit('health failed')"
            result=run(D+['run','--rm',*labels,'--network',net,'--entrypoint','python',
                         'tablekeeper-test-runner:latest','-c',code],str(port)+'-client.log')
            elapsed=time.monotonic()-start;assert elapsed<=60
            inspected=run(D+['inspect',service],str(port)+'-inspect.json')
            state=json.loads(inspected.stdout)[0];host=state['HostConfig']
            assert host['NanoCpus']==2000000000 and host['Memory']==2147483648 and host['ReadonlyRootfs']
            row={'id':'DEPLOY-PORT-'+str(port),'product_sha':sha,'stage':a.stage,'outcome':'PASS','port':port,
                 'override_supplied':configured,'start_to_health_s':elapsed,'observed':json.loads(result.stdout),
                 'service_cpus':2,'service_memory_bytes':2147483648,'read_only':True,'internal_network':True,
                 'client_memory_cap':None,'expected':'Healthy from another internal-network container within60s on default or configured PORT'}
            with (out/'deployment.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            run(D+['logs',service],str(port)+'-service.log')
            run(D+['rm','-f',service],str(port)+'-remove.log');active.remove(service)
    finally:
        for service in active:run(D+['rm','-f',service],service+'-remove.log',False)
        if network:run(D+['network','rm',net],'network-remove.log',False)


if __name__=='__main__':main()
