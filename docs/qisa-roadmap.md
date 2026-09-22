# Future Work: Quantum-Inspired Simulated Annealing (QISA) for Per-Vehicle Routing

## Status today

The multi-vehicle fleet routing pipeline (`POST /api/v1/fleet/routes`,
`app/services/fleet_optimization_service.py`) currently orders each vehicle's
assigned stops with two **classical** algorithms, chosen deliberately for this
first pass instead of building a new metaheuristic from scratch:

1. **Nearest-neighbor construction** (`app/optimization/greedy_route.py`) - a
   deterministic greedy heuristic that always moves to the closest unvisited
   stop.
2. **2-Opt local search** (`app/optimization/two_opt.py`) - repeatedly
   reverses route segments whenever doing so shortens the total route, until
   no improving reversal remains.

This is *not* the existing `QPSOSolver` (`app/optimization/qpso.py`), and it
is *not* Simulated Annealing either - it's plain construction + local search,
reused unchanged per vehicle. `QPSOSolver` remains exactly as-is and continues
to serve only the original single-vehicle `/api/v1/optimization/jobs`
endpoint; this document does not propose changing it.

## Why not QPSO or a new SA implementation right now

An earlier version of the multi-vehicle feature request assumed an "existing
QISA (Quantum-Inspired Simulated Annealing)" implementation already existed in
this codebase, reusable per vehicle. A codebase audit (see PR/commit history
around this document) found that neither QISA nor K-Means nor 2-Opt existed
anywhere before this feature - `QPSOSolver` (Quantum-inspired *Particle
Swarm* Optimization) was the only optimizer present, and it is architecturally
different from Simulated Annealing (no temperature, no cooling schedule, no
Metropolis acceptance criterion).

Rather than either (a) misusing QPSO as if it were QISA, or (b) building a
brand new metaheuristic before the surrounding multi-vehicle plumbing
(clustering, capacity/time-window checks, multi-route API contract) was even
in place, this phase intentionally used classical, easy-to-verify algorithms
so the pipeline itself could be built and tested end-to-end first. This
matches CLAUDE.md's incremental-implementation and no-invented-benchmarks
principles (§28, §41, §42) - it is easier to trust a multi-vehicle result
built on 2-Opt than to debug clustering and metaheuristic tuning at the same
time.

## Planned QISA design (future phase)

When a genuine per-vehicle Simulated-Annealing-style optimizer is built, it
should slot in as a drop-in replacement for the
`nearest_neighbor_order` + `two_opt_refine` pair inside
`FleetOptimizationService.plan_fleet_routes`, without changing the
`FleetRouteRequest` / `FleetRouteResponse` API contract. Planned shape,
matching the original spec's pseudocode:

```
Assigned Stops (per vehicle, from fleet-aware clustering - unchanged)
    -> Greedy Initial Route            (reuse nearest_neighbor_order as the seed)
    -> Hybrid Mutation (Swap + 2-Opt reversal)
    -> Energy Evaluation (distance/time + time-window penalty terms)
    -> Metropolis Tunneling (accept worse moves with probability exp(-delta_E / T))
    -> Cooling (T *= cooling_rate each iteration)
    -> Repeat until termination (max iterations or min temperature)
    -> Best Route found
    -> two_opt_refine() as a final deterministic polish pass (kept as-is - CLAUDE.md #9)
```

Concretely, a new `app/optimization/qisa.py` module would define:

- `QISAConfig` (dataclass): `initial_temperature`, `cooling_rate`,
  `max_iterations`, `min_temperature`, `seed` - all explicit, no magic
  numbers (CLAUDE.md §35), mirroring `QPSOConfig`'s style.
- `QISAResult` (dataclass): `order`, `total_cost`, `iterations_run`,
  `converged`, `cost_history` - same shape as `QPSOResult` so the service
  layer's integration barely changes.
- `QISASolver.optimize(cost_matrix, stop_indices, fixed_start, fixed_end)` -
  same call shape as today's `nearest_neighbor_order`/`two_opt_refine`
  pairing, so `FleetOptimizationService` swaps one call site.

**Energy function**: `E = distance_or_duration_cost + penalty_weight *
time_window_violation_minutes`, with `penalty_weight` configurable
(CLAUDE.md §9's `J = w_distance*... + w_penalty*...` objective, applied per
vehicle instead of globally).

**Mutation operators**: swap two stops, or reverse a sub-segment (2-Opt-style
move) - picked at random each iteration, consistent with "Hybrid Mutation" in
the spec.

**Acceptance rule**: always accept an improving move; accept a worsening move
with probability `exp(-delta_E / T)` (classic Metropolis criterion) - this is
the piece that is genuinely new versus what exists today, since neither QPSO
nor the current greedy+2-Opt pipeline has any concept of temperature or a
probabilistic accept-worse step.

**Testing approach**: mirror `tests/optimization/test_qpso.py` - hand-checkable
small matrices with a known optimum, a fixed-seed reproducibility test, and a
test confirming energy never increases after the final `two_opt_refine`
polish pass.

## Non-goals for this phase

- Replacing `QPSOSolver` or the single-vehicle `/api/v1/optimization/jobs`
  endpoint - out of scope, no plan to change it.
- A full CVRPTW constraint solver - the current time-window check in
  `FleetOptimizationService._check_time_windows` is a heuristic sequential
  walk (no wraparound handling, no explicit slack/wait optimization); QISA's
  energy-penalty approach improves on this but a complete constraint-solving
  guarantee is further out.
- Adding scikit-learn or any new heavy dependency - `app/optimization/clustering.py`
  stays a dependency-free sweep algorithm (bearing-from-depot, capacity-bounded),
  consistent with CLAUDE.md §32.
