import random

def create_random_order_id(seed=None, a=1, b=1000000):
    if seed:
        random.seed(seed)
    return random.randint(a, b)