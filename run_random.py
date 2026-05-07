"""Run a full episode with random agents using the PettingZoo API."""

import numpy as np

from pyxis_portfolio_challenge.environment import make_multi_agent_train_env


def random_policy(obs, masks):
    inv_mask = masks["investments"]
    bd_mask = masks["bd_bids"]

    investments = (np.random.randint(0, 2, size=len(inv_mask)) * inv_mask).astype(
        np.int8
    )

    bd_bids = np.zeros(len(bd_mask), dtype=np.int64)
    for i, slot in enumerate(bd_mask):
        valid = np.where(slot)[0]
        if len(valid) > 0:
            bd_bids[i] = np.random.choice(valid)

    return {"investments": investments, "bd_bids": bd_bids}


env = make_multi_agent_train_env()
obs, infos = env.reset(seed=42)

step = 0
done = False
while not done:
    actions = {}
    for agent_id in env.agents:
        masks = env.action_masks(agent_id)
        actions[agent_id] = random_policy(obs[agent_id], masks)
    obs, rewards, terms, truncs, infos = env.step(actions)
    step += 1
    done = any(terms.values()) or any(truncs.values())
    print(f"Step {step}: rewards={rewards}")

print("Done.")
