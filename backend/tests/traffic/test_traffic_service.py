from datetime import datetime, timedelta, timezone

import pytest

from app.models.traffic_historical_profile import TrafficHistoricalProfile
from app.models.traffic_segment import TrafficSegment
from app.models.traffic_snapshot import TrafficSnapshot
from app.repositories.traffic_repository import TrafficRepository
from app.routing.map_matching import RoadMatchingProvider
from app.schemas.map_matching import MatchedEdge, SnapResult
from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficFlowSegment
from app.traffic.cache import TTLCache
from app.traffic.exceptions import TrafficProviderUnavailableError
from app.traffic.historical import day_of_week, time_bucket_minutes
from app.traffic.traffic_service import TrafficService

POINT = Coordinate(latitude=12.97, longitude=77.59)


class FakeTomTom:
    def __init__(self, flow: TrafficFlowSegment | None = None, fail: bool = False):
        self.flow = flow
        self.fail = fail
        self.calls = 0

    async def get_flow_at_point(self, coordinate):
        self.calls += 1
        if self.fail:
            raise TrafficProviderUnavailableError("boom")
        return self.flow

    async def get_incidents(self, west, south, east, north):
        return []


class FakeMatching(RoadMatchingProvider):
    def __init__(self, node_a: int = 1, node_b: int = 2, matched: bool = True):
        self.node_a = node_a
        self.node_b = node_b
        self.matched = matched

    async def match_trace(self, points):
        raise NotImplementedError

    async def snap_point(self, coordinate):
        if not self.matched:
            return SnapResult(matched=False)
        return SnapResult(matched=True, edge=MatchedEdge(node_a=self.node_a, node_b=self.node_b))


def _service(tomtom=None, matching=None, **overrides) -> TrafficService:
    defaults = dict(
        tomtom_provider=tomtom or FakeTomTom(),
        matching_provider=matching or FakeMatching(),
        cache=TTLCache(60),
        live_ttl_seconds=120,
        recent_ttl_seconds=300,
        expired_seconds=900,
        min_observations=3,
    )
    defaults.update(overrides)
    return TrafficService(**defaults)


@pytest.mark.asyncio
async def test_uses_tomtom_when_available(db_session):
    flow = TrafficFlowSegment(current_speed_mps=5.0, free_flow_speed_mps=15.0, confidence=0.9)
    service = _service(tomtom=FakeTomTom(flow=flow))
    repo = TrafficRepository(db_session)

    result = await service.resolve(repo, POINT)

    assert result.available is True
    assert result.status == "LIVE"
    assert result.source == "TOMTOM"
    assert result.congestion_score == pytest.approx(1 - 5.0 / 15.0)
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_tomtom_response_is_cached_across_calls(db_session):
    flow = TrafficFlowSegment(current_speed_mps=5.0, free_flow_speed_mps=15.0, confidence=0.9)
    tomtom = FakeTomTom(flow=flow)
    service = _service(tomtom=tomtom)
    repo = TrafficRepository(db_session)

    await service.resolve(repo, POINT)
    await service.resolve(repo, POINT)

    assert tomtom.calls == 1


@pytest.mark.asyncio
async def test_falls_back_to_crowd_when_tomtom_unavailable(db_session):
    now = datetime.now(timezone.utc)
    segment = TrafficSegment(node_a=1, node_b=2, geometry=None, profile_speed_mps=15.0, created_at=now)
    db_session.add(segment)
    db_session.flush()
    db_session.add(
        TrafficSnapshot(
            provider="QTRACE_CROWD",
            road_or_route_info={},
            captured_at=now,
            segment_id=segment.id,
            current_speed_mps=5.0,
            reference_speed_mps=15.0,
            congestion_score=0.667,
            observation_count=5,
            confidence=0.8,
            status="LIVE",
        )
    )
    db_session.commit()

    service = _service(tomtom=FakeTomTom(fail=True))
    repo = TrafficRepository(db_session)

    result = await service.resolve(repo, POINT)

    assert result.available is True
    assert result.status == "LIVE"
    assert result.source == "QTRACE_CROWD"
    assert result.congestion_score == 0.667


