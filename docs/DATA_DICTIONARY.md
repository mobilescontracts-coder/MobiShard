# Data dictionary

## Trial table: `results/deployment/results.csv`

UTF-8 CSV with one row per measured trial. The key is
`(suite, profile, concurrency, arrival, validation_mode, policy, seed)`.
There are 880 distinct rows; each configuration has seeds 1–20. Labels are kept
as stored in the original code (`cpu`, `reserve`, `wasted_cpu`) rather than renamed.

| Field | Type / unit | Meaning |
|---|---|---|
| `suite` | string | `main`, `concurrency`, `arrival`, `instrumentation`, or `disconnect` |
| `profile` | string | `default`, `cpu`, `battery`, `mixed`, or `disconnect` |
| `concurrency` | integer | Maximum outstanding driver calls per owner, including calls queued for serialization |
| `arrival` | string | `burst` or globally `staggered` releases |
| `validation_mode` | string | `operational` local checks or `full` in-path ledger reconstruction |
| `policy` | string | `stagewise`, `precheck`, `reserve`, or `serial` |
| `seed` | integer | Workload seed, not a deterministic scheduler seed |
| `tau_ms` | ms per model unit | Timing scale; 1.0 in retained data |
| `input_sha256` | hex string | Digest of devices, ordered workload, fault-target list, concurrency, and arrival mode |
| `submitted` | requests | 256 per trial |
| `admitted` | requests | Requests passing gateway admission |
| `committed` | requests | Requests reaching the local commitment record |
| `blocked` | requests | Admitted requests stopped at handled checks |
| `denied` | requests | Requests rejected before processing |
| `completion_pct` | percent | `100 * committed / submitted` |
| `admitted_completion_pct` | percent | `100 * committed / admitted`; NaN if no admissions |
| `elapsed_s` | seconds | Workload start to all terminal responses at the driver |
| `throughput_rps` | local completions/second | `committed / elapsed_s`; legacy diagnostic field, not production blockchain TPS |
| `mean_latency_ms` | milliseconds | Mean driver latency among successful requests in that trial |
| `p95_latency_ms` | milliseconds | Linearly interpolated 95th percentile of successful-request latency in that trial |
| `wasted_cpu` | logical computation units | Stage charges to requests whose terminal outcome is blocked; paper notation `U_C` |
| `wasted_battery` | logical battery units | Battery-budget charges to blocked requests, not measured energy |
| `blocked_deposit_units` | deposit-accounting units | `blocked * 15`, not a refund or consensus stake |
| `budget_bound` | requests | Sum of initial per-owner bounds for the offered 16 requests per owner; not a post-fault recalculation |
| `invariant_violations` | integer | Legacy runner success marker, set to zero on a completed run; not an exhaustive defect count |
| `trace_events` | events | Number of gateway events in the trial's retained trace |

`submitted = committed + blocked + denied`; `admitted = committed + blocked`.
Mean and P95 timing columns in the paper average trial summaries. They are not
percentiles over pooled requests, and successful subsets can differ by policy.
Input hashes pair workloads but do not authenticate hostile participants.

## Per-trial records: `traces.jsonl.gz`

The compressed file contains 880 JSON lines, one trial per line. It decompresses
to more than its archive size; stream it line by line rather than loading the
whole file into memory. Each line contains these objects:

| Object | Content |
|---|---|
| `summary` | The trial's CSV-equivalent fields |
| `config.devices` | Initial owner balances `w`, `b`, `c`, and `net` |
| `config.workload` | Ordered submission dictionaries with `rid`, `uid`, and `cid` |
| `config.disconnect` | Owner identifiers whose eligibility flags will change |
| `config.concurrency`, `arrival`, `validation_mode` | Control settings |
| `responses` | Actual request-level timing and returned terminal outcomes |
| `gateway.initial` | Initial account state retained by the gateway |
| `gateway.devices` | Final wallet/resource/connectivity balances and aggregate holds |
| `gateway.requests` | Request ledger: owner/routing, admission, remaining holds, spent amounts, last charged stage, outcome/reason, candidate ID |
| `gateway.events` | Ordered account and control events with monotonic timestamps |
| `gateway.deposit_balance` | Deposit accumulation performed by candidate construction |
| `root.commits` | Local commit records with candidate ID, owner, decision and commitment times |
| `root.decisions` | Candidate-ID-to-positive-decision mapping |

Request response times (`scheduled_ns`, `start_ns`, `rpc_ns`, `stop_ns`) are
monotonic nanoseconds, not calendar timestamps. `start_ns` is the actual driver
release before waiting on its concurrency limiter. `rpc_ns` follows that limiter;
`stop_ns` follows the terminal response. The paper's request latency is
`(stop_ns - start_ns) / 1e6`. Do not subtract `scheduled_ns` to recreate that metric.
Do not compare absolute monotonic timestamps between trials on different hosts.

The request ledger fields `hold_b` and `hold_c` hold unused reservations;
`spent_b` and `spent_c` count charged units. `phase` is the last **charged** stage,
not necessarily completed processing. JSON turns some integer dictionary keys
into strings. Synthetic wallet/key strings and numeric owner identifiers are
model/test data, not participant identities or real cryptographic secrets.

## Other records

`environment.json` retains measurement start/end UTC timestamps, Python/platform
versions, cgroup limits, configured model constants, model digest, hashes of the
executed five prototype files, command arguments, and service process IDs/ports.
Those process IDs and ports describe the historical run and must not be reused
as deployment settings. Four warm-ups are in `warmup.json`, outside the trial CSV.

`results/paper/summary.csv` contains configuration-level means, sample standard
deviations, and trial-mean 95% intervals for 44 groups. `paired_differences.csv`
contains signed, seed-paired comparisons; the comparison label states the order
(e.g. `mixed: reserve - serial`). Figure inputs and LaTeX rows are generated from
these records. `analysis_manifest.json` pins the source CSV digest.
