from datetime import datetime, timezone

import pytest

from app.optimization.qpso import QPSOConfig, QPSOSolver
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.repositories.traffic_repository import TrafficRepository
from app.routing.base import RoutingProvider
from app.routing.exceptions import TooManyStopsError
from app.schemas.routing import Coordinate, MatrixResult, RouteRequest, RouteResult
from app.schemas.traffic import TrafficIncident
from app.services.optimization_service import OptimizationService
from app.traffic.matrix_service import TrafficMatrixService
from app.traffic.traffic_service import ResolvedTraffic

ORIGIN = Coordinate(latitude=12.97, longitude=77.59)
DESTINATION = Coordinate(latitude=12.98, longitude=77.60)


class StubRoutingProvider(RoutingProvider):
    async def geocode(self, address):
        raise NotImplementedError

    async def route(self, coordinates):
        return RouteResult(distance_meters=1500.0, duration_seconds=240.0, geometry=None)

    async def matrix(self, coordinates):
        return MatrixResult(distances_meters=[[0, 1500], [1500, 0]], durations_seconds=[[0, 240], [240, 0]])


class SpyRoutingProvider(RoutingProvider):
    """Records every route()/matrix() call so tests can assert OSRM is called the
    expected number of times (CLAUDE.md master-prompt rule: never call the routing
    provider from inside the QPSO fitness loop - exactly one matrix() + one route())."""

    def __init__(self, duration_matrix: list[list[float]]) -> None:
        self._duration_matrix = duration_matrix
        self.route_calls: list[list[Coordinate]] = []
        self.matrix_calls: list[list[Coordinate]] = []

    async def geocode(self, address):
        raise NotImplementedError

    async def route(self, coordinates):
        self.route_calls.append(list(coordinates))
        return RouteResult(distance_meters=1500.0, duration_seconds=240.0, geometry=None)

    async def matrix(self, coordinates):
        self.matrix_calls.append(list(coordinates))
        size = len(coordinates)
        distances = [[0.0] * size for _ in range(size)]
        return MatrixResult(distances_meters=distances, durations_seconds=self._duration_matrix)


@pytest.mark.asyncio
async def test_two_point_request_is_direct_route_not_qpso(db_session):
    service = OptimizationService(
        routing_provider=StubRoutingProvider(), job_repository=OptimizationJobRepository(db_session)
    )

    job, result = await service.plan_route(RouteRequest(origin=ORIGIN, destination=DESTINATION))

    assert result.algorithm == "DIRECT_ROUTE"
    assert result.objective_value is None
    assert result.route.distance_meters == 1500.0
    assert job.algorithm == "DIRECT_ROUTE"
    assert job.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_job_is_persisted_and_retrievable(db_session):
    repository = OptimizationJobRepository(db_session)
    service = OptimizationService(routing_provider=StubRoutingProvider(), job_repository=repository)

    job, _ = await service.plan_route(RouteRequest(origin=ORIGIN, destination=DESTINATION))

    fetched = repository.get_by_id(job.id)
    assert fetched is not None
    assert fetched.id == job.id


# Hand-checkable case (CLAUDE.md #52): two intermediate stops A, B where visiting
# B-then-A costs 3 (1+1+1) and A-then-B costs 21 (10+1+10), so QPSO must pick B-then-A.
_STOP_A = Coordinate(latitude=12.90, longitude=77.50)
_STOP_B = Coordinate(latitude=12.95, longitude=77.55)
# Full order for this matrix is [origin(0), A(1), B(2), destination(3)].
_HAND_CHECKABLE_DURATION_MATRIX = [
    [0, 10, 1, 100],
    [10, 0, 1, 1],
    [1, 1, 0, 10],
    [100, 1, 10, 0],
]


@pytest.mark.asyncio
async def test_multi_stop_request_calls_osrm_exactly_twice_and_picks_optimal_order(db_session):
    """Verifies the master-prompt rule: one matrix() call, QPSO runs locally, one
    final route() call on the QPSO-reordered stops - never OSRM-per-particle."""
    spy = SpyRoutingProvider(duration_matrix=_HAND_CHECKABLE_DURATION_MATRIX)
    service = OptimizationService(
        routing_provider=spy,
        job_repository=OptimizationJobRepository(db_session),
        qpso_solver=QPSOSolver(QPSOConfig(seed=42)),
    )

    _, result = await service.plan_route(
        RouteRequest(origin=ORIGIN, destination=DESTINATION, stops=[_STOP_A, _STOP_B])
    )

    assert len(spy.matrix_calls) == 1
    assert len(spy.route_calls) == 1
    assert result.algorithm == "QPSO"
    assert result.stop_order == [1, 0]  # visit B (index 1) then A (index 0)
    assert spy.route_calls[0] == [ORIGIN, _STOP_B, _STOP_A, DESTINATION]
    # objective_value is the blended (normalized) fitness QPSO actually searched, not
    # raw seconds: distances are all 0 here (normalizes to 0), traffic is disabled by
    # default (0), so this is exactly time_weight=0.4 * (3 / max_duration=100).
    assert result.objective_value == pytest.approx(0.012)


