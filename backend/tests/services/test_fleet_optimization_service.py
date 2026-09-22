"""Integration-style test for the multi-vehicle pipeline, using a realistic
Chennai-area example (per the feature spec): depot + T Nagar / Adyar /
Velachery / Guindy, served by 2 Vans + 1 Mini Truck.
"""

import math
from datetime import time

import pytest

from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.schemas.fleet import (
    Destination,
    FleetRouteRequest,
    OptimizationObjective,
    ScenarioType,
    VehicleSpec,
)
from app.schemas.geocoding import GeocodingSuggestion
from app.schemas.routing import Coordinate, MatrixResult, RouteResult
from app.services.exceptions import FleetInfeasibleError
from app.services.fleet_optimization_service import FleetOptimizationService

_SPEED_METERS_PER_SECOND = 40_000 / 3600  # 40 km/h, a reasonable urban average


def _euclidean_meters(a: Coordinate, b: Coordinate) -> float:
    # Degrees-as-meters approximation scaled up; fine for a self-consistent test stub.
    return math.dist((a.latitude, a.longitude), (b.latitude, b.longitude)) * 111_000


class StubRoutingProvider:
    """Distances/durations are derived consistently from real coordinate deltas,
    so nearest-neighbor + 2-Opt have a genuine geometry to optimize against."""

    async def geocode(self, address):
        raise NotImplementedError

    async def route(self, coordinates: list[Coordinate]) -> RouteResult:
        total = sum(
            _euclidean_meters(coordinates[i], coordinates[i + 1]) for i in range(len(coordinates) - 1)
        )
        return RouteResult(
            distance_meters=total, duration_seconds=total / _SPEED_METERS_PER_SECOND, geometry=None
        )

    async def matrix(self, coordinates: list[Coordinate]) -> MatrixResult:
        n = len(coordinates)
        distances = [[_euclidean_meters(coordinates[i], coordinates[j]) for j in range(n)] for i in range(n)]
        durations = [[d / _SPEED_METERS_PER_SECOND for d in row] for row in distances]
        return MatrixResult(distances_meters=distances, durations_seconds=durations)


class StubGeocodingProvider:
    """Resolves the one address-only destination used below ("Adyar")."""

    async def search(self, query: str, limit: int = 5) -> list[GeocodingSuggestion]:
        if "adyar" in query.lower():
            return [
                GeocodingSuggestion(
                    label="Adyar, Chennai", coordinate=Coordinate(latitude=13.0012, longitude=80.2565)
                )
            ]
        return []


@pytest.fixture()
def service(db_session) -> FleetOptimizationService:
    return FleetOptimizationService(
        routing_provider=StubRoutingProvider(),
        geocoding_provider=StubGeocodingProvider(),
        job_repository=OptimizationJobRepository(db_session),
    )


def _chennai_request(objective: OptimizationObjective = OptimizationObjective.BALANCED) -> FleetRouteRequest:
    return FleetRouteRequest(
        scenario=ScenarioType.PACKAGE_DELIVERY,
        depot=Coordinate(latitude=13.0827, longitude=80.2707),
        return_to_depot=True,
        vehicles=[
            VehicleSpec(vehicle_type="Van", count=2, capacity=100.0, cost_per_km=12.0),
            VehicleSpec(vehicle_type="Mini Truck", count=1, capacity=60.0, cost_per_km=18.0),
        ],
        destinations=[
            Destination(
                name="T Nagar", coordinate=Coordinate(latitude=13.0418, longitude=80.2341), demand=20.0
            ),
            Destination(name="Adyar", address="Adyar, Chennai", demand=30.0),  # geocoded, not given directly
            Destination(
                name="Velachery", coordinate=Coordinate(latitude=12.9789, longitude=80.2189), demand=40.0
            ),
            Destination(
                name="Guindy", coordinate=Coordinate(latitude=13.0067, longitude=80.2206), demand=50.0
            ),
        ],
        objective=objective,
    )


@pytest.mark.asyncio
async def test_every_destination_assigned_exactly_once(service):
    _job, response = await service.plan_fleet_routes(_chennai_request())

    assert response.is_feasible
    assert response.unassigned_destination_indices == []
    all_assigned = sorted(i for route in response.vehicle_routes for i in route.destination_indices)
    assert all_assigned == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_produces_genuinely_separate_routes_not_one_merged_route(service):
    """The core requirement: multiple non-identical routes, not one route with extra labels."""
    _job, response = await service.plan_fleet_routes(_chennai_request())

    assert len(response.vehicle_routes) >= 2
    stop_name_sets = [tuple(route.destination_indices) for route in response.vehicle_routes]
    assert len(stop_name_sets) == len(set(stop_name_sets))  # every vehicle covers a distinct stop set


