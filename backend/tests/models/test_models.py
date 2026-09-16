from app.models import DeliveryStop, Depot, OptimizationJob, OptimizationJobStatus, Route, RouteStop, Vehicle


def test_depot_and_vehicle_persist(db_session):
    depot = Depot(name="Main Depot", latitude=12.97, longitude=77.59, operating_constraints={})
    vehicle = Vehicle(fleet_id="fleet-1", capacity=500.0, operating_constraints={})

    db_session.add_all([depot, vehicle])
    db_session.commit()

    assert depot.id is not None
    assert vehicle.id is not None
    assert vehicle.capacity == 500.0


def test_route_preserves_stop_sequence(db_session):
    vehicle = Vehicle(fleet_id="fleet-1", capacity=500.0, operating_constraints={})
    stop_a = DeliveryStop(latitude=1.0, longitude=1.0)
    stop_b = DeliveryStop(latitude=2.0, longitude=2.0)
    db_session.add_all([vehicle, stop_a, stop_b])
    db_session.flush()

    route = Route(
        vehicle_id=vehicle.id,
        distance_meters=1200.0,
        duration_seconds=300.0,
        optimization_metadata={},
    )
    db_session.add(route)
    db_session.flush()

    db_session.add_all(
        [
            RouteStop(route_id=route.id, delivery_stop_id=stop_b.id, sequence=1),
            RouteStop(route_id=route.id, delivery_stop_id=stop_a.id, sequence=0),
        ]
    )
    db_session.commit()
    db_session.refresh(route)

    assert [s.delivery_stop_id for s in route.stops] == [stop_a.id, stop_b.id]


def test_optimization_job_defaults_to_queued(db_session):
    job = OptimizationJob(input_dataset={}, objective={}, algorithm="QPSO")
    db_session.add(job)
    db_session.commit()

    assert job.status == OptimizationJobStatus.QUEUED
