"""Reference-speed hierarchy (CLAUDE.md traffic-free-system master-prompt #13).

Priority, honestly scoped to what QTrace can actually verify:

1. OSRM's routing-profile speed for the matched edge (app/routing/map_matching.py) -
   real, per-edge, derived from OSM way tags OSRM's profile encodes (typically
   including maxspeed where tagged). NOT independently re-verified as a raw OSM
   maxspeed tag here - the public OSRM demo server does not expose a separate
   maxspeed annotation to check it against (see docs/TRAFFIC_ARCHITECTURE.md). Labeled
   "osrm_profile", not "osm_maxspeed", to avoid overclaiming precision.
2. QTrace's own historical median for this segment/day-of-week/time-bucket, once
   enough samples exist.
3. A single documented fallback constant. No road-class-specific tiers are
   implemented in this pass (CLAUDE.md traffic-free-system master-prompt #13 wants a
   road-class baseline, but OSRM's match/route API does not return reliable per-edge
   road-class in the responses this was verified against - see
   docs/TRAFFIC_ARCHITECTURE.md "Known limitations"). Never silently assumed to be a
   single "all roads" constant without this being the explicit, logged, last resort.
"""

from dataclasses import dataclass

OSRM_PROFILE = "osrm_profile"
HISTORICAL = "historical"
FALLBACK = "fallback"

# ~30 km/h - a documented, conservative urban-arterial guess, used only when neither
# OSRM's profile speed nor a historical baseline is available for a segment.
DEFAULT_FALLBACK_REFERENCE_SPEED_MPS = 8.33


@dataclass(frozen=True)
class ReferenceSpeed:
    speed_mps: float
    source: str


def resolve_reference_speed(
    profile_speed_mps: float | None,
    historical_median_mps: float | None,
    fallback_speed_mps: float = DEFAULT_FALLBACK_REFERENCE_SPEED_MPS,
) -> ReferenceSpeed:
    if profile_speed_mps is not None and profile_speed_mps > 0:
        return ReferenceSpeed(speed_mps=profile_speed_mps, source=OSRM_PROFILE)
    if historical_median_mps is not None and historical_median_mps > 0:
        return ReferenceSpeed(speed_mps=historical_median_mps, source=HISTORICAL)
    return ReferenceSpeed(speed_mps=fallback_speed_mps, source=FALLBACK)
