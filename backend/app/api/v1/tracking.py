"""Driver location tracking and admin fleet-monitoring endpoints (CLAUDE.md
#16 - REST-style, versioned). Additive to /api/v1/fleet/routes, which now also
returns a tracking_code per vehicle and a planning_session_id.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_tracking_service
from app.schemas.tracking import (
    AssignedRoute,
    FleetTrackingOverview,
    LocationPingRequest,
    VehicleTrackingStatus,
)
from app.services.tracking_service import TrackingService

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/jobs/{job_id}", response_model=FleetTrackingOverview)
async def get_fleet_overview(
    job_id: str, tracking_service: TrackingService = Depends(get_tracking_service)
) -> FleetTrackingOverview:
    """Admin view: every vehicle from one planning run, its current location,
    distance travelled, and whether it has strayed off its planned route."""
    return tracking_service.get_fleet_overview(job_id)


@router.get("/{tracking_code}", response_model=AssignedRoute)
async def get_assigned_route(
    tracking_code: str, tracking_service: TrackingService = Depends(get_tracking_service)
) -> AssignedRoute:
    """Driver view: the stops and route this tracking code was assigned."""
    return tracking_service.get_assigned_route(tracking_code)


@router.get("/{tracking_code}/status", response_model=VehicleTrackingStatus)
async def get_status(
    tracking_code: str, tracking_service: TrackingService = Depends(get_tracking_service)
) -> VehicleTrackingStatus:
    return tracking_service.get_status(tracking_code)


@router.post("/{tracking_code}/ping", status_code=204)
async def record_ping(
    tracking_code: str,
    request: LocationPingRequest,
    tracking_service: TrackingService = Depends(get_tracking_service),
) -> None:
    """A driver's app calls this periodically while en route (e.g. every
    15-30s) to report their current location."""
    tracking_service.record_ping(tracking_code, request.coordinate)
