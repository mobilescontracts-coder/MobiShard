# Known limitations and author checks

## Scientific scope

The service prototype is separate from the CPN simulator. Only selected guard,
cost, routing, and evidence rules are retained. Budgets are fixed logical charges
against one owner, without replenishment or external drain. No virtual machine,
real mobile energy measurement, receipt-based cross-shard atomic commit, adversarial
committee consensus, or replicated account authority is evaluated. Trace replay
is not a full model–implementation equivalence proof.

The single-host experiment uses instrumented services and configured delays.
Seeds fix workload inputs, not the execution schedule. A modeled offline flag is
not a broken network connection. Leases, lost-call recovery, and service-crash
settlement have not been implemented. Released allowance would need protection
against spending by delayed requests in a future recovery protocol.

## Figure and code caveats

The active vector architecture corrects the prior image's hold label and combined
outcome arrow. The original PNG is preserved but not used in the current paper.
No extra root process, replicated accounting, recovery or consensus is introduced.

The scientific runner defaults to `results/deployment`, which can overwrite
observations. Use `scripts/run_new_experiments.py` instead. Its old docstring calls
every workload a burst, although the `arrival` suite uses staggered arrivals.
The legacy analysis metadata date is fixed; the safe analysis wrapper corrects
that metadata for new datasets while preserving retained-data regeneration.

Services select free ports before starting child processes; this is not an atomic
port reservation and can race with other processes. Assertions are part of the
research checks, so optimized Python execution must not be used. No security
hardening or production reliability is implied by a passing test suite.

## Manuscript and bibliography

The NGISE prose is edited and condensed, not byte-identical to the prior IEEE
body. It preserves eight equation payloads, Algorithm 1, all retained numerical
evidence and 30 citation identities. Six tables remain with two descriptive tables
shortened. The two 17-page CCIS PDFs pass length/build checks, but this does not
certify acceptance or full submission readiness. Interests, affiliations, hosting,
reuse rights and AI-use disclosure require author review.

Only selected bibliography metadata were newly checked; see BIBLIOGRAPHY_REVIEW.md.
The older reference audit is historical, not fresh certification of every entry.
NGISE is a preparation target, not a claimed accepted venue. Public dates conflict
and no current new-submission opening is assumed. No remote repository, DOI,
blanket license or detector score has been created. The anonymous PDF omits front-
matter identities; the repository and source ZIP remain identifiable.