@pytest.mark.asyncio
async def test_request_exceeding_max_stops_is_rejected(db_session):
    service = OptimizationService(
        routing_provider=StubRoutingProvider(),
        job_repository=OptimizationJobRepository(db_session),
        max_stops=3,
    )

    with pytest.raises(TooManyStopsError):
        await service.plan_route(
            RouteRequest(origin=ORIGIN, destination=DESTINATION, stops=[_STOP_A, _STOP_B])
        )


# City-independence (CLAUDE.md master-prompt #41): the same code path must run
# regardless of which region the coordinates come from. These are test fixtures only.
_CHENNAI = Coordinate(latitude=13.0827, longitude=80.2707)
_LONDON = Coordinate(latitude=51.5072, longitude=-0.1276)
_NEW_YORK = Coordinate(latitude=40.7128, longitude=-74.0060)
_TOKYO = Coordinate(latitude=35.6762, longitude=139.6503)


@pytest.mark.parametrize(
    "origin,stop_a,stop_b,destination",
    [
        (ORIGIN, _STOP_A, _STOP_B, DESTINATION),
        (_CHENNAI, _LONDON, _NEW_YORK, _TOKYO),
        (_TOKYO, _CHENNAI, _LONDON, _NEW_YORK),
    ],
)
@pytest.mark.asyncio
async def test_qpso_path_is_city_independent(db_session, origin, stop_a, stop_b, destination):
    spy = SpyRoutingProvider(duration_matrix=_HAND_CHECKABLE_DURATION_MATRIX)
    service = OptimizationService(
        routing_provider=spy,
        job_repository=OptimizationJobRepository(db_session),
        qpso_solver=QPSOSolver(QPSOConfig(seed=42)),
    )

    _, result = await service.plan_route(
        RouteRequest(origin=origin, destination=destination, stops=[stop_a, stop_b])
    )

    assert result.algorithm == "QPSO"
    assert sorted(result.stop_order) == [0, 1]
    assert len(spy.matrix_calls) == 1
    assert len(spy.route_calls) == 1


# --- Traffic changes which order QPSO picks (CLAUDE.md traffic master-prompt: the
# critical end-to-end proof). Only the network boundary is faked (TomTom's HTTP calls);
# TrafficMatrixService's real corridor-matching/blending and QPSO's real update
# equations run unmodified - see app/traffic/matrix_service.py and app/optimization/
# fitness.py.
_TRAFFIC_ORIGIN = Coordinate(latitude=12.90, longitude=77.50)
_TRAFFIC_STOP_A = Coordinate(latitude=12.90, longitude=77.52)  # due east of origin, same latitude
_TRAFFIC_STOP_B = Coordinate(latitude=12.95, longitude=77.58)  # off that line entirely
_TRAFFIC_DESTINATION = Coordinate(latitude=12.90, longitude=77.60)

# Without traffic, A-then-B is marginally cheaper by duration alone (9 < 10 for the
# first leg). Full order for this matrix is [origin(0), A(1), B(2), destination(3)].
_TRAFFIC_DURATION_MATRIX = [
    [0, 9, 10, 15],
    [9, 0, 5, 10],
    [10, 5, 0, 10],
    [15, 10, 10, 0],
]


class _FakeTrafficService:
    """Stands in for TrafficService (the real TomTom/QTrace-crowd/historical fallback)
    so this test controls resolved traffic per coordinate without a network call, while
    TrafficMatrixService's real combination/corridor logic still runs on top of it."""

    def __init__(self, congestion_by_coordinate: dict[tuple[float, float], float]) -> None:
        self._congestion = congestion_by_coordinate

    async def resolve(self, repository, coordinate) -> ResolvedTraffic:
        return ResolvedTraffic(
            available=True,
            status="LIVE",
            source="TOMTOM",
            congestion_score=self._congestion[(coordinate.latitude, coordinate.longitude)],
            confidence=1.0,
            updated_at=datetime.now(timezone.utc),
        )


class _FakeTomTomIncidents:
    def __init__(self, incidents: list[TrafficIncident]) -> None:
        self._incidents = incidents

    async def get_incidents(self, west, south, east, north) -> list[TrafficIncident]:
        return self._incidents


def _zero_congestion_traffic_matrix_service(incidents: list[TrafficIncident]) -> TrafficMatrixService:
    congestion = {
        (_TRAFFIC_ORIGIN.latitude, _TRAFFIC_ORIGIN.longitude): 0.0,
        (_TRAFFIC_STOP_A.latitude, _TRAFFIC_STOP_A.longitude): 0.0,
        (_TRAFFIC_STOP_B.latitude, _TRAFFIC_STOP_B.longitude): 0.0,
        (_TRAFFIC_DESTINATION.latitude, _TRAFFIC_DESTINATION.longitude): 0.0,
    }
    return TrafficMatrixService(
        traffic_service=_FakeTrafficService(congestion),
        tomtom_provider=_FakeTomTomIncidents(incidents),
        corridor_radius_meters=150.0,
    )


