"""Structured routing errors (CLAUDE.md #20 - explicit, structured, never a bare Exception)."""


class RoutingProviderError(Exception):
    """Base error for all routing provider failures."""

    code = "ROUTING_PROVIDER_ERROR"


class RoutingProviderTimeoutError(RoutingProviderError):
    code = "ROUTING_PROVIDER_TIMEOUT"


class RoutingProviderUnavailableError(RoutingProviderError):
    """Provider unreachable or returned a server-side failure."""

    code = "ROUTING_PROVIDER_UNAVAILABLE"


class InvalidRouteInputError(RoutingProviderError):
    """Raised for malformed coordinates or otherwise invalid routing input (CLAUDE.md #38)."""

    code = "INVALID_ROUTE_INPUT"


class TooManyStopsError(RoutingProviderError):
    """Raised when a request's stop count exceeds settings.max_route_stops (CLAUDE.md #27).

    OSRM's table service (and the public demo server in particular) has a practical
    limit on how many coordinates it will accept in one request; this is checked before
    calling the provider rather than left to fail there, so the caller gets an explicit
    reason instead of a generic provider error.
    """

    code = "LOCATION_LIMIT_EXCEEDED"
