#!/usr/bin/env python3
"""Check preserved files, recorded source identity, and retained trial structure.

Uses the standard library. Does not execute a performance experiment or establish
CPN equivalence. Fresh reports go below build/, never into retained evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import sys
import xml.etree.ElementTree as ET
from repository_common import ROOT, require_checks_enabled, safe_generated_dir, sha256


def verify() -> dict:
    require_checks_enabled()
    checks = []
    def need(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)
    manifest = json.loads((ROOT/'provenance/source_manifest.json').read_text())
    for item in manifest['preserved_files']:
        path = (ROOT/item['path']).resolve()
        need(path.is_relative_to(ROOT.resolve()), 'Unsafe source-manifest path')
        need(path.is_file(), f'Missing preserved source: {item["path"]}')
        need(sha256(path) == item['sha256'], f'Preserved source changed: {item["path"]}')
    checks.append({'name':'preserved_source_files','count':len(manifest['preserved_files'])})
    env = json.loads((ROOT/'results/deployment/environment.json').read_text())
    for name, digest in env['code_sha256'].items():
        need(sha256(ROOT/'prototype'/name)==digest, f'Executed source differs: prototype/{name}')
    need(sha256(ROOT/'model/msc.cpn') == env['model']['sha256'], 'Recorded model differs')
    tree=ET.fromstring((ROOT/'model/msc.cpn').read_bytes())
    pages=tree.findall('.//page')
    inventory={'pages':len(pages),'places':sum(len(p.findall('place')) for p in pages),
               'transitions':sum(len(p.findall('trans')) for p in pages),
               'arcs':sum(len(p.findall('arc')) for p in pages)}
    need(inventory=={'pages':8,'places':72,'transitions':21,'arcs':141},'Unexpected stored-model inventory')
    checks.append({'name':'original_execution_source_hashes','count':len(env['code_sha256']),
                   'model':inventory})
    with (ROOT/'results/deployment/results.csv').open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    design=json.loads((ROOT/'configs/experiment_design.json').read_text())
    key_fields=['suite','profile','concurrency','arrival','validation_mode','policy','seed']
    keys=[tuple(row[k] for k in key_fields) for row in rows]
    need(len(set(keys))==len(rows)==880, 'Retained trial keys/count differ')
    need(sum(int(r['submitted']) for r in rows)==225280, 'Submission count differs')
    need(sum(int(r['committed']) for r in rows)==77929, 'Commitment count differs')
    need(sum(int(r['trace_events']) for r in rows)==781126, 'Gateway event count differs')
    groups=defaultdict(list); pairs={}
    for r in rows:
        n,a,c,b,d=(int(r[x]) for x in ('submitted','admitted','committed','blocked','denied'))
        need(n==256 and n==c+b+d and a==c+b and min(n,a,c,b,d)>=0,'Invalid outcome accounting')
        need(r['policy'] in design['policies'],'Unknown policy')
        group=tuple(r[k] for k in key_fields[:-1]); groups[group].append(int(r['seed']))
        pair=(r['profile'],r['concurrency'],r['arrival'],r['seed'])
        need(pair not in pairs or pairs[pair]==r['input_sha256'], 'Paired workload hashes differ')
        pairs[pair]=r['input_sha256']
    need(len(groups)==44 and all(sorted(v)==list(range(1,21)) for v in groups.values()),'Unbalanced retained design')
    suites=dict(Counter(r['suite'] for r in rows))
    need(suites=={'main':320,'concurrency':320,'arrival':80,'instrumentation':80,'disconnect':80},'Suite counts differ')
    checks.append({'name':'retained_design','trials':len(rows),'configurations':len(groups),
                   'submissions':225280,'commitments':77929,'gateway_events':781126,'suites':suites})
    def expand(path: Path, seen: set[Path] | None = None) -> str:
        visited = set() if seen is None else set(seen)
        path = path.resolve()
        need(path.is_relative_to(ROOT.resolve()), 'Unsafe LaTeX input path')
        need(path not in visited, 'Recursive LaTeX input')
        visited.add(path)
        text = path.read_text()
        def load(match: re.Match) -> str:
            child = ROOT / match.group(1)
            if not child.suffix:
                child = child.with_suffix('.tex')
            return expand(child, visited)
        return re.sub(r'\\input\{([^}]+)\}', load, text)
    body=expand(ROOT/'paper/sections.tex')
    counts={'sections':len(re.findall(r'\\section\{',body)),
            'subsections':len(re.findall(r'\\subsection\{',body)),
            'tables':len(re.findall(r'\\begin\{table\*?\}',body)),
            'numbered_equations':body.count(r'\begin{equation}'),
            'algorithm_environments':body.count(r'\begin{algorithmic}')}
    need(counts=={'sections':6,'subsections':14,'tables':6,'numbered_equations':8,'algorithm_environments':1},'Manuscript structure changed')
    cites=set()
    for group in re.findall(r'\\cite\{([^}]+)\}',body): cites.update(group.split(','))
    bibkeys=set(re.findall(r'@\w+\s*\{\s*([^,\s]+)',(ROOT/'references.bib').read_text()))
    need(len(cites)==30 and cites<=bibkeys, 'Manuscript citation keys differ or are unresolved')
    labels=set(re.findall(r'\\label\{([^}]+)\}',body))
    refs=set(re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',body))
    need(refs<=labels, f'Unresolved manuscript labels: {refs-labels}')
    checks.append({'name':'manuscript_structure','counts':counts,'citation_keys':len(cites)})
    old_body=(ROOT/'archive/ieee/paper/sections.tex').read_text()
    math_pattern=r'\\begin\{equation\}.*?\\end\{equation\}'
    need(re.findall(math_pattern, body, re.S)==re.findall(math_pattern, old_body, re.S),
         'Numbered equation payloads changed')
    algorithm_pattern=r'\\begin\{algorithmic\}.*?\\end\{algorithmic\}'
    need(re.findall(algorithm_pattern, body, re.S)==re.findall(algorithm_pattern, old_body, re.S),
         'Algorithm payload changed')
    old_cites=set()
    for group in re.findall(r'\\cite\{([^}]+)\}', old_body): old_cites.update(group.split(','))
    need(cites==old_cites,'Citation identity changed')
    source_template=json.loads((ROOT/'provenance/ccis_template.json').read_text())
    for item in source_template['files']:
        need(sha256(ROOT/item['path'])==item['sha256'],'Springer class/style modified')
    checks.append({'name':'ngise_preservation','equations':8,'algorithm':'identical',
                   'citation_keys':'same 30','scientific_record':'unchanged and hash checked'})

    full=ROOT/'MANIFEST.sha256'
    if full.exists():
        count=0
        for line in full.read_text().splitlines():
            if not line.strip():continue
            digest,relative=line.split('  ',1)
            path=(ROOT/relative).resolve()
            need(path.is_relative_to(ROOT.resolve()),'Unsafe integrity-manifest path')
            need(path.is_file() and sha256(path)==digest,f'Integrity mismatch: {relative}')
            count+=1
        checks.append({'name':'assembly_file_manifest','count':count})
    return {'status':'passed','checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'python':platform.python_version(),'checks':checks,
            'scope':'File identity and retained-design validation; not native CPN simulation or new performance evidence.'}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',default='build/verification/integrity.json')
    args=parser.parse_args()
    try:
        path=Path(args.report)
        parent=safe_generated_dir(path.parent)
        result=verify();parent.mkdir(parents=True,exist_ok=True)
        (parent/path.name).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));return 0
    except (ValueError,RuntimeError,OSError,KeyError) as error:
        print(f'Validation failed: {error}',file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
