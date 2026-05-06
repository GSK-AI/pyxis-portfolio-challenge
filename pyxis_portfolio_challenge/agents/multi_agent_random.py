"""Random agent for multi-agent competitive environment."""

import numpy as np


class MultiAgentRandomAgent:
    """
    Random agent that respects action masks in the multi-agent environment.

    Selects uniformly random valid actions for both investments and BD bids.
    """

    def __init__(self, agent_name: str, *, env=None):
        """
        Initialise multi-agent random agent.

        Parameters
        ----------
        agent_name : str
            The agent identifier in the multi-agent environment
            (e.g. ``"pharma_0"``).
        env : MultiAgentInvestmentGameEnv | None
            Environment reference. Can be ``None`` if ``set_env`` is
            called before the first ``__call__``.

        """
        self.agent_name = agent_name
        self.env = env

    def set_env(self, env):
        """Set or update the environment reference."""
        self.env = env

    def __call__(self, obs) -> dict:
        """
        Select random valid actions.

        Parameters
        ----------
        obs
            Observation from the environment (unused — actions are
            mask-based).

        Returns
        -------
        dict
            Action dict with ``"investments"`` and ``"bd_bids"`` arrays.

        """
        masks = self.env.action_masks(self.agent_name)
        inv_mask = masks["investments"]
        bd_mask = masks["bd_bids"]

        investments = np.zeros(self.env.max_num_assets, dtype=np.int64)
        for i, m in enumerate(inv_mask):
            if isinstance(m, list):
                valid = [j for j, ok in enumerate(m) if ok]
                investments[i] = np.random.choice(valid) if valid else 0
            else:
                investments[i] = np.random.randint(0, 2) if m else 0

        bd_bids = np.zeros(self.env.bd_max_slots, dtype=np.int64)
        for i, slot in enumerate(bd_mask):
            valid = [j for j, ok in enumerate(slot) if ok]
            bd_bids[i] = np.random.choice(valid) if valid else 0

        return {"investments": investments, "bd_bids": bd_bids}
