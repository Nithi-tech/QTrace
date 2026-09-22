from datetime import datetime, timezone


def test_get_traffic_at_point_is_unavailable_with_no_provider_and_no_history(client):
    response = client.get("/api/v1/traffic/point", params={"latitude": 12.97, "longitude": 77.59})

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["available"] is False
    assert body["status"] == "UNAVAILABLE"
    assert body["source"] is None


def test_get_traffic_at_point_validates_coordinate_bounds(client):
    response = client.get("/api/v1/traffic/point", params={"latitude": 200.0, "longitude": 77.59})

    assert response.status_code == 422


def test_ingest_observations_rejects_implausible_speed(client):
    payload = {
        "observations": [
            {
                "latitude": 12.97,
                "longitude": 77.59,
                "speed_mps": 999.0,
                "accuracy_m": 10.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    response = client.post("/api/v1/traffic/observations", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 0
    assert body["rejected"] == 1
    assert "exceeds plausible maximum" in body["rejection_reasons"][0]


def test_ingest_observations_batch_over_limit_is_rejected(client):
    now = datetime.now(timezone.utc).isoformat()
    observations = [
        {"latitude": 12.97, "longitude": 77.59, "speed_mps": 10.0, "accuracy_m": 10.0, "timestamp": now}
        for _ in range(600)
    ]
    response = client.post("/api/v1/traffic/observations", json={"observations": observations})

    assert response.status_code == 400


def test_unknown_segment_is_404(client):
    response = client.get("/api/v1/traffic/segments/does-not-exist")

    assert response.status_code == 404


def test_get_traffic_area_is_unavailable_with_no_provider(client):
    response = client.get(
        "/api/v1/traffic/area",
        params={"min_lat": 12.90, "min_lon": 77.50, "max_lat": 12.95, "max_lon": 77.55},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["status"] == "UNAVAILABLE"
    assert body["segments"] == []


def test_get_traffic_area_rejects_inverted_bbox(client):
    response = client.get(
        "/api/v1/traffic/area",
        params={"min_lat": 12.95, "min_lon": 77.50, "max_lat": 12.90, "max_lon": 77.55},
    )

    assert response.status_code == 400


def test_get_traffic_area_rejects_area_too_large(client):
    response = client.get(
        "/api/v1/traffic/area",
        params={"min_lat": 10.0, "min_lon": 75.0, "max_lat": 15.0, "max_lon": 80.0},
    )

    assert response.status_code == 400
    assert "Zoom in" in response.json()["detail"]
