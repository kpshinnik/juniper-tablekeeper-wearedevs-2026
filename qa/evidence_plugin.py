"""Additive pytest evidence only; frozen test bytes/assertions stay unchanged.

Load explicitly with -p evidence_plugin and PYTHONPATH=<checkout>/qa. Collection
is preparation, never an application execution. HTTP metrics are opt-in and
record metadata, never authentication headers or response payloads.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import threading
import time

import pytest

_lock = threading.Lock()
_active = 0
_maximum = 0
_case = None


def case_id(item):
    source = Path(str(item.path)).resolve()
    try:
        relative = str(source.relative_to(Path(__file__).resolve().parent))
    except ValueError:
        relative = 'official/' + str(source).split('/official/', 1)[-1]
    return relative + '::' + item.nodeid.split('::', 1)[-1]


def emit(filename, value):
    directory = os.environ.get('QA_EVIDENCE_DIR')
    if not directory:
        return
    value = {'at': datetime.now(timezone.utc).isoformat(), **value}
    with _lock:
        with (Path(directory) / filename).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=True, default=str) + '\n')


def install_json_parse_metrics():
    """Observe the original complete decoder; never replace or stream the oracle."""
    original=json.loads
    def measured(value,*args,**kwargs):
        if not isinstance(value,(str,bytes,bytearray)) or len(value)<65536:
            return original(value,*args,**kwargs)
        import resource
        tick=time.monotonic()
        row={'case':_case,'input_bytes_or_chars':len(value),'input_type':type(value).__name__,
             'parse_int':getattr(kwargs.get('parse_int'),'__name__',None),
             'parse_float':getattr(kwargs.get('parse_float'),'__name__',None),
             'client_memory_cap_added':False,'rss_peak_before':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'rss_peak_units':'KiB' if platform.system()=='Linux' else 'platform_native'}
        try:
            result=original(value,*args,**kwargs)
            row.update(outcome='COMPLETED',result_type=type(result).__name__)
            return result
        except BaseException as exc:
            row.update(outcome='ERROR',exception=type(exc).__name__)
            raise
        finally:
            row['complete_parse_s']=time.monotonic()-tick
            row['rss_peak_after']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            emit('json-parse.jsonl',row)
    json.loads=measured


def pytest_configure(config):
    emit('session.jsonl', {'kind': 'COLLECTION' if config.option.collectonly else 'EXECUTION',
                          'product_revision': os.environ.get('QA_PRODUCT_SHA'),
                          'qa_revision': os.environ.get('QA_SOURCE_SHA'),
                          'stage': os.environ.get('STAGE_UNDER_TEST'),
                          'python': platform.python_version(), 'platform': platform.platform(),
                          'client_memory_limit': os.environ.get('QA_CLIENT_MEMORY_LIMIT', 'uncapped'),
                          'service_limits': {'cpus': 2, 'memory_gib': 2}})
    if os.environ.get('QA_JSON_PARSE_METRICS')=='1':
        install_json_parse_metrics()
    if os.environ.get('QA_HTTP_METRICS') != '1':
        return
    import httpx
    original = httpx.Client.send

    def measured(self, request, *args, **kwargs):
        global _active, _maximum
        tick = time.monotonic()
        with _lock:
            _active += 1
            _maximum = max(_maximum, _active)
            inflight = _active
        row = {'case': _case, 'method': request.method, 'path': request.url.path,
               'inflight_at_start': inflight, 'stream': bool(kwargs.get('stream'))}
        try:
            response = original(self, request, *args, **kwargs)
            row.update(status=response.status_code,
                       content_encoding=response.headers.get('content-encoding'),
                       declared_content_length=response.headers.get('content-length'),
                       received_decompressed_bytes=len(response.content) if response.is_stream_consumed else None)
            return response
        except BaseException as exc:
            row.update(exception=type(exc).__name__)
            raise
        finally:
            row['send_receive_decompression_s'] = time.monotonic() - tick
            with _lock:
                _active -= 1
            emit('http-requests.jsonl', row)
    httpx.Client.send = measured


def pytest_collection_finish(session):
    for item in session.items:
        source = Path(str(item.path))
        emit('catalog.jsonl', {'id': case_id(item), 'native_nodeid': item.nodeid,
                              'definition': case_id(item).replace('baseline-adjudicated/', 'baseline-original/'),
                              'description': (item.obj.__doc__ or '').strip(),
                              'source': str(source), 'line': item.location[1] + 1,
                              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                              'stage': os.environ.get('STAGE_UNDER_TEST'),
                              'application_outcome': 'NOT_RUN'})


def pytest_runtest_logstart(nodeid, location):
    global _case
    _case = nodeid


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    result = yield
    report = result.get_result()
    if report.when != 'call' and report.passed:
        return
    outcome = 'PASS' if report.passed else ('SKIP' if report.skipped else ('FAIL' if report.when == 'call' else 'ERROR'))
    emit('cases.jsonl', {'id': case_id(item), 'native_nodeid': item.nodeid, 'phase': report.when, 'outcome': outcome,
                        'description': (item.obj.__doc__ or '').strip(),
                        'expected': 'All unchanged assertions in the hashed test definition hold',
                        'observed': str(report.longrepr) if not report.passed else 'All assertions completed',
                        'duration_s': report.duration, 'metrics': dict(report.user_properties),
                        'product_revision': os.environ.get('QA_PRODUCT_SHA'),
                        'test_sha256': hashlib.sha256(Path(str(item.path)).read_bytes()).hexdigest()})


def pytest_sessionfinish(session, exitstatus):
    emit('session.jsonl', {'exitstatus': int(exitstatus), 'max_measured_httpx_inflight': _maximum,
                          'kind': 'COLLECTION_END' if session.config.option.collectonly else 'EXECUTION_END'})
