"""Multi-vehicle fleet routing service (CLAUDE.md #6.2 - API -> Service -> Algorithm).

Pipeline (see docs/qisa-roadmap.md for the planned future per-vehicle solver):

    Destinations (+ geocoding for any missing coordinates)
        -> RoutingProvider.matrix() once, over depot + all resolved destinations
        -> fleet-aware sweep clustering (app.optimization.clustering)
        -> per vehicle: nearest-neighbor construction (app.optimization.greedy_route)
                        + 2-Opt refinement (app.optimization.two_opt)
        -> RoutingProvider.route() once per vehicle, on its final stop order
        -> cost / load / time-window checks
        -> FleetRouteResponse

This is entirely additive: it does not touch OptimizationService, QPSOSolver,
or the existing single-vehicle /api/v1/optimization/jobs endpoint.
"""

from __future__ import annotations

import time as time_module
from datetime import datetime, time, timedelta

from app.geocoding.base import GeocodingProvider
from app.optimization.clustering import VehicleInstance, fleet_aware_clusters
from app.optimization.greedy_route import nearest_neighbor_order
from app.optimization.two_opt import two_opt_refine
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.routing.base import RoutingProvider
from app.schemas.fleet import (
    Destination,
    FleetRouteRequest,
    FleetRouteResponse,
    OptimizationObjective,
    VehicleRouteResult,
)
from app.schemas.routing import Coordinate
from app.services.exceptions import FleetInfeasibleError

_ALGORITHM = "GREEDY_NN_2OPT"


def _select_cost_matrix(
    objective: OptimizationObjective,
    distances_meters: list[list[float]],
    durations_seconds: list[list[float]],
) -> list[list[float]]:
    # MIN_COST uses distance because cost = distance_km * a fixed cost_per_km for the
    # vehicle: minimizing distance minimizes cost for any fixed per-km rate.
    if objective in (OptimizationObjective.MIN_DISTANCE, OptimizationObjective.MIN_COST):
        return distances_meters
    return durations_seconds  # MIN_TIME and BALANCED


