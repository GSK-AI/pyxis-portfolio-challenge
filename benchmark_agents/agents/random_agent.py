import numpy as np


class RandomAgent:
    """Random agent that respects action masks from the environment."""

    def __init__(self):
        """Initialize the random agent."""
        self.env = None

    def set_env(self, env):
        """Set the environment for the agent."""
        self.env = env

    def _uses_investment_levels(self):
        """Check if investment levels are enabled."""
        if self.env is not None:
            unwrapped_env = getattr(self.env, "unwrapped", self.env)
            if (
                hasattr(unwrapped_env, 'investment_levels_config')
                and unwrapped_env.investment_levels_config is not None
                and unwrapped_env.investment_levels_config.enabled
            ):
                return True
        return False

    def _uses_interim_observations(self):
        """Check if interim trial observations are enabled (adds STOP action)."""
        if self.env is not None:
            unwrapped_env = getattr(self.env, "unwrapped", self.env)
            if (
                hasattr(unwrapped_env, 'interim_trial_observations_config')
                and unwrapped_env.interim_trial_observations_config is not None
                and unwrapped_env.interim_trial_observations_config.enabled
            ):
                return True
        return False

    def __call__(self, observation):
        """
        Take random actions that respect the environment's action masks.

        Args:
            observation: The observation from the environment.

        Returns:
            np.ndarray: Action array (0-4 for investment levels with STOP, 0-3 without, 0-1 for binary).

        """
        num_assets = len(observation["assets"])
        uses_levels = self._uses_investment_levels()
        uses_interim = self._uses_interim_observations()

        # Determine max action value
        # Without levels: 0-1 (binary)
        # With levels only: 0-3 (NONE, MINIMAL, STANDARD, ACCELERATED)
        # With levels + interim: 0-4 (adds STOP action)
        if uses_levels and uses_interim:
            max_action = 5  # 0-4 inclusive
        elif uses_levels:
            max_action = 4  # 0-3 inclusive
        else:
            max_action = 2  # 0-1 inclusive

        # Get action masks from environment if available
        if self.env is not None:
            try:
                # Get the unwrapped environment to access action_masks
                unwrapped_env = getattr(self.env, "unwrapped", self.env)
                action_masks = unwrapped_env.action_masks()

                # Create random actions respecting masks
                action = np.zeros(num_assets, dtype=int)
                for i in range(num_assets):
                    # Get valid actions from mask
                    mask = action_masks[i]
                    valid_actions = [j for j, allowed in enumerate(mask) if allowed]
                    if valid_actions:
                        action[i] = np.random.choice(valid_actions)
                    else:
                        action[i] = 0

                return action
            except (AttributeError, IndexError):
                # Fall back to pure random if masks not available
                pass

        # Fallback: pure random actions (binary for legacy)
        return np.random.randint(0, 2, size=num_assets)


def random_agent(observation):
    """
    Legacy function wrapper for backward compatibility.

    WARNING: This version does NOT respect action masks.
    Use RandomAgent class instead for proper mask support.
    """
    num_assets = len(observation["assets"])
    action = np.random.randint(0, 2, size=num_assets)
    return action


def get_upcoming_trial(trials_tuple: tuple[dict]) -> dict | None:
    """Get the upcoming trial from a tuple of trials."""
    upcoming_trial = None
    for trial in trials_tuple:
        if trial["time_remaining"] > 0:  # In Development
            upcoming_trial = trial
            break
    return upcoming_trial


