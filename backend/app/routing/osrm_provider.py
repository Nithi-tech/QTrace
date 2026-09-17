"""OSRM-backed RoutingProvider (CLAUDE.md #11 - OSRM for development/testing).

Coordinate order note (CLAUDE.md #39): OSRM's HTTP API expects "longitude,latitude"
pairs. Conversion from the app-wide (latitude, longitude) convention happens only
in this module, at the provider boundary.
"""

import logging

import httpx

from app.routing.base import RoutingProvider
from app.routing.exceptions import (
    InvalidRouteInputError,
    RoutingProviderTimeoutError,
    RoutingProviderUnavailableError,
)
from app.routing.map_matching import RoadMatchingProvider
from app.schemas.map_matching import MatchedEdge, MatchedLeg, SnapResult, TimedCoordinate, TraceMatchResult
from app.schemas.routing import Coordinate, MatrixResult, RouteResult

logger = logging.getLogger(__name__)


def _format_coordinates(coordinates: list[Coordinate]) -> str:
    return ";".join(f"{c.longitude},{c.latitude}" for c in coordinates)


class OSRMProvider(RoutingProvider, RoadMatchingProvider):
    def __init__(
        self,
        base_url: str,
        profile: str = "driving",
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._profile = profile
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def geocode(self, address: str) -> Coordinate:
        # OSRM is a routing engine, not a geocoder - it has no address-lookup endpoint.
        # Geocoding must go through a separate, explicitly configured provider.
        raise NotImplementedError("OSRMProvider does not support geocoding; configure a geocoding provider.")

    async def route(self, coordinates: list[Coordinate]) -> RouteResult:
        if len(coordinates) < 2:
            raise InvalidRouteInputError("route() requires at least two coordinates.")

        path = f"/route/v1/{self._profile}/{_format_coordinates(coordinates)}"
        params = {"overview": "full", "geometries": "geojson"}
        payload = await self._get(path, params)

        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise RoutingProviderUnavailableError(f"OSRM returned no route: {payload.get('code')}")

        route = payload["routes"][0]
        return RouteResult(
            distance_meters=route["distance"],
            duration_seconds=route["duration"],
            geometry=route.get("geometry"),
        )

    async def matrix(self, coordinates: list[Coordinate]) -> MatrixResult:
        if len(coordinates) < 2:
            raise InvalidRouteInputError("matrix() requires at least two coordinates.")

        path = f"/table/v1/{self._profile}/{_format_coordinates(coordinates)}"
        params = {"annotations": "distance,duration"}
        payload = await self._get(path, params)

        if payload.get("code") != "Ok":
            raise RoutingProviderUnavailableError(f"OSRM returned no matrix: {payload.get('code')}")

        return MatrixResult(
            distances_meters=payload["distances"],
            durations_seconds=payload["durations"],
        )

    async def match_trace(self, points: list[TimedCoordinate]) -> TraceMatchResult:
        """Map-matches a continuous, timestamped GPS trace onto real OSM road-graph
        edges via OSRM's Match API (verified live against the public demo server -
        docs/TRAFFIC_ARCHITECTURE.md). Segment geometry is approximated as the whole
        matching's polyline, shared across every edge discovered within it - OSRM's
        match response does not reliably expose per-micro-edge geometry without
        `steps=true`'s much larger response, a documented simplification, not a
        fabrication (every edge's node IDs and speed are still exact, real, matched
        values). Never raises - an unmatchable trace or a provider failure both
        report `matched=False` so ingestion can degrade gracefully (CLAUDE.md #21, #40).
        """
        if len(points) < 2:
            return await self._match_single_point(points)

        coords_param = ";".join(f"{p.longitude},{p.latitude}" for p in points)
        timestamps_param = ";".join(str(int(p.timestamp.timestamp())) for p in points)
        path = f"/match/v1/{self._profile}/{coords_param}"
        params = {
            "timestamps": timestamps_param,
            "annotations": "true",
            "geometries": "geojson",
            "overview": "full",
        }

        try:
            payload = await self._get(path, params)
        except (RoutingProviderTimeoutError, RoutingProviderUnavailableError) as exc:
            logger.warning("OSRM map-matching unavailable: %s", exc)
            return TraceMatchResult(matched=False)

        if payload.get("code") != "Ok" or not payload.get("matchings"):
            return TraceMatchResult(matched=False)

        tracepoints = payload.get("tracepoints") or []
        legs_out: list[MatchedLeg] = []

        for matching_index, matching in enumerate(payload["matchings"]):
            geometry = matching.get("geometry")
            waypoint_to_point: dict[int, TimedCoordinate] = {}
            for original_index, tracepoint in enumerate(tracepoints):
                if tracepoint is None or tracepoint.get("matchings_index") != matching_index:
                    continue
                waypoint_to_point[tracepoint["waypoint_index"]] = points[original_index]

            for leg_index, leg in enumerate(matching.get("legs", [])):
                start_point = waypoint_to_point.get(leg_index)
                end_point = waypoint_to_point.get(leg_index + 1)
                if start_point is None or end_point is None:
                    continue  # can't compute an observed duration without both real timestamps

                annotation = leg.get("annotation") or {}
                nodes = annotation.get("nodes") or []
                speeds = annotation.get("speed") or []
                edges = [
                    MatchedEdge(
                        node_a=round(nodes[i]),
                        node_b=round(nodes[i + 1]),
                        geometry=geometry,
                        profile_speed_mps=speeds[i] if i < len(speeds) else None,
                    )
                    for i in range(len(nodes) - 1)
                ]
                if not edges:
                    continue

                observed_duration = (end_point.timestamp - start_point.timestamp).total_seconds()
                distance_meters = leg.get("distance", 0.0)
                observed_speed = distance_meters / observed_duration if observed_duration > 0 else None
                legs_out.append(
                    MatchedLeg(
                        edges=edges,
                        distance_meters=distance_meters,
                        observed_duration_seconds=observed_duration,
                        observed_speed_mps=observed_speed,
                        start_timestamp=start_point.timestamp,
                        end_timestamp=end_point.timestamp,
                    )
                )

        return TraceMatchResult(matched=True, legs=legs_out)

    async def _match_single_point(self, points: list[TimedCoordinate]) -> TraceMatchResult:
        if not points:
            return TraceMatchResult(matched=False)
        snap = await self.snap_point(Coordinate(latitude=points[0].latitude, longitude=points[0].longitude))
        # A single point has no second timestamp to measure elapsed time against, so
        # there is no observed speed to report - matching succeeds, but with no legs.
        return TraceMatchResult(matched=snap.matched, legs=[])

    async def snap_point(self, coordinate: Coordinate) -> SnapResult:
        path = f"/nearest/v1/{self._profile}/{coordinate.longitude},{coordinate.latitude}"
        params = {"number": 1}

        try:
            payload = await self._get(path, params)
        except (RoutingProviderTimeoutError, RoutingProviderUnavailableError) as exc:
            logger.warning("OSRM nearest-point snap unavailable: %s", exc)
            return SnapResult(matched=False)

        if payload.get("code") != "Ok" or not payload.get("waypoints"):
            return SnapResult(matched=False)

        waypoint = payload["waypoints"][0]
        nodes = waypoint.get("nodes")
        if not nodes or len(nodes) < 2:
            return SnapResult(matched=False)

        location = waypoint.get("location")
        snapped = Coordinate(latitude=location[1], longitude=location[0]) if location else None
        edge = MatchedEdge(node_a=round(nodes[0]), node_b=round(nodes[1]))
        return SnapResult(matched=True, edge=edge, snapped_coordinate=snapped)

    async def _get(self, path: str, params: dict) -> dict:
        url = f"{self._base_url}{path}"
        last_error: Exception | None = None
        timed_out = False

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                last_error = exc
                timed_out = True
                logger.warning(
                    "OSRM request timed out (attempt %d/%d): %s", attempt + 1, self._max_retries + 1, url
                )
            except httpx.HTTPStatusError as exc:
                # 4xx/5xx from OSRM itself is not transient in the way a timeout is; do not retry.
                raise RoutingProviderUnavailableError(
                    f"OSRM responded with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                timed_out = False
                logger.warning(
                    "OSRM request failed (attempt %d/%d): %s", attempt + 1, self._max_retries + 1, exc
                )

        if timed_out:
            raise RoutingProviderTimeoutError(
                f"OSRM request timed out after {self._max_retries + 1} attempts"
            ) from last_error
        raise RoutingProviderUnavailableError(
            f"OSRM request failed after {self._max_retries + 1} attempts"
        ) from last_error
