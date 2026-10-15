# Provenance

`source_manifest.json` identifies supplied source archives and hashes each preserved
scientific/source asset. `source_manifest.sha256` is included in the complete
repository integrity manifest, not a signature of scientific correctness.
`UPSTREAM_LINEAGE.md` is a verbatim upstream record. Its historical names map here
as follows: `runtime_ccis.py` → `results/excluded/ccis/runtime.py`;
`ccis_results_not_used.csv` → `results/excluded/ccis/results.csv`.

`bibliography_source_notes.md` is also a retained source note. The earlier
bibliography files mentioned there are now `research/earlier_references.bib` and
`research/earlier_references.bbl`. The report itself and detector-change logs are
not part of this repository.

The original scientific files in `prototype/`, the model, retained measurements,
analysis/replay engines, and manuscript graphics are unchanged. New repository
wrappers, guides, citation files, and CI configuration were generated during this
assembly. Their validation is distinct from the retained 2026-09-08 experiment.
The neutral initial Git commit identifies repository assembly, not experimental
authorship or a signed release. Model names and attribution are retained.
