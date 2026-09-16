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
from app.schemas.routing import Coordinate, MatrixResult, RouteResult

logger = logging.getLogger(__name__)


def _format_coordinates(coordinates: list[Coordinate]) -> str:
    return ";".join(f"{c.longitude},{c.latitude}" for c in coordinates)


class OSRMProvider(RoutingProvider):
    def __init__(self, base_url: str, timeout_seconds: float = 5.0, max_retries: int = 2) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def geocode(self, address: str) -> Coordinate:
        # OSRM is a routing engine, not a geocoder - it has no address-lookup endpoint.
        # Geocoding must go through a separate, explicitly configured provider.
        raise NotImplementedError("OSRMProvider does not support geocoding; configure a geocoding provider.")

    async def route(self, coordinates: list[Coordinate]) -> RouteResult:
        if len(coordinates) < 2:
            raise InvalidRouteInputError("route() requires at least two coordinates.")

        path = f"/route/v1/driving/{_format_coordinates(coordinates)}"
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

        path = f"/table/v1/driving/{_format_coordinates(coordinates)}"
        params = {"annotations": "distance,duration"}
        payload = await self._get(path, params)

        if payload.get("code") != "Ok":
            raise RoutingProviderUnavailableError(f"OSRM returned no matrix: {payload.get('code')}")

        return MatrixResult(
            distances_meters=payload["distances"],
            durations_seconds=payload["durations"],
        )

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
