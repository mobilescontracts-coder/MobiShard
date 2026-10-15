#!/usr/bin/env python3
"""Run local artifact checks with outputs kept separate from retained evidence."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
import platform
import subprocess
import sys
from repository_common import ROOT,require_checks_enabled,subprocess_environment


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skip-analysis',action='store_true');a=p.parse_args()
    try:require_checks_enabled()
    except RuntimeError as error:print(error,file=sys.stderr);return 1
    out=ROOT/'build/verification';out.mkdir(parents=True,exist_ok=True)
    jobs=[('integrity',[sys.executable,'scripts/validate_repository.py']),
          ('prototype_unit_tests',[sys.executable,'-m','unittest','discover','-s','prototype','-p','test_*.py','-v']),
          ('repository_unit_tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v']),
          ('retained_replay',[sys.executable,'scripts/verify_traces.py','--report','build/verification/retained_replay.json'])]
    if not a.skip_analysis:jobs.append(('retained_analysis',[sys.executable,'scripts/rebuild_analysis.py','--check-retained']))
    report={'started_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
            'platform':platform.platform(),'analysis_skipped':a.skip_analysis,'checks':[],
            'scope':'Rechecks existing evidence. No new performance trials are run by this command.'}
    for name,command in jobs:
        print(f'Checking {name} ...',flush=True)
        with (out/f'{name}.log').open('w') as stream:
            r=subprocess.run(command,cwd=ROOT,env=subprocess_environment(),stdout=stream,stderr=subprocess.STDOUT)
        report['checks'].append({'name':name,'returncode':r.returncode,'log':f'build/verification/{name}.log'})
        if r.returncode:
            print((out/f'{name}.log').read_text()[-5000:],file=sys.stderr);break
    report['status']='passed' if len(report['checks'])==len(jobs) and all(x['returncode']==0 for x in report['checks']) else 'failed'
    report['ended_utc']=datetime.now(timezone.utc).isoformat()
    report['analysis_packages']={}
    for name in ('numpy','pandas','scipy'):
        try:report['analysis_packages'][name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:pass
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
