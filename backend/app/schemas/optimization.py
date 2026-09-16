from datetime import datetime

from pydantic import BaseModel, Field

from app.models.optimization_job import OptimizationJobStatus
from app.schemas.routing import RouteRequest, RouteResult
from app.schemas.traffic import TrafficStatus

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
    traffic: TrafficStatus
    traffic_level: str | None = Field(
        default=None,
        description="LOW/MODERATE/HIGH/SEVERE; None when traffic is unavailable (CLAUDE.md #49 - never "
        "reported as LOW when there is simply no data).",
    )
    traffic_delay_seconds: float | None = Field(
        default=None,
        description="Estimated extra travel time from matched QTrace telemetry. Only populated when "
        "traffic.live is true - never fabricated for baseline/unavailable data (CLAUDE.md #68).",
    )


class OptimizationJobResponse(BaseModel):
    id: str
    status: OptimizationJobStatus
    algorithm: str
    result: OptimizationRouteResult
    created_at: datetime
