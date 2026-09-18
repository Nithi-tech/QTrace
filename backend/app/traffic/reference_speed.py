"""Reference-speed hierarchy (CLAUDE.md traffic master-prompt #13).

1. A reliable provider reference speed - TomTom's own `freeFlowSpeed` for the matched
   segment, verified live against the real API (docs/TRAFFIC_ARCHITECTURE.md). This is
   a genuine provider-supplied free-flow value, not a guess.
2. QTrace's own historical median for this segment/day-of-week/time-bucket, once
   enough samples exist.
3. A single documented fallback constant. No road-class-specific tier is implemented
   (OSRM's match/route responses used for crowd-telemetry map-matching don't reliably
   expose per-edge road class - see docs/TRAFFIC_ARCHITECTURE.md "Known limitations").
"""

from dataclasses import dataclass

PROVIDER = "PROVIDER"
HISTORICAL = "HISTORICAL"
FALLBACK = "FALLBACK"

# ~30 km/h - a documented, conservative urban-arterial guess, used only when neither a
# provider reference speed nor a historical baseline is available.
DEFAULT_FALLBACK_REFERENCE_SPEED_MPS = 8.33


@dataclass(frozen=True)
class ReferenceSpeed:
    speed_mps: float
    source: str


def resolve_reference_speed(
    provider_free_flow_speed_mps: float | None,
    historical_median_mps: float | None,
    fallback_speed_mps: float = DEFAULT_FALLBACK_REFERENCE_SPEED_MPS,
) -> ReferenceSpeed:
    if provider_free_flow_speed_mps is not None and provider_free_flow_speed_mps > 0:
        return ReferenceSpeed(speed_mps=provider_free_flow_speed_mps, source=PROVIDER)
    if historical_median_mps is not None and historical_median_mps > 0:
        return ReferenceSpeed(speed_mps=historical_median_mps, source=HISTORICAL)
    return ReferenceSpeed(speed_mps=fallback_speed_mps, source=FALLBACK)
