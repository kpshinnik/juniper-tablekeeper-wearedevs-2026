"""Immutable producer/consumer frozen upgrades and actual source removal."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import tempfile
import time
import uuid

DOCKER=['/opt/homebrew/bin/docker','--context','colima-tablekeeper']
ROOT=Path(__file__).resolve().parent.parent
ROOM='e04c2728-8535-41c8-be50-88eb8068fa09'


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--checkout',type=Path,required=True)
    p.add_argument('--source-checkout',type=Path)
    p.add_argument('--stage',type=int,choices=[1,2,3,4],default=1)
    p.add_argument('--source-stage',type=int,choices=[1,2,3,4],default=1)
    p.add_argument('--only-producer-removal',action='store_true')
    p.add_argument('--producer-scenario',choices=['ordinary','historical','legacy-selector','stage3-authenticity','stage4-authenticity'],default='ordinary')
    p.add_argument('--browser-transfer',action='store_true')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(exist_ok=True,parents=True)
    producer_script='/qa/producer_historical.py' if a.producer_scenario=='historical' else '/qa/producer_removal.py'
    if a.producer_scenario=='stage3-authenticity':
        producer_script='/qa/producer_stage3.py'
    if a.producer_scenario=='stage4-authenticity':
        producer_script='/qa/producer_stage4.py'
    sha=subprocess.check_output(['git','-C',str(a.checkout),'rev-parse','HEAD'],text=True).strip()
    assert sha==os.environ['QA_PRODUCT_SHA']
    assert subprocess.check_output(['git','-C',str(a.checkout),'status','--porcelain'],text=True)==''
    source_checkout=a.source_checkout or a.checkout
    source_sha=subprocess.check_output(['git','-C',str(source_checkout),'rev-parse','HEAD'],text=True).strip()
    assert subprocess.check_output(['git','-C',str(source_checkout),'status','--porcelain'],text=True)==''
    name='juniper-v-up-'+uuid.uuid4().hex[:10]; network=name+'-net'; image=name+':destination'
    source_image=image if source_checkout==a.checkout and a.source_stage==a.stage else name+':source'
    labels=['--label','juniper.room='+ROOM,'--label','juniper.owner=verifier']
    active=[]; net=False
    def run(args,file,timeout=600,check=True):
        tick=time.monotonic()
        with (out/file).open('wb') as stream: r=subprocess.run(args,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        with (out/'commands.jsonl').open('a') as stream:stream.write(json.dumps({'argv':args,'returncode':r.returncode,'duration_s':time.monotonic()-tick})+'\n')
        if check:assert r.returncode==0,(file,r.returncode)
        return r.returncode
    def start(role):
        container=name+'-'+role+'-'+uuid.uuid4().hex[:4]
        run(DOCKER+['run','-d','--name',container,*labels,'--network',network,'--network-alias',role,
                    '--cpus','2','--memory','2g','--memory-swap','2g','--read-only',
                    '--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777',source_image if role=='source' else image],role+'-'+container[-4:]+'-start.log')
        active.append(container);return container
    def remove(container):
        run(DOCKER+['logs',container],container+'-service.log',check=False)
        run(DOCKER+['inspect',container],container+'-inspect.json',check=False)
        run(DOCKER+['rm','-f',container],container+'-remove.log')
        active.remove(container)
    def runner(extra,file,network_override=None):
        return run(DOCKER+['run','--rm',*labels,'--network',network_override or network,'-v',str(ROOT/'qa')+':/qa:ro',
                     '-v',str(out)+':/evidence','-w','/qa','-e','PYTHONPATH=/qa','-e','PYTHONDONTWRITEBYTECODE=1',
                     '-e','QA_PRODUCT_SHA='+sha,'-e','QA_SOURCE_SHA='+os.environ.get('QA_SOURCE_SHA',''),
                     '-e','STAGE_UNDER_TEST='+str(a.stage),
                     '-e','QA_SOURCE_STAGE='+str(a.source_stage),'-e','QA_BROWSER_BASE=http://127.0.0.1:8080',
                     '-e','QA_LEGACY_SELECTOR='+('1' if a.producer_scenario=='legacy-selector' else '0'),
                     '-e','QA_EVIDENCE_DIR=/evidence','-e','QA_HTTP_METRICS=1',*extra],file,check=False)
    try:
        (out/'environment.json').write_text(json.dumps({'destination_sha':sha,'source_sha':source_sha,
            'source_stage':a.source_stage,'destination_stage':a.stage,'source_checkout':str(source_checkout),
            'destination_checkout':str(a.checkout),'client_memory_cap':None,
            'frozen_suite_executed':not a.only_producer_removal,'producer_removal_executed':True,
            'producer_scenario':a.producer_scenario,'browser_transfer_executed':a.browser_transfer},indent=2)+'\n')
        run(DOCKER+['build',*labels,'-t',image,str(a.checkout/f'stage-{a.stage}')],'build.log')
        if source_image!=image:
            run(DOCKER+['build',*labels,'-t',source_image,str(source_checkout/f'stage-{a.source_stage}')],'source-build.log')
        run(DOCKER+['network','create','--internal',*labels,network],'network-create.log');net=True
        frozen_code=0
        if not a.only_producer_removal:
            source=start('source');destination=start('destination')
            frozen_code=runner(['tablekeeper-test-runner:latest','-p','evidence_plugin','-p','no:cacheprovider','-q','--tb=short',
                               '--junitxml=/evidence/junit.xml','frozen/supplemental/test_upgrade_contract.py'],'frozen-tests.log')
            remove(source);remove(destination)
        browser_code=0
        if a.browser_transfer:
            assert a.stage>=2,'Browser transfer requires the browser contract'
            source=start('source');destination=start('destination')
            browser_code=runner(['--entrypoint','python','df-harness-runner','-m','pytest','-p','evidence_plugin','-p','no:cacheprovider','-q','--tb=short',
                '--junitxml=/evidence/browser-junit.xml','derived/test_stage2_upgrade_browser.py'],
                'browser-tests.log',network_override='container:'+destination)
            remove(source);remove(destination)
        # Export/private synthetic credentials stay in a disposable directory,
        # outside the public evidence tree; hashes and observable checks are retained.
        with tempfile.TemporaryDirectory(prefix=name+'-',dir=str(a.checkout.parent)) as private:
            source=start('source')
            produce=runner(['-v',private+':/private','--entrypoint','python','tablekeeper-test-runner:latest',
                            producer_script,'--phase','produce','--state-dir','/private'],'producer.log')
            assert produce==0
            remove(source)
            missing=subprocess.run(DOCKER+['inspect',source],capture_output=True)
            assert missing.returncode!=0,'Source still exists'
            (out/'producer-removal-proof.json').write_text(json.dumps({'source':source,'removed':True,
                  'post_removal_inspect_returncode':missing.returncode,'destination_not_started_yet':True})+'\n')
            destination=start('destination')
            consume=runner(['-v',private+':/private:ro','--entrypoint','python','tablekeeper-test-runner:latest',
                            producer_script,'--phase','consume','--state-dir','/private'],'consumer.log')
            assert consume==0
        raise SystemExit(frozen_code or browser_code)
    finally:
        for container in active[:]:remove(container)
        if net:run(DOCKER+['network','rm',network],'network-remove.log',check=False)


if __name__=='__main__':main()
