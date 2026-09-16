import pytest

from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.routing.base import RoutingProvider
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
