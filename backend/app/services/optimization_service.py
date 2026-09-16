"""Optimization service (CLAUDE.md #6.2 - API/Worker -> Optimization Service -> Algorithm).

For this first feature (origin -> destination only, CLAUDE.md #15) there is
never more than one intermediate-stop arrangement, so QPSO has nothing to
search for. The service reports this honestly as algorithm="DIRECT_ROUTE"
rather than claiming an optimization that did not happen. The QPSOSolver
call is wired in for when a request carries 2+ intermediate stops (future
VRP work), so the pipeline does not need to change shape then.
"""

import time

from app.optimization.qpso import QPSOSolver
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.routing.base import RoutingProvider
from app.schemas.optimization import OptimizationRouteResult
from app.schemas.routing import Coordinate, RouteRequest

_DIRECT_ROUTE_EXPLANATION = (
    "Single origin-to-destination request: the road route was used directly. "
    "There is no stop order to optimize with only two points."
)
_QPSO_EXPLANATION = "Stop order optimized with QPSO to reduce total estimated travel cost."


class OptimizationService:
    def __init__(
        self,
        routing_provider: RoutingProvider,
        job_repository: OptimizationJobRepository,
        qpso_solver: QPSOSolver | None = None,
    ) -> None:
        self._routing_provider = routing_provider
        self._job_repository = job_repository
        self._qpso_solver = qpso_solver or QPSOSolver()

    async def plan_route(self, request: RouteRequest):
        stops: list[Coordinate] = [request.origin, request.destination]
        intermediate_stop_count = len(stops) - 2

        start = time.perf_counter()
        route = await self._routing_provider.route(stops)

        if intermediate_stop_count >= 2:
            matrix = await self._routing_provider.matrix(stops)
            qpso_result = self._qpso_solver.optimize(
                matrix.durations_seconds, num_intermediate_stops=intermediate_stop_count
            )
            algorithm = "QPSO"
            explanation = _QPSO_EXPLANATION
            objective_value = qpso_result.total_cost
        else:
            algorithm = "DIRECT_ROUTE"
            explanation = _DIRECT_ROUTE_EXPLANATION
            objective_value = None

        runtime_ms = (time.perf_counter() - start) * 1000

        result = OptimizationRouteResult(
            route=route,
            algorithm=algorithm,
            status="COMPLETED",
            stops_count=len(stops),
            objective_value=objective_value,
            optimization_runtime_ms=runtime_ms,
            explanation=explanation,
        )

        job = self._job_repository.create_completed(
            input_dataset={
                "origin": request.origin.model_dump(),
                "destination": request.destination.model_dump(),
            },
            objective={"minimize": "travel_time"},
            algorithm=algorithm,
            result=result.model_dump(mode="json"),
        )

        return job, result
