from datetime import datetime, timezone


def _observation(lat=12.97, lon=77.59, speed_mps=10.0, accuracy_m=10.0, timestamp=None):
    return {
        "latitude": lat,
        "longitude": lon,
        "speed_mps": speed_mps,
        "accuracy_m": accuracy_m,
        "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
    }


def test_ingest_rejects_implausible_speed(client):
    response = client.post(
        "/api/v1/traffic/observations",
        json={"observations": [_observation(speed_mps=100.0)]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 0
    assert body["rejected"] == 1
    assert "exceeds plausible maximum" in body["rejection_reasons"][0]


def test_ingest_reports_map_match_failure_without_crashing(client):
    """The shared test client's road-matching provider always reports no match
    (tests/api/conftest.py) - proves the endpoint degrades gracefully rather than
    erroring when a trace can't be matched."""
    response = client.post(
        "/api/v1/traffic/observations",
        json={"observations": [_observation(speed_mps=10.0)]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 0


def test_ingest_rejects_batch_exceeding_configured_limit(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "traffic_max_batch_size", 1)
    response = client.post(
        "/api/v1/traffic/observations",
        json={"observations": [_observation(), _observation()]},
    )

    assert response.status_code == 400


def test_get_segments_returns_empty_list_when_no_data(client):
    response = client.get(
        "/api/v1/traffic/segments", params={"west": 77.0, "south": 12.0, "east": 78.0, "north": 13.0}
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_segments_rejects_invalid_bbox_bounds(client):
    response = client.get(
        "/api/v1/traffic/segments", params={"west": 999.0, "south": 12.0, "east": 78.0, "north": 13.0}
    )

    assert response.status_code == 422
