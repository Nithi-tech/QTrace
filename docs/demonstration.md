# Demonstration Plan (Draft)

> Status: to be completed in Phase 7 (see [project plan](../README.md#project-plan--roadmap)).

## Scenario

At least one of:

- A realistic urban network extracted from OpenStreetMap (e.g., a mid-size city district), or
- A synthetic large-scale instance (target: hundreds of nodes / thousands of edges) with generated congestion patterns.

## What Will Be Shown

1. Network loaded and rendered (`src/visualization`).
2. Simulated/live traffic condition change applied to edge weights.
3. QPSO computing near-optimal routes, with convergence curve.
4. Side-by-side comparison against baselines (GA, ACO, PSO, Dijkstra/exact) on the same instance.
5. Summary metrics table: solution quality gap vs. exact/best-known, convergence speed (iterations & wall-clock), scalability across instance sizes.

## Outputs to Capture

- Screenshots / recording of the dashboard.
- `benchmarks/results` tables and charts referenced directly in the final report.
