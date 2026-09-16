"""Optimization service (CLAUDE.md #6.2 - API/Worker -> Optimization Service -> Algorithm).

With 0-1 intermediate stops there is only one possible visit order, so QPSO has
nothing to search for; the service reports this honestly as algorithm="DIRECT_ROUTE"
rather than claiming an optimization that did not happen (CLAUDE.md #15). With 2+
intermediate stops, the pipeline follows CLAUDE.md #9/#11 - OSRM's table service is
called exactly once to build a local distance/duration matrix, QPSO searches that
matrix entirely in-process, and OSRM's route service is called exactly once more,
on the QPSO-optimized order, to get the final road geometry. OSRM is never called
from inside the QPSO fitness loop.
"""

import time

from app.optimization.qpso import QPSOSolver
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.routing.base import RoutingProvider
from app.routing.exceptions import TooManyStopsError
from app.schemas.optimization import OptimizationRouteResult
from app.schemas.routing import Coordinate, RouteRequest

_DIRECT_ROUTE_EXPLANATION = (
    "Single origin-to-destination request: the road route was used directly. "
    "There is no stop order to optimize with fewer than two intermediate stops."
)
_QPSO_EXPLANATION = "Stop order optimized with QPSO to reduce total estimated travel time."


class OptimizationService:
    def __init__(
        self,
        routing_provider: RoutingProvider,
        job_repository: OptimizationJobRepository,
        qpso_solver: QPSOSolver | None = None,
        max_stops: int = 25,
    ) -> None:
        self._routing_provider = routing_provider
        self._job_repository = job_repository
        self._qpso_solver = qpso_solver or QPSOSolver()
        self._max_stops = max_stops

    async def plan_route(self, request: RouteRequest):
        intermediate_stops: list[Coordinate] = request.stops
        intermediate_count = len(intermediate_stops)
        total_locations = intermediate_count + 2  # + origin + destination

        if total_locations > self._max_stops:
            raise TooManyStopsError(
                f"Request has {total_locations} locations; the configured limit is "
                f"{self._max_stops} (MAX_ROUTE_STOPS)."
            )

        start = time.perf_counter()

        if intermediate_count >= 2:
            full_order_stops = [request.origin, *intermediate_stops, request.destination]
            matrix = await self._routing_provider.matrix(full_order_stops)
            qpso_result = self._qpso_solver.optimize(
                matrix.durations_seconds, num_intermediate_stops=intermediate_count
            )
            ordered_stops = [
                request.origin,
                *(intermediate_stops[i] for i in qpso_result.order),
                request.destination,
            ]
            route = await self._routing_provider.route(ordered_stops)
            algorithm = "QPSO"
            explanation = _QPSO_EXPLANATION
            objective_value = qpso_result.total_cost
            stop_order = qpso_result.order
        else:
            ordered_stops = [request.origin, *intermediate_stops, request.destination]
            route = await self._routing_provider.route(ordered_stops)
            algorithm = "DIRECT_ROUTE"
            explanation = _DIRECT_ROUTE_EXPLANATION
            objective_value = None
            stop_order = list(range(intermediate_count))

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