@pytest.mark.asyncio
async def test_no_vehicle_exceeds_its_capacity(service):
    _job, response = await service.plan_fleet_routes(_chennai_request())

    for route in response.vehicle_routes:
        assert route.load <= route.capacity
        assert 0.0 <= route.capacity_utilization <= 1.0


@pytest.mark.asyncio
async def test_routes_start_and_end_at_depot(service):
    _job, response = await service.plan_fleet_routes(_chennai_request())

    for route in response.vehicle_routes:
        assert route.stop_names[0] == "Depot"
        assert route.stop_names[-1] == "Depot"


@pytest.mark.asyncio
async def test_geocoded_destination_is_actually_routed(service):
    _job, response = await service.plan_fleet_routes(_chennai_request())

    adyar_route = next(r for r in response.vehicle_routes if 1 in r.destination_indices)
    assert "Adyar" in adyar_route.stop_names


@pytest.mark.asyncio
async def test_all_destinations_unresolvable_raises_infeasible(service):
    request = FleetRouteRequest(
        scenario=ScenarioType.GOODS_LOGISTICS,
        depot=Coordinate(latitude=13.0827, longitude=80.2707),
        vehicles=[VehicleSpec(vehicle_type="Van", count=1, capacity=100.0)],
        destinations=[Destination(name="Nowhere", address="does-not-exist-anywhere")],
    )

    with pytest.raises(FleetInfeasibleError):
        await service.plan_fleet_routes(request)


@pytest.mark.asyncio
async def test_demand_exceeding_total_fleet_capacity_reports_partial_infeasibility(service):
    request = FleetRouteRequest(
        scenario=ScenarioType.GOODS_LOGISTICS,
        depot=Coordinate(latitude=13.0827, longitude=80.2707),
        vehicles=[VehicleSpec(vehicle_type="Van", count=1, capacity=10.0)],  # far too small
        destinations=[
            Destination(
                name="T Nagar", coordinate=Coordinate(latitude=13.0418, longitude=80.2341), demand=20.0
            ),
            Destination(
                name="Guindy", coordinate=Coordinate(latitude=13.0067, longitude=80.2206), demand=50.0
            ),
        ],
    )

    _job, response = await service.plan_fleet_routes(request)

    assert response.is_feasible is False
    assert response.unassigned_destination_indices != []
    assert response.infeasibility_reason is not None
    for route in response.vehicle_routes:
        assert route.load <= route.capacity


@pytest.mark.asyncio
async def test_vehicle_availability_end_exceeded_is_reported_as_a_violation(service):
    """Regression test: availability_end is a real input (VehicleSpec) that was
    previously stored but never checked anywhere - a vehicle configured as
    only available for 5 minutes must surface that its route runs over."""
    request = FleetRouteRequest(
        scenario=ScenarioType.PACKAGE_DELIVERY,
        depot=Coordinate(latitude=13.0827, longitude=80.2707),
        vehicles=[
            VehicleSpec(
                vehicle_type="Van",
                count=1,
                capacity=100.0,
                availability_start=time(8, 0),
                availability_end=time(8, 5),  # far too tight for a real trip
            )
        ],
        destinations=[
            Destination(
                name="Velachery", coordinate=Coordinate(latitude=12.9789, longitude=80.2189), demand=10.0
            ),
        ],
    )

    _job, response = await service.plan_fleet_routes(request)

    route = response.vehicle_routes[0]
    assert any("available until" in v for v in route.time_window_violations)


@pytest.mark.asyncio
async def test_vehicle_availability_end_not_exceeded_reports_no_violation(service):
    request = FleetRouteRequest(
        scenario=ScenarioType.PACKAGE_DELIVERY,
        depot=Coordinate(latitude=13.0827, longitude=80.2707),
        vehicles=[
            VehicleSpec(
                vehicle_type="Van",
                count=1,
                capacity=100.0,
                availability_start=time(8, 0),
                availability_end=time(20, 0),  # generous window
            )
        ],
        destinations=[
            Destination(
                name="Velachery", coordinate=Coordinate(latitude=12.9789, longitude=80.2189), demand=10.0
            ),
        ],
    )

    _job, response = await service.plan_fleet_routes(request)

    route = response.vehicle_routes[0]
    assert route.time_window_violations == []
