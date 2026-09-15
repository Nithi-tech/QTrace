# Mathematical Formulation (Draft)

> Status: draft skeleton to be refined during Phase 2 (see [project plan](../README.md#project-plan--roadmap)).

## Network

- Graph `G = (V, E)`, `V` = intersections/depots, `E` = road segments.
- Edge weight `w_ij(t) = f(distance_ij, travel_time_ij(t), congestion_ij(t))`, time-dependent to support dynamic conditions.

## Decision Variables

- `x_ijk ∈ {0,1}` — 1 if vehicle `k` traverses edge `(i,j)`.
- `u_ik` — auxiliary load/time variable at node `i` for vehicle `k` (subtour elimination / time tracking).

## Objective Function

Minimize total weighted travel cost across all vehicles:

```
minimize  Σ_k Σ_(i,j)∈E  w_ij(t) * x_ijk
```

Optionally a multi-objective weighted sum of `(travel time, distance, congestion exposure)`.

## Constraints

- **Flow conservation:** each customer/node visited exactly once; vehicle flow in = flow out.
- **Capacity:** total demand on a route ≤ vehicle capacity `Q`.
- **Time windows:** arrival time at node `i` within `[e_i, l_i]`.
- **Subtour elimination:** MTZ-style or flow-based constraints.
- **Depot constraints:** every route starts/ends at a depot.

## QPSO Encoding

- Each particle encodes a candidate route/route-set (permutation or priority-vector encoding, decoded via a route-construction heuristic).
- Position update replaced by quantum-behaved update using a mean-best (attractor) position and a contraction-expansion coefficient, instead of classical velocity terms.
- Fitness = objective function value (with penalty terms for constraint violations).

## Benchmarks to Compare Against

- Exact: Dijkstra / A* (shortest path), small-instance exact VRP (branch-and-bound) for a lower-bound reference.
- Metaheuristic: Genetic Algorithm (GA), Ant Colony Optimization (ACO), classical PSO.
