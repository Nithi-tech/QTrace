"""Multi-vehicle fleet routing endpoint (CLAUDE.md #16 - REST-style, versioned).

Additive to the existing single-vehicle /api/v1/optimization/jobs endpoint -
this router does not change or replace it.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_fleet_optimization_service, get_tracking_service
from app.schemas.fleet import FleetRouteRequest, FleetRouteResponse
from app.services.fleet_optimization_service import FleetOptimizationService
from app.services.tracking_service import TrackingService

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.post("/routes", response_model=FleetRouteResponse)
async def create_fleet_routes(
    request: FleetRouteRequest,
    fleet_service: FleetOptimizationService = Depends(get_fleet_optimization_service),
    tracking_service: TrackingService = Depends(get_tracking_service),
) -> FleetRouteResponse:
    job, response = await fleet_service.plan_fleet_routes(request)

    # One tracking code per vehicle actually used, so each driver has an id to
    # enter in the Drivers page and the admin has a planning_session_id to
    # pull up every vehicle from this run in the fleet tracking view. Purely
    # additive - FleetOptimizationService itself never sees or creates these.
    codes = tracking_service.create_sessions_for_job(
        job.id, [route.vehicle_index for route in response.vehicle_routes]
    )
    response = response.model_copy(
        update={
            "planning_session_id": job.id,
            "vehicle_routes": [
                route.model_copy(update={"tracking_code": codes.get(route.vehicle_index)})
                for route in response.vehicle_routes
            ],
        }
    )
    return response
