"""Multi-agent competitive investment game environment using PettingZoo."""

from __future__ import annotations

import functools
import logging
from typing import Any, Optional, Union

import gymnasium as gym
import numpy as np
import upath
from pettingzoo import ParallelEnv

from aiml_pyxis_investment_game.config import (
    ApprovalPhaseConfig,
    DistributionalPtrsConfig,
    InterimTrialObservationsConfig,
    InvestmentLevelsConfig,
    PricingConfig,
    TAExperienceConfig,
    UncertainPtrsConfig,
)
from aiml_pyxis_investment_game.environment.obs_layout import TA_INDEX, ObsLayout
from aiml_pyxis_investment_game.environment.reward import Reward
from aiml_pyxis_investment_game.game.asset import AssetState
from aiml_pyxis_investment_game.game.constants import InvestmentLevel
from aiml_pyxis_investment_game.game.game_state import GameState
from aiml_pyxis_investment_game.game.multi_agent_game import MultiAgentGame
from aiml_pyxis_investment_game.game.shared_market_state import (
    THERAPEUTIC_AREAS,
    AlertType,
    indication_key,
)
from aiml_pyxis_investment_game.game.trial import TrialPhase, TrialState

logger = logging.getLogger(__name__)

# BD observation features: 1 (bd_available) + 8 (asset details) = 9 per slot
_BD_OBS_FEATURES_PER_SLOT = 9

# Indication market features (per indication slot)
_INDICATION_FEATURES = 5  # exclusivity, share, first_mover, my/comp drugs

# Alert features
_ALERT_FEATURES = 8  # event_type (3) + agent_idx + ta_idx + indication + age + phase


