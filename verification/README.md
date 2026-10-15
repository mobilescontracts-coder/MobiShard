# Verification records

Current NGISE revision checks are in [`ngise2026/`](ngise2026/). Files at this
level and the `smoke/` folder record the earlier v0.1.0 repository assembly,
including its 12-page IEEE build. They are historical and not the current
CCIS paper build. The 88-trial smoke study is separate from the retained 880.

## Earlier assembly description

# Repository assembly validation

This folder records checks performed during repository assembly on 11 October
2026. It does not replace the original experiment environment or observations.

- `summary.json`: original source/integrity checks, 19 prototype tests, six new
  repository-utility tests, replay, and retained-analysis comparison.
- `prototype_unit_tests.txt` and `repository_unit_tests.txt`: actual test outputs.
- `retained_replay.json`: 880 trials, 225,280 submissions, 77,929 commitments,
  781,126 gateway events, and no violation of the checker’s scoped properties.
- `analysis_comparison.json`: 11 regenerated analysis/table/plot-input files agree
  byte-for-byte with the retained files under the pinned package versions.
- `paper_build.json`: successful 12-page IEEE manuscript build using pdfLaTeX and
  bibtex8 (the available BibTeX-compatible executable). No undefined citations or
  references and no overfull boxes were reported; rendered pages were inspected.
- `metadata_checks.json`: YAML syntax/selected fields and visual-build review.
  It is not a hosted GitHub Actions run or a full CFF-schema validation.
- `smoke/`: a separate completed two-repetition, 88-trial run with 22,528
  submissions. Its 78,186 gateway events and 7,759 commitments were replayed with
  no recorded violation. The input/source hashes and environment are retained.
  These measurements are integration-test evidence, not the paper dataset.
- `interrupted_smoke_attempt.json`: the first integration attempt was interrupted
  by an execution-tool time limit after 55 rows. It was not combined with the
  completed run or used for validation/analysis. Its metadata is retained for
  transparency; its partial traces are not distributed as a complete experiment.

The smoke analysis was tested through the safe wrapper. The retained numerical
inputs, CPN model, and original five prototype files were not changed. Passing
checks of recorded events does not establish full CPN reachability, cryptographic
security, model–implementation equivalence, or production performance.

To regenerate these checks, run `python scripts/run_checks.py`; fresh reports go
to `build/verification/`. To replay the distributed smoke data directly:

```bash
python scripts/verify_traces.py --input verification/smoke --report build/verification/smoke_replay.json
python scripts/rebuild_analysis.py --input verification/smoke/results.csv --out build/smoke_analysis
```

The assembly’s full `MANIFEST.sha256` covers this folder. Copy new reports here
only as an explicitly reviewed new repository version, updating its manifest.
