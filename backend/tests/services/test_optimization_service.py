from datetime import datetime, timezone
from typing import ClassVar

import pytest

from app.optimization.qpso import QPSOConfig, QPSOSolver
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.repositories.traffic_repository import TrafficRepository
from app.routing.base import RoutingProvider
from app.routing.exceptions import TooManyStopsError
from app.schemas.routing import Coordinate, MatrixResult, RouteRequest, RouteResult
from app.services.optimization_service import OptimizationService
from app.traffic.matrix_service import TrafficMatrixService

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


# --- Real QTrace crowd-traffic integration (not mocked) -----------------------------


class _TiedCostRoutingProvider(RoutingProvider):
    """Distance/duration are identical and tied between the two possible visit orders
    - without traffic, QPSO has no reason to prefer either. Isolates traffic as the
    only thing that can break the tie."""

    _TIED_MATRIX: ClassVar[list[list[float]]] = [
        [0, 5, 5, 100],
        [5, 0, 5, 5],
        [5, 5, 0, 5],
        [100, 5, 5, 0],
    ]

    def __init__(self) -> None:
        self.route_calls: list[list[Coordinate]] = []

    async def geocode(self, address):
        raise NotImplementedError

    async def route(self, coordinates):
        self.route_calls.append(list(coordinates))
        return RouteResult(distance_meters=1000.0, duration_seconds=100.0, geometry=None)

    async def matrix(self, coordinates):
        return MatrixResult(distances_meters=self._TIED_MATRIX, durations_seconds=self._TIED_MATRIX)


@pytest.mark.asyncio
async def test_real_qtrace_traffic_snapshot_changes_which_order_qpso_picks(db_session):
    """End-to-end proof using the REAL TrafficRepository + TrafficMatrixService (a
    genuine DB query and geometric corridor match, not a mock): a stored snapshot of
    heavy congestion on the origin->A road, and nothing on origin->B, must make QPSO
    prefer visiting B first even though distance/duration are exactly tied."""
    from app.models.traffic_segment import TrafficSegment
    from app.models.traffic_snapshot import TrafficSnapshot

    now = datetime.now(timezone.utc)
    # Placed directly on the straight line between ORIGIN (77.59,12.97) and _STOP_A
    # (77.50,12.90) so it reliably intersects that pair's corridor and no other.
    segment = TrafficSegment(
        node_a=1,
        node_b=2,
        geometry={"type": "LineString", "coordinates": [[77.548, 12.9384], [77.542, 12.9316]]},
        profile_speed_mps=15.0,
        created_at=now,
    )
    db_session.add(segment)
    db_session.flush()
    db_session.add(
        TrafficSnapshot(
            provider="qtrace_telemetry",
            road_or_route_info={},
            captured_at=now,
            segment_id=segment.id,
            current_speed_mps=1.0,
            reference_speed_mps=15.0,
            congestion_score=1.0,  # near-stopped
            observation_count=10,
            confidence=1.0,
            status="LIVE",
        )
    )
    db_session.commit()

    routing_provider = _TiedCostRoutingProvider()
    service = OptimizationService(
        routing_provider=routing_provider,
        job_repository=OptimizationJobRepository(db_session),
        qpso_solver=QPSOSolver(QPSOConfig(seed=42)),
        traffic_repository=TrafficRepository(db_session),
        traffic_matrix_service=TrafficMatrixService(corridor_radius_meters=500),
        traffic_enabled=True,
    )

    _, result = await service.plan_route(
        RouteRequest(origin=ORIGIN, destination=DESTINATION, stops=[_STOP_A, _STOP_B])
    )

    assert result.algorithm == "QPSO"
    assert result.stop_order == [1, 0]  # visit B (index 1) before A (index 0), avoiding the jam
    assert routing_provider.route_calls[0] == [ORIGIN, _STOP_B, _STOP_A, DESTINATION]
    assert result.traffic.enabled is True
    assert result.traffic.available is True
    assert result.traffic.source == "qtrace_telemetry"
