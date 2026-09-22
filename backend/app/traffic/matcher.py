"""Geometric helpers for matching TomTom incidents to a stop-pair's corridor
(CLAUDE.md #6.3). Flow is resolved point-by-point (app/traffic/traffic_service.py) and
needs no geometry matching; incidents are the one piece that's genuinely area-based
(TomTom's Incidents API takes a bbox), so this is the one place Shapely is used.
"""

import math

from shapely.geometry import LineString, shape

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


def incidents_on_corridor(
    origin: Coordinate, destination: Coordinate, incidents: list, radius_meters: float
) -> list:
    """Incidents (app.schemas.traffic.TrafficIncident) whose geometry intersects the
    straight-line corridor between two stops - a documented simplification (the real
    route may not be a straight line), same tradeoff as avoiding an OSRM call per pair."""
    corridor = _corridor_polygon(origin, destination, radius_meters)
    matched = []
    for incident in incidents:
        if not incident.geometry:
            continue
        try:
            geom = shape(incident.geometry)
        except (ValueError, AttributeError):
            continue
        if geom.intersects(corridor):
            matched.append(incident)
    return matched
