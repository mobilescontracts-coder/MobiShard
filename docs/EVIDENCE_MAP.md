# Paper-to-evidence map

The current narrative is input by `paper/sections.tex` from `paper/sections/`. The manuscript's section, equation,
figure, and table labels are retained. All quantitative inputs come from the
original 880-trial dataset, not from the repository assembly smoke test.

| Paper item | Primary supporting material | How it is checked/generated |
|---|---|---|
| Architecture; Table 2 traceability | `prototype/runtime.py`, `prototype/artifact.py`, `model/msc.cpn` | Source inspection and model/source hash validation; not equivalence proof |
| Figure 1 | `figures/architecture_ngise.tikz` | Vector layout with corrected terminal paths; implementation unchanged |
| Equations (1)–(8), Algorithm 1 | `paper/objects/eq_*.tex`, gateway admission/spend/terminal operations | Guarded accounting argument plus local tests and trace replay |
| Table 3 resource profiles | `configs/experiment_design.json`, `prototype/run_experiments.py::profiles` | Source profiles and per-owner bound |
| Table 4 main outcomes | `results/deployment/results.csv`, suite `main` | `scripts/analyse_results.py` → `results/paper/outcome_rows.tex` |
| Figure 2 | `results/paper/cpu_outcomes.csv`, `figures/outcomes.tikz` | Main computation-limited means; bars include all 256 submissions |
| Figure 3 | `results/paper/concurrency_*.csv`, `figures/concurrency.tikz` | Four extra concurrency caps plus reused main cap-16 rows |
| Table 5 timings | Suites `main` (profile `cpu`) and `instrumentation` | `results/paper/timing_rows.tex` |
| Table 6 later disconnection | Suite `disconnect` | `results/paper/disconnect_rows.tex` |
| Paired intervals in Section 4 | `results/paper/paired_differences.csv` | Seed-paired trial differences with 19 degrees of freedom |
| 19 unit tests | `prototype/test_runtime.py`, `prototype/test_revision.py` | `python -m unittest discover -s prototype -v` |
| Recorded trace properties | `results/deployment/traces.jsonl.gz` | `scripts/verify_traces.py` |
| Historical runtime environment | `results/deployment/environment.json` | Original metadata, not the current machine's environment |
| Table 1 and references | `paper/sections.tex`, `references.bib` | Condensed supplied synthesis; same works, with limited metadata checks |

## Expected retained-data checks

The file has 880 unique trial keys and 44 configurations repeated over seeds
1–20. Each trial offers 256 requests. Totals are 225,280 submissions, 77,929
commitments, and 781,126 gateway events. At the end of every retained trial:
`submitted = committed + blocked + denied` and `admitted = committed + blocked`.

Successful-path resource bounds: deposit-limited 96, computation-limited 80,
battery-budget-limited 80, and mixed 96. Both Reservation and Serial attain them
with zero blocked admissions in the tested static profiles. Unreserved counts
are schedule-sensitive, including 72.40 mean commitments for Stagewise in the
main computation-limited burst configuration.

The later-disconnection bound field in the CSV is computed from **initial** online
accounts. It is not recomputed as connectivity changes, and must not be treated
as an attainable post-fault capacity. The reported Reservation outcomes are
224 admitted, 168 committed, 56 blocked, and 32 denied. Serial has 172 admitted,
168 committed, four blocked, and 84 denied.

## Interpretation

The difference `80 - 72.40 = 7.60` is a 10.5% relative increase in commitments,
not a blockchain throughput improvement. Reservation completes 31.25% of
submissions in this profile, even though it completes all 80 admitted requests.
The mixed-profile times 220.6 and 377.2 ms are mean trial elapsed times for
Reservation and Serial, respectively. They do not summarize universal per-request
latency improvements. A matched computation-limited comparison does not establish
a timing advantage or statistical equivalence.

The original checker uses Python assertions; passing it says that the implemented
checks passed for those recorded events. It does not prove cryptographic security,
full CPN reachability, or correctness under every possible failure.
