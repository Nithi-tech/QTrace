from app.optimization.clustering import VehicleInstance, fleet_aware_clusters


def _vehicle(capacity: float) -> VehicleInstance:
    return VehicleInstance(vehicle_type="Van", capacity=capacity, cost_per_km=10.0)


def test_every_destination_assigned_when_capacity_allows():
    points = [(13.04, 80.23), (13.05, 80.24), (12.99, 80.22), (13.00, 80.21)]
    demands = [20.0, 30.0, 40.0, 50.0]
    vehicles = [_vehicle(100.0), _vehicle(100.0)]

    result = fleet_aware_clusters(points, demands, vehicles, seed=1)

    assigned = [i for group in result.vehicle_assignments for i in group]
    assert sorted(assigned) == [0, 1, 2, 3]
    assert result.unassigned == []


def test_no_vehicle_exceeds_capacity():
    points = [(13.0 + 0.001 * i, 80.0) for i in range(6)]
    demands = [40.0] * 6  # total 240, two vehicles of 100 each = 200 total capacity
    vehicles = [_vehicle(100.0), _vehicle(100.0)]

    result = fleet_aware_clusters(points, demands, vehicles, seed=2)

    for group in result.vehicle_assignments:
        load = sum(demands[i] for i in group)
        assert load <= 100.0
    # 240 demand > 200 capacity: something must be unassigned rather than overloaded.
    assert result.unassigned != []


def test_unassigned_reported_when_total_demand_exceeds_fleet_capacity():
    points = [(13.0, 80.0), (13.01, 80.01)]
    demands = [80.0, 80.0]
    vehicles = [_vehicle(100.0)]  # only 100 capacity for 160 total demand

    result = fleet_aware_clusters(points, demands, vehicles, seed=3)

    load = sum(demands[i] for i in result.vehicle_assignments[0])
    assert load <= 100.0
    assert len(result.unassigned) == 1


def test_no_vehicles_marks_everything_unassigned():
    result = fleet_aware_clusters([(1.0, 1.0)], [10.0], vehicles=[])

    assert result.vehicle_assignments == []
    assert result.unassigned == [0]


def test_no_destinations_returns_empty_assignments():
    result = fleet_aware_clusters([], [], vehicles=[_vehicle(50.0)])

    assert result.vehicle_assignments == [[]]
    assert result.unassigned == []
