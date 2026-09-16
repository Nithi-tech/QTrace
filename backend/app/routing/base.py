"""RoutingProvider abstraction (CLAUDE.md #6.3).

External routing providers (OSRM, TomTom, ...) must be accessed only through
this interface so provider-specific logic never spreads through the app.
"""

from abc import ABC, abstractmethod

from app.schemas.routing import Coordinate, MatrixResult, RouteResult


class RoutingProvider(ABC):
    @abstractmethod
    async def geocode(self, address: str) -> Coordinate:
        """Resolve a free-text address to a coordinate."""

    @abstractmethod
    async def route(self, coordinates: list[Coordinate]) -> RouteResult:
        """Compute a single road-network route through an ordered list of coordinates."""

    @abstractmethod
    async def matrix(self, coordinates: list[Coordinate]) -> MatrixResult:
        """Compute the full pairwise distance/duration matrix for a set of coordinates."""
