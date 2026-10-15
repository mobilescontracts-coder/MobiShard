# Measurement directories

`deployment/` contains the paper's retained records: 880 measured trials and
four excluded warm-up observations in `warmup.json`. `paper/` contains analysis
outputs derived only from `deployment/results.csv`. Do not overwrite either.

`excluded/pilot/` contains a separate 44-trial pilot and its warm-ups.
`excluded/ccis/` contains older results and the earlier runtime retained for lineage.
Neither directory contributes rows to the 880-trial experiment or manuscript.

New experiments belong in the ignored top-level `runs/` directory. Repository
assembly verification lives under `verification/`, not in this results directory.
