"""Custom random bot that takes random actions according to action masks."""

import numpy as np


class MyBot:
    def __init__(self, agent_name: str, **kwargs):
        self.agent_name = agent_name
        self.env = None

    def set_env(self, env):
        self.env = env

    def __call__(self, obs) -> dict:
        masks = self.env.action_masks(self.agent_name)
        inv_mask = masks["investments"]
        bd_mask = masks["bd_bids"]

        # Random binary investments, masked to only valid (Idle) assets
        investments = (np.random.randint(0, 2, size=len(inv_mask)) * inv_mask).astype(
            np.int8
        )

        # Random BD bids, picking uniformly from valid bid levels per slot
        bd_bids = np.zeros(len(bd_mask), dtype=np.int64)
        for i, slot in enumerate(bd_mask):
            valid = np.where(slot)[0]
            if len(valid) > 0:
                bd_bids[i] = np.random.choice(valid)

        return {"investments": investments, "bd_bids": bd_bids}


def create_agent(agent_name: str, **kwargs):
    return MyBot(agent_name, **kwargs)
