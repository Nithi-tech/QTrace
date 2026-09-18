"""Structured traffic errors (CLAUDE.md #20). Mirrors app/routing/exceptions.py and
app/geocoding/exceptions.py so all provider families fail the same way."""


class TrafficProviderError(Exception):
    code = "TRAFFIC_PROVIDER_ERROR"


class TrafficProviderTimeoutError(TrafficProviderError):
    code = "TRAFFIC_PROVIDER_TIMEOUT"


class TrafficProviderUnavailableError(TrafficProviderError):
    code = "TRAFFIC_PROVIDER_UNAVAILABLE"


class TrafficConfigurationError(TrafficProviderError):
    """Raised when required provider config (e.g. TOMTOM_API_KEY) is missing.
    TrafficService catches this and falls back to the next tier rather than failing
    the whole optimization request (CLAUDE.md #21, #34)."""

    code = "TRAFFIC_PROVIDER_NOT_CONFIGURED"
