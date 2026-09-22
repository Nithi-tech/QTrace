"""Structured service-layer errors (CLAUDE.md #20 - explicit, structured, never a bare Exception)."""


class FleetInfeasibleError(Exception):
    """Raised when a fleet routing request cannot be solved at all - e.g. total
    fleet capacity is less than total destination demand, so not a single
    feasible assignment exists (CLAUDE.md #10 - explain infeasibility rather
    than returning a broken solution).

    A request that is only *partially* infeasible (some, not all, destinations
    cannot be served) is not an error - it comes back as a normal
    FleetRouteResponse with is_feasible=False and unassigned_destination_indices
    listing what could not be placed.
    """

    code = "FLEET_INFEASIBLE"


class TrackingSessionNotFoundError(Exception):
    """Raised when a tracking code (driver-entered) or job id (admin-viewed)
    doesn't match any tracking session/planning job on record."""

    code = "TRACKING_SESSION_NOT_FOUND"
