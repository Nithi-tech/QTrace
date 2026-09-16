"""Multi-vehicle fleet routing endpoint (CLAUDE.md #16 - REST-style, versioned).

Additive to the existing single-vehicle /api/v1/optimization/jobs endpoint -
this router does not change or replace it.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_fleet_optimization_service
from app.schemas.fleet import FleetRouteRequest, FleetRouteResponse
from app.services.fleet_optimization_service import FleetOptimizationService

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.post("/routes", response_model=FleetRouteResponse)
async def create_fleet_routes(
    request: FleetRouteRequest,
    fleet_service: FleetOptimizationService = Depends(get_fleet_optimization_service),
) -> FleetRouteResponse:
    _job, response = await fleet_service.plan_fleet_routes(request)
    return response
