from datetime import datetime, timedelta, timezone

from app.models.traffic_observation import TrafficObservation
from app.models.traffic_segment import TrafficSegment
from app.repositories.traffic_repository import TrafficRepository
from app.traffic.retention import purge_expired_traffic_data

NOW = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)


def _seed(db_session):
    segment = TrafficSegment(node_a=1, node_b=2, geometry=None, profile_speed_mps=10.0, created_at=NOW)
    db_session.add(segment)
    db_session.flush()

    old_observation = TrafficObservation(
        segment_id=segment.id,
        observed_speed_mps=5.0,
        accuracy_m=10.0,
        recorded_at=NOW - timedelta(days=10),
        created_at=NOW - timedelta(days=10),
    )
    recent_observation = TrafficObservation(
        segment_id=segment.id,
        observed_speed_mps=6.0,
        accuracy_m=10.0,
        recorded_at=NOW - timedelta(hours=1),
        created_at=NOW - timedelta(hours=1),
    )
    db_session.add_all([old_observation, recent_observation])
    db_session.commit()
    return segment


def test_purge_deletes_only_observations_older_than_raw_retention(db_session):
    _seed(db_session)
    repo = TrafficRepository(db_session)

    observations_deleted, _ = purge_expired_traffic_data(
        repo, now=NOW, raw_retention_days=7, snapshot_retention_days=30
    )
    db_session.commit()

    assert observations_deleted == 1
    remaining = db_session.query(TrafficObservation).all()
    assert len(remaining) == 1
    assert remaining[0].observed_speed_mps == 6.0


def test_purge_is_a_no_op_when_nothing_is_old_enough(db_session):
    _seed(db_session)
    repo = TrafficRepository(db_session)

    observations_deleted, _ = purge_expired_traffic_data(
        repo, now=NOW, raw_retention_days=365, snapshot_retention_days=365
    )

    assert observations_deleted == 0
