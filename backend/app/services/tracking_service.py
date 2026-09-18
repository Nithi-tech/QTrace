"""Vehicle tracking service - generates each vehicle's driver tracking code,
serves a driver's assigned route back to them, records their location pings,
and builds the live status (current location, distance travelled, whether
they've strayed off the planned route) both a driver and the admin fleet-wide
view are built from.

Entirely additive: FleetOptimizationService and its algorithms are untouched -
this only reads a completed job's already-stored result JSON by
(job_id, vehicle_index) rather than duplicating route data.
"""

from __future__ import annotations

import random
import string
from math import asin, cos, radians, sin, sqrt

from app.repositories.tracking_repository import TrackingRepository
from app.schemas.routing import Coordinate
from app.schemas.tracking import AssignedRoute, FleetTrackingOverview, VehicleTrackingStatus
from app.services.exceptions import TrackingSessionNotFoundError

_EARTH_RADIUS_METERS = 6_371_000.0
_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LENGTH = 6
# A driver more than this far from every point on their planned route is
# flagged as off-route on the admin view. Chosen to tolerate normal GPS drift
# and minor road-level detours without false-flagging every ping.
_OFF_ROUTE_THRESHOLD_METERS = 250.0


def _haversine_meters(a: Coordinate, b: Coordinate) -> float:
    lat1, lon1, lat2, lon2 = (radians(v) for v in (a.latitude, a.longitude, b.latitude, b.longitude))
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    h = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    return 2 * _EARTH_RADIUS_METERS * asin(sqrt(min(1.0, h)))


def _min_distance_to_route_meters(point: Coordinate, geometry: list[Coordinate]) -> float | None:
    """Nearest-vertex approximation, not exact point-to-segment projection - a
    planned route's geometry is many closely-spaced road-snapped points
    (from OSRM), so this is accurate enough without extra geometry math
    (CLAUDE.md #32 - no new dependency for one calculation)."""
    if not geometry:
        return None
    return min(_haversine_meters(point, vertex) for vertex in geometry)


def _parse_geometry(raw_geometry: dict | None) -> list[Coordinate]:
    if not raw_geometry:
        return []
    coordinates = raw_geometry.get("coordinates") or []
    return [Coordinate(latitude=lat, longitude=lon) for lon, lat in coordinates]


def _find_vehicle_route(job_result: dict, vehicle_index: int) -> dict | None:
    for route in job_result.get("vehicle_routes", []):
        if route.get("vehicle_index") == vehicle_index:
            return route
    return None


class TrackingService:
    def __init__(self, repository: TrackingRepository) -> None:
        self._repository = repository

    def create_sessions_for_job(self, job_id: str, vehicle_indices: list[int]) -> dict[int, str]:
        """One tracking code per vehicle actually used in this planning run."""
        codes: dict[int, str] = {}
        for vehicle_index in vehicle_indices:
            code = self._generate_unique_code()
            self._repository.create_session(job_id=job_id, vehicle_index=vehicle_index, tracking_code=code)
            codes[vehicle_index] = code
        return codes

    def _generate_unique_code(self) -> str:
        for _ in range(20):
            candidate = "".join(random.choices(_CODE_ALPHABET, k=_CODE_LENGTH))
            if not self._repository.code_exists(candidate):
                return candidate
        raise RuntimeError("Could not generate a unique tracking code after 20 attempts.")

    def get_assigned_route(self, tracking_code: str) -> AssignedRoute:
        session = self._repository.get_by_code(tracking_code)
        if session is None:
            raise TrackingSessionNotFoundError(f"No tracking session for code {tracking_code!r}.")
        job = self._repository.get_job(session.job_id)
        if job is None or job.result is None:
            raise TrackingSessionNotFoundError(f"Planning job for code {tracking_code!r} no longer exists.")
        route = _find_vehicle_route(job.result, session.vehicle_index)
        if route is None:
            raise TrackingSessionNotFoundError(f"Vehicle route for code {tracking_code!r} no longer exists.")

        return AssignedRoute(
            tracking_code=tracking_code,
            vehicle_type=route["vehicle_type"],
            stop_names=route["stop_names"],
            geometry=_parse_geometry(route.get("geometry")),
            distance_meters=route["distance_meters"],
            duration_seconds=route["duration_seconds"],
        )

    def record_ping(self, tracking_code: str, coordinate: Coordinate) -> None:
        session = self._repository.get_by_code(tracking_code)
        if session is None:
            raise TrackingSessionNotFoundError(f"No tracking session for code {tracking_code!r}.")
        self._repository.add_ping(session.id, coordinate.latitude, coordinate.longitude)

    def get_status(self, tracking_code: str) -> VehicleTrackingStatus:
        session = self._repository.get_by_code(tracking_code)
        if session is None:
            raise TrackingSessionNotFoundError(f"No tracking session for code {tracking_code!r}.")
        job = self._repository.get_job(session.job_id)
        if job is None or job.result is None:
            raise TrackingSessionNotFoundError(f"Planning job for code {tracking_code!r} no longer exists.")
        route = _find_vehicle_route(job.result, session.vehicle_index)
        if route is None:
            raise TrackingSessionNotFoundError(f"Vehicle route for code {tracking_code!r} no longer exists.")
        return self._build_status(session.tracking_code, session.vehicle_index, session.id, route)

    def get_fleet_overview(self, job_id: str) -> FleetTrackingOverview:
        job = self._repository.get_job(job_id)
        if job is None or job.result is None:
            raise TrackingSessionNotFoundError(f"No planning job {job_id!r}.")

        vehicles = []
        for session in self._repository.list_sessions_for_job(job_id):
            route = _find_vehicle_route(job.result, session.vehicle_index)
            if route is None:
                continue  # stale session referencing a route that no longer exists in the job result
            vehicles.append(
                self._build_status(session.tracking_code, session.vehicle_index, session.id, route)
            )

        return FleetTrackingOverview(job_id=job_id, vehicles=vehicles)

    def _build_status(
        self, tracking_code: str, vehicle_index: int, session_id: str, route: dict
    ) -> VehicleTrackingStatus:
        geometry = _parse_geometry(route.get("geometry"))
        pings = self._repository.list_pings(session_id)

        distance_travelled = 0.0
        for previous, current in zip(pings, pings[1:]):
            distance_travelled += _haversine_meters(
                Coordinate(latitude=previous.latitude, longitude=previous.longitude),
                Coordinate(latitude=current.latitude, longitude=current.longitude),
            )

        current_location: Coordinate | None = None
        off_route_distance: float | None = None
        if pings:
            latest = pings[-1]
            current_location = Coordinate(latitude=latest.latitude, longitude=latest.longitude)
            off_route_distance = _min_distance_to_route_meters(current_location, geometry)

        return VehicleTrackingStatus(
            tracking_code=tracking_code,
            vehicle_index=vehicle_index,
            vehicle_type=route["vehicle_type"],
            stop_names=route["stop_names"],
            geometry=geometry,
            planned_distance_meters=route["distance_meters"],
            current_location=current_location,
            last_ping_at=pings[-1].recorded_at if pings else None,
            distance_travelled_meters=distance_travelled,
            is_off_route=off_route_distance is not None and off_route_distance > _OFF_ROUTE_THRESHOLD_METERS,
            off_route_distance_meters=off_route_distance,
        )