class RandomAgentWithCashWrapper:
    """
    Random agent that respects both action masks and cash constraints.

    Takes random actions filtered by:
    1. Environment action masks (including negative eNPV masking)
    2. Cash availability constraints
    """

    def __init__(self):
        """Initialize the random agent with cash wrapper."""
        self.env = None

    def set_env(self, env):
        """Set the environment for the agent."""
        self.env = env

    def _get_investment_levels_config(self):
        """Get investment levels config if enabled, else None."""
        if self.env is not None:
            unwrapped_env = getattr(self.env, "unwrapped", self.env)
            if (
                hasattr(unwrapped_env, 'investment_levels_config')
                and unwrapped_env.investment_levels_config is not None
                and unwrapped_env.investment_levels_config.enabled
            ):
                return unwrapped_env.investment_levels_config
        return None

    def _uses_interim_observations(self):
        """Check if interim trial observations are enabled (adds STOP action)."""
        if self.env is not None:
            unwrapped_env = getattr(self.env, "unwrapped", self.env)
            if (
                hasattr(unwrapped_env, 'interim_trial_observations_config')
                and unwrapped_env.interim_trial_observations_config is not None
                and unwrapped_env.interim_trial_observations_config.enabled
            ):
                return True
        return False

    def __call__(self, observation):
        """
        Take random actions respecting masks and cash limits.

        Args:
            observation: The observation from the environment.

        Returns:
            np.ndarray: Action array (0-4 for investment levels with STOP, 0-3 without, 0-1 for binary).

        """
        # States
        # "Idle": 0,
        # "In Development": 1,
        # "On Market": 2,
        # "Failed": 3,
        # "Expired": 4,

        assets = observation["assets"]
        num_assets = len(assets)
        levels_config = self._get_investment_levels_config()
        uses_levels = levels_config is not None
        uses_interim = self._uses_interim_observations()

        # Get action masks from environment if available
        action_masks = None
        if self.env is not None:
            try:
                unwrapped_env = getattr(self.env, "unwrapped", self.env)
                action_masks = unwrapped_env.action_masks()
            except (AttributeError, IndexError):
                pass

        # Generate random actions respecting masks
        # Use proper mask-based selection to include STOP action when available
        if action_masks is not None:
            random_actions = np.zeros(num_assets, dtype=int)
            for i in range(num_assets):
                # Get valid actions from mask
                mask = action_masks[i]
                valid_actions = [j for j, allowed in enumerate(mask) if allowed]
                if valid_actions:
                    random_actions[i] = np.random.choice(valid_actions)
                else:
                    random_actions[i] = 0
        else:
            # Fallback to pure random (binary)
            random_actions = np.random.randint(0, 2, size=num_assets)

        # Calculate available cash
        available_cash = observation["cash"]
        for asset in assets:
            if asset["state"] == 1:  # In Development
                available_cash -= asset["cost_this_step"]

        # Filter by cash constraints
        # For investment levels, we need to estimate cost based on level
        final_actions = np.zeros_like(random_actions)

        # Build cost modifiers map from config
        cost_modifiers = {}
        if uses_levels:
            # Map action values to cost modifiers from config
            # Action 1 = MINIMAL, 2 = STANDARD, 3 = ACCELERATED, 4 = STOP (no cost)
            cost_modifiers = {
                1: levels_config.levels["minimal"].cost_modifier,
                2: levels_config.levels["standard"].cost_modifier,
                3: levels_config.levels["accelerated"].cost_modifier,
                4: 0.0,  # STOP has no cost
            }

        for i, asset in enumerate(assets):
            action = random_actions[i]

            # STOP action (4) can be applied to InDevelopment assets - no cash cost
            if action == 4 and asset["state"] == 1:
                final_actions[i] = action
                continue

            if asset["state"] != 0:  # not Idle (and not a STOP action)
                continue

            if action > 0 and action <= 3:  # Decided to invest at some level (1-3)
                trial = get_upcoming_trial(asset["trials"])
                if trial is None:
                    continue
                base_cost = trial["cost_remaining"] / trial["time_remaining"]

                # Estimate cost based on investment level
                if uses_levels:
                    cost_this_step = base_cost * cost_modifiers.get(action, 1.0)
                else:
                    cost_this_step = base_cost

                available_cash -= cost_this_step
                if available_cash < 0:
                    break
                final_actions[i] = action

        return final_actions


def random_agent_with_cash_wrapper(observation):
    """
    Legacy function wrapper for backward compatibility.

    WARNING: This version does NOT respect action masks.
    Use RandomAgentWithCashWrapper class instead for proper mask support.
    """
    # States
    # "Idle": 0,
    # "In Development": 1,
    # "On Market": 2,
    # "Failed": 3,
    # "Expired": 4,

    random_actions = random_agent(observation)
    available_cash = observation["cash"]
    assets = observation["assets"]
    for asset in assets:
        if asset["state"] == 1:  # In Development
            available_cash -= asset["cost_this_step"]

    final_actions = np.zeros_like(random_actions)

    for i, asset in enumerate(assets):
        if asset["state"] != 0:  # not Idle
            continue

        if random_actions[i] == 1:
            trial = get_upcoming_trial(asset["trials"])
            cost_this_step = trial["cost_remaining"] / trial["time_remaining"]
            available_cash -= cost_this_step
            if available_cash < 0:
                break
            final_actions[i] = 1  # Invest

    return final_actions