@pytest.mark.asyncio
async def test_traffic_incident_flips_qpso_stop_order(db_session):
    spy_no_incident = SpyRoutingProvider(duration_matrix=_TRAFFIC_DURATION_MATRIX)
    baseline_service = OptimizationService(
        routing_provider=spy_no_incident,
        job_repository=OptimizationJobRepository(db_session),
        qpso_solver=QPSOSolver(QPSOConfig(seed=42)),
        traffic_repository=object(),  # unused by _FakeTrafficService; DB never touched
        traffic_matrix_service=_zero_congestion_traffic_matrix_service(incidents=[]),
        traffic_enabled=True,
    )

    _, baseline_result = await baseline_service.plan_route(
        RouteRequest(
            origin=_TRAFFIC_ORIGIN,
            destination=_TRAFFIC_DESTINATION,
            stops=[_TRAFFIC_STOP_A, _TRAFFIC_STOP_B],
        )
    )

    # With no incident, duration alone makes A-then-B (origin's 9 < 10) the cheaper order.
    assert baseline_result.stop_order == [0, 1]

    # A real road closure whose geometry sits only on the origin->A corridor (verified
    # by construction: colinear with origin and A, at longitudes strictly between them;
    # far from the diagonal origin->B, A->B, and B->destination corridors at this
    # radius - see app/traffic/matcher.py for the corridor-intersection logic actually
    # exercised here).
    closure = TrafficIncident(
        geometry={"type": "LineString", "coordinates": [[77.505, 12.90], [77.515, 12.90]]},
        incident_type="Closed",
        road_closed=True,
    )
    spy_with_incident = SpyRoutingProvider(duration_matrix=_TRAFFIC_DURATION_MATRIX)
    traffic_aware_service = OptimizationService(
        routing_provider=spy_with_incident,
        job_repository=OptimizationJobRepository(db_session),
        qpso_solver=QPSOSolver(QPSOConfig(seed=42)),
        traffic_repository=object(),
        traffic_matrix_service=_zero_congestion_traffic_matrix_service(incidents=[closure]),
        traffic_enabled=True,
    )

    _, traffic_result = await traffic_aware_service.plan_route(
        RouteRequest(
            origin=_TRAFFIC_ORIGIN,
            destination=_TRAFFIC_DESTINATION,
            stops=[_TRAFFIC_STOP_A, _TRAFFIC_STOP_B],
        )
    )

    # Same distances/durations, same seed - only the real, geometry-matched traffic
    # incident changed. QPSO now picks B-then-A to avoid the closed origin->A corridor.
    assert traffic_result.stop_order == [1, 0]
    assert traffic_result.traffic.available is True
    assert traffic_result.traffic.source == "TOMTOM"
    # The winning order's own edges (0->2, 2->1, 1->3) never cross the closed corridor,
    # so the route it actually reports on is LOW, not HEAVY (CLAUDE.md #72 - the label
    # must match what the rider actually experiences, not the worst edge anywhere).
    assert traffic_result.traffic.level == "LOW"


@pytest.mark.asyncio
async def test_traffic_level_reflects_heavy_congestion_on_the_chosen_route(db_session):
    """classify_traffic_level (app/traffic/aggregation.py) is applied to this route's own
    average traffic score, not left unwired (it existed but was never surfaced in an API
    response before this test)."""
    heavily_congested = {
        (_TRAFFIC_ORIGIN.latitude, _TRAFFIC_ORIGIN.longitude): 0.9,
        (_TRAFFIC_STOP_A.latitude, _TRAFFIC_STOP_A.longitude): 0.9,
        (_TRAFFIC_STOP_B.latitude, _TRAFFIC_STOP_B.longitude): 0.9,
        (_TRAFFIC_DESTINATION.latitude, _TRAFFIC_DESTINATION.longitude): 0.9,
    }
    matrix_service = TrafficMatrixService(
        traffic_service=_FakeTrafficService(heavily_congested),
        tomtom_provider=_FakeTomTomIncidents(incidents=[]),
        corridor_radius_meters=150.0,
    )
    service = OptimizationService(
        routing_provider=SpyRoutingProvider(duration_matrix=_TRAFFIC_DURATION_MATRIX),
        job_repository=OptimizationJobRepository(db_session),
        qpso_solver=QPSOSolver(QPSOConfig(seed=42)),
        traffic_repository=object(),
        traffic_matrix_service=matrix_service,
        traffic_enabled=True,
    )

    _, result = await service.plan_route(
        RouteRequest(
            origin=_TRAFFIC_ORIGIN,
            destination=_TRAFFIC_DESTINATION,
            stops=[_TRAFFIC_STOP_A, _TRAFFIC_STOP_B],
        )
    )

    assert result.traffic.available is True
    assert result.traffic.level == "HEAVY"
