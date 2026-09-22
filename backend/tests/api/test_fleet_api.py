from app.api.deps import get_geocoding_provider
from app.main import app

DEPOT = {"latitude": 13.0827, "longitude": 80.2707}


def _destination(name: str, lat: float, lon: float, demand: float = 10.0) -> dict:
    return {"name": name, "coordinate": {"latitude": lat, "longitude": lon}, "demand": demand}


def _request(**overrides) -> dict:
    body = {
        "scenario": "PACKAGE_DELIVERY",
        "depot": DEPOT,
        "return_to_depot": True,
        "vehicles": [{"vehicle_type": "Van", "count": 2, "capacity": 100.0, "cost_per_km": 12.0}],
        "destinations": [
            _destination("T Nagar", 13.0418, 80.2341, 20.0),
            _destination("Adyar", 13.0012, 80.2565, 30.0),
        ],
        "objective": "BALANCED",
    }
    body.update(overrides)
    return body


def test_create_fleet_routes_returns_a_route_per_vehicle_used(client):
    response = client.post("/api/v1/fleet/routes", json=_request())

    assert response.status_code == 200
    body = response.json()
    assert body["is_feasible"] is True
    assert body["unassigned_destination_indices"] == []
    all_assigned = sorted(i for route in body["vehicle_routes"] for i in route["destination_indices"])
    assert all_assigned == [0, 1]


def test_missing_destinations_is_rejected_by_schema(client):
    response = client.post("/api/v1/fleet/routes", json=_request(destinations=[]))

    assert response.status_code == 422


def test_missing_vehicles_is_rejected_by_schema(client):
    response = client.post("/api/v1/fleet/routes", json=_request(vehicles=[]))

    assert response.status_code == 422


def test_destination_without_coordinate_or_address_is_rejected(client):
    response = client.post(
        "/api/v1/fleet/routes",
        json=_request(destinations=[{"name": "Nowhere", "demand": 10.0}]),
    )

    assert response.status_code == 422


def test_destination_that_cannot_be_geocoded_reports_infeasible(client):
    class NoResultsGeocodingProvider:
        async def search(self, query, limit=5):
            return []

    app.dependency_overrides[get_geocoding_provider] = lambda: NoResultsGeocodingProvider()

    response = client.post(
        "/api/v1/fleet/routes",
        json=_request(destinations=[{"name": "Unresolvable", "address": "??", "demand": 10.0}]),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "FLEET_INFEASIBLE"
