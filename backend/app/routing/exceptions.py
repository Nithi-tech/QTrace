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
