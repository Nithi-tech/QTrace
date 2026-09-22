import pytest

from app.models.optimization_job import OptimizationJob, OptimizationJobStatus
from app.repositories.tracking_repository import TrackingRepository
from app.schemas.routing import Coordinate
from app.services.exceptions import TrackingSessionNotFoundError
from app.services.tracking_service import TrackingService

# A short, straight "road" of geometry points a driver can be near or far from -
# matches the shape FleetOptimizationService actually stores (raw GeoJSON dict
# with (lon, lat) coordinate pairs, as OSRM returns it).
_ROUTE_GEOMETRY = {
    "coordinates": [[80.0, 13.0], [80.01, 13.0], [80.02, 13.0], [80.03, 13.0]],
}


def _job_with_two_vehicle_routes(db_session) -> OptimizationJob:
    job = OptimizationJob(
        input_dataset={},
        objective={"type": "MIN_DISTANCE"},
        algorithm="GREEDY_NN_2OPT",
        status=OptimizationJobStatus.COMPLETED,
        result={
            "vehicle_routes": [
                {
                    "vehicle_index": 0,
                    "vehicle_type": "Van",
                    "stop_names": ["Depot", "T Nagar", "Depot"],
                    "distance_meters": 5000.0,
                    "duration_seconds": 600.0,
                    "geometry": _ROUTE_GEOMETRY,
                },
                {
                    "vehicle_index": 2,  # not contiguous - vehicle 1 got no stops and was skipped
                    "vehicle_type": "Mini Truck",
                    "stop_names": ["Depot", "Adyar", "Depot"],
                    "distance_meters": 8000.0,
                    "duration_seconds": 900.0,
                    "geometry": _ROUTE_GEOMETRY,
                },
            ]
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture()
def service(db_session) -> TrackingService:
    return TrackingService(TrackingRepository(db_session))


def test_create_sessions_returns_one_code_per_vehicle_index(service, db_session):
    job = _job_with_two_vehicle_routes(db_session)

    codes = service.create_sessions_for_job(job.id, [0, 2])

    assert set(codes.keys()) == {0, 2}
    assert codes[0] != codes[2]
    assert all(len(code) == 6 for code in codes.values())


def test_get_assigned_route_matches_by_vehicle_index_not_list_position(service, db_session):
    """Regression-style test for the non-contiguous vehicle_index case (a
    skipped, unused vehicle instance) - the second route's vehicle_index is 2,
    not 1, and lookup must follow the field, not list position."""
    job = _job_with_two_vehicle_routes(db_session)
    codes = service.create_sessions_for_job(job.id, [0, 2])

    route = service.get_assigned_route(codes[2])

    assert route.vehicle_type == "Mini Truck"
    assert route.stop_names == ["Depot", "Adyar", "Depot"]
    assert len(route.geometry) == 4


def test_get_assigned_route_unknown_code_raises(service):
    with pytest.raises(TrackingSessionNotFoundError):
        service.get_assigned_route("NOPE99")


def test_status_with_no_pings_has_no_location_and_zero_distance(service, db_session):
    job = _job_with_two_vehicle_routes(db_session)
    codes = service.create_sessions_for_job(job.id, [0])

    status = service.get_status(codes[0])

    assert status.current_location is None
    assert status.distance_travelled_meters == 0.0
    assert status.is_off_route is False


def test_status_accumulates_distance_across_pings(service, db_session):
    job = _job_with_two_vehicle_routes(db_session)
    codes = service.create_sessions_for_job(job.id, [0])

    # Two pings ~1.11km apart (0.01 degrees longitude at the equator-ish latitude used here).
    service.record_ping(codes[0], Coordinate(latitude=13.0, longitude=80.0))
    service.record_ping(codes[0], Coordinate(latitude=13.0, longitude=80.01))

    status = service.get_status(codes[0])

    assert status.current_location == Coordinate(latitude=13.0, longitude=80.01)
    assert 1000.0 < status.distance_travelled_meters < 1200.0


def test_status_flags_off_route_when_far_from_planned_geometry(service, db_session):
    job = _job_with_two_vehicle_routes(db_session)
    codes = service.create_sessions_for_job(job.id, [0])

    # ~1 degree of latitude away (well over 100km) from every point on _ROUTE_GEOMETRY.
    service.record_ping(codes[0], Coordinate(latitude=14.0, longitude=80.0))

    status = service.get_status(codes[0])

    assert status.is_off_route is True
    assert status.off_route_distance_meters is not None
    assert status.off_route_distance_meters > 250.0


def test_status_not_off_route_when_near_planned_geometry(service, db_session):
    job = _job_with_two_vehicle_routes(db_session)
    codes = service.create_sessions_for_job(job.id, [0])

    # ~22m from the vertex at (13.0, 80.0) - the nearest-vertex approximation
    # (see tracking_service._min_distance_to_route_meters) only ever gets as
    # accurate as the geometry's point spacing; this fixture's synthetic
    # geometry is sparse (~1.1km between points) versus real OSRM output
    # (points every few meters to tens of meters), so the probe point must be
    # near an actual vertex, not merely near the line between two of them.
    service.record_ping(codes[0], Coordinate(latitude=13.0001, longitude=80.0001))

    status = service.get_status(codes[0])

    assert status.is_off_route is False


def test_fleet_overview_lists_every_vehicle_for_the_job(service, db_session):
    job = _job_with_two_vehicle_routes(db_session)
    service.create_sessions_for_job(job.id, [0, 2])

    overview = service.get_fleet_overview(job.id)

    assert overview.job_id == job.id
    assert {v.vehicle_index for v in overview.vehicles} == {0, 2}


def test_fleet_overview_unknown_job_raises(service):
    with pytest.raises(TrackingSessionNotFoundError):
        service.get_fleet_overview("does-not-exist")
