"""Classical nearest-neighbor route construction for a single vehicle's stops.

Scope: given a precomputed cost matrix (distance or duration) over a fixed
start (the depot, index 0) and a set of intermediate stop indices, produce an
initial visit order by always moving to the nearest unvisited stop. This is a
plain, deterministic construction heuristic - no randomness, no QPSO/QISA -
per the current implementation direction (see docs/qisa-roadmap.md for the
planned future quantum-inspired refinement).

The result is a starting point for app.optimization.two_opt.two_opt_refine,
not a final route.
"""

from __future__ import annotations


def nearest_neighbor_order(
    cost_matrix: list[list[float]], start_index: int, stop_indices: list[int], end_index: int | None = None
) -> list[int]:
    """Greedily order `stop_indices` starting from `start_index`.

    Returns the full visit order including `start_index` first and, if
    `end_index` is given, that index last (e.g. returning to the depot).
    `end_index` is excluded from the nearest-neighbor search itself so it is
    never picked early.
    """
    remaining = set(stop_indices)
    order = [start_index]
    current = start_index

    while remaining:
        nearest = min(remaining, key=lambda i: cost_matrix[current][i])
        order.append(nearest)
        remaining.remove(nearest)
        current = nearest

    if end_index is not None:
        order.append(end_index)

    return order
