from app.traffic.aggregation import (
    EXPIRED,
    LIVE,
    RECENT,
    STALE,
    classify_freshness,
    classify_map_traffic_level,
    classify_traffic_level,
    compute_crowd_confidence,
    congestion_score,
    median_speed_mps,
    speed_ratio,
)

_MAP_THRESHOLDS = {
    "green_threshold": 0.80,
    "yellow_threshold": 0.60,
    "orange_threshold": 0.40,
    "red_threshold": 0.20,
}


def test_median_speed_is_robust_to_a_single_outlier():
    assert median_speed_mps([10.0, 11.0, 12.0, 100.0]) == 11.5


def test_speed_ratio_clamped_to_one_when_faster_than_reference():
    assert speed_ratio(25.0, 15.0) == 1.0


def test_speed_ratio_handles_zero_reference_as_free_flowing():
    assert speed_ratio(5.0, 0.0) == 1.0


def test_congestion_score_zero_when_at_reference_speed():
    assert congestion_score(15.0, 15.0) == 0.0


def test_congestion_score_one_when_stopped():
    assert congestion_score(0.0, 15.0) == 1.0


def test_classify_freshness_thresholds():
    assert classify_freshness(0, 120, 300, 900) == LIVE
    assert classify_freshness(120, 120, 300, 900) == LIVE
    assert classify_freshness(121, 120, 300, 900) == RECENT
    assert classify_freshness(301, 120, 300, 900) == STALE
    assert classify_freshness(901, 120, 300, 900) == EXPIRED


def test_confidence_increases_with_observation_count_up_to_saturation():
    low = compute_crowd_confidence(1, 3, LIVE)
    high = compute_crowd_confidence(9, 3, LIVE)
    saturated = compute_crowd_confidence(90, 3, LIVE)
    assert low < high == saturated == 1.0


def test_confidence_is_reduced_by_staleness_even_with_many_observations():
    assert compute_crowd_confidence(100, 3, STALE) < compute_crowd_confidence(100, 3, LIVE)


def test_confidence_is_zero_when_expired_regardless_of_observation_count():
    assert compute_crowd_confidence(1000, 3, EXPIRED) == 0.0


def test_classify_traffic_level_thresholds():
    assert classify_traffic_level(0.0) == "LOW"
    assert classify_traffic_level(0.3) == "MODERATE"
    assert classify_traffic_level(0.6) == "HEAVY"
    assert classify_traffic_level(1.0) == "HEAVY"


def test_classify_map_traffic_level_thresholds():
    assert classify_map_traffic_level(0.90, **_MAP_THRESHOLDS) == "FREE_FLOW"
    assert classify_map_traffic_level(0.75, **_MAP_THRESHOLDS) == "MODERATE"
    assert classify_map_traffic_level(0.50, **_MAP_THRESHOLDS) == "HEAVY"
    assert classify_map_traffic_level(0.30, **_MAP_THRESHOLDS) == "VERY_HEAVY"
    assert classify_map_traffic_level(0.10, **_MAP_THRESHOLDS) == "SEVERE"


def test_classify_map_traffic_level_boundaries_are_inclusive_on_the_higher_side():
    assert classify_map_traffic_level(0.80, **_MAP_THRESHOLDS) == "FREE_FLOW"
    assert classify_map_traffic_level(0.60, **_MAP_THRESHOLDS) == "MODERATE"
    assert classify_map_traffic_level(0.40, **_MAP_THRESHOLDS) == "HEAVY"
    assert classify_map_traffic_level(0.20, **_MAP_THRESHOLDS) == "VERY_HEAVY"
