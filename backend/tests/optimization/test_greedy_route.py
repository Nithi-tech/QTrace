from app.optimization.greedy_route import nearest_neighbor_order


def test_visits_nearest_unvisited_stop_each_step():
    # depot(0) -> nearest is 2 (dist 1) -> from 2 nearest remaining is 1 (dist 2) -> end at depot.
    matrix = [
        [0, 10, 1, 999],
        [10, 0, 2, 1],
        [1, 2, 0, 10],
        [999, 1, 10, 0],
    ]

    order = nearest_neighbor_order(matrix, start_index=0, stop_indices=[1, 2], end_index=0)

    assert order == [0, 2, 1, 0]


def test_no_stops_returns_just_start_and_end():
    matrix = [[0, 5], [5, 0]]

    order = nearest_neighbor_order(matrix, start_index=0, stop_indices=[], end_index=0)

    assert order == [0, 0]


def test_without_end_index_stops_at_last_visited_stop():
    matrix = [
        [0, 1, 5],
        [1, 0, 1],
        [5, 1, 0],
    ]

    order = nearest_neighbor_order(matrix, start_index=0, stop_indices=[1, 2])

    assert order == [0, 1, 2]
