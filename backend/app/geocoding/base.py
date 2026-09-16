"""GeocodingProvider abstraction (CLAUDE.md #6.3 - provider-specific logic stays behind an interface)."""

from abc import ABC, abstractmethod

from app.schemas.geocoding import GeocodingSuggestion


class GeocodingProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[GeocodingSuggestion]:
        """Resolve free-text input to a ranked list of place suggestions."""
