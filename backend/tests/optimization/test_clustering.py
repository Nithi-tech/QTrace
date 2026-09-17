import math

from app.optimization.clustering import VehicleInstance, fleet_aware_clusters

DEPOT = (13.0, 80.0)


def _bearing(depot: tuple[float, float], point: tuple[float, float]) -> float:
    return math.degrees(math.atan2(point[1] - depot[1], point[0] - depot[0])) % 360.0


def _vehicle(capacity: float) -> VehicleInstance:
    return VehicleInstance(vehicle_type="Van", capacity=capacity, cost_per_km=10.0)


def test_every_destination_assigned_when_capacity_allows():
    points = [(13.04, 80.23), (13.05, 80.24), (12.99, 80.22), (13.00, 80.21)]
    demands = [20.0, 30.0, 40.0, 50.0]
    vehicles = [_vehicle(100.0), _vehicle(100.0)]

    result = fleet_aware_clusters(points, demands, vehicles, depot=DEPOT)

    assigned = [i for group in result.vehicle_assignments for i in group]
    assert sorted(assigned) == [0, 1, 2, 3]
    assert result.unassigned == []


def test_no_vehicle_exceeds_capacity():
    points = [(13.0 + 0.001 * i, 80.0) for i in range(6)]
    demands = [40.0] * 6  # total 240, two vehicles of 100 each = 200 total capacity
    vehicles = [_vehicle(100.0), _vehicle(100.0)]

    result = fleet_aware_clusters(points, demands, vehicles, depot=DEPOT)

    for group in result.vehicle_assignments:
        load = sum(demands[i] for i in group)
        assert load <= 100.0
    # 240 demand > 200 capacity: something must be unassigned rather than overloaded.
    assert result.unassigned != []


def test_unassigned_reported_when_total_demand_exceeds_fleet_capacity():
    points = [(13.0, 80.0), (13.01, 80.01)]
    demands = [80.0, 80.0]
    vehicles = [_vehicle(100.0)]  # only 100 capacity for 160 total demand

    result = fleet_aware_clusters(points, demands, vehicles, depot=DEPOT)

    load = sum(demands[i] for i in result.vehicle_assignments[0])
    assert load <= 100.0
    assert len(result.unassigned) == 1


def test_no_vehicles_marks_everything_unassigned():
    result = fleet_aware_clusters([(1.0, 1.0)], [10.0], vehicles=[], depot=DEPOT)

    assert result.vehicle_assignments == []
    assert result.unassigned == [0]


def test_no_destinations_returns_empty_assignments():
    result = fleet_aware_clusters([], [], vehicles=[_vehicle(50.0)], depot=DEPOT)

    assert result.vehicle_assignments == [[]]
    assert result.unassigned == []


def test_each_vehicle_serves_a_contiguous_directional_wedge_from_the_depot():
    """Regression test for the reported issue: routes must not criss-cross -
    each vehicle's stops should all lie in roughly one compass direction from
    the depot, not scattered across opposite sides of it."""
    depot = (13.0827, 80.2707)
    # North cluster (Perambur, Anna Nagar) and south cluster (Adyar, Velachery,
    # Tambaram), interleaved in the destinations list so index order can't
    # accidentally produce a good grouping on its own.
    points = [
        (13.0418, 80.2341),  # T Nagar - south-west
        (13.1141, 80.2445),  # Perambur - north
        (13.0012, 80.2565),  # Adyar - south
        (13.0850, 80.2101),  # Anna Nagar - north-west
        (12.9791, 80.2183),  # Velachery - south
        (12.9249, 80.1000),  # Tambaram - far south
    ]
    demands = [15.0, 12.0, 20.0, 25.0, 10.0, 18.0]
    vehicles = [_vehicle(60.0), _vehicle(60.0)]

    result = fleet_aware_clusters(points, demands, vehicles, depot=depot)

    assert result.unassigned == []
    for group in result.vehicle_assignments:
        if not group:
            continue
        bearings = [_bearing(depot, points[i]) for i in group]
        # A contiguous angular wedge spans meaningfully less than a half-circle
        # here; a criss-crossing assignment (e.g. mixing the north and south
        # groups) would span close to 180 degrees.
        assert max(bearings) - min(bearings) < 120.0
