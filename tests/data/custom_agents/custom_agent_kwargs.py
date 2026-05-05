import random

import numpy as np

rng = random.Random()
rng.seed(0)


def main(observation, **kwargs):
    """A dumb agent that takes random actions and extra kwargs."""
    num_assets = len(observation["assets"])
    action = np.zeros(num_assets)
    invest_idx = rng.randint(0, num_assets - 1)
    action[invest_idx] = 1.0
    return np.array(action)
