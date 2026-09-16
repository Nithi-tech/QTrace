import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_geocoding_provider, get_road_matching_provider, get_routing_provider
from app.core.db import get_db
from app.main import app
from app.models import Base
from app.schemas.geocoding import GeocodingSuggestion
from app.schemas.map_matching import TraceMatchResult
from app.schemas.routing import Coordinate, MatrixResult, RouteResult


class StubRoutingProvider:
    async def geocode(self, address):
        raise NotImplementedError

    async def route(self, coordinates):
        return RouteResult(distance_meters=1500.0, duration_seconds=240.0, geometry={"type": "LineString"})

    async def matrix(self, coordinates):
        size = len(coordinates)
        return MatrixResult(
            distances_meters=[[0] * size for _ in range(size)],
            durations_seconds=[[0] * size for _ in range(size)],
        )


class StubGeocodingProvider:
    async def search(self, query, limit=5):
        coordinate = Coordinate(latitude=1.0, longitude=2.0)
        return [GeocodingSuggestion(label=f"Result for {query}", coordinate=coordinate)]


class StubRoadMatchingProvider:
    """Never hits a real routing provider in API tests (CLAUDE.md #44) - dedicated
    map-matching tests (tests/traffic/) cover real matching behavior."""

    async def match_trace(self, points):
        return TraceMatchResult(matched=False)

    async def snap_point(self, coordinate):
        from app.schemas.map_matching import SnapResult

        return SnapResult(matched=False)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_routing_provider] = lambda: StubRoutingProvider()
    app.dependency_overrides[get_geocoding_provider] = lambda: StubGeocodingProvider()
    app.dependency_overrides[get_road_matching_provider] = lambda: StubRoadMatchingProvider()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
