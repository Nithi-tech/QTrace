"""Fleet-aware stop clustering for multi-vehicle routing.

Scope: given a set of destination coordinates and a fleet of vehicle instances
(each with a capacity), partition destinations into feasible groups - one per
vehicle - so that no group's total demand exceeds its vehicle's capacity.

This is deliberately a classical, dependency-free approach (CLAUDE.md #32 - no
new heavy dependency such as scikit-learn for one algorithm): the sweep
algorithm (Gillett & Miller, 1974). Destinations are sorted by compass bearing
from the depot, then walked in that angular order, filling one vehicle at a
time until its capacity would be overflowed, then moving on to the next.
Unlike plain spatial K-Means (the previous approach here), sweep guarantees
each vehicle's stops form one contiguous directional wedge around the depot -
two vehicles never double back through the same corridor - which is what
keeps "which direction does this vehicle actually go" well-defined on the
map. Any destination that cannot fit anywhere (total fleet capacity
exhausted, or its own demand exceeds every vehicle's capacity) is reported as
unassigned rather than forced into an infeasible route (CLAUDE.md #10).

A future QISA-based per-vehicle optimizer (see docs/qisa-roadmap.md) does not
change this module - clustering decides *which* vehicle serves each stop;
route ordering *within* a vehicle's stops is a separate concern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from math import atan2, degrees


@dataclass(frozen=True)
class VehicleInstance:
    """One physical vehicle expanded out of a fleet spec's (type, count) pair."""

    vehicle_type: str
    capacity: float
    cost_per_km: float
    availability_start: time | None = None
    availability_end: time | None = None


@dataclass
class ClusterAssignment:
    vehicle_assignments: list[list[int]]
    """vehicle_assignments[v] = list of destination indices assigned to vehicle v."""
    unassigned: list[int] = field(default_factory=list)
    """Destination indices that did not fit in any vehicle's remaining capacity."""


def _bearing_from_depot(depot: tuple[float, float], point: tuple[float, float]) -> float:
    """Compass bearing in degrees [0, 360) from the depot to a point.

    Plain lat/lon deltas (not a full great-circle bearing) only need to
    preserve angular ORDER around the depot at city/regional scale, which
    they do - exact geodesic precision isn't needed just to sweep by
    direction.
    """
    d_lat = point[0] - depot[0]
    d_lon = point[1] - depot[1]
    return degrees(atan2(d_lon, d_lat)) % 360.0


def fleet_aware_clusters(
    destination_points: list[tuple[float, float]],
    demands: list[float],
    vehicles: list[VehicleInstance],
    depot: tuple[float, float],
) -> ClusterAssignment:
    """Assign destinations to vehicle instances via the sweep algorithm.

    Step 1: sort destinations by compass bearing from the depot.
    Step 2: sort vehicles largest-capacity-first, then walk the sorted
    destinations in angular order, adding each to the current vehicle unless
    doing so would exceed its capacity - in which case that vehicle's wedge
    is closed and the next vehicle starts from there.
    A destination whose own demand exceeds every remaining vehicle's
    capacity (or that runs out of vehicles to sweep into) is reported as
    unassigned rather than forced into an infeasible route (CLAUDE.md #10).
    """
    n = len(destination_points)
    if n == 0:
        return ClusterAssignment(vehicle_assignments=[[] for _ in vehicles])
    if not vehicles:
        return ClusterAssignment(vehicle_assignments=[], unassigned=list(range(n)))

    order = sorted(range(n), key=lambda i: _bearing_from_depot(depot, destination_points[i]))
    vehicle_order = sorted(range(len(vehicles)), key=lambda v: vehicles[v].capacity, reverse=True)

    vehicle_assignments: list[list[int]] = [[] for _ in vehicles]
    unassigned: list[int] = []

    vi = 0
    load = 0.0
    for idx in order:
        demand = demands[idx]
        # Close out the current vehicle's wedge (move to the next one) whenever
        # it already has stops and this one would overflow it.
        while (
            vi < len(vehicle_order)
            and vehicle_assignments[vehicle_order[vi]]
            and load + demand > vehicles[vehicle_order[vi]].capacity
        ):
            vi += 1
            load = 0.0

        if vi >= len(vehicle_order) or demand > vehicles[vehicle_order[vi]].capacity:
            unassigned.append(idx)
            continue

        vehicle_assignments[vehicle_order[vi]].append(idx)
        load += demand

    return ClusterAssignment(vehicle_assignments=vehicle_assignments, unassigned=sorted(unassigned))
