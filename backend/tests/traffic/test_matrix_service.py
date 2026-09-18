from datetime import datetime, timezone

import pytest

from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficIncident
from app.traffic.matrix_service import TrafficMatrixService
from app.traffic.traffic_service import ResolvedTraffic

ORIGIN = Coordinate(latitude=12.90, longitude=77.50)
DESTINATION = Coordinate(latitude=12.90, longitude=77.60)


class FakeTrafficService:
    def __init__(self, results: dict[tuple[float, float], ResolvedTraffic]):
        self._results = results
        self.calls = 0

    async def resolve(self, repository, coordinate):
        self.calls += 1
        return self._results[(coordinate.latitude, coordinate.longitude)]


class FakeTomTomIncidents:
    def __init__(self, incidents=None, fail=False):
        self.incidents = incidents or []
        self.fail = fail

    async def get_incidents(self, west, south, east, north):
        if self.fail:
            from app.traffic.exceptions import TrafficProviderUnavailableError

            raise TrafficProviderUnavailableError("boom")
        return self.incidents


_UNAVAILABLE = ResolvedTraffic(
    available=False, status="UNAVAILABLE", source=None, congestion_score=0.0, confidence=0.0, updated_at=None
)


def _live(congestion: float, confidence: float) -> ResolvedTraffic:
    return ResolvedTraffic(
        available=True,
        status="LIVE",
        source="TOMTOM",
        congestion_score=congestion,
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_disabled_returns_baseline_without_resolving(db_session):
    traffic_service = FakeTrafficService({})
    service = TrafficMatrixService(traffic_service, tomtom_provider=None, corridor_radius_meters=200)

    result = await service.get_traffic_matrix(db_session, [ORIGIN, DESTINATION], enabled=False)

    assert result.status.enabled is False
    assert result.matrix == [[0.0, 0.0], [0.0, 0.0]]
    assert traffic_service.calls == 0


@pytest.mark.asyncio
async def test_no_data_anywhere_reports_unavailable(db_session):
    traffic_service = FakeTrafficService(
        {
            (ORIGIN.latitude, ORIGIN.longitude): _UNAVAILABLE,
            (DESTINATION.latitude, DESTINATION.longitude): _UNAVAILABLE,
        }
    )
    service = TrafficMatrixService(traffic_service, tomtom_provider=None, corridor_radius_meters=200)

    result = await service.get_traffic_matrix(db_session, [ORIGIN, DESTINATION], enabled=True)

    assert result.status.available is False
    assert result.matrix == [[0.0, 0.0], [0.0, 0.0]]


@pytest.mark.asyncio
async def test_confidence_weighted_score_from_both_endpoints(db_session):
    traffic_service = FakeTrafficService(
        {
            (ORIGIN.latitude, ORIGIN.longitude): _live(congestion=0.8, confidence=1.0),
            (DESTINATION.latitude, DESTINATION.longitude): _live(congestion=0.4, confidence=1.0),
        }
    )
    service = TrafficMatrixService(traffic_service, tomtom_provider=None, corridor_radius_meters=200)

    result = await service.get_traffic_matrix(db_session, [ORIGIN, DESTINATION], enabled=True)

    # avg congestion = (0.8+0.4)/2 = 0.6, avg confidence = 1.0 -> cell = 0.6
    assert result.matrix[0][1] == pytest.approx(0.6)
    assert result.status.status == "LIVE"
    assert result.status.source == "TOMTOM"


@pytest.mark.asyncio
async def test_incident_on_corridor_can_override_low_congestion():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    session = sessionmaker(bind=engine)()

    traffic_service = FakeTrafficService(
        {
            (ORIGIN.latitude, ORIGIN.longitude): _live(congestion=0.1, confidence=1.0),
            (DESTINATION.latitude, DESTINATION.longitude): _live(congestion=0.1, confidence=1.0),
        }
    )
    closure = TrafficIncident(
        geometry={"type": "LineString", "coordinates": [[77.52, 12.90], [77.58, 12.90]]},
        incident_type="Closed",
        road_closed=True,
    )
    service = TrafficMatrixService(
        traffic_service, tomtom_provider=FakeTomTomIncidents(incidents=[closure]), corridor_radius_meters=200
    )

    result = await service.get_traffic_matrix(session, [ORIGIN, DESTINATION], enabled=True)

    # incident penalty (1.0, road closed) beats the low congestion (0.1) - max, not sum.
    assert result.matrix[0][1] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_incident_fetch_failure_does_not_crash_matrix_building(db_session):
    traffic_service = FakeTrafficService(
        {
            (ORIGIN.latitude, ORIGIN.longitude): _live(congestion=0.5, confidence=1.0),
            (DESTINATION.latitude, DESTINATION.longitude): _live(congestion=0.5, confidence=1.0),
        }
    )
    service = TrafficMatrixService(
        traffic_service, tomtom_provider=FakeTomTomIncidents(fail=True), corridor_radius_meters=200
    )

    result = await service.get_traffic_matrix(db_session, [ORIGIN, DESTINATION], enabled=True)

    assert result.status.available is True  # flow data still used despite incidents failing
    assert result.matrix[0][1] == pytest.approx(0.5)
