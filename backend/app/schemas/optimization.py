from datetime import datetime

from pydantic import BaseModel, Field

from app.models.optimization_job import OptimizationJobStatus
from app.schemas.routing import RouteRequest, RouteResult

# Request for the first QTrace feature: a single origin -> destination route.
# Intentionally does not accept intermediate stops yet (CLAUDE.md #15 -
# implement only what this feature actually requires); the service layer
# underneath is already shaped to extend to a stops list for VRP later.
OptimizationRouteRequest = RouteRequest


class OptimizationRouteResult(BaseModel):
    route: RouteResult
    algorithm: str = Field(
        description='"DIRECT_ROUTE" when there is no stop-ordering decision to make, "QPSO" once solved.'
    )
    status: OptimizationJobStatus
    stops_count: int
    objective_value: float | None = None
    optimization_runtime_ms: float | None = None
    explanation: str


class OptimizationJobResponse(BaseModel):
    id: str
    status: OptimizationJobStatus
    algorithm: str
    result: OptimizationRouteResult
    created_at: datetime
