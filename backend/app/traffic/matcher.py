"""Spatial matching between a stop-pair's corridor and QTrace's own stored segments
(CLAUDE.md #6.3). Adapted from the same corridor-matching approach used for any
external traffic source (see docs/TRAFFIC_ARCHITECTURE.md "Traffic matrix"), just
against our own database instead of a third-party API - the geometric problem is
identical: OSRM stop-to-stop pairs don't line up with segment IDs 1:1, so matching is
done by real geometric intersection, not by name or ID guesswork.
"""

import math

from shapely.geometry import LineString, shape

from app.models.traffic_segment import TrafficSegment
from app.models.traffic_snapshot import TrafficSnapshot
from app.schemas.routing import Coordinate

_METERS_PER_DEGREE_LAT = 111_320.0


def _meters_to_degrees_lon(meters: float, at_latitude: float) -> float:
    return meters / (_METERS_PER_DEGREE_LAT * max(math.cos(math.radians(at_latitude)), 1e-6))


def build_bounding_box(stops: list[Coordinate], radius_meters: float) -> tuple[float, float, float, float]:
    """Returns (west, south, east, north) covering all stops, expanded by the corridor
    radius - scoped to just this request's stops, never an entire city."""
    lats = [s.latitude for s in stops]
    lons = [s.longitude for s in stops]
    mean_lat = sum(lats) / len(lats)
    delta_lat = radius_meters / _METERS_PER_DEGREE_LAT
    delta_lon = _meters_to_degrees_lon(radius_meters, mean_lat)
    return (
        min(lons) - delta_lon,
        min(lats) - delta_lat,
        max(lons) + delta_lon,
        max(lats) + delta_lat,
    )


def _corridor_polygon(origin: Coordinate, destination: Coordinate, radius_meters: float):
    line = LineString([(origin.longitude, origin.latitude), (destination.longitude, destination.latitude)])
    mean_lat = (origin.latitude + destination.latitude) / 2
    return line.buffer(_meters_to_degrees_lon(radius_meters, mean_lat))


def match_pair_to_snapshots(
    origin: Coordinate,
    destination: Coordinate,
    candidates: list[tuple[TrafficSnapshot, TrafficSegment]],
    radius_meters: float,
) -> list[tuple[TrafficSnapshot, TrafficSegment]]:
    """Segments (with their current snapshot) whose geometry intersects the
    straight-line corridor between two stops. Same documented straight-line-corridor
    simplification as the OSRM-route-per-pair problem this avoids (CLAUDE.md #20 -
    never call an external/heavy provider per matrix cell to build a matrix)."""
    corridor = _corridor_polygon(origin, destination, radius_meters)
    matched = []
    for snapshot, segment in candidates:
        if not segment.geometry:
            continue
        try:
            geom = shape(segment.geometry)
        except (ValueError, AttributeError):
            continue
        if geom.intersects(corridor):
            matched.append((snapshot, segment))
    return matched
