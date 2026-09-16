import pytest

from app.optimization.qpso import QPSOConfig, QPSOSolver
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.routing.base import RoutingProvider
from app.routing.exceptions import TooManyStopsError
from app.schemas.routing import Coordinate, MatrixResult, RouteRequest, RouteResult
from app.services.optimization_service import OptimizationService

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
    assert result.objective_value == 3


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
