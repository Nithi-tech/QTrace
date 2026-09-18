"""Traffic area sampling for the map visualization layer (docs/TRAFFIC_ARCHITECTURE.md).

TomTom's Flow Segment Data API is point-based, not area-based
(app/traffic/tomtom_provider.py) - there is no "every segment in this bbox" endpoint in
the plain-JSON API. To render a Google-Maps-like colored-roads layer over a visible map
area, this samples a bounded grid of points across the requested bbox and uses each
response's own real, TomTom-returned segment geometry - never a fabricated shape, never
a random color. The grid is capped (settings.traffic_area_max_points) so a large
viewport never triggers an unbounded number of TomTom calls; sampled points still go
through the shared TomTom flow cache (app/traffic/cache.py), so panning back over an
already-sampled area costs no extra calls within the TTL window.
"""

import asyncio
from dataclasses import dataclass

from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficFlowSegment
from app.traffic.cache import TTLCache
from app.traffic.exceptions import TrafficProviderError
from app.traffic.tomtom_provider import TomTomTrafficProvider


@dataclass
class SampledSegment:
    geometry: dict
    current_speed_mps: float
    free_flow_speed_mps: float
    confidence: float | None


# A long arterial/highway segment can carry 500-1000+ coordinate points from TomTom -
# far more detail than a color-only line layer needs (CLAUDE.md traffic master-prompt
# #32 - avoid excessive GeoJSON size). Decimating keeps the shape recognizable on a map
# while bounding response size; this never changes speed/congestion values, only how
# finely the line is drawn.
_MAX_GEOMETRY_POINTS = 80


def _decimate(coordinates: list, max_points: int) -> list:
    if len(coordinates) <= max_points:
        return coordinates
    step = (len(coordinates) - 1) / (max_points - 1)
    indices = {round(i * step) for i in range(max_points)}
    return [c for i, c in enumerate(coordinates) if i in indices]


def build_sample_grid(
    west: float, south: float, east: float, north: float, max_points: int
) -> list[Coordinate]:
    """An evenly spaced lat/lon grid inside the bbox, capped at max_points total
    samples - never one call per pixel, never unbounded for a huge viewport."""
    if max_points < 1 or east <= west or north <= south:
        return []
    side = max(1, int(max_points**0.5))
    lat_step = (north - south) / side
    lon_step = (east - west) / side
    points: list[Coordinate] = []
    for i in range(side):
        for j in range(side):
            if len(points) >= max_points:
                return points
            points.append(
                Coordinate(latitude=south + lat_step * (i + 0.5), longitude=west + lon_step * (j + 0.5))
            )
    return points


def _geometry_key(geometry: dict) -> tuple | None:
    """Two grid points landing on the same road commonly return (near-)identical
    geometry from TomTom - deduped by rounded endpoints so the map doesn't draw the
    same segment twice."""
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    first, last = coordinates[0], coordinates[-1]
    return (tuple(round(c, 4) for c in first), tuple(round(c, 4) for c in last))


class TrafficAreaSampler:
    def __init__(
        self, tomtom_provider: TomTomTrafficProvider | None, cache: TTLCache, max_points: int
    ) -> None:
        self._tomtom_provider = tomtom_provider
        self._cache = cache
        self._max_points = max_points

    async def sample(self, west: float, south: float, east: float, north: float) -> list[SampledSegment]:
        if self._tomtom_provider is None:
            return []
        points = build_sample_grid(west, south, east, north, self._max_points)
        results = await asyncio.gather(*(self._get_flow_cached(p) for p in points))

        seen: set[tuple] = set()
        segments: list[SampledSegment] = []
        for flow in results:
            if flow is None or flow.geometry is None:
                continue
            key = _geometry_key(flow.geometry)
            if key is None or key in seen:
                continue
            seen.add(key)
            decimated_geometry = {
                **flow.geometry,
                "coordinates": _decimate(flow.geometry["coordinates"], _MAX_GEOMETRY_POINTS),
            }
            segments.append(
                SampledSegment(
                    geometry=decimated_geometry,
                    current_speed_mps=flow.current_speed_mps,
                    free_flow_speed_mps=flow.free_flow_speed_mps,
                    confidence=flow.confidence,
                )
            )
        return segments

    async def _get_flow_cached(self, coordinate: Coordinate) -> TrafficFlowSegment | None:
        assert self._tomtom_provider is not None
        cache_key = (round(coordinate.latitude, 4), round(coordinate.longitude, 4))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            flow = await self._tomtom_provider.get_flow_at_point(coordinate)
        except TrafficProviderError:
            flow = None
        self._cache.set(cache_key, flow)
        return flow
