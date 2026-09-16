from datetime import datetime

from pydantic import BaseModel, Field

from app.models.optimization_job import OptimizationJobStatus
from app.schemas.routing import RouteRequest, RouteResult

# origin, destination, and 0+ intermediate stops (CLAUDE.md #8.2 - a TSP-path
# variant of VRP; CVRP/CVRPTW constraints are not yet implemented).
OptimizationRouteRequest = RouteRequest


class OptimizationRouteResult(BaseModel):
    route: RouteResult
    algorithm: str = Field(
        description='"DIRECT_ROUTE" when there is no stop-ordering decision to make, "QPSO" once solved.'
    )
    status: OptimizationJobStatus
    stops_count: int
    stop_order: list[int] = Field(
        description="Indices into the request's `stops` list, in the order QPSO visits them."
    )
    objective_value: float | None = None
    optimization_runtime_ms: float | None = None
    explanation: str


class OptimizationJobResponse(BaseModel):
    id: str
    status: OptimizationJobStatus
    algorithm: str
    result: OptimizationRouteResult
    created_at: datetime
