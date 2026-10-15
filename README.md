# MobiShard
## Lifecycle-Aware Resource Reservation for Mobile Smart-Contract Validation

**NGISE 2026 / Springer CCIS preparation · local version `v0.2.0-ngise2026`.**
The repository packages the revised paper, unchanged CPN and six-service
prototype, retained experimental evidence, and reproduction tools. No external
submission, acceptance, public release or hosted repository update is claimed.
The default PDF is anonymous; the repository itself is **not anonymous**.

[Submission checklist](docs/NGISE2026_SUBMISSION.md) ·
[Reproduction guide](docs/REPRODUCIBILITY.md) ·
[Evidence map](docs/EVIDENCE_MAP.md) ·
[Revision notes](docs/NGISE2026_REVISION.md) ·
[Limitations](docs/KNOWN_LIMITATIONS.md)

## Paper and conference format

The [NGISE call for papers](https://ngise.org/call-for-papers) gives 15–17 pages
for long camera-ready papers and 6–8 for short papers, and specifies double-blind
review. This is a **long-paper preparation**. Both variants compile to **17 pages
including references, code/data policy and declarations**. They use the unmodified
`llncs` class and `splncs04` style, without reduced margins or line spacing.

| File | Purpose |
|---|---|
| [`paper/MobiShard_NGISE_Review.pdf`](paper/MobiShard_NGISE_Review.pdf) | Anonymous review preparation PDF |
| [`paper/MobiShard_NGISE_Author.pdf`](paper/MobiShard_NGISE_Author.pdf) | Named-author preparation PDF, not a camera-ready certification |
| [`main.tex`](main.tex) | Default anonymous LaTeX entry |
| [`main_author.tex`](main_author.tex) | Named-author LaTeX entry |
| [`paper/sections/`](paper/sections/) | Five principal sections plus Code and Data Policy |
| [`paper/objects/`](paper/objects/) | Eight equations, algorithm, and six tables |
| [`figures/architecture_ngise.tikz`](figures/architecture_ngise.tikz) | Editable CCIS-sized architecture with corrected terminal paths |
| [`archive/ieee/`](archive/ieee/) | Previous manuscript; tag `v0.1.0` restores the older complete build |

An explicit unfinished **Disclosure of Interests** remains for the authors.
Affiliations, public hosting, reuse permissions and AI-use wording also require
author review. The prose is revised for clarity, not certified by a detector.
No Turnitin or similarity test was run and no AI-writing score is promised.

**Dates need confirmation.** On 11 October 2026 the homepage listed camera-ready
10 November, whereas the CFP listed 30 September. Both listed 30 July for original
submission. This package does not establish that new submission is currently
permitted; see the dated source record in the submission checklist.

## Mechanism and evidence

MobiShard reserves an admitted request's remaining validation cost before shard
dispatch, consumes it stage by stage, and releases unused holds on handled
termination. Resource ownership is separate from execution placement. A gateway,
four shard workers and a root-policy service execute locally. Candidate construction
remains in the gateway. Completion is a local commitment record, not consensus
finality. Fixed stage costs are `(2,3)`, `(1,2)`, `(1,2)` in logical battery and
computation units, with a separate admission deposit of 15.

The retained dataset contains **880 trials, 225,280 submissions, 77,929 local
commitments and 781,126 gateway events**. It was not replaced or extended during
this revision. The older repository smoke test is still separate.

| Profile | Stagewise | Precheck | Reservation | Serial |
|---|---:|---:|---:|---:|
| Deposit-limited | 96.00 | 96.00 | 96.00 | 96.00 |
| Computation-limited | 72.40 | 72.35 | 80.00 | 80.00 |
| Battery-budget-limited | 72.45 | 72.40 | 80.00 | 80.00 |
| Mixed | 90.75 | 90.25 | 96.00 | 96.00 |

These are mean completions per 256 submissions over 20 repetitions, not production
transactions per second. Reservation and serialization reach the same static
budget bound. Timing benefits depend on workload; modeled connectivity loss exposes
more admitted requests under Reservation. No physical energy, smart-contract VM,
live blockchain or native CPN simulator is evaluated.

## Quick start

Use Python 3.13.5 for the closest match to the original environment. Services,
tests and replay use the standard library; analysis uses pinned dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-analysis.txt
python scripts/run_checks.py
python scripts/build_paper.py
```

On Windows activate `.venv\Scripts\Activate.ps1` in PowerShell; the service
experiment was tested on Linux, not native Windows. Do not use Python `-O` or
`PYTHONOPTIMIZE`: the preserved code uses assertions. For dependency-free checks
use `python scripts/run_checks.py --skip-analysis`.

The paper builder requires pdfLaTeX and BibTeX (or bibtex8). By default it builds
both variants under `build/paper/`, checks 15–17 total pages, 30 resolved references
and no overfull boxes. It does not certify editorial eligibility or author approval.

```bash
python scripts/build_paper.py --variant review
python scripts/build_paper.py --variant author
```

In Overleaf select `main.tex` or `main_author.tex` and pdfLaTeX. The paper-only
source ZIP is convenient, but contains identities. For double-blind paper review,
use the anonymous PDF, not the full repository or source archive.

## New experiments without overwriting retained data

```bash
python scripts/run_new_experiments.py --label my-smoke --repetitions 2
python scripts/verify_traces.py --input runs/my-smoke --report runs/my-smoke/replay.json
python scripts/rebuild_analysis.py --input runs/my-smoke/results.csv --out runs/my-smoke/analysis
# Full design: 20 repetitions × 44 configurations = 880 trials.
python scripts/run_new_experiments.py --label my-replication --repetitions 20
```

The wrapper refuses existing destinations and writes only under `runs/`. The
legacy runner's default points to retained observations: do not invoke it without
a safe new output. Seeds pair workloads, not operating-system schedules.

## Repository map

```text
main.tex, main_author.tex   Anonymous / author CCIS build entry points
paper/                     Current text, equation/table objects and cached PDFs
figures/                   Editable architecture and unchanged result plots
model/msc.cpn              Unchanged, hash-pinned CPN specification
prototype/                 Measured implementation and 19 original unit tests
scripts/, tests/           Replay, analysis, safe wrappers and repository tests
results/deployment/        Retained observations and separately stored warm-ups
results/paper/             Retained numerical tables, plot inputs and statistics
results/excluded/          Earlier observations excluded from paper analysis
archive/ieee/              Previous manuscript snapshot
configs/, provenance/     Experiment design, NGISE rules, hashes and lineage
verification/ngise2026/    Checks actually performed for this revision
research/                  Bibliography metadata and historical audit qualifications
docs/                      Reproduction, evidence, limitations and submission guides
.github/workflows/         CI definitions; no hosted run is claimed
```

## Attribution and release

The supplied authors are Vipin Deval, Vimal Dwivedi, Alex Norta and Dirk Draheim.
`CITATION.cff` names NGISE only as a preparation target, not an accepted venue.
No DOI or public artifact URL is invented. Project-wide reuse permissions remain
undecided in `LICENSE.md`. Original third-party notices remain; no font files are
bundled. Consult the [hosting guide](docs/PUBLISHING.md) before publishing.
