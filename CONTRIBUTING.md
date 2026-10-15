# Contributing

Preserve the distinction between the recorded study and later modifications.
Do not edit `results/deployment/` or `results/excluded/` in place. Store new trials
under a new `runs/` label and record the environment and executed source hashes.

Changes to the model or `prototype/` break the preserved execution hashes. Treat
such changes as a new experimental version: recheck the adapter, update provenance
explicitly, rerun relevant tests, and retain fresh evidence before changing claims.
Do not just change a hash to make verification pass.

Use `python scripts/run_checks.py` before proposing a change. Report expected vs
observed behavior, Python/OS versions, the command used, and a minimal trace or
fixture. Do not include credentials or real wallet keys. Purely editorial changes
must not silently alter equations, cost assumptions, denominators, or result data.
All contributors must agree an appropriate license with the maintainers before
contributions are released publicly.
