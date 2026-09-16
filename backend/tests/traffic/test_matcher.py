from app.schemas.routing import Coordinate
from app.traffic.matcher import build_bounding_box, match_pair_to_snapshots

ORIGIN = Coordinate(latitude=12.90, longitude=77.50)
DESTINATION = Coordinate(latitude=12.90, longitude=77.60)


class _FakeSegment:
    def __init__(self, geometry):
        self.geometry = geometry


class _FakeSnapshot:
    def __init__(self, congestion_score=0.5, confidence=0.8, status="LIVE"):
        self.congestion_score = congestion_score
        self.confidence = confidence
        self.status = status


_ON_CORRIDOR = (
    _FakeSnapshot(),
    _FakeSegment({"type": "LineString", "coordinates": [[77.52, 12.90], [77.58, 12.90]]}),
)
_FAR_AWAY = (
    _FakeSnapshot(),
    _FakeSegment({"type": "LineString", "coordinates": [[80.0, 20.0], [80.1, 20.1]]}),
)
_NO_GEOMETRY = (_FakeSnapshot(), _FakeSegment(None))


def test_build_bounding_box_covers_all_stops_and_expands_by_radius():
    stops = [Coordinate(latitude=12.9, longitude=77.5), Coordinate(latitude=13.0, longitude=77.7)]
    west, south, east, north = build_bounding_box(stops, radius_meters=1000)

    assert south < 12.9
    assert north > 13.0
    assert west < 77.5
    assert east > 77.7


def test_match_finds_intersecting_segment():
    matched = match_pair_to_snapshots(ORIGIN, DESTINATION, [_ON_CORRIDOR], radius_meters=200)
    assert len(matched) == 1


def test_match_ignores_far_away_segment():
    matched = match_pair_to_snapshots(ORIGIN, DESTINATION, [_FAR_AWAY], radius_meters=200)
    assert matched == []


def test_match_skips_segments_without_geometry():
    matched = match_pair_to_snapshots(ORIGIN, DESTINATION, [_NO_GEOMETRY], radius_meters=200)
    assert matched == []


def test_match_combines_multiple_candidates():
    matched = match_pair_to_snapshots(
        ORIGIN, DESTINATION, [_ON_CORRIDOR, _FAR_AWAY, _NO_GEOMETRY], radius_meters=200
    )
    assert len(matched) == 1
