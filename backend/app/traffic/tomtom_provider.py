"""TomTom Traffic API-backed provider (CLAUDE.md #11 - approved production provider).

Both endpoints and their response shapes were verified live during development
(docs/TRAFFIC_ARCHITECTURE.md) - this is not written from documentation alone.

Deliberately point-based for flow, not bbox-based: TomTom's Traffic Flow Segment Data
API (v4) takes a single `point`, not an area - there is no "give me every segment in
this bounding box" flow endpoint in the plain JSON API (only a protobuf vector-tile
API, far more complex to parse for no benefit here). app/traffic/traffic_service.py
therefore queries flow once per unique stop coordinate (not per stop-pair, and never
inside QPSO's loop), which is also more precise than a bbox sweep would be - it asks
for a segment exactly where a stop is, not memory or an bounding rectangle.

Incidents genuinely are bbox-based in TomTom's API and are used that way here.

Speed unit: TomTom's flow endpoint returns km/h by default (the `unit` query parameter
defaults to KMPH) - converted to m/s once, here, at the provider boundary (CLAUDE.md
#39 - never mix units silently).
"""

import logging

import httpx

from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficFlowSegment, TrafficIncident
from app.traffic.exceptions import (
    TrafficConfigurationError,
    TrafficProviderTimeoutError,
    TrafficProviderUnavailableError,
)

logger = logging.getLogger(__name__)

_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"
_KMPH_TO_MPS = 1.0 / 3.6

# TomTom's incident `iconCategory` for a fully closed road (verified live).
_ROAD_CLOSED_ICON_CATEGORY = 8
# TomTom's `magnitudeOfDelay` is natively 0(unknown)-4(undefined/closure). Rescaled onto
# the same 0-10 severity scale used elsewhere in this codebase - a documented QTrace
# mapping, not a TomTom-native number.
_MAGNITUDE_TO_SEVERITY = 2.5


def _bbox_param(west: float, south: float, east: float, north: float) -> str:
    return f"{west},{south},{east},{north}"


class TomTomTrafficProvider:
    def __init__(self, api_key: str | None, timeout_seconds: float = 5.0, max_retries: int = 2) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def get_flow_at_point(self, coordinate: Coordinate) -> TrafficFlowSegment | None:
        payload = await self._get(_FLOW_URL, {"point": f"{coordinate.latitude},{coordinate.longitude}"})

        flow = payload.get("flowSegmentData")
        if not flow:
            return None
        current_speed = flow.get("currentSpeed")
        free_flow_speed = flow.get("freeFlowSpeed")
        if current_speed is None or free_flow_speed is None:
            return None

        coordinates = (flow.get("coordinates") or {}).get("coordinate") or []
        geometry = (
            {"type": "LineString", "coordinates": [[c["longitude"], c["latitude"]] for c in coordinates]}
            if coordinates
            else None
        )

        return TrafficFlowSegment(
            geometry=geometry,
            current_speed_mps=current_speed * _KMPH_TO_MPS,
            free_flow_speed_mps=free_flow_speed * _KMPH_TO_MPS,
            confidence=flow.get("confidence"),
        )

    async def get_incidents(
        self, west: float, south: float, east: float, north: float
    ) -> list[TrafficIncident]:
        payload = await self._get(
            _INCIDENTS_URL,
            {
                "bbox": _bbox_param(west, south, east, north),
                "fields": "{incidents{type,geometry{type,coordinates},"
                "properties{iconCategory,magnitudeOfDelay,events{description}}}}",
            },
        )

        incidents: list[TrafficIncident] = []
        for feature in payload.get("incidents", []):
            properties = feature.get("properties") or {}
            icon_category = properties.get("iconCategory")
            magnitude = properties.get("magnitudeOfDelay")
            events = properties.get("events") or []
            road_closed = icon_category == _ROAD_CLOSED_ICON_CATEGORY or any(
                str(e.get("description", "")).strip().lower() == "closed" for e in events
            )
            severity = magnitude * _MAGNITUDE_TO_SEVERITY if magnitude is not None else None
            incidents.append(
                TrafficIncident(
                    geometry=feature.get("geometry"),
                    incident_type=events[0]["description"] if events else "UNKNOWN",
                    delay_seconds=None,  # not requested from TomTom in this pass - never fabricated
                    severity=severity,
                    road_closed=road_closed,
                )
            )
        return incidents

    async def _get(self, url: str, params: dict) -> dict:
        if not self._api_key:
            raise TrafficConfigurationError(
                "TOMTOM_API_KEY is not configured; set it in the backend environment (see .env.example)."
            )

        request_params = {**params, "key": self._api_key}
        last_error: Exception | None = None
        timed_out = False

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.get(url, params=request_params)
                if response.status_code in (401, 403):
                    # Never retry an auth failure indefinitely (CLAUDE.md traffic
                    # master-prompt #10.10) - it will not resolve itself on retry.
                    raise TrafficProviderUnavailableError(
                        f"TomTom traffic authentication failed (HTTP {response.status_code})"
                    )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                last_error = exc
                timed_out = True
                logger.warning(
                    "TomTom traffic request timed out (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries + 1,
                    url,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    logger.warning("TomTom traffic rate limit hit (429): %s", url)
                raise TrafficProviderUnavailableError(
                    f"TomTom traffic responded with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                timed_out = False
                logger.warning(
                    "TomTom traffic request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries + 1,
                    exc,
                )

        if timed_out:
            raise TrafficProviderTimeoutError(
                f"TomTom traffic request timed out after {self._max_retries + 1} attempts"
            ) from last_error
        raise TrafficProviderUnavailableError(
            f"TomTom traffic request failed after {self._max_retries + 1} attempts"
        ) from last_error
