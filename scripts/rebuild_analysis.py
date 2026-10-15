#!/usr/bin/env python3
"""Generate statistics without overwriting retained inputs or paper outputs."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from repository_common import ROOT,require_checks_enabled,safe_generated_dir,subprocess_environment,sha256


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=ROOT/'results/deployment/results.csv')
    p.add_argument('--out',default='build/analysis')
    p.add_argument('--check-retained',action='store_true',help='Compare all generated files against retained paper outputs')
    a=p.parse_args()
    try:
        require_checks_enabled()
        out=safe_generated_dir(a.out)
        src=(a.input if a.input.is_absolute() else ROOT/a.input).resolve()
        if not src.is_file():raise ValueError(f'No input CSV: {src}')
        retained=src==(ROOT/'results/deployment/results.csv').resolve()
        if a.check_retained and not retained:raise ValueError('--check-retained requires the original deployment CSV')
        if any(importlib.util.find_spec(n) is None for n in ('numpy','pandas','scipy')):
            raise ValueError('Install analysis dependencies: python -m pip install -r requirements-analysis.txt')
        out.mkdir(parents=True,exist_ok=True)
        result=subprocess.run([sys.executable,str(ROOT/'scripts/analyse_results.py'),'--input',str(src),'--out',str(out)],
                              cwd=ROOT,env=subprocess_environment(),capture_output=True,text=True)
        (out/'analysis.log').write_text(result.stdout+result.stderr)
        if result.returncode:
            print(result.stderr,file=sys.stderr);raise ValueError('Analysis failed; inspect '+str(out/'analysis.log'))
        # The preserved engine has a literal date. Correct only new-output metadata;
        # retain its numerical analysis and original-study output byte-for-byte.
        metadata_file=out/'analysis_manifest.json'
        if not retained:
            data=json.loads(metadata_file.read_text())
            data['legacy_analysis_header_date']=data.pop('date',None)
            envpath=src.parent/'environment.json'
            measured=json.loads(envpath.read_text()) if envpath.exists() else {}
            data['date']=str(measured.get('started_utc',''))[:10] or None
            data['analysis_generated_utc']=datetime.now(timezone.utc).isoformat()
            data['note']='New local experiment, not the paper dataset. Date comes from its environment record; numerical engine unchanged.'
            metadata_file.write_text(json.dumps(data,indent=2)+'\n')
        compared=[]
        if a.check_retained:
            for existing in sorted((ROOT/'results/paper').iterdir()):
                if not existing.is_file():continue
                generated=out/existing.name
                if not generated.is_file() or generated.read_bytes()!=existing.read_bytes():
                    raise ValueError('Generated file differs from retained paper output: '+existing.name)
                compared.append(existing.name)
        report={'status':'passed','input_sha256':sha256(src),'retained_dataset':retained,
                'compared_files':compared,'output':str(out.relative_to(ROOT)),
                'generated_utc':datetime.now(timezone.utc).isoformat()}
        (out/'comparison_report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2));return 0
    except (ValueError,OSError,RuntimeError,KeyError) as error:
        print('Analysis error: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
