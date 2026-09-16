ORIGIN = {"latitude": 12.97, "longitude": 77.59}
DESTINATION = {"latitude": 12.98, "longitude": 77.60}


def test_create_and_fetch_optimization_job(client):
    create_response = client.post(
        "/api/v1/optimization/jobs", json={"origin": ORIGIN, "destination": DESTINATION}
    )

    assert create_response.status_code == 200
    body = create_response.json()
    assert body["status"] == "COMPLETED"
    assert body["algorithm"] == "DIRECT_ROUTE"
    assert body["result"]["route"]["distance_meters"] == 1500.0
    assert body["result"]["stops_count"] == 2

    job_id = body["id"]
    fetch_response = client.get(f"/api/v1/optimization/jobs/{job_id}")
    assert fetch_response.status_code == 200
    assert fetch_response.json()["id"] == job_id


def test_fetch_unknown_job_returns_404(client):
    response = client.get("/api/v1/optimization/jobs/does-not-exist")
    assert response.status_code == 404
