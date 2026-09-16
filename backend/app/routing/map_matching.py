"""RoadMatchingProvider abstraction (CLAUDE.md #6.3).

Deliberately separate from RoutingProvider (app/routing/base.py) rather than adding
methods to that ABC: RoutingProvider is already implemented by test stubs across the
existing test suite (tests/services, tests/api) that only provide geocode()/route()/
matrix() - adding new @abstractmethods there would break every one of them for a
capability only the traffic-telemetry ingestion path needs. OSRMProvider implements
both interfaces (see app/routing/osrm_provider.py).
"""

from abc import ABC, abstractmethod

from app.schemas.map_matching import SnapResult, TimedCoordinate, TraceMatchResult
from app.schemas.routing import Coordinate


class RoadMatchingProvider(ABC):
    @abstractmethod
    async def match_trace(self, points: list[TimedCoordinate]) -> TraceMatchResult:
        """Map-match an ordered, timestamped GPS trace (one continuous session) onto
        real road-graph edges. Must never raise for a trace that simply can't be
        matched - return matched=False instead (CLAUDE.md #21, #40)."""

    @abstractmethod
    async def snap_point(self, coordinate: Coordinate) -> SnapResult:
        """Snap a single GPS point (no trace context) to its nearest road edge."""
