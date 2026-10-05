"""One independent containerized suite on a clean committed product checkout.

Invoke through attempt.py. Every suite is sequential; this runner never caps
client memory. Only uniquely named resources created here are removed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid

DOCKER = ['/opt/homebrew/bin/docker', '--context', 'colima-tablekeeper']
ROOM = 'e04c2728-8535-41c8-be50-88eb8068fa09'
ROOT = Path(__file__).resolve().parent.parent
COMMON = ['test_boundaries.py', 'test_auth_contract.py', 'test_json_responses.py',
          'test_protocol_resources.py', 'test_audit30.py']
SUITES = {'original': ['frozen/baseline-original'], 'adjudicated': ['frozen/baseline-adjudicated'],
          'common': ['frozen/supplemental/' + p for p in COMMON],
          'numeric': ['frozen/numeric-original'], 'derived': ['derived/test_stage1.py'],
          'snapshot-semantics': ['derived/test_snapshot_semantics.py'],
          'snapshot-adapted': ['adapters/test_string_payload.py'],
          'stage4-snapshot-adapted': ['adapters/test_stage4_payload.py'],
          'stage4-integrity': ['derived/test_stage4_integrity.py'],
          'stage4-encoding-collision': ['derived/test_stage4_encoding_collision.py'],
          'stage4-route-reconciliation': ['derived/test_stage4.py::test_D404_noops_replays_preview_and_other_restaurant_do_not_stale'],
          'additional-stage1': ['derived/test_additional_stage1.py'],
          'official-detail': ['/official/tablekeeper/test/stage_1'],
          'calendar-edges': ['derived/test_calendar_edges.py'],
          'calendar-lifetime': ['derived/test_calendar_lifetime.py'],
          'historical-timestamps': ['derived/test_historical_timestamps.py'],
          'timestamp-boundaries': ['derived/test_timestamp_boundaries.py'],
          'stage2-pairs': ['derived/test_stage2_pairs.py'],
          'stage2-browser': ['derived/test_stage2_browser.py'],
          'stage2-label-lifetime': ['derived/test_stage2_label_lifetime.py'],
          'stage2-native-range': ['derived/test_stage2_native_range.py'],
          'stage2-numeric-geometry': ['derived/test_stage2_numeric_geometry.py'],
          'stage2-integer-validation': ['derived/test_stage2_integer_validation.py'],
          'stage2-pair-visibility': ['derived/test_stage2_pair_visibility.py'],
          'stage2-pair-repair': ['derived/test_stage2_pair_repair.py'],
          'stage3-domain': ['derived/test_stage3.py'],
          'stage4-domain': ['derived/test_stage4.py'],
          'stage4-browser-derived': ['derived/test_stage4_browser.py'],
          'official-stage2-detail': ['/official/tablekeeper/test/stage_1','/official/tablekeeper/test/stage_2'],
          'official-stage3-detail': ['/official/tablekeeper/test/stage_1','/official/tablekeeper/test/stage_2','/official/tablekeeper/test/stage_3'],
          'official-stage4-detail': ['/official/tablekeeper/test/stage_1','/official/tablekeeper/test/stage_2','/official/tablekeeper/test/stage_3','/official/tablekeeper/test/stage_4'],
          'pairs': ['frozen/supplemental/test_compact_pairs.py'],
          'advanced': ['frozen/supplemental/test_advanced.py'],
          'stage4-load': ['frozen/supplemental/test_stage4_load.py'],
          'stage4-numeric': ['frozen/supplemental/test_stage4_numeric.py'],
          'stage4-ui': ['frozen/supplemental/test_stage4_ui.py', 'frozen/supplemental/test_stage4_ui_lost.py']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkout', type=Path, required=True)
    p.add_argument('--stage', type=int, choices=[1, 2, 3, 4], required=True)
    p.add_argument('--suite', choices=SUITES, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    def command(args, logfile, timeout=1800, check=True):
        tick = time.monotonic()
        with (out / logfile).open('wb') as stream:
            result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        with (out / 'commands.jsonl').open('a') as stream:
            stream.write(json.dumps({'argv': args, 'returncode': result.returncode,
                                     'duration_s': time.monotonic()-tick})+'\n')
        if check and result.returncode:
            raise RuntimeError(f'Command returned {result.returncode}; see {logfile}')
        return result.returncode
    def git(*args):
        return subprocess.check_output(['git','-C',str(a.checkout),*args], text=True).strip()
    sha = git('rev-parse','HEAD')
    assert sha == os.environ['QA_PRODUCT_SHA'], (sha, os.environ['QA_PRODUCT_SHA'])
    assert not git('status','--porcelain=v1','--untracked-files=all'), 'Product checkout is dirty'
    ident = 'juniper-v-' + uuid.uuid4().hex[:12]
    network, service, client, image = ident+'-net', ident+'-svc', ident+'-qa', ident+':s'+str(a.stage)
    labels = ['--label','juniper.room='+ROOM,'--label','juniper.owner=verifier']
    created_network = created_service = created_client = created_previous = False
    previous=service+'-previous'
    try:
        command(DOCKER+['build',*labels,'-t',image,str(a.checkout/f'stage-{a.stage}')], 'build.log')
        command(DOCKER+['image','inspect',image], 'service-image.json',60)
        command(DOCKER+['network','create','--internal',*labels,network], 'network-create.log',60)
        created_network = True
        command(DOCKER+['network','inspect',network], 'network.json',60)
        started = time.monotonic()
        command(DOCKER+['run','-d','--name',service,*labels,'--network',network,
                         '--network-alias','tablekeeper','--network-alias','service',
                         '--cpus','2','--memory','2g','--memory-swap','2g','--read-only',
                         '--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777','-e','PORT=8080',image], 'service-start.log',60)
        created_service = True
        health_code = "import httpx,time; t=time.monotonic();\nwhile time.monotonic()-t<55:\n try:\n  r=httpx.get('http://tablekeeper:8080/health',timeout=2,trust_env=False)\n  if r.status_code==200 and r.json()=={'status':'ok'}: print(time.monotonic()-t); break\n except (httpx.HTTPError,ValueError): pass\n time.sleep(.1)\nelse: raise SystemExit('health deadline')"
        command(DOCKER+['run','--rm',*labels,'--network',network,'--entrypoint','python',
                         'tablekeeper-test-runner:latest','-c',health_code], 'health.log',60)
        healthy_s = time.monotonic()-started
        assert healthy_s <= 60, healthy_s
        command(DOCKER+['inspect',service], 'service-before.json',60)
        (out/'environment.json').write_text(json.dumps({'product_sha':sha,'stage':a.stage,'suite':a.suite,
            'checkout':str(a.checkout),'qa_root':str(ROOT/'qa'),'service':service,'network':network,
            'image':image,'client':client,'client_memory_cap':None,'healthy_s':healthy_s,
            'service_limits':{'cpus':2,'memory_bytes':2147483648,'read_only':True,'runtime_network':'internal'}} ,indent=2)+'\n')
        official=a.suite in ('official-detail','official-stage2-detail','official-stage3-detail','official-stage4-detail')
        browser=a.suite in ('stage2-browser','stage2-label-lifetime','stage2-native-range','stage2-numeric-geometry','stage2-integer-validation','stage2-pair-visibility','stage2-pair-repair','stage4-ui','stage4-browser-derived')
        cumulative_official=a.suite in ('official-stage2-detail','official-stage3-detail','official-stage4-detail')
        if cumulative_official:
            previous_stage = {'official-stage2-detail':1,'official-stage3-detail':2,'official-stage4-detail':3}[a.suite]
            previous_image=ident+':previous-stage'+str(previous_stage)
            command(DOCKER+['build',*labels,'-t',previous_image,str(a.checkout/f'stage-{previous_stage}')],'previous-build.log')
            command(DOCKER+['run','-d','--name',previous,*labels,'--network',network,
                '--network-alias','previous','--cpus','2','--memory','2g','--memory-swap','2g','--read-only',
                '--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777',previous_image],'previous-start.log',60)
            created_previous=True
            command(DOCKER+['run','--rm',*labels,'--network',network,'--entrypoint','python',
                'tablekeeper-test-runner:latest','-c',health_code.replace('tablekeeper:8080','previous:8080')],
                'previous-health.log',60)
        client_image='df-harness-runner' if browser or cumulative_official else 'tablekeeper-test-runner:latest'
        extra_mounts=['-v','/Users/kirillpsinnik/Code/wearedevelopers-hackathon/official:/official:ro'] if official else []
        if a.suite=='stage4-ui':
            # Frozen browser fixtures write /reports/stage4-ui. Preserve their
            # exact source and all screenshots/videos in this owned attempt.
            extra_mounts += ['-v',str(out)+':/reports']
        args = DOCKER+['run','--name',client,*labels,'--network','container:'+service if browser else network,*extra_mounts,
                      '-v',str(ROOT/'qa')+':/qa:ro','-v',str(out)+':/evidence',
                      '-w','/qa','-e','PYTHONPATH=/qa:/official','-e','PYTHONDONTWRITEBYTECODE=1',
                      '-e','QA_EVIDENCE_DIR=/evidence','-e','QA_PRODUCT_SHA='+sha,
                      '-e','QA_SOURCE_SHA='+os.environ.get('QA_SOURCE_SHA',''),
                      '-e','QA_HTTP_METRICS=1','-e','QA_JSON_PARSE_METRICS='+('1' if a.suite=='numeric' else '0'),
                      '-e','STAGE_UNDER_TEST='+str(a.stage),'-e','QA_BROWSER_BASE=http://127.0.0.1:8080',
                      '--entrypoint','python',client_image,'-m','pytest','-p','evidence_plugin','-p','no:cacheprovider',
                      '-q','--tb=short','--junitxml=/evidence/junit.xml',*SUITES[a.suite]]
        if a.suite in ('original','adjudicated'):
            args += ['--target','http://tablekeeper:8080','--case-log','/evidence/frozen-case-log.jsonl']
        if official:
            args += ['-p','harness.plugin','--base-url','http://tablekeeper:8080',
                     '--rootdir=/official/tablekeeper/test','--harness-summary=/evidence/official-counts.json']
        if cumulative_official:
            # Different stages intentionally share test_sample.py basenames.
            # Importlib gives each unchanged source file a distinct module name.
            args += ['--import-mode=importlib','--previous-base-url','http://previous:8080']
        created_client = True
        code = command(args, 'tests.log',1800,check=False)
        command(DOCKER+['inspect',client], 'client-after.json',60,check=False)
        assert not git('status','--porcelain=v1','--untracked-files=all'), 'Checkout changed during build'
        raise SystemExit(code)
    finally:
        if created_previous:
            command(DOCKER+['logs',previous],'previous-service.log',60,check=False)
            command(DOCKER+['inspect',previous],'previous-after.json',60,check=False)
            command(DOCKER+['rm','-f',previous],'previous-remove.log',60,check=False)
        if created_service:
            command(DOCKER+['logs',service], 'service.log',60,check=False)
            command(DOCKER+['inspect',service], 'service-after.json',60,check=False)
        if created_client:
            command(DOCKER+['rm','-f',client], 'client-remove.log',60,check=False)
        if created_service:
            command(DOCKER+['rm','-f',service], 'service-remove.log',60,check=False)
        if created_network:
            command(DOCKER+['network','rm',network], 'network-remove.log',60,check=False)


if __name__ == '__main__':
    main()
