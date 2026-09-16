ORIGIN = {"latitude": 12.97, "longitude": 77.59}
DESTINATION = {"latitude": 12.98, "longitude": 77.6}


def test_compute_route_returns_road_route(client):
    response = client.post("/api/v1/routes", json={"origin": ORIGIN, "destination": DESTINATION})

    assert response.status_code == 200
    body = response.json()
    assert body["distance_meters"] == 1500.0
    assert body["duration_seconds"] == 240.0


def test_compute_route_rejects_invalid_latitude(client):
    invalid_origin = {"latitude": 999, "longitude": 77.59}
    response = client.post("/api/v1/routes", json={"origin": invalid_origin, "destination": DESTINATION})

    assert response.status_code == 422
