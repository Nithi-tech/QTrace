from datetime import datetime, timezone

from app.repositories.traffic_repository import TrafficRepository
from app.schemas.routing import Coordinate
from app.traffic.matrix_service import TrafficMatrixService

ORIGIN = Coordinate(latitude=12.90, longitude=77.50)
DESTINATION = Coordinate(latitude=12.90, longitude=77.60)


def _seed_segment_with_snapshot(db_session, *, congestion_score, confidence, status):
    from app.models.traffic_segment import TrafficSegment
    from app.models.traffic_snapshot import TrafficSnapshot

    now = datetime.now(timezone.utc)
    segment = TrafficSegment(
        node_a=1,
        node_b=2,
        geometry={"type": "LineString", "coordinates": [[77.52, 12.90], [77.58, 12.90]]},
        profile_speed_mps=15.0,
        created_at=now,
    )
    db_session.add(segment)
    db_session.flush()
    snapshot = TrafficSnapshot(
        provider="qtrace_telemetry",
        road_or_route_info={},
        captured_at=now,
        segment_id=segment.id,
        current_speed_mps=5.0,
        reference_speed_mps=15.0,
        congestion_score=congestion_score,
        observation_count=5,
        confidence=confidence,
        status=status,
    )
    db_session.add(snapshot)
    db_session.commit()
    return segment, snapshot


def test_disabled_returns_baseline_without_querying(db_session):
    service = TrafficMatrixService(corridor_radius_meters=200)
    repo = TrafficRepository(db_session)

    result = service.get_traffic_matrix(repo, [ORIGIN, DESTINATION], enabled=False)

    assert result.status.enabled is False
    assert result.status.available is False
    assert result.matrix == [[0.0, 0.0], [0.0, 0.0]]


def test_no_data_in_area_reports_unavailable_not_zero_traffic(db_session):
    service = TrafficMatrixService(corridor_radius_meters=200)
    repo = TrafficRepository(db_session)

    result = service.get_traffic_matrix(repo, [ORIGIN, DESTINATION], enabled=True)

    assert result.status.enabled is True
    assert result.status.available is False
    assert result.status.live is False
    assert result.status.source == "unavailable"


def test_matched_segment_produces_confidence_weighted_score(db_session):
    _seed_segment_with_snapshot(db_session, congestion_score=0.8, confidence=0.5, status="LIVE")
    service = TrafficMatrixService(corridor_radius_meters=200)
    repo = TrafficRepository(db_session)

    result = service.get_traffic_matrix(repo, [ORIGIN, DESTINATION], enabled=True)

    assert result.status.available is True
    assert result.status.live is True
    assert result.status.source == "qtrace_telemetry"
    # effective score = congestion_score * confidence = 0.8 * 0.5
    assert result.matrix[0][1] == 0.4
    assert result.matrix[1][0] == 0.4
    assert result.status.confidence == 0.5


def test_stale_segment_reports_available_but_not_live(db_session):
    _seed_segment_with_snapshot(db_session, congestion_score=0.3, confidence=0.2, status="STALE")
    service = TrafficMatrixService(corridor_radius_meters=200)
    repo = TrafficRepository(db_session)

    result = service.get_traffic_matrix(repo, [ORIGIN, DESTINATION], enabled=True)

    assert result.status.available is True
    assert result.status.live is False
