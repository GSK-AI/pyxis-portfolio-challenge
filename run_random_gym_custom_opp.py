"""Run a full episode with a random agent vs a custom callable opponent."""

import numpy as np
from pyxis_portfolio_challenge.environment import make_multi_agent_train_env
from pyxis_portfolio_challenge.agents import MultiAgentKnapsackAgent


def random_policy(obs, masks):
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
custom_opp = MultiAgentKnapsackAgent(agent_name="pharma_1", capacity=8)
trainer = env.train([None, custom_opp])

obs, info = trainer.reset(seed=42)
step = 0
done = False
while not done:
    masks = trainer.action_masks()
    action = random_policy(obs, masks)
    obs, reward, terminated, truncated, info = trainer.step(action)
    step += 1
    done = terminated or truncated
    print(f"Step {step}: reward={reward}")

print("Done.")
