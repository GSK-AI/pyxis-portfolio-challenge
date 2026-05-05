"""
Greedy 'invest in everything' agent for multi-agent environment.

Invests in every idle asset with positive eNPV, ranked by eNPV descending,
respecting cash budget and a max concurrent investment cap.
Bids on BD assets at 50% eNPV if affordable.
"""

import numpy as np

from aiml_pyxis_investment_game.game.asset import AssetState


class MultiAgentGreedyAgent:
    """Invests in everything affordable with positive eNPV, up to a capacity cap."""

    def __init__(self, env, agent_name: str, max_concurrent: int = 10):
        self.env = env
        self.agent_name = agent_name
        self.max_num_assets = env.max_num_assets
        self.bd_max_slots = env.bd_max_slots
        self.max_concurrent = max_concurrent

    def set_env(self, env):
        self.env = env
        self.max_num_assets = env.max_num_assets
        self.bd_max_slots = env.bd_max_slots

    def __call__(self, observation) -> dict:
        portfolio = self.env.agent_portfolios[self.agent_name]
        masks = self.env.action_masks(self.agent_name)
        asset_order = self.env._asset_id_orders[self.agent_name]

        investments = np.zeros(self.max_num_assets, dtype=np.int64)
        bd_bids = np.zeros(self.bd_max_slots, dtype=np.int64)

        # Count current in-dev
        n_in_dev = 0
        for asset in portfolio.assets.values():
            if asset.state == AssetState.InDevelopment:
                n_in_dev += 1

        remaining_slots = self.max_concurrent - n_in_dev

        # Collect investable idle assets with positive eNPV
        candidates = []
        inv_mask = masks["investments"]

        for i, asset_id in enumerate(asset_order):
            if asset_id is None or asset_id not in portfolio.assets:
                continue
            # Check mask — handle both MultiBinary and MultiDiscrete formats
            if isinstance(inv_mask, list) and isinstance(inv_mask[i], list):
                can_invest = any(inv_mask[i][1:])
            else:
                can_invest = bool(inv_mask[i])
            if not can_invest:
                continue

            asset = portfolio.assets[asset_id]
            if asset.enpv > 0:
                candidates.append((i, asset.enpv))

        # Sort by eNPV descending, invest in top N (no cash management)
        candidates.sort(key=lambda x: -x[1])
        for idx, enpv in candidates:
            if remaining_slots <= 0:
                break
            investments[idx] = 1
            remaining_slots -= 1

        # BD: bid at level 5 (50% eNPV) on any available BD asset if affordable
        bd_masks = masks["bd_bids"]
        for slot_idx in range(self.bd_max_slots):
            slot_mask = bd_masks[slot_idx]
            for level in range(min(5, len(slot_mask) - 1), 0, -1):
                if slot_mask[level]:
                    bd_bids[slot_idx] = level
                    break

        # Default pricing: standard level (index 2) for all assets
        pricing = np.full(self.max_num_assets, 2, dtype=np.int64)
        return {"investments": investments, "bd_bids": bd_bids, "pricing": pricing}
