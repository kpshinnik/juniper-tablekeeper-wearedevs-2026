"""Check the independent planner oracle on hand-derived examples, without a service.

These checks validate QA tooling and never count as application passes.
"""
import copy
import json
import pathlib
import sys
from planning_oracle import solve


def reservation(ref, table, party, capacities, start='18:00', end='19:00'):
    return {'reference':ref,'table_ids':[table],'party_size':party,'status':'confirmed',
            'starts_at':'2030-01-01T'+start+':00+00:00','ends_at':'2030-01-01T'+end+':00+00:00',
            'accepted_terms':{'capacities':dict(capacities)}}


def check():
    rows=[]
    def run(name,caps,records,expected,pairs=(),end='19:00'):
        tables=[{'id':k,'capacity':v} for k,v in caps.items()]
        closure={'table_id':'a','from':'2030-01-01T18:00:00+00:00','to':'2030-01-01T'+end+':00+00:00'}
        original=copy.deepcopy(records)
        actual=solve(tables,pairs,records,closure)
        objective=None if actual is None else [actual['moved_count'],actual['unused_seats'],actual['rank_vector']]
        assert objective==expected,(name,objective,expected)
        assert records==original
        rows.append({'id':name,'kind':'QA self-check, not application test','expected':expected,'observed':objective,'outcome':'passed'})
    c={'a':2,'b':2,'c':4}
    run('O001-minimum-moved-before-ranks',c,[reservation('R1','a',2,c),reservation('R2','b',2,c)],[1,2,[2,1]])
    run('O002-minimum-unused',c,[reservation('R1','a',1,c)],[1,1,[1]])
    c={'a':2,'b':2,'c':2}
    run('O003-rank-tiebreak',c,[reservation('R1','a',2,c)],[1,0,[1]])
    c={'a':4,'b':2,'c':2}
    run('O004-pair-required',c,[reservation('R1','a',4,c)],[1,0,[3]],[['b','c']])
    run('O005-no-feasible-plan',c,[reservation('R1','a',4,c)],None)
    c={'a':2,'b':2,'c':2}
    run('O006-fixed-booking-outside-closure',c,[reservation('R1','a',2,c),reservation('R2','b',2,c,'18:30','19:30')],[1,0,[2]],end='18:30')
    run('O007-empty-considered-set',c,[reservation('R1','a',2,c,'20:00','21:00')],[0,0,[]])
    # Both books overlap closure but not each other; the same remaining table is reusable.
    c={'a':2,'b':2}
    run('O008-half-open-temporal-reuse',c,[reservation('R1','a',2,c,'18:00','18:30'),reservation('R2','a',2,c,'18:30','19:00')],[2,0,[1,1]])
    return rows


if __name__=='__main__':
    rows=check()
    result={'scope':'QA tooling only; no Stage 4 application was executed','cases':rows,'passed':len(rows),'failed':0}
    if len(sys.argv)>1:
        p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'scope':result['scope'],'passed':len(rows),'failed':0}))
