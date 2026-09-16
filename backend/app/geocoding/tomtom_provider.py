"""TomTom Search API-backed GeocodingProvider (CLAUDE.md #11 - approved production provider).

Requires TOMTOM_API_KEY to be configured. The key is read from settings/env
only - never hard-coded (CLAUDE.md #18, #78) - and a missing key raises a
clear configuration error rather than silently degrading (CLAUDE.md #34).
"""

import logging
from urllib.parse import quote

import httpx

from app.geocoding.base import GeocodingProvider
from app.geocoding.exceptions import (
    GeocodingConfigurationError,
    GeocodingProviderTimeoutError,
    GeocodingProviderUnavailableError,
)
from app.schemas.geocoding import GeocodingSuggestion
from app.schemas.routing import Coordinate

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.tomtom.com/search/2/search/{query}.json"


class TomTomGeocodingProvider(GeocodingProvider):
    def __init__(
        self,
        api_key: str | None,
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def search(self, query: str, limit: int = 5) -> list[GeocodingSuggestion]:
        if not self._api_key:
            raise GeocodingConfigurationError(
                "TOMTOM_API_KEY is not configured; set it in the backend environment (see .env.example)."
            )
        if not query or not query.strip():
            return []

        url = _SEARCH_URL.format(query=quote(query.strip()))
        params = {"key": self._api_key, "limit": limit}
        payload = await self._get(url, params)

        suggestions: list[GeocodingSuggestion] = []
        for result in payload.get("results", []):
            position = result.get("position")
            address = result.get("address", {})
            if not position or "lat" not in position or "lon" not in position:
                continue
            label = address.get("freeformAddress") or result.get("poi", {}).get("name")
            if not label:
                continue
            suggestions.append(
                GeocodingSuggestion(
                    label=label,
                    coordinate=Coordinate(latitude=position["lat"], longitude=position["lon"]),
                )
            )
        return suggestions

    async def _get(self, url: str, params: dict) -> dict:
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
                    "TomTom search request timed out (attempt %d/%d)", attempt + 1, self._max_retries + 1
                )
            except httpx.HTTPStatusError as exc:
                raise GeocodingProviderUnavailableError(
                    f"TomTom search responded with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                timed_out = False
                logger.warning(
                    "TomTom search request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries + 1,
                    exc,
                )

        if timed_out:
            raise GeocodingProviderTimeoutError(
                f"TomTom search timed out after {self._max_retries + 1} attempts"
            ) from last_error
        raise GeocodingProviderUnavailableError(
            f"TomTom search failed after {self._max_retries + 1} attempts"
        ) from last_error
