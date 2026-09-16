from app.optimization.two_opt import _order_cost, two_opt_refine

# Hand-checkable: 0->1->2->3 costs 10+1+10=21; 0->2->1->3 costs 1+1+1=3 (optimal).
_MATRIX = [
    [0, 10, 1, 999],
    [10, 0, 1, 1],
    [1, 1, 0, 10],
    [999, 1, 10, 0],
]


def test_fixes_a_crossed_path_between_fixed_endpoints():
    order = two_opt_refine(_MATRIX, [0, 1, 2, 3], fixed_end=True)

    assert order == [0, 2, 1, 3]
    assert _order_cost(_MATRIX, order) == 3


def test_never_worsens_an_already_optimal_route():
    order = two_opt_refine(_MATRIX, [0, 2, 1, 3], fixed_end=True)

    assert _order_cost(_MATRIX, order) == 3


def test_endpoints_are_never_moved():
    order = two_opt_refine(_MATRIX, [0, 1, 2, 3], fixed_end=True)

    assert order[0] == 0
    assert order[-1] == 3


def test_short_routes_are_returned_unchanged():
    matrix = [[0, 1, 2], [1, 0, 1], [2, 1, 0]]

    order = two_opt_refine(matrix, [0, 1, 2], fixed_end=True)

    assert order == [0, 1, 2]


def test_free_end_can_be_reordered():
    # Same costs, but the last stop (2) is a real destination, not a fixed depot return.
    order = two_opt_refine(_MATRIX, [0, 1, 2, 3], fixed_end=False)

    assert _order_cost(_MATRIX, order) <= _order_cost(_MATRIX, [0, 1, 2, 3])
