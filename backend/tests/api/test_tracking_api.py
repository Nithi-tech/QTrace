DEPOT = {"latitude": 13.0827, "longitude": 80.2707}


def _fleet_request() -> dict:
    return {
        "scenario": "PACKAGE_DELIVERY",
        "depot": DEPOT,
        "return_to_depot": True,
        "vehicles": [{"vehicle_type": "Van", "count": 1, "capacity": 100.0, "cost_per_km": 12.0}],
        "destinations": [
            {"name": "T Nagar", "coordinate": {"latitude": 13.0418, "longitude": 80.2341}, "demand": 20.0},
        ],
        "objective": "BALANCED",
    }


def test_fleet_routes_response_includes_tracking_code_and_session_id(client):
    response = client.post("/api/v1/fleet/routes", json=_fleet_request())

    assert response.status_code == 200
    body = response.json()
    assert body["planning_session_id"]
    assert len(body["vehicle_routes"]) == 1
    assert body["vehicle_routes"][0]["tracking_code"]


def test_driver_can_fetch_their_assigned_route_by_code(client):
    fleet_response = client.post("/api/v1/fleet/routes", json=_fleet_request())
    code = fleet_response.json()["vehicle_routes"][0]["tracking_code"]

    response = client.get(f"/api/v1/tracking/{code}")

    assert response.status_code == 200
    body = response.json()
    assert body["tracking_code"] == code
    assert body["stop_names"][0] == "Depot"


def test_unknown_tracking_code_is_404(client):
    response = client.get("/api/v1/tracking/NOPE99")

    assert response.status_code == 404
    assert response.json()["code"] == "TRACKING_SESSION_NOT_FOUND"


def test_driver_ping_then_status_reflects_current_location(client):
    fleet_response = client.post("/api/v1/fleet/routes", json=_fleet_request())
    code = fleet_response.json()["vehicle_routes"][0]["tracking_code"]

    ping = client.post(f"/api/v1/tracking/{code}/ping", json={"coordinate": {"latitude": 13.05, "longitude": 80.25}})
    assert ping.status_code == 204

    status = client.get(f"/api/v1/tracking/{code}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["current_location"] == {"latitude": 13.05, "longitude": 80.25}
    assert body["last_ping_at"] is not None


def test_admin_fleet_overview_lists_the_vehicle_from_this_job(client):
    fleet_response = client.post("/api/v1/fleet/routes", json=_fleet_request())
    body = fleet_response.json()
    job_id = body["planning_session_id"]
    code = body["vehicle_routes"][0]["tracking_code"]

    overview = client.get(f"/api/v1/tracking/jobs/{job_id}")

    assert overview.status_code == 200
    vehicles = overview.json()["vehicles"]
    assert len(vehicles) == 1
    assert vehicles[0]["tracking_code"] == code


def test_admin_overview_for_unknown_job_is_404(client):
    response = client.get("/api/v1/tracking/jobs/does-not-exist")

    assert response.status_code == 404
