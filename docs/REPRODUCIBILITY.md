# Reproducing the artifact

## Three different tasks

1. **Recheck supplied records:** validate hashes, run the existing tests, replay
   stored events, and regenerate the paper's table/plot inputs. This does not run
   a new performance experiment.
2. **Smoke-test the service implementation:** run the complete design with two
   repetitions per configuration. This checks executability of all suites; it is
   not a replacement for the paper's 20-repetition dataset.
3. **Replicate the design on a new host:** run 20 repetitions and retain a new
   environment record. Timing and scheduling-sensitive outcomes need not match
   the original machine.

## Environment

The original `environment.json` records Python 3.13.5, Linux x86_64, five exposed
logical processors, a four-CPU-equivalent cgroup quota, and 4 GiB of memory.
Model units were mapped to 1 ms: edge 2, block 5, and local commitment 10 ms.
No production-chain or wireless calibration was used.

Python's standard library suffices for the services, tests, and trace replay.
Analysis was generated with NumPy 2.3.5, pandas 2.2.3, and SciPy 1.17.0;
`requirements-analysis.txt` preserves those versions. Internet is needed to
install dependencies, not to execute the local experiment or read retained data.
Use an isolated environment. No wallet keys, external node, CPN Tools installation,
cloud account, or blockchain funding is required.

## Read-only verification

```bash
python scripts/run_checks.py
```

This writes fresh logs to `build/verification/` and performs:
- preserved-file and executed-source hash checks;
- the 19 original prototype tests and the separate repository utility tests;
- full replay of `results/deployment/traces.jsonl.gz` against `results.csv`;
- regenerated analysis in `build/analysis/` and comparison with `results/paper/`.

Use `--skip-analysis` without third-party Python packages. Inspect output logs
before interpreting a pass. Run without `-O`; assertions in the original runtime
and replay must stay active. Hash equality establishes identity, not correctness.
The replay is a separate checker, not an independently developed implementation
or exhaustive CPN verification.

To invoke individual operations:

```bash
python scripts/validate_repository.py
python -m unittest discover -s prototype -p 'test_*.py' -v
python scripts/verify_traces.py --report build/verification/retained_replay.json
python scripts/rebuild_analysis.py --check-retained
```

## Fresh experiments

```bash
python scripts/run_new_experiments.py --label replication-01 --repetitions 20
```

Every invocation uses `--extended` and covers all five suites. The safe wrapper
creates a new directory under `runs/`, refuses reuse, and records its own invocation.
The original five `prototype/*.py` files are not edited. It resets logical state
between trials but reuses processes, just as the retained experiment did.

For quick integration testing, use two repetitions. Each repetition contains 44
configurations and each trial submits 256 requests. Four warm-ups occur before
measured trials. Two repetitions therefore yield 88 measured trials and 22,528
submissions, plus separately stored warm-ups. At least two repetitions are needed
for sample standard deviations and intervals in the analysis script.

```bash
python scripts/verify_traces.py --input runs/replication-01 --report runs/replication-01/replay.json
python scripts/rebuild_analysis.py --input runs/replication-01/results.csv --out runs/replication-01/analysis
```

A nominal arrival spacing of 2 ms applies only to the `arrival` suite, not every
trial. The old runner's docstring says every experiment is a burst; its executable
`arrival` branch and the manuscript describe the staggered case correctly.

### Protect the supplied evidence

The old `prototype/run_experiments.py` defaults to `results/deployment` and opens
its CSV and gzip files for writing. Do not call it with that destination. The new
wrapper restricts all outputs to a fresh `runs/<label>` directory. The analysis
wrapper likewise refuses writes under `results/` or `provenance/`.

The preserved analysis engine has a literal `2026-09-08` metadata date. For a new
input dataset, the new wrapper records that legacy value separately and takes the
actual measurement date from the new `environment.json`. This corrects metadata
only; it does not change the engine's computations. With the retained input, its
output is left unchanged for exact comparison.

## Build the NGISE / Springer CCIS paper

Install pdfLaTeX, BibTeX or bibtex8, `amsmath`, `amssymb`, `graphicx`, `booktabs`,
`array`, `multirow`, `tabularx`, `algorithmic`, `tikz`, `pgfplots`, `hyperref` and
`microtype`. Unmodified `llncs` and `splncs04` files are bundled; TeX fonts are not.

```bash
python scripts/build_paper.py                   # both variants
python scripts/build_paper.py --variant review # anonymous
python scripts/build_paper.py --variant author # supplied authors
```

Outputs are `build/paper/main.pdf` and `build/paper/main_author.pdf`, a JSON report
and pass logs. Compilation uses no shell escape. Checks cover 15–17 total pages,
30 references, unresolved citations/references and overfull boxes. They do not
certify all editorial requirements, author approval, acceptance or complete
artifact anonymity. Complete the explicit interest declaration before submission.

In Overleaf select `main.tex` or `main_author.tex` with pdfLaTeX. The paper-only
ZIP is convenient, but contains identities. Use the anonymous PDF for blind paper
review unless supplementary sources have separately been anonymized. The original
IEEE files are in `archive/ieee/`; `v0.1.0` restores the full older build. Any changed
source must be rebuilt and page-checked again.

## Troubleshooting

- **`Unreviewed CPN snapshot`:** restore the exact model bytes; do not bypass the
  pinned hash without rechecking the adapter and recording a new experiment version.
- **Port/service start failure:** allow local loopback connections and subprocesses.
  The legacy free-port selection has a possible port-reuse race; stop an incomplete
  run and use a fresh output label rather than overwriting its diagnostics.
- **Partial run:** a CSV with fewer rows is not the full study. Retain failure logs.
  Replay and analysis must complete before using its outputs.
- **Analysis comparison differs:** inspect package versions and input/source hashes.
  Do not replace retained results to make a check pass.
- **Different elapsed times:** this is expected across hosts, load, and schedulers.
  Seed matching fixes inputs, not service interleavings.
- **One repetition:** replay can still run; statistical analysis intentionally
  rejects a single repetition because sample standard deviation is undefined.
