from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficIncident
from app.traffic.matcher import build_bounding_box, incidents_on_corridor

ORIGIN = Coordinate(latitude=12.90, longitude=77.50)
DESTINATION = Coordinate(latitude=12.90, longitude=77.60)

_ON_CORRIDOR = TrafficIncident(
    geometry={"type": "LineString", "coordinates": [[77.52, 12.90], [77.58, 12.90]]},
    incident_type="Accident",
    road_closed=False,
)
_FAR_AWAY = TrafficIncident(
    geometry={"type": "LineString", "coordinates": [[80.0, 20.0], [80.1, 20.1]]},
    incident_type="Accident",
    road_closed=False,
)
_NO_GEOMETRY = TrafficIncident(geometry=None, incident_type="Accident")


def test_build_bounding_box_covers_all_stops_and_expands_by_radius():
    stops = [Coordinate(latitude=12.9, longitude=77.5), Coordinate(latitude=13.0, longitude=77.7)]
    west, south, east, north = build_bounding_box(stops, radius_meters=1000)
    assert south < 12.9
    assert north > 13.0
    assert west < 77.5
    assert east > 77.7


def test_finds_incident_on_corridor():
    matched = incidents_on_corridor(ORIGIN, DESTINATION, [_ON_CORRIDOR], radius_meters=200)
    assert matched == [_ON_CORRIDOR]


def test_ignores_far_away_incident():
    matched = incidents_on_corridor(ORIGIN, DESTINATION, [_FAR_AWAY], radius_meters=200)
    assert matched == []


def test_skips_incidents_without_geometry():
    matched = incidents_on_corridor(ORIGIN, DESTINATION, [_NO_GEOMETRY], radius_meters=200)
    assert matched == []
