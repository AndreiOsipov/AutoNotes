from utils import create_random_order_id


def test_same_seed_returns_same_result(fixed_seed):
    id1 = create_random_order_id(seed=fixed_seed)
    id2 = create_random_order_id(seed=fixed_seed)

    assert id1 == id2


def test_value_in_range():
    order_id = create_random_order_id()
    assert 1 <= order_id <= 1_000_000


