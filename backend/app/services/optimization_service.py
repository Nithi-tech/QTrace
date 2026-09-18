"""Optimization service (CLAUDE.md #6.2 - API/Worker -> Optimization Service -> Algorithm).

With 0-1 intermediate stops there is only one possible visit order, so QPSO has
nothing to search for; the service reports this honestly as algorithm="DIRECT_ROUTE"
rather than claiming an optimization that did not happen (CLAUDE.md #15). With 2+
intermediate stops, the pipeline follows CLAUDE.md #9/#11 - OSRM's table service is
called exactly once to build a local distance/duration matrix, QPSO searches that
matrix entirely in-process, and OSRM's route service is called exactly once more,
on the QPSO-optimized order, to get the final road geometry. OSRM is never called
from inside the QPSO fitness loop.

Traffic (docs/TRAFFIC_ARCHITECTURE.md): TrafficMatrixService is queried once per
request to resolve every unique stop's traffic (TomTom live -> QTrace crowd ->
historical -> unavailable) and build a traffic matrix. When 2+ intermediate stops are
present, that matrix is blended with distance/duration (app/optimization/fitness.py)
into the single cost matrix QPSO actually searches - so traffic genuinely changes
which order QPSO picks, it is not just decoration on the response. QPSO itself
(app/optimization/qpso.py) is unmodified - it always only ever saw a generic
cost_matrix.
"""

import time

from app.optimization.fitness import FitnessWeights, build_cost_matrix
from app.optimization.qpso import QPSOSolver
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.repositories.traffic_repository import TrafficRepository
from app.routing.base import RoutingProvider
from app.routing.exceptions import TooManyStopsError
from app.schemas.optimization import OptimizationRouteResult
from app.schemas.routing import Coordinate, RouteRequest
from app.schemas.traffic import TrafficStatus
from app.traffic.aggregation import classify_traffic_level
from app.traffic.matrix_service import TrafficMatrixResult, TrafficMatrixService

_DIRECT_ROUTE_EXPLANATION = (
    "Single origin-to-destination request: the road route was used directly. "
    "There is no stop order to optimize with fewer than two intermediate stops."
)
_QPSO_EXPLANATION = "Stop order optimized with QPSO to reduce total estimated travel time."


def _unavailable_traffic_result(num_stops: int) -> TrafficMatrixResult:
    return TrafficMatrixResult(
        matrix=[[0.0] * num_stops for _ in range(num_stops)],
        status=TrafficStatus(enabled=False, available=False, status="UNAVAILABLE", source=None),
    )


class OptimizationService:
    def __init__(
        self,
        routing_provider: RoutingProvider,
        job_repository: OptimizationJobRepository,
        qpso_solver: QPSOSolver | None = None,
        max_stops: int = 25,
        traffic_repository: TrafficRepository | None = None,
        traffic_matrix_service: TrafficMatrixService | None = None,
        traffic_enabled: bool = False,
        fitness_weights: FitnessWeights | None = None,
    ) -> None:
        self._routing_provider = routing_provider
        self._job_repository = job_repository
        self._qpso_solver = qpso_solver or QPSOSolver()
        self._max_stops = max_stops
        self._traffic_repository = traffic_repository
        self._traffic_matrix_service = traffic_matrix_service
        self._traffic_enabled = traffic_enabled
        self._fitness_weights = fitness_weights or FitnessWeights()

    async def _get_traffic_matrix(self, full_order_stops: list[Coordinate]) -> TrafficMatrixResult:
        if self._traffic_repository is None or self._traffic_matrix_service is None:
            return _unavailable_traffic_result(len(full_order_stops))
        return await self._traffic_matrix_service.get_traffic_matrix(
            self._traffic_repository, full_order_stops, enabled=self._traffic_enabled
        )

    async def plan_route(self, request: RouteRequest):
        intermediate_stops: list[Coordinate] = request.stops
        intermediate_count = len(intermediate_stops)
        full_order_stops = [request.origin, *intermediate_stops, request.destination]
        total_locations = len(full_order_stops)

        if total_locations > self._max_stops:
            raise TooManyStopsError(
                f"Request has {total_locations} locations; the configured limit is "
                f"{self._max_stops} (MAX_ROUTE_STOPS)."
            )

        start = time.perf_counter()

        traffic_result = await self._get_traffic_matrix(full_order_stops)

        if intermediate_count >= 2:
            matrix = await self._routing_provider.matrix(full_order_stops)
            cost_matrix = build_cost_matrix(
                matrix.distances_meters,
                matrix.durations_seconds,
                traffic_result.matrix,
                self._fitness_weights,
            )
            qpso_result = self._qpso_solver.optimize(cost_matrix, num_intermediate_stops=intermediate_count)
            ordered_stops = [
                request.origin,
                *(intermediate_stops[i] for i in qpso_result.order),
                request.destination,
            ]
            final_indices = [0, *(i + 1 for i in qpso_result.order), total_locations - 1]
            route = await self._routing_provider.route(ordered_stops)
            algorithm = "QPSO"
            explanation = _QPSO_EXPLANATION
            objective_value = qpso_result.total_cost
            stop_order = qpso_result.order
        else:
            ordered_stops = full_order_stops
            final_indices = list(range(total_locations))
            route = await self._routing_provider.route(ordered_stops)
            algorithm = "DIRECT_ROUTE"
            explanation = _DIRECT_ROUTE_EXPLANATION
            objective_value = None
            stop_order = list(range(intermediate_count))

        edge_scores = [
            traffic_result.matrix[final_indices[k]][final_indices[k + 1]]
            for k in range(len(final_indices) - 1)
        ]
        avg_traffic_score = sum(edge_scores) / len(edge_scores) if edge_scores else 0.0
        traffic_available = traffic_result.status.available
        traffic_impact_seconds = route.duration_seconds * avg_traffic_score if traffic_available else None
        # Classified from this specific route's own edges (the same avg_traffic_score
        # traffic_impact_seconds uses), not a whole-matrix average - so the label a rider
        # sees always matches the delay actually added to their route (CLAUDE.md #72).
        traffic_status = traffic_result.status.model_copy(
            update={"level": classify_traffic_level(avg_traffic_score) if traffic_available else None}
        )

        runtime_ms = (time.perf_counter() - start) * 1000

        result = OptimizationRouteResult(
            route=route,
            algorithm=algorithm,
            status="COMPLETED",
            stops_count=len(ordered_stops),
            stop_order=stop_order,
            objective_value=objective_value,
            optimization_runtime_ms=runtime_ms,
            explanation=explanation,
            traffic=traffic_status,
            traffic_impact_seconds=traffic_impact_seconds,
        )

        job = self._job_repository.create_completed(
            input_dataset={
                "origin": request.origin.model_dump(),
                "destination": request.destination.model_dump(),
                "stops": [stop.model_dump() for stop in intermediate_stops],
            },
            objective={"minimize": "travel_time"},
            algorithm=algorithm,
            result=result.model_dump(mode="json"),
        )

        return job, result
