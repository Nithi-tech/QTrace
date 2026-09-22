"""Fleet-aware stop clustering for multi-vehicle routing.

Scope: given a set of destination coordinates and a fleet of vehicle instances
(each with a capacity), partition destinations into feasible groups - one per
vehicle - so that no group's total demand exceeds its vehicle's capacity, and
so that the fleet the caller actually configured (how many vehicles, what
type/capacity each) is what determines the routes produced.

This is deliberately a classical, dependency-free approach (CLAUDE.md #32 - no
new heavy dependency such as scikit-learn for one algorithm), in two steps:

1. Cluster: sort destinations by compass bearing from the depot (the sweep
   algorithm, Gillett & Miller, 1974) and cut that angular order into exactly
   `k = min(number of vehicles, number of destinations)` contiguous,
   demand-balanced groups. Fixing k to the fleet size - rather than greedily
   packing everything into as few vehicles as fit - is what makes the fleet's
   configured vehicle count actually show up as that many routes. Sweeping by
   bearing (rather than plain spatial K-Means) also guarantees each group is
   one directional wedge around the depot, so two vehicles never criss-cross
   the same corridor.
2. Assign: match each group to whichever available vehicle serves it most
   cheaply (group's approximate route length x that vehicle's cost_per_km),
   preferring capacity-feasible matches, via a greedy cheapest-pair-first
   assignment - so a cheaper-per-km vehicle is actually preferred over a
   pricier one when both could serve a group, not just whichever has the
   biggest capacity. Any group whose demand still exceeds its matched
   vehicle's capacity is resolved by shedding stops from that group's angular
   boundary into an adjacent group's vehicle (falling back to any vehicle
   with room, then to unassigned) - preserving each group's directional
   coherence as much as possible while respecting capacity.

A future QISA-based per-vehicle optimizer (see docs/qisa-roadmap.md) does not
change this module - clustering decides *which* vehicle serves each stop;
route ordering *within* a vehicle's stops is a separate concern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from math import atan2, degrees, dist


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


def _split_into_k_groups_by_demand(order: list[int], demands: list[float], k: int) -> list[list[int]]:
    """Cut an angularly-sorted destination order into exactly `k` contiguous,
    demand-balanced groups (each destination's group is a slice of `order`,
    so group membership stays a directional wedge). Assumes len(order) >= k
    (the caller picks k = min(vehicles, destinations))."""
    if k <= 1:
        return [list(order)]

    target = sum(demands[i] for i in order) / k
    groups: list[list[int]] = []
    current: list[int] = []
    current_load = 0.0
    for idx in order:
        if current and current_load >= target and len(groups) < k - 1:
            groups.append(current)
            current = []
            current_load = 0.0
        current.append(idx)
        current_load += demands[idx]
    groups.append(current)

    # Demand can be skewed enough (e.g. one destination dominating the total)
    # that the running load never re-crosses `target` k-1 times, leaving
    # fewer than k groups - split the largest remaining group(s) in half
    # (still a contiguous slice, so still one angular wedge) until there are
    # exactly k, since k was chosen specifically so every vehicle gets one.
    while len(groups) < k:
        biggest = max(range(len(groups)), key=lambda g: len(groups[g]))
        if len(groups[biggest]) <= 1:
            break  # can't split single-stop groups further; k <= len(order) guarantees this isn't reached
        group = groups[biggest]
        split_at = len(group) // 2
        groups[biggest] = group[:split_at]
        groups.insert(biggest + 1, group[split_at:])

    return groups


def _group_route_length(
    depot: tuple[float, float], destination_points: list[tuple[float, float]], group: list[int]
) -> float:
    """Approximate round-trip route length for a group: depot -> its stops (in
    their existing, angularly-sorted order) -> back to depot. Straight-line on
    raw lat/lon, same approximation the rest of this module uses - just needs
    to rank groups by relative length for vehicle matching, not be exact (the
    real road distance is computed later, once vehicles are assigned, via
    RoutingProvider)."""
    if not group:
        return 0.0
    total = dist(depot, destination_points[group[0]])
    for a, b in zip(group, group[1:]):
        total += dist(destination_points[a], destination_points[b])
    total += dist(destination_points[group[-1]], depot)
    return total


def _match_vehicles_to_groups(
    group_demand: list[float], group_length: list[float], vehicles: list[VehicleInstance]
) -> dict[int, int]:
    """Match each group to a vehicle to minimize total estimated cost
    (group_length * vehicle.cost_per_km), preferring capacity-feasible
    matches.

    Estimated cost for a (group, vehicle) pair is a simple product of that
    group's route length and that vehicle's per-km rate, so - by the
    rearrangement inequality - the total-cost-minimizing pairing is: process
    groups longest-route-first (that's where the per-km rate matters most)
    and always give the current group the cheapest still-available vehicle
    that can carry its demand, falling back to the cheapest available vehicle
    at all if none can (overflow-shedding resolves any resulting capacity gap
    afterwards). Picking the single globally-cheapest (group, vehicle) pair
    first - the more obvious-looking greedy - is NOT optimal here: it can
    lock in a cheap vehicle for a short group and strand the expensive
    vehicle on the longest one, which is exactly the outcome this should
    avoid.
    """
    k = len(group_demand)
    group_order = sorted(range(k), key=lambda g: group_length[g], reverse=True)
    unmatched_vehicles = set(range(len(vehicles)))
    vehicle_for_group: dict[int, int] = {}

    for group in group_order:
        feasible = [v for v in unmatched_vehicles if vehicles[v].capacity >= group_demand[group]]
        candidates = feasible or list(unmatched_vehicles)
        if not candidates:
            break
        best = min(candidates, key=lambda v: (vehicles[v].cost_per_km, v))
        vehicle_for_group[group] = best
        unmatched_vehicles.discard(best)

    return vehicle_for_group


def _shed_overflow(
    group_index: int,
    groups: list[list[int]],
    vehicle_for_group: dict[int, int],
    vehicle_assignments: list[list[int]],
    remaining_capacity: list[float],
    destination_points: list[tuple[float, float]],
    demands: list[float],
) -> list[int]:
    """Resolve `group_index`'s vehicle being over capacity by moving stops out
    of it, one at a time, preferring the group's own angular boundary (its
    first or last stop, in sweep order) into an angularly-adjacent group's
    vehicle so directional coherence is disturbed as little as possible.
    Falls back to any vehicle with room, then to unassigned."""
    k = len(groups)
    vehicle = vehicle_for_group[group_index]
    unassigned: list[int] = []

    while remaining_capacity[vehicle] < 0 and vehicle_assignments[vehicle]:
        moved = False
        for neighbor in (group_index + 1, group_index - 1):
            if not (0 <= neighbor < k) or neighbor not in vehicle_for_group:
                continue
            neighbor_vehicle = vehicle_for_group[neighbor]
            candidate = (
                vehicle_assignments[vehicle][-1]
                if neighbor > group_index
                else vehicle_assignments[vehicle][0]
            )
            if remaining_capacity[neighbor_vehicle] >= demands[candidate]:
                vehicle_assignments[vehicle].remove(candidate)
                vehicle_assignments[neighbor_vehicle].append(candidate)
                remaining_capacity[vehicle] += demands[candidate]
                remaining_capacity[neighbor_vehicle] -= demands[candidate]
                moved = True
                break
        if moved:
            continue

        # Neither angular neighbor has room - fall back to whichever other
        # vehicle (with spare capacity) is geographically closest, else the
        # boundary stop is unassigned.
        boundary = vehicle_assignments[vehicle][-1]
        other_candidates = [
            v
            for v in range(len(remaining_capacity))
            if v != vehicle and remaining_capacity[v] >= demands[boundary]
        ]
        if other_candidates:
            best = min(
                other_candidates,
                key=lambda v: (
                    dist(destination_points[boundary], destination_points[vehicle_assignments[v][0]])
                    if vehicle_assignments[v]
                    else 0.0
                ),
            )
            vehicle_assignments[vehicle].remove(boundary)
            vehicle_assignments[best].append(boundary)
            remaining_capacity[vehicle] += demands[boundary]
            remaining_capacity[best] -= demands[boundary]
        else:
            vehicle_assignments[vehicle].remove(boundary)
            remaining_capacity[vehicle] += demands[boundary]
            unassigned.append(boundary)

    return unassigned


def fleet_aware_clusters(
    destination_points: list[tuple[float, float]],
    demands: list[float],
    vehicles: list[VehicleInstance],
    depot: tuple[float, float],
) -> ClusterAssignment:
    """Assign destinations to vehicle instances: cluster into as many
    directional groups as vehicles are available, then match the best-fit
    vehicle to each group (see module docstring for the two-step algorithm).
    """
    n = len(destination_points)
    if n == 0:
        return ClusterAssignment(vehicle_assignments=[[] for _ in vehicles])
    if not vehicles:
        return ClusterAssignment(vehicle_assignments=[], unassigned=list(range(n)))

    k = min(len(vehicles), n)
    order = sorted(range(n), key=lambda i: _bearing_from_depot(depot, destination_points[i]))
    groups = _split_into_k_groups_by_demand(order, demands, k)
    group_demand = [sum(demands[i] for i in group) for group in groups]
    group_length = [_group_route_length(depot, destination_points, group) for group in groups]

    vehicle_for_group = _match_vehicles_to_groups(group_demand, group_length, vehicles)
    group_order = sorted(range(k), key=lambda g: group_demand[g], reverse=True)

    vehicle_assignments: list[list[int]] = [[] for _ in vehicles]
    remaining_capacity = [v.capacity for v in vehicles]
    for group, vehicle in vehicle_for_group.items():
        vehicle_assignments[vehicle] = list(groups[group])
        remaining_capacity[vehicle] -= group_demand[group]

    unassigned: list[int] = []
    for group in group_order:
        unassigned.extend(
            _shed_overflow(
                group,
                groups,
                vehicle_for_group,
                vehicle_assignments,
                remaining_capacity,
                destination_points,
                demands,
            )
        )

    return ClusterAssignment(vehicle_assignments=vehicle_assignments, unassigned=sorted(unassigned))
