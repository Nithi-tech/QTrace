from datetime import datetime, timedelta, timezone

from app.models.traffic_observation import TrafficObservation
from app.models.traffic_segment import TrafficSegment
from app.models.traffic_snapshot import TrafficSnapshot
from app.repositories.traffic_repository import TrafficRepository
from app.traffic.retention import purge_expired_traffic_data

NOW = datetime.now(timezone.utc)


def _segment(db_session) -> TrafficSegment:
    segment = TrafficSegment(node_a=1, node_b=2, geometry=None, profile_speed_mps=13.9, created_at=NOW)
    db_session.add(segment)
    db_session.flush()
    return segment


def test_purges_only_observations_and_snapshots_older_than_retention(db_session):
    segment = _segment(db_session)

    old_observation = TrafficObservation(
        segment_id=segment.id,
        observed_speed_mps=10.0,
        accuracy_m=10.0,
        recorded_at=NOW - timedelta(days=10),
        created_at=NOW - timedelta(days=10),
    )
    recent_observation = TrafficObservation(
        segment_id=segment.id,
        observed_speed_mps=12.0,
        accuracy_m=10.0,
        recorded_at=NOW - timedelta(hours=1),
        created_at=NOW - timedelta(hours=1),
    )
    old_snapshot = TrafficSnapshot(
        provider="QTRACE_CROWD",
        road_or_route_info={"segment_id": segment.id},
        segment_id=segment.id,
        captured_at=NOW - timedelta(days=40),
    )
    db_session.add_all([old_observation, recent_observation, old_snapshot])
    db_session.commit()

    repository = TrafficRepository(db_session)
    result = purge_expired_traffic_data(repository, now=NOW, raw_retention_days=7, snapshot_retention_days=30)

    assert result.observations_deleted == 1
    assert result.snapshots_deleted == 1
    remaining_observations = db_session.query(TrafficObservation).all()
    assert len(remaining_observations) == 1
    assert remaining_observations[0].id == recent_observation.id
    assert db_session.query(TrafficSnapshot).count() == 0


def test_nothing_to_purge_returns_zero_counts(db_session):
    repository = TrafficRepository(db_session)
    result = purge_expired_traffic_data(repository, now=NOW, raw_retention_days=7, snapshot_retention_days=30)
    assert result.observations_deleted == 0
    assert result.snapshots_deleted == 0
