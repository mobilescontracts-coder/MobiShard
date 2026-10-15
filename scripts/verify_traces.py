#!/usr/bin/env python3
"""Independently replay resource accounting from retained deployment events.

This verifies measured prototype traces, not reachability in the original CPN.
Read-only: no benchmark observations are changed.
"""
from pathlib import Path
from collections import Counter
import csv
import gzip
import json
import math
import argparse
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'prototype'))
from artifact import COSTS, NP, MODEL, TOTAL_B, TOTAL_C

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=BASE/'results/deployment', help='Directory containing results.csv and traces.jsonl.gz')
parser.add_argument('--report', type=Path, default=BASE/'results/trace_verification.json', help='Output JSON report; input observations are read-only')
args = parser.parse_args()
rows = list(csv.DictReader((args.input/'results.csv').open()))
if not rows:
    raise ValueError('No trials found in input CSV.')
def key_of(r):
    return (r['suite'],r['profile'],int(r['concurrency']),r['arrival'],r['validation_mode'],r['policy'],int(r['seed']))
lookup = {key_of(r):r for r in rows}
assert len(lookup)==len(rows)
paired_inputs={}
for r in rows:
    k=(r['profile'],int(r['concurrency']),r['arrival'],int(r['seed']))
    if k in paired_inputs: assert paired_inputs[k]==r['input_sha256']
    paired_inputs[k]=r['input_sha256']
seen=set()
events_total=0
commits_total=0
with gzip.open(args.input/'traces.jsonl.gz','rt') as f:
    for line in f:
        tr=json.loads(line)
        s=tr['summary']
        key=key_of(s)
        assert key not in seen and key in lookup
        seen.add(key)
        for field in ['submitted','admitted','committed','blocked','denied','wasted_cpu','wasted_battery']:
            assert float(s[field])==float(lookup[key][field])
        accounts=[dict(d,hb=0,hc=0) for d in tr['config']['devices']]
        requests=tr['gateway']['requests']
        holds={}
        stages={}
        outcomes={}
        deposits=0
        active=Counter()
        for e in tr['gateway']['events']:
            rid,event=e['rid'],e['event']
            r=requests[rid]
            d=accounts[r['uid']]
            if event=='admitted':
                assert d['w'] >= NP['minDeposit']
                active[r['uid']]+=1
                if s['policy']=='serial': assert active[r['uid']]==1
                if s['policy']!='stagewise':
                    hb,hc=(d['hb'],d['hc']) if s['policy']=='reserve' else (0,0)
                    assert d['b']-hb >= TOTAL_B and d['c']-hc >= TOTAL_C and d['net']!=0
                d['w']-=NP['minDeposit']
                holds[rid]=[TOTAL_B,TOTAL_C] if s['policy']=='reserve' else [0,0]
                d['hb']+=holds[rid][0]; d['hc']+=holds[rid][1]
                stages[rid]=[]
            elif event in COSTS:
                cb,cc=COSTS[event]
                assert d['b']>=cb and d['c']>=cc and d['net']!=0
                assert stages[rid] == list(COSTS)[:list(COSTS).index(event)]
                stages[rid].append(event)
                d['b']-=cb; d['c']-=cc
                if s['policy']=='reserve':
                    holds[rid][0]-=cb; holds[rid][1]-=cc
                    d['hb']-=cb; d['hc']-=cc
                assert (d['b'],d['c'],d['hb'],d['hc']) == (e['b'],e['c'],e['held_b'],e['held_c'])
                if event=='block':deposits+=NP['minDeposit']
            elif event=='guard_blocked':
                cb,cc=COSTS[e['phase']]
                assert d['net']==0 or d['b']<cb or d['c']<cc
            elif event=='disconnect':
                d['net']=0
            elif event=='routed':
                assert e['sid']==MODEL['mapping'][e['cid']]
            elif event in ('committed','blocked'):
                assert rid not in outcomes
                outcomes[rid]=event
                active[r['uid']]-=1
                if event=='committed':assert stages[rid]==['block','proof','root']
                d['hb']-=holds[rid][0];d['hc']-=holds[rid][1]
                holds[rid]=[0,0]
            elif event=='denied':
                assert rid not in outcomes
                assert (r['cid'] not in MODEL['mapping'] or d['w']<NP['minDeposit'] or
                        (s['policy']!='stagewise' and (d['net']==0 or
                         d['b']-(d['hb'] if s['policy']=='reserve' else 0)<TOTAL_B or
                         d['c']-(d['hc'] if s['policy']=='reserve' else 0)<TOTAL_C)))
                outcomes[rid]='denied'
            else:
                raise AssertionError('Unknown trace event '+event)
            assert min(d[x] for x in ['w','b','c','hb','hc'])>=0
            if s['policy']=='reserve':
                assert d['b']>=d['hb'] and d['c']>=d['hc']
                own=[h for req,h in holds.items() if requests[req]['uid']==r['uid']]
                assert d['hb']==sum(h[0] for h in own) and d['hc']==sum(h[1] for h in own)
        assert all(v==0 for v in active.values())
        counts=Counter(outcomes.values())
        assert len(outcomes)==s['submitted']==256
        assert counts['committed']==s['committed'] and counts['blocked']==s['blocked'] and counts['denied']==s['denied']
        assert deposits==tr['gateway']['deposit_balance']
        for uid,d in enumerate(accounts):
            final=tr['gateway']['devices'][str(uid)]
            assert all(d[k]==final[k] for k in ['w','b','c','net'])
            assert d['hb']==d['hc']==0
        commits=tr['root']['commits']
        assert len(commits)==len({c['bid'] for c in commits})==s['committed']
        for c in commits:
            assert outcomes[c['rid']]=='committed'
            assert tr['root']['decisions'][str(c['bid'])] is True
            assert c['commit_ns']-c['decision_ns']>=s['tau_ms']*10*1e6
        assert sum(requests[r]['spent_c'] for r,v in outcomes.items() if v=='blocked')==s['wasted_cpu']
        events_total+=len(tr['gateway']['events'])
        commits_total+=len(commits)
assert seen==set(lookup) and len(seen)==len(rows)
report={'verified_trials':len(seen),'submitted_requests':len(seen)*256,
        'committed_requests':commits_total,'events_replayed':events_total,
        'recorded_violations':0, 'paired_input_signatures_verified':True,
        'serial_owner_nonoverlap_verified':True,
        'scope':'Independent accounting replay of prototype traces; not original-CPN reachability verification'}
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
