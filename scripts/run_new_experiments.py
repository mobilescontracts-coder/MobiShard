#!/usr/bin/env python3
"""Run the complete preserved experiment design into a fresh runs/<label> directory."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import platform
import subprocess
import sys
from repository_common import ROOT, create_fresh_run, require_checks_enabled, subprocess_environment


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label',default=None,help='New destination name; defaults to a UTC timestamp')
    p.add_argument('--repetitions',type=int,default=2,help='2 for smoke checking; 20 for the paper design')
    a=p.parse_args()
    try:
        require_checks_enabled()
        if not 1<=a.repetitions<=1000:raise ValueError('Repetitions must be between 1 and 1000')
        label=a.label or datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%S%fZ')
        out=create_fresh_run(label)
    except (OSError,ValueError,RuntimeError) as error:
        p.error(str(error))
    command=[sys.executable,str(ROOT/'prototype/run_experiments.py'),'--extended',
             '--repetitions',str(a.repetitions),'--out',str(out)]
    meta={'created_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),
          'command':command,'expected_measured_trials':44*a.repetitions,
          'expected_submissions':44*a.repetitions*256,'output_relative':str(out.relative_to(ROOT)),
          'scope':'New execution; not the paper retained dataset','status':'running'}
    path=out/'repository_run.json';path.write_text(json.dumps(meta,indent=2)+'\n')
    print(f'Running {44*a.repetitions} new measured trials. Output: {out}',flush=True)
    print('Progress and service errors: '+str(out/'runner.log'),flush=True)
    with (out/'runner.log').open('w') as log:
        result=subprocess.run(command,cwd=ROOT,env=subprocess_environment(),stdout=log,stderr=subprocess.STDOUT)
    meta.update(status='completed' if result.returncode==0 else 'failed',
                returncode=result.returncode,ended_utc=datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(meta,indent=2)+'\n')
    print(f'{meta["status"]}: {out.relative_to(ROOT)}')
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