class MultiAgentInvestmentGameEnv(ParallelEnv):
    """
    Multi-agent competitive investment game environment.

    Uses MultiAgentGame to orchestrate N GameState instances.
    All single-player dynamics come from GameState.step().
    Cross-agent interactions (BD deals, market share, alerts)
    are handled by MultiAgentGame.
    """

    metadata = {"render_modes": ["human"], "name": "multi_agent_investment_game"}

    def __init__(
        self,
        assets_dir: upath.UPath,
        num_agents: int,
        starting_cash: float,
        max_num_assets: int,
        horizon: int,
        equilibrium_num_assets: int,
        asset_arrival_sensitivity_below: float,
        asset_arrival_sensitivity_above: float,
        reinvestment_percentage: float,
        # BD market parameters (Poisson-distributed, event-driven)
        bd_enabled: bool,
        bd_assets_dir: upath.UPath,
        bd_base_lambda: float,
        bd_leak_lambda_boost: float,
        bd_min_step: int,
        bd_num_bid_levels: int,
        bd_break_even_bid_level: int,
        bd_max_slots: int,
        bd_phase_weights: list[float],
        bd_indication_activity_bias: float,
        # Competition parameters
        exclusivity_period: int,
        first_mover_bonus: float,
        disable_market_share_competition: bool,
        # Intelligence parameters (event-driven leaks)
        alert_history_length: int,
        leak_phase_probabilities: list[float],
        alerts_per_agent: int,
        # Reward parameters
        reward_fn: Reward,
        # Masking and ordering
        shuffle_order: bool,
        mask_first_order_assets: bool,
        mask_negative_enpv_assets: bool,
        # Feature configs
        flatten_obs: bool,
        distributional_ptrs_config: DistributionalPtrsConfig,
        ta_experience_config: TAExperienceConfig,
        uncertain_ptrs_config: UncertainPtrsConfig,
        investment_levels_config: InvestmentLevelsConfig,
        interim_trial_observations_config: InterimTrialObservationsConfig,
        rd_capacity_config,
        approval_phase_config: ApprovalPhaseConfig,
        # Pricing configuration
        pricing_config: PricingConfig,
        # Multi-agent reward type
        reward_type: str,
        reward_scale: float,
        # Indication-based market segmentation
        max_indications_per_ta: int,
        target_drugs_per_indication: float,
        on_market_fraction: float,
        indication_spread: float,
        indication_drift_speed: float,
        trial_cost_multiplier: float,
        # Congestion penalty
        congestion_exponent: float,
        congestion_ramp_steps: int,
        congestion_incumbent_penalty: float,
        render_mode: Optional[str] = None,
    ):
        """Initialize multi-agent investment game environment."""
        super().__init__()

        # Store configuration for reset
        self._num_agents = num_agents
        self.assets_dir = assets_dir
        self.starting_cash = starting_cash
        self.max_num_assets = max_num_assets
        self.horizon = horizon
        self.equilibrium_num_assets = equilibrium_num_assets
        self.asset_arrival_sensitivity_below = asset_arrival_sensitivity_below
        self.asset_arrival_sensitivity_above = asset_arrival_sensitivity_above
        self.reinvestment_percentage = reinvestment_percentage

        # BD configuration
        self.bd_enabled = bd_enabled
        self.bd_assets_dir = bd_assets_dir
        self.bd_base_lambda = bd_base_lambda
        self.bd_leak_lambda_boost = bd_leak_lambda_boost
        self.bd_min_step = bd_min_step
        self.bd_num_bid_levels = bd_num_bid_levels
        self.bd_break_even_bid_level = bd_break_even_bid_level
        self.bd_max_slots = bd_max_slots
        self.bd_phase_weights = bd_phase_weights
        self.bd_indication_activity_bias = bd_indication_activity_bias

        # Competition
        self.exclusivity_period = exclusivity_period
        self.first_mover_bonus = first_mover_bonus
        self.disable_market_share_competition = disable_market_share_competition

        # Intelligence
        self.alert_history_length = alert_history_length
        self.leak_phase_probabilities = leak_phase_probabilities
        self.alerts_per_agent = alerts_per_agent
        self.max_alerts = alerts_per_agent * max(num_agents - 1, 1)

        self.shuffle_order = shuffle_order
        self.mask_first_order_assets = mask_first_order_assets
        self.mask_negative_enpv_assets = mask_negative_enpv_assets
        self.flatten_obs = flatten_obs
        self.render_mode = render_mode

        # Feature configs
        self.distributional_ptrs_config = distributional_ptrs_config
        self.ta_experience_config = ta_experience_config
        self.uncertain_ptrs_config = uncertain_ptrs_config
        self.investment_levels_config = investment_levels_config
        self.interim_trial_observations_config = interim_trial_observations_config
        self.rd_capacity_config = rd_capacity_config
        self.approval_phase_config = approval_phase_config
        self.pricing_config = pricing_config

        # Reward
        self._reward_fn = reward_fn
        self._reward_type = reward_type
        self._reward_scale = reward_scale

        # Indication-based market segmentation
        self.max_indications_per_ta = max_indications_per_ta
        self.target_drugs_per_indication = target_drugs_per_indication
        self.on_market_fraction = on_market_fraction
        self.indication_spread = indication_spread
        self.indication_drift_speed = indication_drift_speed
        self.trial_cost_multiplier = trial_cost_multiplier
        self.congestion_exponent = congestion_exponent
        self.congestion_ramp_steps = congestion_ramp_steps
        self.congestion_incumbent_penalty = congestion_incumbent_penalty

        # Persistent RNG for generating per-episode seeds.
        # When reset(seed=N) is called, this is re-seeded.
        # When reset() is called without a seed, a new game seed is drawn
        # from this RNG so each episode is different.
        self._episode_rng = np.random.default_rng(42)

        # Agent names
        self.possible_agents = [f"pharma_{i}" for i in range(num_agents)]
        self.agents = self.possible_agents.copy()

        # Will be initialized on reset
        self.multi_agent_game: Optional[MultiAgentGame] = None
        self._asset_id_orders: dict[str, list] = {}
        self._indications_per_ta: int = 0  # Set on reset
        # Per-agent pricing multipliers (asset_id -> multiplier), updated each step
        self._current_pricing: dict[str, dict[str, float]] = {}

        # Build observation layout from feature configs
        self._layout = ObsLayout.from_config(
            ta_experience_config=ta_experience_config,
            rd_capacity_config=rd_capacity_config,
            distributional_ptrs_config=distributional_ptrs_config,
            uncertain_ptrs_config=uncertain_ptrs_config,
            interim_trial_observations_config=interim_trial_observations_config,
            pricing_config=pricing_config,
            has_time_feature=True,
            has_indication_feature=True,
        )

        # Calculate observation size
        L = self._layout
        self._obs_size = (
            L.global_features
            + self.max_num_assets * L.asset_total_features
            + self.bd_max_slots * _BD_OBS_FEATURES_PER_SLOT
            + len(THERAPEUTIC_AREAS)
            * self.max_indications_per_ta
            * _INDICATION_FEATURES
            + self.max_alerts * _ALERT_FEATURES
        )

    @property
    def agent_portfolios(self) -> dict[str, GameState]:
        """Access agent GameState instances (compatibility property)."""
        if self.multi_agent_game is None:
            return {}
        return self.multi_agent_game.agent_states

    @property
    def time(self) -> int:
        """Current game time step."""
        if self.multi_agent_game is None:
            return 0
        return self.multi_agent_game.time

    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent: str) -> gym.Space:
        """Return observation space for an agent."""
        if self.flatten_obs:
            return gym.spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=(self._obs_size,),
                dtype=np.float32,
            )

        L = self._layout

        # Trial space
        trial_fields = {
            "cost_remaining": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=float
            ),
            "time_remaining": gym.spaces.Box(
                low=0, high=int(1e9), shape=(), dtype=int
            ),
            "ptrs": gym.spaces.Box(low=0, high=1, shape=(), dtype=float),
        }
        if L.distributional_ptrs_enabled:
            trial_fields["ptrs_expected"] = gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            )
            trial_fields["ptrs_confidence"] = gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            )
            trial_fields["ptrs_range_low"] = gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            )
            trial_fields["ptrs_range_high"] = gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            )
        trial_space = gym.spaces.Dict(trial_fields)

        # Asset space
        asset_fields = {
            "max_revenue": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=float
            ),
            "time_until_max_revenue": gym.spaces.Box(
                low=0, high=int(1e9), shape=(), dtype=int
            ),
            "time_until_patent_expiry": gym.spaces.Box(
                low=0, high=int(1e9), shape=(), dtype=int
            ),
            "pending_trial_phase": gym.spaces.Discrete(len(TrialPhase) + 1),
            "time_on_market": gym.spaces.Box(
                low=0, high=int(1e9), shape=(), dtype=int
            ),
            "cost_this_step": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=float
            ),
            "revenue_this_step": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=float
            ),
            "enpv": gym.spaces.Box(
                low=-float("inf"), high=float("inf"), shape=(), dtype=float
            ),
            "eroi": gym.spaces.Box(
                low=-float("inf"), high=float("inf"), shape=(), dtype=float
            ),
            "trials": gym.spaces.Tuple(
                [trial_space] * len(TrialPhase)
            ),
            "state": gym.spaces.Discrete(len(AssetState)),
            "ta_index": gym.spaces.Discrete(3),
            "indication": gym.spaces.Discrete(
                self.max_indications_per_ta
            ),
        }
        if L.interim_obs_enabled:
            asset_fields["interim_signal"] = gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            )
            asset_fields["trial_progress"] = gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            )
        if L.pricing_enabled:
            asset_fields["price_multiplier"] = gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=float
            )
        asset_space = gym.spaces.Dict(asset_fields)

        # BD slot space
        bd_fields = {
            "available": gym.spaces.Discrete(2),
            "max_revenue": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=float
            ),
            "time_until_max_revenue": gym.spaces.Box(
                low=0, high=int(1e9), shape=(), dtype=int
            ),
            "time_until_patent_expiry": gym.spaces.Box(
                low=0, high=int(1e9), shape=(), dtype=int
            ),
            "ta_index": gym.spaces.Discrete(3),
            "indication": gym.spaces.Discrete(
                self.max_indications_per_ta
            ),
            "enpv": gym.spaces.Box(
                low=-float("inf"), high=float("inf"), shape=(), dtype=float
            ),
            "trial_phase": gym.spaces.Discrete(len(TrialPhase) + 1),
            "ptrs": gym.spaces.Box(low=0, high=1, shape=(), dtype=float),
        }
        bd_space = gym.spaces.Dict(bd_fields)

        # Indication market space
        indication_fields = {
            "exclusivity_remaining": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=float
            ),
            "my_avg_share": gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            ),
            "first_mover": gym.spaces.Discrete(2),
            "my_drugs": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=int
            ),
            "competitor_drugs": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=int
            ),
        }
        indication_space = gym.spaces.Dict(indication_fields)

        # Alert space
        alert_fields = {
            "event_type": gym.spaces.Discrete(3),
            "agent_index": gym.spaces.Box(
                low=0, high=self._num_agents, shape=(), dtype=int
            ),
            "ta_index": gym.spaces.Discrete(3),
            "indication": gym.spaces.Discrete(
                self.max_indications_per_ta
            ),
            "age": gym.spaces.Box(
                low=0, high=float("inf"), shape=(), dtype=int
            ),
            "phase": gym.spaces.Box(
                low=0, high=1, shape=(), dtype=float
            ),
        }
        alert_space = gym.spaces.Dict(alert_fields)

        # Top-level space
        obs_fields = {
            "cash": gym.spaces.Box(
                low=float("-inf"),
                high=float("inf"),
                shape=(1,),
                dtype=np.float32,
            ),
            "time": gym.spaces.Box(
                low=0, high=int(1e9), shape=(1,), dtype=np.float32
            ),
            "assets": gym.spaces.Tuple(
                [asset_space] * self.max_num_assets
            ),
            "bd_market": gym.spaces.Tuple(
                [bd_space] * self.bd_max_slots
            ),
            "indication_markets": gym.spaces.Dict({
                ta: gym.spaces.Tuple(
                    [indication_space] * self.max_indications_per_ta
                )
                for ta in THERAPEUTIC_AREAS
            }),
            "alerts": gym.spaces.Tuple(
                [alert_space] * self.max_alerts
            ),
        }
        if L.ta_experience_enabled:
            obs_fields["ta_experience"] = gym.spaces.Dict({
                ta: gym.spaces.Box(
                    low=0, high=float("inf"), shape=(), dtype=float
                )
                for ta in THERAPEUTIC_AREAS
            })

        return gym.spaces.Dict(obs_fields)

    @functools.lru_cache(maxsize=None)
    def action_space(self, agent: str) -> gym.Space:
        """
        Return action space for an agent.

        When investment_levels is enabled, investments use MultiDiscrete with
        5 choices per asset (NONE/MINIMAL/STANDARD/ACCELERATED/STOP).
        Otherwise, investments use MultiBinary (invest or not).

        BD bids use MultiDiscrete with bd_num_bid_levels levels per slot:
          0 = pass, 1-N = bid (level/N) of eNPV.
        """
        use_levels = (
            self.investment_levels_config is not None
            and self.investment_levels_config.enabled
        )
        if use_levels:
            inv_space = gym.spaces.MultiDiscrete(
                [len(InvestmentLevel)] * self.max_num_assets
            )
        else:
            inv_space = gym.spaces.MultiBinary(self.max_num_assets)

        spaces = {
            "investments": inv_space,
            "bd_bids": gym.spaces.MultiDiscrete(
                [self.bd_num_bid_levels] * self.bd_max_slots
            ),
        }
        if self.pricing_config.enabled:
            num_price_levels = len(self.pricing_config.levels)
            spaces["pricing"] = gym.spaces.MultiDiscrete(
                [num_price_levels] * self.max_num_assets
            )
        return gym.spaces.Dict(spaces)

    def action_masks(self, agent: str) -> dict[str, np.ndarray]:
        """
        Return action masks for an agent.

        When investment_levels is enabled, returns per-asset masks with shape
        (max_num_assets, num_levels) matching MultiDiscrete action space:
            0: NONE - always valid
            1: MINIMAL - valid for investable Idle assets
            2: STANDARD - valid for investable Idle assets
            3: ACCELERATED - valid for investable Idle assets
            4: STOP - valid for InDevelopment assets only

        When investment_levels is disabled, returns binary mask (max_num_assets,)
        matching MultiBinary action space.

        BD bid masks: per-slot (bd_num_bid_levels,) array.
        No BD asset → only level 0 valid. Asset present → 0 always valid,
        levels 1-N valid if agent can afford eNPV * (level / (N-1)).
        """
        game_state = self.multi_agent_game.agent_states[agent]
        asset_order = self._asset_id_orders[agent]
        use_levels = (
            self.investment_levels_config is not None
            and self.investment_levels_config.enabled
        )

        if use_levels:
            num_levels = len(InvestmentLevel)
            investment_mask = []
            for i in range(self.max_num_assets):
                asset_id = asset_order[i] if i < len(asset_order) else None
                if asset_id is None or asset_id not in game_state.assets:
                    # Padding slot: only NONE valid
                    mask = [True] + [False] * (num_levels - 1)
                else:
                    asset = game_state.assets[asset_id]
                    if asset.state == AssetState.Idle:
                        can_invest = True
                        if self.mask_first_order_assets:
                            if game_state.cash - asset.cost_to_invest_this_step < 0:
                                can_invest = False
                        if self.mask_negative_enpv_assets:
                            if asset.enpv < 0:
                                can_invest = False
                        if can_invest:
                            # NONE + all investment levels, no STOP
                            mask = [True, True, True, True, False]
                        else:
                            mask = [True] + [False] * (num_levels - 1)
                    elif asset.state == AssetState.InDevelopment:
                        # Can change level or STOP
                        mask = [True, True, True, True, True]
                    else:
                        # OnMarket, Failed, Expired: only NONE
                        mask = [True] + [False] * (num_levels - 1)
                investment_mask.append(mask)
        else:
            investment_mask = np.zeros(self.max_num_assets, dtype=np.int8)
            for i, asset_id in enumerate(asset_order):
                if asset_id is not None and asset_id in game_state.assets:
                    asset = game_state.assets[asset_id]
                    if asset.state == AssetState.Idle:
                        can_invest = True
                        if self.mask_first_order_assets:
                            if game_state.cash - asset.cost_to_invest_this_step < 0:
                                can_invest = False
                        if self.mask_negative_enpv_assets:
                            if asset.enpv < 0:
                                can_invest = False
                        if can_invest:
                            investment_mask[i] = 1

        # BD bid masks: per-slot, per-level
        shared_market = (
            self.multi_agent_game.shared_market
            if self.multi_agent_game is not None
            else None
        )
        bd_bid_mask = []
        can_bid = (
            self.bd_enabled
            and len(game_state.assets) < game_state.max_num_assets
            and not game_state.bankrupt
            and game_state.cash > 0
        )

        bd_assets = shared_market.current_bd_assets if shared_market else []
        for slot in range(self.bd_max_slots):
            if not can_bid or slot >= len(bd_assets):
                # No BD asset in this slot or can't bid: only level 0 (pass) valid
                bd_bid_mask.append([True] + [False] * (self.bd_num_bid_levels - 1))
            else:
                from aiml_pyxis_investment_game.environment.market_mechanics import (
                    bd_bid_price,
                )

                bd_asset = bd_assets[slot]
                enpv = bd_asset.enpv
                num_levels = self.bd_num_bid_levels
                break_even = shared_market.bd_break_even_bid_level
                reinv_pct = self.reinvestment_percentage
                level_mask = [True]  # Level 0 (pass) always valid
                for level in range(1, num_levels):
                    price = bd_bid_price(enpv, level, break_even, reinv_pct)
                    level_mask.append(game_state.cash >= price)
                bd_bid_mask.append(level_mask)

        result = {
            "investments": investment_mask,
            "bd_bids": bd_bid_mask,
        }

        # Pricing masks: only on-market assets can have non-default pricing
        if self.pricing_config.enabled:
            num_price_levels = len(self.pricing_config.levels)
            default_level = self.pricing_config.default_level
            pricing_mask = []
            for i in range(self.max_num_assets):
                asset_id = asset_order[i] if i < len(asset_order) else None
                if asset_id is not None and asset_id in game_state.assets:
                    asset = game_state.assets[asset_id]
                    if asset.state == AssetState.OnMarket:
                        # All price levels valid for on-market drugs
                        pricing_mask.append([True] * num_price_levels)
                        continue
                # Not on market or empty slot: only default level valid
                mask = [False] * num_price_levels
                mask[default_level] = True
                pricing_mask.append(mask)
            result["pricing"] = pricing_mask

        return result

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Reset the environment."""
        self.agents = self.possible_agents.copy()

        if seed is not None:
            self._episode_rng = np.random.default_rng(seed)
        actual_seed = int(self._episode_rng.integers(0, 2**31))

        # Compute indications per TA based on game parameters
        num_tas = 3
        raw = (
            self._num_agents
            * (self.equilibrium_num_assets / num_tas)
            * self.on_market_fraction
            / self.target_drugs_per_indication
        )
        self._indications_per_ta = min(max(2, round(raw)), self.max_indications_per_ta)

        self.multi_agent_game = MultiAgentGame.initialise(
            num_agents=self._num_agents,
            seed=actual_seed,
            starting_cash=self.starting_cash,
            horizon=self.horizon,
            equilibrium_num_assets=self.equilibrium_num_assets,
            max_num_assets=self.max_num_assets,
            asset_arrival_sensitivity_below=self.asset_arrival_sensitivity_below,
            asset_arrival_sensitivity_above=self.asset_arrival_sensitivity_above,
            reinvestment_percentage=self.reinvestment_percentage,
            assets_dir=self.assets_dir,
            exclusivity_period=self.exclusivity_period,
            first_mover_bonus=self.first_mover_bonus,
            disable_market_share_competition=self.disable_market_share_competition,
            alert_history_length=self.alert_history_length,
            reward_fn_config={},
            distributional_ptrs_config=self.distributional_ptrs_config,
            ta_experience_config=self.ta_experience_config,
            uncertain_ptrs_config=self.uncertain_ptrs_config,
            investment_levels_config=self.investment_levels_config,
            interim_trial_observations_config=self.interim_trial_observations_config,
            rd_capacity_config=self.rd_capacity_config,
            indications_per_ta=self._indications_per_ta,
            indication_spread=self.indication_spread,
            indication_drift_speed=self.indication_drift_speed,
            trial_cost_multiplier=self.trial_cost_multiplier,
            approval_phase_config=self.approval_phase_config,
            # BD configuration
            bd_enabled=self.bd_enabled,
            bd_assets_dir=self.bd_assets_dir,
            bd_base_lambda=self.bd_base_lambda,
            bd_leak_lambda_boost=self.bd_leak_lambda_boost,
            bd_min_step=self.bd_min_step,
            bd_num_bid_levels=self.bd_num_bid_levels,
            bd_break_even_bid_level=self.bd_break_even_bid_level,
            bd_phase_weights=self.bd_phase_weights,
            bd_indication_activity_bias=self.bd_indication_activity_bias,
            bd_max_slots=self.bd_max_slots,
            # Leak configuration
            leak_phase_probabilities=self.leak_phase_probabilities,
            # Congestion penalty
            congestion_exponent=self.congestion_exponent,
            congestion_ramp_steps=self.congestion_ramp_steps,
            congestion_incumbent_penalty=self.congestion_incumbent_penalty,
            # Pricing elasticity
            pricing_elasticity=self.pricing_config.elasticity,
        )

        # Initialize asset ordering for observations
        self._asset_id_orders = {}
        for agent in self.possible_agents:
            game_state = self.multi_agent_game.agent_states[agent]
            asset_ids = list(game_state.assets.keys())
            asset_order = asset_ids + [None] * (self.max_num_assets - len(asset_ids))
            if self.shuffle_order:
                self.np_random.shuffle(asset_order)
            self._asset_id_orders[agent] = asset_order

        # Build initial observations
        observations = {agent: self._get_observation(agent) for agent in self.agents}
        infos = {agent: self._get_info(agent) for agent in self.agents}

        return observations, infos

    def step(
        self,
        actions: dict[str, Any],
    ) -> tuple[
        dict[str, Any],  # observations
        dict[str, float],  # rewards
        dict[str, bool],  # terminations
        dict[str, bool],  # truncations
        dict[str, Any],  # infos
    ]:
        """Execute one step in the environment."""
        # Store pre-step game for reward calculation
        pre_step_game = self.multi_agent_game

        # Parse actions
        parsed = self._parse_actions(actions)
        investments = parsed["investments"]
        bd_bids = parsed["bd_bids"]
        pricing_levels = parsed["pricing"]

        # Convert investment arrays to GameState-compatible action dicts
        use_levels = (
            self.investment_levels_config is not None
            and self.investment_levels_config.enabled
        )
        investor_actions = {}
        for agent in self.agents:
            agent_actions = {}
            asset_order = self._asset_id_orders[agent]
            agent_investments = investments[agent]

            for i, invest in enumerate(agent_investments):
                if i < len(asset_order) and asset_order[i] is not None:
                    asset_id = asset_order[i]
                    if use_levels:
                        level = InvestmentLevel.from_int(int(invest))
                        if level != InvestmentLevel.NONE:
                            agent_actions[asset_id] = level
                    else:
                        if invest:
                            agent_actions[asset_id] = InvestmentLevel.STANDARD
            investor_actions[agent] = agent_actions

        # Convert pricing level indices to per-drug multipliers
        pricing_actions: dict[str, dict] | None = None
        if self.pricing_config.enabled:
            levels_list = self.pricing_config.levels
            pricing_actions = {}
            for agent in self.agents:
                agent_pricing: dict = {}
                asset_order = self._asset_id_orders[agent]
                agent_pricing_levels = pricing_levels[agent]
                for i, level_idx in enumerate(agent_pricing_levels):
                    if i < len(asset_order) and asset_order[i] is not None:
                        asset_id = asset_order[i]
                        mult = levels_list[int(level_idx)]
                        if mult != 1.0:
                            agent_pricing[asset_id] = mult
                pricing_actions[agent] = agent_pricing

        # Store pricing for observation building
        if pricing_actions is not None:
            self._current_pricing = pricing_actions
        else:
            self._current_pricing = {}

        # Step the multi-agent game
        has_bids = any(
            any(level > 0 for level in levels) for levels in bd_bids.values()
        )
        self.multi_agent_game = pre_step_game.step(
            investor_actions=investor_actions,
            bd_bids=bd_bids if has_bids else None,
            pricing_actions=pricing_actions,
        )

        # Update asset orderings for new/removed assets
        self._update_asset_orderings()

        # Calculate rewards
        base_rewards = {}
        for agent in self.agents:
            pre_state = pre_step_game.agent_states[agent]
            post_state = self.multi_agent_game.agent_states[agent]
            base_rewards[agent] = self._reward_fn.compute(
                pre_step_game_state=pre_state,
                post_step_game_state=post_state,
            )

        rewards = self._apply_reward_type(base_rewards)

        # Check terminations
        # Per-agent: game_ended (bankruptcy or horizon)
        # Episode terminates when ALL agents' games have ended
        terminations = {
            agent: self.multi_agent_game.agent_states[agent].game_ended
            for agent in self.agents
        }
        truncations = {agent: False for agent in self.agents}

        # Build observations and infos
        observations = {agent: self._get_observation(agent) for agent in self.agents}
        infos = {agent: self._get_info(agent) for agent in self.agents}

        return observations, rewards, terminations, truncations, infos

    def _apply_reward_type(self, base_rewards: dict[str, float]) -> dict[str, float]:
        """Apply multi-agent reward type wrapper to base rewards."""
        if self._reward_type == "absolute":
            return {aid: r / self._reward_scale for aid, r in base_rewards.items()}

        if self._reward_type == "relative_rank":
            ranked = sorted(
                base_rewards.keys(),
                key=lambda x: base_rewards[x],
                reverse=True,
            )
            n = len(ranked)
            rewards = {}
            for rank, aid in enumerate(ranked):
                state = self.multi_agent_game.agent_states[aid]
                if state.game_ended and state.cash < 0:
                    # Bankrupt: strong negative
                    rewards[aid] = -1.0
                else:
                    # Zero-sum ranking: winner +1.0, loser -1.0
                    # For 2 agents: rank 0 → +1.0, rank 1 → -1.0
                    # For N agents: linearly spaced from +1.0 to -1.0
                    rewards[aid] = 1.0 - 2.0 * rank / max(n - 1, 1)
            return rewards

        if self._reward_type == "zero_sum":
            active = [
                aid
                for aid in base_rewards
                if not (
                    self.multi_agent_game.agent_states[aid].game_ended
                    and self.multi_agent_game.agent_states[aid].cash < 0
                )
            ]
            if not active:
                return {aid: 0.0 for aid in base_rewards}
            total = sum(base_rewards[aid] for aid in active)
            rewards = {}
            for aid in base_rewards:
                state = self.multi_agent_game.agent_states[aid]
                if state.game_ended and state.cash < 0:
                    rewards[aid] = -1.0
                else:
                    others_total = total - base_rewards[aid]
                    others_count = len(active) - 1
                    if others_count > 0:
                        others_mean = others_total / others_count
                        rewards[aid] = (
                            base_rewards[aid] - others_mean
                        ) / self._reward_scale
                    else:
                        rewards[aid] = base_rewards[aid] / self._reward_scale
            return rewards

        raise ValueError(f"Unknown reward_type: {self._reward_type}")

    def _parse_actions(self, actions: dict[str, Any]) -> dict[str, dict]:
        """
        Parse actions from agents.

        Supports both:
        - Dict actions: {"investments": array, "bd_bids": array, "pricing": array}
        - Raw array actions: interpreted as investments only (legacy)

        BD bids are integer levels (0=pass, 1-N = bid fraction of eNPV).
        Pricing is integer level indices into pricing_config.levels.
        """
        investments = {}
        bd_bids = {}
        pricing = {}
        default_level = (
            self.pricing_config.default_level if self.pricing_config.enabled else 0
        )

        for agent in self.agents:
            action = actions.get(agent)
            if action is None:
                investments[agent] = np.zeros(self.max_num_assets, dtype=np.int64)
                bd_bids[agent] = [0] * self.bd_max_slots
                pricing[agent] = np.full(
                    self.max_num_assets, default_level, dtype=np.int64
                )
            elif isinstance(action, dict):
                investments[agent] = np.asarray(
                    action.get("investments", np.zeros(self.max_num_assets)),
                    dtype=np.int64,
                )
                raw_bids = action.get("bd_bids", np.zeros(self.bd_max_slots))
                raw_bids = np.asarray(raw_bids, dtype=np.int64)
                bd_bids[agent] = [int(b) for b in raw_bids]
                if self.pricing_config.enabled:
                    raw_pricing = action.get(
                        "pricing", np.full(self.max_num_assets, default_level)
                    )
                    pricing[agent] = np.asarray(raw_pricing, dtype=np.int64)
                else:
                    pricing[agent] = np.full(
                        self.max_num_assets, default_level, dtype=np.int64
                    )
            else:
                investments[agent] = np.asarray(action, dtype=np.int64)
                bd_bids[agent] = [0] * self.bd_max_slots
                pricing[agent] = np.full(
                    self.max_num_assets, default_level, dtype=np.int64
                )

        return {
            "investments": investments,
            "bd_bids": bd_bids,
            "pricing": pricing,
        }

    def _update_asset_orderings(self) -> None:
        """Update asset orderings for new assets acquired this step."""
        for agent in self.agents:
            game_state = self.multi_agent_game.agent_states[agent]
            asset_order = self._asset_id_orders[agent]

            # Remove stale entries first to free up slots
            for i in range(len(asset_order)):
                if (
                    asset_order[i] is not None
                    and asset_order[i] not in game_state.assets
                ):
                    asset_order[i] = None

            # Then add new assets to available slots
            ordered_ids = set(aid for aid in asset_order if aid is not None)
            for asset_id in game_state.assets:
                if asset_id not in ordered_ids:
                    for i in range(len(asset_order)):
                        if asset_order[i] is None:
                            asset_order[i] = asset_id
                            break

    def _get_observation(
        self, agent: str
    ) -> Union[np.ndarray, dict]:
        """Build observation for an agent (flat or dict)."""
        if not self.flatten_obs:
            return self._get_observation_dict(agent)
        return self._get_observation_flat(agent)

    def _get_observation_flat(self, agent: str) -> np.ndarray:
        """Build flattened observation for an agent."""
        obs = np.zeros(self._obs_size, dtype=np.float32)
        game_state = self.multi_agent_game.agent_states[agent]
        shared_market = self.multi_agent_game.shared_market

        L = self._layout
        asset_total = L.asset_total_features
        asset_scalar = L.asset_scalar_features
        trial_feat = L.trial_features
        dist_on = L.distributional_ptrs_enabled
        interim_on = L.interim_obs_enabled
        off_interim = L.offset_interim_signal
        off_progress = L.offset_trial_progress
        off_ta_idx = L.offset_ta_index
        off_indication = L.offset_indication
        off_pricing = L.offset_pricing

        # Global features
        pos = 0
        obs[pos] = game_state.cash
        obs[pos + 1] = self.multi_agent_game.time
        pos = 2

        if L.ta_experience_enabled:
            for i, ta in enumerate(THERAPEUTIC_AREAS):
                obs[pos + i] = game_state.ta_experience.get(ta, 0.0)
            pos += L.num_ta_exp_features

        offset = L.global_features

        # Per-asset features
        asset_order = self._asset_id_orders[agent]
        for i in range(self.max_num_assets):
            asset_offset = offset + i * asset_total
            asset_id = asset_order[i] if i < len(asset_order) else None

            if asset_id is None or asset_id not in game_state.assets:
                obs[asset_offset + 9] = AssetState.Expired.integer
                if dist_on:
                    trial_off = asset_offset + asset_scalar
                    for _ in TrialPhase:
                        obs[trial_off + 4] = 1.0  # ptrs_confidence
                        trial_off += trial_feat
                continue

            asset = game_state.assets[asset_id]
            obs[asset_offset] = asset.max_revenue
            obs[asset_offset + 1] = asset.time_until_max_revenue
            obs[asset_offset + 2] = asset.time_until_patent_expiry

            if asset.state == AssetState.OnMarket:
                obs[asset_offset + 3] = 0
            elif asset.trial and asset.trial.state == TrialState.PHASE_FAILED:
                obs[asset_offset + 3] = 0
            elif asset.trial:
                obs[asset_offset + 3] = asset.trial.phase.integer + 1
            else:
                obs[asset_offset + 3] = 0

            obs[asset_offset + 4] = asset.time_on_market
            obs[asset_offset + 5] = asset.cost_this_step
            obs[asset_offset + 6] = asset.revenue_this_step
            obs[asset_offset + 7] = asset.enpv
            obs[asset_offset + 8] = asset.eroi
            obs[asset_offset + 9] = asset.state.integer

            if interim_on:
                obs[asset_offset + off_interim] = asset.interim_signal
                obs[asset_offset + off_progress] = asset.trial_progress

            obs[asset_offset + off_ta_idx] = TA_INDEX.get(asset.therapeutic_area, 0)
            obs[asset_offset + off_indication] = asset.indication

            if L.pricing_enabled:
                agent_pricing = self._current_pricing.get(agent, {})
                obs[asset_offset + off_pricing] = agent_pricing.get(asset_id, 1.0)

            # Trial phase features
            trial_off = asset_offset + asset_scalar
            trial = asset.trial
            for phase in TrialPhase:
                if trial and trial.phase == phase:
                    obs[trial_off] = trial.cost_remaining
                    obs[trial_off + 1] = trial.time_remaining
                    obs[trial_off + 2] = trial.ptrs
                    if dist_on:
                        obs[trial_off + 3] = trial.ptrs_expected
                        obs[trial_off + 4] = trial.ptrs_confidence
                        obs[trial_off + 5] = trial.ptrs_range_low
                        obs[trial_off + 6] = trial.ptrs_range_high
                    trial = trial.next_trial_on_success
                else:
                    if dist_on:
                        obs[trial_off + 4] = 1.0  # ptrs_confidence default
                trial_off += trial_feat

        offset += self.max_num_assets * asset_total

        # BD observation
        bd_obs_list = shared_market.get_bd_observations()
        for slot in range(self.bd_max_slots):
            bd_offset = offset + slot * _BD_OBS_FEATURES_PER_SLOT
            if slot < len(bd_obs_list):
                bd_obs = bd_obs_list[slot]
                obs[bd_offset] = 1.0
                obs[bd_offset + 1] = bd_obs["max_revenue"]
                obs[bd_offset + 2] = bd_obs["time_until_max_revenue"]
                obs[bd_offset + 3] = bd_obs["time_until_patent_expiry"]
                obs[bd_offset + 4] = TA_INDEX.get(bd_obs["therapeutic_area"], 0)
                obs[bd_offset + 5] = bd_obs["indication"]
                obs[bd_offset + 6] = bd_obs["enpv"]
                obs[bd_offset + 7] = bd_obs["trial_phase"]
                obs[bd_offset + 8] = bd_obs["ptrs"]
        offset += self.bd_max_slots * _BD_OBS_FEATURES_PER_SLOT

        # Indication market features
        per_drug_shares = self.multi_agent_game._cached_market_shares.get(agent, {})

        for ta_idx, ta in enumerate(THERAPEUTIC_AREAS):
            for ind_idx in range(self.max_indications_per_ta):
                slot = ta_idx * self.max_indications_per_ta + ind_idx
                ind_offset = offset + slot * _INDICATION_FEATURES

                key = indication_key(ta, ind_idx)
                ind_market = shared_market.indication_markets.get(key)

                if ind_market is not None:
                    obs[ind_offset] = ind_market.exclusivity_remaining(
                        self.multi_agent_game.time
                    )
                    my_drug_ids = ind_market.active_drugs.get(agent, [])
                    if my_drug_ids:
                        drug_shares = [
                            per_drug_shares.get(did, 0.0) for did in my_drug_ids
                        ]
                        obs[ind_offset + 1] = sum(drug_shares) / len(drug_shares)
                    obs[ind_offset + 2] = float(ind_market.first_mover_agent == agent)
                    my_drugs = 0
                    competitor_drugs = 0
                    for aid, drug_ids in ind_market.active_drugs.items():
                        if aid == agent:
                            my_drugs += len(drug_ids)
                        else:
                            competitor_drugs += len(drug_ids)
                    obs[ind_offset + 3] = my_drugs
                    obs[ind_offset + 4] = competitor_drugs

        offset += (
            len(THERAPEUTIC_AREAS) * self.max_indications_per_ta * _INDICATION_FEATURES
        )

        # Alert features
        alerts = shared_market.get_alerts_for_agent(agent)
        recent_alerts = alerts[-self.max_alerts :] if self.max_alerts > 0 else []
        for i, alert in enumerate(recent_alerts):
            alert_offset = offset + i * _ALERT_FEATURES
            if alert.event_type == AlertType.DRUG_RELEASE:
                obs[alert_offset] = 1.0
            elif alert.event_type == AlertType.BD_DEAL:
                obs[alert_offset + 1] = 1.0
            elif alert.event_type == AlertType.PIPELINE_LEAK:
                obs[alert_offset + 2] = 1.0
            if alert.agent_id in self.possible_agents:
                obs[alert_offset + 3] = self.possible_agents.index(alert.agent_id)
            obs[alert_offset + 4] = TA_INDEX.get(alert.therapeutic_area, 0)
            obs[alert_offset + 5] = alert.indication
            obs[alert_offset + 6] = self.multi_agent_game.time - alert.step
            if alert.event_type == AlertType.PIPELINE_LEAK:
                phase_str = alert.details.get("new_phase", "")
                phase_map = {"Phase 2": 0.33, "Phase 3": 0.67, "Approval": 1.0}
                obs[alert_offset + 7] = phase_map.get(phase_str, 0.0)

        return obs

    @property
    def _padding_asset_obs(self):
        """Generate padding asset observation for empty slots."""
        L = self._layout
        trial_pad = {"cost_remaining": 0.0, "time_remaining": 0, "ptrs": 0.0}
        if L.distributional_ptrs_enabled:
            trial_pad["ptrs_expected"] = 0.0
            trial_pad["ptrs_confidence"] = 1.0
            trial_pad["ptrs_range_low"] = 0.0
            trial_pad["ptrs_range_high"] = 0.0

        obs = {
            "max_revenue": 0.0,
            "time_until_max_revenue": 0,
            "time_until_patent_expiry": 0,
            "pending_trial_phase": 0,
            "time_on_market": 0,
            "cost_this_step": 0.0,
            "revenue_this_step": 0.0,
            "enpv": 0.0,
            "eroi": 0.0,
            "trials": tuple(
                [dict(trial_pad) for _ in range(len(TrialPhase))]
            ),
            "state": AssetState.Expired.integer,
            "ta_index": 0,
            "indication": 0,
        }
        if L.interim_obs_enabled:
            obs["interim_signal"] = 0.0
            obs["trial_progress"] = 0.0
        if L.pricing_enabled:
            obs["price_multiplier"] = 1.0
        return obs

    _PADDING_BD_OBS = {
        "available": 0,
        "max_revenue": 0.0,
        "time_until_max_revenue": 0,
        "time_until_patent_expiry": 0,
        "ta_index": 0,
        "indication": 0,
        "enpv": 0.0,
        "trial_phase": 0,
        "ptrs": 0.0,
    }

    _PADDING_INDICATION_OBS = {
        "exclusivity_remaining": 0.0,
        "my_avg_share": 0.0,
        "first_mover": 0,
        "my_drugs": 0,
        "competitor_drugs": 0,
    }

    # -1 sentinel distinguishes padding from real alerts (0/1/2 = release/bd/leak)
    _PADDING_ALERT_OBS = {
        "event_type": -1,
        "agent_index": 0,
        "ta_index": 0,
        "indication": 0,
        "age": 0,
        "phase": 0.0,
    }

    def _get_observation_dict(self, agent: str) -> dict:
        """Build dict-based observation for an agent."""
        L = self._layout
        dist_on = L.distributional_ptrs_enabled
        interim_on = L.interim_obs_enabled
        game_state = self.multi_agent_game.agent_states[agent]
        shared_market = self.multi_agent_game.shared_market

        def _make_trial_obs(
            cost, time_rem, ptrs, ptrs_exp, ptrs_conf, ptrs_lo, ptrs_hi
        ):
            t = {
                "cost_remaining": cost,
                "time_remaining": time_rem,
                "ptrs": ptrs,
            }
            if dist_on:
                t["ptrs_expected"] = ptrs_exp
                t["ptrs_confidence"] = ptrs_conf
                t["ptrs_range_low"] = ptrs_lo
                t["ptrs_range_high"] = ptrs_hi
            return t

        def _get_asset_obs(asset, asset_id):
            trial = asset.trial
            trials_list = []
            for phase in TrialPhase:
                if trial and trial.phase == phase:
                    trials_list.append(
                        _make_trial_obs(
                            trial.cost_remaining,
                            trial.time_remaining,
                            trial.ptrs,
                            trial.ptrs_expected,
                            trial.ptrs_confidence,
                            trial.ptrs_range_low,
                            trial.ptrs_range_high,
                        )
                    )
                    trial = trial.next_trial_on_success
                else:
                    trials_list.append(
                        _make_trial_obs(
                            0.0, 0, 0.0, 0.0, 1.0, 0.0, 0.0
                        )
                    )

            if asset.state == AssetState.OnMarket:
                pending = 0
            elif (
                asset.trial
                and asset.trial.state == TrialState.PHASE_FAILED
            ):
                pending = 0
            elif asset.trial:
                pending = asset.trial.phase.integer + 1
            else:
                pending = 0

            obs = {
                "max_revenue": asset.max_revenue,
                "time_until_max_revenue": asset.time_until_max_revenue,
                "time_until_patent_expiry": (
                    asset.time_until_patent_expiry
                ),
                "pending_trial_phase": pending,
                "time_on_market": asset.time_on_market,
                "cost_this_step": asset.cost_this_step,
                "revenue_this_step": asset.revenue_this_step,
                "enpv": asset.enpv,
                "eroi": asset.eroi,
                "trials": tuple(trials_list),
                "state": asset.state.integer,
                "ta_index": TA_INDEX.get(asset.therapeutic_area, 0),
                "indication": asset.indication,
            }
            if interim_on:
                obs["interim_signal"] = asset.interim_signal
                obs["trial_progress"] = asset.trial_progress
            if L.pricing_enabled:
                agent_pricing = self._current_pricing.get(agent, {})
                obs["price_multiplier"] = agent_pricing.get(
                    asset_id, 1.0
                )
            return obs

        # Per-asset observations
        asset_order = self._asset_id_orders[agent]
        asset_obs = []
        for i in range(self.max_num_assets):
            asset_id = (
                asset_order[i] if i < len(asset_order) else None
            )
            if (
                asset_id is None
                or asset_id not in game_state.assets
            ):
                asset_obs.append(self._padding_asset_obs)
            else:
                asset_obs.append(
                    _get_asset_obs(
                        game_state.assets[asset_id], asset_id
                    )
                )

        # BD market observations
        bd_obs_list = shared_market.get_bd_observations()
        bd_obs = []
        for slot in range(self.bd_max_slots):
            if slot < len(bd_obs_list):
                bd = bd_obs_list[slot]
                bd_obs.append({
                    "available": 1,
                    "max_revenue": bd["max_revenue"],
                    "time_until_max_revenue": bd[
                        "time_until_max_revenue"
                    ],
                    "time_until_patent_expiry": bd[
                        "time_until_patent_expiry"
                    ],
                    "ta_index": TA_INDEX.get(
                        bd["therapeutic_area"], 0
                    ),
                    "indication": bd["indication"],
                    "enpv": bd["enpv"],
                    "trial_phase": bd["trial_phase"],
                    "ptrs": bd["ptrs"],
                })
            else:
                bd_obs.append(dict(self._PADDING_BD_OBS))

        # Indication market observations
        per_drug_shares = (
            self.multi_agent_game._cached_market_shares.get(
                agent, {}
            )
        )
        indication_obs: dict[str, list] = {}
        for ta in THERAPEUTIC_AREAS:
            ta_indications = []
            for ind_idx in range(self.max_indications_per_ta):
                key = indication_key(ta, ind_idx)
                ind_market = shared_market.indication_markets.get(
                    key
                )
                if ind_market is None:
                    ta_indications.append(
                        dict(self._PADDING_INDICATION_OBS)
                    )
                else:
                    my_drug_ids = ind_market.active_drugs.get(
                        agent, []
                    )
                    if my_drug_ids:
                        drug_shares = [
                            per_drug_shares.get(did, 0.0)
                            for did in my_drug_ids
                        ]
                        avg_share = sum(drug_shares) / len(
                            drug_shares
                        )
                    else:
                        avg_share = 0.0
                    my_drugs = 0
                    comp_drugs = 0
                    for aid, drug_ids in (
                        ind_market.active_drugs.items()
                    ):
                        if aid == agent:
                            my_drugs += len(drug_ids)
                        else:
                            comp_drugs += len(drug_ids)
                    ta_indications.append({
                        "exclusivity_remaining": (
                            ind_market.exclusivity_remaining(
                                self.multi_agent_game.time
                            )
                        ),
                        "my_avg_share": avg_share,
                        "first_mover": int(
                            ind_market.first_mover_agent == agent
                        ),
                        "my_drugs": my_drugs,
                        "competitor_drugs": comp_drugs,
                    })
            indication_obs[ta] = tuple(ta_indications)

        # Alert observations
        alerts = shared_market.get_alerts_for_agent(agent)
        recent = (
            alerts[-self.max_alerts :]
            if self.max_alerts > 0
            else []
        )
        alert_obs = []
        phase_map = {
            "Phase 2": 0.33,
            "Phase 3": 0.67,
            "Approval": 1.0,
        }
        for alert in recent:
            event_type_idx = {
                AlertType.DRUG_RELEASE: 0,
                AlertType.BD_DEAL: 1,
                AlertType.PIPELINE_LEAK: 2,
            }.get(alert.event_type, 0)
            agent_idx = (
                self.possible_agents.index(alert.agent_id)
                if alert.agent_id in self.possible_agents
                else 0
            )
            phase = 0.0
            if alert.event_type == AlertType.PIPELINE_LEAK:
                phase_str = alert.details.get("new_phase", "")
                phase = phase_map.get(phase_str, 0.0)
            alert_obs.append({
                "event_type": event_type_idx,
                "agent_index": agent_idx,
                "ta_index": TA_INDEX.get(
                    alert.therapeutic_area, 0
                ),
                "indication": alert.indication,
                "age": self.multi_agent_game.time - alert.step,
                "phase": phase,
            })
        # Pad remaining alert slots
        while len(alert_obs) < self.max_alerts:
            alert_obs.append(dict(self._PADDING_ALERT_OBS))

        result = {
            "cash": np.array(
                [game_state.cash], dtype=np.float32
            ),
            "time": np.array(
                [self.multi_agent_game.time], dtype=np.float32
            ),
            "assets": tuple(asset_obs),
            "bd_market": tuple(bd_obs),
            "indication_markets": {
                ta: tuple(inds)
                for ta, inds in indication_obs.items()
            },
            "alerts": tuple(alert_obs),
        }

        if L.ta_experience_enabled:
            result["ta_experience"] = {
                ta: game_state.ta_experience.get(ta, 0.0)
                for ta in THERAPEUTIC_AREAS
            }

        return result

    def flatten_dict_obs(self, dict_obs: dict) -> np.ndarray:
        """
        Convert a dict observation to flattened array format.

        Parameters
        ----------
        dict_obs: dict
            Dictionary observation from _get_observation_dict().

        Returns
        -------
        np.ndarray
            Flattened observation array.

        """
        L = self._layout
        obs = np.zeros(self._obs_size, dtype=np.float32)
        pos = 0

        # Global features
        obs[pos] = dict_obs["cash"][0]
        obs[pos + 1] = dict_obs["time"][0]
        pos = 2

        if L.ta_experience_enabled:
            ta_exp = dict_obs.get("ta_experience", {})
            for i, ta in enumerate(THERAPEUTIC_AREAS):
                obs[pos + i] = ta_exp.get(ta, 0.0)
            pos += L.num_ta_exp_features

        offset = L.global_features
        asset_total = L.asset_total_features
        asset_scalar = L.asset_scalar_features
        trial_feat = L.trial_features

        # Per-asset features
        for asset_d in dict_obs["assets"]:
            obs[offset] = asset_d["max_revenue"]
            obs[offset + 1] = asset_d["time_until_max_revenue"]
            obs[offset + 2] = asset_d["time_until_patent_expiry"]
            obs[offset + 3] = asset_d["pending_trial_phase"]
            obs[offset + 4] = asset_d["time_on_market"]
            obs[offset + 5] = asset_d["cost_this_step"]
            obs[offset + 6] = asset_d["revenue_this_step"]
            obs[offset + 7] = asset_d["enpv"]
            obs[offset + 8] = asset_d["eroi"]
            obs[offset + 9] = asset_d["state"]

            if L.interim_obs_enabled:
                obs[offset + L.offset_interim_signal] = (
                    asset_d.get("interim_signal", 0.0)
                )
                obs[offset + L.offset_trial_progress] = (
                    asset_d.get("trial_progress", 0.0)
                )

            obs[offset + L.offset_ta_index] = asset_d.get(
                "ta_index", 0
            )
            obs[offset + L.offset_indication] = asset_d.get(
                "indication", 0
            )

            if L.pricing_enabled:
                obs[offset + L.offset_pricing] = asset_d.get(
                    "price_multiplier", 1.0
                )

            # Trial features
            trial_off = offset + asset_scalar
            for trial in asset_d["trials"]:
                obs[trial_off] = trial["cost_remaining"]
                obs[trial_off + 1] = trial["time_remaining"]
                obs[trial_off + 2] = trial["ptrs"]
                if L.distributional_ptrs_enabled:
                    obs[trial_off + 3] = trial.get(
                        "ptrs_expected", trial["ptrs"]
                    )
                    obs[trial_off + 4] = trial.get(
                        "ptrs_confidence", 1.0
                    )
                    obs[trial_off + 5] = trial.get(
                        "ptrs_range_low", trial["ptrs"]
                    )
                    obs[trial_off + 6] = trial.get(
                        "ptrs_range_high", trial["ptrs"]
                    )
                trial_off += trial_feat

            offset += asset_total

        # BD features
        for bd_d in dict_obs["bd_market"]:
            obs[offset] = bd_d["available"]
            obs[offset + 1] = bd_d["max_revenue"]
            obs[offset + 2] = bd_d["time_until_max_revenue"]
            obs[offset + 3] = bd_d["time_until_patent_expiry"]
            obs[offset + 4] = bd_d["ta_index"]
            obs[offset + 5] = bd_d["indication"]
            obs[offset + 6] = bd_d["enpv"]
            obs[offset + 7] = bd_d["trial_phase"]
            obs[offset + 8] = bd_d["ptrs"]
            offset += _BD_OBS_FEATURES_PER_SLOT

        # Indication market features
        for ta in THERAPEUTIC_AREAS:
            for ind_d in dict_obs["indication_markets"][ta]:
                obs[offset] = ind_d["exclusivity_remaining"]
                obs[offset + 1] = ind_d["my_avg_share"]
                obs[offset + 2] = ind_d["first_mover"]
                obs[offset + 3] = ind_d["my_drugs"]
                obs[offset + 4] = ind_d["competitor_drugs"]
                offset += _INDICATION_FEATURES

        # Alert features (-1 event_type = padding, all zeros)
        for alert_d in dict_obs["alerts"]:
            event_type = alert_d["event_type"]
            if event_type >= 0:
                if event_type == 0:
                    obs[offset] = 1.0
                elif event_type == 1:
                    obs[offset + 1] = 1.0
                elif event_type == 2:
                    obs[offset + 2] = 1.0
                obs[offset + 3] = alert_d["agent_index"]
                obs[offset + 4] = alert_d["ta_index"]
                obs[offset + 5] = alert_d["indication"]
                obs[offset + 6] = alert_d["age"]
                obs[offset + 7] = alert_d["phase"]
            offset += _ALERT_FEATURES

        return obs

    def unflatten_to_dict_obs(
        self, flat_obs: np.ndarray
    ) -> dict:
        """
        Convert a flattened observation array to dict format.

        Parameters
        ----------
        flat_obs: np.ndarray
            Flattened observation array.

        Returns
        -------
        dict
            Dictionary observation.

        """
        L = self._layout
        dist_on = L.distributional_ptrs_enabled
        pos = 0

        cash = float(flat_obs[pos])
        time_val = float(flat_obs[pos + 1])
        pos = 2

        result: dict[str, Any] = {
            "cash": np.array([cash], dtype=np.float32),
            "time": np.array([time_val], dtype=np.float32),
        }

        if L.ta_experience_enabled:
            result["ta_experience"] = {
                ta: float(flat_obs[pos + i])
                for i, ta in enumerate(THERAPEUTIC_AREAS)
            }
            pos += L.num_ta_exp_features

        offset = L.global_features
        asset_total = L.asset_total_features
        asset_scalar = L.asset_scalar_features
        trial_feat = L.trial_features

        # Assets
        assets = []
        for _ in range(self.max_num_assets):
            trials = []
            trial_off = offset + asset_scalar
            for _ in range(len(TrialPhase)):
                t = {
                    "cost_remaining": float(flat_obs[trial_off]),
                    "time_remaining": int(flat_obs[trial_off + 1]),
                    "ptrs": float(flat_obs[trial_off + 2]),
                }
                if dist_on:
                    t["ptrs_expected"] = float(
                        flat_obs[trial_off + 3]
                    )
                    t["ptrs_confidence"] = float(
                        flat_obs[trial_off + 4]
                    )
                    t["ptrs_range_low"] = float(
                        flat_obs[trial_off + 5]
                    )
                    t["ptrs_range_high"] = float(
                        flat_obs[trial_off + 6]
                    )
                trials.append(t)
                trial_off += trial_feat

            asset_d: dict[str, Any] = {
                "max_revenue": float(flat_obs[offset]),
                "time_until_max_revenue": int(
                    flat_obs[offset + 1]
                ),
                "time_until_patent_expiry": int(
                    flat_obs[offset + 2]
                ),
                "pending_trial_phase": int(flat_obs[offset + 3]),
                "time_on_market": int(flat_obs[offset + 4]),
                "cost_this_step": float(flat_obs[offset + 5]),
                "revenue_this_step": float(flat_obs[offset + 6]),
                "enpv": float(flat_obs[offset + 7]),
                "eroi": float(flat_obs[offset + 8]),
                "state": int(flat_obs[offset + 9]),
                "ta_index": int(
                    flat_obs[offset + L.offset_ta_index]
                ),
                "indication": int(
                    flat_obs[offset + L.offset_indication]
                ),
                "trials": tuple(trials),
            }
            if L.interim_obs_enabled:
                asset_d["interim_signal"] = float(
                    flat_obs[offset + L.offset_interim_signal]
                )
                asset_d["trial_progress"] = float(
                    flat_obs[offset + L.offset_trial_progress]
                )
            if L.pricing_enabled:
                asset_d["price_multiplier"] = float(
                    flat_obs[offset + L.offset_pricing]
                )
            assets.append(asset_d)
            offset += asset_total

        result["assets"] = tuple(assets)

        # BD market
        bd_obs = []
        for _ in range(self.bd_max_slots):
            bd_obs.append({
                "available": int(flat_obs[offset]),
                "max_revenue": float(flat_obs[offset + 1]),
                "time_until_max_revenue": int(
                    flat_obs[offset + 2]
                ),
                "time_until_patent_expiry": int(
                    flat_obs[offset + 3]
                ),
                "ta_index": int(flat_obs[offset + 4]),
                "indication": int(flat_obs[offset + 5]),
                "enpv": float(flat_obs[offset + 6]),
                "trial_phase": int(flat_obs[offset + 7]),
                "ptrs": float(flat_obs[offset + 8]),
            })
            offset += _BD_OBS_FEATURES_PER_SLOT
        result["bd_market"] = tuple(bd_obs)

        # Indication markets
        indication_obs: dict[str, list] = {}
        for ta in THERAPEUTIC_AREAS:
            ta_inds = []
            for _ in range(self.max_indications_per_ta):
                ta_inds.append({
                    "exclusivity_remaining": float(
                        flat_obs[offset]
                    ),
                    "my_avg_share": float(flat_obs[offset + 1]),
                    "first_mover": int(flat_obs[offset + 2]),
                    "my_drugs": int(flat_obs[offset + 3]),
                    "competitor_drugs": int(flat_obs[offset + 4]),
                })
                offset += _INDICATION_FEATURES
            indication_obs[ta] = tuple(ta_inds)
        result["indication_markets"] = indication_obs

        # Alerts
        alert_obs = []
        for _ in range(self.max_alerts):
            # Decode one-hot event type (-1 = padding)
            if flat_obs[offset] == 1.0:
                event_type = 0
            elif flat_obs[offset + 1] == 1.0:
                event_type = 1
            elif flat_obs[offset + 2] == 1.0:
                event_type = 2
            else:
                event_type = -1  # padding
            alert_obs.append({
                "event_type": event_type,
                "agent_index": int(flat_obs[offset + 3]),
                "ta_index": int(flat_obs[offset + 4]),
                "indication": int(flat_obs[offset + 5]),
                "age": int(flat_obs[offset + 6]),
                "phase": float(flat_obs[offset + 7]),
            })
            offset += _ALERT_FEATURES
        result["alerts"] = tuple(alert_obs)

        return result

    def _get_info(self, agent: str) -> dict:
        """Build info dict for an agent."""
        game_state = self.multi_agent_game.agent_states[agent]
        shared_market = self.multi_agent_game.shared_market

        return {
            "cash": game_state.cash,
            "time": self.multi_agent_game.time,
            "num_assets": len(game_state.assets),
            "bankrupt": game_state.bankrupt,
            "ta_experience": dict(game_state.ta_experience),
            "capacity_ratio": game_state.capacity_ratio,
            "indication_names": dict(shared_market.indication_name_map),
            "indications_per_ta": shared_market.indications_per_ta,
        }
