"""Nominatim (OpenStreetMap) GeocodingProvider - keyless, city-independent default.

Nominatim's usage policy (https://operations.osmfoundation.org/policies/nominatim/)
requires a descriptive User-Agent and caps unattended use at ~1 request/second; this
provider identifies itself and throttles to that limit rather than sending uncontrolled
bursts (CLAUDE.md #45).
"""

import asyncio
import logging
import time

import httpx

from app.geocoding.base import GeocodingProvider
from app.geocoding.exceptions import (
    GeocodingProviderTimeoutError,
    GeocodingProviderUnavailableError,
)
from app.schemas.geocoding import GeocodingSuggestion
from app.schemas.routing import Coordinate

logger = logging.getLogger(__name__)

_USER_AGENT = "QTrace/0.1 (Smart India Hackathon 2026 - Quantum-Inspired Route Intelligence)"
_MIN_REQUEST_INTERVAL_SECONDS = 1.0


class NominatimProvider(GeocodingProvider):
    def __init__(
        self,
        base_url: str = "https://nominatim.openstreetmap.org",
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._last_request_monotonic: float | None = None

    async def search(self, query: str, limit: int = 5) -> list[GeocodingSuggestion]:
        if not query or not query.strip():
            return []

        await self._throttle()
        url = f"{self._base_url}/search"
        params = {"q": query.strip(), "format": "jsonv2", "limit": limit}
        payload = await self._get(url, params)

        suggestions: list[GeocodingSuggestion] = []
        for result in payload:
            try:
                coordinate = Coordinate(latitude=float(result["lat"]), longitude=float(result["lon"]))
            except (KeyError, ValueError, TypeError):
                continue
            label = result.get("display_name")
            if not label:
                continue
            suggestions.append(GeocodingSuggestion(label=label, coordinate=coordinate))
        return suggestions

    async def _throttle(self) -> None:
        if self._last_request_monotonic is None:
            self._last_request_monotonic = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_request_monotonic
        remaining = _MIN_REQUEST_INTERVAL_SECONDS - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._last_request_monotonic = time.monotonic()

    async def _get(self, url: str, params: dict) -> list[dict]:
        headers = {"User-Agent": _USER_AGENT}
        last_error: Exception | None = None
        timed_out = False

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                last_error = exc
                timed_out = True
                logger.warning(
                    "Nominatim search request timed out (attempt %d/%d)", attempt + 1, self._max_retries + 1
                )
            except httpx.HTTPStatusError as exc:
                raise GeocodingProviderUnavailableError(
                    f"Nominatim search responded with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                timed_out = False
                logger.warning(
                    "Nominatim search request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries + 1,
                    exc,
                )

        if timed_out:
            raise GeocodingProviderTimeoutError(
                f"Nominatim search timed out after {self._max_retries + 1} attempts"
            ) from last_error
        raise GeocodingProviderUnavailableError(
            f"Nominatim search failed after {self._max_retries + 1} attempts"
        ) from last_error
