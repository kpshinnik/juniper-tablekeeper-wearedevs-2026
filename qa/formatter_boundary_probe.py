"""Independent source experiment, separate from HTTP counts and real IANA cases."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import time


def coordinate(value):
    offset=value.utcoffset()
    return ((value.toordinal()-1)*86400+value.hour*3600+value.minute*60+value.second)*1000000+value.microsecond-(offset.days*86400+offset.seconds)*1000000-offset.microseconds


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage-path',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();sys.path.insert(0,str(a.stage_path.resolve()));domain=importlib.import_module('domain')
    rows=[]
    for date in ['0001-01-01T00:00:00','9999-12-31T23:59:59']:
        for seconds in [3208,-3208]:
            tick=time.monotonic();original=datetime.fromisoformat(date).replace(tzinfo=timezone(timedelta(seconds=seconds)))
            actual=domain.timestamp(original);expected=coordinate(original)
            assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}',actual),actual
            assert coordinate(datetime.fromisoformat(actual))==expected,(date,seconds,actual)
            rows.append({'id':'D127-formatter-'+date+'-'+str(seconds),'description':'Exact RFC3339 formatter for a fixed second offset at a calendar extremum; synthetic offset, not future IANA rules',
                'expected_instant_us':expected,'observed':actual,'outcome':'PASS','duration_s':time.monotonic()-tick,
                'http_requests':0,'product_source_sha256':hashlib.sha256((a.stage_path/'domain.py').read_bytes()).hexdigest(),
                'test_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    a.out.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    print(json.dumps({'source_formatter_executions':len(rows),'outcome':'PASS','http_requests':0,'rows':rows}))


if __name__=='__main__':main()
