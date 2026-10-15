# Implementation architecture

The active diagram is `figures/architecture_ngise.tikz`, an editable CCIS layout
of the same services. It corrects per-request `h_x` notation and separates terminal
status paths. Root checking and local commitment share one process. The old PNG
remains at `figures/MobiShard_Architecture.png` for provenance, not as the active
paper figure. No new runtime functionality is implied by the drawing.

## Service responsibilities

| Element | Executable location | Responsibility |
|---|---|---|
| Request driver | `prototype/run_experiments.py` | Creates 16 owners × 16 uniquely identified requests, sets arrival/concurrency conditions, records responses |
| Gateway | `prototype/runtime.py::Gateway` | Admission, wallet debits, logical budgets, per-request/aggregate holds, routing, candidate construction, terminal settlement |
| Four workers | `prototype/runtime.py::Shard` | Serialized block-stage scheduling per worker, proof-input check, symbolic proof generation, root call |
| Root-policy service | `prototype/runtime.py::Root` | Scoped root predicates, root-stage charge, positive decision, configured local commitment delay |
| Design-time CPN | `model/msc.cpn` | Source of selected types, constants, guard/evidence relationships, and routing map |
| Adapter | `prototype/artifact.py` | Hash-pins the model, extracts constants/map, transcribes selected symbolic predicates |

`Deployment` starts six processes using multiprocessing `spawn`. Services listen
only on `127.0.0.1` using dynamically selected ports and line-delimited JSON.
There is no authentication, replicated gateway, leader election, validator
committee, or peer-to-peer consensus subsystem. Do not expose the service ports.

## Account updates

Write `a_u` for the remaining two-component account budget, `H_u` for its aggregate
outstanding reservations, and `h_x` for one request's remaining reservation.
Admission under Reservation requires `a_u - H_u >= (4, 7)` componentwise, a mapped
routing key, online eligibility, and wallet balance at least 15. An atomic gateway
operation debits the deposit and records the hold. Admission does not consume the
battery or computation balance.

Charging stage `j` subtracts the same vector from `a_u`, `H_u`, and `h_x`, preserving
`a_u >= H_u >= 0`. Active-state and expected-stage assertions prevent duplicate
or out-of-order charging. Unused reservation is released on handled termination,
not refunded as spent resources or deposits. The stage marker records the last
charge, not completion of the associated delay.

## Evidence and failures

The worker calls the gateway for block construction. The root accepts scoped
predicates over the auxiliary deposit record at the head of a candidate's list.
These are symbolic relationships, not payload-wide public-key verification.
A commitment requires a matching positive decision and the local timer.

The fault experiment sets a modeled eligibility flag to offline after an owner's
first successful block-stage delay. TCP connectivity stays available. Requests
may be blocked at later guarded stages, but the commitment timer does not recheck
the flag after root acceptance. A runtime failed check is handled as terminal
`blocked`; a failed CPN guard merely disables a binding. These are intentionally
different execution semantics.

## Policies

- `stagewise`: mapping/wallet admission, resource checks at the charged stages.
- `precheck`: full-path current-balance check and connectivity check; no hold.
- `reserve`: full-path unreserved-balance check and hold/consume/release accounting.
- `serial`: queue per owner, then full-path precheck; retain the owner lock through
  terminal response. This restricts request overlap, not database isolation.
