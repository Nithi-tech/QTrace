"""Routing data contracts shared by every RoutingProvider implementation.

Coordinate ordering convention (CLAUDE.md #39): QTrace uses (latitude, longitude)
everywhere internally and at the API boundary. Providers that expect a different
order (e.g. OSRM uses longitude,latitude) must convert at their own boundary -
see app/routing/osrm_provider.py.
"""

from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteResult(BaseModel):
    distance_meters: float
    duration_seconds: float
    geometry: dict | None = None  # GeoJSON LineString, when the provider returns one


class MatrixResult(BaseModel):
    distances_meters: list[list[float]]
    durations_seconds: list[list[float]]
