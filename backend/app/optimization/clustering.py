"""Fleet-aware stop clustering for multi-vehicle routing.

Scope: given a set of destination coordinates and a fleet of vehicle instances
(each with a capacity), partition destinations into feasible groups - one per
vehicle - so that no group's total demand exceeds its vehicle's capacity.

This is deliberately a classical, dependency-free approach (CLAUDE.md #32 - no
new heavy dependency such as scikit-learn for one algorithm): plain K-Means on
(latitude, longitude) for geographic proximity, followed by a greedy capacity
rebalancing pass that moves stops out of over-capacity clusters into the
nearest cluster with spare room. Any destination that cannot fit anywhere
(total fleet capacity exhausted) is reported as unassigned rather than forced
into an infeasible route (CLAUDE.md #10).

A future QISA-based per-vehicle optimizer (see docs/qisa-roadmap.md) does not
change this module - clustering decides *which* vehicle serves each stop;
route ordering *within* a vehicle's stops is a separate concern.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import time
from math import dist


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


def _kmeans(
    points: list[tuple[float, float]], k: int, max_iterations: int = 50, seed: int | None = None
) -> list[int]:
    """Plain K-Means over (lat, lon) points. Returns a cluster index per point.

    Euclidean distance on raw lat/lon degrees is an approximation (not
    haversine-accurate), but is sufficient for grouping nearby stops - the
    real road distance/duration is computed later via RoutingProvider for the
    actual route metrics.
    """
    n = len(points)
    if k <= 0:
        raise ValueError("k must be >= 1")
    k = min(k, n)

    rng = random.Random(seed)
    centroids = [points[i] for i in rng.sample(range(n), k)]
    assignments = [0] * n

    for _ in range(max_iterations):
        changed = False
        for i, point in enumerate(points):
            nearest = min(range(k), key=lambda c: dist(point, centroids[c]))
            if assignments[i] != nearest:
                assignments[i] = nearest
                changed = True

        new_centroids = []
        for c in range(k):
            members = [points[i] for i in range(n) if assignments[i] == c]
            if members:
                new_centroids.append(
                    (sum(p[0] for p in members) / len(members), sum(p[1] for p in members) / len(members))
                )
            else:
                new_centroids.append(centroids[c])  # empty cluster keeps its centroid
        centroids = new_centroids

        if not changed:
            break

    return assignments


def fleet_aware_clusters(
    destination_points: list[tuple[float, float]],
    demands: list[float],
    vehicles: list[VehicleInstance],
    seed: int | None = None,
) -> ClusterAssignment:
    """Assign destinations to vehicle instances, respecting each vehicle's capacity.

    Step 1: geographic K-Means with k = number of vehicles.
    Step 2: sort vehicles largest-capacity-first and greedily match them to the
    highest-demand clusters, so big loads go to big vehicles where possible.
    Step 3: for any cluster whose demand exceeds its matched vehicle's
    capacity, move its farthest-from-centroid, still-unassigned-elsewhere
    destinations out one at a time (largest demand first) into whichever
    other vehicle has enough spare capacity and is geographically closest;
    if none has room, the destination is reported unassigned.
    """
    n = len(destination_points)
    if n == 0:
        return ClusterAssignment(vehicle_assignments=[[] for _ in vehicles])
    if not vehicles:
        return ClusterAssignment(vehicle_assignments=[], unassigned=list(range(n)))

    raw_clusters = _kmeans(destination_points, k=len(vehicles), seed=seed)
    cluster_members: dict[int, list[int]] = {}
    for idx, cluster in enumerate(raw_clusters):
        cluster_members.setdefault(cluster, []).append(idx)

    cluster_demand = {c: sum(demands[i] for i in members) for c, members in cluster_members.items()}

    # Match vehicles to clusters: largest capacity vehicle <-> highest-demand cluster.
    vehicle_order = sorted(range(len(vehicles)), key=lambda v: vehicles[v].capacity, reverse=True)
    cluster_order = sorted(cluster_members.keys(), key=lambda c: cluster_demand[c], reverse=True)

    vehicle_assignments: list[list[int]] = [[] for _ in vehicles]
    remaining_capacity = [v.capacity for v in vehicles]
    vehicle_for_cluster: dict[int, int] = {}
    for cluster, vehicle in zip(cluster_order, vehicle_order, strict=False):
        vehicle_for_cluster[cluster] = vehicle
        vehicle_assignments[vehicle] = list(cluster_members[cluster])
        remaining_capacity[vehicle] -= cluster_demand[cluster]

    def centroid_of(indices: list[int]) -> tuple[float, float]:
        pts = [destination_points[i] for i in indices]
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    unassigned: list[int] = []

    for cluster in cluster_order:
        vehicle = vehicle_for_cluster[cluster]
        # Re-check the live remaining_capacity (it already had this cluster's demand
        # subtracted above), so overflow = how negative it went.
        overflow = -remaining_capacity[vehicle]
        if overflow <= 0:
            continue

        members = sorted(vehicle_assignments[vehicle], key=lambda i: demands[i], reverse=True)
        for idx in members:
            if overflow <= 0:
                break
            demand = demands[idx]

            # Find another vehicle with enough spare capacity, preferring the
            # geographically closest one.
            candidates = [v for v in range(len(vehicles)) if v != vehicle and remaining_capacity[v] >= demand]
            if candidates:
                best = min(
                    candidates,
                    key=lambda v: (
                        dist(destination_points[idx], centroid_of(vehicle_assignments[v]))
                        if vehicle_assignments[v]
                        else 0.0
                    ),
                )
                vehicle_assignments[vehicle].remove(idx)
                vehicle_assignments[best].append(idx)
                remaining_capacity[vehicle] += demand
                remaining_capacity[best] -= demand
                overflow -= demand
            else:
                vehicle_assignments[vehicle].remove(idx)
                remaining_capacity[vehicle] += demand
                unassigned.append(idx)
                overflow -= demand

    return ClusterAssignment(vehicle_assignments=vehicle_assignments, unassigned=sorted(unassigned))
