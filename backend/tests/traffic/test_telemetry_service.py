from datetime import datetime, timedelta, timezone

import pytest

from app.models.traffic_segment import TrafficSegment
from app.repositories.traffic_repository import TrafficRepository
from app.routing.map_matching import RoadMatchingProvider
from app.schemas.map_matching import MatchedEdge, MatchedLeg, SnapResult, TraceMatchResult
from app.schemas.traffic import TrafficObservationInput
from app.traffic.telemetry_service import (
    MAX_PLAUSIBLE_SPEED_MPS,
    MAX_USABLE_ACCURACY_M,
    TrafficTelemetryService,
)

# Relative to real wall-clock time, not a fixed date, so freshness-window checks
# (which compare against datetime.now()) stay valid no matter when this test runs.
T0 = datetime.now(timezone.utc) - timedelta(minutes=1)


def _obs(lat, lon, speed_mps, accuracy_m=10.0, timestamp=T0) -> TrafficObservationInput:
    return TrafficObservationInput(
        latitude=lat, longitude=lon, speed_mps=speed_mps, accuracy_m=accuracy_m, timestamp=timestamp
    )


class FakeMatchingProvider(RoadMatchingProvider):
    def __init__(self, matched: bool = True, distance_meters: float = 500.0):
        self.matched = matched
        self.distance_meters = distance_meters

    async def match_trace(self, points):
        if not self.matched or len(points) < 2:
            return TraceMatchResult(matched=self.matched, legs=[])
        edges = [
            MatchedEdge(
                node_a=1,
                node_b=2,
                geometry={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                profile_speed_mps=13.9,
            ),
            MatchedEdge(
                node_a=2,
                node_b=3,
                geometry={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                profile_speed_mps=13.9,
            ),
        ]
        duration = (points[-1].timestamp - points[0].timestamp).total_seconds()
        return TraceMatchResult(
            matched=True,
            legs=[
                MatchedLeg(
                    edges=edges,
                    distance_meters=self.distance_meters,
                    observed_duration_seconds=duration,
                    observed_speed_mps=self.distance_meters / duration if duration > 0 else None,
                    start_timestamp=points[0].timestamp,
                    end_timestamp=points[-1].timestamp,
                )
            ],
        )

    async def snap_point(self, coordinate):
        return SnapResult(matched=False)


def _service(**overrides) -> TrafficTelemetryService:
    defaults = dict(
        matching_provider=FakeMatchingProvider(),
        min_observations=3,
        live_ttl_seconds=120,
        recent_ttl_seconds=300,
        expired_seconds=900,
    )
    defaults.update(overrides)
    return TrafficTelemetryService(**defaults)


@pytest.mark.asyncio
async def test_rejects_implausibly_fast_observation(db_session):
    service = _service()
    repo = TrafficRepository(db_session)
    result = await service.ingest_observations(
        repo, [_obs(12.97, 77.59, speed_mps=MAX_PLAUSIBLE_SPEED_MPS + 1)]
    )
    assert result.accepted == 0
    assert result.rejected == 1
    assert "exceeds plausible maximum" in result.rejection_reasons[0]


@pytest.mark.asyncio
async def test_rejects_poor_accuracy_observation(db_session):
    service = _service()
    repo = TrafficRepository(db_session)
    result = await service.ingest_observations(
        repo, [_obs(12.97, 77.59, speed_mps=10.0, accuracy_m=MAX_USABLE_ACCURACY_M + 1)]
    )
    assert result.accepted == 0
    assert "too poor to be usable" in result.rejection_reasons[0]


@pytest.mark.asyncio
async def test_rejects_future_timestamp(db_session):
    service = _service()
    repo = TrafficRepository(db_session)
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    result = await service.ingest_observations(repo, [_obs(12.97, 77.59, speed_mps=10.0, timestamp=future)])
    assert result.accepted == 0
    assert "future" in result.rejection_reasons[0]


@pytest.mark.asyncio
async def test_map_match_failure_is_reported_not_crashed_on(db_session):
    service = _service(matching_provider=FakeMatchingProvider(matched=False))
    repo = TrafficRepository(db_session)
    observations = [
        _obs(12.97, 77.59, speed_mps=10.0, timestamp=T0),
        _obs(12.98, 77.60, speed_mps=12.0, timestamp=T0 + timedelta(seconds=60)),
    ]
    result = await service.ingest_observations(repo, observations)
    assert result.accepted == 0
    assert result.rejected == 2
    assert any("map-matched" in reason for reason in result.rejection_reasons)


@pytest.mark.asyncio
async def test_successful_ingestion_creates_segments_observations_and_snapshot(db_session):
    service = _service()
    repo = TrafficRepository(db_session)
    observations = [
        _obs(12.97, 77.59, speed_mps=10.0, timestamp=T0),
        _obs(12.98, 77.60, speed_mps=14.0, timestamp=T0 + timedelta(seconds=60)),
    ]
    result = await service.ingest_observations(repo, observations)
    db_session.commit()

    assert result.accepted == 2
    assert result.rejected == 0
    assert result.segment_observations_stored == 2

    segment = db_session.query(TrafficSegment).filter_by(node_a=1, node_b=2).one()
    snapshot = repo.get_snapshot(segment.id)
    assert snapshot is not None
    assert snapshot.current_speed_mps == 12.0
    assert snapshot.status == "LIVE"
    assert snapshot.reference_speed_source == "PROVIDER"  # OSRM profile_speed_mps=13.9
    assert 0.0 < snapshot.confidence < 1.0
