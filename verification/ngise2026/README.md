# NGISE revision verification

These checks were run locally for v0.2.0-ngise2026 on 11 October 2026. They
recheck the retained 880-trial experiment; no new performance experiment or
Turnitin assessment was run. The older smoke experiment is separate.

`summary.json` describes the check runner. Logs copied from build/verification
are retained here as `.txt` files; the report's original `build/` paths describe
where the checks ran. `integrity.json` was captured before the final assembly
manifest; `MANIFEST.sha256` is checked again after packaging. `paper_build.json`
records both complete 17-page builds and 30 bibliography entries. `pdf_preflight.json`
records page dimensions, fonts and absence of supplied author identifiers from
the anonymous PDF's extracted text and author metadata. Visual inspection is
recorded separately. These checks do not certify acceptance, all venue rules,
exhaustive CPN behavior, or anonymity of the source/repository.
