"""Hand-derived new QA scenarios checked without any application or Docker."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent/'frozen/supplemental'))
from planning_oracle import solve
from selfcheck_oracle import reservation


def main():
    rows=[]
    def check(name,caps,records,closure,expected,pairs=(),prior=()):
        actual=solve([{'id':k,'capacity':v} for k,v in caps.items()],pairs,records,closure,prior)
        got=None if actual is None else (actual['moved_count'],actual['unused_seats'],
                 {a['reference']:a['table_ids'] for a in actual['assignments']})
        assert got==expected,(name,got,expected)
        rows.append({'id':name,'outcome':'PASS','scope':'QA_DESIGN_NOT_APPLICATION'})
    close={'table_id':'a','from':'2030-01-01T18:00:00Z','to':'2030-01-01T19:00:00Z'}
    for exponent in (16,40,400):
        h=10**exponent; caps={'a':2,'b':4,'c':3,'huge':h}
        records=[reservation('HUGE','huge',1,caps),reservation('MOVE','a',2,caps)]
        check('Q4-exact-common-cost-'+str(exponent),caps,records,close,(1,h,{'HUGE':['huge'],'MOVE':['c']}))
    caps={'a':100,'b':100,'c':100}
    records=[reservation('MOVE','a',2,caps),reservation('OTHER','c',2,caps),reservation('FIXED','b',2,caps,'17:30','18:30')]
    check('Q4-full-interval-refusal',caps,records,{**close,'from':'2030-01-01T18:30:00Z','to':'2030-01-01T18:45:00Z'},None,[['b','a'],['b','c']])
    caps={k:4 for k in 'abcdef'}
    records=[reservation('R'+str(i),'a',2,caps,f'{10+i:02}:00',f'{11+i:02}:00') for i in range(6)]
    check('Q4-inclusive-limits',caps,records,{**close,'from':'2030-01-01T09:00:00Z','to':'2030-01-01T17:00:00Z'},
          (6,12,{'R'+str(i):['b'] for i in range(6)}),[['a','b'],['b','c'],['c','d'],['d','e']])
    caps={'a':100,'b':100,'c':100}
    check('Q4-prior-full-interval',caps,[reservation('MOVE','a',2,caps)],
          {**close,'from':'2030-01-01T18:30:00Z'},(1,98,{'MOVE':['c']}),[['b','a'],['b','c']],
          [{'table_id':'b','from':'2030-01-01T17:30:00Z','to':'2030-01-01T18:30:00Z'}])
    result={'scope':'QA tooling only, no product import or execution','passed':len(rows),'cases':rows,
            'extreme_exponent_design':'For any positive H, (H-1)+(3-2)=H < (H-1)+(4-2)=H+1. Application case additionally uses compact H=1e100000000 without expanding this power.'}
    Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'scope':result['scope'],'passed':len(rows)}))


if __name__=='__main__': main()
