from app.optimization.qpso import QPSOConfig, QPSOSolver


def test_zero_intermediate_stops_skips_search():
    solver = QPSOSolver()
    matrix = [[0, 5], [5, 0]]

    result = solver.optimize(matrix, num_intermediate_stops=0)

    assert result.order == []
    assert result.total_cost == 5
    assert result.iterations_run == 0
    assert result.converged is True


def test_single_intermediate_stop_skips_search():
    solver = QPSOSolver()
    # origin(0) -> stop(1) -> destination(2)
    matrix = [
        [0, 4, 999],
        [4, 0, 6],
        [999, 6, 0],
    ]

    result = solver.optimize(matrix, num_intermediate_stops=1)

    assert result.order == [0]
    assert result.total_cost == 10
    assert result.iterations_run == 0


def test_two_intermediate_stops_finds_hand_checkable_optimum():
    # origin(0), stopA(1), stopB(2), destination(3).
    # Visiting B then A costs 1+1+1=3; visiting A then B costs 10+1+10=21.
    matrix = [
        [0, 10, 1, 999],
        [10, 0, 1, 1],
        [1, 1, 0, 10],
        [999, 1, 10, 0],
    ]
    solver = QPSOSolver(QPSOConfig(population_size=20, max_iterations=60, seed=42))

    result = solver.optimize(matrix, num_intermediate_stops=2)

    assert result.order == [1, 0]
    assert result.total_cost == 3
    assert result.iterations_run > 0


def test_same_seed_is_reproducible():
    matrix = [
        [0, 10, 1, 999],
        [10, 0, 1, 1],
        [1, 1, 0, 10],
        [999, 1, 10, 0],
    ]
    config = QPSOConfig(population_size=15, max_iterations=40, seed=7)

    result_a = QPSOSolver(config).optimize(matrix, num_intermediate_stops=2)
    result_b = QPSOSolver(config).optimize(matrix, num_intermediate_stops=2)

    assert result_a.order == result_b.order
    assert result_a.cost_history == result_b.cost_history
