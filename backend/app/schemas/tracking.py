"""Vehicle tracking data contracts - driver location reporting and admin fleet
monitoring. Additive to app/schemas/fleet.py (which gains a `tracking_code` per
vehicle route and a `planning_session_id` at the top level - see FleetRouteResponse).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.routing import Coordinate


class LocationPingRequest(BaseModel):
    coordinate: Coordinate


class AssignedRoute(BaseModel):
    """What a driver's app shows after entering their tracking code: their
    assigned stops and route geometry, exactly as planned."""

    tracking_code: str
    vehicle_type: str
    stop_names: list[str]
    geometry: list[Coordinate]
    distance_meters: float
    duration_seconds: float


class VehicleTrackingStatus(BaseModel):
    """One vehicle's live status - used for both the driver's own map and each
    entry in the admin's fleet-wide view."""

    tracking_code: str
    vehicle_index: int
    vehicle_type: str
    stop_names: list[str]
    geometry: list[Coordinate]
    planned_distance_meters: float
    current_location: Coordinate | None = None
    last_ping_at: datetime | None = None
    distance_travelled_meters: float = 0.0
    is_off_route: bool = False
    off_route_distance_meters: float | None = None


class FleetTrackingOverview(BaseModel):
    job_id: str
    vehicles: list[VehicleTrackingStatus]
