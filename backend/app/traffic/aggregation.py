"""Pure aggregation/scoring functions (CLAUDE.md #52 - hand-checkable, no I/O).

None of this runs inside the QPSO fitness loop (CLAUDE.md traffic-free-system
master-prompt #22) - it is computed once, ahead of time, when a segment's snapshot is
updated (app/traffic/service.py) or when the optimizer builds its traffic matrix
(app/traffic/matrix_service.py).
"""

import statistics

LIVE = "LIVE"
RECENT = "RECENT"
STALE = "STALE"
EXPIRED = "EXPIRED"
UNKNOWN = "UNKNOWN"


def median_speed_mps(speeds: list[float]) -> float:
    """Median, not mean (CLAUDE.md traffic-free-system master-prompt #11) - robust to a
    single outlier observation (e.g. one fast/slow vehicle) skewing the result."""
    return statistics.median(speeds)


def congestion_score(current_speed_mps: float, reference_speed_mps: float) -> float:
    """1 - clamp(current/reference, 0, 1): 0 = at/above reference (free-flowing),
    1 = stopped. reference_speed_mps<=0 is treated as free-flowing (score 0) rather
    than dividing by zero - it indicates no usable reference, not congestion."""
    if reference_speed_mps <= 0:
        return 0.0
    return 1.0 - max(0.0, min(1.0, current_speed_mps / reference_speed_mps))


def classify_freshness(
    age_seconds: float, live_ttl_seconds: float, recent_ttl_seconds: float, expired_seconds: float
) -> str:
    """CLAUDE.md traffic-free-system master-prompt #17 - never label stale/historical
    data as LIVE. Callers with zero observations should use UNKNOWN directly rather
    than calling this (there is no "age" for data that doesn't exist)."""
    if age_seconds <= live_ttl_seconds:
        return LIVE
    if age_seconds <= recent_ttl_seconds:
        return RECENT
    if age_seconds <= expired_seconds:
        return STALE
    return EXPIRED


# Confidence contribution per freshness status (CLAUDE.md traffic-free-system
# master-prompt #16 - confidence must decrease with data age).
_FRESHNESS_CONFIDENCE_FACTOR = {LIVE: 1.0, RECENT: 0.7, STALE: 0.3, EXPIRED: 0.0, UNKNOWN: 0.0}


def compute_confidence(observation_count: int, min_observations: int, freshness_status: str) -> float:
    """Combines two independent signals - CLAUDE.md #16 requires confidence to fall
    with both few observations AND stale data, so this multiplies rather than averages
    them (either one being bad should pull confidence down, not get diluted by the
    other being good).

    count_factor saturates at 1.0 once observation_count reaches 3x min_observations -
    a documented, configurable-in-spirit choice (min_observations itself is the
    configurable TRAFFIC_MIN_OBSERVATIONS setting; the 3x saturation multiple is not
    separately configurable, kept simple for this first version, CLAUDE.md #46).
    """
    if min_observations <= 0:
        count_factor = 1.0
    else:
        count_factor = max(0.0, min(1.0, observation_count / (min_observations * 3)))
    freshness_factor = _FRESHNESS_CONFIDENCE_FACTOR.get(freshness_status, 0.0)
    return count_factor * freshness_factor


# Presentation-only thresholds (CLAUDE.md traffic-free-system master-prompt #28 - this
# is QTrace's own classification, not any provider's).
_LEVEL_THRESHOLDS = ((0.25, "LOW"), (0.5, "MODERATE"), (0.75, "HIGH"))
_SEVERE_LEVEL = "SEVERE"


def classify_traffic_level(score: float) -> str:
    for threshold, label in _LEVEL_THRESHOLDS:
        if score < threshold:
            return label
    return _SEVERE_LEVEL
