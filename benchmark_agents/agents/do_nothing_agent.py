import numpy as np


def do_nothing_agent(observation):
    """An agent that does nothing."""
    num_assets = len(observation["assets"])
    action = np.zeros(num_assets)
    return action
