"""Run evaluation over multiple episodes and print metrics."""

import json
import numpy as np
from pyxis_portfolio_challenge.environment.competition import evaluate


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


my_agent = RandomAgent(agent_name="pharma_0")

per_agent_reports, playthrough = evaluate(
    agents=[my_agent, "knapsack(c12)"],
    num_episodes=10,
    num_workers=1,
    flat_obs={0: True},
)

for agent_id, reports in per_agent_reports.items():
    print(f"\n{'=' * 60}")
    print(f"Agent: {agent_id}")
    print(f"{'=' * 60}")
    for group in reports:
        for group_name, metrics in group.items():
            print(f"\n  {group_name}:")
            for metric in metrics:
                print(f"    {json.dumps(metric, indent=6, default=str)}")

