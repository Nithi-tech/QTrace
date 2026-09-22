"""Deterministic 2-Opt local search refinement for a single vehicle's route.

Scope: given a visit order (typically from greedy_route.nearest_neighbor_order)
and the cost matrix it was built from, repeatedly reverse segments of the
route whenever doing so reduces total cost, until no such improving reversal
exists (a local optimum) or `max_passes` is reached. This removes the
"crossed path" detours nearest-neighbor construction is prone to.

The first and last positions in `order` are treated as fixed (the depot start,
and - if the vehicle returns to base - the depot end) and are never moved,
since they are not stops to reorder.
"""

from __future__ import annotations


def _order_cost(cost_matrix: list[list[float]], order: list[int]) -> float:
    return sum(cost_matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def two_opt_refine(
    cost_matrix: list[list[float]], order: list[int], fixed_end: bool = True, max_passes: int = 200
) -> list[int]:
    """Return an improved copy of `order`; never returns a worse route.

    `fixed_end` should be True when `order[-1]` is a real fixed endpoint (e.g.
    the depot on a return trip) and False when the last element is actually a
    stop that is free to be reordered.
    """
    n = len(order)
    # With <=3 positions (e.g. depot, one stop, depot) no reversal can change anything.
    if n <= 3:
        return list(order)

    best = list(order)
    last_reorderable = n - 1 if not fixed_end else n - 2

    for _ in range(max_passes):
        improved = False
        for i in range(1, last_reorderable):
            for j in range(i + 1, last_reorderable + 1):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                if _order_cost(cost_matrix, candidate) < _order_cost(cost_matrix, best):
                    best = candidate
                    improved = True
        if not improved:
            break

    return best
