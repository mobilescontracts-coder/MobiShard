#!/usr/bin/env python3
"""Rebuild paper tables and plot data from the retained IEEE-revision trials.
Requires pandas, numpy, scipy. Uses trial-level, paired-seed t intervals.
"""
from pathlib import Path
import json
import argparse
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import t
B=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=B/'results/deployment/results.csv')
parser.add_argument('--out', type=Path, default=B/'results/paper')
args=parser.parse_args()
O=args.out; O.mkdir(parents=True,exist_ok=True)
d=pd.read_csv(args.input)
assert len(d)>0 and not d.duplicated(['suite','profile','concurrency','arrival','validation_mode','policy','seed']).any()
if set(d.suite) != {'main','concurrency','arrival','instrumentation','disconnect'}:
    raise ValueError('Table generation requires the complete --extended experiment design.')
repetitions=d.groupby(['suite','profile','concurrency','arrival','validation_mode','policy']).size()
if repetitions.nunique()!=1 or repetitions.iloc[0]<2:
    raise ValueError('At least two equal repetitions per configuration are required for sample statistics.')
n_reps=int(repetitions.iloc[0])
keys=['suite','profile','concurrency','arrival','validation_mode','policy']
metrics=['admitted','committed','blocked','denied','elapsed_s','mean_latency_ms','p95_latency_ms','wasted_cpu','wasted_battery']
out=[]
for key,g in d.groupby(keys):
    z=dict(zip(keys,key)); z['n']=len(g)
    assert len(g)==n_reps
    for m in metrics:
        a=g[m].to_numpy(); z[m+'_mean']=a.mean(); z[m+'_sd']=a.std(ddof=1)
        z[m+'_ci95']=t.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a))
    out.append(z)
s=pd.DataFrame(out);s.to_csv(O/'summary.csv',index=False)
names={'stagewise':'Stagewise','precheck':'Precheck','reserve':'Reservation','serial':'Serial'}
profiles={'default':'Deposit-limited','cpu':'Computation-limited','battery':'Battery-budget-limited','mixed':'Mixed'}
rows=[]
for p in profiles:
    g=s[(s.suite=='main')&(s.profile==p)].set_index('policy')
    for pol in names:
        z=g.loc[pol]
        rows.append(f"{profiles[p] if pol=='stagewise' else ''} & {names[pol]} & {z.admitted_mean:.0f} & {z.committed_mean:.2f} $\\pm$ {z.committed_sd:.2f} & {z.blocked_mean:.2f} & {z.denied_mean:.0f} & {z.wasted_cpu_mean:.2f} \\\\")
    rows.append('\\addlinespace[2pt]')
(O/'outcome_rows.tex').write_text('\n'.join(rows[:-1])+'\n')
rows=[]
for pol in names:
    z=s[(s.suite=='main')&(s.profile=='cpu')&(s.policy==pol)].iloc[0]
    f=s[(s.suite=='instrumentation')&(s.policy==pol)].iloc[0]
    rows.append(f"{names[pol]} & {1000*z.elapsed_s_mean:.1f} $\\pm$ {1000*z.elapsed_s_sd:.1f} & {1000*f.elapsed_s_mean:.1f} $\\pm$ {1000*f.elapsed_s_sd:.1f} & {z.mean_latency_ms_mean:.1f} & {z.p95_latency_ms_mean:.1f} \\\\")
(O/'timing_rows.tex').write_text('\n'.join(rows)+'\n')
rows=[]
for pol in names:
    z=s[(s.suite=='disconnect')&(s.policy==pol)].iloc[0]
    rows.append(f"{names[pol]} & {z.admitted_mean:.0f} & {z.committed_mean:.2f} & {z.blocked_mean:.2f} & {z.denied_mean:.0f} & {z.wasted_cpu_mean:.2f} \\\\")
(O/'disconnect_rows.tex').write_text('\n'.join(rows)+'\n')
cc=s[(s.suite=='concurrency')|((s.suite=='main')&(s.profile=='cpu'))]
for pol in names:
    g=cc[cc.policy==pol].sort_values('concurrency')
    pd.DataFrame({'cap':g.concurrency,'mean':g.committed_mean,'ci':g.committed_ci95,'runtime_ms':1000*g.elapsed_s_mean}).to_csv(O/f'concurrency_{pol}.csv',index=False)
g=s[(s.suite=='main')&(s.profile=='cpu')].set_index('policy').loc[list(names)]
pd.DataFrame({'policy':[names[i] for i in g.index],'committed':g.committed_mean.values,'blocked':g.blocked_mean.values,'denied':g.denied_mean.values}).to_csv(O/'cpu_outcomes.csv',index=False)
# Paired difference = B - A. Shared input seeds, not request-level samples.
pairs=[]
def paired(label,a,b,m):
    x=a.set_index('seed')[m];y=b.set_index('seed')[m]; assert set(x.index)==set(y.index)
    v=(y-x).to_numpy(); n=len(v); c=t.ppf(.975,n-1)*v.std(ddof=1)/np.sqrt(n)
    z={'comparison':label,'metric':m,'n':n,'difference_mean':v.mean(),'ci_low':v.mean()-c,'ci_high':v.mean()+c};pairs.append(z)
for p in profiles:
    g=d[(d.suite=='main')&(d.profile==p)]
    for other in ['stagewise','precheck','serial']:
        for metric in ['committed','elapsed_s','mean_latency_ms']:
            paired(f'{p}: reserve - {other}',g[g.policy==other],g[g.policy=='reserve'],metric)
for pol in names:
    a=d[(d.suite=='main')&(d.profile=='cpu')&(d.policy==pol)]
    b=d[(d.suite=='instrumentation')&(d.policy==pol)]
    paired(f'{pol}: full - operational',a,b,'elapsed_s')
pd.DataFrame(pairs).to_csv(O/'paired_differences.csv',index=False)
report={'trials':len(d),'requests':int(d.submitted.sum()),'commits':int(d.committed.sum()),'groups':len(s),'seed_repetitions':n_reps,'source_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),'date':'2026-09-08','note':'All data are measured local prototype trials. CI unit is a trial, not a request.'}
(O/'analysis_manifest.json').write_text(json.dumps(report,indent=2))
print(pd.DataFrame(pairs).round(5).to_string(index=False))
