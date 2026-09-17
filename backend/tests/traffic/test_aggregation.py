from app.traffic.aggregation import (
    EXPIRED,
    LIVE,
    RECENT,
    STALE,
    classify_freshness,
    compute_confidence,
    congestion_score,
    median_speed_mps,
)


def test_median_speed_is_robust_to_a_single_outlier():
    assert median_speed_mps([10.0, 11.0, 12.0, 100.0]) == 11.5


def test_congestion_score_zero_when_at_reference_speed():
    assert congestion_score(current_speed_mps=15.0, reference_speed_mps=15.0) == 0.0


def test_congestion_score_one_when_stopped():
    assert congestion_score(current_speed_mps=0.0, reference_speed_mps=15.0) == 1.0


def test_congestion_score_handles_zero_reference_as_free_flowing():
    assert congestion_score(current_speed_mps=5.0, reference_speed_mps=0.0) == 0.0


def test_congestion_score_clamped_when_faster_than_reference():
    assert congestion_score(current_speed_mps=25.0, reference_speed_mps=15.0) == 0.0


def test_classify_freshness_thresholds():
    assert classify_freshness(0, live_ttl_seconds=120, recent_ttl_seconds=300, expired_seconds=900) == LIVE
    assert classify_freshness(120, live_ttl_seconds=120, recent_ttl_seconds=300, expired_seconds=900) == LIVE
    assert (
        classify_freshness(121, live_ttl_seconds=120, recent_ttl_seconds=300, expired_seconds=900) == RECENT
    )
    assert classify_freshness(301, live_ttl_seconds=120, recent_ttl_seconds=300, expired_seconds=900) == STALE
    assert (
        classify_freshness(901, live_ttl_seconds=120, recent_ttl_seconds=300, expired_seconds=900) == EXPIRED
    )


def test_confidence_increases_with_observation_count_up_to_saturation():
    low = compute_confidence(observation_count=1, min_observations=3, freshness_status=LIVE)
    high = compute_confidence(observation_count=9, min_observations=3, freshness_status=LIVE)
    saturated = compute_confidence(observation_count=90, min_observations=3, freshness_status=LIVE)
    assert low < high == saturated == 1.0


def test_confidence_is_reduced_by_staleness_even_with_many_observations():
    live_confidence = compute_confidence(observation_count=100, min_observations=3, freshness_status=LIVE)
    stale_confidence = compute_confidence(observation_count=100, min_observations=3, freshness_status=STALE)
    assert stale_confidence < live_confidence


def test_confidence_is_zero_when_expired_regardless_of_observation_count():
    assert compute_confidence(observation_count=1000, min_observations=3, freshness_status=EXPIRED) == 0.0
