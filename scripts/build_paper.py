#!/usr/bin/env python3
"""Build the NGISE 2026 Springer CCIS draft and check its 15--17-page limit.

Default: build both anonymous review and named-author preparation copies.
Outputs are written below build/paper; retained evidence is never modified.
The named version is a draft, not evidence of acceptance or camera-ready approval.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from repository_common import ROOT


def build(variant: str) -> dict:
    out = ROOT / 'build/paper'
    out.mkdir(parents=True, exist_ok=True)
    stem = 'main' if variant == 'review' else 'main_author'
    bibtex = shutil.which('bibtex') or shutil.which('bibtex8')
    if not shutil.which('pdflatex') or not bibtex:
        raise RuntimeError('Install pdfLaTeX and BibTeX; see docs/REPRODUCIBILITY.md.')
    latex = ['pdflatex', '-no-shell-escape', '-interaction=nonstopmode',
             '-halt-on-error', '-file-line-error', '-output-directory=build/paper', stem+'.tex']
    commands = [latex, [bibtex, 'build/paper/'+stem], latex, latex]
    for number, command in enumerate(commands, 1):
        logfile = out / f'{stem}-pass-{number}.txt'
        with logfile.open('w') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'{command[0]} failed; {logfile.relative_to(ROOT)}\n'+logfile.read_text(errors='replace')[-4000:])
    log = (out / (stem+'.log')).read_text(errors='replace')
    pages_match = re.search(r'Output written on .*?\((\d+) pages?[,\s]', log, re.S)
    pages = int(pages_match.group(1)) if pages_match else None
    issues = []
    if re.search(r'LaTeX Warning: (?:Citation|Reference).*undefined', log) or 'There were undefined references' in log:
        issues.append('Undefined reference or citation')
    issues.extend(re.findall(r'Overfull \\[hv]box[^\n]*', log))
    if pages is None or not 15 <= pages <= 17:
        issues.append(f'Expected 15--17 total pages, including references; observed {pages}')
    bibitems = len(re.findall(r'\\bibitem(?:\[[^\]]*\])?\{', (out/(stem+'.bbl')).read_text()))
    if bibitems != 30:
        issues.append(f'Expected 30 bibliography entries, observed {bibitems}')
    return {'variant': variant, 'status': 'passed' if not issues else 'review_needed',
            'pdf': f'build/paper/{stem}.pdf', 'pages': pages, 'bibliography_items': bibitems,
            'issues': issues, 'bibliography_engine': Path(bibtex).name,
            'page_limit_source': 'https://ngise.org/call-for-papers',
            'page_count_scope': 'Whole PDF, including title, abstract, code/data policy, declarations and references.',
            'underfull_box_notices': len(re.findall(r'Underfull \\[hv]box',log))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['review', 'author', 'both'], default='both')
    args = parser.parse_args()
    variants = ['review', 'author'] if args.variant == 'both' else [args.variant]
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'target': 'NGISE 2026; Springer CCIS',
              'format': 'Unmodified llncs 2.26 and splncs04; A4; standard 12.2 x 19.3 cm text area.',
              'publication_status': 'Preparation draft; not submitted or accepted by this build.',
              'author_actions': ['Complete competing-interest declaration', 'Review all scientific claims and AI-use disclosure',
                                 'Finalize author metadata, artifact hosting and reuse permissions', 'Confirm conference stage and conflicting public dates'],
              'builds': []}
    try:
        for variant in variants:
            report['builds'].append(build(variant))
        report['status'] = 'passed' if all(x['status']=='passed' for x in report['builds']) else 'review_needed'
    except (OSError, RuntimeError) as error:
        report.update(status='failed', error=str(error))
    out=ROOT/'build/paper'; out.mkdir(parents=True,exist_ok=True)
    (out/'build_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
