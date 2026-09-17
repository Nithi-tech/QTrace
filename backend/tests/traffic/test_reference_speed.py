from app.traffic.reference_speed import FALLBACK, HISTORICAL, OSRM_PROFILE, resolve_reference_speed


def test_prefers_osrm_profile_speed_when_available():
    result = resolve_reference_speed(profile_speed_mps=13.5, historical_median_mps=10.0)
    assert result.speed_mps == 13.5
    assert result.source == OSRM_PROFILE


def test_falls_back_to_historical_when_profile_speed_missing():
    result = resolve_reference_speed(profile_speed_mps=None, historical_median_mps=10.0)
    assert result.speed_mps == 10.0
    assert result.source == HISTORICAL


def test_falls_back_to_historical_when_profile_speed_is_zero():
    result = resolve_reference_speed(profile_speed_mps=0.0, historical_median_mps=10.0)
    assert result.source == HISTORICAL


def test_falls_back_to_documented_constant_when_nothing_else_available():
    result = resolve_reference_speed(
        profile_speed_mps=None, historical_median_mps=None, fallback_speed_mps=8.33
    )
    assert result.speed_mps == 8.33
    assert result.source == FALLBACK
