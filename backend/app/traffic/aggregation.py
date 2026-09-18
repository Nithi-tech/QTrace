"""Pure aggregation/scoring functions (CLAUDE.md #52 - hand-checkable, no I/O).

None of this runs inside the QPSO fitness loop (CLAUDE.md traffic master-prompt #26) -
it is computed once, ahead of time, when a snapshot is built (app/traffic/traffic_service.py)
or when the optimizer builds its traffic matrix (app/traffic/matrix_service.py).
"""

import statistics

LIVE = "LIVE"
RECENT = "RECENT"
STALE = "STALE"
EXPIRED = "EXPIRED"
HISTORICAL = "HISTORICAL"
UNAVAILABLE = "UNAVAILABLE"


def median_speed_mps(speeds: list[float]) -> float:
    """Median, not mean - robust to a single outlier observation (e.g. one fast/slow
    vehicle) skewing the result (CLAUDE.md traffic master-prompt #18)."""
    return statistics.median(speeds)


def speed_ratio(current_speed_mps: float, reference_speed_mps: float) -> float:
    """clamp(current/reference, 0, 1). reference<=0 is treated as free-flowing (1.0)
    rather than dividing by zero - it indicates no usable reference, not congestion."""
    if reference_speed_mps <= 0:
        return 1.0
    return max(0.0, min(1.0, current_speed_mps / reference_speed_mps))


def congestion_score(current_speed_mps: float, reference_speed_mps: float) -> float:
    """1 - speed_ratio: 0 = at/above reference (free-flowing), 1 = stopped."""
    return 1.0 - speed_ratio(current_speed_mps, reference_speed_mps)


def classify_freshness(
    age_seconds: float, live_ttl_seconds: float, recent_ttl_seconds: float, expired_seconds: float
) -> str:
    """Never labels stale/historical data as LIVE (CLAUDE.md traffic master-prompt
    #15). Callers with zero observations should use UNAVAILABLE directly rather than
    calling this - there is no "age" for data that doesn't exist."""
    if age_seconds <= live_ttl_seconds:
        return LIVE
    if age_seconds <= recent_ttl_seconds:
        return RECENT
    if age_seconds <= expired_seconds:
        return STALE
    return EXPIRED


# Confidence contribution per freshness status (CLAUDE.md traffic master-prompt #16 -
# confidence must fall with data age).
_FRESHNESS_CONFIDENCE_FACTOR = {
    LIVE: 1.0,
    RECENT: 0.7,
    STALE: 0.3,
    EXPIRED: 0.0,
    HISTORICAL: 0.5,
    UNAVAILABLE: 0.0,
}


def compute_crowd_confidence(observation_count: int, min_observations: int, freshness_status: str) -> float:
    """Confidence for a QTrace-crowd-sourced snapshot - considers both how many
    independent observations back it and how fresh they are (CLAUDE.md traffic
    master-prompt #16). Multiplied, not averaged: either signal being bad should pull
    confidence down, not get diluted by the other being good.

    count_factor saturates at 1.0 once observation_count reaches 3x min_observations -
    a documented, simple choice (not itself separately configurable) for this first
    version (CLAUDE.md #46).
    """
    if min_observations <= 0:
        count_factor = 1.0
    else:
        count_factor = max(0.0, min(1.0, observation_count / (min_observations * 3)))
    freshness_factor = _FRESHNESS_CONFIDENCE_FACTOR.get(freshness_status, 0.0)
    return count_factor * freshness_factor


# Presentation-only thresholds (CLAUDE.md traffic master-prompt #32 - this is QTrace's
# own classification, not any provider's).
_LEVEL_THRESHOLDS = ((0.25, "LOW"), (0.5, "MODERATE"), (0.75, "HEAVY"))
_SEVERE_LEVEL = "HEAVY"


def classify_traffic_level(score: float) -> str:
    for threshold, label in _LEVEL_THRESHOLDS:
        if score < threshold:
            return label
    return _SEVERE_LEVEL


def classify_map_traffic_level(
    speed_ratio_value: float,
    green_threshold: float,
    yellow_threshold: float,
    orange_threshold: float,
    red_threshold: float,
) -> str:
    """QTrace's own 5-level scale for the Google-Maps-style map traffic layer
    (docs/TRAFFIC_ARCHITECTURE.md) - a different, finer scale than
    classify_traffic_level above (which summarizes one whole route, not one road
    segment). Thresholds are speed_ratio (current/free-flow), not congestion_score,
    matching how the map feature was specified; configurable, not hard-coded
    (CLAUDE.md #35), and explicitly QTrace's own choice, not any provider's or
    Google's (CLAUDE.md traffic master-prompt #8)."""
    if speed_ratio_value >= green_threshold:
        return "FREE_FLOW"
    if speed_ratio_value >= yellow_threshold:
        return "MODERATE"
    if speed_ratio_value >= orange_threshold:
        return "HEAVY"
    if speed_ratio_value >= red_threshold:
        return "VERY_HEAVY"
    return "SEVERE"