@pytest.mark.asyncio
async def test_falls_back_to_historical_when_tomtom_and_crowd_both_unavailable(db_session):
    now = datetime.now(timezone.utc)
    segment = TrafficSegment(node_a=1, node_b=2, geometry=None, profile_speed_mps=15.0, created_at=now)
    db_session.add(segment)
    db_session.flush()
    db_session.add(
        TrafficHistoricalProfile(
            segment_id=segment.id,
            day_of_week=day_of_week(now),
            time_bucket_minutes=time_bucket_minutes(now),
            median_speed_mps=7.5,
            sample_count=10,
            updated_at=now,
        )
    )
    db_session.commit()

    service = _service(tomtom=FakeTomTom(fail=True))
    repo = TrafficRepository(db_session)

    result = await service.resolve(repo, POINT)

    assert result.available is True
    assert result.status == "HISTORICAL"
    assert result.source == "HISTORICAL"
    assert result.congestion_score == pytest.approx(1 - 7.5 / 15.0)
    assert 0.0 < result.confidence < 1.0


@pytest.mark.asyncio
async def test_historical_with_too_few_samples_is_rejected(db_session):
    now = datetime.now(timezone.utc)
    segment = TrafficSegment(node_a=1, node_b=2, geometry=None, profile_speed_mps=15.0, created_at=now)
    db_session.add(segment)
    db_session.flush()
    db_session.add(
        TrafficHistoricalProfile(
            segment_id=segment.id,
            day_of_week=day_of_week(now),
            time_bucket_minutes=time_bucket_minutes(now),
            median_speed_mps=7.5,
            sample_count=1,  # below min_observations=3
            updated_at=now,
        )
    )
    db_session.commit()

    service = _service(tomtom=FakeTomTom(fail=True))
    repo = TrafficRepository(db_session)

    result = await service.resolve(repo, POINT)

    assert result.available is False
    assert result.status == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_stale_crowd_snapshot_is_rejected_in_favor_of_historical(db_session):
    now = datetime.now(timezone.utc)
    segment = TrafficSegment(node_a=1, node_b=2, geometry=None, profile_speed_mps=15.0, created_at=now)
    db_session.add(segment)
    db_session.flush()
    db_session.add(
        TrafficSnapshot(
            provider="QTRACE_CROWD",
            road_or_route_info={},
            captured_at=now - timedelta(hours=2),  # well past expired_seconds=900
            segment_id=segment.id,
            current_speed_mps=5.0,
            reference_speed_mps=15.0,
            congestion_score=0.667,
            observation_count=5,
            confidence=0.8,
            status="LIVE",  # stored status is stale-by-now, must not be trusted as-is
        )
    )
    db_session.add(
        TrafficHistoricalProfile(
            segment_id=segment.id,
            day_of_week=day_of_week(now),
            time_bucket_minutes=time_bucket_minutes(now),
            median_speed_mps=7.5,
            sample_count=10,
            updated_at=now,
        )
    )
    db_session.commit()

    service = _service(tomtom=FakeTomTom(fail=True))
    repo = TrafficRepository(db_session)

    result = await service.resolve(repo, POINT)

    assert result.source == "HISTORICAL"  # not QTRACE_CROWD, despite the stored status


@pytest.mark.asyncio
async def test_completely_unavailable_returns_safe_result(db_session):
    service = _service(tomtom=FakeTomTom(fail=True), matching=FakeMatching(matched=False))
    repo = TrafficRepository(db_session)

    result = await service.resolve(repo, POINT)

    assert result.available is False
    assert result.status == "UNAVAILABLE"
    assert result.source is None
    assert result.congestion_score == 0.0
    assert result.confidence == 0.0
