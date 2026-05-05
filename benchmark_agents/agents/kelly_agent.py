"""
Kelly Criterion Agent for the Investment Game.

Uses Kelly criterion to determine optimal position sizing (investment level)
based on estimated probability of success and expected payoff.
"""

import numpy as np


class KellyAgent:
    """
    Kelly Criterion agent that sizes positions based on edge and odds.

    Maps Kelly fraction to investment levels:
    - Kelly < 0: Don't invest (NONE)
    - Kelly 0-20%: MINIMAL (conservative)
    - Kelly 20-50%: STANDARD
    - Kelly > 50%: ACCELERATED (aggressive)

    Also respects capacity constraints and can use STOP based on interim signals.
    """

    def __init__(
        self,
        kelly_fraction: float = 0.5,  # Use half-Kelly for safety
        capacity_limit: float = 4.0,  # Base capacity
        stop_threshold: float = 0.3,  # STOP if interim signal below this
        use_stop: bool = True,
    ):
        """
        Initialize Kelly agent.

        Args:
            kelly_fraction: Fraction of full Kelly to use (0.5 = half-Kelly)
            capacity_limit: Maximum capacity before penalties
            stop_threshold: STOP trials with interim signal below this
            use_stop: Whether to use STOP action

        """
        self.env = None
        self.kelly_fraction = kelly_fraction
        self.capacity_limit = capacity_limit
        self.stop_threshold = stop_threshold
        self.use_stop = use_stop

    def set_env(self, env):
        """Set the environment for the agent."""
        self.env = env

    def _get_config(self):
        """Get investment levels config from environment."""
        if self.env is not None:
            unwrapped = getattr(self.env, "unwrapped", self.env)
            if hasattr(unwrapped, 'investment_levels_config'):
                return unwrapped.investment_levels_config
        return None

    def _uses_interim_observations(self):
        """Check if interim trial observations are enabled."""
        if self.env is not None:
            unwrapped = getattr(self.env, "unwrapped", self.env)
            if (
                hasattr(unwrapped, 'interim_trial_observations_config')
                and unwrapped.interim_trial_observations_config is not None
                and unwrapped.interim_trial_observations_config.enabled
            ):
                return True
        return False

    def _calculate_kelly_fraction(self, asset: dict) -> float:
        """
        Calculate Kelly fraction for an asset.

        Kelly formula: f* = (p * b - q) / b
        where:
            p = probability of success (PTRS)
            q = probability of failure (1 - p)
            b = odds (net return if successful)

        Args:
            asset: Asset dictionary from observation

        Returns:
            Kelly fraction (can be negative if negative EV)

        """
        # Get PTRS estimate
        # In the observation, we need to find the current trial's PTRS
        trials = asset.get("trials", ())

        # Find the upcoming trial (first one with time_remaining > 0 or not started)
        ptrs = 0.5  # Default
        cost_remaining = 0
        time_remaining = 1

        for trial in trials:
            if trial.get("time_remaining", 0) > 0 or trial.get("cost_remaining", 0) > 0:
                ptrs = trial.get("ptrs", 0.5)
                cost_remaining = trial.get("cost_remaining", 1)
                time_remaining = max(trial.get("time_remaining", 1), 1)
                break

        # Get eNPV for expected return
        enpv = asset.get("enpv", 0)

        # Estimate cost for this phase
        cost_per_step = cost_remaining / time_remaining if time_remaining > 0 else cost_remaining

        # Rough estimate of total remaining cost (current phase)
        total_cost = cost_remaining

        if total_cost <= 0:
            return 0.0

        # Calculate odds: net return if successful
        # b = (enpv - cost) / cost = enpv/cost - 1
        odds = max(enpv / total_cost - 1, 0.01)  # Avoid division issues

        # Kelly fraction: f* = (p * b - q) / b
        p = ptrs
        q = 1 - p
        kelly = (p * odds - q) / odds

        # Apply fractional Kelly
        kelly *= self.kelly_fraction

        return kelly

    def _kelly_to_level(self, kelly: float) -> int:
        """
        Map Kelly fraction to investment level.

        Args:
            kelly: Kelly fraction

        Returns:
            Investment level (0=NONE, 1=MINIMAL, 2=STANDARD, 3=ACCELERATED)

        """
        if kelly < 0:
            return 0  # NONE - negative EV
        elif kelly < 0.15:
            return 1  # MINIMAL - low edge
        elif kelly < 0.40:
            return 2  # STANDARD - moderate edge
        else:
            return 3  # ACCELERATED - high edge

    def _should_stop(self, asset: dict) -> bool:
        """
        Decide whether to STOP a trial based on interim signal.

        Args:
            asset: Asset dictionary

        Returns:
            True if should STOP

        """
        if not self.use_stop:
            return False

        # Check if asset is in development
        if asset.get("state") != 1:  # 1 = InDevelopment
            return False

        # Get interim signal if available
        interim_signal = asset.get("interim_signal", None)
        if interim_signal is None:
            return False

        # STOP if signal is below threshold
        return interim_signal < self.stop_threshold

    def _estimate_capacity_usage(self, level: int) -> int:
        """Get capacity cost for investment level."""
        capacity_costs = {0: 0, 1: 1, 2: 2, 3: 4, 4: 0}  # 4 = STOP
        return capacity_costs.get(level, 2)

    def __call__(self, observation: dict) -> np.ndarray:
        """
        Select actions based on Kelly criterion.

        Args:
            observation: Environment observation dict

        Returns:
            Action array (investment levels per asset)

        """
        assets = observation["assets"]
        num_assets = len(assets)
        config = self._get_config()
        uses_levels = config is not None and config.enabled
        uses_interim = self._uses_interim_observations()

        # Get action masks
        action_masks = None
        if self.env is not None:
            try:
                unwrapped = getattr(self.env, "unwrapped", self.env)
                action_masks = unwrapped.action_masks()
            except (AttributeError, IndexError):
                pass

        # Calculate current capacity usage
        current_capacity = 0
        for asset in assets:
            if asset.get("state") == 1:  # InDevelopment
                # Estimate capacity based on investment level (assume STANDARD if unknown)
                current_capacity += 2

        # Build actions
        actions = np.zeros(num_assets, dtype=int)

        # First pass: identify STOP candidates and calculate Kelly for idle assets
        asset_kelly = []
        for i, asset in enumerate(assets):
            state = asset.get("state", 0)

            if state == 1 and uses_interim and self._should_stop(asset):
                # STOP this trial
                if action_masks is None or (len(action_masks[i]) > 4 and action_masks[i][4]):
                    actions[i] = 4  # STOP
                    current_capacity -= 2  # Free up capacity
                    asset_kelly.append((i, -999, state))  # Already handled
                else:
                    asset_kelly.append((i, 0, state))
            elif state == 0:  # Idle - candidate for investment
                kelly = self._calculate_kelly_fraction(asset)
                asset_kelly.append((i, kelly, state))
            else:
                asset_kelly.append((i, 0, state))

        # Sort idle assets by Kelly fraction (highest first)
        idle_assets = [(i, k, s) for i, k, s in asset_kelly if s == 0 and k > -900]
        idle_assets.sort(key=lambda x: -x[1])  # Descending by Kelly

        # Second pass: allocate investments respecting capacity
        for i, kelly, state in idle_assets:
            if kelly <= 0:
                actions[i] = 0  # Don't invest in negative EV
                continue

            # Determine investment level from Kelly
            level = self._kelly_to_level(kelly)

            # Check capacity
            capacity_needed = self._estimate_capacity_usage(level)

            # If over capacity, try lower level
            while current_capacity + capacity_needed > self.capacity_limit and level > 0:
                level -= 1
                capacity_needed = self._estimate_capacity_usage(level)

            # Check action mask
            if action_masks is not None:
                mask = action_masks[i]
                if level >= len(mask) or not mask[level]:
                    # Find highest allowed level
                    for try_level in range(min(level, len(mask) - 1), -1, -1):
                        if mask[try_level]:
                            level = try_level
                            capacity_needed = self._estimate_capacity_usage(level)
                            break
                    else:
                        level = 0
                        capacity_needed = 0

            if level > 0 and current_capacity + capacity_needed <= self.capacity_limit:
                actions[i] = level
                current_capacity += capacity_needed

        return actions


class ConservativeKellyAgent(KellyAgent):
    """More conservative Kelly agent using quarter-Kelly."""

    def __init__(self):
        super().__init__(
            kelly_fraction=0.25,
            capacity_limit=4.0,
            stop_threshold=0.25,
            use_stop=True,
        )


# Alias for clarity
QuarterKellyAgent = ConservativeKellyAgent


class AggressiveKellyAgent(KellyAgent):
    """More aggressive Kelly agent using full Kelly."""

    def __init__(self):
        super().__init__(
            kelly_fraction=1.0,
            capacity_limit=5.0,  # Allow slight overage
            stop_threshold=0.35,
            use_stop=True,
        )
