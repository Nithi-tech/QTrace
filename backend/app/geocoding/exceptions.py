"""Structured geocoding errors (CLAUDE.md #20)."""


class GeocodingProviderError(Exception):
    code = "GEOCODING_PROVIDER_ERROR"


class GeocodingProviderTimeoutError(GeocodingProviderError):
    code = "GEOCODING_PROVIDER_TIMEOUT"


class GeocodingProviderUnavailableError(GeocodingProviderError):
    code = "GEOCODING_PROVIDER_UNAVAILABLE"


class GeocodingConfigurationError(GeocodingProviderError):
    """Raised when a required provider credential/config value is missing.

    This must never be papered over with a silent fallback to a different
    provider (CLAUDE.md #34, #36) - it is surfaced to the caller as a clear
    configuration problem.
    """

    code = "GEOCODING_PROVIDER_NOT_CONFIGURED"
