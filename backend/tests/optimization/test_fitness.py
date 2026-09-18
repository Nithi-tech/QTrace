from app.optimization.fitness import FitnessWeights, build_cost_matrix


def test_distance_and_duration_are_min_max_normalized_before_weighting():
    distances = [[0, 100], [100, 0]]
    durations = [[0, 10], [10, 0]]
    traffic = [[0, 0], [0, 0]]
    weights = FitnessWeights(distance_weight=1.0, time_weight=0.0, traffic_weight=0.0)

    cost = build_cost_matrix(distances, durations, traffic, weights)

    assert cost == [[0.0, 1.0], [1.0, 0.0]]


def test_traffic_matrix_is_used_as_is_without_renormalization():
    distances = [[0, 0], [0, 0]]
    durations = [[0, 0], [0, 0]]
    traffic = [[0.0, 0.9], [0.9, 0.0]]
    weights = FitnessWeights(distance_weight=0.0, time_weight=0.0, traffic_weight=1.0)

    cost = build_cost_matrix(distances, durations, traffic, weights)

    assert cost == [[0.0, 0.9], [0.9, 0.0]]


def test_weights_combine_all_three_signals():
    distances = [[0, 100], [100, 0]]
    durations = [[0, 50], [50, 0]]
    traffic = [[0.0, 0.5], [0.5, 0.0]]
    weights = FitnessWeights(distance_weight=0.4, time_weight=0.4, traffic_weight=0.2)

    cost = build_cost_matrix(distances, durations, traffic, weights)

    expected = 0.4 * 1.0 + 0.4 * 1.0 + 0.2 * 0.5
    assert cost[0][1] == expected
