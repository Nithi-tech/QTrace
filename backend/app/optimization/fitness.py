"""Blended cost matrix for QPSO (CLAUDE.md #9, traffic master-prompt #27/#28).

QPSOSolver (app/optimization/qpso.py) takes a single generic cost_matrix and has no
knowledge of distance, time, or traffic - so traffic-awareness requires zero changes
to QPSO itself. This module builds that one matrix.

Distance and duration are on incomparable scales (meters vs seconds), so both are
min-max normalized to [0, 1] before combining; the traffic matrix from
app/traffic/matrix_service.py is already in [0, 1] (and already confidence-weighted -
see that module) and is used as-is - not double-counted with anything else.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FitnessWeights:
    """Configurable, documented weights (CLAUDE.md #9, #35 - never hard-coded, never
    silently changed). Not claimed to be a universally optimal combination - see
    DISTANCE_WEIGHT/TIME_WEIGHT/TRAFFIC_WEIGHT in .env.example."""

    distance_weight: float = 0.4
    time_weight: float = 0.4
    traffic_weight: float = 0.2


def _normalize(matrix: list[list[float]]) -> list[list[float]]:
    values = [v for row in matrix for v in row]
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [[0.0] * len(row) for row in matrix]
    return [[(v - lo) / (hi - lo) for v in row] for row in matrix]


def build_cost_matrix(
    distances_meters: list[list[float]],
    durations_seconds: list[list[float]],
    traffic_matrix: list[list[float]],
    weights: FitnessWeights,
) -> list[list[float]]:
    normalized_distance = _normalize(distances_meters)
    normalized_duration = _normalize(durations_seconds)
    size = len(distances_meters)

    return [
        [
            weights.distance_weight * normalized_distance[i][j]
            + weights.time_weight * normalized_duration[i][j]
            + weights.traffic_weight * traffic_matrix[i][j]
            for j in range(size)
        ]
        for i in range(size)
    ]