class FleetOptimizationService:
    def __init__(
        self,
        routing_provider: RoutingProvider,
        geocoding_provider: GeocodingProvider,
        job_repository: OptimizationJobRepository,
    ) -> None:
        self._routing_provider = routing_provider
        self._geocoding_provider = geocoding_provider
        self._job_repository = job_repository

    async def _resolve_coordinate(self, destination: Destination) -> Coordinate | None:
        if destination.coordinate is not None:
            return destination.coordinate
        suggestions = await self._geocoding_provider.search(destination.address, limit=1)
        return suggestions[0].coordinate if suggestions else None

    def _expand_vehicles(self, request: FleetRouteRequest) -> list[VehicleInstance]:
        instances: list[VehicleInstance] = []
        for spec in request.vehicles:
            instances.extend(
                VehicleInstance(
                    vehicle_type=spec.vehicle_type,
                    capacity=spec.capacity,
                    cost_per_km=spec.cost_per_km,
                    availability_start=spec.availability_start,
                    availability_end=spec.availability_end,
                )
                for _ in range(spec.count)
            )
        return instances

    def _check_time_windows(
        self,
        vehicle_availability_start: time | None,
        vehicle_availability_end: time | None,
        order: list[int],
        destination_by_matrix_index: dict[int, Destination],
        durations_seconds: list[list[float]],
    ) -> list[str]:
        """Heuristic sequential check: does each stop get reached inside its time
        window, assuming departure at the vehicle's availability_start (or
        midnight if unset)? `order` includes the depot (matrix index 0) at its
        start and, if the vehicle returns to base, its end. Also flags the
        vehicle's own availability_end being exceeded by the time the route
        finishes (its last position in `order`), so that input isn't collected
        and then silently ignored. Ignores overnight wraparound (CLAUDE.md #40
        note: a full CVRPTW time-domain model is future work, see
        docs/qisa-roadmap.md)."""
        violations: list[str] = []
        clock = datetime.combine(datetime.min.date(), vehicle_availability_start or time(0, 0))

        for position in range(1, len(order)):
            clock += timedelta(seconds=durations_seconds[order[position - 1]][order[position]])
            destination = destination_by_matrix_index.get(order[position])
            if destination is None:
                continue  # back at the depot - no time window to check
            if destination.time_window_start is not None and clock.time() < destination.time_window_start:
                clock = datetime.combine(
                    clock.date(), destination.time_window_start
                )  # wait for the window to open
            if destination.time_window_end is not None and clock.time() > destination.time_window_end:
                violations.append(
                    f"{destination.name}: arrived at {clock.time().strftime('%H:%M')}, "
                    f"after window end {destination.time_window_end.strftime('%H:%M')}"
                )
            clock += timedelta(seconds=destination.service_time_seconds)

        if vehicle_availability_end is not None and clock.time() > vehicle_availability_end:
            violations.append(
                f"Vehicle: route finishes at {clock.time().strftime('%H:%M')}, "
                f"after it is available until {vehicle_availability_end.strftime('%H:%M')}"
            )

        return violations

    async def plan_fleet_routes(self, request: FleetRouteRequest) -> tuple[object, FleetRouteResponse]:
        start = time_module.perf_counter()
        vehicles = self._expand_vehicles(request)

        resolved_coordinates: list[Coordinate | None] = [
            await self._resolve_coordinate(destination) for destination in request.destinations
        ]

        geocoded_indices = [i for i, c in enumerate(resolved_coordinates) if c is not None]
        unresolved_indices = [i for i, c in enumerate(resolved_coordinates) if c is None]

        if not geocoded_indices:
            raise FleetInfeasibleError(
                "None of the requested destinations could be resolved to a coordinate; nothing to route."
            )

        full_points = [request.depot] + [resolved_coordinates[i] for i in geocoded_indices]
        matrix = await self._routing_provider.matrix(full_points)
        cost_matrix = _select_cost_matrix(
            request.objective, matrix.distances_meters, matrix.durations_seconds
        )

        # matrix index 0 is the depot; matrix index (1 + local) is geocoded_indices[local].
        destination_points = [
            (resolved_coordinates[i].latitude, resolved_coordinates[i].longitude) for i in geocoded_indices
        ]
        demands = [request.destinations[i].demand for i in geocoded_indices]

        assignment = fleet_aware_clusters(
            destination_points,
            demands,
            vehicles,
            depot=(request.depot.latitude, request.depot.longitude),
        )

        vehicle_routes: list[VehicleRouteResult] = []
        for vehicle_index, local_indices in enumerate(assignment.vehicle_assignments):
            if not local_indices:
                continue
            vehicle = vehicles[vehicle_index]

            matrix_indices = [1 + local for local in local_indices]
            order = nearest_neighbor_order(
                cost_matrix,
                start_index=0,
                stop_indices=matrix_indices,
                end_index=0 if request.return_to_depot else None,
            )
            order = two_opt_refine(cost_matrix, order, fixed_end=request.return_to_depot)

            ordered_coordinates = [
                request.depot if m == 0 else resolved_coordinates[geocoded_indices[m - 1]] for m in order
            ]
            route = await self._routing_provider.route(ordered_coordinates)

            destination_by_matrix_index = {
                m: request.destinations[geocoded_indices[m - 1]] for m in matrix_indices
            }
            stop_destination_order = [destination_by_matrix_index[m] for m in order if m != 0]
            original_destination_indices = [geocoded_indices[m - 1] for m in order if m != 0]

            load = sum(request.destinations[i].demand for i in original_destination_indices)
            distance_km = route.distance_meters / 1000.0
            violations = self._check_time_windows(
                vehicle.availability_start,
                vehicle.availability_end,
                order,
                destination_by_matrix_index,
                matrix.durations_seconds,
            )

            stop_names = ["Depot"] + [d.name for d in stop_destination_order]
            if request.return_to_depot:
                stop_names.append("Depot")

            vehicle_routes.append(
                VehicleRouteResult(
                    vehicle_index=vehicle_index,
                    vehicle_type=vehicle.vehicle_type,
                    stop_names=stop_names,
                    destination_indices=original_destination_indices,
                    distance_meters=route.distance_meters,
                    duration_seconds=route.duration_seconds,
                    load=load,
                    capacity=vehicle.capacity,
                    capacity_utilization=(load / vehicle.capacity) if vehicle.capacity else 0.0,
                    estimated_cost=distance_km * vehicle.cost_per_km,
                    time_window_violations=violations,
                    geometry=route.geometry,
                )
            )

        unassigned = sorted(unresolved_indices + [geocoded_indices[i] for i in assignment.unassigned])
        reasons = []
        if unresolved_indices:
            names = ", ".join(request.destinations[i].name for i in unresolved_indices)
            reasons.append(f"could not geocode: {names}")
        if assignment.unassigned:
            names = ", ".join(request.destinations[geocoded_indices[i]].name for i in assignment.unassigned)
            reasons.append(f"exceeds available fleet capacity: {names}")

        response = FleetRouteResponse(
            scenario=request.scenario,
            objective=request.objective,
            algorithm=_ALGORITHM,
            is_feasible=not unassigned,
            infeasibility_reason="; ".join(reasons) if reasons else None,
            vehicle_routes=vehicle_routes,
            unassigned_destination_indices=unassigned,
            total_distance_meters=sum(v.distance_meters for v in vehicle_routes),
            total_duration_seconds=sum(v.duration_seconds for v in vehicle_routes),
            total_estimated_cost=sum(v.estimated_cost for v in vehicle_routes),
            optimization_runtime_ms=(time_module.perf_counter() - start) * 1000,
        )

        job = self._job_repository.create_completed(
            input_dataset=request.model_dump(mode="json"),
            objective={"type": request.objective.value},
            algorithm=_ALGORITHM,
            result=response.model_dump(mode="json"),
        )

        return job, response
