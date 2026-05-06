"""Run a single episode using env.run() and save a replay file."""

import numpy as np
from pyxis_portfolio_challenge.environment import make_multi_agent_train_env


class RandomAgent:
    def __init__(self, agent_name, **kwargs):
        self.agent_name = agent_name
        self.env = None

    def set_env(self, env):
        self.env = env

    def __call__(self, obs):
        masks = self.env.action_masks(self.agent_name)
        inv_mask = masks["investments"]
        bd_mask = masks["bd_bids"]

        investments = (np.random.randint(0, 2, size=len(inv_mask)) * inv_mask).astype(np.int8)

        bd_bids = np.zeros(len(bd_mask), dtype=np.int64)
        for i, slot in enumerate(bd_mask):
            valid = np.where(slot)[0]
            if len(valid) > 0:
                bd_bids[i] = np.random.choice(valid)

        return {"investments": investments, "bd_bids": bd_bids}


env = make_multi_agent_train_env()
my_agent = RandomAgent(agent_name="pharma_0")

per_agent_reports, playthrough = env.run(
    [my_agent, "knapsack(c12)"],
    seed=42,
    flat_obs={0: True},
)

print("Per-agent report keys:", {k: len(v) for k, v in per_agent_reports.items()})

with open("replay.json", "w") as f:
    f.write(playthrough.model_dump_json(indent=2))

print("Replay saved to replay.json")
print(playthrough.model_dump_json(indent=2))
