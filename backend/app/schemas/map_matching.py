"""Map-matching data contracts (CLAUDE.md #6.3). Separate from app/schemas/routing.py
because these are about associating GPS points with OSM road-graph edges, a distinct
concern from plain point-to-point routing - see app/routing/map_matching.py.
"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.routing import Coordinate


class TimedCoordinate(BaseModel):
    latitude: float
    longitude: float
    timestamp: datetime


class MatchedEdge(BaseModel):
    """One real OSM-graph edge (a pair of consecutive nodes) that a GPS trace crossed."""

    node_a: int
    node_b: int
    geometry: dict | None = None  # GeoJSON LineString, when OSRM returned one
    profile_speed_mps: float | None = None  # OSRM's routing-profile speed for this edge

    @property
    def segment_key(self) -> str:
        """Order-independent key so both travel directions share one segment
        (CLAUDE.md traffic-free-system master-prompt #21 - documented simplification)."""
        return f"{min(self.node_a, self.node_b)}:{max(self.node_a, self.node_b)}"


class MatchedLeg(BaseModel):
    """The road distance/edges between two consecutive uploaded GPS points.

    observed_speed_mps here is derived from OSRM's matched distance / the phone's own
    elapsed time - a cross-check value. app/traffic/service.py uses the two bounding
    observations' own reported speed_mps as the primary signal instead (a phone's GPS
    speed reading is generally more accurate than back-computing from two position
    fixes), correlated via start_timestamp/end_timestamp.
    """

    edges: list[MatchedEdge]
    distance_meters: float
    observed_duration_seconds: float
    observed_speed_mps: float | None  # None when duration_seconds <= 0 (clock skew/duplicate timestamps)
    start_timestamp: datetime
    end_timestamp: datetime


class TraceMatchResult(BaseModel):
    matched: bool
    legs: list[MatchedLeg] = []


class SnapResult(BaseModel):
    matched: bool
    edge: MatchedEdge | None = None
    snapped_coordinate: Coordinate | None = None
